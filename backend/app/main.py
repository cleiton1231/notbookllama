import uuid
import logging
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app.config import settings
from app.schemas import (
    DocumentResponse,
    DocumentListResponse,
    ChatRequest,
    HealthResponse,
    DocumentMetadata
)
from app.services.document_parser import parse_document
from app.services.chunker import create_document_chunks
from app.services.llama_client import llama_client
from app.services.vector_store import vector_store
from app.services.rag_engine import rag_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("docmind.main")

app = FastAPI(
    title="DocMind API",
    description="API do Segundo Cérebro & RAG Local com llama.cpp",
    version="1.0.0"
)

# CORS para desenvolvimento com Vite
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Verifica a saúde da API, dos modelos llama-server e contagem de itens."""
    endpoints_health = await llama_client.check_all_health()
    total_docs, total_chunks = await vector_store.get_counts()

    all_online = all(ep.online for ep in endpoints_health.values())
    overall_status = "healthy" if all_online else "degraded"

    return HealthResponse(
        status=overall_status,
        chat_endpoint=endpoints_health["chat"],
        embed_endpoint=endpoints_health["embed"],
        rerank_endpoint=endpoints_health["rerank"],
        total_indexed_documents=total_docs,
        total_indexed_chunks=total_chunks
    )


@app.get("/api/documents", response_model=DocumentListResponse)
async def list_documents():
    """Retorna todos os documentos indexados na base."""
    docs = await vector_store.list_documents()
    total_docs, total_chunks = await vector_store.get_counts()
    return DocumentListResponse(
        documents=docs,
        total_documents=total_docs,
        total_chunks=total_chunks
    )


@app.post("/api/documents/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Recebe um arquivo (PDF, TXT, MD), verifica desduplicação via SHA-256,
    fatia em chunks semânticos, gera embeddings e salva no ChromaDB.
    """
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado está vazio."
        )

    # 1. Parsing e extração
    parsed_doc = parse_document(content, file.filename)

    # 2. Desduplicação por SHA-256
    existing = await vector_store.get_document_by_sha256(parsed_doc.sha256)
    if existing:
        return DocumentResponse(
            message=f"Documento já indexado anteriormente (ID: {existing.doc_id})",
            document=existing
        )

    # 3. Chunking
    doc_id = str(uuid.uuid4())[:8]
    chunks = create_document_chunks(
        parsed_doc=parsed_doc,
        doc_id=doc_id,
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP
    )

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível extrair texto utilizável do documento."
        )

    # 4. Gerar Embeddings em batch via llama-server
    try:
        chunk_texts = [c.content for c in chunks]
        embeddings = await llama_client.get_embeddings(chunk_texts)
    except Exception as e:
        logger.error(f"Erro ao gerar embeddings para o arquivo {file.filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha ao conectar no endpoint de embeddings do llama-server ({settings.LLAMA_EMBED_URL}): {str(e)}"
        )

    # 5. Salvar no Vector Store
    doc_metadata = DocumentMetadata(
        doc_id=doc_id,
        filename=parsed_doc.filename,
        file_type=parsed_doc.file_type,
        file_size=parsed_doc.file_size,
        sha256=parsed_doc.sha256,
        total_chunks=len(chunks),
        total_pages=parsed_doc.total_pages
    )

    await vector_store.add_document(
        metadata=doc_metadata,
        chunks=chunks,
        embeddings=embeddings
    )

    return DocumentResponse(
        message=f"Documento '{parsed_doc.filename}' indexado com sucesso!",
        document=doc_metadata
    )


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Remove um documento e todos os seus vetores indexados."""
    success = await vector_store.delete_document(doc_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento com ID {doc_id} não encontrado."
        )
    return {"message": f"Documento {doc_id} removido com sucesso."}


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Endpoint de chat RAG com streaming via Server-Sent Events (SSE).
    Emite eventos tipados: sources, token, done, error.
    """
    return StreamingResponse(
        rag_engine.stream_rag_response(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
