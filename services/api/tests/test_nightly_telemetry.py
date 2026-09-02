"""Unit and Integration Tests for Ticket #DEV-53: Nightly Telemetry Export & Execution Control."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pandas as pd
import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from data.pipelines.telemetry_kpi_daily.run import run_daily_pipeline
from scripts.nightly_export import (
    JOB_NAME,
    export_telemetry_csv,
    resolve_target_date,
    run_nightly_export,
)
from services.job_runner import (
    create_job_run,
    get_job_run_by_id,
    has_completed_for_date,
    has_processing_lock,
    mark_as_completed,
    mark_as_failed,
)
from trackflow_api.models import JobRun, JobRunStatusEnum, TelemetryEventRecord


@pytest.fixture
def test_engine(tmp_path):
    """Create an isolated in-memory or SQLite database with all tables initialized."""
    db_file = tmp_path / "test_job_runs.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def sample_telemetry_events(test_engine):
    """Seed sample telemetry events across different dates."""
    events = [
        TelemetryEventRecord(
            event_id="e1a2b3c4",
            timestamp="2026-08-27T10:15:30Z",
            session_id="sess-1",
            user_id="usr_101",
            event_type="api_request",
            service="backoffice",
            request_id="req-1",
            tags={"endpoint": "/v1/predict"},
        ),
        TelemetryEventRecord(
            event_id="e5f6g7h8",
            timestamp="2026-08-27T11:20:00Z",
            session_id="sess-2",
            user_id="usr_102",
            event_type="api_request",
            service="backoffice",
            request_id="req-2",
            tags={"endpoint": "/v1/health"},
        ),
        TelemetryEventRecord(
            event_id="e9i0j1k2",
            timestamp="2026-08-26T08:00:00Z",
            session_id="sess-3",
            user_id="usr_103",
            event_type="auth_login_succeeded",
            service="backoffice",
            request_id="req-3",
            tags={"role": "admin"},
        ),
    ]
    with Session(test_engine) as session:
        for ev in events:
            session.add(ev)
        session.commit()
    return test_engine


# ─── Job Runner Unit Tests ───────────────────────────────────────────────────

def test_job_runner_lifecycle(test_engine):
    """Test full state lifecycle: create -> mark_completed and create -> mark_failed."""
    target_dt = date(2026, 8, 27)

    # 1. Create job run in processing
    job = create_job_run(job_name="nightly_export", target_date=target_dt, engine=test_engine)
    assert job.id is not None
    assert job.job_name == "nightly_export"
    assert job.target_date == target_dt
    assert job.status == JobRunStatusEnum.PROCESSING.value
    assert job.started_at is not None
    assert job.finished_at is None
    assert job.error_message is None

    # 2. Mark completed
    completed_job = mark_as_completed(job_id=job.id, engine=test_engine)
    assert completed_job is not None
    assert completed_job.status == JobRunStatusEnum.COMPLETED.value
    assert completed_job.finished_at is not None

    # 3. Create another job and mark failed
    job2 = create_job_run(job_name="nightly_export", target_date=date(2026, 8, 28), engine=test_engine)
    failed_job = mark_as_failed(job_id=job2.id, error_message="Simulated connection error", engine=test_engine)
    assert failed_job is not None
    assert failed_job.status == JobRunStatusEnum.FAILED.value
    assert failed_job.error_message == "Simulated connection error"
    assert failed_job.finished_at is not None


def test_has_processing_lock(test_engine):
    """Test distributed lock checking via database state."""
    target_dt = date(2026, 8, 27)

    # No job running -> No lock
    assert has_processing_lock(job_name="nightly_export", engine=test_engine) is False

    # Start processing job -> Lock is active
    job = create_job_run(job_name="nightly_export", target_date=target_dt, status=JobRunStatusEnum.PROCESSING.value, engine=test_engine)
    assert has_processing_lock(job_name="nightly_export", engine=test_engine) is True

    # Complete job -> Lock is released
    mark_as_completed(job_id=job.id, engine=test_engine)
    assert has_processing_lock(job_name="nightly_export", engine=test_engine) is False

    # Another job for another name should not lock nightly_export
    create_job_run(job_name="other_job", target_date=target_dt, status=JobRunStatusEnum.PROCESSING.value, engine=test_engine)
    assert has_processing_lock(job_name="nightly_export", engine=test_engine) is False
    assert has_processing_lock(job_name="other_job", engine=test_engine) is True


def test_has_completed_for_date(test_engine):
    """Test idempotency checking for target date."""
    target_dt_1 = date(2026, 8, 27)
    target_dt_2 = date(2026, 8, 28)

    assert has_completed_for_date("nightly_export", target_dt_1, engine=test_engine) is False

    # Job in processing should not count as completed
    job = create_job_run(job_name="nightly_export", target_date=target_dt_1, engine=test_engine)
    assert has_completed_for_date("nightly_export", target_dt_1, engine=test_engine) is False

    # Mark as completed -> should return True for date 1, False for date 2
    mark_as_completed(job_id=job.id, engine=test_engine)
    assert has_completed_for_date("nightly_export", target_dt_1, engine=test_engine) is True
    assert has_completed_for_date("nightly_export", target_dt_2, engine=test_engine) is False


# ─── Target Date Resolution Tests ─────────────────────────────────────────────

def test_resolve_target_date(monkeypatch):
    """Test resolution of target date with CLI arg, environment variable and default fallback."""
    # 1. Direct CLI arg takes precedence
    assert resolve_target_date("2026-08-15") == date(2026, 8, 15)

    # 2. TARGET_DATE environment variable
    monkeypatch.setenv("TARGET_DATE", "2026-08-20")
    assert resolve_target_date(None) == date(2026, 8, 20)

    # 3. Default fallback to yesterday UTC
    monkeypatch.delenv("TARGET_DATE", raising=False)
    expected_yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    assert resolve_target_date(None) == expected_yesterday


# ─── CSV Export Tests ─────────────────────────────────────────────────────────

def test_export_telemetry_csv(sample_telemetry_events, tmp_path):
    """Test exporting raw CSV backup matches specification format and filters by date."""
    target_dt = date(2026, 8, 27)
    csv_file = export_telemetry_csv(target_date=target_dt, raw_dir=tmp_path, engine=sample_telemetry_events)

    assert csv_file.exists()
    assert csv_file.name == "telemetry_2026-08-27.csv"

    df = pd.read_csv(csv_file)
    assert list(df.columns) == ["event_id", "event_name", "user_id", "timestamp", "payload"]
    assert len(df) == 2
    assert set(df["event_id"]) == {"e1a2b3c4", "e5f6g7h8"}
    assert df.loc[df["event_id"] == "e1a2b3c4", "event_name"].iloc[0] == "api_request"
    assert df.loc[df["event_id"] == "e1a2b3c4", "user_id"].iloc[0] == "usr_101"

    payload_parsed = json.loads(df.loc[df["event_id"] == "e1a2b3c4", "payload"].iloc[0])
    assert payload_parsed == {"endpoint": "/v1/predict"}

    # Test idempotency / skipping if file exists
    second_csv = export_telemetry_csv(target_date=target_dt, raw_dir=tmp_path, engine=sample_telemetry_events)
    assert second_csv == csv_file


# ─── Script Execution Workflow & Anti-Zombie Tests ────────────────────────────

def test_nightly_export_success_flow(sample_telemetry_events, tmp_path):
    """Test complete successful flow: creates processing record, exports CSV, runs subprocess, marks completed."""
    target_dt = date(2026, 8, 27)
    subprocess_called = []

    def mock_runner(dt: date, root: Path):
        subprocess_called.append((dt, root))

    result = run_nightly_export(
        target_date=target_dt,
        engine=sample_telemetry_events,
        raw_dir=tmp_path,
        subprocess_runner=mock_runner,
    )

    assert result["status"] == "completed"
    assert result["target_date"] == "2026-08-27"
    assert result["job_id"] is not None
    assert len(subprocess_called) == 1

    # Verify job record state in DB
    job_record = get_job_run_by_id(result["job_id"], engine=sample_telemetry_events)
    assert job_record is not None
    assert job_record.status == JobRunStatusEnum.COMPLETED.value
    assert job_record.finished_at is not None
    assert job_record.error_message is None


def test_nightly_export_distributed_lock_skip(sample_telemetry_events, tmp_path):
    """Test that a concurrent job skips quietly if another instance is processing."""
    target_dt = date(2026, 8, 27)

    # Simulate existing active job
    create_job_run(job_name=JOB_NAME, target_date=date(2026, 8, 26), status=JobRunStatusEnum.PROCESSING.value, engine=sample_telemetry_events)

    runner_called = []
    result = run_nightly_export(
        target_date=target_dt,
        engine=sample_telemetry_events,
        raw_dir=tmp_path,
        subprocess_runner=lambda dt, root: runner_called.append(dt),
    )

    assert result["status"] == "locked"
    assert result["job_id"] is None
    assert len(runner_called) == 0


def test_nightly_export_idempotency_skip(sample_telemetry_events, tmp_path):
    """Test that execution is skipped if the target date has already completed."""
    target_dt = date(2026, 8, 27)

    # First run succeeds
    run_nightly_export(
        target_date=target_dt,
        engine=sample_telemetry_events,
        raw_dir=tmp_path,
        subprocess_runner=lambda dt, root: None,
    )

    # Second run should skip
    runner_called = []
    result = run_nightly_export(
        target_date=target_dt,
        engine=sample_telemetry_events,
        raw_dir=tmp_path,
        subprocess_runner=lambda dt, root: runner_called.append(dt),
    )

    assert result["status"] == "skipped"
    assert result["job_id"] is None
    assert len(runner_called) == 0


def test_nightly_export_anti_zombie_on_failure(sample_telemetry_events, tmp_path):
    """Test anti-zombie guarantee: if subprocess fails, the job_run transitions to failed."""
    target_dt = date(2026, 8, 27)

    def failing_runner(dt: date, root: Path):
        raise RuntimeError("Data pipeline crashed due to upstream timeout")

    with pytest.raises(RuntimeError, match="Data pipeline crashed"):
        run_nightly_export(
            target_date=target_dt,
            engine=sample_telemetry_events,
            raw_dir=tmp_path,
            subprocess_runner=failing_runner,
        )

    # Verify that in DB, no job remains in processing state, but exactly one in failed state
    with Session(sample_telemetry_events) as session:
        processing_jobs = session.exec(select(JobRun).where(JobRun.status == JobRunStatusEnum.PROCESSING.value)).all()
        assert len(processing_jobs) == 0

        failed_jobs = session.exec(select(JobRun).where(JobRun.status == JobRunStatusEnum.FAILED.value)).all()
        assert len(failed_jobs) == 1
        failed_job = failed_jobs[0]
        assert failed_job.target_date == target_dt
        assert failed_job.finished_at is not None
        assert "Data pipeline crashed due to upstream timeout" in (failed_job.error_message or "")


# ─── Daily KPI Pipeline Integration ──────────────────────────────────────────

def test_daily_kpi_pipeline(sample_telemetry_events):
    """Test the daily telemetry KPI pipeline logic."""
    result = run_daily_pipeline(
        target_date=date(2026, 8, 27),
        no_prefect=True,
        engine=sample_telemetry_events,
    )
    assert result["status"] == "success"
    assert result["target_date"] == "2026-08-27"
    assert result["total_events"] == 2
