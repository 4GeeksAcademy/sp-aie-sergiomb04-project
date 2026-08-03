from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

import pytest

from trackflow_api.password_reset import (
    build_password_reset_expiration,
    build_password_reset_url,
    create_password_reset_token,
    get_password_reset_base_url,
    get_password_reset_expire_minutes,
    get_resend_api_key,
    get_resend_from_email,
    hash_password_reset_token,
    send_password_reset_email,
)


class TestGetPasswordResetExpireMinutes:
    def test_returns_env_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PASSWORD_RESET_EXPIRE_MINUTES", "60")
        assert get_password_reset_expire_minutes() == 60

    def test_returns_default_when_not_set(self) -> None:
        assert get_password_reset_expire_minutes() == 30


class TestGetPasswordResetBaseUrl:
    def test_returns_env_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PASSWORD_RESET_BASE_URL", "https://example.com/reset")
        assert get_password_reset_base_url() == "https://example.com/reset"

    def test_returns_default_when_not_set(self) -> None:
        assert get_password_reset_base_url() == "http://localhost:3000/reset-password"


class TestGetResendApiKey:
    def test_returns_env_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RESEND_API_KEY", "re_abc123")
        assert get_resend_api_key() == "re_abc123"

    def test_returns_none_when_not_set(self) -> None:
        assert get_resend_api_key() is None

    def test_strips_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RESEND_API_KEY", "  re_abc123  ")
        assert get_resend_api_key() == "re_abc123"


class TestGetResendFromEmail:
    def test_returns_env_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RESEND_FROM_EMAIL", "noreply@trackflow.test")
        assert get_resend_from_email() == "noreply@trackflow.test"

    def test_returns_none_when_not_set(self) -> None:
        assert get_resend_from_email() is None

    def test_strips_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RESEND_FROM_EMAIL", "  test@test.com  ")
        assert get_resend_from_email() == "test@test.com"


class TestCreatePasswordResetToken:
    def test_token_is_generated(self) -> None:
        token = create_password_reset_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_is_urlsafe(self) -> None:
        token = create_password_reset_token()
        # URLsafe base64: alphanumeric plus - and _
        import string
        allowed = set(string.ascii_letters + string.digits + "-_")
        assert all(c in allowed for c in token)

    def test_consecutive_tokens_are_different(self) -> None:
        token1 = create_password_reset_token()
        token2 = create_password_reset_token()
        assert token1 != token2

    def test_token_length(self) -> None:
        token = create_password_reset_token()
        # token_urlsafe(48) produces 64 characters
        assert len(token) == 64


class TestHashPasswordResetToken:
    def test_hash_is_sha256(self) -> None:
        token = "test-token-value"
        expected = hashlib.sha256(token.encode("utf-8")).hexdigest()
        assert hash_password_reset_token(token) == expected

    def test_hash_is_deterministic(self) -> None:
        token = "my-reset-token"
        assert hash_password_reset_token(token) == hash_password_reset_token(token)

    def test_different_tokens_produce_different_hashes(self) -> None:
        assert hash_password_reset_token("token-a") != hash_password_reset_token("token-b")


class TestBuildPasswordResetExpiration:
    def test_expiration_is_in_future(self) -> None:
        exp = build_password_reset_expiration()
        assert exp > datetime.now(timezone.utc)

    def test_expiration_is_30_minutes_by_default(self) -> None:
        exp = build_password_reset_expiration()
        now = datetime.now(timezone.utc)
        diff = exp - now
        assert timedelta(minutes=29) < diff < timedelta(minutes=31)

    def test_expiration_uses_env_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PASSWORD_RESET_EXPIRE_MINUTES", "5")
        exp = build_password_reset_expiration()
        now = datetime.now(timezone.utc)
        diff = exp - now
        assert timedelta(minutes=4) < diff < timedelta(minutes=6)


class TestBuildPasswordResetUrl:
    def test_url_with_query_params(self) -> None:
        url = build_password_reset_url("abc123")
        assert "token=abc123" in url

    def test_url_with_existing_query_params(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PASSWORD_RESET_BASE_URL", "https://example.com/reset?lang=es")
        url = build_password_reset_url("abc123")
        assert "lang=es" in url
        assert "&token=abc123" in url

    def test_url_with_base_url_no_trailing_slash(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PASSWORD_RESET_BASE_URL", "https://example.com/reset")
        url = build_password_reset_url("abc123")
        assert url == "https://example.com/reset?token=abc123"


class TestSendPasswordResetEmail:
    def test_no_api_key_does_not_raise(self) -> None:
        """Should silently return if API key is not configured."""
        send_password_reset_email("test@example.com", "some-token")

    def test_no_from_email_does_not_raise(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RESEND_API_KEY", "re_abc123")
        send_password_reset_email("test@example.com", "some-token")