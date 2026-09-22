# Fase 2 — Backend Core & AI Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** FastAPI app dengan JWT auth (register/login, role-based deps), dan tiga tools berdiri sendiri (RAG search via pgvector, OCR via PaddleOCR, SQL query read-only ke `orders`) yang dapat dipanggil langsung (tanpa agent orchestrator — itu Fase 3).

**Architecture:** FastAPI app di `backend/app/main.py` meng-include router dari `app/api/`. Auth pakai JWT (python-jose) + bcrypt (passlib), role disimpan di token payload. Setiap tool adalah fungsi Python murni di `app/tools/*.py` yang dipanggil service layer (`app/services/*.py`); agent binding menyusul Fase 3. Dependensi ke Fase 1: tabel `users/chat_history/documents/orders` sudah ada, `agent_readonly` DB role sudah ada, Ollama sudah jalan dengan `llama3`+`nomic-embed-text`.

**Tech Stack:** FastAPI, Uvicorn, SQLAlchemy, python-jose, passlib[bcrypt], PaddleOCR, langchain-ollama (embedding client), pgvector.

**Spec:** `docs/superpowers/specs/2026-09-21-agentic-rag-local-design.md` (section 4, 5, 6)

## Global Constraints

- SQL Tool hanya SELECT, allowlist tabel `orders`, timeout 5s, pakai `SQL_AGENT_DB_URL` (role `agent_readonly`).
- JWT expiry 60 menit, role ADMIN/USER/READ_ONLY. READ_ONLY tidak boleh POST `/upload` atau `/documents`.
- Semua endpoint kecuali `/health`, `/auth/*` butuh `Authorization: Bearer <token>`.
- Dokumen hasil RAG diperlakukan sebagai untrusted data dalam prompt, bukan instruksi.
- Embedding dimension 768 (`nomic-embed-text`).

---

### Task 1: Auth core — password hashing & JWT

**Files:**
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/security.py`
- Test: `backend/tests/test_security.py`

**Interfaces:**
- Produces: `hash_password(password: str) -> str`, `verify_password(password: str, hashed: str) -> bool`, `create_access_token(user_id: int, username: str, role: str) -> str`, `decode_access_token(token: str) -> dict` (raises `jose.JWTError` on invalid/expired).

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_security.py
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token


def test_password_hash_and_verify():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_create_and_decode_token():
    token = create_access_token(user_id=1, username="alice", role="USER")
    payload = decode_access_token(token)
    assert payload["sub"] == "1"
    assert payload["username"] == "alice"
    assert payload["role"] == "USER"
```

- [ ] **Step 2: Run test verify fails**

Run: `cd backend && source venv/bin/activate && pytest tests/test_security.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.core.security'`

- [ ] **Step 3: Write `backend/app/core/__init__.py`** (empty file)

- [ ] **Step 4: Write `backend/app/core/security.py`**

```python
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_access_token(user_id: int, username: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
```

- [ ] **Step 5: Run test verify passes**

Run: `pytest tests/test_security.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/ backend/tests/test_security.py
git commit -m "Add password hashing and JWT helpers"
```

---

### Task 2: Auth API — register & login

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/auth.py`
- Modify: `backend/app/main.py` (create if not present)
- Test: `backend/tests/test_auth_api.py`

**Interfaces:**
- Consumes: `hash_password`, `verify_password`, `create_access_token` (Task 1); `app.models.User`, `app.database.get_db` (Fase 1).
- Produces: `router` (FastAPI `APIRouter`) in `app.api.auth` mounted at prefix `/auth`; endpoints `POST /auth/register`, `POST /auth/login`.

- [ ] **Step 1: Write `backend/app/schemas/__init__.py`** (empty file)

- [ ] **Step 2: Write `backend/app/schemas/auth.py`**

```python
from pydantic import BaseModel


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "USER"


class UserResponse(BaseModel):
    id: int
    username: str
    role: str

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

- [ ] **Step 3: Write `backend/app/api/__init__.py`** (empty file)

- [ ] **Step 4: Write `backend/app/api/auth.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="username already taken")
    user = User(username=payload.username, password_hash=hash_password(payload.password), role=payload.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    token = create_access_token(user_id=user.id, username=user.username, role=user.role)
    return TokenResponse(access_token=token)
```

- [ ] **Step 5: Write `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth
from app.config import settings

app = FastAPI(title="Agentic RAG Local")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
```

- [ ] **Step 6: Write failing test**

