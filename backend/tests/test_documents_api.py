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
