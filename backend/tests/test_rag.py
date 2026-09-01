import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from app.services.document_parser import parse_document, calculate_sha256
from app.services.chunker import split_text_into_chunks, create_document_chunks
from app.services.rag_engine import RAGEngine
from app.schemas import ChatRequest, ChatMessage, DocumentMetadata, DocumentChunk


def test_calculate_sha256():
    data = b"Hello DocMind RAG"
    h1 = calculate_sha256(data)
    h2 = calculate_sha256(data)
    assert h1 == h2
    assert len(h1) == 64


def test_parse_plain_text():
    content = "Linha 1 do documento.\n\nLinha 2 com informacoes importantes.".encode("utf-8")
    parsed = parse_document(content, "teste.txt")
    assert parsed.filename == "teste.txt"
    assert parsed.file_type == "text"
    assert len(parsed.pages) == 1
    assert "Linha 1 do documento." in parsed.pages[0].text


def test_split_text_into_chunks():
    text = "Parágrafo um com algum texto informativo.\n\nParágrafo dois com detalhes técnicos adicionais.\n\nParágrafo três de conclusão."
    chunks = split_text_into_chunks(text, chunk_size=80, chunk_overlap=15)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= 120  # Respeita o tamanho máximo com margem


def test_create_document_chunks():
    content = "Seção 1: Arquitetura RAG.\n\nSeção 2: llama.cpp e embeddings locais.\n\nSeção 3: Reranker de alta precisão.".encode("utf-8")
    parsed = parse_document(content, "manual.md")
    chunks = create_document_chunks(parsed, doc_id="doc-123", chunk_size=60, chunk_overlap=10)
    
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.doc_id == "doc-123"
        assert chunk.filename == "manual.md"
        assert chunk.chunk_id.startswith("doc-123_c")


@pytest.mark.asyncio
async def test_rag_engine_prompt_building():
    engine = RAGEngine()
    dummy_chunk = DocumentChunk(
        chunk_id="doc1_c0",
        doc_id="doc1",
        filename="relatorio.pdf",
        chunk_index=0,
        page_number=2,
        content="O faturamento no Q3 foi de R$ 1.5 milhão.",
        char_count=40
    )
    
    sources = [(dummy_chunk, 0.88, 0.95)]
    prompt_context = engine._build_context_prompt(sources)
    
    assert "relatorio.pdf" in prompt_context
    assert "Página 2" in prompt_context
    assert "0.95" in prompt_context
    assert "R$ 1.5 milhão" in prompt_context


@pytest.mark.asyncio
async def test_rag_rerank_fallback():
    engine = RAGEngine()
    
    # Mock do llama_client
    engine.llama.get_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    engine.llama.rerank = AsyncMock(return_value=None)  # Simula Reranker offline
    engine.llama.stream_chat = AsyncMock()
    
    async def dummy_stream(msgs, temperature=0.3):
        yield "Resposta baseada no "
        yield "documento."
    
    engine.llama.stream_chat.side_effect = dummy_stream

    dummy_chunk = DocumentChunk(
        chunk_id="doc1_c0",
        doc_id="doc1",
        filename="nota.txt",
        chunk_index=0,
        page_number=1,
        content="Conteudo importante da nota.",
        char_count=28
    )

    # Mock do vector store
    engine.vectors.search_chunks = AsyncMock(return_value=[(dummy_chunk, 0.85)])

    request = ChatRequest(
        message="Qual o conteúdo da nota?",
        use_rerank=True
    )

    events = []
    async for event in engine.stream_rag_response(request):
        events.append(event)

    # Deve ter emitido sources, tokens e done sem quebrar
    joined_events = "".join(events)
    assert "event: sources" in joined_events
    assert "nota.txt" in joined_events
    assert "event: token" in joined_events
    assert "Resposta baseada no " in joined_events
    assert "event: done" in joined_events
