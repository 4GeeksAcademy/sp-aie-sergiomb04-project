"""Incident management tool for TrackFlow MCP Server with lifecycle status enforcement."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from tinydb import Query as TinyQuery, TinyDB

from mcps.trackflow_mcp.auth import (
    SCOPE_INCIDENTS_READ,
    SCOPE_INCIDENTS_WRITE,
    get_current_auth_info,
    log_tool_invocation,
    require_scope,
)
from trackflow_api.database import get_incidents_db
from trackflow_api.models import (
    INCIDENT_BRANCHES,
    INCIDENT_CATEGORIES,
    STATUS_TRANSITIONS,
    Incident,
    IncidentCreate,
    IncidentOriginEnum,
    IncidentStatusEnum,
    IncidentStatusUpdate,
    incident_record_from_create,
)

logger = logging.getLogger("trackflow.mcp.tools.incidents")
_INCIDENT_QUERY = TinyQuery()


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SERVICES_API_DIR = PROJECT_ROOT / "services" / "api"


def _get_incidents_db_instance():
    """Resolve and return TinyDB incidents instance pointing to the real dataset."""
    env_path = os.getenv("TRACKFLOW_INCIDENTS_DB_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists() and p.stat().st_size > 0:
            return TinyDB(p)
        candidate = SERVICES_API_DIR / env_path
        if candidate.exists() and candidate.stat().st_size > 0:
            return TinyDB(candidate)

    default_path = SERVICES_API_DIR / "trackflow_api" / "data" / "incidents.json"
    if default_path.exists() and default_path.stat().st_size > 0:
        return TinyDB(default_path)

    return get_incidents_db()


def _extract_id(query_str: Optional[str]) -> Optional[str]:
    """Helper to extract ticket ID from string."""
    if not query_str:
        return None
    clean = query_str.strip()
    return clean


def manage_incidents(
    action: Literal["get", "create", "update_status", "list"],
    *,
    incident_id: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    category: Optional[str] = None,
    origin: Optional[str] = None,
    branch: Optional[str] = None,
    new_status: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """Manage TrackFlow Incidents Manager tickets (Create, Update Status, Query).

    Enforces OAuth scopes ('incidents:read' for queries, 'incidents:write' for mutations)
    and strictly enforces the company's lifecycle status transitions:
    - 'open' -> ['in_progress', 'discarded']
    - 'in_progress' -> ['resolved', 'discarded']
    - 'resolved' / 'discarded' -> terminal states (no further transitions).

    Args:
        action: Operation to perform ('get', 'create', 'update_status', 'list').
        incident_id: Target incident ID (e.g. TRF-000001, UUID) for 'get' or 'update_status'.
        title: Title for new incident (required for 'create').
        description: Detailed explanation for new incident (required for 'create').
        category: Category for new incident. Must be one of:
                  'carrier_last_mile', 'carrier_international', 'warehouse_operations',
                  'reverse_logistics', 'customer_experience', 'commercial', 'technology', 'executive'.
        origin: Source of incident ('customer', 'branch', 'internal').
        branch: Operating facility ('los_angeles' or 'zaragoza').
        new_status: Target status for 'update_status' ('open', 'in_progress', 'resolved', 'discarded').
        status_filter: Optional status filter for 'list' action.

    Returns:
        Structured response containing success status, incident details, message, and audit metadata.
    """
    t0 = time.perf_counter()
    auth_info = get_current_auth_info()

    try:
        # 1. Enforce Scope & Permissions
        if action in ("get", "list"):
            require_scope(SCOPE_INCIDENTS_READ, auth_info)
        elif action in ("create", "update_status"):
            require_scope(SCOPE_INCIDENTS_WRITE, auth_info)
        else:
            raise ValueError(f"Acción '{action}' no reconocida. Use 'get', 'create', 'update_status' o 'list'.")

        db = _get_incidents_db_instance()
        table = db.table("incidents")

        # ── ACTION: CREATE ────────────────────────────────────────────────────────
        if action == "create":
            if not title or not title.strip():
                raise ValueError("El campo 'title' es obligatorio para crear una incidencia.")
            if not description or not description.strip():
                raise ValueError("El campo 'description' es obligatorio para crear una incidencia.")
            if not category or category not in INCIDENT_CATEGORIES:
                raise ValueError(
                    f"Categoría '{category}' inválida. Valores permitidos: {', '.join(INCIDENT_CATEGORIES)}"
                )
            if not origin or origin not in [e.value for e in IncidentOriginEnum]:
                raise ValueError(
                    f"Origen '{origin}' inválido. Valores permitidos: {[e.value for e in IncidentOriginEnum]}"
                )
            if not branch or branch not in INCIDENT_BRANCHES:
                raise ValueError(
                    f"Sede '{branch}' inválida. Valores permitidos: {', '.join(INCIDENT_BRANCHES)}"
                )

            payload = IncidentCreate(
                title=title.strip(),
                description=description.strip(),
                category=category,
                origin=IncidentOriginEnum(origin),
                branch=branch,
                status=IncidentStatusEnum.OPEN,
            )
            incident_obj = incident_record_from_create(payload)
            table.insert(incident_obj.model_dump(mode="json"))
            db.close()

            duration_ms = (time.perf_counter() - t0) * 1000.0
            msg = f"Incidencia creada exitosamente con ID '{incident_obj.id}' y estado 'open'."
            log_tool_invocation("manage_incidents.create", auth_info, True, msg, duration_ms)

            return {
                "success": True,
                "action": "create",
                "incident": incident_obj.model_dump(mode="json"),
                "message": msg,
                "duration_ms": round(duration_ms, 2),
            }

        # ── ACTION: GET ───────────────────────────────────────────────────────────
        if action == "get":
            target_id = _extract_id(incident_id)
            if not target_id:
                raise ValueError("Debe proporcionar 'incident_id' para la acción 'get'.")

            records = table.all()
            db.close()

            matched = None
            target_lower = target_id.lower()
            for r in records:
                r_id = str(r.get("id", "")).lower()
                r_csv = str(r.get("_csv_id", "")).lower()
                r_title = str(r.get("title", "")).lower()
                if target_lower == r_id or target_lower == r_csv:
                    matched = r
                    break
                if target_id.upper() in r_csv.upper() or target_id.upper() in r_title.upper():
                    matched = r
                    break

            duration_ms = (time.perf_counter() - t0) * 1000.0
            if matched:
                msg = f"Incidencia '{matched.get('id')}' encontrada en estado '{matched.get('status')}'."
                log_tool_invocation("manage_incidents.get", auth_info, True, msg, duration_ms)
                return {
                    "success": True,
                    "action": "get",
                    "incident": dict(matched),
                    "message": msg,
                    "duration_ms": round(duration_ms, 2),
                }

            msg = f"No se encontró ninguna incidencia con identificador '{target_id}'."
            log_tool_invocation("manage_incidents.get", auth_info, False, msg, duration_ms)
            return {
                "success": False,
                "action": "get",
                "incident": None,
                "error_code": "INCIDENT_NOT_FOUND",
                "message": msg,
                "duration_ms": round(duration_ms, 2),
            }

        # ── ACTION: UPDATE_STATUS (LIFECYCLE TRANSITION) ──────────────────────────
        if action == "update_status":
            target_id = _extract_id(incident_id)
            if not target_id:
                raise ValueError("Debe proporcionar 'incident_id' para actualizar el estado.")
            if not new_status:
                raise ValueError("Debe proporcionar 'new_status' para actualizar el estado.")

            try:
                target_status_enum = IncidentStatusEnum(new_status)
            except ValueError:
                valid_statuses = [s.value for s in IncidentStatusEnum]
                raise ValueError(
                    f"Estado '{new_status}' inválido. Estados permitidos: {valid_statuses}"
                )

            records = table.all()
            matched = None
            target_lower = target_id.lower()
            for r in records:
                r_id = str(r.get("id", "")).lower()
                r_csv = str(r.get("_csv_id", "")).lower()
                if target_lower == r_id or target_lower == r_csv:
                    matched = r
                    break

            if not matched:
                db.close()
                duration_ms = (time.perf_counter() - t0) * 1000.0
                msg = f"No se encontró la incidencia '{target_id}' para actualizar su estado."
                log_tool_invocation("manage_incidents.update_status", auth_info, False, msg, duration_ms)
                return {
                    "success": False,
                    "action": "update_status",
                    "error_code": "INCIDENT_NOT_FOUND",
                    "message": msg,
                    "duration_ms": round(duration_ms, 2),
                }

            current_status = IncidentStatusEnum(matched["status"])
            allowed_transitions = STATUS_TRANSITIONS.get(current_status, [])

            if target_status_enum not in allowed_transitions:
                db.close()
                duration_ms = (time.perf_counter() - t0) * 1000.0
                err_msg = (
                    f"Transición no permitida: no se puede cambiar de '{current_status.value}' a '{target_status_enum.value}'. "
                    f"Transiciones válidas desde '{current_status.value}': {[s.value for s in allowed_transitions]}"
                )
                log_tool_invocation(
                    "manage_incidents.update_status", auth_info, False, err_msg, duration_ms, error="INVALID_STATUS_TRANSITION"
                )
                return {
                    "success": False,
                    "action": "update_status",
                    "error_code": "INVALID_STATUS_TRANSITION",
                    "current_status": current_status.value,
                    "target_status": target_status_enum.value,
                    "allowed_transitions": [s.value for s in allowed_transitions],
                    "message": err_msg,
                    "duration_ms": round(duration_ms, 2),
                }

            # Apply atomic status update
            now_iso = datetime.now(timezone.utc).isoformat()
            table.update(
                {"status": target_status_enum.value, "updated_at": now_iso},
                _INCIDENT_QUERY.id == matched["id"],
            )
            updated_record = table.get(_INCIDENT_QUERY.id == matched["id"])
            db.close()

            duration_ms = (time.perf_counter() - t0) * 1000.0
            success_msg = f"Estado de la incidencia '{matched['id']}' actualizado de '{current_status.value}' a '{target_status_enum.value}'."
            log_tool_invocation("manage_incidents.update_status", auth_info, True, success_msg, duration_ms)

            return {
                "success": True,
                "action": "update_status",
                "incident": dict(updated_record) if updated_record else None,
                "previous_status": current_status.value,
                "current_status": target_status_enum.value,
                "message": success_msg,
                "duration_ms": round(duration_ms, 2),
            }

        # ── ACTION: LIST ──────────────────────────────────────────────────────────
        if action == "list":
            records = table.all()
            db.close()

            if status_filter:
                records = [r for r in records if r.get("status") == status_filter]

            clean_records = [dict(r) for r in records]
            duration_ms = (time.perf_counter() - t0) * 1000.0
            msg = f"Se obtuvieron {len(clean_records)} incidencias."
            log_tool_invocation("manage_incidents.list", auth_info, True, msg, duration_ms)

            return {
                "success": True,
                "action": "list",
                "total": len(clean_records),
                "incidents": clean_records,
                "message": msg,
                "duration_ms": round(duration_ms, 2),
            }

    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000.0
        err_type = type(exc).__name__
        err_msg = str(exc)
        logger.error("Error executing manage_incidents action=%s: %s", action, err_msg, exc_info=True)
        log_tool_invocation("manage_incidents", auth_info, False, err_msg, duration_ms, error=err_type)

        return {
            "success": False,
            "action": action,
            "error_code": "INCIDENT_TOOL_ERROR" if err_type != "ValueError" else "VALIDATION_ERROR",
            "error": err_msg,
            "message": f"Error ejecutando acción '{action}' en Incidents Manager: {err_msg}",
            "duration_ms": round(duration_ms, 2),
        }
