import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.schemas import ChatMessage, ChatRequest
from app.services.rag_engine import rag_engine

logger = logging.getLogger("docmind.routers.regenerate")

router = APIRouter(prefix="/api/chat", tags=["chat"])


class RegenerateRequest(BaseModel):
    """
    Payload para regeneração de resposta ou reenvio de pergunta editada.
    Aceita 'query' ou 'message', histórico prévio, e configurações de RAG.
    """
    message: Optional[str] = None
    query: Optional[str] = None
    history: List[ChatMessage] = Field(default_factory=list)
    doc_ids: Optional[List[str]] = None
    temperature: float = 0.3
    use_rerank: bool = True
    top_k: Optional[int] = None
    session_id: Optional[str] = None
    message_id: Optional[str] = None


@router.post("/regenerate")
async def regenerate_chat_stream(request: RegenerateRequest):
    """
    Endpoint para regenerar a resposta de uma mensagem ou re-executar uma pergunta editada.
    Streams SSE identical to /api/chat/stream.
    """
    user_query = request.query or request.message
    if not user_query or not user_query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campo 'message' ou 'query' é obrigatório e não pode ser vazio para regeneração."
        )

    chat_request = ChatRequest(
        message=user_query.strip(),
        history=request.history,
        doc_ids=request.doc_ids,
        temperature=request.temperature,
        use_rerank=request.use_rerank,
        top_k=request.top_k
    )

    logger.info(
        f"Regenerando resposta para query (len={len(chat_request.message)}), "
        f"session_id={request.session_id}, message_id={request.message_id}, "
        f"use_rerank={request.use_rerank}"
    )

    return StreamingResponse(
        rag_engine.stream_rag_response(chat_request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
