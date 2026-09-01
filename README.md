# 🧠 DocMind — Segundo Cérebro & RAG Local com llama.cpp

DocMind é uma aplicação 100% local e privada de gerenciamento de conhecimento e busca inteligente sobre documentos (PDF, Markdown, TXT) utilizando arquitetura **RAG de 2 Estágios** (Busca Vetorial no ChromaDB + Reranking de Alta Precisão) e inferência via `llama-server` (`llama.cpp`).

---

## 🌟 Principais Recursos

- **🔒 100% Local & Privado:** Nenhum dado sai da sua máquina. Funciona totalmente offline.
- **⚡ RAG de 2 Estágios:**
  1. *Recall Amplo:* ChromaDB recupera os Top-12 chunks por similaridade de cosseno.
  2. *Precisão Cirúrgica:* O Reranker (`/v1/rerank`) seleciona e reordena os Top-4 chunks mais relevantes para o prompt final.
  3. *Fallback Automático:* Caso o servidor de rerank esteja offline, o sistema faz fallback gracioso para similaridade vetorial sem quebrar o fluxo.
- **📄 Ingestão Inteligente:** Suporte a PDFs com extração por página, Markdown e TXT com desduplicação automática por hash **SHA-256**.
- **💬 Streaming SSE:** Respostas em tempo real com eventos tipados (`sources`, `token`, `done`, `error`) e suporte a cancelamento imediato (`AbortController`).
- **🎯 Citações & Fontes:** Chips interativos no chat que abrem o modal de inspeção do trecho exato do documento com score de relevância.
- **📊 Monitor de Status:** Painel em tempo real verificando a saúde dos endpoints de Chat, Embedding e Reranker.

---

## 🏗️ Estrutura do Projeto

```
docmind/
├── backend/
│   ├── app/
│   │   ├── config.py              # Configurações de portas e hiperparâmetros RAG
│   │   ├── schemas.py             # Schemas Pydantic para a API
│   │   ├── main.py                # Rotas FastAPI e streaming SSE
│   │   └── services/
│   │       ├── document_parser.py # Leitor de PDF/TXT com SHA-256
│   │       ├── chunker.py         # Splitter semântico com overlap
│   │       ├── llama_client.py    # Cliente HTTP assíncrono para llama-server
│   │       ├── vector_store.py    # ChromaDB com lock thread-safe
│   │       └── rag_engine.py      # Orquestrador RAG (Recall + Rerank + Prompt)
│   ├── data/                      # Dados locais (chroma/ e uploads/)
│   ├── tests/
│   │   └── test_rag.py            # Testes unitários com mocks
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/            # Sidebar, FileUpload, ChatMessage, SourceModal, StatusIndicator
│   │   ├── services/              # Cliente API com suporte a SSE
│   │   ├── types.ts               # Tipos TypeScript
│   │   ├── App.tsx                # Interface principal
│   │   └── index.css              # Tailwind & tipografia
│   ├── package.json
│   └── vite.config.ts             # Proxy reverso para o backend
└── README.md
```

---

## 🚀 Como Executar

### 1. Inicializar os servidores do `llama-server`

Abra terminais dedicados para cada modelo:

```bash
# 1. Embeddings (Qwen3-Embedding-0.6B) — Porta 8081
llama-server \
  -m /home/cleiton/local/models/qwen3-embedding-0.6b-q8/Qwen3-Embedding-0.6B-Q8_0.gguf \
  --embedding \
  --pooling last \
  -c 4096 \
  -ngl 99 \
  --port 8081 \
  --host 127.0.0.1

# 2. Reranker (Qwen3-Reranker-0.6B) — Porta 8082
llama-server \
  -m /home/cleiton/local/models/qwen3-reranker-0.6b-q8/qwen3-reranker-0.6b-q8_0.gguf \
  --reranking \
  -c 4096 \
  -ngl 99 \
  --port 8082 \
  --host 127.0.0.1

# 3. Modelo de Chat / Geração (ex: Qwen3.5-9B) — Porta 8080
llama-server \
  -m /home/cleiton/local/models/qwen3.5-9b/Qwen3.5-9B-Q5_K_M.gguf \
  -c 8192 \
  -ngl 99 \
  --port 8080 \
  --host 127.0.0.1
```

> **Nota:** Se você não iniciar o Reranker na porta 8082 ou o Chat na 8080 temporariamente, o DocMind possui fallback e monitoramento visual de status no topo da tela.

---

### 2. Inicializar o Backend (FastAPI)

```bash
cd backend

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Iniciar servidor
uvicorn app.main:app --reload --port 8000
```

Documentação interativa do Swagger disponível em: `http://localhost:8000/docs`

---

### 3. Inicializar o Frontend (React + Vite)

```bash
cd frontend

# Instalar dependências
npm install

# Iniciar ambiente de desenvolvimento
npm run dev
```

Acesse a interface no navegador em: `http://localhost:5173`

---

## 🧪 Rodando os Testes Automatizados

Para executar os testes do backend:

```bash
cd backend
pytest tests/test_rag.py -v
```
