"""Reporting router for business performance metrics and pipeline execution."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

from trackflow_api.reporting.service import (
    get_latest_pipeline_run,
    get_weekly_performance_report,
    trigger_pipeline_run,
)

logger = logging.getLogger("trackflow_api.reporting")

router = APIRouter(prefix="/reporting", tags=["reporting"])


class TriggerPipelineRequest(BaseModel):
    """Payload for manually triggering a pipeline run."""

    target_week_start: str | None = Field(
        default=None,
        description="Target week start in YYYY-MM-DD format (Monday). Defaults to previous week.",
    )
    force_recompute: bool = Field(
        default=False,
        description="Force recomputation even if already processed.",
    )


@router.options("/pipeline-runs/latest", status_code=200)
@router.options("/pipeline-runs", status_code=200)
@router.options("/weekly-warehouse-client-performance", status_code=200)
async def options_reporting_endpoints() -> Response:
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


@router.get("/pipeline-runs/latest", status_code=200)
async def get_latest_run(
    pipeline_name: str = Query(
        default="weekly_warehouse_client_performance_pipeline",
        description="Name of the pipeline to check",
    ),
) -> dict[str, Any]:
    """Retrieve execution status, timings and metadata of the most recent pipeline run."""
    run = get_latest_pipeline_run(pipeline_name=pipeline_name)
    if not run:
        raise HTTPException(
            status_code=404,
            detail=f"No pipeline runs found for '{pipeline_name}'",
        )
    return run


@router.post("/pipeline-runs", status_code=200)
async def trigger_run(payload: TriggerPipelineRequest | None = None) -> dict[str, Any]:
    """Manually trigger an execution of the weekly business performance pipeline."""
    target_week = payload.target_week_start if payload else None
    force = payload.force_recompute if payload else False

    try:
        result = trigger_pipeline_run(
            target_week_start=target_week,
            force_recompute=force,
            triggered_by="manual_api",
        )
        return result
    except Exception as exc:
        logger.exception("Failed to trigger pipeline run: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute pipeline run: {str(exc)}",
        ) from exc


@router.get("/weekly-warehouse-client-performance", status_code=200)
async def get_weekly_performance(
    week_start: str | None = Query(
        default=None,
        description="Target week start YYYY-MM-DD. Defaults to the latest available week.",
    ),
    warehouse: str | None = Query(
        default=None,
        description="Filter by warehouse (e.g. 'los_angeles' or 'zaragoza')",
    ),
    client_id: str | None = Query(
        default=None,
        description="Filter by client ID (e.g. 'fashion-co')",
    ),
) -> dict[str, Any]:
    """Query aggregated business performance KPIs per warehouse and client."""
    report = get_weekly_performance_report(
        week_start=week_start,
        warehouse=warehouse,
        client_id=client_id,
    )
    return report
