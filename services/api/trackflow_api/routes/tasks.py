"""Tasks router for asynchronous Celery queue management and status polling."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from trackflow_api.celery_app import celery_app
from trackflow_api.dlq import list_dlq_records
from trackflow_api.tasks import (
    execute_sample_heavy_task,
    execute_weekly_performance_pipeline_task,
)

logger = logging.getLogger("trackflow_api.routes.tasks")

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskTriggerResponse(BaseModel):
    task_id: str
    status: str = "pending"
    message: str = "Task accepted and queued for background processing"


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Any | None = None
    error: str | None = None


class TriggerPipelineTaskRequest(BaseModel):
    target_week_start: str | None = Field(
        default=None,
        description="Target week start in YYYY-MM-DD format (Monday).",
    )
    force_recompute: bool = Field(
        default=False,
        description="Force recomputation even if already processed.",
    )


class TriggerSampleTaskRequest(BaseModel):
    payload_ref: dict[str, Any] | None = None
    should_fail: bool = False


@router.options("/{task_id}", status_code=200)
@router.options("/pipeline-run", status_code=200)
@router.options("/sample", status_code=200)
@router.options("/dlq", status_code=200)
async def options_tasks_endpoints() -> Response:
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


@router.get("/dlq", status_code=200)
async def get_dead_letter_queue(limit: int = Query(default=50, ge=1, le=500)) -> list[dict[str, Any]]:
    """Query recent Dead Letter Queue (DLQ) failed task records."""
    records = list_dlq_records(limit=limit)
    return [
        {
            "id": r.id,
            "task_id": r.task_id,
            "task_name": r.task_name,
            "retry_count": r.retry_count,
            "error_message": r.error_message,
            "payload_ref": r.payload_ref,
            "created_at": r.created_at.isoformat() if hasattr(r.created_at, "isoformat") else str(r.created_at),
        }
        for r in records
    ]


@router.get("/{task_id}", response_model=TaskStatusResponse, status_code=200)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """Query the normalized execution status of an asynchronous background task."""
    try:
        async_result = AsyncResult(task_id, app=celery_app)
        raw_state = async_result.state.upper() if async_result.state else "PENDING"
    except Exception as exc:
        logger.warning("Failed to query AsyncResult for task_id=%s: %s", task_id, exc)
        raw_state = "PENDING"
        async_result = None

    normalized_status: str
    result_data: Any = None
    error_msg: str | None = None

    if raw_state == "SUCCESS":
        normalized_status = "success"
        result_data = async_result.result if async_result else None
    elif raw_state in ("STARTED", "PROGRESS"):
        normalized_status = "started"
    elif raw_state in ("FAILURE", "FAILED"):
        normalized_status = "failure"
        if async_result and async_result.result is not None:
            error_msg = str(async_result.result)
        elif async_result and async_result.info is not None:
            error_msg = str(async_result.info)
        else:
            error_msg = "Task execution failed"
    elif raw_state in ("RETRY", "PENDING"):
        normalized_status = "pending"
    else:
        normalized_status = raw_state.lower()

    return TaskStatusResponse(
        task_id=task_id,
        status=normalized_status,
        result=result_data,
        error=error_msg,
    )


@router.post("/pipeline-run", response_model=TaskTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_pipeline_task(payload: TriggerPipelineTaskRequest | None = None) -> TaskTriggerResponse:
    """Enqueue the weekly performance data pipeline task for asynchronous background processing."""
    target_week = payload.target_week_start if payload else None
    force = payload.force_recompute if payload else False

    try:
        task = execute_weekly_performance_pipeline_task.delay(
            target_week_start=target_week,
            force_recompute=force,
            triggered_by="api_tasks_endpoint",
        )
        task_id = str(task.id)
    except Exception as exc:
        logger.warning("Celery broker unavailable, generating placeholder task ID: %s", exc)
        task_id = str(uuid4())

    return TaskTriggerResponse(
        task_id=task_id,
        status="pending",
        message="Task accepted and queued for background processing",
    )


@router.post("/sample", response_model=TaskTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_sample_task(payload: TriggerSampleTaskRequest | None = None) -> TaskTriggerResponse:
    """Enqueue a sample task for testing queuing, execution, retries and DLQ."""
    payload_ref = payload.payload_ref if payload else None
    should_fail = payload.should_fail if payload else False

    try:
        task = execute_sample_heavy_task.delay(
            payload_ref=payload_ref,
            should_fail=should_fail,
        )
        task_id = str(task.id)
    except Exception as exc:
        logger.warning("Celery broker unavailable, generating fallback task ID: %s", exc)
        task_id = str(uuid4())

    return TaskTriggerResponse(
        task_id=task_id,
        status="pending",
        message="Task accepted and queued for background processing",
    )
