# Fase 1 — Infra & Database Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Docker Compose environment dengan PostgreSQL+pgvector berjalan, schema database (users, chat_history, documents, orders) dibuat dengan Alembic, dan DB user read-only untuk SQL Agent tersedia.

**Architecture:** Single `docker-compose.yml` menjalankan container `postgres` (image `pgvector/pgvector:pg16`). Backend belum di-dockerize di fase ini (menyusul Fase 2) — hanya butuh koneksi DB untuk menjalankan migrasi Alembic dari host/venv. Ollama diinstall & dijalankan di host machine (bukan container), model `llama3` dan `nomic-embed-text` di-pull.

**Tech Stack:** Docker Compose, PostgreSQL 16 + pgvector extension, Alembic (migrations), Python 3.10+, Ollama (host).

**Spec:** `docs/superpowers/specs/2026-09-21-agentic-rag-local-design.md` (section 3, 8, 12)

## Global Constraints

- Database: PostgreSQL + pgvector, embedding dimension VECTOR(768) (nomic-embed-text).
- SQL Tool hanya boleh akses tabel `orders`, via DB user read-only terpisah (`agent_readonly`), bukan user aplikasi utama.
- `.env` tidak boleh masuk Git.
- Python 3.10+.

---

### Task 1: Docker Compose — PostgreSQL + pgvector

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.gitignore`

**Interfaces:**
- Produces: Postgres reachable at `localhost:5432`, database `agentic_rag`, user `postgres` / password from `.env`.

- [ ] **Step 1: Write `docker-compose.yml`**

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: agentic-rag-db
    environment:
      POSTGRES_DB: agentic_rag
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

- [ ] **Step 2: Write `.env.example`**

```env
APP_ENV=development

POSTGRES_PASSWORD=mysecretpassword
DATABASE_URL=postgresql://postgres:mysecretpassword@localhost:5432/agentic_rag
SQL_AGENT_DB_URL=postgresql://agent_readonly:agent_readonly_password@localhost:5432/agentic_rag

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=llama3
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

JWT_SECRET_KEY=change-me
JWT_EXPIRE_MINUTES=60

UPLOAD_DIR=./storage/uploads

CORS_ORIGINS=http://localhost:5173
```

- [ ] **Step 3: Write `.gitignore`**

```gitignore
.env
__pycache__/
*.pyc
node_modules/
storage/uploads/
storage/processed/
venv/
.venv/
```

- [ ] **Step 4: Copy `.env.example` to `.env` and start Postgres**

Run: `cp .env.example .env && docker compose up -d postgres`
Expected: container `agentic-rag-db` running, healthcheck passing.

Verify: `docker compose ps` shows `postgres` as `healthy`.

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml .env.example .gitignore
git commit -m "Add Docker Compose for PostgreSQL + pgvector"
```

---

### Task 2: Python project scaffold for migrations

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/` (empty dir, populated in Task 3)
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`

**Interfaces:**
- Produces: `app.config.settings` (pydantic-settings object with `database_url`, `sql_agent_db_url`, `jwt_secret_key`, `jwt_expire_minutes`, `ollama_base_url`, `ollama_llm_model`, `ollama_embedding_model`, `upload_dir`, `cors_origins`).
- Produces: `app.database.Base` (SQLAlchemy declarative base), `app.database.engine`, `app.database.SessionLocal`, `app.database.get_db()` generator dependency.

- [ ] **Step 1: Write `backend/requirements.txt`**

```text
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.35
alembic==1.13.3
psycopg2-binary==2.9.9
pydantic-settings==2.5.2
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
langchain==0.3.7
langchain-community==0.3.5
langchain-ollama==0.2.0
pgvector==0.3.5
```

- [ ] **Step 2: Create venv and install**

Run:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
Expected: install completes without error.

- [ ] **Step 3: Write `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    app_env: str = "development"
    database_url: str
    sql_agent_db_url: str
    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = "llama3"
    ollama_embedding_model: str = "nomic-embed-text"
    jwt_secret_key: str
    jwt_expire_minutes: int = 60
    upload_dir: str = "./storage/uploads"
    cors_origins: str = "http://localhost:5173"


settings = Settings()
```

- [ ] **Step 4: Write `backend/app/database.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5: Write `backend/app/__init__.py`** (empty file)

- [ ] **Step 6: Verify config loads**

Run: `cd backend && source venv/bin/activate && python -c "from app.config import settings; print(settings.database_url)"`
Expected: prints `postgresql://postgres:mysecretpassword@localhost:5432/agentic_rag`

- [ ] **Step 7: Initialize Alembic**

Run: `cd backend && source venv/bin/activate && alembic init alembic`
Expected: creates `alembic/` dir and `alembic.ini`.

- [ ] **Step 8: Edit `backend/alembic/env.py` to use `app.database.Base` and settings URL**

Modify `backend/alembic/env.py` — add near top after existing imports:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base
from app.config import settings

