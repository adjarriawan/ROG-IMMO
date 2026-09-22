# backend/tests/test_chat_api.py
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _get_token(username):
    client.post("/auth/register", json={"username": username, "password": "pass1234"})
    resp = client.post("/auth/login", json={"username": username, "password": "pass1234"})
    return resp.json()["access_token"]


def test_chat_requires_auth():
    resp = client.post("/chat", json={"session_id": "s1", "message": "hi"})
    assert resp.status_code == 401


def test_chat_and_history_roundtrip():
    token = _get_token("chatuser1")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/chat", json={"session_id": "session-test-1", "message": "Halo"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "answer" in body
    assert "tool_used" in body
    assert "sources" in body

    resp = client.get("/chat/history", params={"session_id": "session-test-1"}, headers=headers)
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"
