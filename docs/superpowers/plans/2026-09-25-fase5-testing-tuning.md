# Fase 5 — Testing & Tuning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validasi end-to-end sesuai Testing Matrix di spec (RAG-001, OCR-001, SQL-001, AGENT-001/002, SEC-001/002 + SEC-003 auth) berjalan hijau, dan checklist Definition of Done (spec section 9 README) terpenuhi.

**Architecture:** Test tambahan di level integrasi (`backend/tests/test_e2e_scenarios.py`) yang menjalankan skenario testing matrix lewat `TestClient`, melengkapi unit test yang sudah ada dari Fase 1-3. Tidak ada kode aplikasi baru — fase ini murni verifikasi + dokumentasi Definition of Done.

**Tech Stack:** pytest, FastAPI TestClient.

**Spec:** `docs/superpowers/specs/2026-09-21-agentic-rag-local-design.md` (section 9, referencing README section 16-17, 24)

## Global Constraints

- Semua test butuh Postgres + Ollama berjalan (tidak ada mocking untuk hal yang justru mau diverifikasi kebenarannya — lihat Fase 2/3 constraint yang sama).
- SEC-001 (SQL destruktif ditolak) dan SEC-002 (dokumen tidak ditemukan) sudah punya coverage unit test di Fase 2 Task 7 dan Fase 3 Task 2 — fase ini menambah test level HTTP end-to-end untuk melengkapi, bukan duplikasi logic-level.

---

### Task 1: End-to-end scenario tests (Testing Matrix)

**Files:**
- Create: `backend/tests/test_e2e_scenarios.py`

**Interfaces:**
- Consumes: `app.main.app` (Fase 2/3), existing seeded `orders` (Fase 1 Task 4), ability to register/login users.

- [ ] **Step 1: Write test covering RAG-001, OCR-001, SQL-001, AGENT-001, AGENT-002, SEC-001, SEC-002, SEC-003**

```python
# backend/tests/test_e2e_scenarios.py
import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _token(username, role="USER"):
    client.post("/auth/register", json={"username": username, "password": "pass1234", "role": role})
    resp = client.post("/auth/login", json={"username": username, "password": "pass1234"})
    return resp.json()["access_token"]


def _headers(username, role="USER"):
    return {"Authorization": f"Bearer {_token(username, role)}"}


def test_rag_001_document_question_returns_answer_from_document():
    headers = _headers("e2e_rag_user")
    client.post(
        "/documents",
        json={"filename": "leave_policy.txt", "content": "Kebijakan cuti karyawan adalah 12 hari kerja per tahun."},
        headers=headers,
    )
    resp = client.post(
        "/chat",
        json={"session_id": "e2e-rag-1", "message": "Menurut dokumen, berapa hari cuti karyawan per tahun?"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tool_used"] == "rag_search_tool"
    assert any(s["filename"] == "leave_policy.txt" for s in body["sources"])


def test_ocr_001_image_upload_and_extraction():
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (300, 100), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 40), "TOTAL 250000", fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    headers = _headers("e2e_ocr_user")
    resp = client.post(
        "/upload",
        files={"file": ("receipt.png", buf, "image/png")},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "processed"


def test_sql_001_statistics_question_returns_data_from_postgres():
    headers = _headers("e2e_sql_user")
    resp = client.post(
        "/chat",
        json={"session_id": "e2e-sql-1", "message": "Berapa jumlah order yang tercatat di database?"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["tool_used"] == "sql_query_tool"


def test_agent_001_general_question_answered_directly():
    headers = _headers("e2e_general_user")
    resp = client.post(
        "/chat",
        json={"session_id": "e2e-general-1", "message": "Halo, apa kabar?"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["answer"]


def test_agent_002_ambiguous_question_selects_a_tool_or_answers_directly():
    headers = _headers("e2e_ambiguous_user")
    resp = client.post(
        "/chat",
        json={"session_id": "e2e-ambiguous-1", "message": "Ada info apa yang bisa kamu bantu?"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["answer"]


def test_sec_001_destructive_sql_rejected_end_to_end():
    from app.tools.sql_tool import sql_query
    import pytest

    with pytest.raises(ValueError):
        sql_query("DROP TABLE orders")


def test_sec_002_missing_document_reports_not_found():
    headers = _headers("e2e_notfound_user")
    resp = client.post(
        "/chat",
        json={"session_id": "e2e-notfound-1", "message": "Menurut dokumen rahasia XYZ123, apa isinya?"},
        headers=headers,
    )
    assert resp.status_code == 200
    answer_lower = resp.json()["answer"].lower()
    assert "tidak" in answer_lower or "not found" in answer_lower or "tidak ditemukan" in answer_lower


def test_sec_003_read_only_role_cannot_upload_or_create_document():
    headers = _headers("e2e_readonly_user", role="READ_ONLY")

    resp = client.post(
        "/upload",
        files={"file": ("blocked.txt", io.BytesIO(b"data"), "text/plain")},
        headers=headers,
    )
    assert resp.status_code == 403

    resp = client.post(
        "/documents",
        json={"filename": "blocked.txt", "content": "data"},
        headers=headers,
    )
    assert resp.status_code == 403
```

