import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.regenerate import router, RegenerateRequest
from app.schemas import ChatRequest, ChatMessage


@pytest.fixture
def app():
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_regenerate_request_schema():
    # Test query-based payload
    req1 = RegenerateRequest(query="Qual a diferença entre malloc e calloc?", use_rerank=True)
    assert req1.query == "Qual a diferença entre malloc e calloc?"
    assert req1.message is None
    assert req1.use_rerank is True
    assert req1.history == []

    # Test message-based payload
    req2 = RegenerateRequest(
        message="Explique ponteiros",
        history=[ChatMessage(role="user", content="oi"), ChatMessage(role="assistant", content="olá")],
        doc_ids=["doc_123"],
        temperature=0.7,
        top_k=5,
        session_id="sess_1",
        message_id="msg_1"
    )
    assert req2.message == "Explique ponteiros"
    assert len(req2.history) == 2
    assert req2.doc_ids == ["doc_123"]
    assert req2.temperature == 0.7
    assert req2.top_k == 5
    assert req2.session_id == "sess_1"
    assert req2.message_id == "msg_1"


def test_regenerate_endpoint_with_query(client):
    captured_request = None

    async def mock_stream_rag(req: ChatRequest):
        nonlocal captured_request
        captured_request = req
        yield "event: sources\ndata: " + json.dumps({"sources": []}) + "\n\n"
        yield "event: token\ndata: " + json.dumps({"token": "Resposta regenerada com sucesso."}) + "\n\n"
        yield "event: done\ndata: {}\n\n"

    with patch("app.routers.regenerate.rag_engine.stream_rag_response", side_effect=mock_stream_rag):
        payload = {
            "query": "Explique alocação dinâmica",
            "doc_ids": ["doc_abc"],
            "use_rerank": True,
            "temperature": 0.2
        }
        response = client.post("/api/chat/regenerate", json=payload)
        
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        assert response.headers.get("cache-control") == "no-cache"
        assert response.headers.get("x-accel-buffering") == "no"
        
        body = response.text
        assert "event: sources" in body
        assert "event: token" in body
        assert "Resposta regenerada com sucesso." in body
        assert "event: done" in body

        assert captured_request is not None
        assert captured_request.message == "Explique alocação dinâmica"
        assert captured_request.doc_ids == ["doc_abc"]
        assert captured_request.use_rerank is True
        assert captured_request.temperature == 0.2


def test_regenerate_endpoint_with_message_and_history(client):
    captured_request = None

    async def mock_stream_rag(req: ChatRequest):
        nonlocal captured_request
        captured_request = req
        yield "event: token\ndata: " + json.dumps({"token": "Token 1"}) + "\n\n"
        yield "event: done\ndata: {}\n\n"

    with patch("app.routers.regenerate.rag_engine.stream_rag_response", side_effect=mock_stream_rag):
        payload = {
            "message": "Pergunta editada pelo usuário",
            "history": [
                {"role": "user", "content": "Primeira pergunta"},
                {"role": "assistant", "content": "Primeira resposta"}
            ],
            "top_k": 3
        }
        response = client.post("/api/chat/regenerate", json=payload)
        
        assert response.status_code == 200
        body = response.text
        assert "Token 1" in body
        assert "event: done" in body

        assert captured_request is not None
        assert captured_request.message == "Pergunta editada pelo usuário"
        assert len(captured_request.history) == 2
        assert captured_request.history[0].role == "user"
        assert captured_request.top_k == 3


def test_regenerate_endpoint_empty_query_and_message(client):
    # Missing both query and message
    payload = {
        "temperature": 0.3
    }
    response = client.post("/api/chat/regenerate", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "obrigatório" in data["detail"]


def test_regenerate_endpoint_whitespace_only(client):
    payload = {
        "query": "   \n\t  "
    }
    response = client.post("/api/chat/regenerate", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


def test_regenerate_endpoint_error_event_propagation(client):
    async def mock_stream_error(req: ChatRequest):
        yield "event: error\ndata: " + json.dumps({"error": "Erro simulado no llama-server"}) + "\n\n"

    with patch("app.routers.regenerate.rag_engine.stream_rag_response", side_effect=mock_stream_error):
        payload = {
            "query": "Pergunta que causa erro interno"
        }
        response = client.post("/api/chat/regenerate", json=payload)
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        body = response.text
        assert "event: error" in body
        assert "Erro simulado no llama-server" in body


def test_router_configuration():
    assert router.prefix == "/api/chat"
    assert "chat" in router.tags
    routes = [route.path for route in router.routes]
    assert "/api/chat/regenerate" in routes
