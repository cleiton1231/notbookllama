import pytest
import os
import uuid
import json
from datetime import datetime, timezone
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.services.chat_history import (
    ChatHistoryService,
    init_db,
    create_session,
    list_sessions,
    get_session,
    add_message,
    delete_session,
    update_session_title,
    clear_all
)
from app.routers.sessions import router as sessions_router


@pytest.fixture
def temp_db(tmp_path):
    """Provides an isolated SQLite database path for each test."""
    db_file = str(tmp_path / "test_chat.db")
    init_db(db_file)
    return db_file


@pytest.fixture
def app_with_sessions(temp_db):
    """FastAPI app instance configured with the sessions router and test DB."""
    app = FastAPI(title="Test App")
    app.include_router(sessions_router)
    ChatHistoryService.set_default_db_path(temp_db)
    yield app
    ChatHistoryService.reset_default_db_path()


# ============================================================================
# Service Layer Unit Tests (backend/app/services/chat_history.py)
# ============================================================================

def test_init_db_creates_tables(temp_db):
    """Verify init_db initializes the database schema idempotently."""
    assert os.path.exists(temp_db)
    init_db(temp_db)
    init_db(temp_db)


def test_create_and_get_session(temp_db):
    """Verify creating a session and fetching its details."""
    session = create_session(title="Conversa de Teste", db_path=temp_db)
    assert session["id"] is not None
    assert session["title"] == "Conversa de Teste"
    assert "created_at" in session
    assert "updated_at" in session

    fetched = get_session(session["id"], db_path=temp_db)
    assert fetched is not None
    assert fetched["id"] == session["id"]
    assert fetched["title"] == "Conversa de Teste"
    assert fetched["messages"] == []


def test_create_session_default_title(temp_db):
    """Verify default session title is 'Nova Conversa'."""
    session = create_session(db_path=temp_db)
    assert session["title"] == "Nova Conversa"


def test_get_nonexistent_session_returns_none(temp_db):
    """Verify get_session returns None when session_id does not exist."""
    assert get_session("non-existent-id-123", db_path=temp_db) is None


def test_list_sessions_ordered_by_updated_at(temp_db):
    """Verify sessions are listed in descending order of updated_at."""
    s1 = create_session(title="Sessao 1", db_path=temp_db)
    s2 = create_session(title="Sessao 2", db_path=temp_db)
    s3 = create_session(title="Sessao 3", db_path=temp_db)

    # Adding a message to s1 should update its updated_at timestamp
    add_message(s1["id"], role="user", content="Mensagem para s1", db_path=temp_db)

    sessions = list_sessions(db_path=temp_db)
    assert len(sessions) == 3
    # s1 should now be first because it was most recently updated
    assert sessions[0]["id"] == s1["id"]


def test_add_message_with_sources(temp_db):
    """Verify adding messages to a session with metadata sources."""
    session = create_session(title="Chat com Fontes", db_path=temp_db)
    session_id = session["id"]

    sources_data = [
        {
            "doc_id": "doc-01",
            "filename": "relatorio.pdf",
            "chunk_index": 0,
            "page_number": 3,
            "snippet": "Informação relevante encontrada.",
            "score": 0.89,
            "rerank_score": 0.96
        }
    ]

    # Add user message
    msg_user = add_message(session_id, role="user", content="Qual o faturamento?", db_path=temp_db)
    assert msg_user["role"] == "user"
    assert msg_user["content"] == "Qual o faturamento?"
    assert msg_user["sources"] is None or msg_user["sources"] == []
    assert "id" in msg_user
    assert "created_at" in msg_user

    # Add assistant message with sources
    msg_assistant = add_message(
        session_id,
        role="assistant",
        content="O faturamento foi de 1.5M.",
        sources=sources_data,
        db_path=temp_db
    )
    assert msg_assistant["role"] == "assistant"
    assert msg_assistant["content"] == "O faturamento foi de 1.5M."
    assert len(msg_assistant["sources"]) == 1
    assert msg_assistant["sources"][0]["doc_id"] == "doc-01"
    assert msg_assistant["sources"][0]["rerank_score"] == 0.96

    # Verify session retrieval contains all messages in chronological order
    session_details = get_session(session_id, db_path=temp_db)
    assert session_details is not None
    assert len(session_details["messages"]) == 2
    assert session_details["messages"][0]["id"] == msg_user["id"]
    assert session_details["messages"][1]["id"] == msg_assistant["id"]
    assert session_details["messages"][1]["sources"] == sources_data


