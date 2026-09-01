import json
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional, Tuple
import httpx
from app.config import settings
from app.schemas import EndpointStatus

logger = logging.getLogger("docmind.llama_client")


class LlamaClient:
    def __init__(self):
        # Clientes HTTP reutilizáveis com timeouts dedicados
        self.chat_url = settings.LLAMA_CHAT_URL.rstrip("/")
        self.embed_url = settings.LLAMA_EMBED_URL.rstrip("/")
        self.rerank_url = settings.LLAMA_RERANK_URL.rstrip("/")

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Obtém vetores de embeddings para uma lista de textos via llama-server (/v1/embeddings ou /embedding).
        """
        if not texts:
            return []

        url = f"{self.embed_url}/v1/embeddings" if not self.embed_url.endswith("/v1/embeddings") else self.embed_url
        
        payload = {
            "input": texts,
            "model": "embedding"
        }

        async with httpx.AsyncClient(timeout=settings.EMBED_TIMEOUT) as client:
            try:
                response = await client.post(url, json=payload)
                if response.status_code == 404:
                    # Fallback para endpoint nativo /embedding do llama.cpp
                    native_url = f"{self.embed_url}/embedding"
                    embeddings = []
                    for t in texts:
                        res = await client.post(native_url, json={"content": t})
                        res.raise_for_status()
                        embeddings.append(res.json().get("embedding", []))
                    return embeddings

                response.raise_for_status()
                data = response.json()
                # Padrão OpenAI: data["data"] = [{"embedding": [...]}, ...]
                embeddings = [item["embedding"] for item in data.get("data", [])]
                return embeddings
            except Exception as e:
                logger.error(f"Erro ao gerar embeddings no endpoint {url}: {e}")
                raise RuntimeError(f"Falha na geração de embeddings via llama-server: {str(e)}")

    async def rerank(self, query: str, documents: List[str]) -> Optional[List[Dict[str, Any]]]:
        """
        Reclassifica documentos candidatos em relação à query no llama-server (--reranking).
        Retorna lista ordenada: [{'index': int, 'relevance_score': float}].
        Retorna None se o endpoint estiver offline para acionar fallback gracioso.
        """
        if not documents:
            return []

        # Tenta /v1/rerank ou /rerank
        url = self.rerank_url
        if not url.endswith("/v1/rerank") and not url.endswith("/rerank"):
            url = f"{self.rerank_url}/v1/rerank"

        payload = {
            "query": query,
            "documents": documents,
            "top_n": len(documents),
            "return_documents": False
        }

        async with httpx.AsyncClient(timeout=settings.RERANK_TIMEOUT) as client:
            try:
                response = await client.post(url, json=payload)
                if response.status_code in [404, 405]:
                    # Tenta formato alternativo /rerank
                    fallback_url = f"{self.rerank_url}/rerank"
                    response = await client.post(fallback_url, json=payload)
                    if response.status_code in [404, 405]:
                        # Tenta payload com 'texts' em vez de 'documents'
                        alt_payload = {"query": query, "texts": documents}
                        response = await client.post(fallback_url, json=alt_payload)

                response.raise_for_status()
                data = response.json()
                
                # Suporte aos formatos de retorno (results ou data)
                results = data.get("results") or data.get("data") or []
                formatted_results = []
                for item in results:
                    idx = item.get("index", 0)
                    score = item.get("relevance_score", item.get("score", 0.0))
                    formatted_results.append({"index": idx, "relevance_score": float(score)})
                
                # Ordenar decrescente pelo score de relevância
                formatted_results.sort(key=lambda x: x["relevance_score"], reverse=True)
                return formatted_results
            except Exception as e:
                logger.warning(f"Reranker offline/indisponível em {url}: {e}. Acionando fallback para busca vetorial direta.")
                return None

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3
    ) -> AsyncGenerator[str, None]:
        """
        Envia mensagens para o llama-server (/v1/chat/completions) e faz streaming de tokens via SSE.
        Desativa 'thinking' para economizar contexto na resposta RAG.
        """
        url = f"{self.chat_url}/v1/chat/completions" if not self.chat_url.endswith("/v1/chat/completions") else self.chat_url

        payload = {
            "messages": messages,
            "reasoning_effort": "none",
            "temperature": temperature,
            "stream": True,
            "enable_thinking": False
        }

        async with httpx.AsyncClient(timeout=settings.CHAT_TIMEOUT) as client:
            try:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk_json = json.loads(data_str)
                                choices = chunk_json.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                logger.error(f"Erro no streaming de chat com llama-server ({url}): {e}")
                yield f"\n\n[Erro na comunicação com o modelo local: {str(e)}]"

    async def check_endpoint(self, name: str, url: str) -> EndpointStatus:
        """Verifica a saúde de um endpoint individual com timeout de 2 segundos."""
        async with httpx.AsyncClient(timeout=2.0) as client:
            try:
                # Tenta /health ou root
                base = url.rstrip("/")
                res = await client.get(f"{base}/health")
                if res.status_code < 500:
                    return EndpointStatus(name=name, url=url, online=True, details="OK")
            except Exception:
                try:
                    res = await client.get(base)
                    return EndpointStatus(name=name, url=url, online=res.status_code < 500, details="Conectado")
                except Exception as e:
                    return EndpointStatus(name=name, url=url, online=False, details=str(e))
        return EndpointStatus(name=name, url=url, online=False, details="Offline")

    async def check_all_health(self) -> Dict[str, EndpointStatus]:
        chat_status = await self.check_endpoint("Llama Chat", self.chat_url)
        embed_status = await self.check_endpoint("Llama Embeddings", self.embed_url)
        rerank_status = await self.check_endpoint("Llama Reranker", self.rerank_url)
        return {
            "chat": chat_status,
            "embed": embed_status,
            "rerank": rerank_status
        }


llama_client = LlamaClient()
