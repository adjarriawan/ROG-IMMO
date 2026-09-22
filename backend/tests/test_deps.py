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
