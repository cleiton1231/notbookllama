from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class DocumentMetadata(BaseModel):
    doc_id: str
    filename: str
    file_type: str
    file_size: int
    sha256: str
    total_chunks: int
    total_pages: Optional[int] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class DocumentChunk(BaseModel):
    chunk_id: str
    doc_id: str
    filename: str
    chunk_index: int
    page_number: Optional[int] = None
    content: str
    char_count: int


class DocumentResponse(BaseModel):
    message: str
    document: DocumentMetadata


class DocumentListResponse(BaseModel):
    documents: List[DocumentMetadata]
    total_documents: int
    total_chunks: int


class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = Field(default_factory=list)
    doc_ids: Optional[List[str]] = None  # None significa pesquisar em todos os documentos
    temperature: float = 0.3
    use_rerank: bool = True
    top_k: Optional[int] = None


class SourceReference(BaseModel):
    doc_id: str
    filename: str
    chunk_index: int
    page_number: Optional[int] = None
    snippet: str
    score: Optional[float] = None
    rerank_score: Optional[float] = None


class EndpointStatus(BaseModel):
    name: str
    url: str
    online: bool
    details: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    chat_endpoint: EndpointStatus
    embed_endpoint: EndpointStatus
    rerank_endpoint: EndpointStatus
    total_indexed_documents: int
    total_indexed_chunks: int