def test_add_message_to_nonexistent_session_raises_error(temp_db):
    """Verify add_message raises ValueError when adding to non-existent session."""
    with pytest.raises(ValueError, match="Session .* not found"):
        add_message("invalid-session-id", role="user", content="Ola", db_path=temp_db)


def test_delete_session_cascades_messages(temp_db):
    """Verify deleting a session removes the session and all associated messages."""
    session = create_session(title="Para Deletar", db_path=temp_db)
    session_id = session["id"]

    add_message(session_id, role="user", content="Mensagem 1", db_path=temp_db)
    add_message(session_id, role="assistant", content="Resposta 1", db_path=temp_db)

    # Delete existing session
    deleted = delete_session(session_id, db_path=temp_db)
    assert deleted is True

    # Session should no longer exist
    assert get_session(session_id, db_path=temp_db) is None

    # Deleting again should return False
    assert delete_session(session_id, db_path=temp_db) is False


def test_update_session_title(temp_db):
    """Verify updating session title."""
    session = create_session(title="Titulo Antigo", db_path=temp_db)
    session_id = session["id"]

    updated = update_session_title(session_id, "Novo Titulo Personalizado", db_path=temp_db)
    assert updated is not None
    assert updated["title"] == "Novo Titulo Personalizado"
    assert "created_at" in updated
    assert "updated_at" in updated

    fetched = get_session(session_id, db_path=temp_db)
    assert fetched["title"] == "Novo Titulo Personalizado"

    # Non-existent session update
    assert update_session_title("invalid-id", "Outro Titulo", db_path=temp_db) is None


def test_clear_all_sessions(temp_db):
    """Verify clear_all removes all data."""
    s1 = create_session(title="S1", db_path=temp_db)
    add_message(s1["id"], role="user", content="Hi", db_path=temp_db)
    assert len(list_sessions(db_path=temp_db)) == 1

    clear_all(db_path=temp_db)
    assert len(list_sessions(db_path=temp_db)) == 0
    assert get_session(s1["id"], db_path=temp_db) is None


def test_unicode_and_special_chars(temp_db):
    """Verify storing and retrieving special characters, emojis, and multiline markdown."""
    title = "🤖 Conversa Especial: Olá Mundo! Çãõ <script>"
    session = create_session(title=title, db_path=temp_db)
    
    content = "Aqui está um código:\n```python\nprint('Olá!')\n```\nEmojis: 🚀🔥🧠"
    msg = add_message(session["id"], role="user", content=content, db_path=temp_db)
    
    fetched = get_session(session["id"], db_path=temp_db)
    assert fetched["title"] == title
    assert fetched["messages"][0]["content"] == content


def test_auto_title_generation(temp_db):
    """Verify default titled session auto-updates title from first user message."""
    session = create_session(title="Nova Conversa", db_path=temp_db)
    assert session["title"] == "Nova Conversa"
    
    add_message(session["id"], role="user", content="Como configurar o ChromaDB no Linux?", db_path=temp_db)
    fetched = get_session(session["id"], db_path=temp_db)
    assert fetched["title"] == "Como configurar o ChromaDB no Linux?"


# ============================================================================
# API Router Integration Tests (backend/app/routers/sessions.py)
# ============================================================================

@pytest.mark.asyncio
async def test_api_list_sessions_empty(app_with_sessions):
    """GET /api/sessions returns empty list initially."""
    transport = ASGITransport(app=app_with_sessions)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/sessions")
        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.asyncio