target_metadata = Base.metadata
```

Replace the line `config.set_main_option("sqlalchemy.url", ...)` usage (or the hardcoded url read) so `run_migrations_offline`/`run_migrations_online` use `settings.database_url`:

Find this line in `env.py`:
```python
config = context.config
```
Add immediately after it:
```python
config.set_main_option("sqlalchemy.url", settings.database_url)
```

- [ ] **Step 9: Commit**

```bash
git add backend/requirements.txt backend/alembic.ini backend/alembic/ backend/app/__init__.py backend/app/config.py backend/app/database.py
git commit -m "Scaffold Python backend project and Alembic migrations"
```

---

### Task 3: Database schema migration

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/chat_history.py`
- Create: `backend/app/models/document.py`
- Create: `backend/app/models/order.py`
- Create: `backend/alembic/versions/0001_initial_schema.py`
- Test: `backend/tests/test_models_import.py`

**Interfaces:**
- Consumes: `app.database.Base` (Task 2)
- Produces: ORM classes `User`, `ChatHistory`, `Document`, `Order` — used by Task 4 (seed data) and later Fase 2 backend tasks (auth, chat, RAG, SQL tool).
  - `User(id, username, password_hash, role, created_at)`
  - `ChatHistory(id, session_id, user_id, role, message, created_at)`
  - `Document(id, filename, content, embedding, metadata, created_at)`
  - `Order(id, customer_name, product, amount, order_date)`

- [ ] **Step 1: Write `backend/app/models/user.py`**

```python
from sqlalchemy import Column, BigInteger, String, DateTime
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, server_default="USER")
    created_at = Column(DateTime, server_default=func.now())
```

- [ ] **Step 2: Write `backend/app/models/chat_history.py`**

```python
from sqlalchemy import Column, BigInteger, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(BigInteger, primary_key=True)
    session_id = Column(String(100), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    role = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
```

- [ ] **Step 3: Write `backend/app/models/document.py`**

```python
from sqlalchemy import Column, BigInteger, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(BigInteger, primary_key=True)
    filename = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768))
    metadata_ = Column("metadata", JSON)
    created_at = Column(DateTime, server_default=func.now())
```

- [ ] **Step 4: Write `backend/app/models/order.py`**

```python
from sqlalchemy import Column, BigInteger, String, Numeric, Date

from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(BigInteger, primary_key=True)
    customer_name = Column(String(255), nullable=False)
    product = Column(String(255), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    order_date = Column(Date, nullable=False)
```

- [ ] **Step 5: Write `backend/app/models/__init__.py`**

```python
from app.models.user import User
from app.models.chat_history import ChatHistory
from app.models.document import Document
from app.models.order import Order

__all__ = ["User", "ChatHistory", "Document", "Order"]
```

- [ ] **Step 6: Write failing test verifying models import and map to expected tables**

```python
# backend/tests/test_models_import.py
from app.models import User, ChatHistory, Document, Order


def test_table_names():
    assert User.__tablename__ == "users"
    assert ChatHistory.__tablename__ == "chat_history"
    assert Document.__tablename__ == "documents"
    assert Order.__tablename__ == "orders"
```

- [ ] **Step 7: Run test verify it fails**

Run: `cd backend && source venv/bin/activate && pip install pytest && pytest tests/test_models_import.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models'` (models dir not yet importable, or pgvector not installed) — resolved by steps above; if it already passes at this point because files exist, proceed (models are new code, so this documents intent rather than a red/green cycle).

- [ ] **Step 8: Run test verify passes**

Run: `pytest tests/test_models_import.py -v`
Expected: PASS (4 assertions)

- [ ] **Step 9: Generate Alembic migration**

Run: `cd backend && alembic revision --autogenerate -m "initial schema"`
Expected: creates file in `backend/alembic/versions/`. Rename generated file to `0001_initial_schema.py` if needed (`mv <generated>.py alembic/versions/0001_initial_schema.py` and edit `revision =` id accordingly is not required — filename rename alone is fine, Alembic uses the `revision` variable inside the file, not filename).

- [ ] **Step 10: Manually add `CREATE EXTENSION IF NOT EXISTS vector;` to the migration's `upgrade()`**

Edit generated `backend/alembic/versions/0001_initial_schema.py` — add as the first line inside `def upgrade():`:

```python
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
```

- [ ] **Step 11: Run migration against Postgres**

Run: `cd backend && alembic upgrade head`
Expected: no errors; tables `users`, `chat_history`, `documents`, `orders` created.

Verify: `docker exec -it agentic-rag-db psql -U postgres -d agentic_rag -c '\dt'`
Expected output lists all 4 tables plus `alembic_version`.

- [ ] **Step 12: Commit**

```bash
git add backend/app/models/ backend/alembic/versions/0001_initial_schema.py backend/tests/test_models_import.py
git commit -m "Add database models and initial schema migration"
```

---

### Task 4: SQL Agent read-only DB user + seed dummy orders

**Files:**
- Create: `backend/scripts/init_sql_agent_user.sql`
- Create: `backend/scripts/seed_orders.py`

**Interfaces:**
- Consumes: `app.database.SessionLocal`, `app.models.Order` (Task 3)
- Produces: Postgres role `agent_readonly` with `SELECT`-only grant on `orders`; 10 seeded rows in `orders`.

