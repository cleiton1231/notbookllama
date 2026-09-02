# Project: DocMind Modular RAG Expansion (100% Offline)

## Architecture
DocMind is a 100% offline local RAG system composed of:
- **Backend**: FastAPI with SQLite persistence, ChromaDB vector store, Okapi BM25 indexer, hybrid RRF search, OCR fallback parser, RAG evaluator, and HTTP client for local `llama-server` instances (:8080 chat, :8081 embed, :8082 rerank).
- **Frontend**: React + Vite + TypeScript + Tailwind CSS with Session History sidebar, ChatMessage actions (regenerate & inline edit), and SSE streaming chat client.
- **Concurrency & Resource Model**: Zero GPU/VRAM contention during automated testing; deterministic mocks (`unittest.mock.AsyncMock`) are used in all test suites.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | SQLite Conversation Persistence | Store sessions, messages, and timestamps in SQLite database with CRUD APIs | M1 (R1) | ORIGINAL_REQUEST.md §R1 |
| 2 | Session History UI Component | Sidebar/drawer component to list, select, switch, and delete chat sessions | M1 (R1) | ORIGINAL_REQUEST.md §R1 |
| 3 | Regenerate & Edit API Endpoint | Router to re-execute questions or edited queries against RAG pipeline via SSE | M2 (R2) | ORIGINAL_REQUEST.md §R2 |
| 4 | Chat Message Actions UI | Inline question editing and message regeneration triggers on message turns | M2 (R2) | ORIGINAL_REQUEST.md §R2 |
| 5 | Okapi BM25 Lexical Search | Pure-Python Okapi BM25 indexing and lexical retrieval over document chunks | M3 (R3) | ORIGINAL_REQUEST.md §R3 |
| 6 | Hybrid Search & RRF Fusion | Reciprocal Rank Fusion ($k=60$) combining ChromaDB vector hits and BM25 hits | M3 (R3) | ORIGINAL_REQUEST.md §R3 |
| 7 | OCR Fallback Parser | Detect image-only/scanned PDFs and trigger OCR extraction with SHA-256 dedupe | M4 (R4) | ORIGINAL_REQUEST.md §R4 |
| 8 | RAG Deterministic Evaluator | Offline evaluation metrics: Lexical Faithfulness overlap, Chunk Recall, Precision | M5 (R5) | ORIGINAL_REQUEST.md §R5 |
| 9 | Evaluation API Endpoints | REST endpoints (`/api/eval/rag`) to benchmark retrieval and answer quality | M5 (R5) | ORIGINAL_REQUEST.md §R5 |
| 10 | Backend Shared Integration | Connect routers (`sessions`, `regenerate`, `eval`), R3 hybrid search, R4 OCR parser | M6 | ORIGINAL_REQUEST.md §Integração |
| 11 | Frontend Shared Integration | Connect `SessionHistory` in `Sidebar.tsx` and `ChatMessageActions` in `App.tsx` | M6 | ORIGINAL_REQUEST.md §Integração |
| 12 | Full Verification & Hardening | Complete test suite green (`pytest tests/ -v`), frontend build, security checks | M7 | ORIGINAL_REQUEST.md §Acceptance |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | R1: Conversation Persistence | `backend/app/services/chat_history.py`, `backend/app/routers/sessions.py`, `frontend/src/components/SessionHistory.tsx`, `backend/tests/test_chat_history.py` | None | DONE |
| M2 | R2: Regenerate & Edit | `backend/app/routers/regenerate.py`, `frontend/src/components/ChatMessageActions.tsx`, `backend/tests/test_regenerate.py` | None | DONE |
| M3 | R3: BM25 + Hybrid Search | `backend/app/services/bm25_search.py`, `backend/app/services/hybrid_search.py`, `backend/tests/test_hybrid_search.py` | None | DONE |
| M4 | R4: OCR Fallback Local | `backend/app/services/ocr_parser.py`, `backend/tests/test_ocr_parser.py` | None | DONE |
| M5 | R5: RAG Quality Evaluator | `backend/app/services/rag_evaluator.py`, `backend/app/routers/eval.py`, `backend/tests/test_rag_evaluator.py` | None | DONE |
| M6 | Serial Shared Integration | `backend/app/main.py`, `backend/app/services/rag_engine.py`, `backend/app/services/document_parser.py`, `frontend/src/App.tsx`, `frontend/src/components/Sidebar.tsx`, `frontend/src/components/ChatMessage.tsx` | M1, M2, M3, M4, M5 | DONE |
| M7 | Full Verification & Hardening | Full `pytest backend/tests/ -v`, `npm run build`, path traversal, zero /home/ paths, no secret leaks | M6 | DONE |

## Interface Contracts

### 1. R1: Conversation Persistence (`chat_history.py` & `sessions.py`)
- **Service (`backend/app/services/chat_history.py`)**:
  - `init_db(db_path: Optional[str] = None) -> None`: Initialize SQLite tables (`sessions`, `messages`).
  - `create_session(title: str = "Nova Conversa") -> Dict[str, Any]`: Returns `{"id": str, "title": str, "created_at": str, "updated_at": str}`.
  - `list_sessions() -> List[Dict[str, Any]]`: Returns list of sessions ordered by `updated_at DESC`.
  - `get_session(session_id: str) -> Optional[Dict[str, Any]]`: Returns session metadata + list of messages.
  - `add_message(session_id: str, role: str, content: str, sources: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]`: Appends message and updates session timestamp.
  - `delete_session(session_id: str) -> bool`: Deletes session and associated messages.
