import logging
from typing import Any

from app.schemas import DocumentChunk
from app.services.bm25_search import BM25Search
from app.services.bm25_search import bm25_search as default_bm25_search
from app.services.vector_store import vector_store as default_vector_store

logger = logging.getLogger("docmind.hybrid_search")


def reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[DocumentChunk, float]]],
    weights: list[float] | None = None,
    k_rrf: int = 60,
    top_k: int | None = None
) -> list[tuple[DocumentChunk, float]]:
    """
    Combina múltiplos rankings de documentos usando Reciprocal Rank Fusion (RRF).

    Fórmula:
        Score_RRF(d) = sum_{m=1}^{M} ( w_m / (k_rrf + rank_m(d)) )

    Onde rank_m(d) é a posição 1-based do documento d no ranking da modalidade m.
    """
    if not ranked_lists:
        return []

    # Se apenas uma lista contiver itens e as demais estiverem vazias
    non_empty_lists = [rl for rl in ranked_lists if rl]
    if not non_empty_lists:
        return []

    # Dicionário de agregação por chunk_id: chunk_id -> (DocumentChunk, score_acumulado)
    chunk_map: dict[str, DocumentChunk] = {}
    fused_scores: dict[str, float] = {}

    for list_idx, rank_list in enumerate(ranked_lists):
        w = weights[list_idx] if (weights and list_idx < len(weights)) else 1.0
        for rank_zero_based, (chunk, _) in enumerate(rank_list):
            rank_one_based = rank_zero_based + 1
            cid = chunk.chunk_id

            if cid not in chunk_map:
                chunk_map[cid] = chunk
                fused_scores[cid] = 0.0

            # Contribuição RRF ponderada
            rrf_contrib = float(w) / float(k_rrf + rank_one_based)
            fused_scores[cid] += rrf_contrib

    # Ordenação por score RRF decrescente com desempate determinístico
    ranked_chunks: list[tuple[DocumentChunk, float]] = [
        (chunk_map[cid], score)
        for cid, score in fused_scores.items()
    ]
    ranked_chunks.sort(key=lambda item: (-item[1], item[0].chunk_index, item[0].chunk_id))

    if top_k is not None and top_k > 0:
        return ranked_chunks[:top_k]
    return ranked_chunks


class HybridSearcher:
    """
    Mecanismo de busca híbrida que combina recuperação densa (vetorial ChromaDB)
    e recuperação esparsa (BM25 lexical) via Reciprocal Rank Fusion (RRF).
    """

    def __init__(
        self,
        vector_store: Any | None = None,
        bm25_search_instance: BM25Search | None = None,
        default_k: int = 60
    ):
        self.vector_store = vector_store or default_vector_store
        self.bm25_search = bm25_search_instance or default_bm25_search
        self.default_k = default_k

    def reciprocal_rank_fusion(
        self,
        ranked_lists: list[list[tuple[DocumentChunk, float]]],
        weights: list[float] | None = None,
        k_rrf: int | None = None,
        top_k: int | None = None
    ) -> list[tuple[DocumentChunk, float]]:
        """Aplica RRF aos rankings fornecidos."""
        k = k_rrf if k_rrf is not None else self.default_k
        return reciprocal_rank_fusion(
            ranked_lists=ranked_lists,
            weights=weights,
            k_rrf=k,
            top_k=top_k
        )

    async def search(
        self,
        query: str,
        query_embedding: list[float] | None = None,
        top_k: int = 10,
        doc_ids: list[str] | None = None,
        k_rrf: int | None = None,
        alpha: float = 0.5,
        vector_chunks: list[tuple[DocumentChunk, float]] | None = None,
        bm25_chunks: list[tuple[DocumentChunk, float]] | None = None
    ) -> list[tuple[DocumentChunk, float]]:
        """
        Executa busca híbrida integrando busca vetorial e busca BM25 com fusão RRF.

        Parâmetros:
            query: Texto da consulta do usuário.
            query_embedding: Vetor denso gerado pelo llama-server (opcional se vector_chunks já fornecido).
            top_k: Quantidade máxima de chunks a retornar.
            doc_ids: Filtro de documentos específicos (opcional).
            k_rrf: Constante de suavização RRF (padrão: 60).
            alpha: Peso da busca vetorial (0.0 a 1.0, padrão 0.5 = balanceado).
            vector_chunks: Chunks vetoriais pré-recuperados (opcional).
            bm25_chunks: Chunks BM25 pré-recuperados (opcional).

        Retorno:
            Lista de tuplas (DocumentChunk, rrf_score) ordenadas por relevância combinada.
        """
        k = k_rrf if k_rrf is not None else self.default_k
        candidate_k = max(top_k * 2, 20)

        # 1. Recuperação Vetorial (ChromaDB) se não fornecida previamente
        if vector_chunks is None:
            if query_embedding is not None and self.vector_store is not None:
                try:
                    vector_chunks = await self.vector_store.search_chunks(
                        query_embedding=query_embedding,
                        top_k=candidate_k,
                        doc_ids=doc_ids
                    )
                except Exception as e:  # noqa: BLE001
                    logger.error(f"Erro na busca vetorial durante hybrid search: {e}")
                    vector_chunks = []
            else:
                vector_chunks = []

        # 2. Recuperação Lexical (BM25) se não fornecida previamente
        if bm25_chunks is None:
            if self.bm25_search is not None and query:
                try:
                    bm25_chunks = self.bm25_search.search(
                        query=query,
                        top_k=candidate_k,
                        doc_ids=doc_ids
                    )
                except Exception as e:  # noqa: BLE001
                    logger.error(f"Erro na busca BM25 durante hybrid search: {e}")
                    bm25_chunks = []
            else:
                bm25_chunks = []

        # 3. Ponderação baseada em alpha
        # Se alpha=0.5 -> w_vec=1.0, w_bm25=1.0
        # Se alpha=0.8 -> w_vec=1.6, w_bm25=0.4
        w_vec = 2.0 * alpha
        w_bm25 = 2.0 * (1.0 - alpha)

        # 4. Fusão RRF
        return self.reciprocal_rank_fusion(
            ranked_lists=[vector_chunks, bm25_chunks],
            weights=[w_vec, w_bm25],
            k_rrf=k,
            top_k=top_k
        )


# Helper funcional de alto nível para integração com rag_engine
async def hybrid_search_chunks(
    query: str,
    query_embedding: list[float] | None = None,
    top_k: int = 10,
    doc_ids: list[str] | None = None,
    k_rrf: int = 60,
    alpha: float = 0.5,
    vector_store: Any | None = None,
    bm25_search_instance: BM25Search | None = None,
    vector_chunks: list[tuple[DocumentChunk, float]] | None = None,
    bm25_chunks: list[tuple[DocumentChunk, float]] | None = None
) -> list[tuple[DocumentChunk, float]]:
    """
    Função utilitária de busca híbrida assíncrona recomendada para o rag_engine.py.
    """
    searcher = HybridSearcher(
        vector_store=vector_store,
        bm25_search_instance=bm25_search_instance,
        default_k=k_rrf
    )
    return await searcher.search(
        query=query,
        query_embedding=query_embedding,
        top_k=top_k,
        doc_ids=doc_ids,
        k_rrf=k_rrf,
        alpha=alpha,
        vector_chunks=vector_chunks,
        bm25_chunks=bm25_chunks
    )


# Instâncias singleton para reuso
hybrid_searcher = HybridSearcher()
hybrid_search_instance = hybrid_searcher
