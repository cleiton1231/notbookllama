import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.chat_history import (
    create_session,
    list_sessions,
    get_session,
    add_message,
    delete_session,
    update_session_title
)

logger = logging.getLogger("docmind.routers.sessions")

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    title: Optional[str] = Field(default="Nova Conversa", description="Título da conversa")


class UpdateSessionRequest(BaseModel):
    title: str = Field(..., min_length=1, description="Novo título da conversa")


class MessageCreatePayload(BaseModel):
    role: str = Field(..., description="Papel da mensagem: user, assistant ou system")
    content: str = Field(..., description="Conteúdo textual da mensagem")
    sources: Optional[List[Dict[str, Any]]] = Field(default=None, description="Fontes/chunks referenciados")


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    sources: Optional[List[Dict[str, Any]]] = None
    created_at: str


class SessionSummaryResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class SessionDetailResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[MessageResponse] = Field(default_factory=list)


class DeleteSessionResponse(BaseModel):
    deleted: bool
    id: str


@router.get("", response_model=List[SessionSummaryResponse])
async def get_all_sessions():
    """Lista todas as sessões de chat em ordem decrescente de última atualização."""
    return list_sessions()


@router.post("", response_model=SessionSummaryResponse, status_code=status.HTTP_201_CREATED)
async def create_new_session(payload: Optional[CreateSessionRequest] = None):
    """Cria uma nova sessão de chat."""
    title = payload.title if payload and payload.title else "Nova Conversa"
    session = create_session(title=title)
    return session


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session_by_id(session_id: str):
    """Obtém detalhes e histórico completo de mensagens de uma sessão."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sessão '{session_id}' não encontrada."
        )
    return session


@router.delete("/{session_id}", response_model=DeleteSessionResponse)
async def delete_session_by_id(session_id: str):
    """Exclui uma sessão de chat e todas as suas mensagens associadas."""
    deleted = delete_session(session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sessão '{session_id}' não encontrada para exclusão."
        )
    return DeleteSessionResponse(deleted=True, id=session_id)


@router.patch("/{session_id}", response_model=SessionSummaryResponse)
@router.put("/{session_id}", response_model=SessionSummaryResponse)
async def update_session(session_id: str, payload: UpdateSessionRequest):
    """Atualiza o título de uma sessão de chat."""
    updated = update_session_title(session_id, payload.title)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sessão '{session_id}' não encontrada para atualização."
        )
    return updated


@router.post("/{session_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def add_message_to_session(session_id: str, payload: MessageCreatePayload):
    """Adiciona uma nova mensagem à sessão especificada."""
    try:
        msg = add_message(
            session_id=session_id,
            role=payload.role,
            content=payload.content,
            sources=payload.sources
        )
        return msg
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
