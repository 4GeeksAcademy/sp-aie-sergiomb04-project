"""Job runner service for managing job_runs state transitions and distributed locking."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import sys
from typing import Any

# Ensure project roots are in sys.path
_CURRENT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _CURRENT_DIR.parent if _CURRENT_DIR.name == "services" else _CURRENT_DIR.parents[1]
_API_DIR = _REPO_ROOT / "services" / "api"

for path in [_REPO_ROOT, _API_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from sqlmodel import Session, select

from trackflow_api.database import get_inventory_engine
from trackflow_api.models import JobRun, JobRunStatusEnum, now_utc


def _normalize_target_date(target_date: date | str) -> date:
    """Normalize target date to datetime.date."""
    if isinstance(target_date, str):
        return date.fromisoformat(target_date.strip())
    if isinstance(target_date, datetime):
        return target_date.date()
    if isinstance(target_date, date):
        return target_date
    raise ValueError(f"Invalid target_date type: {type(target_date)}")


def has_processing_lock(job_name: str = "nightly_export", engine: Any = None) -> bool:
    """Check if an active instance with status='processing' exists for the job_name.
    
    Distributed Lock: If a job is currently 'processing', returns True.
    """
    db_engine = engine or get_inventory_engine()
    with Session(db_engine) as session:
        statement = (
            select(JobRun)
            .where(
                JobRun.job_name == job_name,
                JobRun.status == JobRunStatusEnum.PROCESSING.value,
            )
            .limit(1)
        )
        return session.exec(statement).first() is not None


def has_completed_for_date(
    job_name: str = "nightly_export",
    target_date: date | str = None,
    engine: Any = None,
) -> bool:
    """Check if the job has already completed successfully for the target date."""
    if target_date is None:
        raise ValueError("target_date is required")
    norm_date = _normalize_target_date(target_date)
    db_engine = engine or get_inventory_engine()
    with Session(db_engine) as session:
        statement = (
            select(JobRun)
            .where(
                JobRun.job_name == job_name,
                JobRun.target_date == norm_date,
                JobRun.status == JobRunStatusEnum.COMPLETED.value,
            )
            .limit(1)
        )
        return session.exec(statement).first() is not None


def create_job_run(
    job_name: str = "nightly_export",
    target_date: date | str = None,
    status: str = JobRunStatusEnum.PROCESSING.value,
    engine: Any = None,
) -> JobRun:
    """Create and persist a new job_run record in pending or processing state."""
    if target_date is None:
        raise ValueError("target_date is required")
    norm_date = _normalize_target_date(target_date)
    db_engine = engine or get_inventory_engine()

    job_run = JobRun(
        job_name=job_name,
        target_date=norm_date,
        status=status,
        started_at=now_utc(),
        created_at=now_utc(),
    )
    with Session(db_engine) as session:
        session.add(job_run)
        session.commit()
        session.refresh(job_run)
        return job_run


def mark_as_completed(
    job_id: str,
    engine: Any = None,
) -> JobRun | None:
    """Transition job_run to 'completed' and record finished_at timestamp."""
    db_engine = engine or get_inventory_engine()
    with Session(db_engine) as session:
        job = session.get(JobRun, job_id)
        if not job:
            return None
        job.status = JobRunStatusEnum.COMPLETED.value
        job.finished_at = now_utc()
        session.add(job)
        session.commit()
        session.refresh(job)
        return job


def mark_as_failed(
    job_id: str,
    error_message: str,
    engine: Any = None,
) -> JobRun | None:
    """Transition job_run to 'failed', record error message and finished_at timestamp."""
    db_engine = engine or get_inventory_engine()
    with Session(db_engine) as session:
        job = session.get(JobRun, job_id)
        if not job:
            return None
        job.status = JobRunStatusEnum.FAILED.value
        job.error_message = error_message
        job.finished_at = now_utc()
        session.add(job)
        session.commit()
        session.refresh(job)
        return job


def get_job_run_by_id(job_id: str, engine: Any = None) -> JobRun | None:
    """Retrieve job_run record by id."""
    db_engine = engine or get_inventory_engine()
    with Session(db_engine) as session:
        return session.get(JobRun, job_id)