```python
# backend/tests/test_auth_api.py
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_register_and_login():
    resp = client.post("/auth/register", json={"username": "testuser1", "password": "pass1234"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "testuser1"

    resp = client.post("/auth/login", json={"username": "testuser1", "password": "pass1234"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password():
    resp = client.post("/auth/login", json={"username": "testuser1", "password": "wrong"})
    assert resp.status_code == 401
```

- [ ] **Step 7: Run test verify fails or passes only after wiring**

Run: `pytest tests/test_auth_api.py -v`
Expected: PASS once Steps 1-5 are in place (requires Postgres running from Fase 1 with `users` table migrated). If it fails with connection error, run `docker compose up -d postgres` first.

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/ backend/app/api/ backend/app/main.py backend/tests/test_auth_api.py
git commit -m "Add auth register/login API"
```

---

### Task 3: Auth dependencies — current user & role guard

**Files:**
- Create: `backend/app/core/deps.py`
- Test: `backend/tests/test_deps.py`

**Interfaces:**
- Consumes: `decode_access_token` (Task 1), `app.models.User`, `app.database.get_db`.
- Produces: `get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User` (raises 401 if invalid), `require_role(allowed_roles: list[str])` — returns a FastAPI dependency callable that raises 403 if `current_user.role` not in `allowed_roles`.

- [ ] **Step 1: Write `backend/app/core/deps.py`**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")
    return user


def require_role(allowed_roles: list[str]):
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
        return current_user

    return checker
```

- [ ] **Step 2: Write test**

```python
# backend/tests/test_deps.py
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.deps import get_current_user, require_role
from app.core.security import create_access_token
from app.main import app as main_app

client = TestClient(main_app)


def _register_and_login(username, role="USER"):
    client.post("/auth/register", json={"username": username, "password": "pass1234", "role": role})
    resp = client.login = client.post("/auth/login", json={"username": username, "password": "pass1234"})
    return resp.json()["access_token"]


def test_protected_route_requires_token():
    test_app = FastAPI()

    @test_app.get("/protected")
    def protected(user=Depends(get_current_user)):
        return {"username": user.username}

    test_app.dependency_overrides.update(main_app.dependency_overrides)
    local_client = TestClient(test_app)
    resp = local_client.get("/protected")
    assert resp.status_code == 401


def test_require_role_forbids_wrong_role():
    token = _register_and_login("readonlyuser1", role="READ_ONLY")

    test_app = FastAPI()

    @test_app.get("/admin-only")
    def admin_only(user=Depends(require_role(["ADMIN"]))):
        return {"ok": True}

    local_client = TestClient(test_app)
    resp = local_client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
```

- [ ] **Step 3: Run test**

Run: `pytest tests/test_deps.py -v`
Expected: PASS (2 tests). Requires Postgres running.

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/deps.py backend/tests/test_deps.py
git commit -m "Add current-user and role-guard dependencies"
```

---

### Task 4: Embedding service (Ollama)

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/embedding_service.py`
- Test: `backend/tests/test_embedding_service.py`

**Interfaces:**
- Produces: `embed_text(text: str) -> list[float]` — returns a 768-length vector via Ollama `nomic-embed-text`.

- [ ] **Step 1: Write `backend/app/services/__init__.py`** (empty file)

- [ ] **Step 2: Write `backend/app/services/embedding_service.py`**

```python
from langchain_ollama import OllamaEmbeddings

from app.config import settings

_embeddings = OllamaEmbeddings(model=settings.ollama_embedding_model, base_url=settings.ollama_base_url)


def embed_text(text: str) -> list[float]:
    return _embeddings.embed_query(text)
```

- [ ] **Step 3: Write test (requires Ollama running with nomic-embed-text pulled from Fase 1)**

```python
# backend/tests/test_embedding_service.py
from app.services.embedding_service import embed_text


def test_embed_text_returns_768_dim_vector():
    vector = embed_text("hello world")
    assert len(vector) == 768
    assert all(isinstance(x, float) for x in vector)
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_embedding_service.py -v`
Expected: PASS. If Ollama isn't running, start it first (`ollama serve`) — this test requires a live Ollama instance, no mocking, since dimension correctness is the thing being verified.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/__init__.py backend/app/services/embedding_service.py backend/tests/test_embedding_service.py
git commit -m "Add embedding service using Ollama"
```

---

### Task 5: RAG tool — document ingestion + similarity search

**Files:**
- Create: `backend/app/services/document_service.py`
- Create: `backend/app/tools/__init__.py`
- Create: `backend/app/tools/rag_tool.py`
- Test: `backend/tests/test_rag_tool.py`

**Interfaces:**
- Consumes: `embed_text` (Task 4), `app.models.Document`, `app.database.SessionLocal`.
- Produces: `ingest_document(filename: str, content: str) -> int` (returns new document id, stores embedding); `rag_search(query: str, top_k: int = 3) -> list[dict]` (each dict: `{"filename": str, "content": str, "score": float}`), ordered by pgvector cosine distance ascending (best match first).

- [ ] **Step 1: Write `backend/app/services/document_service.py`**

```python
from app.database import SessionLocal
from app.models import Document
from app.services.embedding_service import embed_text


