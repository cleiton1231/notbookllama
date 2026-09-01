import json
import logging
from typing import AsyncGenerator, List, Dict, Any, Tuple
from app.config import settings
from app.schemas import ChatRequest, SourceReference, DocumentChunk
from app.services.llama_client import llama_client
from app.services.vector_store import vector_store

logger = logging.getLogger("docmind.rag_engine")


class RAGEngine:
    def __init__(self):
        self.llama = llama_client
        self.vectors = vector_store

    def _estimate_tokens(self, text: str) -> int:
        """Estimativa aproximada: ~4 caracteres por token em português/inglês."""
        return max(1, len(text) // 4)

    def _build_context_prompt(self, sources: List[Tuple[DocumentChunk, float, float | None]]) -> str:
        """Formata os trechos recuperados em blocos numerados e identificados."""
        context_parts = []
        for idx, (chunk, sim_score, rerank_score) in enumerate(sources, 1):
            page_info = f" | Página {chunk.page_number}" if chunk.page_number else ""
            score_info = f" (Relevância: {rerank_score:.2f})" if rerank_score is not None else f" (Similaridade: {sim_score:.2f})"
            header = f"[Fonte {idx}: {chunk.filename}{page_info}{score_info}]"
            context_parts.append(f"{header}\n{chunk.content}")
        
        return "\n\n---\n\n".join(context_parts)

    async def stream_rag_response(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Executa o pipeline RAG completo em 2 estágios e emite eventos SSE tipados:
        - event: sources
        - event: token
        - event: done
        - event: error
        """
        try:
            # 1. Gerar Embedding da Pergunta
            query_embeddings = await self.llama.get_embeddings([request.message])
            if not query_embeddings or len(query_embeddings) == 0:
                yield "event: error\ndata: " + json.dumps({"error": "Falha ao gerar embedding da pergunta no llama-server."}) + "\n\n"
                return

            query_vec = query_embeddings[0]

            # 2. Busca Vetorial Ampla (Estágio 1: Recall)
            top_k_retrieval = request.top_k or settings.TOP_K_RETRIEVAL
            candidate_chunks = await self.vectors.search_chunks(
                query_embedding=query_vec,
                top_k=top_k_retrieval,
                doc_ids=request.doc_ids
            )

            if not candidate_chunks:
                # Nenhum chunk encontrado
                no_docs_msg = "Nenhum documento indexado correspondente à sua busca foi encontrado. Faça o upload de arquivos na barra lateral para começar a pesquisar!"
                yield "event: sources\ndata: " + json.dumps({"sources": []}) + "\n\n"
                yield "event: token\ndata: " + json.dumps({"token": no_docs_msg}) + "\n\n"
                yield "event: done\ndata: {}\n\n"
                return

            # 3. Reranking de Alta Precisão (Estágio 2: Precision)
            final_sources: List[Tuple[DocumentChunk, float, float | None]] = []
            top_k_final = min(settings.TOP_K_RERANK, len(candidate_chunks))

            if request.use_rerank:
                doc_texts = [chunk.content for chunk, _ in candidate_chunks]
                rerank_results = await self.llama.rerank(request.message, doc_texts)

                if rerank_results:
                    # Rerank funcionou com sucesso
                    for item in rerank_results[:top_k_final]:
                        idx = item["index"]
                        score = item["relevance_score"]
                        chunk, sim_score = candidate_chunks[idx]
                        final_sources.append((chunk, sim_score, score))
                else:
                    # Fallback gracioso para a similaridade vetorial do ChromaDB
                    logger.info("Executando fallback para similaridade de cosseno pura.")
                    for chunk, sim_score in candidate_chunks[:top_k_final]:
                        final_sources.append((chunk, sim_score, None))
            else:
                for chunk, sim_score in candidate_chunks[:top_k_final]:
                    final_sources.append((chunk, sim_score, None))

            # 4. Enviar fontes estruturadas para o frontend via SSE
            source_payload = []
            for idx, (chunk, sim_score, rerank_score) in enumerate(final_sources, 1):
                source_payload.append(
                    SourceReference(
                        doc_id=chunk.doc_id,
                        filename=chunk.filename,
                        chunk_index=chunk.chunk_index,
                        page_number=chunk.page_number,
                        snippet=chunk.content[:280] + ("..." if len(chunk.content) > 280 else ""),
                        score=round(sim_score, 4),
                        rerank_score=round(rerank_score, 4) if rerank_score is not None else None
                    ).model_dump()
                )

            yield "event: sources\ndata: " + json.dumps({"sources": source_payload}) + "\n\n"

            # 5. Montagem do Contexto e Prompt com Gestão de Token Budget
            context_text = self._build_context_prompt(final_sources)
            system_prompt = (
                "Você é o DocMind, um Professor Universitário e Especialista Sênior em Ciência da Computação e Análise de Documentos.\n"
                "Sua missão é explicar os conceitos com profunda clareza didática, precisão técnica e rigor conceitual, baseando-se estritamente nas Fontes fornecidas abaixo.\n\n"
                "### DIRETRIZES DE RESPOSTA E ESTRUTURAÇÃO:\n"
                "1. **Didática & Intuição:** Comece explicando a ideia central e a motivação do problema antes de entrar no código. Use analogias claras para facilitar a compreensão.\n"
                "2. **Citações Precisas:** Sempre que fizer afirmações ou apresentar códigos, referencie a fonte exata no formato: `[NomeDoArquivo.pdf, pág. X]`.\n"
                "3. **Tabelas Comparativas:** Sempre que houver 2 ou mais conceitos, técnicas ou soluções (ex: malloc vs calloc, diferentes soluções de alocação de matrizes, estruturas de dados), crie uma tabela Markdown comparando: Mecanismo, Contiguidade de Memória, Complexidade, Prós e Contras.\n"
                "4. **Código Didaticamente Comentado:** Ao exibir códigos em C ou qualquer linguagem, comente as linhas críticas explicando o papel de cada ponteiro, tipo de retorno e cálculo de índice.\n"
                "5. **⚠️ Pontos de Atenção & Armadilhas Comuns:** Inclua ao final uma seção prática alertando sobre erros comuns (ex: vazamento de memória / memory leaks, ponteiros soltos, falta de checagem de NULL no malloc, ordem incorreta do free).\n"
                "6. **Fidelidade Total:** Baseie-se estritamente no material fornecido. Se uma pergunta for além das fontes, aponte com transparência o que está e o que não está documentado.\n\n"
                f"### FONTES DISPONÍVEIS:\n{context_text}"
            )

            # Histórico recente truncado para não estourar a janela de contexto
            messages = [{"role": "system", "content": system_prompt}]
            
            # Adiciona até 4 últimas mensagens de histórico se houver
            history_slice = request.history[-4:] if request.history else []
            for h in history_slice:
                messages.append({"role": h.role, "content": h.content})
            
            messages.append({"role": "user", "content": request.message})

            # 6. Streaming dos tokens da LLM
            async for token in self.llama.stream_chat(messages, temperature=request.temperature):
                yield "event: token\ndata: " + json.dumps({"token": token}) + "\n\n"

            # 7. Finalização do SSE
            yield "event: done\ndata: {}\n\n"

        except Exception as e:
            logger.error(f"Erro no pipeline RAG: {e}", exc_info=True)
            yield "event: error\ndata: " + json.dumps({"error": f"Erro interno no processamento RAG: {str(e)}"}) + "\n\n"


rag_engine = RAGEngine()
