from __future__ import annotations

from fastapi.testclient import TestClient


class TestGetMyProfile:
    def test_get_profile_success(self, client: TestClient, monkeypatch_env: None, user_token: str) -> None:
        response = client.get(
            "/profiles/me",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test User"
        assert data["phone"] == "+1 555 000 0000"
        assert data["address"] == "Test Address"
        assert "user_id" in data

    def test_get_profile_without_auth(self, client: TestClient, monkeypatch_env: None) -> None:
        response = client.get("/profiles/me")
        assert response.status_code == 401

    def test_get_profile_with_invalid_token(self, client: TestClient, monkeypatch_env: None) -> None:
        response = client.get(
            "/profiles/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401


class TestUpdateMyProfile:
    def test_update_profile_success(self, client: TestClient, monkeypatch_env: None, user_token: str) -> None:
        response = client.put(
            "/profiles/me",
            json={
                "name": "Updated Name",
                "phone": "+1 555 999 9999",
                "address": "Updated Address 42",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["phone"] == "+1 555 999 9999"
        assert data["address"] == "Updated Address 42"

    def test_update_profile_empty_name(self, client: TestClient, monkeypatch_env: None, user_token: str) -> None:
        response = client.put(
            "/profiles/me",
            json={
                "name": "",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 400

    def test_update_profile_without_auth(self, client: TestClient, monkeypatch_env: None) -> None:
        response = client.put(
            "/profiles/me",
            json={
                "name": "No Auth",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )
        assert response.status_code == 401

    def test_update_profile_whitespace_stripping(self, client: TestClient, monkeypatch_env: None, user_token: str) -> None:
        response = client.put(
            "/profiles/me",
            json={
                "name": "  Spaced Name  ",
                "phone": "  +1 555 000 0000  ",
                "address": "  Spaced Address  ",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Spaced Name"
        assert data["phone"] == "+1 555 000 0000"
        assert data["address"] == "Spaced Address"