def ingest_document(filename: str, content: str) -> int:
    db = SessionLocal()
    try:
        embedding = embed_text(content)
        doc = Document(filename=filename, content=content, embedding=embedding)
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc.id
    finally:
        db.close()
```

- [ ] **Step 2: Write `backend/app/tools/__init__.py`** (empty file)

- [ ] **Step 3: Write `backend/app/tools/rag_tool.py`**

```python
from app.database import SessionLocal
from app.models import Document
from app.services.embedding_service import embed_text


def rag_search(query: str, top_k: int = 3) -> list[dict]:
    db = SessionLocal()
    try:
        query_embedding = embed_text(query)
        results = (
            db.query(Document, Document.embedding.cosine_distance(query_embedding).label("distance"))
            .order_by("distance")
            .limit(top_k)
            .all()
        )
        return [
            {"filename": doc.filename, "content": doc.content, "score": float(distance)}
            for doc, distance in results
        ]
    finally:
        db.close()
```

- [ ] **Step 4: Write test**

```python
# backend/tests/test_rag_tool.py
from app.services.document_service import ingest_document
from app.tools.rag_tool import rag_search


def test_ingest_and_search_finds_relevant_document():
    ingest_document("policy.txt", "Masa retensi dokumen perusahaan adalah 5 tahun sejak tanggal pembuatan.")
    ingest_document("unrelated.txt", "Resep membuat kopi susu dengan gula aren.")

    results = rag_search("berapa lama masa retensi dokumen?", top_k=2)

    assert len(results) == 2
    assert results[0]["filename"] == "policy.txt"
```

- [ ] **Step 5: Run test**

Run: `pytest tests/test_rag_tool.py -v`
Expected: PASS. Requires Postgres + Ollama running.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/document_service.py backend/app/tools/__init__.py backend/app/tools/rag_tool.py backend/tests/test_rag_tool.py
git commit -m "Add RAG tool: document ingestion and similarity search"
```

---

### Task 6: OCR tool — PaddleOCR

**Files:**
- Create: `backend/app/tools/ocr_tool.py`
- Test: `backend/tests/test_ocr_tool.py`
- Test fixture: `backend/tests/fixtures/sample_text_image.png`

**Interfaces:**
- Produces: `image_ocr(image_path: str) -> str` — returns extracted text (newline-joined lines), raises `FileNotFoundError` if path doesn't exist.

- [ ] **Step 1: Add PaddleOCR to requirements**

Modify `backend/requirements.txt` — append:
```text
paddleocr==2.9.1
paddlepaddle==2.6.2
```

Run: `cd backend && source venv/bin/activate && pip install -r requirements.txt`
Expected: install completes (may take several minutes — PaddleOCR pulls a base model on first use).

- [ ] **Step 2: Write `backend/app/tools/ocr_tool.py`**

```python
import os

from paddleocr import PaddleOCR

_ocr = None


def _get_ocr() -> PaddleOCR:
    global _ocr
    if _ocr is None:
        _ocr = PaddleOCR(use_angle_cls=True, lang="en")
    return _ocr


def image_ocr(image_path: str) -> str:
    if not os.path.exists(image_path):
        raise FileNotFoundError(image_path)
    result = _get_ocr().ocr(image_path, cls=True)
    lines = [line[1][0] for block in result for line in block]
    return "\n".join(lines)
```

- [ ] **Step 3: Create a fixture image with known text**

Run (Python, one-off, generates a PNG with the word "TOTAL 150000"):
```bash
cd backend && source venv/bin/activate && python -c "
from PIL import Image, ImageDraw
import os
os.makedirs('tests/fixtures', exist_ok=True)
img = Image.new('RGB', (300, 100), color='white')
draw = ImageDraw.Draw(img)
draw.text((10, 40), 'TOTAL 150000', fill='black')
img.save('tests/fixtures/sample_text_image.png')
"
```
Expected: file `backend/tests/fixtures/sample_text_image.png` created. (Add `Pillow` to `requirements.txt` if not already installed as a PaddleOCR dependency — check with `pip show Pillow`; install with `pip install Pillow` if missing.)

