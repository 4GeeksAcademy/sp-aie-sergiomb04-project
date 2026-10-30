"""Strict secret loading for TrackFlow services (NIST Protect - Gestión de Secretos).

Secrets (JWT signing keys, carrier API keys, webhook secrets) MUST come from the
process environment (`.env` loaded by docker-compose / a vault agent). No literal
fallback secret is allowed in source code.

Behaviour:
- If the variable is set, it is returned (and validated for minimum length).
- If it is missing in a production-like environment (`TRACKFLOW_ENV` in
  `production`/`prod`/`staging`), a `MissingSecretError` is raised (fail closed).
- If it is missing in local development/tests, an ephemeral random secret is
  generated once per process and a warning is logged. Tokens signed with it are
  invalidated on restart, which is acceptable for dev and never leaks a shared key.
"""

from __future__ import annotations

import logging
import os
import secrets
import threading
from typing import Dict

logger = logging.getLogger("trackflow.security.secrets")

PRODUCTION_ENVIRONMENTS = frozenset({"production", "prod", "staging"})

_ephemeral_secrets: Dict[str, str] = {}
_lock = threading.Lock()


class MissingSecretError(RuntimeError):
    """Raised when a mandatory secret is not configured in a production environment."""


def current_environment() -> str:
    """Return normalized deployment environment name (defaults to `development`)."""
    return os.getenv("TRACKFLOW_ENV", "development").strip().lower() or "development"


def is_production_environment() -> bool:
    """Return True when running in an environment that must fail closed on missing secrets."""
    return current_environment() in PRODUCTION_ENVIRONMENTS


def get_required_secret(name: str, *, min_length: int = 16) -> str:
    """Load a mandatory secret strictly from the environment.

    Args:
        name: Environment variable name (e.g. `SECRET_KEY`).
        min_length: Minimum accepted length; shorter values are rejected in production.

    Raises:
        MissingSecretError: if missing/too short in a production-like environment.
    """
    value = os.getenv(name)
    if value is not None and value.strip():
        value = value.strip()
        if len(value) < min_length:
            if is_production_environment():
                raise MissingSecretError(
                    f"El secreto '{name}' no cumple la longitud mínima ({min_length}) exigida en producción."
                )
            logger.warning(
                "[SECRETS] secret=%s length_below_minimum=%d env=%s",
                name,
                min_length,
                current_environment(),
            )
        return value

    if is_production_environment():
        raise MissingSecretError(
            f"El secreto obligatorio '{name}' no está configurado. "
            "Defínelo vía variables de entorno o vault antes de arrancar el servicio."
        )

    with _lock:
        if name not in _ephemeral_secrets:
            _ephemeral_secrets[name] = secrets.token_urlsafe(48)
            logger.warning(
                "[SECRETS] secret=%s missing env=%s -> using ephemeral per-process value "
                "(configure it in .env to persist sessions)",
                name,
                current_environment(),
            )
        return _ephemeral_secrets[name]


def reset_ephemeral_secrets() -> None:
    """Clear cached ephemeral secrets (test helper)."""
    with _lock:
        _ephemeral_secrets.clear()
