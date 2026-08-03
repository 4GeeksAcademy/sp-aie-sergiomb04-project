from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from trackflow_api.auth import get_password_hash
from trackflow_api.database import get_tinydb


class TestCreateUser:
    def test_create_user_success(self, client: TestClient, monkeypatch_env: None) -> None:
        response = client.post(
            "/users",
            json={
                "email": "newuser@example.com",
                "password": "Secret123",
                "name": "New User",
                "phone": "+1 555 000 0000",
                "address": "Some Address",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["role"] == "user"
        assert data["is_active"] is True
        assert "hashed_password" not in data
        assert "id" in data

    def test_create_user_duplicate_email(self, client: TestClient, monkeypatch_env: None) -> None:
        client.post(
            "/users",
            json={
                "email": "duplicate@example.com",
                "password": "Secret123",
                "name": "First",
                "phone": "+1 555 000 0000",
                "address": "Address 1",
            },
        )
        response = client.post(
            "/users",
            json={
                "email": "duplicate@example.com",
                "password": "OtherPass1",
                "name": "Second",
                "phone": "+1 555 000 0001",
                "address": "Address 2",
            },
        )
        assert response.status_code == 400
        assert "registrado" in response.json()["detail"]

    def test_create_user_weak_password(self, client: TestClient, monkeypatch_env: None) -> None:
        response = client.post(
            "/users",
            json={
                "email": "weak@example.com",
                "password": "short",
                "name": "Weak",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )
        assert response.status_code == 400

    def test_create_user_empty_name(self, client: TestClient, monkeypatch_env: None) -> None:
        response = client.post(
            "/users",
            json={
                "email": "noname@example.com",
                "password": "Secret123",
                "name": "",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )
        assert response.status_code == 400

    def test_create_user_normalizes_email(self, client: TestClient, monkeypatch_env: None) -> None:
        response = client.post(
            "/users",
            json={
                "email": "  UPPERCASE@EXAMPLE.COM  ",
                "password": "Secret123",
                "name": "User",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )
        assert response.status_code == 201
        assert response.json()["email"] == "uppercase@example.com"

    def test_create_user_invalid_email(self, client: TestClient, monkeypatch_env: None) -> None:
        response = client.post(
            "/users",
            json={
                "email": "not-an-email",
                "password": "Secret123",
                "name": "User",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )
        assert response.status_code == 400


class TestListUsers:
    def test_list_users_as_admin(self, client: TestClient, monkeypatch_env: None, admin_token: str) -> None:
        response = client.get(
            "/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_users_as_non_admin(self, client: TestClient, monkeypatch_env: None, user_token: str) -> None:
        response = client.get(
            "/users",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403

    def test_list_users_without_auth(self, client: TestClient, monkeypatch_env: None) -> None:
        response = client.get("/users")
        assert response.status_code == 401


class TestGetUser:
    def test_admin_can_get_any_user(self, client: TestClient, monkeypatch_env: None, admin_token: str) -> None:
        # Create a user first
        create_resp = client.post(
            "/users",
            json={
                "email": "target@example.com",
                "password": "Secret123",
                "name": "Target User",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )
        user_id = create_resp.json()["id"]

        response = client.get(
            f"/users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "target@example.com"

    def test_user_can_get_self(self, client: TestClient, monkeypatch_env: None, user_token: str) -> None:
        login_resp = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "Secret123"},
        )
        token = login_resp.json()["access_token"]

        # Get user info from /auth/me first to get the ID
        me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 200

    def test_user_cannot_get_other_user(self, client: TestClient, monkeypatch_env: None, user_token: str) -> None:
        # Create another user
        create_resp = client.post(
            "/users",
            json={
                "email": "other@example.com",
                "password": "Secret123",
                "name": "Other",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )
        other_id = create_resp.json()["id"]

        # Try to get the other user's profile
        response = client.get(
            f"/users/{other_id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403

    def test_get_nonexistent_user(self, client: TestClient, monkeypatch_env: None, admin_token: str) -> None:
        response = client.get(
            "/users/nonexistent-id",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404


class TestUpdateUser:
    def test_admin_can_change_role(self, client: TestClient, monkeypatch_env: None, admin_token: str) -> None:
        create_resp = client.post(
            "/users",
            json={
                "email": "promote@example.com",
                "password": "Secret123",
                "name": "Promote",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )
        user_id = create_resp.json()["id"]

        response = client.put(
            f"/users/{user_id}",
            json={"role": "manager"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["role"] == "manager"

    def test_user_cannot_change_role(self, client: TestClient, monkeypatch_env: None, user_token: str) -> None:
        create_resp = client.post(
            "/users",
            json={
                "email": "regular@example.com",
                "password": "Secret123",
                "name": "Regular",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )
        user_id = create_resp.json()["id"]

        response = client.put(
            f"/users/{user_id}",
            json={"role": "manager"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403

    def test_user_can_update_own_email(self, client: TestClient, monkeypatch_env: None, user_token: str) -> None:
        # Get the user ID from /auth/me
        me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {user_token}"})
        assert me_resp.status_code == 200
        user_id = me_resp.json()["profile"]["user_id"]

        response = client.put(
            f"/users/{user_id}",
            json={"email": "updated@example.com"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "updated@example.com"

    def test_update_email_duplicate(self, client: TestClient, monkeypatch_env: None, admin_token: str) -> None:
        # Create two users
        client.post(
            "/users",
            json={
                "email": "first@example.com",
                "password": "Secret123",
                "name": "First",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )
        create2 = client.post(
            "/users",
            json={
                "email": "second@example.com",
                "password": "Secret123",
                "name": "Second",
                "phone": "+1 555 000 0001",
                "address": "Address 2",
            },
        )
        user2_id = create2.json()["id"]

        # Try to set second's email to first's email
        response = client.put(
            f"/users/{user2_id}",
            json={"email": "first@example.com"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 400
        assert "registrado" in response.json()["detail"]


class TestDeleteUser:
    def test_admin_can_delete_user(self, client: TestClient, monkeypatch_env: None, admin_token: str) -> None:
        create_resp = client.post(
            "/users",
            json={
                "email": "todelete@example.com",
                "password": "Secret123",
                "name": "Delete Me",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )
        user_id = create_resp.json()["id"]

        response = client.delete(
            f"/users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200

        # Verify user is gone
        get_resp = client.get(
            f"/users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert get_resp.status_code == 404

    def test_user_cannot_delete_other(self, client: TestClient, monkeypatch_env: None, user_token: str) -> None:
        create_resp = client.post(
            "/users",
            json={
                "email": "other2@example.com",
                "password": "Secret123",
                "name": "Other",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )
        user_id = create_resp.json()["id"]

        response = client.delete(
            f"/users/{user_id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403

    def test_delete_nonexistent_user(self, client: TestClient, monkeypatch_env: None, admin_token: str) -> None:
        response = client.delete(
            "/users/nonexistent-id",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404