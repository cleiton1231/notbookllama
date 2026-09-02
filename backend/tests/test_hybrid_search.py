from unittest.mock import AsyncMock, MagicMock

import pytest
from app.schemas import DocumentChunk
from app.services.bm25_search import BM25Index, BM25Search, strip_accents, tokenize
from app.services.hybrid_search import (
    HybridSearcher,
    hybrid_search_chunks,
    reciprocal_rank_fusion,
)

# =====================================================================
# Fixtures & Helper Chunks
# =====================================================================

@pytest.fixture
def sample_chunks() -> list[DocumentChunk]:
    return [
        DocumentChunk(
            chunk_id="doc1_c0",
            doc_id="doc1",
            filename="alocacao_memoria.pdf",
            chunk_index=0,
            page_number=1,
            content="A função malloc aloca blocos contíguos de memória no heap em C.",
            char_count=65
        ),
        DocumentChunk(
            chunk_id="doc1_c1",
            doc_id="doc1",
            filename="alocacao_memoria.pdf",
            chunk_index=1,
            page_number=2,
            content="A função free libera a memória previamente alocada dinamicamente.",
            char_count=67
        ),
        DocumentChunk(
            chunk_id="doc2_c0",
            doc_id="doc2",
            filename="estruturas_dados.pdf",
            chunk_index=0,
            page_number=1,
            content="Árvores binárias de busca mantêm elementos ordenados na memória com complexidade O(log n).",
            char_count=90
        ),
        DocumentChunk(
            chunk_id="doc2_c1",
            doc_id="doc2",
            filename="estruturas_dados.pdf",
            chunk_index=1,
            page_number=3,
            content="Tabelas hash utilizam funções hash para busca em tempo constante O(1).",
            char_count=70
        ),
    ]


# =====================================================================
# 1. Testes de Tokenização e Normalização BM25
# =====================================================================

def test_tokenize_basic():
    tokens = tokenize("Hello, World! DocMind RAG 2026.")
    assert "hello" in tokens
    assert "world" in tokens
    assert "docmind" in tokens
    assert "rag" in tokens
    assert "2026" in tokens


def test_tokenize_accent_normalization():
    # Normalização de acentos em português
    text1 = "Alocação de memória dinâmica e índices rápidos."
    tokens1 = tokenize(text1, normalize_accents=True)
    assert "alocacao" in tokens1
    assert "memoria" in tokens1
    assert "dinamica" in tokens1
    assert "indices" in tokens1
    assert "rapidos" in tokens1

    # Sem normalização preserva acentos
    tokens_raw = tokenize(text1, normalize_accents=False)
    assert "alocação" in tokens_raw
    assert "memória" in tokens_raw


def test_tokenize_stopwords():
    text = "O ponteiro para a memória foi alocado com malloc."
    tokens_with_sw = tokenize(text, remove_stopwords=False)
    tokens_without_sw = tokenize(text, remove_stopwords=True)

    assert "para" in tokens_with_sw
    assert "foi" in tokens_with_sw
    assert "para" not in tokens_without_sw
    assert "foi" not in tokens_without_sw
    assert "malloc" in tokens_without_sw
    assert "ponteiro" in tokens_without_sw


def test_strip_accents():
    assert strip_accents("olá mundo café árvore") == "ola mundo cafe arvore"
    assert strip_accents("MALLOC & CALLOC") == "MALLOC & CALLOC"


# =====================================================================
# 2. Testes de Busca Lexical BM25
# =====================================================================

def test_bm25_empty_index():
    bm25 = BM25Search()
    results = bm25.search("malloc")
    assert results == []
    assert bm25.get_chunk_count() == 0
    assert bm25.get_doc_ids() == []


def test_bm25_empty_query(sample_chunks):
    bm25 = BM25Search()
    bm25.index_chunks(sample_chunks)
    assert bm25.search("") == []
    assert bm25.search("   ") == []
    assert bm25.search("!@#$%^&*()") == []


def test_bm25_exact_match(sample_chunks):
    bm25 = BM25Search()
    bm25.index_chunks(sample_chunks)

    # Busca por "malloc" deve retornar doc1_c0 em 1º lugar com score positivo
    results = bm25.search("malloc")
    assert len(results) > 0
    top_chunk, top_score = results[0]
    assert top_chunk.chunk_id == "doc1_c0"
    assert top_score > 0.0
    assert "malloc" in top_chunk.content


