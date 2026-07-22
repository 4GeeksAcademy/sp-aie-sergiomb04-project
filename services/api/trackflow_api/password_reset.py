from __future__ import annotations

import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib import error, request

RESEND_API_URL = "https://api.resend.com/emails"


def get_password_reset_expire_minutes() -> int:
    return int(os.getenv("PASSWORD_RESET_EXPIRE_MINUTES", "30"))


def get_password_reset_base_url() -> str:
    return os.getenv("PASSWORD_RESET_BASE_URL", "http://localhost:3000/reset-password")


def get_resend_api_key() -> str | None:
    value = os.getenv("RESEND_API_KEY")
    return value.strip() if value else None


def get_resend_from_email() -> str | None:
    value = os.getenv("RESEND_FROM_EMAIL")
    return value.strip() if value else None


def create_password_reset_token() -> str:
    return secrets.token_urlsafe(48)


def hash_password_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def build_password_reset_expiration() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=get_password_reset_expire_minutes())


def build_password_reset_url(token: str) -> str:
    base_url = get_password_reset_base_url().rstrip("/")
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}token={token}"


def send_password_reset_email(to_email: str, token: str) -> None:
    api_key = get_resend_api_key()
    from_email = get_resend_from_email()

    # Si el proveedor no esta configurado, no se rompe forgot-password para evitar enumeracion.
    if not api_key or not from_email:
                return

    reset_url = build_password_reset_url(token)
    expire_minutes = get_password_reset_expire_minutes()

    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": "Recupera tu contraseña de TrackFlow",
        "html": (
            "<div style='font-family:Arial,sans-serif;line-height:1.5;color:#111'>"
            "<h2>Recuperación de contraseña</h2>"
            "<p>Recibimos una solicitud para restablecer tu contraseña.</p>"
            f"<p><a href='{reset_url}' style='display:inline-block;padding:10px 14px;"
            "background:#0f172a;color:#fff;text-decoration:none;border-radius:6px'>"
            "Restablecer contraseña</a></p>"
            f"<p>Este enlace expira en {expire_minutes} minutos y solo se puede usar una vez.</p>"
            "<p>Si no solicitaste este cambio, puedes ignorar este correo.</p>"
            "</div>"
        ),
    }

    req = request.Request(
        RESEND_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=10):
            return
    except error.HTTPError:
        return
    except error.URLError:
        return
