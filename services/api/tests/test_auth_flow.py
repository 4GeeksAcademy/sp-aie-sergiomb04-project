from __future__ import annotations

from fastapi.testclient import TestClient

from trackflow_api.auth import get_password_hash
from trackflow_api.database import get_db
from trackflow_api.main import app

client = TestClient(app)


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_auth_flow_and_protected_routes(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRACKFLOW_DB_PATH", str(tmp_path / "trackflow-test.json"))
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")

    register_response = client.post(
        "/users",
        json={
            "email": "user1@example.com",
            "password": "Secret123",
            "name": "User One",
            "phone": "+1 555 000 0001",
            "address": "LA Warehouse 1",
        },
    )
    assert register_response.status_code == 201
    created_user = register_response.json()
    assert created_user["email"] == "user1@example.com"
    assert created_user["role"] == "user"
    assert "hashed_password" not in created_user

    unauthorized_response = client.get("/auth/me")
    assert unauthorized_response.status_code == 401

    login_response = client.post(
        "/auth/login",
        json={"email": "user1@example.com", "password": "Secret123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = client.get("/auth/me", headers=_auth_headers(token))
    assert me_response.status_code == 200
    me_payload = me_response.json()
    assert me_payload["email"] == "user1@example.com"
    assert me_payload["profile"]["name"] == "User One"

    suppliers_without_token = client.get("/suppliers")
    assert suppliers_without_token.status_code == 401

    suppliers_with_invalid_token = client.get(
        "/suppliers",
        headers=_auth_headers("invalid-token"),
    )
    assert suppliers_with_invalid_token.status_code == 401

    suppliers_with_token = client.get("/suppliers", headers=_auth_headers(token))
    assert suppliers_with_token.status_code == 200
    assert suppliers_with_token.json() == []


def test_only_admin_can_change_role_and_other_users_are_forbidden(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRACKFLOW_DB_PATH", str(tmp_path / "trackflow-admin-test.json"))
    monkeypatch.setenv("SECRET_KEY", "test-secret")

    admin_id = "admin-1"
    db = get_db()
    db.table("users").insert(
        {
            "id": admin_id,
            "email": "admin@example.com",
            "hashed_password": get_password_hash("AdminSecret123"),
            "is_active": True,
            "role": "admin",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    )
    db.table("profiles").insert(
        {
            "id": "profile-admin-1",
            "user_id": admin_id,
            "name": "Admin",
            "phone": "+1 555 000 0002",
            "address": "HQ",
        }
    )
    db.close()

    user_response = client.post(
        "/users",
        json={
            "email": "user2@example.com",
            "password": "Secret123",
            "name": "User Two",
            "phone": "+1 555 000 0003",
            "address": "Zaragoza",
        },
    )
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]

    regular_login = client.post(
        "/auth/login",
        json={"email": "user2@example.com", "password": "Secret123"},
    )
    assert regular_login.status_code == 200
    regular_token = regular_login.json()["access_token"]

    forbidden_role_change = client.put(
        f"/users/{user_id}",
        json={"role": "manager"},
        headers=_auth_headers(regular_token),
    )
    assert forbidden_role_change.status_code == 403

    forbidden_other_user_read = client.get(
        f"/users/{admin_id}",
        headers=_auth_headers(regular_token),
    )
    assert forbidden_other_user_read.status_code == 403

    admin_login = client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "AdminSecret123"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]

    admin_role_change = client.put(
        f"/users/{user_id}",
        json={"role": "manager"},
        headers=_auth_headers(admin_token),
    )
    assert admin_role_change.status_code == 200
    assert admin_role_change.json()["role"] == "manager"