def test_bm25_accent_insensitive_search(sample_chunks):
    bm25 = BM25Search()
    bm25.index_chunks(sample_chunks)

    # Buscar "arvores binarias" sem acento deve casar com "Árvores binárias"
    results = bm25.search("arvores binarias")
    assert len(results) > 0
    assert results[0][0].chunk_id == "doc2_c0"

    # Buscar com acento também deve casar
    results_accented = bm25.search("Árvores binárias")
    assert len(results_accented) > 0
    assert results_accented[0][0].chunk_id == "doc2_c0"


def test_bm25_partial_match_and_ranking(sample_chunks):
    bm25 = BM25Search()
    bm25.index_chunks(sample_chunks)

    # doc1_c0 tem "aloca" e "memoria", doc1_c1 tem "memoria" e "libera", doc2_c0 tem "memoria"
    # Uma busca por "aloca memoria heap" deve pontuar doc1_c0 acima de doc1_c1 e doc2_c0
    results = bm25.search("aloca memoria heap")
    assert len(results) >= 2
    assert results[0][0].chunk_id == "doc1_c0"
    # O score do primeiro deve ser estritamente maior que o do segundo
    assert results[0][1] > results[1][1]


def test_bm25_doc_ids_filter(sample_chunks):
    bm25 = BM25Search()
    bm25.index_chunks(sample_chunks)

    # Busca por termo "memória" existe em doc1 e doc2
    all_results = bm25.search("memoria", top_k=10)
    found_doc_ids = {chunk.doc_id for chunk, _ in all_results}
    assert "doc1" in found_doc_ids
    assert "doc2" in found_doc_ids

    # Filtrar exclusivamente para doc2
    filtered_doc2 = bm25.search("memoria", doc_ids=["doc2"])
    for chunk, _ in filtered_doc2:
        assert chunk.doc_id == "doc2"

    # Filtrar para doc inexistente
    empty_filter = bm25.search("memoria", doc_ids=["doc_inexistente"])
    assert empty_filter == []


def test_bm25_term_frequency_saturation():
    # Verifica que termos repetidos têm ganho decrescente (k1=1.5)
    c1 = DocumentChunk(
        chunk_id="c1", doc_id="d1", filename="f.txt", chunk_index=0,
        content="malloc malloc malloc", char_count=20
    )
    c2 = DocumentChunk(
        chunk_id="c2", doc_id="d2", filename="f.txt", chunk_index=0,
        content="malloc malloc malloc malloc malloc malloc", char_count=42
    )
    bm25 = BM25Search(k1=1.5, b=0.0)  # b=0 para isolar efeito do TF puro sem penalidade de tamanho
    bm25.index_chunks([c1, c2])

    score1 = bm25.score_chunk(["malloc"], "c1")
    score2 = bm25.score_chunk(["malloc"], "c2")

    # c2 tem o dobro de ocorrências, mas devido à saturação (k1 + 1), score2 < 2 * score1
    assert score2 > score1
    assert score2 < 2.0 * score1


def test_bm25_length_normalization():
    # Documento mais curto com a mesma frequência do termo deve ter score maior (b=0.75)
    short_chunk = DocumentChunk(
        chunk_id="short", doc_id="d1", filename="f.txt", chunk_index=0,
        content="algoritmo de ordenacao", char_count=22
    )
    long_chunk = DocumentChunk(
        chunk_id="long", doc_id="d2", filename="f.txt", chunk_index=0,
        content="algoritmo muito longo com varias palavras irrelevantes adicionais no texto para aumentar o tamanho do documento consideravelmente", char_count=135
    )
    bm25 = BM25Search(k1=1.5, b=0.75)
    bm25.index_chunks([short_chunk, long_chunk])

    res = bm25.search("algoritmo")
    assert len(res) == 2
    assert res[0][0].chunk_id == "short"
    assert res[0][1] > res[1][1]


def test_bm25_incremental_add_remove_clear(sample_chunks):
    bm25 = BM25Search()
    bm25.add_chunks([sample_chunks[0], sample_chunks[1]])
    assert bm25.get_chunk_count() == 2
    assert bm25.get_doc_ids() == ["doc1"]

    # Adiciona mais chunks
    bm25.add_chunks([sample_chunks[2], sample_chunks[3]])
    assert bm25.get_chunk_count() == 4
    assert set(bm25.get_doc_ids()) == {"doc1", "doc2"}

    # Remove doc1
    bm25.remove_document("doc1")
    assert bm25.get_chunk_count() == 2
    assert bm25.get_doc_ids() == ["doc2"]
    assert bm25.search("malloc") == []  # doc1 foi removido

    # Limpa completamente
    bm25.clear()
    assert bm25.get_chunk_count() == 0
    assert bm25.get_doc_ids() == []


