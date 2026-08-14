"""Telemetry stub router — receives frontend telemetry batches, validates and logs them.

This is a verification-only endpoint (no database persistence).
Persistence will be added in Fase 3 of the telemetry project.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

logger = logging.getLogger("trackflow_api.telemetry")

# Read the endpoint URL from env to establish the configuration pattern.
# In the stub phase this is informational only.
_TELEMETRY_ENDPOINT = os.getenv(
    "TELEMETRY_ENDPOINT", "http://localhost:8000/telemetry/events"
)


# ─── Pydantic models ──────────────────────────────────────────────────────────


class TelemetryEvent(BaseModel):
    """Standard telemetry event envelope as defined in the approved telemetry plan."""

    eventId: str = Field(..., description="UUID v4 unique event identifier")
    timestamp: str = Field(..., description="ISO 8601 UTC capture timestamp")
    sessionId: str = Field(..., description="User or technical session identifier")
    userId: str | None = Field(..., description="Authenticated user identifier or null")
    event_type: str = Field(..., description="Taxonomy entity_action")
    schemaVersion: str = Field(..., description="Explicit schema version, e.g. 1.0.0")
    requestId: str = Field(..., description="Frontend-backend-logs correlation ID")
    properties: dict[str, Any] = Field(
        ..., description="Event-specific fields (closed allowlist per event_type)"
    )


class TelemetryBatchRequest(BaseModel):
    """Wrapper for a batch of telemetry events."""

    events: list[TelemetryEvent]


class TelemetryBatchResponse(BaseModel):
    """Response acknowledging received events."""

    received: int


@router.options("/events", status_code=200)
async def options_telemetry_events() -> Response:
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


@router.post("/events", response_model=TelemetryBatchResponse, status_code=200)
async def receive_telemetry_events(
    batch: TelemetryBatchRequest,
) -> TelemetryBatchResponse:
    """Receive a batch of telemetry events, validate, log and acknowledge.

    This is a stub endpoint — it does NOT persist events to a database.
    """
    event_count = len(batch.events)
    event_types = [event.event_type for event in batch.events]

    logger.info(
        "telemetry_batch_received count=%d event_types=%s",
        event_count,
        event_types,
    )

    for event in batch.events:
        logger.info(
            "telemetry_event eventId=%s event_type=%s timestamp=%s sessionId=%s",
            event.eventId,
            event.event_type,
            event.timestamp,
            event.sessionId,
        )

    return TelemetryBatchResponse(received=event_count)
