import asyncio
import json
import logging
from typing import List, Optional, Tuple, Dict, Any

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
except ImportError:
    chromadb = None
    ChromaSettings = None

from app.config import settings
from app.schemas import DocumentChunk, DocumentMetadata

logger = logging.getLogger("docmind.vector_store")


class VectorStore:
    _instance: Optional["VectorStore"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        if chromadb is None:
            logger.warning("ChromaDB não está instalado no ambiente Python atual. Instale com pip install chromadb.")
            self.client = None
            self.chunk_collection = None
            self.doc_collection = None
            return

        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False, is_persistent=True)
        )
        # Coleção principal de chunks
        self.chunk_collection = self.client.get_or_create_collection(
            name="document_chunks",
            metadata={"hnsw:space": "cosine"}
        )
        # Coleção para metadados de documentos e verificação de SHA-256
        self.doc_collection = self.client.get_or_create_collection(
            name="document_metadata"
        )

    @classmethod
    def get_instance(cls) -> "VectorStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def get_document_by_sha256(self, sha256_hash: str) -> Optional[DocumentMetadata]:
        """Verifica se um documento já foi indexado usando hash SHA-256."""
        async with self._lock:
            try:
                results = self.doc_collection.get(
                    where={"sha256": sha256_hash},
                    limit=1
                )
                if results and results["ids"]:
                    meta = results["metadatas"][0]
                    return DocumentMetadata(**meta)
            except Exception as e:
                logger.error(f"Erro ao buscar documento por hash: {e}")
        return None

    async def add_document(
        self,
        metadata: DocumentMetadata,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]]
    ) -> None:
        """Salva metadados do documento e chunks com seus respectivos vetores."""
        if not chunks or not embeddings:
            return

        async with self._lock:
            # 1. Registrar metadados do documento
            doc_dict = metadata.model_dump()
            self.doc_collection.upsert(
                ids=[metadata.doc_id],
                metadatas=[doc_dict],
                documents=[metadata.filename]
            )

            # 2. Inserir chunks em lotes
            ids = [chunk.chunk_id for chunk in chunks]
            documents = [chunk.content for chunk in chunks]
            metadatas = [
                {
                    "doc_id": chunk.doc_id,
                    "filename": chunk.filename,
                    "chunk_index": chunk.chunk_index,
                    "page_number": chunk.page_number if chunk.page_number is not None else -1,
                    "char_count": chunk.char_count
                }
                for chunk in chunks
            ]

            self.chunk_collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )

    async def search_chunks(
        self,
        query_embedding: List[float],
        top_k: int = 12,
        doc_ids: Optional[List[str]] = None
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Realiza busca vetorial por similaridade de cosseno.
        Retorna tuplas (DocumentChunk, score_de_similaridade).
        """
        async with self._lock:
            where_filter = None
            if doc_ids and len(doc_ids) == 1:
                where_filter = {"doc_id": doc_ids[0]}
            elif doc_ids and len(doc_ids) > 1:
                where_filter = {"doc_id": {"$in": doc_ids}}

            results = self.chunk_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )

            matched_chunks: List[Tuple[DocumentChunk, float]] = []
            if results and results["ids"] and len(results["ids"][0]) > 0:
                ids = results["ids"][0]
                docs = results["documents"][0]
                metas = results["metadatas"][0]
                distances = results["distances"][0]

                for chunk_id, content, meta, dist in zip(ids, docs, metas, distances):
                    # Chroma com cosine retorna distância = 1 - similaridade
                    similarity = max(0.0, 1.0 - float(dist))
                    page_num = meta.get("page_number")
                    if page_num == -1:
                        page_num = None
                    
                    chunk = DocumentChunk(
                        chunk_id=chunk_id,
                        doc_id=meta.get("doc_id", ""),
                        filename=meta.get("filename", ""),
                        chunk_index=meta.get("chunk_index", 0),
                        page_number=page_num,
                        content=content,
                        char_count=meta.get("char_count", len(content))
                    )
                    matched_chunks.append((chunk, similarity))

            return matched_chunks

    async def list_documents(self) -> List[DocumentMetadata]:
        """Retorna todos os documentos indexados."""
        async with self._lock:
            try:
                results = self.doc_collection.get()
                docs = []
                if results and results["metadatas"]:
                    for meta in results["metadatas"]:
                        docs.append(DocumentMetadata(**meta))
                return docs
            except Exception as e:
                logger.error(f"Erro ao listar documentos: {e}")
                return []

    async def delete_document(self, doc_id: str) -> bool:
        """Exclui documento e todos os seus chunks associados."""
        async with self._lock:
            try:
                # Deletar chunks associados
                self.chunk_collection.delete(where={"doc_id": doc_id})
                # Deletar registro de metadados
                self.doc_collection.delete(ids=[doc_id])
                return True
            except Exception as e:
                logger.error(f"Erro ao excluir documento {doc_id}: {e}")
                return False

    async def get_counts(self) -> Tuple[int, int]:
        """Retorna (total_documentos, total_chunks)."""
        async with self._lock:
            total_docs = self.doc_collection.count()
            total_chunks = self.chunk_collection.count()
            return total_docs, total_chunks


vector_store = VectorStore.get_instance()