def test_bm25_top_k_limit(sample_chunks):
    bm25 = BM25Search()
    bm25.index_chunks(sample_chunks)

    # 3 chunks contêm termos relevantes para "memória busca"
    res_1 = bm25.search("memoria busca", top_k=1)
    res_2 = bm25.search("memoria busca", top_k=2)
    assert len(res_1) == 1
    assert len(res_2) == 2


# =====================================================================
# 3. Testes de Reciprocal Rank Fusion (RRF)
# =====================================================================

def test_rrf_exact_formula_calculation():
    c_a = DocumentChunk(chunk_id="A", doc_id="d1", filename="f.txt", chunk_index=0, content="A", char_count=1)
    c_b = DocumentChunk(chunk_id="B", doc_id="d2", filename="f.txt", chunk_index=0, content="B", char_count=1)
    c_c = DocumentChunk(chunk_id="C", doc_id="d3", filename="f.txt", chunk_index=0, content="C", char_count=1)

    # Vetor: A (rank 1), B (rank 2)
    vector_list = [(c_a, 0.95), (c_b, 0.85)]
    # BM25: B (rank 1), C (rank 2)
    bm25_list = [(c_b, 12.0), (c_c, 8.0)]

    k = 60
    # Cálculo analítico esperado:
    # A: 1/(60+1) + 0 = 1/61 ≈ 0.0163934426
    # B: 1/(60+2) + 1/(60+1) = 1/62 + 1/61 = 0.016129032 + 0.0163934426 ≈ 0.0325224748
    # C: 0 + 1/(60+2) = 1/62 ≈ 0.016129032
    fused = reciprocal_rank_fusion([vector_list, bm25_list], k_rrf=k)

    assert len(fused) == 3
    # B deve ser 1º colocado pois apareceu bem posicionado em ambos os rankings
    assert fused[0][0].chunk_id == "B"
    assert pytest.approx(fused[0][1], rel=1e-5) == (1.0 / 61.0 + 1.0 / 62.0)

    # A deve ser 2º colocado (1/61 > 1/62)
    assert fused[1][0].chunk_id == "A"
    assert pytest.approx(fused[1][1], rel=1e-5) == (1.0 / 61.0)

    # C deve ser 3º colocado
    assert fused[2][0].chunk_id == "C"
    assert pytest.approx(fused[2][1], rel=1e-5) == (1.0 / 62.0)


def test_rrf_with_alpha_weights():
    c_a = DocumentChunk(chunk_id="A", doc_id="d1", filename="f.txt", chunk_index=0, content="A", char_count=1)
    c_b = DocumentChunk(chunk_id="B", doc_id="d2", filename="f.txt", chunk_index=0, content="B", char_count=1)

    # Vetor rank 1: A
    vector_list = [(c_a, 0.9)]
    # BM25 rank 1: B
    bm25_list = [(c_b, 10.0)]

    # Se alpha = 0.9 (peso forte para busca vetorial):
    # w_vec = 2 * 0.9 = 1.8, w_bm25 = 2 * 0.1 = 0.2
    weights = [1.8, 0.2]
    fused = reciprocal_rank_fusion([vector_list, bm25_list], weights=weights, k_rrf=60)

    assert fused[0][0].chunk_id == "A"
    assert pytest.approx(fused[0][1], rel=1e-5) == 1.8 / 61.0
    assert fused[1][0].chunk_id == "B"
    assert pytest.approx(fused[1][1], rel=1e-5) == 0.2 / 61.0


def test_rrf_empty_lists():
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[], []]) == []

    # Uma lista vazia e outra populada
    c = DocumentChunk(chunk_id="A", doc_id="d1", filename="f.txt", chunk_index=0, content="A", char_count=1)
    fused = reciprocal_rank_fusion([[(c, 0.8)], []], k_rrf=60)
    assert len(fused) == 1
    assert fused[0][0].chunk_id == "A"
    assert pytest.approx(fused[0][1], rel=1e-5) == 1.0 / 61.0


