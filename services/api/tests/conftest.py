from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trackflow_api.auth import get_password_hash
from trackflow_api.database import get_db
from trackflow_api.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    yield TestClient(app)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "trackflow-test.json"


@pytest.fixture
def monkeypatch_env(monkeypatch: pytest.MonkeyPatch, db_path: Path) -> None:
    monkeypatch.setenv("TRACKFLOW_DB_PATH", str(db_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")


@pytest.fixture
def auth_headers() -> type:
    """Return a helper class to build auth headers."""

    class _AuthHeaders:
        @staticmethod
        def with_token(token: str) -> dict[str, str]:
            return {"Authorization": f"Bearer {token}"}

        @staticmethod
        def invalid() -> dict[str, str]:
            return {"Authorization": "Bearer invalid-token"}

    return _AuthHeaders


@pytest.fixture
def created_user(monkeypatch_env: None, client: TestClient) -> dict:
    """Create a regular user and return the response data."""
    response = client.post(
        "/users",
        json={
            "email": "test@example.com",
            "password": "Secret123",
            "name": "Test User",
            "phone": "+1 555 000 0000",
            "address": "Test Address",
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def admin_token(monkeypatch_env: None, client: TestClient) -> str:
    """Create an admin user directly in DB and return a token."""
    db = get_db()
    db.table("users").insert(
        {
            "id": "admin-1",
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
            "user_id": "admin-1",
            "name": "Admin",
            "phone": "+1 555 000 0002",
            "address": "HQ",
        }
    )
    db.close()

    login_resp = client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "AdminSecret123"},
    )
    assert login_resp.status_code == 200
    return login_resp.json()["access_token"]


@pytest.fixture
def user_token(created_user: dict, client: TestClient) -> str:
    """Login as the created user and return a token."""
    login_resp = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "Secret123"},
    )
    assert login_resp.status_code == 200
    return login_resp.json()["access_token"]