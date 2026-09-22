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