def test_rrf_top_k():
    chunks = [
        DocumentChunk(chunk_id=f"c_{i}", doc_id=f"d_{i}", filename="f.txt", chunk_index=i, content=f"C {i}", char_count=3)
        for i in range(10)
    ]
    vector_list = [(c, 1.0 - i * 0.1) for i, c in enumerate(chunks)]
    fused = reciprocal_rank_fusion([vector_list], top_k=3, k_rrf=60)
    assert len(fused) == 3


# =====================================================================
# 4. Testes do HybridSearcher Assíncrono
# =====================================================================

@pytest.mark.asyncio
async def test_hybrid_searcher_full_flow(sample_chunks):
    # Mock do VectorStore
    mock_vector_store = MagicMock()
    mock_vector_store.search_chunks = AsyncMock(return_value=[
        (sample_chunks[0], 0.88),
        (sample_chunks[2], 0.75)
    ])

    # Instância real do BM25Search
    bm25 = BM25Search()
    bm25.index_chunks(sample_chunks)

    searcher = HybridSearcher(
        vector_store=mock_vector_store,
        bm25_search_instance=bm25,
        default_k=60
    )

    # Busca por "malloc"
    results = await searcher.search(
        query="malloc",
        query_embedding=[0.1, 0.2, 0.3],
        top_k=3,
        alpha=0.5
    )

    assert len(results) > 0
    # sample_chunks[0] (doc1_c0) apareceu em 1º no vector search e em 1º no BM25
    top_chunk, score = results[0]
    assert top_chunk.chunk_id == "doc1_c0"
    assert score > (1.0 / 61.0)  # Fused score deve somar contribuições de ambas as fontes

    # Verifica se o vector_store foi chamado com os argumentos corretos
    mock_vector_store.search_chunks.assert_called_once()


@pytest.mark.asyncio
async def test_hybrid_search_chunks_convenience(sample_chunks):
    mock_vector_store = MagicMock()
    mock_vector_store.search_chunks = AsyncMock(return_value=[(sample_chunks[1], 0.80)])

    bm25 = BM25Search()
    bm25.index_chunks(sample_chunks)

    results = await hybrid_search_chunks(
        query="libera memoria dinamicamente",
        query_embedding=[0.5, 0.5],
        top_k=2,
        vector_store=mock_vector_store,
        bm25_search_instance=bm25
    )

    assert len(results) > 0
    assert results[0][0].chunk_id == "doc1_c1"


@pytest.mark.asyncio
async def test_hybrid_search_with_precomputed_chunks(sample_chunks):
    # Permite passar vector_chunks e bm25_chunks diretamente sem rede ou banco
    vec_chunks = [(sample_chunks[0], 0.9)]
    bm25_chunks = [(sample_chunks[0], 15.0), (sample_chunks[1], 8.0)]

    results = await hybrid_search_chunks(
        query="qualquer",
        vector_chunks=vec_chunks,
        bm25_chunks=bm25_chunks,
        top_k=2
    )

    assert len(results) == 2
    assert results[0][0].chunk_id == "doc1_c0"
    assert results[1][0].chunk_id == "doc1_c1"


# =====================================================================
# 5. Testes Adicionais de Casos de Borda e Robustez
# =====================================================================

def test_bm25_chunk_update_reindex():
    bm25 = BM25Search()
    initial_chunk = DocumentChunk(
        chunk_id="c_update", doc_id="d1", filename="doc.txt", chunk_index=0,
        content="texto inicial sobre compiladores", char_count=32
    )
    bm25.index_chunks([initial_chunk])
    assert len(bm25.search("compiladores")) == 1

    # Atualiza o mesmo chunk_id com novo conteúdo
    updated_chunk = DocumentChunk(
        chunk_id="c_update", doc_id="d1", filename="doc.txt", chunk_index=0,
        content="novo texto totalmente focado em interpretadores", char_count=47
    )
    bm25.add_chunks([updated_chunk])
    assert bm25.get_chunk_count() == 1
    assert bm25.search("compiladores") == []
    assert len(bm25.search("interpretadores")) == 1


def test_bm25_multiple_doc_ids_filter(sample_chunks):
    bm25 = BM25Search()
    bm25.index_chunks(sample_chunks)

    # Filtrar por múltiplos doc_ids
    results = bm25.search("memoria", doc_ids=["doc1", "doc2"])
    found_docs = {c.doc_id for c, _ in results}
    assert "doc1" in found_docs
    assert "doc2" in found_docs

    # Filtrar por apenas um que contém
    results_only_doc1 = bm25.search("memoria", doc_ids=["doc1"])
    for c, _ in results_only_doc1:
        assert c.doc_id == "doc1"


