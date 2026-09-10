# 🧠 DocMind — Local Second Brain & High-Precision RAG Workstation

> **Repository:** [`cleiton1231/notbookllama`](https://github.com/cleiton1231/notbookllama) · **Product name:** DocMind

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.2-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange.svg)](https://trychroma.com)
[![llama.cpp](https://img.shields.io/badge/llama.cpp-Engine-purple.svg)](https://github.com/ggerganov/llama.cpp)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**A private, 100% local "Second Brain" & RAG application powered by `llama.cpp` (`llama-server`), with hybrid BM25 + vector retrieval, cross-encoder reranking, conversation persistence, OCR fallback for scanned PDFs, real-time SSE streaming, and a modern React UI.**

</div>

---

## ✨ Features

- **🔒 100% Offline & Private:** No telemetry, no external cloud dependencies. Documents and chat history stay on your machine.
- **⚡ Hybrid Retrieval + Rerank Pipeline:**
  1. **Lexical recall:** Okapi BM25 over indexed chunks.
  2. **Semantic recall:** ChromaDB cosine similarity (Top-K retrieval pool).
  3. **Fusion:** Reciprocal Rank Fusion (RRF, `k=60`) merges both rankings.
  4. **Precision reranking:** Cross-encoder via `llama-server` `/v1/rerank` (Top-K rerank), with automatic fallback to fused scores if the reranker is offline.
  5. **Noise prune:** `MIN_RELEVANCE_SCORE` drops near-zero matches before prompting.
- **💬 Conversation Persistence:** SQLite sessions and messages, sidebar history, switch/resume/delete chats.
- **♻️ Regenerate & Inline Edit:** Re-run the last turn or an edited question through the same SSE RAG stream.
- **📄 Smart Document Ingestion:**
  - PDF, Markdown (`.md`), plain text (`.txt`), plus `.csv` / `.json`.
  - Page-number tracking for citation linking.
  - SHA-256 deduplication and path-traversal-safe filename sanitization.
  - **OCR fallback** for image-only / scanned PDFs via local `pdftoppm` + `tesseract` (optional system tools).
- **📊 Deterministic RAG Evaluator:** Lexical faithfulness, chunk recall/precision APIs — no LLM-as-judge.
- **🖥️ Local AI Studio UI:**
  - Health / latency indicators for chat, embed, and rerank endpoints.
  - Drag-and-drop upload, document multi-select, citation pills, source deep-inspect modal.
  - Session history tab, regenerate and inline edit actions on messages.

---

## 🏛️ Architecture Overview

```
                      ┌─────────────────────────────────┐
                      │    User / React 18 + Vite UI    │
                      └───────────────┬─────────────────┘
                                      │ (HTTP REST / SSE Stream)
                                      ▼
                      ┌─────────────────────────────────┐
                      │      FastAPI Backend Core       │
                      │  sessions · regenerate · eval   │
                      └───────┬───────────────┬─────────┘
                              │               │
            ┌─────────────────┴────┐     ┌────┴─────────────────┐
            │ Document Ingestion   │     │  Hybrid RAG Engine   │
            │ • SHA-256 Hash       │     │ • BM25 + Vector RRF  │
            │ • OCR fallback       │     │ • Cross-Reranking    │
            │ • Semantic Chunker   │     │ • SQLite chat hist.  │
            └─────────┬────────────┘     └────┬────────────┬────┘
                      │                       │            │
                      ▼                       ▼            ▼
             ┌────────────────┐     ┌───────────┐   ┌──────────────┐
             │    ChromaDB    │     │  Embed    │   │  Chat / LLM  │
             │  Vector Store  │     │ llama.cpp │   │  llama.cpp   │
             │ (SQLite Lock)  │     │  (:8081)  │   │   (:8080)    │
             └────────────────┘     └───────────┘   └──────────────┘
                                          │
                                    ┌─────┴─────┐
                                    │  Reranker │
                                    │ llama.cpp │
                                    │  (:8082)  │
                                    └───────────┘
```

---

## 📋 Prerequisites

- **Python:** 3.10 or higher
- **Node.js:** 18.x or higher (with `npm`)
- **llama.cpp:** Built with hardware acceleration (CUDA, ROCm, Vulkan, or Metal)
- **Local GGUF Models:**
  - 1× Chat / Instruction model (e.g. `Qwen3.5-9B-Instruct`, `Qwen2.5-7B-Instruct`, `Gemma-2-9B-IT`)
  - 1× Embedding model (e.g. `Qwen3-Embedding-0.6B`, `bge-m3`, `nomic-embed-text`)
  - 1× Reranker model (e.g. `Qwen3-Reranker-0.6B`, `bge-reranker-large`) — optional but recommended
- **OCR (optional, for scanned PDFs):**
  - `tesseract` (language packs as needed, e.g. `por` + `eng`)
  - `pdftoppm` from Poppler (`poppler-utils` on Debian/Ubuntu)

  If these tools are missing, text PDFs still work; scanned PDFs return a diagnostic notice instead of crashing.

---

## 🚀 Quickstart Guide

### 1. Launch `llama-server` Instances

Start each model in a separate terminal or background process:

```bash
# Terminal 1 — Chat / Generation Model (Port 8080)
llama-server \
  -m /path/to/models/chat-model-Q5_K_M.gguf \
  -c 8192 \
  -ngl 99 \
  --port 8080 \
  --host 127.0.0.1

# Terminal 2 — Embeddings Model (Port 8081)
llama-server \
  -m /path/to/models/embedding-model-Q8_0.gguf \
  --embedding \
  --pooling last \
  -c 4096 \
  -ngl 99 \
  --port 8081 \
  --host 127.0.0.1

# Terminal 3 — Reranker Model (Port 8082 - Optional)
llama-server \
  -m /path/to/models/reranker-model-Q8_0.gguf \
  --reranking \
  -c 4096 \
  -ngl 99 \
  --port 8082 \
  --host 127.0.0.1
```

---

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and adjust environment variables
cp .env.example .env

# Run FastAPI development server
uvicorn app.main:app --reload --port 8000
```

Interactive OpenAPI docs: `http://localhost:8000/docs`.

---

### 3. Frontend Setup

```bash
cd frontend

# Install packages
npm install

# Start development server
npm run dev
```

Open **`http://localhost:5173`**.

---

## ⚙️ Configuration (`.env`)

Copy `backend/.env.example` to `backend/.env` and adjust as needed.

| Variable | Default | Description |
| :--- | :--- | :--- |
| `LLAMA_CHAT_URL` | `http://127.0.0.1:8080` | Chat Completions endpoint |
| `LLAMA_EMBED_URL` | `http://127.0.0.1:8081` | Embeddings endpoint |
| `LLAMA_RERANK_URL` | `http://127.0.0.1:8082` | Reranking endpoint |
| `CHROMA_PERSIST_DIR` | `./data/chroma` | Persistent ChromaDB directory |
| `UPLOAD_DIR` | `./data/uploads` | Uploaded files directory |
| `CHUNK_SIZE` | `1000` | Target characters per chunk |
| `CHUNK_OVERLAP` | `100` | Overlap between consecutive chunks |
| `TOP_K_RETRIEVAL` | `24` | Candidate pool size before / during hybrid fusion |
| `TOP_K_RERANK` | `12` | Chunks kept after rerank for the LLM prompt |
| `MIN_RELEVANCE_SCORE` | `0.05` | Drop near-zero relevance sources |
| `MAX_CONTEXT_TOKENS` | `6000` | Prompt context token ceiling |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Comma-separated allowed origins |
| `MAX_UPLOAD_SIZE_MB` | `50` | Max upload size per document |

---

## 📡 API Reference

### Core

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Connectivity + latency of chat/embed/rerank; indexed counts |
| `GET` | `/api/documents` | List indexed documents |
| `POST` | `/api/documents/upload` | Upload & index (SHA-256 dedupe, optional OCR) |
| `DELETE` | `/api/documents/{doc_id}` | Delete document + vectors (+ BM25 sync) |
| `POST` | `/api/chat/stream` | Full hybrid RAG pipeline as SSE |

### Sessions (conversation persistence)

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/sessions` | List sessions (`updated_at` DESC) |
| `POST` | `/api/sessions` | Create session |
| `GET` | `/api/sessions/{session_id}` | Session + messages |
| `PUT` | `/api/sessions/{session_id}` | Update session metadata (e.g. title) |
| `DELETE` | `/api/sessions/{session_id}` | Delete session and messages |
| `POST` | `/api/sessions/{session_id}/messages` | Append a message |

### Regenerate

| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/chat/regenerate` | Re-run query (optional `session_id` / `message_id` / edited `query`) as SSE |

### Evaluation

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/eval/health` | Evaluator service health |
| `POST` | `/api/eval/rag` | Single-turn deterministic metrics |
| `POST` | `/api/eval/rag/batch` | Batch evaluation |

### SSE event contract (`/api/chat/stream` and `/api/chat/regenerate`)

- `event: sources` — JSON array of source references (similarity / rerank scores)
- `event: token` — incremental text delta
- `event: done` — generation finished
- `event: error` — sanitized error message

---

## 🧪 Testing

Backend unit/integration suite (mocks llama-server; no GPU contention):

```bash
cd backend
source venv/bin/activate
# From repo root you can also use: PYTHONPATH=backend pytest backend/tests/ -v
python3 -m pytest tests/ -v
```

Frontend production build:

```bash
cd frontend
npm run build
```

---

## 🛡️ Security & Privacy Notice

- **Zero Data Leakage:** Inference and storage stay on `127.0.0.1` / local disk.
- **Upload Hardening:** Filenames sanitized against path traversal; non-whitelisted extensions blocked.
- **Shielded Errors:** Stack traces and filesystem paths stay in server logs, not client responses.
- **Test Isolation:** Automated tests mock llama endpoints and guard sockets to ports `8080`/`8081`/`8082`.

---

## 🗺️ Roadmap notes

Implemented modular expansion (see `PROJECT.md`): conversation persistence, regenerate/edit, BM25+RRF hybrid search, OCR fallback, deterministic RAG evaluator.

Next polish focus (not yet shipped): mobile sidebar/drawer UX, upload OCR feedback in the UI, lightweight eval panel, richer markdown/code rendering.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