- [ ] **Step 4: Write test**

```python
# backend/tests/test_ocr_tool.py
import pytest

from app.tools.ocr_tool import image_ocr


def test_ocr_extracts_text_from_image():
    text = image_ocr("tests/fixtures/sample_text_image.png")
    assert "150000" in text or "TOTAL" in text.upper()


def test_ocr_raises_on_missing_file():
    with pytest.raises(FileNotFoundError):
        image_ocr("tests/fixtures/does_not_exist.png")
```

- [ ] **Step 5: Run test**

Run: `pytest tests/test_ocr_tool.py -v`
Expected: PASS (first run downloads PaddleOCR detection/recognition models, may take a minute).

- [ ] **Step 6: Commit**

```bash
git add backend/requirements.txt backend/app/tools/ocr_tool.py backend/tests/test_ocr_tool.py backend/tests/fixtures/sample_text_image.png
git commit -m "Add OCR tool using PaddleOCR"
```

---

### Task 7: SQL tool — read-only query on `orders`

**Files:**
- Create: `backend/app/tools/sql_tool.py`
- Test: `backend/tests/test_sql_tool.py`

**Interfaces:**
- Produces: `sql_query(query: str) -> list[dict]` — executes SELECT-only query against `SQL_AGENT_DB_URL` (role `agent_readonly`), rejects anything not starting with `SELECT` or referencing tables other than `orders`, 5s timeout, returns list of row dicts. Raises `ValueError` on disallowed query.

- [ ] **Step 1: Write `backend/app/tools/sql_tool.py`**

```python
import re

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from app.config import settings

_engine = create_engine(settings.sql_agent_db_url, connect_args={"options": "-c statement_timeout=5000"})

ALLOWED_TABLES = {"orders"}
FORBIDDEN_KEYWORDS = {"insert", "update", "delete", "drop", "alter", "truncate", "grant", "revoke", "--", ";"}


def _validate_query(query: str) -> None:
    normalized = query.strip().lower()
    if not normalized.startswith("select"):
        raise ValueError("only SELECT queries are allowed")
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in normalized:
            raise ValueError(f"query contains forbidden keyword: {keyword}")
    tables_referenced = set(re.findall(r"from\s+([a-zA-Z_][a-zA-Z0-9_]*)", normalized))
    tables_referenced |= set(re.findall(r"join\s+([a-zA-Z_][a-zA-Z0-9_]*)", normalized))
    if not tables_referenced or not tables_referenced.issubset(ALLOWED_TABLES):
        raise ValueError(f"query references disallowed table(s): {tables_referenced - ALLOWED_TABLES}")


def sql_query(query: str) -> list[dict]:
    _validate_query(query)
    try:
        with _engine.connect() as conn:
            result = conn.execute(text(query))
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]
    except OperationalError as exc:
        raise ValueError(f"query execution failed: {exc}") from exc
```

- [ ] **Step 2: Write test**

```python
# backend/tests/test_sql_tool.py
import pytest

from app.tools.sql_tool import sql_query


def test_select_orders_succeeds():
    rows = sql_query("SELECT * FROM orders LIMIT 5")
    assert len(rows) <= 5
    assert "customer_name" in rows[0]


def test_select_disallowed_table_raises():
    with pytest.raises(ValueError):
        sql_query("SELECT * FROM users")


def test_non_select_raises():
    with pytest.raises(ValueError):
        sql_query("DELETE FROM orders")


def test_semicolon_injection_raises():
    with pytest.raises(ValueError):
        sql_query("SELECT * FROM orders; DROP TABLE orders")
```

- [ ] **Step 3: Run test**

Run: `pytest tests/test_sql_tool.py -v`
Expected: PASS (4 tests). Requires `agent_readonly` role from Fase 1 Task 4 to exist and `SQL_AGENT_DB_URL` in `.env` to match.

- [ ] **Step 4: Commit**

```bash
git add backend/app/tools/sql_tool.py backend/tests/test_sql_tool.py
git commit -m "Add SQL tool with read-only allowlist validation"
```

---

### Task 8: Upload & documents API

**Files:**
- Create: `backend/app/schemas/document.py`
- Create: `backend/app/api/documents.py`
- Modify: `backend/app/main.py` (register router)
- Test: `backend/tests/test_documents_api.py`

**Interfaces:**
- Consumes: `require_role` (Task 3), `ingest_document` (Task 5), `settings.upload_dir`.
- Produces: `router` in `app.api.documents` mounted at no extra prefix; `POST /upload` (multipart file, role != READ_ONLY), `POST /documents` (JSON `{filename, content}`, role != READ_ONLY).

