"""OAuth 2.1 authentication and authorization module for TrackFlow MCP Server using MCP Auth (mcpauth)."""

from __future__ import annotations

import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import jwt
from mcpauth import MCPAuth
from mcpauth.config import (
    AuthServerConfig,
    AuthServerType,
    AuthorizationServerMetadata,
    ServerMetadataPaths,
)
from mcpauth.exceptions import (
    BearerAuthExceptionCode,
    MCPAuthBearerAuthException,
    MCPAuthTokenVerificationException,
    MCPAuthTokenVerificationExceptionCode,
)
from mcpauth.types import AuthInfo
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Ensure project root and services/api are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SERVICES_API_DIR = PROJECT_ROOT / "services" / "api"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SERVICES_API_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICES_API_DIR))

logger = logging.getLogger("trackflow.mcp.auth")

DEFAULT_SECRET_KEY: str = "trackflow-dev-secret-key-32-bytes-secure!!"
OAUTH_ISSUER: str = os.getenv("TRACKFLOW_OAUTH_ISSUER", "https://auth.trackflow.tech")
OAUTH_AUDIENCE: str = os.getenv("TRACKFLOW_OAUTH_AUDIENCE", "https://api.trackflow.tech/mcp")
OAUTH_ALGORITHM: str = "HS256"

# TrackFlow Domain Scopes (Principle of Least Privilege)
SCOPE_INCIDENTS_READ = "incidents:read"
SCOPE_INCIDENTS_WRITE = "incidents:write"
SCOPE_INVENTORY_READ = "inventory:read"

SUPPORTED_SCOPES = [
    SCOPE_INCIDENTS_READ,
    SCOPE_INCIDENTS_WRITE,
    SCOPE_INVENTORY_READ,
]


def get_secret_key() -> str:
    """Return configured secret key with minimum 32-character requirement."""
    secret = os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY)
    if len(secret) < 32:
        return secret.ljust(32, "#")
    return secret


def build_auth_server_metadata() -> AuthorizationServerMetadata:
    """Build OAuth 2.1 RFC 8414 compliant Authorization Server Metadata."""
    return AuthorizationServerMetadata(
        issuer=OAUTH_ISSUER,
        authorization_endpoint=f"{OAUTH_ISSUER}/oauth/authorize",
        token_endpoint=f"{OAUTH_ISSUER}/oauth/token",
        jwks_uri=f"{OAUTH_ISSUER}/.well-known/jwks.json",
        registration_endpoint=f"{OAUTH_ISSUER}/oauth/register",
        response_types_supported=["code"],
        grant_types_supported=["authorization_code", "client_credentials"],
        code_challenge_methods_supported=["S256"],
        scopes_supported=SUPPORTED_SCOPES,
        token_endpoint_auth_methods_supported=["client_secret_basic", "client_secret_post", "none"],
        service_documentation="https://docs.trackflow.tech/api/oauth",
    )


def build_protected_resource_metadata(resource_url: str) -> Dict[str, Any]:
    """Build RFC 9728 OAuth 2.0 Protected Resource Metadata."""
    return {
        "resource": resource_url,
        "authorization_servers": [OAUTH_ISSUER],
        "scopes_supported": SUPPORTED_SCOPES,
        "bearer_methods_supported": ["header"],
        "resource_documentation": "https://docs.trackflow.tech/mcp",
    }


def verify_trackflow_jwt(token: str) -> AuthInfo:
    """Verify incoming Bearer JWT against TrackFlow OAuth 2.1 resource server config.

    Raises:
        MCPAuthTokenVerificationException on invalid or expired token.
    """
    secret = get_secret_key()
    try:
        decoded = jwt.decode(
            token,
            secret,
            algorithms=[OAUTH_ALGORITHM],
            options={"verify_aud": False, "verify_iss": False},
        )
        token_issuer = decoded.get("iss", OAUTH_ISSUER)
        client_id = decoded.get("client_id") or decoded.get("azp") or "trackflow-client"
        subject = decoded.get("sub", "anonymous")
        audience = decoded.get("aud", OAUTH_AUDIENCE)

        raw_scope = decoded.get("scope") or decoded.get("scopes") or ""
        if isinstance(raw_scope, str):
            scopes = [s.strip() for s in raw_scope.split() if s.strip()]
        elif isinstance(raw_scope, list):
            scopes = [str(s).strip() for s in raw_scope if str(s).strip()]
        else:
            scopes = []

        return AuthInfo(
            token=token,
            issuer=token_issuer,
            client_id=client_id,
            subject=subject,
            audience=audience,
            scopes=scopes,
            claims=decoded,
        )
    except jwt.ExpiredSignatureError as exc:
        logger.warning("Expired JWT token presented: %s", exc)
        raise MCPAuthTokenVerificationException(
            MCPAuthTokenVerificationExceptionCode.INVALID_TOKEN,
            cause=exc,
        )
    except Exception as exc:
        logger.warning("Failed to decode JWT token: %s", exc)
        raise MCPAuthTokenVerificationException(
            MCPAuthTokenVerificationExceptionCode.INVALID_TOKEN,
            cause=exc,
        )


