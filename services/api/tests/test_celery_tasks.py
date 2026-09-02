"""Tests for Celery asynchronous tasks, FastAPI endpoints, retry policy, and DLQ."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4
import pytest
from celery.exceptions import MaxRetriesExceededError, Retry
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select

from trackflow_api.app import app
from trackflow_api.celery_app import celery_app
from trackflow_api.dlq import get_dlq_record, list_dlq_records, save_to_dlq
from trackflow_api.models import DeadLetterQueue
from trackflow_api.tasks import (
    execute_sample_heavy_task,
    execute_weekly_performance_pipeline_task,
)


@pytest.fixture
def test_db_engine(tmp_path):
    """Create isolated SQLite database engine with all tables initialized."""
    db_file = tmp_path / "test_celery.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def client(test_db_engine, monkeypatch):
    """Provide FastAPI test client patched with test engine."""
    monkeypatch.setattr("trackflow_api.database.get_inventory_engine", lambda: test_db_engine)
    monkeypatch.setattr("trackflow_api.dlq.get_inventory_engine", lambda: test_db_engine)
    monkeypatch.setattr("trackflow_api.reporting.service.get_inventory_engine", lambda: test_db_engine)
    return TestClient(app)


# ─── Celery Configuration Tests ──────────────────────────────────────────────

def test_celery_app_configuration():
    """Verify Celery app has proper tracking, expiration, and serializer settings."""
    assert celery_app.conf.task_track_started is True
    assert celery_app.conf.result_expires == 3600
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.enable_utc is True


# ─── DLQ Persistence Unit Tests ──────────────────────────────────────────────

def test_save_to_dlq_and_query(test_db_engine):
    """Verify saving failed task to DLQ and querying by ID or list."""
    task_id = str(uuid4())
    record = save_to_dlq(
        task_id=task_id,
        task_name="tasks.execute_weekly_performance_pipeline",
        retry_count=3,
        error_message="Connection timeout after 3 attempts",
        payload_ref={"target_week_start": "2026-08-17", "force_recompute": True},
        engine=test_db_engine,
    )

    assert record.task_id == task_id
    assert record.retry_count == 3
    assert record.error_message == "Connection timeout after 3 attempts"
    assert record.payload_ref == {"target_week_start": "2026-08-17", "force_recompute": True}

    fetched = get_dlq_record(task_id, engine=test_db_engine)
    assert fetched is not None
    assert fetched.id == record.id

    records = list_dlq_records(limit=10, engine=test_db_engine)
    assert len(records) >= 1
    assert any(r.task_id == task_id for r in records)


# ─── Task Retry & DLQ Behavior Unit Tests ────────────────────────────────────

def test_task_retry_exponential_backoff():
    """Verify that task failure triggers retry with exponential backoff countdown."""
    with patch.object(execute_weekly_performance_pipeline_task, "retry", side_effect=Retry(message="Retry triggered")) as mock_retry:
        with patch("trackflow_api.tasks.trigger_pipeline_run", side_effect=ValueError("Simulated pipeline failure")):
            with pytest.raises(Retry):
                execute_weekly_performance_pipeline_task(
                    target_week_start="2026-08-17",
                    force_recompute=False,
                )

            mock_retry.assert_called_once()
            _, kwargs = mock_retry.call_args
            assert kwargs["countdown"] == 5


def test_task_dlq_on_max_retries_exceeded(test_db_engine, monkeypatch):
    """Verify that when retries reach max_retries, task records to DLQ."""
    monkeypatch.setattr("trackflow_api.dlq.get_inventory_engine", lambda: test_db_engine)

    with patch.object(execute_weekly_performance_pipeline_task, "retry", side_effect=MaxRetriesExceededError("Max retries reached")):
        # Mock request with retries = 3
        execute_weekly_performance_pipeline_task.request.retries = 3
        execute_weekly_performance_pipeline_task.request.id = f"dlq-test-{uuid4()}"

        with patch("trackflow_api.tasks.trigger_pipeline_run", side_effect=RuntimeError("Fatal database crash")):
            with pytest.raises(MaxRetriesExceededError):
                execute_weekly_performance_pipeline_task(
                    target_week_start="2026-08-17",
                )

        dlq_record = get_dlq_record(execute_weekly_performance_pipeline_task.request.id, engine=test_db_engine)
        assert dlq_record is not None
        assert dlq_record.task_name == "tasks.execute_weekly_performance_pipeline"
        assert dlq_record.retry_count == 3
        assert "Fatal database crash" in dlq_record.error_message


# ─── API Endpoints Tests ─────────────────────────────────────────────────────

def test_trigger_pipeline_task_endpoint(client):
    """Verify POST /tasks/pipeline-run enqueues task and returns 202 Accepted."""
    with patch.object(execute_weekly_performance_pipeline_task, "delay") as mock_delay:
        mock_delay.return_value.id = "mock-uuid-12345"

        response = client.post(
            "/tasks/pipeline-run",
            json={"target_week_start": "2026-08-17", "force_recompute": True},
        )

        assert response.status_code == 202
        data = response.json()
        assert data["task_id"] == "mock-uuid-12345"
        assert data["status"] == "pending"
        assert "accepted" in data["message"].lower()
        mock_delay.assert_called_once_with(
            target_week_start="2026-08-17",
            force_recompute=True,
            triggered_by="api_tasks_endpoint",
        )


def test_trigger_reporting_pipeline_runs_endpoint_async(client):
    """Verify POST /reporting/pipeline-runs enqueues task and returns 202 Accepted."""
    with patch.object(execute_weekly_performance_pipeline_task, "delay") as mock_delay:
        mock_delay.return_value.id = "reporting-task-uuid"

        response = client.post(
            "/reporting/pipeline-runs",
            json={"target_week_start": "2026-08-17", "force_recompute": False},
        )

        assert response.status_code == 202
        data = response.json()
        assert data["task_id"] == "reporting-task-uuid"
        assert data["status"] == "pending"


def test_get_task_status_endpoint_pending(client):
    """Verify GET /tasks/{task_id} returns pending status."""
    with patch("trackflow_api.routes.tasks.AsyncResult") as mock_async_result:
        mock_instance = MagicMock()
        mock_instance.state = "PENDING"
        mock_instance.result = None
        mock_async_result.return_value = mock_instance

        response = client.get("/tasks/task-pending-1")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task-pending-1"
        assert data["status"] == "pending"
        assert data["result"] is None
        assert data["error"] is None


def test_get_task_status_endpoint_success(client):
    """Verify GET /tasks/{task_id} returns success status and output."""
    with patch("trackflow_api.routes.tasks.AsyncResult") as mock_async_result:
        mock_instance = MagicMock()
        mock_instance.state = "SUCCESS"
        mock_instance.result = {"run_id": "run-99", "status": "COMPLETED"}
        mock_async_result.return_value = mock_instance

        response = client.get("/tasks/task-success-1")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task-success-1"
        assert data["status"] == "success"
        assert data["result"] == {"run_id": "run-99", "status": "COMPLETED"}
        assert data["error"] is None


def test_get_task_status_endpoint_failure(client):
    """Verify GET /tasks/{task_id} returns failure status and error message."""
    with patch("trackflow_api.routes.tasks.AsyncResult") as mock_async_result:
        mock_instance = MagicMock()
        mock_instance.state = "FAILURE"
        mock_instance.result = RuntimeError("Worker out of memory")
        mock_async_result.return_value = mock_instance

        response = client.get("/tasks/task-failure-1")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task-failure-1"
        assert data["status"] == "failure"
        assert "Worker out of memory" in data["error"]


def test_dlq_api_endpoint(client, test_db_engine):
    """Verify GET /tasks/dlq returns list of DLQ records."""
    save_to_dlq(
        task_id="dlq-api-test-1",
        task_name="tasks.execute_sample_heavy_task",
        retry_count=3,
        error_message="API test failure",
        payload_ref={"sample": "data"},
        engine=test_db_engine,
    )

    response = client.get("/tasks/dlq")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(item["task_id"] == "dlq-api-test-1" for item in data)