- [ ] **Step 1: Write `backend/app/schemas/document.py`**

```python
from pydantic import BaseModel


class DocumentCreateRequest(BaseModel):
    filename: str
    content: str


class DocumentResponse(BaseModel):
    filename: str
    status: str
```

- [ ] **Step 2: Write `backend/app/api/documents.py`**

```python
import os

from fastapi import APIRouter, Depends, UploadFile

from app.config import settings
from app.core.deps import require_role
from app.schemas.document import DocumentCreateRequest, DocumentResponse
from app.services.document_service import ingest_document

router = APIRouter(tags=["documents"])

allow_write = require_role(["ADMIN", "USER"])


@router.post("/upload", response_model=DocumentResponse)
async def upload_file(file: UploadFile, _user=Depends(allow_write)):
    os.makedirs(settings.upload_dir, exist_ok=True)
    dest_path = os.path.join(settings.upload_dir, file.filename)
    content_bytes = await file.read()
    with open(dest_path, "wb") as f:
        f.write(content_bytes)

    text_content = content_bytes.decode("utf-8", errors="ignore")
    ingest_document(file.filename, text_content)

    return DocumentResponse(filename=file.filename, status="processed")


@router.post("/documents", response_model=DocumentResponse)
def create_document(payload: DocumentCreateRequest, _user=Depends(allow_write)):
    ingest_document(payload.filename, payload.content)
    return DocumentResponse(filename=payload.filename, status="processed")
```

- [ ] **Step 3: Modify `backend/app/main.py`** — add import and router registration

Add to imports: `from app.api import documents`
Add after `app.include_router(auth.router)`: `app.include_router(documents.router)`

- [ ] **Step 4: Write test**

```python
# backend/tests/test_documents_api.py
import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _get_token(username, role="USER"):
    client.post("/auth/register", json={"username": username, "password": "pass1234", "role": role})
    resp = client.post("/auth/login", json={"username": username, "password": "pass1234"})
    return resp.json()["access_token"]


def test_upload_requires_write_role():
    token = _get_token("readonlyuploader1", role="READ_ONLY")
    resp = client.post(
        "/upload",
        files={"file": ("test.txt", io.BytesIO(b"hello world"), "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_upload_succeeds_for_user_role():
    token = _get_token("uploaderuser1", role="USER")
    resp = client.post(
        "/upload",
        files={"file": ("test2.txt", io.BytesIO(b"isi dokumen contoh"), "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "processed"
```

- [ ] **Step 5: Run test**

Run: `pytest tests/test_documents_api.py -v`
Expected: PASS (2 tests). Requires Postgres + Ollama running (upload triggers embedding).

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/document.py backend/app/api/documents.py backend/app/main.py backend/tests/test_documents_api.py
git commit -m "Add upload and documents API with role restriction"
```

---

### Task 9: Health check API

**Files:**
- Create: `backend/app/api/health.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_health_api.py`

**Interfaces:**
- Produces: `GET /health` -> `{"status": "ok"}`, no auth required.

- [ ] **Step 1: Write `backend/app/api/health.py`**

```python
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 2: Modify `backend/app/main.py`** — add import and router

Add to imports: `from app.api import health`
Add: `app.include_router(health.router)`

- [ ] **Step 3: Write test**

```python
# backend/tests/test_health_api.py
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_health_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/health.py backend/app/main.py backend/tests/test_health_api.py
git commit -m "Add health check endpoint"
```

---

### Task 10: Run full backend test suite

**Files:** None (verification task)

- [ ] **Step 1: Run full test suite**

Run: `cd backend && source venv/bin/activate && pytest tests/ -v`
Expected: all tests PASS (Tasks 1-9 combined). Requires Postgres and Ollama both running.

- [ ] **Step 2: Start server manually and smoke-test**

Run: `cd backend && uvicorn app.main:app --reload --port 8000`
In another terminal: `curl http://localhost:8000/health`
Expected: `{"status":"ok"}`

Stop the server (Ctrl+C) after verifying.

---

## Definition of Done for Fase 2

- [ ] `POST /auth/register` and `POST /auth/login` work; login returns valid JWT.
- [ ] `require_role` blocks READ_ONLY from `/upload` and `/documents` (403).
- [ ] `rag_search()` returns relevant document given ingested content.
- [ ] `image_ocr()` extracts text from a sample image.
- [ ] `sql_query()` executes SELECT on `orders`, rejects other tables/statements.
- [ ] `GET /health` returns 200 without auth.
- [ ] `pytest backend/tests/` passes in full.
