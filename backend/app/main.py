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

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa banco SQLite de histórico e recursos na inicialização da aplicação."""
    try:
        from app.services.chat_history import init_db
        init_db()
    except Exception as e:
        logger.warning(f"Erro ao inicializar DB de histórico de chat: {e}")
    yield


app = FastAPI(
    title="DocMind API",
    description="API do Segundo Cérebro & RAG Local com llama.cpp",
    version="1.0.0",
    lifespan=lifespan
)

# Configuração segura de CORS
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
if not origins:
    origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Importar e registrar roteadores modulares
from app.routers.sessions import router as sessions_router
from app.routers.regenerate import router as regenerate_router
from app.routers.eval import router as eval_router

app.include_router(sessions_router)
app.include_router(regenerate_router)
app.include_router(eval_router)


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
    Recebe um arquivo (PDF, TXT, MD), sanitiza nome/extensão, verifica desduplicação via SHA-256,
    fatia em chunks semânticos de forma não-bloqueante, gera embeddings e salva no ChromaDB.
    """
    # 1. Validação de Extensão
    raw_filename = file.filename or "document.txt"
    ext = Path(raw_filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Extensão '{ext}' não suportada. Extensões permitidas: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # 2. Leitura com Limite de Tamanho
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await file.read()
    if not content or len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado está vazio."
        )

    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Tamanho do arquivo excede o limite máximo permitido de {settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    # 3. Sanitização do Nome do Arquivo
    from app.services.document_parser import sanitize_filename
    safe_filename = sanitize_filename(raw_filename)

    # 4. Parsing e Extração Não-Bloqueante (executa em worker thread)
    try:
        parsed_doc = await asyncio.to_thread(parse_document, content, safe_filename)
    except Exception as e:
        logger.error(f"Erro ao processar documento {safe_filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Falha ao extrair texto do documento fornecido."
        )

    # 5. Desduplicação por SHA-256
    existing = await vector_store.get_document_by_sha256(parsed_doc.sha256)
    if existing:
        return DocumentResponse(
            message=f"Documento já indexado anteriormente (ID: {existing.doc_id})",
            document=existing
        )

    # 6. Chunking Não-Bloqueante
    doc_id = str(uuid.uuid4())[:8]
    try:
        chunks = await asyncio.to_thread(
            create_document_chunks,
            parsed_doc,
            doc_id,
            settings.CHUNK_SIZE,
            settings.CHUNK_OVERLAP
        )
    except Exception as e:
        logger.error(f"Erro no chunking do documento {safe_filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao fatiar o documento em chunks."
        )

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível extrair texto utilizável do documento."
        )

    # 7. Gerar Embeddings via llama-server
    try:
        chunk_texts = [c.content for c in chunks]
        embeddings = await llama_client.get_embeddings(chunk_texts)
    except Exception as e:
        logger.error(f"Erro ao gerar embeddings para o arquivo {safe_filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha ao conectar no endpoint de embeddings do llama-server ({settings.LLAMA_EMBED_URL}). Verifique se o servidor de embedding está ativo."
        )

    # 8. Salvar no Vector Store
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

    # 9. Sincronizar índice lexical BM25
    try:
        from app.services.bm25_search import bm25_search
        bm25_search.add_chunks(chunks)
    except Exception as e:
        logger.warning(f"Erro ao sincronizar BM25 no upload: {e}")

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

    # Sincronizar remoção no índice lexical BM25
    try:
        from app.services.bm25_search import bm25_search
        bm25_search.remove_document(doc_id)
    except Exception as e:
        logger.warning(f"Erro ao remover documento do BM25: {e}")

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
