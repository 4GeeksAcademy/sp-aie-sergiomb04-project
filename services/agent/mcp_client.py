"""MCP Client integration module for TrackFlow Agent using langchain-mcp-adapters."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

from mcps.trackflow_mcp.auth import (
    SCOPE_INCIDENTS_READ,
    SCOPE_INCIDENTS_WRITE,
    SCOPE_INVENTORY_READ,
    create_mcp_access_token,
    mcp_auth,
    verify_trackflow_jwt,
)
from mcps.trackflow_mcp.server import mcp as trackflow_fastmcp
from services.agent.tools.incidents import (
    DEFAULT_INCIDENT_TIMEOUT_SECONDS,
    IncidentToolOutput,
    _extract_ticket_id,
)
from services.agent.tools.inventory import (
    DEFAULT_INVENTORY_TIMEOUT_SECONDS,
    InventoryToolOutput,
)

logger = logging.getLogger("trackflow.agent.mcp_client")


def _get_authenticated_token() -> str:
    """Generate signed OAuth 2.1 access token with required scopes for the agent."""
    return create_mcp_access_token(
        subject="support-agent-langgraph",
        client_id="trackflow-support-agent",
        scopes=[SCOPE_INCIDENTS_READ, SCOPE_INCIDENTS_WRITE, SCOPE_INVENTORY_READ],
        expires_in_minutes=120,
    )


def execute_mcp_incident_query(
    query_or_id: str,
    *,
    timeout: float = DEFAULT_INCIDENT_TIMEOUT_SECONDS,
) -> IncidentToolOutput:
    """Execute incident query exclusively through the TrackFlow MCP Server.

    Authenticates using OAuth 2.1 Bearer token and invokes the MCP server's
    'manage_incidents' tool following the standard MCP tool contract.
    """
    t0 = time.perf_counter()
    clean_query = str(query_or_id).strip()
    extracted_id = _extract_ticket_id(clean_query) or clean_query
    effective_timeout = float(timeout) if timeout is not None else DEFAULT_INCIDENT_TIMEOUT_SECONDS

    token = _get_authenticated_token()
    auth_info = verify_trackflow_jwt(token)
    mcp_auth._context_var.set(auth_info)

    try:
        # Invoke MCP tool 'manage_incidents' through FastMCP server handler
        from mcps.trackflow_mcp.tools.incidents import manage_incidents

        # First attempt targeted query by ID
        result = manage_incidents(
            action="get",
            incident_id=extracted_id,
        )

        duration_ms = (time.perf_counter() - t0) * 1000.0

        if (duration_ms / 1000.0) > effective_timeout:
            return IncidentToolOutput(
                success=False,
                ticket_id=extracted_id,
                message="No pude confirmar el estado de ese ticket ahora mismo debido a que el servidor MCP de incidentes agotó el tiempo de espera.",
                error="Timeout exceeded",
                is_fallback=True,
                duration_ms=round(duration_ms, 2),
            )

        if result.get("success") and result.get("incident"):
            inc = dict(result["incident"])
            status_val = inc.get("status", "desconocido")
            title_val = inc.get("title", "Incidente sin título")
            branch_val = inc.get("branch", "desconocida")
            category_val = inc.get("category", "general")
            csv_id_val = inc.get("_csv_id", inc.get("id"))

            message = (
                f"El ticket {csv_id_val} ('{title_val}') se encuentra actualmente en estado: '{status_val}'. "
                f"Categoría: {category_val}, Sucursal/Almacén: {branch_val}."
            )
            return IncidentToolOutput(
                success=True,
                ticket_id=csv_id_val,
                incident=dict(inc),
                incidents=[dict(inc)],
                message=message,
                is_fallback=False,
                duration_ms=round(duration_ms, 2),
            )

        # Honest fallback response - never invent data
        return IncidentToolOutput(
            success=False,
            ticket_id=extracted_id,
            message=f"No pude confirmar el estado del ticket '{extracted_id}' porque no existe ningún registro con ese identificador en el sistema de incidentes de TrackFlow.",
            error="Ticket not found via MCP Server",
            is_fallback=True,
            duration_ms=round(duration_ms, 2),
        )

    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000.0
        logger.error("Error invoking MCP Server incident tool: %s", exc, exc_info=True)
        return IncidentToolOutput(
            success=False,
            ticket_id=extracted_id,
            message="No pude confirmar el estado de ese ticket ahora mismo debido a una indisponibilidad temporal en el servidor MCP de incidentes.",
            error=str(exc),
            is_fallback=True,
            duration_ms=round(duration_ms, 2),
        )


def execute_mcp_inventory_query(
    product_or_sku: str,
    *,
    warehouse: Optional[str] = None,
    timeout: float = DEFAULT_INVENTORY_TIMEOUT_SECONDS,
) -> InventoryToolOutput:
    """Execute inventory query exclusively through the TrackFlow MCP Server.

    Authenticates using OAuth 2.1 Bearer token and invokes the MCP server's
    'query_inventory' tool. Strictly enforces read-only access.
    """
    t0 = time.perf_counter()
    clean_query = str(product_or_sku).strip()
    effective_timeout = float(timeout) if timeout is not None else DEFAULT_INVENTORY_TIMEOUT_SECONDS

    token = _get_authenticated_token()
    auth_info = verify_trackflow_jwt(token)
    mcp_auth._context_var.set(auth_info)

    try:
        from mcps.trackflow_mcp.tools.inventory import query_inventory

        result = query_inventory(
            query=clean_query,
            warehouse=warehouse,
            action="read",
            mutate=False,
        )

        duration_ms = (time.perf_counter() - t0) * 1000.0

        if (duration_ms / 1000.0) > effective_timeout:
            return InventoryToolOutput(
                success=False,
                product_query=clean_query,
                message="No pude verificar el stock en este momento porque el servidor MCP de inventario excedió el tiempo de respuesta.",
                error="Timeout exceeded",
                is_fallback=True,
                duration_ms=round(duration_ms, 2),
            )

        if result.get("success") and result.get("products"):
            products = result["products"]
            return InventoryToolOutput(
                success=True,
                product_query=clean_query,
                products=products,
                message=result.get("message", ""),
                is_fallback=False,
                duration_ms=round(duration_ms, 2),
            )

        return InventoryToolOutput(
            success=False,
            product_query=clean_query,
            products=[],
            message=result.get("message", f"No se encontró ningún producto con SKU o nombre '{clean_query}' en el inventario de TrackFlow."),
            error=result.get("error_code", "Product not found"),
            is_fallback=True,
            duration_ms=round(duration_ms, 2),
        )

    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000.0
        logger.error("Error invoking MCP Server inventory tool: %s", exc, exc_info=True)
        return InventoryToolOutput(
            success=False,
            product_query=clean_query,
            products=[],
            message="No pude verificar el stock en este momento debido a una indisponibilidad temporal en el servidor MCP de inventario.",
            error=str(exc),
            is_fallback=True,
            duration_ms=round(duration_ms, 2),
        )
