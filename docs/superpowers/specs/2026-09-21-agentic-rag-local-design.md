# Agentic RAG — Local AI System — Design Spec

Date: 2026-09-21
Source of truth: `README.md`

## 1. Scope

Full-stack MVP: FastAPI backend + Vue 3 frontend, agent orchestrator (LangChain)
dengan 3 tools (RAG, OCR, SQL), JWT auth + role-based authorization, Docker
Compose untuk Postgres+pgvector dan backend. Ollama berjalan di host (akses GPU).

Keputusan yang menyimpang / memperjelas README:

| Topik | Keputusan |
|---|---|
| Frontend framework | Vue 3 (bukan React) |
| Auth | JWT + role (ADMIN/USER/READ_ONLY) masuk MVP, bukan iterasi berikutnya |
| SQL Tool data | Tabel dummy `orders` (bukan data bisnis nyata) |
| LLM/embedding | `llama3` + `nomic-embed-text` (768 dim), via `.env` |
| Backend structure | Package-based (`app/api`, `app/agent`, `app/tools`, `app/services`, `app/models`, `app/core`) — bukan flat file di root `backend/` |
| Dev environment | Docker Compose untuk Postgres+pgvector & backend; Ollama di host |

## 2. Backend Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI app, router registration
│   ├── config.py               # Settings (pydantic-settings, reads .env)
│   ├── core/
│   │   ├── security.py         # JWT encode/decode, password hashing
│   │   └── deps.py             # FastAPI dependencies (get_current_user, require_role)
│   ├── api/
│   │   ├── auth.py             # POST /auth/login, /auth/register
│   │   ├── chat.py             # POST /chat, GET /chat/history
│   │   ├── documents.py        # POST /upload, POST /documents
│   │   └── health.py           # GET /health
│   ├── agent/
│   │   └── orchestrator.py     # LangChain agent, system prompt, tool binding
│   ├── tools/
│   │   ├── rag_tool.py
│   │   ├── ocr_tool.py
│   │   └── sql_tool.py
│   ├── services/
│   │   ├── embedding_service.py
│   │   ├── document_service.py
│   │   └── llm_service.py
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── chat_history.py
│   │   └── document.py
│   ├── schemas/                # Pydantic request/response schemas
│   └── database.py             # engine, session, Base
├── alembic/                    # migrations
├── requirements.txt
└── .env
```

frontend/ tetap seperti README section 6 (Vue templates alih-alih React).

## 3. Database Schema

Tambahan dari README section 7: tabel `users` untuk auth, dan tabel dummy `orders` untuk SQL Tool.

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'USER', -- ADMIN | USER | READ_ONLY
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat_history (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    user_id BIGINT REFERENCES users(id),
    role VARCHAR(20) NOT NULL, -- user | assistant | system | tool
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(768),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dummy business table for SQL Tool demo
CREATE TABLE orders (
    id BIGSERIAL PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    product VARCHAR(255) NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    order_date DATE NOT NULL
);
```

SQL Tool hanya boleh mengakses `orders` (allowlist), lewat DB user read-only
terpisah (`agent_readonly`), bukan user aplikasi utama.

## 4. Auth & Authorization

- JWT bearer token, expiry 60 menit, `python-jose` + `passlib[bcrypt]`.
- Endpoint: `POST /auth/register`, `POST /auth/login` → `{access_token}`.
- Role di JWT payload. `require_role(["ADMIN","USER"])` dependency untuk endpoint
  yang butuh restriction. `/chat`, `/upload` butuh role apa saja terautentikasi.
  READ_ONLY tidak boleh `/upload` atau `/documents` (POST).
- Password hashing bcrypt. Tidak ada refresh token di MVP — re-login setelah expiry.

## 5. Agent & Tools

Sesuai README section 8, 13, 14 — tidak berubah secara konsep:
- `rag_search(query)`: embed query via `nomic-embed-text`, similarity search pgvector, return top-k chunks.
- `image_ocr(image_path)`: PaddleOCR extract text.
- `sql_query(query)`: hanya SELECT, allowlist tabel `orders`, timeout 5s, parameterized, dijalankan via `agent_readonly` DB user.
- LangChain agent (tool-calling agent, bukan LangGraph) dengan system prompt seperti README section 14.
- Dokumen hasil RAG diberi label "untrusted context" dalam prompt (mitigasi prompt injection, README section 18).

## 6. API Contract (tambahan dari README section 20)

```
POST /auth/register   {username, password}              -> {id, username, role}
POST /auth/login       {username, password}              -> {access_token, token_type}
GET  /health                                              -> {status: "ok"}
POST /chat  (auth)     {session_id, message}              -> {answer, tool_used, sources}
POST /upload (auth)    multipart file                     -> {filename, status}
POST /documents (auth) {filename, content}                -> {id, status}
GET  /chat/history (auth) ?session_id=                    -> [{role, message, created_at}]
```

Semua endpoint kecuali `/health`, `/auth/*` butuh `Authorization: Bearer <token>`.

## 7. Frontend (Vue)

```
frontend/
├── src/
│   ├── components/
│   │   ├── ChatBox.vue
│   │   ├── UploadButton.vue
│   │   └── MessageBubble.vue
│   ├── services/api.js       # axios instance, attaches JWT
│   ├── stores/auth.js        # pinia store: token, user, login/logout
│   ├── views/LoginView.vue
│   ├── App.vue
│   └── main.js
├── package.json
└── vite.config.js
```

Fitur: login form → simpan token → chat UI dengan markdown render, source citation,
file upload, loading state, error handling. Sesuai README section 15.

## 8. Docker & Environment

Docker Compose (README section 22) + service tambahan tidak diperlukan — Ollama
tetap di host per keputusan awal. `.env` tambahan:

```env
JWT_SECRET_KEY=change-me
JWT_EXPIRE_MINUTES=60
SQL_AGENT_DB_URL=postgresql://agent_readonly:...@localhost:5432/agentic_rag
```

## 9. Development Phases (eksekusi)

Mengikuti README section 12–17 dengan tambahan auth di Fase 2:

1. **Fase 1 — Infra**: Docker Compose Postgres+pgvector, Ollama host, tabel `users/chat_history/documents/orders`, seed dummy orders.
2. **Fase 2 — Backend Core**: FastAPI skeleton, auth (JWT), RAG/OCR/SQL tools, services.
3. **Fase 3 — Agent**: LangChain orchestrator + system prompt + tool binding.
4. **Fase 4 — Frontend**: Vue init, login view, chat UI, upload, API integration.
5. **Fase 5 — Testing**: sesuai testing matrix README section 17 + tes auth (SEC-003: role restriction).

## 10. Out of Scope (MVP)

- Refresh token, password reset, multi-tenant.
- Hybrid search, reranking, streaming response, multi-agent (README section 25 — future).
- Antivirus/malware scanning file upload.
- Kubernetes deployment.