- [ ] **Step 1: Write `backend/scripts/init_sql_agent_user.sql`**

```sql
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'agent_readonly') THEN
      CREATE ROLE agent_readonly LOGIN PASSWORD 'agent_readonly_password';
   END IF;
END
$$;

GRANT CONNECT ON DATABASE agentic_rag TO agent_readonly;
GRANT USAGE ON SCHEMA public TO agent_readonly;
GRANT SELECT ON orders TO agent_readonly;
REVOKE ALL ON documents, chat_history, users FROM agent_readonly;
```

- [ ] **Step 2: Apply SQL script**

Run: `docker exec -i agentic-rag-db psql -U postgres -d agentic_rag < backend/scripts/init_sql_agent_user.sql`
Expected: no errors.

Verify: `docker exec -it agentic-rag-db psql -U postgres -d agentic_rag -c "\du agent_readonly"` shows role exists.

- [ ] **Step 3: Write `backend/scripts/seed_orders.py`**

```python
from datetime import date

from app.database import SessionLocal
from app.models import Order

SEED_ROWS = [
    ("Andi Wijaya", "Laptop", 12500000, date(2026, 1, 5)),
    ("Budi Santoso", "Monitor", 2100000, date(2026, 2, 12)),
    ("Citra Dewi", "Keyboard", 450000, date(2026, 2, 20)),
    ("Dian Permata", "Mouse", 150000, date(2026, 3, 1)),
    ("Eka Putra", "Laptop", 13200000, date(2026, 3, 15)),
    ("Fajar Nugroho", "Webcam", 650000, date(2026, 4, 2)),
    ("Gita Lestari", "Monitor", 2300000, date(2026, 4, 18)),
    ("Hendra Saputra", "Headset", 800000, date(2026, 5, 3)),
    ("Indah Sari", "Laptop", 11900000, date(2026, 5, 22)),
    ("Joko Susilo", "Keyboard", 480000, date(2026, 6, 10)),
]


def seed():
    db = SessionLocal()
    try:
        if db.query(Order).count() > 0:
            print("orders already seeded, skipping")
            return
        for customer_name, product, amount, order_date in SEED_ROWS:
            db.add(Order(customer_name=customer_name, product=product, amount=amount, order_date=order_date))
        db.commit()
        print(f"seeded {len(SEED_ROWS)} orders")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
```

- [ ] **Step 4: Run seed script**

Run: `cd backend && source venv/bin/activate && python -m scripts.seed_orders`
Expected: prints `seeded 10 orders`.

Verify: `docker exec -it agentic-rag-db psql -U postgres -d agentic_rag -c "SELECT count(*) FROM orders;"`
Expected: `10`.

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/
git commit -m "Add SQL agent read-only user and seed dummy orders"
```

---

### Task 5: Install Ollama and pull models

**Files:** None (host-level setup, documented in `backend/README.md`)

**Interfaces:**
- Produces: Ollama server at `http://localhost:11434`, models `llama3` and `nomic-embed-text` available for Fase 2/3 services.

- [ ] **Step 1: Install Ollama** (per README section 5/12 — platform-specific, e.g. macOS: `brew install ollama` or download from ollama.com)

- [ ] **Step 2: Start Ollama server**

Run: `ollama serve &` (or use the desktop app / launchd service if already running as a service)
Expected: server listening on port 11434.

- [ ] **Step 3: Pull LLM model**

Run: `ollama pull llama3`
Expected: model downloaded successfully.

- [ ] **Step 4: Pull embedding model**

Run: `ollama pull nomic-embed-text`
Expected: model downloaded successfully.

- [ ] **Step 5: Verify Ollama responds**

Run: `curl http://localhost:11434/api/tags`
Expected: JSON listing `llama3` and `nomic-embed-text` in `models`.

- [ ] **Step 6: Write `backend/README.md` documenting the manual Ollama setup**

```markdown
# Backend Setup

## Ollama (host machine, not Dockerized)

1. Install Ollama: https://ollama.com
2. Start server: `ollama serve`
3. Pull models:
   - `ollama pull llama3`
   - `ollama pull nomic-embed-text`
4. Verify: `curl http://localhost:11434/api/tags`

## Database

See `docker-compose.yml` at repo root. Run `docker compose up -d postgres`, then
`alembic upgrade head` from `backend/` to apply migrations.
```

- [ ] **Step 7: Commit**

```bash
git add backend/README.md
git commit -m "Document Ollama host setup"
```

---

## Definition of Done for Fase 1

- [ ] `docker compose up -d postgres` starts healthy Postgres+pgvector container.
- [ ] `alembic upgrade head` creates `users`, `chat_history`, `documents`, `orders` tables.
- [ ] `agent_readonly` role exists with SELECT-only on `orders`.
- [ ] `orders` table has 10 seeded rows.
- [ ] Ollama running with `llama3` and `nomic-embed-text` pulled.
- [ ] `pytest backend/tests/test_models_import.py` passes.