def test_bm25_special_characters_and_punctuation():
    chunk = DocumentChunk(
        chunk_id="special_1", doc_id="d_special", filename="code.c", chunk_index=0,
        content="void* ptr = malloc(sizeof(int) * 10); // O(1) alloc!\n/* ponteiro -> heap */",
        char_count=78
    )
    bm25 = BM25Search()
    bm25.index_chunks([chunk])

    # Deve casar com termos extraídos ignorando pontuações
    assert len(bm25.search("malloc")) == 1
    assert len(bm25.search("sizeof")) == 1
    assert len(bm25.search("ponteiro heap")) == 1


@pytest.mark.asyncio
async def test_hybrid_searcher_graceful_degradation_on_vector_error(sample_chunks):
    # Simula erro de conexão no VectorStore (ChromaDB)
    failing_vector_store = MagicMock()
    failing_vector_store.search_chunks = AsyncMock(side_effect=RuntimeError("ChromaDB indisponível"))

    bm25 = BM25Search()
    bm25.index_chunks(sample_chunks)

    searcher = HybridSearcher(
        vector_store=failing_vector_store,
        bm25_search_instance=bm25,
        default_k=60
    )

    # Não deve estourar exceção, deve usar resultados do BM25 como fallback gracioso
    results = await searcher.search(
        query="malloc",
        query_embedding=[0.1, 0.2],
        top_k=5
    )

    assert len(results) > 0
    assert results[0][0].chunk_id == "doc1_c0"


@pytest.mark.asyncio
async def test_hybrid_searcher_graceful_degradation_on_bm25_error():
    c = DocumentChunk(chunk_id="c_vec", doc_id="d1", filename="v.txt", chunk_index=0, content="vetor", char_count=5)
    mock_vector_store = MagicMock()
    mock_vector_store.search_chunks = AsyncMock(return_value=[(c, 0.92)])

    failing_bm25 = MagicMock()
    failing_bm25.search = MagicMock(side_effect=Exception("Erro no BM25"))

    searcher = HybridSearcher(
        vector_store=mock_vector_store,
        bm25_search_instance=failing_bm25,
        default_k=60
    )

    # Não deve estourar exceção, deve usar resultados vetoriais
    results = await searcher.search(
        query="qualquer",
        query_embedding=[0.1, 0.2],
        top_k=5
    )

    assert len(results) == 1
    assert results[0][0].chunk_id == "c_vec"


def test_bm25_index_alias_and_singletons():
    from app.services.bm25_search import bm25_search
    from app.services.hybrid_search import hybrid_search_instance, hybrid_searcher

    assert BM25Index is BM25Search
    assert isinstance(bm25_search, BM25Search)
    assert hybrid_search_instance is hybrid_searcher
    assert isinstance(hybrid_searcher, HybridSearcher)


# =====================================================================
# 6. Testes para Cobertura Total de Linhas e Ramificações
# =====================================================================

def test_bm25_edge_cases_empty_inputs():
    bm25 = BM25Search()
    # tokenize vazio/None
    assert tokenize("") == []
    assert tokenize(None) == []

    # add_chunks vazio
    bm25.add_chunks([])
    assert bm25.get_chunk_count() == 0

    # remove_document inexistente
    bm25.remove_document("doc_inexistente")
    assert bm25.get_chunk_count() == 0

    # get_idf para termo nunca visto
    assert bm25.get_idf("termo_inexistente") == 0.0

    # score_chunk para chunk_id inexistente
    assert bm25.score_chunk(["termo"], "chunk_inexistente") == 0.0

    # search com top_k <= 0
    c = DocumentChunk(chunk_id="c1", doc_id="d1", filename="f.txt", chunk_index=0, content="termo presente", char_count=14)
    bm25.index_chunks([c])
    res_zero = bm25.search("termo", top_k=0)
    assert len(res_zero) == 1  # top_k <= 0 retorna todos


@pytest.mark.asyncio
async def test_hybrid_searcher_no_embedding_and_no_bm25():
    # Instância sem query_embedding e sem bm25_search
    searcher = HybridSearcher(
        vector_store=None,
        bm25_search_instance=None,
        default_k=60
    )

    results = await searcher.search(
        query="",
        query_embedding=None,
        top_k=5
    )

    assert results == []
