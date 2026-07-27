from __future__ import annotations

import time
from datetime import timedelta

import pytest
from jose import jwt

from trackflow_api.auth import (
    ALGORITHM,
    create_access_token,
    get_access_token_expire_minutes,
    get_password_hash,
    get_secret_key,
    verify_password,
)


class TestGetSecretKey:
    def test_returns_env_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SECRET_KEY", "custom-key")
        assert get_secret_key() == "custom-key"

    def test_returns_default_when_not_set(self) -> None:
        assert get_secret_key() == "trackflow-dev-secret-key"


class TestGetAccessTokenExpireMinutes:
    def test_returns_env_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120")
        assert get_access_token_expire_minutes() == 120

    def test_returns_default_when_not_set(self) -> None:
        assert get_access_token_expire_minutes() == 30


class TestVerifyPassword:
    def test_correct_password_returns_true(self) -> None:
        hashed = get_password_hash("Secret123")
        assert verify_password("Secret123", hashed) is True

    def test_wrong_password_returns_false(self) -> None:
        hashed = get_password_hash("Secret123")
        assert verify_password("WrongPassword", hashed) is False

    def test_empty_password_against_hash_returns_false(self) -> None:
        hashed = get_password_hash("Secret123")
        assert verify_password("", hashed) is False

    def test_unicode_password(self) -> None:
        password = "contraseñaÑñ😀"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_special_characters(self) -> None:
        password = "P@$$w0rd!#$%&/()=?"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_very_long_password(self) -> None:
        password = "a" * 1000
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True


class TestGetPasswordHash:
    def test_hash_is_not_plaintext(self) -> None:
        hashed = get_password_hash("Secret123")
        assert hashed != "Secret123"

    def test_hash_is_deterministic_with_bcrypt(self) -> None:
        """Same password produces different hashes due to salt."""
        hash1 = get_password_hash("Secret123")
        hash2 = get_password_hash("Secret123")
        assert hash1 != hash2  # bcrypt uses different salt each time
        assert verify_password("Secret123", hash1) is True
        assert verify_password("Secret123", hash2) is True

    def test_min_length_password(self) -> None:
        hashed = get_password_hash("12345678")
        assert verify_password("12345678", hashed) is True

    def test_empty_password_hash_works(self) -> None:
        """Even empty strings should hash without error."""
        hashed = get_password_hash("")
        assert isinstance(hashed, str)
        assert len(hashed) > 0


class TestCreateAccessToken:
    def test_token_contains_subject(self) -> None:
        token = create_access_token("user-123")
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
        assert payload["sub"] == "user-123"

    def test_token_has_expiration(self) -> None:
        token = create_access_token("user-123")
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
        assert "exp" in payload

    def test_custom_expires_delta(self) -> None:
        token = create_access_token("user-123", expires_delta=timedelta(minutes=5))
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
        assert "exp" in payload

    def test_default_expires_delta_is_30_minutes(self) -> None:
        token = create_access_token("user-123")
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
        exp = payload["exp"]
        now = time.time()
        # Should be ~30 minutes from now
        assert 29 * 60 < exp - now < 31 * 60

    def test_different_subjects_produce_different_tokens(self) -> None:
        token1 = create_access_token("user-111")
        token2 = create_access_token("user-222")
        assert token1 != token2

    def test_token_with_different_secret_fails_decode(self) -> None:
        token = create_access_token("user-123")
        with pytest.raises(Exception):
            jwt.decode(token, "wrong-secret", algorithms=[ALGORITHM])