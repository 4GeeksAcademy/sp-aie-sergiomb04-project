"""TrackFlow MCP Server implementation with FastMCP and OAuth 2.1 via MCP Auth."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

# Ensure project root and services/api are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SERVICES_API_DIR = PROJECT_ROOT / "services" / "api"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SERVICES_API_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICES_API_DIR))

from mcps.trackflow_mcp.auth import (
    OAUTH_ISSUER,
    SUPPORTED_SCOPES,
    MCPBearerAuthMiddleware,
    build_auth_server_metadata,
    build_protected_resource_metadata,
    create_mcp_access_token,
    mcp_auth,
)
from mcps.trackflow_mcp.tools.incidents import manage_incidents as _manage_incidents_impl
from mcps.trackflow_mcp.tools.inventory import query_inventory as _query_inventory_impl

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("trackflow.mcp.server")

# ─── FastMCP Server Definition ────────────────────────────────────────────────

mcp = FastMCP(
    name="TrackFlow MCP Server",
    instructions=(
        "Servidor MCP oficial de TrackFlow Tech para operaciones logísticas, "
        "gestión de incidencias e inventario en almacenes de Los Ángeles y Zaragoza. "
        "Todas las llamadas requieren autenticación OAuth 2.1 Bearer Token con los scopes correspondientes."
    ),
)


@mcp.tool(
    name="manage_incidents",
    description=(
        "Gestiona incidencias y tickets en el Incidents Manager de TrackFlow (crear, consultar y actualizar estado). "
        "Las consultas requieren el scope 'incidents:read'. "
        "Las creaciones y cambios de estado requieren el scope 'incidents:write'. "
        "Los cambios de estado siguen estrictamente el ciclo de vida de TrackFlow: "
        "open -> [in_progress, discarded], in_progress -> [resolved, discarded]. "
        "Los estados 'resolved' y 'discarded' son terminales."
    ),
)
def manage_incidents(
    action: Literal["get", "create", "update_status", "list"],
    incident_id: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    category: Optional[str] = None,
    origin: Optional[str] = None,
    branch: Optional[str] = None,
    new_status: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """Herramienta de gestión de incidencias de TrackFlow.

    Args:
        action: Acción a ejecutar ('get', 'create', 'update_status', 'list').
        incident_id: Identificador del incidente (e.g. TRF-000001, UUID) para 'get' o 'update_status'.
        title: Título de la nueva incidencia (obligatorio para 'create').
        description: Descripción detallada de la incidencia (obligatorio para 'create').
        category: Categoría ('carrier_last_mile', 'carrier_international', 'warehouse_operations',
                  'reverse_logistics', 'customer_experience', 'commercial', 'technology', 'executive').
        origin: Origen del reporte ('customer', 'branch', 'internal').
        branch: Almacén/sucursal ('los_angeles' o 'zaragoza').
        new_status: Nuevo estado deseado para 'update_status' ('open', 'in_progress', 'resolved', 'discarded').
        status_filter: Filtro opcional por estado para la acción 'list'.
    """
    return _manage_incidents_impl(
        action=action,
        incident_id=incident_id,
        title=title,
        description=description,
        category=category,
        origin=origin,
        branch=branch,
        new_status=new_status,
        status_filter=status_filter,
    )


@mcp.tool(
    name="query_inventory",
    description=(
        "Consulta en tiempo real el catálogo de productos y existencias de stock en los almacenes de TrackFlow. "
        "Requiere el scope 'inventory:read'. "
        "SEGURIDAD Y POLÍTICA DE ACCESO: Esta herramienta es ESTRICTAMENTE DE SOLO LECTURA por diseño. "
        "Cualquier intento de modificación, inserción, actualización o mutación será explícitamente "
        "rechazado por el servidor con código de error INVENTORY_MUTATION_FORBIDDEN."
    ),
)
def query_inventory(
    query: str,
    warehouse: Optional[str] = None,
    action: str = "read",
    mutate: bool = False,
    quantity_change: Optional[int] = None,
) -> Dict[str, Any]:
    """Herramienta de consulta de inventario y stock de TrackFlow (Solo Lectura).

    Args:
        query: Nombre de producto, código SKU (e.g., 'CLT-SNK-W-42', 'TEC-EAR-001') o 'all'.
        warehouse: Filtro opcional por almacén ('LA' para Los Ángeles, 'ZGZ' para Zaragoza).
        action: Tipo de acción (debe ser 'read', 'get' o 'query'). Acciones de escritura son rechazadas.
        mutate: Flag de mutación (debe ser False).
        quantity_change: Parámetro prohibido. Si se suministra, la petición es rechazada inmediatamente.
    """
    return _query_inventory_impl(
        query=query,
        warehouse=warehouse,
        action=action,
        mutate=mutate,
        quantity_change=quantity_change,
    )


# ─── HTTP Endpoints & Starlette App ───────────────────────────────────────────

async def root_endpoint(request: Request) -> Response:
    """Server discovery root endpoint."""
    base_url = str(request.base_url).rstrip("/")
    return JSONResponse(
        {
            "server": "TrackFlow MCP Server",
            "version": "1.0.0",
            "protocol_version": "2024-11-05",
            "auth": {
                "type": "OAuth 2.1 / OIDC",
                "issuer": OAUTH_ISSUER,
                "supported_scopes": SUPPORTED_SCOPES,
            },
            "discovery": {
                "protected_resource_metadata": f"{base_url}/.well-known/oauth-protected-resource",
                "authorization_server_metadata": f"{base_url}/.well-known/oauth-authorization-server",
                "openid_configuration": f"{base_url}/.well-known/openid-configuration",
            },
            "transports": {
                "sse": f"{base_url}/sse",
                "streamable_http": f"{base_url}/mcp",
            },
        }
    )


async def protected_resource_metadata_endpoint(request: Request) -> Response:
    """RFC 9728 OAuth 2.0 Protected Resource Metadata."""
    base_url = str(request.base_url).rstrip("/")
    resource_url = f"{base_url}/mcp"
    data = build_protected_resource_metadata(resource_url)
    res = JSONResponse(data)
    res.headers["Access-Control-Allow-Origin"] = "*"
    return res


async def openid_configuration_endpoint(request: Request) -> Response:
    """OpenID Connect Discovery metadata."""
    meta = build_auth_server_metadata().model_dump(exclude_none=True)
    res = JSONResponse(meta)
    res.headers["Access-Control-Allow-Origin"] = "*"
    return res


async def token_endpoint(request: Request) -> Response:
    """OAuth 2.1 Token endpoint helper for testing, CLI and MCP Playground."""
    if request.method == "POST":
        content_type = request.headers.get("content-type", "")
        client_id = "trackflow-mcp-client"
        subject = "service-account"
        scopes = list(SUPPORTED_SCOPES)

        if "application/json" in content_type:
            try:
                body = await request.json()
                client_id = body.get("client_id", client_id)
                subject = body.get("subject", body.get("sub", subject))
                req_scope = body.get("scope") or body.get("scopes")
                if req_scope:
                    scopes = req_scope.split() if isinstance(req_scope, str) else req_scope
            except Exception:
                pass
        elif "application/x-www-form-urlencoded" in content_type:
            form = await request.form()
            client_id = str(form.get("client_id", client_id))
            subject = str(form.get("username", form.get("sub", subject)))
            req_scope = form.get("scope")
            if req_scope:
                scopes = str(req_scope).split()

        token = create_mcp_access_token(subject=subject, client_id=client_id, scopes=scopes)
        return JSONResponse(
            {
                "access_token": token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": " ".join(scopes),
            }
        )

    return JSONResponse({"error": "method_not_allowed"}, status_code=405)


async def health_endpoint(request: Request) -> Response:
    """Health status endpoint."""
    return JSONResponse({"status": "ok", "server": "TrackFlow MCP Server", "mcp_sdk": "FastMCP"})


def create_app() -> Starlette:
    """Build and configure the complete ASGI Starlette application with FastMCP and MCP Auth."""
    # FastMCP SSE app provides /sse and /messages endpoints
    fastmcp_sse_app = mcp.sse_app()
    fastmcp_http_app = mcp.streamable_http_app()

    routes = [
        Route("/", root_endpoint, methods=["GET", "OPTIONS"]),
        Route("/health", health_endpoint, methods=["GET", "OPTIONS"]),
        Route("/.well-known/oauth-protected-resource", protected_resource_metadata_endpoint, methods=["GET", "OPTIONS"]),
        Route("/.well-known/oauth-authorization-server", mcp_auth.metadata_endpoint(), methods=["GET", "OPTIONS"]),
        Route("/.well-known/openid-configuration", openid_configuration_endpoint, methods=["GET", "OPTIONS"]),
        Route("/oauth/token", token_endpoint, methods=["POST", "OPTIONS"]),
        # Mount FastMCP SSE routes directly
        Mount("/mcp", app=fastmcp_http_app),
        Mount("/", app=fastmcp_sse_app),
    ]

    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
            allow_credentials=True,
        ),
        Middleware(MCPBearerAuthMiddleware),
    ]

    app = Starlette(
        routes=routes,
        middleware=middleware,
    )
    return app


# Module-level ASGI app for uvicorn deployment
app = create_app()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", os.getenv("MCP_PORT", "8000")))
    host = os.getenv("HOST", "0.0.0.0")
    logger.info("Starting TrackFlow MCP Server on http://%s:%d", host, port)
    uvicorn.run("mcps.trackflow_mcp.server:app", host=host, port=port, reload=False)
