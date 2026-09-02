"""Celery tasks for TrackFlow background processing with retry logic and DLQ."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any
from uuid import uuid4

from celery.exceptions import MaxRetriesExceededError

from trackflow_api.celery_app import celery_app
from trackflow_api.dlq import save_to_dlq
from trackflow_api.reporting.service import trigger_pipeline_run

logger = logging.getLogger("trackflow_api.tasks")


@celery_app.task(
    bind=True,
    max_retries=3,
    time_limit=300,
    soft_time_limit=240,
    name="tasks.execute_weekly_performance_pipeline",
)
def execute_weekly_performance_pipeline_task(
    self,
    target_week_start: str | None = None,
    force_recompute: bool = False,
    triggered_by: str = "celery_worker",
) -> dict[str, Any]:
    """Execute the weekly warehouse and client performance data pipeline asynchronously."""
    task_id = self.request.id or str(uuid4())
    retry_count = self.request.retries
    start_time = perf_counter()

    logger.info(
        "task_started task_name=%s task_id=%s retry_count=%d target_week=%s force=%s",
        self.name,
        task_id,
        retry_count,
        target_week_start,
        force_recompute,
    )

    try:
        result = trigger_pipeline_run(
            target_week_start=target_week_start,
            force_recompute=force_recompute,
            triggered_by=triggered_by,
        )
        duration_ms = (perf_counter() - start_time) * 1000
        logger.info(
            "task_success task_name=%s task_id=%s retry_count=%d duration_ms=%.2f status=%s run_id=%s",
            self.name,
            task_id,
            retry_count,
            duration_ms,
            result.get("status"),
            result.get("run_id"),
        )
        return result

    except Exception as exc:
        duration_ms = (perf_counter() - start_time) * 1000
        logger.warning(
            "task_failed_attempt task_name=%s task_id=%s retry_count=%d duration_ms=%.2f error=%s",
            self.name,
            task_id,
            retry_count,
            duration_ms,
            exc,
            exc_info=True,
        )

        payload_ref = {
            "target_week_start": target_week_start,
            "force_recompute": force_recompute,
            "triggered_by": triggered_by,
        }

        if retry_count < self.max_retries:
            countdown = (2 ** retry_count) * 5
            logger.info(
                "task_scheduling_retry task_name=%s task_id=%s next_retry=%d countdown=%ds",
                self.name,
                task_id,
                retry_count + 1,
                countdown,
            )
            raise self.retry(exc=exc, countdown=countdown)

        # Max retries exhausted - record in Dead Letter Queue (DLQ)
        logger.error(
            "task_dlq_persisted task_name=%s task_id=%s max_retries=%d error=%s",
            self.name,
            task_id,
            self.max_retries,
            exc,
            exc_info=True,
        )
        save_to_dlq(
            task_id=task_id,
            task_name=self.name,
            retry_count=retry_count,
            error_message=str(exc),
            payload_ref=payload_ref,
        )
        raise MaxRetriesExceededError(f"Task {self.name}[{task_id}] failed after {retry_count} retries: {exc}") from exc


@celery_app.task(
    bind=True,
    max_retries=3,
    time_limit=300,
    soft_time_limit=240,
    name="tasks.execute_sample_heavy_task",
)
def execute_sample_heavy_task(
    self,
    payload_ref: dict[str, Any] | None = None,
    should_fail: bool = False,
) -> dict[str, Any]:
    """Sample background task for testing retries, backoff, and DLQ handling."""
    task_id = self.request.id or str(uuid4())
    retry_count = self.request.retries
    start_time = perf_counter()

    logger.info(
        "task_started task_name=%s task_id=%s retry_count=%d payload=%s",
        self.name,
        task_id,
        retry_count,
        payload_ref,
    )

    if should_fail:
        duration_ms = (perf_counter() - start_time) * 1000
        logger.warning(
            "task_simulated_error task_name=%s task_id=%s retry_count=%d duration_ms=%.2f",
            self.name,
            task_id,
            retry_count,
            duration_ms,
        )
        if retry_count < self.max_retries:
            countdown = (2 ** retry_count) * 5
            raise self.retry(exc=RuntimeError("Simulated failure for testing retries"), countdown=countdown)

        save_to_dlq(
            task_id=task_id,
            task_name=self.name,
            retry_count=retry_count,
            error_message="Simulated permanent failure for testing DLQ",
            payload_ref=payload_ref,
        )
        raise MaxRetriesExceededError(f"Task {self.name}[{task_id}] reached maximum retries")

    duration_ms = (perf_counter() - start_time) * 1000
    return {
        "task_id": task_id,
        "status": "completed",
        "duration_ms": duration_ms,
        "payload_ref": payload_ref,
    }