- **Router (`backend/app/routers/sessions.py`)**:
  - `router = APIRouter(prefix="/api/sessions", tags=["sessions"])`
  - `GET /api/sessions`: List all sessions.
  - `POST /api/sessions`: Create new session.
  - `GET /api/sessions/{session_id}`: Get session details and messages.
  - `DELETE /api/sessions/{session_id}`: Delete session.
  - `POST /api/sessions/{session_id}/messages`: Add message to session.
- **Frontend Component (`frontend/src/components/SessionHistory.tsx`)**:
  - Props: `interface SessionHistoryProps { currentSessionId: string | null; onSelectSession: (id: string) => void; onNewChat: () => void; refreshTrigger?: number; }`

### 2. R2: Regenerate & Edit (`regenerate.py` & `ChatMessageActions.tsx`)
- **Router (`backend/app/routers/regenerate.py`)**:
  - `router = APIRouter(prefix="/api/chat", tags=["chat"])`
  - `POST /api/chat/regenerate`: Accepts `{ "session_id"?: string, "message_id"?: string, "query"?: string, "use_rerank"?: bool, "doc_ids"?: list[str] }` and returns SSE stream identical to `/api/chat/stream`.
- **Frontend Component (`frontend/src/components/ChatMessageActions.tsx`)**:
  - Props: `interface ChatMessageActionsProps { messageIndex: number; role: 'user' | 'assistant'; content: string; isLast: boolean; isGenerating: boolean; onRegenerate?: () => void; onEdit?: (newContent: string) => void; }`

### 3. R3: BM25 + Hybrid Search (`bm25_search.py` & `hybrid_search.py`)
- **Service (`backend/app/services/bm25_search.py`)**:
  - `class BM25Search`: Pure-Python Okapi BM25 indexer.
  - `index_chunks(chunks: List[DocumentChunk]) -> None`: Index documents in memory / FTS.
  - `search(query: str, top_k: int = 10, doc_ids: Optional[List[str]] = None) -> List[Tuple[DocumentChunk, float]]`: Return ranked chunks with BM25 score.
- **Service (`backend/app/services/hybrid_search.py`)**:
  - `class HybridSearcher`: Combines ChromaDB vector search and BM25 search.
  - `search(query: str, query_embedding: List[float], top_k: int = 10, doc_ids: Optional[List[str]] = None, k_rrf: int = 60, alpha: float = 0.5) -> List[Tuple[DocumentChunk, float]]`: Combines scores via Reciprocal Rank Fusion ($Score = \sum \frac{1}{k + rank}$).
  - `hybrid_search_instance`: Singleton or factory helper for `rag_engine.py`.

### 4. R4: OCR Fallback (`ocr_parser.py`)
- **Service (`backend/app/services/ocr_parser.py`)**:
  - `extract_text_ocr(file_path: Path, min_chars_threshold: int = 50) -> Tuple[str, bool]`: Attempts OCR extraction when `pypdf` yields < `min_chars_threshold` text. Returns `(extracted_text, ocr_used_bool)`.
  - Preserves SHA-256 deduplication and sanitized filename rules.
  - Graceful fallback with diagnostic messages if host OCR tools are missing.

### 5. R5: RAG Quality Evaluator (`rag_evaluator.py` & `eval.py`)
- **Service (`backend/app/services/rag_evaluator.py`)**:
  - `calculate_chunk_recall(retrieved_chunk_ids: List[str], ground_truth_chunk_ids: List[str]) -> float`
  - `calculate_chunk_precision(retrieved_chunk_ids: List[str], ground_truth_chunk_ids: List[str]) -> float`
  - `calculate_lexical_faithfulness(answer: str, context_chunks: List[str]) -> float`: Deterministic token overlap / n-gram containment.
  - `evaluate_rag_turn(query: str, answer: str, context_chunks: List[str], retrieved_chunk_ids: List[str], ground_truth_chunk_ids: Optional[List[str]] = None) -> Dict[str, float]`
- **Router (`backend/app/routers/eval.py`)**:
  - `router = APIRouter(prefix="/api/eval", tags=["evaluation"])`
  - `POST /api/eval/rag`: Evaluate turn payload and return metrics JSON.

## Code Layout
- Exclusive Worker 1 (R1):
  - `backend/app/services/chat_history.py`
  - `backend/app/routers/sessions.py`
  - `frontend/src/components/SessionHistory.tsx`
  - `backend/tests/test_chat_history.py`
- Exclusive Worker 2 (R2):
  - `backend/app/routers/regenerate.py`
  - `frontend/src/components/ChatMessageActions.tsx`
  - `backend/tests/test_regenerate.py`
- Exclusive Worker 3 (R3):
  - `backend/app/services/bm25_search.py`
  - `backend/app/services/hybrid_search.py`
  - `backend/tests/test_hybrid_search.py`
- Exclusive Worker 4 (R4):
  - `backend/app/services/ocr_parser.py`
  - `backend/tests/test_ocr_parser.py`
- Exclusive Worker 5 (R5):
  - `backend/app/services/rag_evaluator.py`
  - `backend/app/routers/eval.py`
  - `backend/tests/test_rag_evaluator.py`
- Shared Files (Integration Worker in M6 ONLY):
  - `backend/app/main.py`
  - `backend/app/services/rag_engine.py`
  - `backend/app/services/document_parser.py`
  - `frontend/src/App.tsx`
  - `frontend/src/components/Sidebar.tsx`
  - `frontend/src/components/ChatMessage.tsx`
  - `frontend/src/types.ts`
  - `frontend/src/services/api.ts`
