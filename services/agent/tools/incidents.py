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
    """[DEPRECATED] Query real-time incident status.

    DEPRECATION NOTICE:
    Direct invocations to Incidents Manager database are deprecated.
    All incident operations are now routed exclusively through TrackFlow MCP Server
    with OAuth 2.1 authentication and scope verification.
    """
    logger.info("get_incident_ticket: Delegating to TrackFlow MCP Server client...")
    from services.agent.mcp_client import execute_mcp_incident_query
    return execute_mcp_incident_query(query_or_id, timeout=timeout)