async def test_api_create_and_get_session(app_with_sessions):
    """POST /api/sessions creates a new session and GET /api/sessions/{id} returns it."""
    transport = ASGITransport(app=app_with_sessions)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create
        create_res = await client.post("/api/sessions", json={"title": "Sessão API"})
        assert create_res.status_code in (200, 201)
        data = create_res.json()
        assert data["title"] == "Sessão API"
        session_id = data["id"]

        # Get details
        get_res = await client.get(f"/api/sessions/{session_id}")
        assert get_res.status_code == 200
        session_data = get_res.json()
        assert session_data["id"] == session_id
        assert session_data["title"] == "Sessão API"
        assert session_data["messages"] == []


@pytest.mark.asyncio
async def test_api_get_session_not_found(app_with_sessions):
    """GET /api/sessions/{id} returns 404 for unknown session."""
    transport = ASGITransport(app=app_with_sessions)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/sessions/unknown-id-404")
        assert res.status_code == 404
        assert "não encontrada" in res.json()["detail"].lower() or "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_add_message_and_retrieve(app_with_sessions):
    """POST /api/sessions/{id}/messages adds a message to the session."""
    transport = ASGITransport(app=app_with_sessions)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        create_res = await client.post("/api/sessions", json={"title": "Sessão com Mensagens"})
        session_id = create_res.json()["id"]

        # Add message
        msg_payload = {
            "role": "user",
            "content": "Olá, assistente!",
            "sources": None
        }
        msg_res = await client.post(f"/api/sessions/{session_id}/messages", json=msg_payload)
        assert msg_res.status_code in (200, 201)
        msg_data = msg_res.json()
        assert msg_data["role"] == "user"
        assert msg_data["content"] == "Olá, assistente!"

        # Add assistant response with sources
        assistant_payload = {
            "role": "assistant",
            "content": "Olá! Como posso ajudar?",
            "sources": [
                {
                    "doc_id": "doc-abc",
                    "filename": "manual.pdf",
                    "chunk_index": 1,
                    "page_number": 2,
                    "snippet": "Manual de instrução",
                    "score": 0.95
                }
            ]
        }
        asst_res = await client.post(f"/api/sessions/{session_id}/messages", json=assistant_payload)
        assert asst_res.status_code in (200, 201)

        # Retrieve session
        session_res = await client.get(f"/api/sessions/{session_id}")
        assert session_res.status_code == 200
        full_session = session_res.json()
        assert len(full_session["messages"]) == 2
        assert full_session["messages"][0]["content"] == "Olá, assistente!"
        assert full_session["messages"][1]["content"] == "Olá! Como posso ajudar?"
        assert full_session["messages"][1]["sources"][0]["doc_id"] == "doc-abc"


@pytest.mark.asyncio
async def test_api_add_message_not_found(app_with_sessions):
    """POST /api/sessions/{id}/messages returns 404 for non-existent session."""
    transport = ASGITransport(app=app_with_sessions)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/sessions/nonexistent/messages",
            json={"role": "user", "content": "Teste"}
        )
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_api_delete_session(app_with_sessions):
    """DELETE /api/sessions/{id} deletes the session."""
    transport = ASGITransport(app=app_with_sessions)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_res = await client.post("/api/sessions", json={"title": "Sessão a Excluir"})
        session_id = create_res.json()["id"]

        # Delete
        del_res = await client.delete(f"/api/sessions/{session_id}")
        assert del_res.status_code == 200
        assert del_res.json().get("deleted") is True

        # Confirm not found
        get_res = await client.get(f"/api/sessions/{session_id}")
        assert get_res.status_code == 404

        # Deleting again should return 404
        del_again = await client.delete(f"/api/sessions/{session_id}")
        assert del_again.status_code == 404


@pytest.mark.asyncio
async def test_api_update_session_title(app_with_sessions):
    """PATCH /api/sessions/{id} updates the session title."""
    transport = ASGITransport(app=app_with_sessions)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_res = await client.post("/api/sessions", json={"title": "Original"})
        session_id = create_res.json()["id"]

        patch_res = await client.patch(f"/api/sessions/{session_id}", json={"title": "Modificado"})
        assert patch_res.status_code == 200
        assert patch_res.json()["title"] == "Modificado"

        get_res = await client.get(f"/api/sessions/{session_id}")
        assert get_res.json()["title"] == "Modificado"

        patch_404 = await client.patch("/api/sessions/invalid-id", json={"title": "Novo"})
        assert patch_404.status_code == 404
