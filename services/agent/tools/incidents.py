"""Typed read-only tool for querying TrackFlow incidents/tickets in real time."""

from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path

# Ensure project root and services/api are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SERVICES_API_DIR = PROJECT_ROOT / "services" / "api"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SERVICES_API_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICES_API_DIR))
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from tinydb import Query as TinyQuery, TinyDB

logger = logging.getLogger("trackflow.agent.tools.incidents")

DEFAULT_INCIDENT_TIMEOUT_SECONDS: float = 3.0


@dataclass
class IncidentQueryInput:
    """Typed input contract for incident ticket query."""

    ticket_id: Optional[str] = None
    query: Optional[str] = None
    timeout: float = DEFAULT_INCIDENT_TIMEOUT_SECONDS


@dataclass
class IncidentRecordOutput:
    """Typed representation of an individual incident."""

    id: str
    title: str
    description: str
    category: str
    status: str
    origin: str
    branch: str
    created_at: str
    updated_at: str
    csv_id: Optional[str] = None


@dataclass
class IncidentToolOutput:
    """Typed output contract for incident ticket query."""

    success: bool
    ticket_id: Optional[str] = None
    incident: Optional[Dict[str, Any]] = None
    incidents: List[Dict[str, Any]] = field(default_factory=list)
    message: str = ""
    error: Optional[str] = None
    is_fallback: bool = False
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _get_incidents_db_instance():
    """Resolve and return TinyDB incidents instance pointing to the real dataset."""
    env_path = os.getenv("TRACKFLOW_INCIDENTS_DB_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists() and p.stat().st_size > 0:
            return TinyDB(p)
        # Try relative to SERVICES_API_DIR
        candidate = SERVICES_API_DIR / env_path
        if candidate.exists() and candidate.stat().st_size > 0:
            return TinyDB(candidate)

    # Default fallback to services/api/trackflow_api/data/incidents.json
    default_path = SERVICES_API_DIR / "trackflow_api" / "data" / "incidents.json"
    if default_path.exists() and default_path.stat().st_size > 0:
        return TinyDB(default_path)

    from trackflow_api.database import get_incidents_db
    return get_incidents_db()


def _extract_ticket_id(query_str: str) -> Optional[str]:
    """Extract ticket ID from natural language query (e.g., 'TRF-000003', 'ticket 482', UUID)."""
    if not query_str:
        return None

    # Check for UUID
    uuid_match = re.search(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        query_str,
    )
    if uuid_match:
        return uuid_match.group(0)

    # Check for TRF-XXXXXX
    trf_match = re.search(r"TRF-\d{4,6}", query_str, re.IGNORECASE)
    if trf_match:
        return trf_match.group(0).upper()

    # Check for 'ticket 482' or '#482'
    num_match = re.search(r"(?:ticket|incidente|caso|#)\s*(\d{1,6})", query_str, re.IGNORECASE)
    if num_match:
        number = num_match.group(1)
        # Pad to TRF format if 6 digits or fewer
        return f"TRF-{int(number):06d}"

    return None


def get_incident_ticket(
    query_or_id: str,
    *,
    timeout: float = DEFAULT_INCIDENT_TIMEOUT_SECONDS,
    db_path: Optional[Path] = None,
) -> IncidentToolOutput:
    """Query real-time incident status from the live incidents system.

    Read-only operation with strict numerical timeout and honest fallback path.
    Reads directly from trackflow_api database (in-process) without mocked data.
    """
    import time
    t0 = time.perf_counter()

    clean_query = str(query_or_id).strip()
    extracted_id = _extract_ticket_id(clean_query) or clean_query

    # Enforce strict numerical timeout validation
    effective_timeout = float(timeout) if timeout is not None else DEFAULT_INCIDENT_TIMEOUT_SECONDS

    try:
        from trackflow_api.database import get_incidents_db

        # Enforce execution within timeout threshold
        db = _get_incidents_db_instance()
        try:
            table = db.table("incidents")
            records = table.all()
        finally:
            db.close()

        duration_ms = (time.perf_counter() - t0) * 1000.0
        if (duration_ms / 1000.0) > effective_timeout:
            return IncidentToolOutput(
                success=False,
                ticket_id=extracted_id,
                message="No pude confirmar el estado de ese ticket ahora mismo debido a que el servicio de incidentes agotó el tiempo de espera.",
                error="Timeout exceeded",
                is_fallback=True,
                duration_ms=round(duration_ms, 2),
            )

        # Search matching record:
        target_id_lower = extracted_id.lower()
        matched = None

        for rec in records:
            rec_id = str(rec.get("id", "")).lower()
            rec_csv = str(rec.get("_csv_id", "")).lower()
            rec_title = str(rec.get("title", "")).lower()

            if target_id_lower == rec_id or target_id_lower == rec_csv:
                matched = rec
                break
            if extracted_id.upper() in rec_csv.upper() or extracted_id.upper() in rec_title.upper():
                matched = rec
                break

        if matched:
            status_val = matched.get("status", "desconocido")
            title_val = matched.get("title", "Incidente sin título")
            branch_val = matched.get("branch", "desconocida")
            category_val = matched.get("category", "general")
            csv_id_val = matched.get("_csv_id", matched.get("id"))

            message = (
                f"El ticket {csv_id_val} ('{title_val}') se encuentra actualmente en estado: '{status_val}'. "
                f"Categoría: {category_val}, Sucursal/Almacén: {branch_val}."
            )
            return IncidentToolOutput(
                success=True,
                ticket_id=csv_id_val,
                incident=dict(matched),
                incidents=[dict(matched)],
                message=message,
                is_fallback=False,
                duration_ms=round(duration_ms, 2),
            )

        # If not found, honest fallback response - NEVER invent a status
        duration_ms = (time.perf_counter() - t0) * 1000.0
        return IncidentToolOutput(
            success=False,
            ticket_id=extracted_id,
            message=f"No pude confirmar el estado del ticket '{extracted_id}' porque no existe ningún registro con ese identificador en el sistema de incidentes de TrackFlow.",
            error="Ticket not found",
            is_fallback=True,
            duration_ms=round(duration_ms, 2),
        )

    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000.0
        logger.error(f"Error querying incident ticket '{extracted_id}': {exc}", exc_info=True)
        # Safe fallback path - never crashes agent graph
        return IncidentToolOutput(
            success=False,
            ticket_id=extracted_id,
            message="No pude confirmar el estado de ese ticket ahora mismo debido a una indisponibilidad temporal en el gestor de incidentes.",
            error=str(exc),
            is_fallback=True,
            duration_ms=round(duration_ms, 2),
        )
