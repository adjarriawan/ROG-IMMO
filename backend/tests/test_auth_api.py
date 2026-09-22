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
