"""Telemetry router — receives frontend telemetry batches, validates and persists them to the database."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, ValidationError
from sqlmodel import Session

from trackflow_api.cache import api_cache
from trackflow_api.database import get_db, get_inventory_engine
from trackflow_api.models import TelemetryEventRecord
from trackflow_api.telemetry.analysis import (
    _to_iso_utc,
    generate_telemetry_report,
)

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

logger = logging.getLogger("trackflow_api.telemetry")

_TELEMETRY_ENDPOINT = os.getenv(
    "TELEMETRY_ENDPOINT", "http://localhost:8000/telemetry/events"
)

# ─── Property Allowlists per Event Type ───────────────────────────────────────

EVENT_ALLOWLIST: dict[str, set[str]] = {
    "inbound_order_created": {
        "warehouse",
        "client_id",
        "product_id",
        "product_category",
        "quantity",
        "order_id",
        "reference",
        "user_uuid",
    },
    "outbound_order_created": {
        "warehouse",
        "client_id",
        "product_id",
        "product_category",
        "quantity",
        "order_id",
        "exit_type",
        "tracking_number_present",
        "user_uuid",
    },
    "stock_threshold_triggered": {
        "warehouse",
        "client_id",
        "product_id",
        "product_category",
        "quantity",
        "minimum_threshold",
        "deficit_units",
    },
    "direct_stock_edit_rejected": {
        "warehouse",
        "client_id",
        "product_id",
        "product_category",
        "quantity",
        "attempted_action",
        "rejection_reason",
        "user_uuid",
    },
    "inventory_discrepancy_detected": {
        "warehouse",
        "client_id",
        "product_id",
        "product_category",
        "quantity",
        "physical_count",
        "system_count",
        "discrepancy_units",
        "audit_id",
    },
    "outbound_order_rejected_insufficient_stock": {
        "warehouse",
        "client_id",
        "product_id",
        "product_category",
        "quantity",
        "available_stock",
        "requested_quantity",
        "user_uuid",
        "rejection_reason",
    },
    "inventory_order_rejected_warehouse_mismatch": {
        "warehouse",
        "client_id",
        "product_id",
        "product_category",
        "quantity",
        "expected_warehouse",
        "provided_warehouse",
        "order_type",
        "user_uuid",
    },
    "inventory_form_validation_failed": {
        "form_name",
        "error_code",
        "field_name",
        "warehouse",
        "client_id",
        "product_id",
        "product_category",
        "quantity",
    },
    "auth_login_succeeded": {
        "auth_method",
        "user_role",
        "identity_provider",
        "session_age_seconds",
        "device_type",
    },
    "auth_login_failed": {
        "auth_method",
        "failure_reason",
        "failure_code",
        "identity_hash",
        "device_type",
    },
    "session_access_denied": {
        "route_path",
        "denial_reason",
        "http_status",
        "had_session_cookie",
    },
    "backoffice_navigation_clicked": {
        "from_path",
        "to_path",
        "nav_surface",
        "is_mobile",
    },
    "api_request_latency_sampled": {
        "api_route",
        "method",
        "status_code",
        "latency_ms",
        "upstream_service",
        "request_source",
    },
    "api_request_failed": {
        "api_route",
        "method",
        "status_code",
        "error_family",
        "error_message_sanitized",
        "retryable",
        "request_source",
    },
    "inventory_form_abandoned": {
        "form_name",
        "step",
        "dwell_time_seconds",
        "had_validation_error",
        "warehouse",
        "client_id",
        "product_id",
    },
}


def filter_properties_by_allowlist(
    event_type: str, properties: dict[str, Any]
) -> dict[str, Any]:
    """Filter properties to only include fields allowed for the specific event type."""
    allowed_keys = EVENT_ALLOWLIST.get(event_type, set())
    return {k: v for k, v in properties.items() if k in allowed_keys}


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

    events: list[dict[str, Any]] = Field(default_factory=list)


class TelemetryBatchResponse(BaseModel):
    """Response acknowledging received, stored, and rejected event counts."""

    received: int
    stored: int
    rejected: int


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
    db: Session = Depends(get_db),
) -> TelemetryBatchResponse:
    """Receive a batch of telemetry events, validate granularly, and persist valid events in bulk."""
    total_received = len(batch.events)
    records_to_insert: list[TelemetryEventRecord] = []
    rejected_count = 0

    for raw_event in batch.events:
        try:
            event = TelemetryEvent.model_validate(raw_event)
            filtered_tags = filter_properties_by_allowlist(
                event.event_type, event.properties
            )
            record = TelemetryEventRecord(
                event_id=event.eventId,
                timestamp=event.timestamp,
                session_id=event.sessionId,
                user_id=event.userId,
                event_type=event.event_type,
                service="backoffice",
                request_id=event.requestId,
                tags=filtered_tags,
            )
            records_to_insert.append(record)
        except (ValidationError, Exception) as exc:
            logger.warning("telemetry_event_rejected error=%s", exc)
            rejected_count += 1

    if records_to_insert:
        db.add_all(records_to_insert)
        db.commit()
        stored_count = len(records_to_insert)
    else:
        stored_count = 0

    logger.info(
        "telemetry_batch_processed received=%d stored=%d rejected=%d",
        total_received,
        stored_count,
        rejected_count,
    )

    return TelemetryBatchResponse(
        received=total_received,
        stored=stored_count,
        rejected=rejected_count,
    )


@router.options("/report", status_code=200)
async def options_telemetry_report() -> Response:
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


@router.get("/report", status_code=200)
async def get_telemetry_report(
    start_date: str | None = Query(default=None, description="Start date ISO 8601 UTC (inclusive)"),
    end_date: str | None = Query(default=None, description="End date ISO 8601 UTC (exclusive)"),
) -> dict[str, Any]:
    """Retrieve operational telemetry report with 60-second in-memory TTL caching."""
    now = datetime.now(timezone.utc)

    try:
        if start_date is not None and start_date.strip():
            resolved_start = _to_iso_utc(start_date.strip())
        else:
            resolved_start = (now - timedelta(days=7)).isoformat()

        if end_date is not None and end_date.strip():
            resolved_end = _to_iso_utc(end_date.strip())
        else:
            resolved_end = now.isoformat()
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    cache_key = f"telemetry_report:{resolved_start}:{resolved_end}"
    cached_report = api_cache.get(cache_key)
    if cached_report is not None:
        return cached_report

    report = generate_telemetry_report(
        start_date=resolved_start,
        end_date=resolved_end,
        engine=get_inventory_engine(),
    )

    api_cache.set(cache_key, report, ttl_seconds=60)
    return report

