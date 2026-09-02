import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.chat_history import ChatHistoryService, get_session, list_sessions
from app.services.bm25_search import bm25_search
from app.schemas import DocumentChunk, ChatRequest, EndpointStatus
from app.services.rag_engine import RAGEngine
from app.services.document_parser import parse_pdf, ParsedPage


@pytest.fixture
def temp_db(tmp_path):
    db_file = str(tmp_path / "test_integration_history.db")
    ChatHistoryService.set_default_db_path(db_file)
    ChatHistoryService.init_db()
    yield db_file
    ChatHistoryService.reset_default_db_path()


@pytest.fixture
def client(temp_db):
    return TestClient(app)


def test_all_routers_mounted(client):
    """Verifies that all modular routers (sessions, regenerate, eval) are mounted in main app."""
    # 1. Health endpoint (mocked to prevent live socket calls to llama-server ports)
    mock_health = {
        "chat": EndpointStatus(name="Llama Chat", url="http://127.0.0.1:8080", online=True, latency_ms=5, details="Operacional"),
        "embed": EndpointStatus(name="Llama Embeddings", url="http://127.0.0.1:8081", online=True, latency_ms=5, details="Operacional"),
        "rerank": EndpointStatus(name="Llama Reranker", url="http://127.0.0.1:8082", online=True, latency_ms=5, details="Operacional"),
    }
    with patch("app.main.llama_client.check_all_health", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_health
        res_health = client.get("/api/health")
        assert res_health.status_code == 200
        data = res_health.json()
        assert data["status"] == "healthy"
        assert data["chat_endpoint"]["online"] is True
        assert data["embed_endpoint"]["online"] is True
        assert data["rerank_endpoint"]["online"] is True
        mock_check.assert_called_once()

    # 2. Eval health endpoint
    res_eval_health = client.get("/api/eval/health")
    assert res_eval_health.status_code == 200
    assert res_eval_health.json()["status"] == "online"

    # 3. Sessions endpoint
    res_sessions = client.get("/api/sessions")
    assert res_sessions.status_code == 200
    assert isinstance(res_sessions.json(), list)

    # 4. Regenerate endpoint (empty payload returns 400 or 422)
    res_regen = client.post("/api/chat/regenerate", json={})
    assert res_regen.status_code in [400, 422]


def test_health_endpoint_degraded_when_any_model_offline(client):
    """Verifies that /api/health returns 'degraded' status when an endpoint is offline."""
    mock_health = {
        "chat": EndpointStatus(name="Llama Chat", url="http://127.0.0.1:8080", online=True, latency_ms=5, details="Operacional"),
        "embed": EndpointStatus(name="Llama Embeddings", url="http://127.0.0.1:8081", online=False, latency_ms=None, details="Offline"),
        "rerank": EndpointStatus(name="Llama Reranker", url="http://127.0.0.1:8082", online=False, latency_ms=None, details="Offline"),
    }
    with patch("app.main.llama_client.check_all_health", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_health
        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "degraded"
        assert data["chat_endpoint"]["online"] is True
        assert data["embed_endpoint"]["online"] is False
        assert data["rerank_endpoint"]["online"] is False



@pytest.mark.asyncio
async def test_rag_stream_session_persistence(temp_db):
    """Verifies that stream_rag_response automatically saves user and assistant messages when session_id is provided."""
    engine = RAGEngine()

    engine.llama.get_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    engine.llama.rerank = AsyncMock(return_value=None)

    async def mock_stream_chat(msgs, temperature=0.3):
        yield "Alocação dinâmica "
        yield "em C utiliza malloc."

    engine.llama.stream_chat = mock_stream_chat

    dummy_chunk = DocumentChunk(
        chunk_id="chunk_int_1",
        doc_id="doc_int_1",
        filename="ponteiros.pdf",
        chunk_index=0,
        page_number=3,
        content="malloc aloca memoria dinamicamente na heap.",
        char_count=45
    )

    engine.vectors.search_chunks = AsyncMock(return_value=[(dummy_chunk, 0.9)])

    session_id = "test-session-int-1"
    request = ChatRequest(
        message="Como funciona malloc em C?",
        session_id=session_id,
        use_rerank=False
    )

    events = []
    async for event in engine.stream_rag_response(request):
        events.append(event)

    joined = "".join(events)
    assert "event: sources" in joined
    assert "event: token" in joined
    assert "Alocação dinâmica " in joined
    assert "event: done" in joined

    # Verify database persistence
    session_data = get_session(session_id)
    assert session_data is not None
    assert len(session_data["messages"]) == 2
    user_msg = session_data["messages"][0]
    assistant_msg = session_data["messages"][1]

    assert user_msg["role"] == "user"
    assert user_msg["content"] == "Como funciona malloc em C?"

    assert assistant_msg["role"] == "assistant"
    assert "Alocação dinâmica em C utiliza malloc." in assistant_msg["content"]
    assert len(assistant_msg["sources"]) > 0
    assert assistant_msg["sources"][0]["filename"] == "ponteiros.pdf"


@pytest.mark.asyncio
async def test_rag_stream_empty_candidates_session_persistence(temp_db):
    """Verifies that empty retrieval results are persisted in session history gracefully."""
    engine = RAGEngine()
    engine.llama.get_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    engine.vectors.search_chunks = AsyncMock(return_value=[])

    session_id = "test-session-empty"
    request = ChatRequest(
        message="Pergunta sem nenhum documento correspondente",
        session_id=session_id
    )

    events = []
    async for event in engine.stream_rag_response(request):
        events.append(event)

    session_data = get_session(session_id)
    assert session_data is not None
    assert len(session_data["messages"]) == 2
    assert "Nenhum documento indexado" in session_data["messages"][1]["content"]


def test_bm25_sync_on_chunks_lifecycle():
    """Verifies that BM25 index correctly adds and removes document chunks."""
    bm25_search.clear()
    assert bm25_search.total_chunks == 0

    chunks = [
        DocumentChunk(
            chunk_id="c1",
            doc_id="doc_a",
            filename="intro.txt",
            chunk_index=0,
            content="Introdução ao processamento de linguagem natural.",
            char_count=50
        ),
        DocumentChunk(
            chunk_id="c2",
            doc_id="doc_b",
            filename="compiladores.txt",
            chunk_index=0,
            content="Análise sintática e semântica de compiladores.",
            char_count=48
        )
    ]

    bm25_search.add_chunks(chunks)
    assert bm25_search.total_chunks == 2

    # Search for "linguagem natural"
    results = bm25_search.search(query="linguagem natural", top_k=5)
    assert len(results) >= 1
    assert results[0][0].chunk_id == "c1"

    # Remove doc_a
    bm25_search.remove_document("doc_a")
    assert bm25_search.total_chunks == 1

    # Now searching for "linguagem natural" returns nothing for doc_a
    results_after = bm25_search.search(query="linguagem natural", top_k=5)
    assert not any(c[0].doc_id == "doc_a" for c in results_after)


def test_document_parser_pdf_ocr_integration():
    """Verifies that parse_pdf handles both readable PDFs and scanned PDFs via ocr fallback."""
    fake_pdf = b"%PDF-1.4 ... minimal pdf content"
    with patch("app.services.document_parser.extract_pdf_pages_ocr") as mock_ocr:
        mock_ocr.return_value = [
            {"page_number": 1, "text": "Texto extraido via OCR com sucesso", "ocr_used": True}
        ]
        pages = parse_pdf(fake_pdf, "scanned.pdf")
        assert len(pages) == 1
        assert pages[0].page_number == 1
        assert "Texto extraido via OCR" in pages[0].text
