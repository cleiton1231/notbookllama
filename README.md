# 🧠 DocMind — Local Second Brain & High-Precision RAG Workstation

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.2-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange.svg)](https://trychroma.com)
[![llama.cpp](https://img.shields.io/badge/llama.cpp-Engine-purple.svg)](https://github.com/ggerganov/llama.cpp)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**A private, 100% local "Second Brain" & RAG (Retrieval-Augmented Generation) application powered by `llama.cpp` (`llama-server`), featuring a 2-stage retrieval + cross-encoder reranker pipeline, persistent vector storage, real-time SSE token streaming, and an interactive modern UI.**

</div>

---

## ✨ Features

- **🔒 100% Offline & Private:** No telemetry, no external cloud dependencies. Your documents and conversation history never leave your machine.
- **⚡ Two-Stage RAG Pipeline:**
  1. **Broad Recall:** ChromaDB retrieves the Top-24 candidate chunks using semantic cosine similarity.
  2. **Precision Reranking:** A dedicated cross-encoder reranker (`/v1/rerank`) evaluates cross-attention to select the Top-12 most relevant passages.
  3. **Resilient Fallback:** Automatically falls back to pure vector similarity if the reranking service is offline.
- **📄 Smart Document Ingestion:**
  - Automated parsing for PDF, Markdown (`.md`), and Plain Text (`.txt`).
  - Page-number tracking for exact citation linking.
  - Cryptographic **SHA-256 deduplication** to avoid re-indexing identical files.
  - Safe filename sanitization protecting against Path Traversal.
- **💬 Real-Time SSE Token Streaming:**
  - Server-Sent Events with typed event contracts (`sources`, `token`, `done`, `error`).
  - Native client disconnect / `AbortController` cancellation support.
  - Reasoning effort disabled (`reasoning_effort: "none"`, `enable_thinking: false`) for fast, context-preserving answers.
- **🖥️ Local AI Studio Interface:**
  - Dynamic latency and health monitoring across all local endpoints (Chat, Embeddings, Reranker).
  - Drag-and-drop document upload with real-time feedback.
  - Interactive source citation pills with confidence breakdown.
  - Deep-inspection modal displaying original chunk text and similarity vs. rerank metrics.

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
                      └───────┬───────────────┬─────────┘
                              │               │
            ┌─────────────────┴────┐     ┌────┴─────────────────┐
            │ Document Ingestion   │     │  2-Stage RAG Engine  │
            │ • SHA-256 Hash       │     │ • Broad Retrieval    │
            │ • Semantic Chunker   │     │ • Cross-Reranking    │
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
  - 1x Chat / Instruction model (e.g. `Qwen3.5-9B-Instruct`, `Qwen2.5-7B-Instruct`, `Gemma-2-9B-IT`)
  - 1x Embedding model (e.g. `Qwen3-Embedding-0.6B`, `bge-m3`, `nomic-embed-text`)
  - 1x Reranker model (e.g. `Qwen3-Reranker-0.6B`, `bge-reranker-large`)

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

The interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

---

### 3. Frontend Setup

```bash
cd frontend

# Install packages
npm install

# Start development server
npm run dev
```

Open your browser at **`http://localhost:5173`**.

---

## ⚙️ Configuration (`.env`)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `LLAMA_CHAT_URL` | `http://127.0.0.1:8080` | URL for the `llama-server` Chat Completions endpoint |
| `LLAMA_EMBED_URL` | `http://127.0.0.1:8081` | URL for the `llama-server` Embeddings endpoint |
| `LLAMA_RERANK_URL` | `http://127.0.0.1:8082` | URL for the `llama-server` Reranking endpoint |
| `CHROMA_PERSIST_DIR` | `./data/chroma` | Local directory for persistent ChromaDB vectors |
| `UPLOAD_DIR` | `./data/uploads` | Local directory for uploaded files |
| `CHUNK_SIZE` | `1000` | Target character size per chunk |
| `CHUNK_OVERLAP` | `100` | Overlap character count between consecutive chunks |
| `TOP_K_RETRIEVAL` | `24` | Candidate chunks retrieved from ChromaDB in Stage 1 |
| `TOP_K_RERANK` | `12` | Filtered chunks passed to the LLM prompt in Stage 2 |
| `MAX_CONTEXT_TOKENS` | `6000` | Maximum token ceiling for prompt context |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Allowed CORS origins for the API |
| `MAX_UPLOAD_SIZE_MB`| `50` | Maximum upload size per document |

---

## 📡 API Reference

### `GET /api/health`
Checks the live connectivity and latency of all three `llama-server` endpoints and returns indexed counts.

### `GET /api/documents`
Lists all indexed documents with metadata (ID, filename, file size, chunk count, pages, hash).

### `POST /api/documents/upload`
Uploads and indexes a new document (PDF, Markdown, TXT) with SHA-256 deduplication and sanitized filenames.

### `DELETE /api/documents/{doc_id}`
Deletes a document and clears all corresponding vector embeddings from ChromaDB.

### `POST /api/chat/stream`
Executes the full 2-stage RAG pipeline and returns a Server-Sent Events (SSE) stream:
- `event: sources` — JSON array of `SourceReference` with similarity and rerank scores.
- `event: token` — Incremental text token delta generated by the LLM.
- `event: done` — Signals completion of generation.
- `event: error` — Emits sanitized error messages.

---

## 🧪 Testing

Run backend automated unit tests:

```bash
cd backend
python3 -m pytest tests/test_rag.py -v
```

Build and validate the frontend:

```bash
cd frontend
npm run build
```

---

## 🛡️ Security & Privacy Notice

- **Zero Data Leakage:** All computation, vector transformations, and inferences run on `127.0.0.1`.
- **Upload Hardening:** Filenames are sanitized against path traversal attacks (`..`, null bytes, control characters), and non-whitelisted extensions are blocked.
- **Shielded Error Handling:** Internal stack traces and file system hierarchies are kept on the server logs and never exposed in client API responses.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
