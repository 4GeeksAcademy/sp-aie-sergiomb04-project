from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from trackflow_api.auth import create_access_token, get_password_hash
from trackflow_api.database import get_users_db


class TestLogin:
    def test_login_success(self, client: TestClient, monkeypatch_env: None) -> None:
        # Create user first
        client.post(
            "/users",
            json={
                "email": "user@example.com",
                "password": "Secret123",
                "name": "User",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )
        # Login
        response = client.post(
            "/auth/login",
            json={"email": "user@example.com", "password": "Secret123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_normalizes_email(self, client: TestClient, monkeypatch_env: None) -> None:
        client.post(
            "/users",
            json={
                "email": "user@example.com",
                "password": "Secret123",
                "name": "User",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )
        # Login with uppercase email
        response = client.post(
            "/auth/login",
            json={"email": "USER@EXAMPLE.COM", "password": "Secret123"},
        )
        assert response.status_code == 200

    def test_login_with_spaces_in_email(self, client: TestClient, monkeypatch_env: None) -> None:
        client.post(
            "/users",
            json={
                "email": "user@example.com",
                "password": "Secret123",
                "name": "User",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )
        # Login with spaces around email
        response = client.post(
            "/auth/login",
            json={"email": "  user@example.com  ", "password": "Secret123"},
        )
        assert response.status_code == 200

    def test_login_wrong_password(self, client: TestClient, monkeypatch_env: None) -> None:
        client.post(
            "/users",
            json={
                "email": "user@example.com",
                "password": "Secret123",
                "name": "User",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )
        response = client.post(
            "/auth/login",
            json={"email": "user@example.com", "password": "WrongPassword"},
        )
        assert response.status_code == 401
        data = response.json()
        assert "Credenciales invalidas" in str(data)

    def test_login_nonexistent_user(self, client: TestClient, monkeypatch_env: None) -> None:
        response = client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "Secret123"},
        )
        assert response.status_code == 401
        data = response.json()
        assert "Credenciales invalidas" in str(data)

    def test_login_inactive_user(self, client: TestClient, monkeypatch_env: None) -> None:
        # Create inactive user directly in DB
        db = get_users_db()
        db.table("users").insert(
            {
                "id": "inactive-1",
                "email": "inactive@example.com",
                "hashed_password": get_password_hash("Secret123"),
                "is_active": False,
                "role": "user",
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        )
        db.table("profiles").insert(
            {
                "id": "profile-inactive-1",
                "user_id": "inactive-1",
                "name": "Inactive",
                "phone": "+1 555 000 0000",
                "address": "Address",
            }
        )
        db.close()

        response = client.post(
            "/auth/login",
            json={"email": "inactive@example.com", "password": "Secret123"},
        )
        assert response.status_code == 403
        data = response.json()
        assert "inactivo" in str(data).lower()

    def test_login_empty_password(self, client: TestClient, monkeypatch_env: None) -> None:
        response = client.post(
            "/auth/login",
            json={"email": "user@example.com", "password": ""},
        )
        # Empty password fails validation before business logic
        assert response.status_code == 400


class TestAuthMe:
    def test_me_success(self, client: TestClient, monkeypatch_env: None) -> None:
        create_resp = client.post(
            "/users",
            json={
                "email": "user@example.com",
                "password": "Secret123",
                "name": "Test User",
                "phone": "+1 555 000 0000",
                "address": "Test Address",
            },
        )
        assert create_resp.status_code == 201

        login_resp = client.post(
            "/auth/login",
            json={"email": "user@example.com", "password": "Secret123"},
        )
        token = login_resp.json()["access_token"]

        response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "user@example.com"
        assert data["role"] == "user"
        assert data["profile"]["name"] == "Test User"

    def test_me_without_token(self, client: TestClient, monkeypatch_env: None) -> None:
        response = client.get("/auth/me")
        assert response.status_code == 401  # FastAPI returns 401 for missing Bearer

    def test_me_with_invalid_token(self, client: TestClient, monkeypatch_env: None) -> None:
        response = client.get("/auth/me", headers={"Authorization": "Bearer invalid-token"})
        assert response.status_code == 401

    def test_me_with_malformed_token(self, client: TestClient, monkeypatch_env: None) -> None:
        response = client.get("/auth/me", headers={"Authorization": "Bearer abc.def"})
        assert response.status_code == 401

    def test_me_with_expired_token(self, client: TestClient, monkeypatch_env: None) -> None:
        # Create a token that's already expired
        expired = create_access_token("some-user", expires_delta=timedelta(hours=-1))
        response = client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})
        assert response.status_code == 401

    def test_me_user_not_found_in_db(self, client: TestClient, monkeypatch_env: None) -> None:
        # Token for a user that doesn't exist in DB
        token = create_access_token("nonexistent-user-id")
        response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

    def test_me_inactive_user(self, client: TestClient, monkeypatch_env: None) -> None:
        # Create inactive user
        db = get_users_db()
        db.table("users").insert(
            {
                "id": "inactive-2",
                "email": "inactive2@example.com",
                "hashed_password": get_password_hash("Secret123"),
                "is_active": False,
                "role": "user",
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        )
        db.table("profiles").insert(
            {
                "id": "profile-inactive-2",
                "user_id": "inactive-2",
                "name": "Inactive",
                "phone": "+1 555 000 0000",
                "address": "Address",
            }
        )
        db.close()

        token = create_access_token("inactive-2")
        response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        # Inactive user gets 403 when accessing /auth/me
        assert response.status_code == 403


class TestForgotPassword:
    def test_forgot_password_existing_user(self, client: TestClient, monkeypatch_env: None) -> None:
        client.post(
            "/users",
            json={
                "email": "user@example.com",
                "password": "Secret123",
                "name": "User",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )
        response = client.post(
            "/auth/forgot-password",
            json={"email": "user@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "recibiras" in str(data["detail"]).lower()

    def test_forgot_password_nonexistent_user(self, client: TestClient, monkeypatch_env: None) -> None:
        """Should return same message to avoid user enumeration."""
        response = client.post(
            "/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "recibiras" in str(data["detail"]).lower()

    def test_forgot_password_multiple_times(self, client: TestClient, monkeypatch_env: None) -> None:
        """Multiple requests should not error."""
        client.post(
            "/users",
            json={
                "email": "user@example.com",
                "password": "Secret123",
                "name": "User",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )
        for _ in range(3):
            response = client.post(
                "/auth/forgot-password",
                json={"email": "user@example.com"},
            )
            assert response.status_code == 200


class TestResetPassword:
    def _create_reset_token_for(self, client: TestClient, email: str) -> str:
        """Helper: trigger forgot-password and extract the token from DB."""
        import hashlib

        from trackflow_api.repositories import get_password_reset_tokens_table

        client.post("/auth/forgot-password", json={"email": email})
        db = get_users_db()
        tokens = get_password_reset_tokens_table(db).all()
        db.close()
        if not tokens:
            pytest.fail("No reset token created")
        # We need the original token, but we only have the hash.
        # Instead, let's find the latest token record and return something useful
        return tokens[-1]

    def _extract_token_hash(self, client: TestClient, email: str) -> str:
        """Extract the latest token hash from DB for the given user."""
        from trackflow_api.repositories import get_password_reset_tokens_table

        client.post("/auth/forgot-password", json={"email": email})
        db = get_users_db()
        tokens = get_password_reset_tokens_table(db).all()
        db.close()
        if not tokens:
            pytest.fail("No reset token created")
        return tokens[-1]["token_hash"]

    def test_reset_password_success(self, client: TestClient, monkeypatch_env: None) -> None:
        client.post(
            "/users",
            json={
                "email": "user@example.com",
                "password": "Secret123",
                "name": "User",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )

        # Get the raw token from password_reset module
        import hashlib

        from trackflow_api.password_reset import create_password_reset_token, hash_password_reset_token
        from trackflow_api.repositories import get_password_reset_tokens_table

        # We need the original token to send it. The hash is stored.
        # We must send the UNHASHED token.
        raw_token = create_password_reset_token()
        token_hash = hash_password_reset_token(raw_token)

        # Insert the reset token record with known hash
        from datetime import datetime, timezone

        from trackflow_api.models import password_reset_token_record_from_create
        from trackflow_api.repositories import get_user_record_by_email

        db = get_users_db()
        user = get_user_record_by_email(db, "user@example.com")
        assert user is not None

        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        token_record = password_reset_token_record_from_create(
            user_id=user["id"],
            token_hash=token_hash,
            expires_at=expires_at,
        )
        get_password_reset_tokens_table(db).insert(token_record.model_dump(mode="json"))
        db.close()

        # Now reset password using the raw token
        response = client.post(
            "/auth/reset-password",
            json={"token": raw_token, "new_password": "NewPassword456"},
        )
        assert response.status_code == 200
        assert "updated" in response.json()["detail"].lower()

        # Verify new password works
        login_resp = client.post(
            "/auth/login",
            json={"email": "user@example.com", "password": "NewPassword456"},
        )
        assert login_resp.status_code == 200

    def test_reset_password_invalid_token(self, client: TestClient, monkeypatch_env: None) -> None:
        response = client.post(
            "/auth/reset-password",
            json={"token": "invalid-token-that-is-long-enough!!", "new_password": "NewPassword456"},
        )
        assert response.status_code == 400
        assert "Invalid token" in response.json()["detail"]

    def test_reset_password_short_token(self, client: TestClient, monkeypatch_env: None) -> None:
        response = client.post(
            "/auth/reset-password",
            json={"token": "short", "new_password": "NewPassword456"},
        )
        assert response.status_code == 400

    def test_reset_password_short_new_password(self, client: TestClient, monkeypatch_env: None) -> None:
        response = client.post(
            "/auth/reset-password",
            json={"token": "a" * 16, "new_password": "short"},
        )
        assert response.status_code == 400

    def test_reset_password_token_already_used(self, client: TestClient, monkeypatch_env: None) -> None:
        from datetime import datetime, timezone

        from trackflow_api.password_reset import create_password_reset_token, hash_password_reset_token
        from trackflow_api.repositories import get_password_reset_tokens_table

        client.post(
            "/users",
            json={
                "email": "user@example.com",
                "password": "Secret123",
                "name": "User",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )

        raw_token = create_password_reset_token()
        token_hash = hash_password_reset_token(raw_token)

        from trackflow_api.models import password_reset_token_record_from_create
        from trackflow_api.repositories import get_user_record_by_email

        db = get_users_db()
        user = get_user_record_by_email(db, "user@example.com")
        assert user is not None

        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        token_record = password_reset_token_record_from_create(
            user_id=user["id"],
            token_hash=token_hash,
            expires_at=expires_at,
        )
        get_password_reset_tokens_table(db).insert(token_record.model_dump(mode="json"))
        db.close()

        # First use - should succeed
        response1 = client.post(
            "/auth/reset-password",
            json={"token": raw_token, "new_password": "NewPassword456"},
        )
        assert response1.status_code == 200

        # Second use - should fail (token already used)
        response2 = client.post(
            "/auth/reset-password",
            json={"token": raw_token, "new_password": "AnotherPass789"},
        )
        assert response2.status_code == 400

    def test_reset_password_token_expired(self, client: TestClient, monkeypatch_env: None) -> None:
        from datetime import datetime, timezone

        from trackflow_api.password_reset import create_password_reset_token, hash_password_reset_token
        from trackflow_api.repositories import get_password_reset_tokens_table

        client.post(
            "/users",
            json={
                "email": "user@example.com",
                "password": "Secret123",
                "name": "User",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )

        raw_token = create_password_reset_token()
        token_hash = hash_password_reset_token(raw_token)

        from trackflow_api.models import password_reset_token_record_from_create
        from trackflow_api.repositories import get_user_record_by_email

        db = get_users_db()
        user = get_user_record_by_email(db, "user@example.com")
        assert user is not None

        # Token expired 1 hour ago
        expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        token_record = password_reset_token_record_from_create(
            user_id=user["id"],
            token_hash=token_hash,
            expires_at=expires_at,
        )
        get_password_reset_tokens_table(db).insert(token_record.model_dump(mode="json"))
        db.close()

        response = client.post(
            "/auth/reset-password",
            json={"token": raw_token, "new_password": "NewPassword456"},
        )
        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()


class TestChangePassword:
    def test_change_password_success(self, client: TestClient, monkeypatch_env: None) -> None:
        create_resp = client.post(
            "/users",
            json={
                "email": "user@example.com",
                "password": "Secret123",
                "name": "User",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )
        assert create_resp.status_code == 201

        login_resp = client.post(
            "/auth/login",
            json={"email": "user@example.com", "password": "Secret123"},
        )
        token = login_resp.json()["access_token"]

        response = client.post(
            "/auth/change-password",
            json={"current_password": "Secret123", "new_password": "NewPassword456"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert "changed" in response.json()["detail"].lower()

        # Verify new password works
        login_resp2 = client.post(
            "/auth/login",
            json={"email": "user@example.com", "password": "NewPassword456"},
        )
        assert login_resp2.status_code == 200

    def test_change_password_wrong_current(self, client: TestClient, monkeypatch_env: None) -> None:
        create_resp = client.post(
            "/users",
            json={
                "email": "user@example.com",
                "password": "Secret123",
                "name": "User",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )
        assert create_resp.status_code == 201

        login_resp = client.post(
            "/auth/login",
            json={"email": "user@example.com", "password": "Secret123"},
        )
        token = login_resp.json()["access_token"]

        response = client.post(
            "/auth/change-password",
            json={"current_password": "WrongPassword", "new_password": "NewPassword456"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "Current password is incorrect" in response.json()["detail"]

    def test_change_password_without_auth(self, client: TestClient, monkeypatch_env: None) -> None:
        response = client.post(
            "/auth/change-password",
            json={"current_password": "Secret123", "new_password": "NewPassword456"},
        )
        assert response.status_code == 401  # Missing Bearer token

    def test_change_password_short_new_password(self, client: TestClient, monkeypatch_env: None) -> None:
        create_resp = client.post(
            "/users",
            json={
                "email": "user@example.com",
                "password": "Secret123",
                "name": "User",
                "phone": "+1 555 000 0000",
                "address": "Address",
            },
        )
        assert create_resp.status_code == 201

        login_resp = client.post(
            "/auth/login",
            json={"email": "user@example.com", "password": "Secret123"},
        )
        token = login_resp.json()["access_token"]

        response = client.post(
            "/auth/change-password",
            json={"current_password": "Secret123", "new_password": "short"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400