def create_mcp_access_token(
    subject: str,
    client_id: str = "trackflow-mcp-agent",
    scopes: Optional[List[str]] = None,
    expires_in_minutes: int = 60,
    audience: str = OAUTH_AUDIENCE,
) -> str:
    """Generate a signed OAuth 2.1 Bearer access token for client consumption."""
    now = datetime.now(timezone.utc)
    effective_scopes = scopes if scopes is not None else list(SUPPORTED_SCOPES)
    payload: Dict[str, Any] = {
        "iss": OAUTH_ISSUER,
        "sub": subject,
        "aud": audience,
        "client_id": client_id,
        "scope": " ".join(effective_scopes),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_in_minutes)).timestamp()),
    }
    return jwt.encode(payload, get_secret_key(), algorithm=OAUTH_ALGORITHM)


# Initialize global MCPAuth instance
auth_server_config = AuthServerConfig(
    metadata=build_auth_server_metadata(),
    type=AuthServerType.OAUTH,
)
mcp_auth = MCPAuth(server=auth_server_config)


def get_current_auth_info() -> Optional[AuthInfo]:
    """Retrieve authenticated caller AuthInfo from context variable."""
    return mcp_auth.auth_info


def require_scope(required_scope: str, auth_info: Optional[AuthInfo] = None) -> AuthInfo:
    """Enforce specific required OAuth scope for tool execution.

    Raises:
        MCPAuthBearerAuthException if caller lacks the required scope or is unauthenticated.
    """
    info = auth_info or get_current_auth_info()
    if info is None:
        raise MCPAuthBearerAuthException(
            BearerAuthExceptionCode.MISSING_AUTH_HEADER
        )

    if required_scope not in info.scopes and "*" not in info.scopes:
        logger.warning(
            "Access denied: Subject '%s' (client '%s') lacks required scope '%s'. Granted: %s",
            info.subject,
            info.client_id,
            required_scope,
            info.scopes,
        )
        raise MCPAuthBearerAuthException(
            BearerAuthExceptionCode.MISSING_REQUIRED_SCOPES
        )

    return info


def log_tool_invocation(
    tool_name: str,
    auth_info: Optional[AuthInfo],
    success: bool,
    result_summary: str,
    duration_ms: float,
    error: Optional[str] = None,
) -> None:
    """Structured audit logging for every MCP tool invocation.

    Logs: Tool name, Client ID, Subject, Success flag, Result summary, Latency.
    """
    client_id = auth_info.client_id if auth_info else "unauthenticated"
    subject = auth_info.subject if auth_info else "anonymous"
    granted_scopes = auth_info.scopes if auth_info else []

    status_str = "SUCCESS" if success else "FAILED"
    logger.info(
        "[MCP_AUDIT] status=%s tool=%s client_id=%s subject=%s scopes=%s duration_ms=%.2f result='%s'%s",
        status_str,
        tool_name,
        client_id,
        subject,
        granted_scopes,
        duration_ms,
        result_summary[:120],
        f" error='{error}'" if error else "",
    )


class MCPBearerAuthMiddleware(BaseHTTPMiddleware):
    """Starlette middleware protecting MCP routes with OAuth 2.1 Bearer verification.

    Allows unauthenticated access to standard OAuth metadata and health discovery endpoints.
    """

    def __init__(self, app: Any, **kwargs: Any) -> None:
        super().__init__(app)
        self._auth_middleware_handler = mcp_auth.bearer_auth_middleware(
            mode_or_verify=verify_trackflow_jwt,
            show_error_details=True,
        )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Unauthenticated endpoints: Well-Known metadata, health, token issuance helper, root
        public_prefixes = (
            "/.well-known/",
            "/health",
            "/oauth/token",
            "/docs",
            "/openapi.json",
        )
        if request.method == "OPTIONS" or any(path.startswith(prefix) for prefix in public_prefixes) or path == "/":
            return await call_next(request)

        # Apply Bearer Auth verification via mcpauth middleware logic
        try:
            auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
            if not auth_header:
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "missing_auth_header",
                        "error_description": "Missing Authorization header. Please provide a valid Bearer token.",
                        "error_code": "AUTH_401_MISSING_HEADER",
                    },
                    headers={"WWW-Authenticate": 'Bearer error="invalid_token", resource="/mcp"'},
                )

            parts = auth_header.split(" ")
            if len(parts) != 2 or parts[0].lower() != "bearer":
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "invalid_auth_header_format",
                        "error_description": "Invalid Authorization header format. Expected 'Bearer <token>'.",
                        "error_code": "AUTH_401_INVALID_FORMAT",
                    },
                    headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
                )

            token = parts[1].strip()
            auth_info = verify_trackflow_jwt(token)
            mcp_auth._context_var.set(auth_info)

            # Continue request processing
            response = await call_next(request)
            return response

        except MCPAuthTokenVerificationException as exc:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "invalid_token",
                    "error_description": "The access token is invalid or has expired.",
                    "error_code": "AUTH_401_INVALID_TOKEN",
                    "details": str(exc),
                },
                headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
            )
        except MCPAuthBearerAuthException as exc:
            status_code = 403 if exc.code == BearerAuthExceptionCode.MISSING_REQUIRED_SCOPES else 401
            err_name = "insufficient_scope" if status_code == 403 else "unauthorized"
            return JSONResponse(
                status_code=status_code,
                content={
                    "error": err_name,
                    "error_description": str(exc),
                    "error_code": f"AUTH_{status_code}_{err_name.upper()}",
                },
                headers={"WWW-Authenticate": f'Bearer error="{err_name}"'},
            )
        except Exception as exc:
            logger.error("Unhandled exception in MCP Bearer Auth: %s", exc, exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "server_error",
                    "error_description": "Internal error verifying authentication credentials.",
                    "error_code": "AUTH_500_INTERNAL_ERROR",
                },
            )