- [ ] **Step 2: Run tests**

Run: `cd backend && source venv/bin/activate && pytest tests/test_e2e_scenarios.py -v`
Expected: all 8 tests PASS. Requires Postgres + Ollama running.

Note on `test_sec_002`: this asserts the LLM's phrasing includes a "not found" signal. Since llama3's exact wording can vary, if this test flakes, loosen the system prompt in Fase 3 Task 2 to more forcefully instruct the exact phrase "tidak ditemukan" rather than loosening the assertion (the spec requires this behavior, so weakening the test would hide a real gap).

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_e2e_scenarios.py
git commit -m "Add end-to-end scenario tests covering testing matrix"
```

---

### Task 2: Full regression run + Definition of Done checklist

**Files:** None (verification task)

- [ ] **Step 1: Run entire backend test suite**

Run: `cd backend && source venv/bin/activate && pytest tests/ -v`
Expected: all tests across Fase 1-5 PASS.

- [ ] **Step 2: Manually verify frontend flows** (per Fase 4 Definition of Done)

With backend running (`uvicorn app.main:app --port 8000`) and frontend running (`npm run dev` in `frontend/`):
- Login, send chat message, upload file, verify markdown + source citation render — repeat the Fase 4 Task 5 Step 5 checklist.

- [ ] **Step 3: Walk through Definition of Done checklist from spec section 9 / README section 24**

Confirm each item, checking off in this plan:

- [ ] FastAPI berjalan (`GET /health` returns 200).
- [ ] PostgreSQL terhubung (migrations applied, `pytest` DB-backed tests pass).
- [ ] pgvector aktif (`rag_search` test passes).
- [ ] Ollama berjalan (embedding + chat tests pass).
- [ ] RAG berhasil (RAG-001 passes).
- [ ] OCR berhasil (OCR-001 passes).
- [ ] SQL Tool berhasil (SQL-001 passes).
- [ ] Agent dapat memilih tool (AGENT-001, AGENT-002 pass).
- [ ] Chat UI berjalan (manual check).
- [ ] User dapat mengirim pertanyaan (manual check).
- [ ] User dapat upload gambar (manual check).
- [ ] User dapat upload dokumen (manual check).
- [ ] Response AI tampil (manual check).
- [ ] Loading state tersedia (manual check).
- [ ] Error handling tersedia (manual check).
- [ ] Authentication (JWT login/register tests pass).
- [ ] Authorization (SEC-003 test passes).
- [ ] File validation — note: basic upload works; strict MIME/signature validation is listed as Out of Scope in the spec (section 10) beyond extension-based acceptance. Confirm this gap is acceptable for MVP or file a follow-up.
- [ ] SQL restriction (SEC-001 test passes).
- [ ] Prompt injection mitigation (untrusted-context framing in Fase 3 Task 2 system prompt).
- [ ] `.env` tidak masuk Git (`git status` shows `.env` untracked, only `.env.example` committed).

- [ ] **Step 4: Record any unresolved gaps as follow-up notes** (no code change in this task — just list them for the user)

---

## Definition of Done for Fase 5

- [ ] All 8 end-to-end scenario tests pass.
- [ ] Full `pytest backend/tests/` suite (Fase 1-5) passes with zero failures.
- [ ] Manual frontend checklist from Fase 4 completed.
- [ ] Definition of Done checklist from spec walked through and confirmed or gaps flagged.
