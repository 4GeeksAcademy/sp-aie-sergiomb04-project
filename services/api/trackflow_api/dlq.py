"""Dead Letter Queue (DLQ) service for persisting failed asynchronous Celery tasks."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from sqlmodel import Session, select

from trackflow_api.database import get_inventory_engine
from trackflow_api.models import DeadLetterQueue, now_utc

logger = logging.getLogger("trackflow_api.dlq")


def save_to_dlq(
    task_id: str,
    task_name: str,
    retry_count: int = 0,
    error_message: str | None = None,
    payload_ref: Any = None,
    engine: Any = None,
) -> DeadLetterQueue:
    """Persist a failed task execution into the dead_letter_queue table."""
    db_engine = engine or get_inventory_engine()
    
    # Ensure payload_ref is JSON serializable dict or primitive
    normalized_payload = payload_ref if isinstance(payload_ref, (dict, list, str, int, float, bool)) or payload_ref is None else str(payload_ref)

    record = DeadLetterQueue(
        id=str(uuid4()),
        task_id=task_id,
        task_name=task_name,
        retry_count=retry_count,
        error_message=error_message,
        payload_ref=normalized_payload if isinstance(normalized_payload, dict) else {"raw": normalized_payload},
        created_at=now_utc(),
    )

    with Session(db_engine) as session:
        # Check if already recorded to guarantee idempotency
        existing = session.exec(
            select(DeadLetterQueue).where(DeadLetterQueue.task_id == task_id).limit(1)
        ).first()
        if existing:
            existing.retry_count = retry_count
            existing.error_message = error_message
            existing.payload_ref = record.payload_ref
            session.add(existing)
            session.commit()
            session.refresh(existing)
            logger.info("Updated existing DLQ record for task_id=%s", task_id)
            return existing

        session.add(record)
        session.commit()
        session.refresh(record)
        logger.warning(
            "Persisted dead-letter task to DLQ: task_id=%s task_name=%s retries=%d error=%s",
            task_id,
            task_name,
            retry_count,
            error_message,
        )
        return record


def get_dlq_record(task_id: str, engine: Any = None) -> DeadLetterQueue | None:
    """Retrieve DLQ record by task_id."""
    db_engine = engine or get_inventory_engine()
    with Session(db_engine) as session:
        return session.exec(
            select(DeadLetterQueue).where(DeadLetterQueue.task_id == task_id).limit(1)
        ).first()


def list_dlq_records(limit: int = 50, engine: Any = None) -> list[DeadLetterQueue]:
    """List recent DLQ records ordered by creation date."""
    db_engine = engine or get_inventory_engine()
    with Session(db_engine) as session:
        return list(
            session.exec(
                select(DeadLetterQueue).order_by(DeadLetterQueue.created_at.desc()).limit(limit)
            ).all()
        )
