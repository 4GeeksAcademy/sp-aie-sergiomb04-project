"""Comprehensive tests for the business performance pipeline and reporting endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import uuid4

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from data.pipelines.pipeline import (
    extract_telemetry_events_task,
    load_reporting_metrics_task,
    optional_pipeline_notification_task,
    transform_warehouse_client_metrics_task,
    weekly_warehouse_client_performance_flow,
)
from data.process.weekly_performance import (
    calculate_weekly_performance,
    extract_event_payload,
    normalize_raw_events_dataframe,
    resolve_week_range,
)
from trackflow_api.app import app
from trackflow_api.models import (
    PipelineRunRecord,
    TelemetryEventRecord,
    WeeklyWarehouseClientPerformance,
)
from trackflow_api.reporting.service import (
    get_latest_pipeline_run,
    get_weekly_performance_report,
    trigger_pipeline_run,
)


@pytest.fixture
def reporting_test_engine(tmp_path):
    """Create an isolated SQLite database engine with all tables initialized."""
    db_file = tmp_path / "test_reporting.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def seeded_telemetry_events(reporting_test_engine):
    """Seed sample telemetry events into the test database."""
    events = [
        # Inbound orders
        TelemetryEventRecord(
            event_id="inbound-1",
            timestamp="2026-08-17T10:00:00Z",
            session_id="s1",
            event_type="inbound_order_created",
            service="backoffice",
            request_id="r1",
            tags={"warehouse": "los_angeles", "client_id": "fashion-co", "quantity": 100},
        ),
        TelemetryEventRecord(
            event_id="inbound-2",
            timestamp="2026-08-17T11:00:00Z",
            session_id="s1",
            event_type="inbound_order_created",
            service="backoffice",
            request_id="r2",
            tags={"warehouse": "los_angeles", "client_id": "fashion-co", "quantity": 150},
        ),
        TelemetryEventRecord(
            event_id="inbound-3",
            timestamp="2026-08-18T09:00:00Z",
            session_id="s2",
            event_type="inbound_order_created",
            service="backoffice",
            request_id="r3",
            tags={"warehouse": "zaragoza", "client_id": "tech-gear", "quantity": 80},
        ),
        # Outbound orders
        TelemetryEventRecord(
            event_id="outbound-1",
            timestamp="2026-08-18T14:00:00Z",
            session_id="s1",
            event_type="outbound_order_created",
            service="backoffice",
            request_id="r4",
            tags={"warehouse": "los_angeles", "client_id": "fashion-co", "quantity": 5},
        ),
        TelemetryEventRecord(
            event_id="outbound-2",
            timestamp="2026-08-19T10:00:00Z",
            session_id="s1",
            event_type="outbound_order_created",
            service="backoffice",
            request_id="r5",
            tags={"warehouse": "los_angeles", "client_id": "fashion-co", "quantity": 2},
        ),
        TelemetryEventRecord(
            event_id="outbound-3",
            timestamp="2026-08-19T11:00:00Z",
            session_id="s2",
            event_type="outbound_order_created",
            service="backoffice",
            request_id="r6",
            tags={"warehouse": "zaragoza", "client_id": "tech-gear", "quantity": 10},
        ),
        # Stockout threshold
        TelemetryEventRecord(
            event_id="stockout-1",
            timestamp="2026-08-19T15:00:00Z",
            session_id="s1",
            event_type="stock_threshold_triggered",
            service="backoffice",
            request_id="r7",
            tags={"warehouse": "los_angeles", "client_id": "fashion-co", "deficit_units": 10},
        ),
        # Discrepancy detected
        TelemetryEventRecord(
            event_id="discrepancy-1",
            timestamp="2026-08-20T16:00:00Z",
            session_id="s1",
            event_type="inventory_discrepancy_detected",
            service="backoffice",
            request_id="r8",
            tags={"warehouse": "los_angeles", "client_id": "fashion-co", "discrepancy_units": 1},
        ),
        # Event outside the week (should NOT be included in 2026-08-17 week)
        TelemetryEventRecord(
            event_id="outbound-outside",
            timestamp="2026-08-10T12:00:00Z",
            session_id="s3",
            event_type="outbound_order_created",
            service="backoffice",
            request_id="r9",
            tags={"warehouse": "los_angeles", "client_id": "fashion-co", "quantity": 20},
        ),
    ]

    with Session(reporting_test_engine) as session:
        session.add_all(events)
        session.commit()

    return reporting_test_engine


# ─── Unit Tests: Data Processing Logic ────────────────────────────────────────

def test_resolve_week_range():
    """Verify correct Monday resolution and UTC window calculation."""
    week_start, start_iso, end_iso = resolve_week_range("2026-08-19")
    assert week_start == "2026-08-17"
    assert start_iso.startswith("2026-08-17T00:00:00")
    assert end_iso.startswith("2026-08-24T00:00:00")

    # When passing None, returns a valid 7-day Monday window
    auto_week, auto_start, auto_end = resolve_week_range(None)
    assert len(auto_week) == 10
    assert auto_start < auto_end


def test_extract_event_payload():
    """Verify safe payload extraction from dict and JSON strings."""
    assert extract_event_payload({"warehouse": "LA"}) == {"warehouse": "LA"}
    assert extract_event_payload('{"warehouse": "ZGZ", "quantity": 5}') == {"warehouse": "ZGZ", "quantity": 5}
    assert extract_event_payload("invalid json") == {}
    assert extract_event_payload(None) == {}


def test_normalize_raw_events_dataframe_deduplication():
    """Verify that duplicate event_ids are deduplicated deterministically."""
    df = pd.DataFrame([
        {
            "event_id": "dup-1",
            "timestamp": "2026-08-17T10:00:00Z",
            "event_type": "inbound_order_created",
            "tags": {"warehouse": "los_angeles", "client_id": "client-a", "quantity": 10},
        },
        {
            "event_id": "dup-1",
            "timestamp": "2026-08-17T10:00:00Z",
            "event_type": "inbound_order_created",
            "tags": {"warehouse": "los_angeles", "client_id": "client-a", "quantity": 10},
        },
    ])
    normalized = normalize_raw_events_dataframe(df)
    assert len(normalized) == 1
    assert normalized.iloc[0]["warehouse"] == "los_angeles"
    assert normalized.iloc[0]["client_id"] == "client-a"
    assert normalized.iloc[0]["quantity"] == 10


def test_calculate_weekly_performance_aggregation():
    """Verify accurate aggregation of KPIs and zero-division handling."""
    raw_data = [
        # los_angeles | fashion-co
        {"event_id": "1", "timestamp": "2026-08-17T10:00:00Z", "event_type": "inbound_order_created", "tags": {"warehouse": "los_angeles", "client_id": "fashion-co", "quantity": 100}},
        {"event_id": "2", "timestamp": "2026-08-17T11:00:00Z", "event_type": "inbound_order_created", "tags": {"warehouse": "los_angeles", "client_id": "fashion-co", "quantity": 50}},
        {"event_id": "3", "timestamp": "2026-08-18T10:00:00Z", "event_type": "outbound_order_created", "tags": {"warehouse": "los_angeles", "client_id": "fashion-co", "quantity": 10}},
        {"event_id": "4", "timestamp": "2026-08-18T12:00:00Z", "event_type": "outbound_order_created", "tags": {"warehouse": "los_angeles", "client_id": "fashion-co", "quantity": 5}},
        {"event_id": "5", "timestamp": "2026-08-19T10:00:00Z", "event_type": "stock_threshold_triggered", "tags": {"warehouse": "los_angeles", "client_id": "fashion-co"}},
        {"event_id": "6", "timestamp": "2026-08-19T11:00:00Z", "event_type": "inventory_discrepancy_detected", "tags": {"warehouse": "los_angeles", "client_id": "fashion-co"}},
        # zaragoza | zero-orders client (discrepancy without orders -> safe rate 0.0)
        {"event_id": "7", "timestamp": "2026-08-18T08:00:00Z", "event_type": "inbound_order_created", "tags": {"warehouse": "zaragoza", "client_id": "brand-x", "quantity": 30}},
        {"event_id": "8", "timestamp": "2026-08-18T09:00:00Z", "event_type": "inventory_discrepancy_detected", "tags": {"warehouse": "zaragoza", "client_id": "brand-x"}},
    ]

    metrics_df = calculate_weekly_performance(pd.DataFrame(raw_data), target_week_start="2026-08-17")
    assert len(metrics_df) == 2

    # Verify fashion-co
    fashion_row = metrics_df[(metrics_df["warehouse"] == "los_angeles") & (metrics_df["client_id"] == "fashion-co")].iloc[0]
    assert fashion_row["inbound_units_count"] == 150
    assert fashion_row["outbound_orders_count"] == 2
    assert fashion_row["stockout_events_count"] == 1
    assert fashion_row["discrepancy_events_count"] == 1
    assert fashion_row["discrepancy_rate"] == 0.5

    # Verify brand-x with zero outbound orders
    brand_row = metrics_df[(metrics_df["warehouse"] == "zaragoza") & (metrics_df["client_id"] == "brand-x")].iloc[0]
    assert brand_row["inbound_units_count"] == 30
    assert brand_row["outbound_orders_count"] == 0
    assert brand_row["stockout_events_count"] == 0
    assert brand_row["discrepancy_events_count"] == 1
    assert brand_row["discrepancy_rate"] == 0.0


# ─── Integration Tests: Prefect Flow & Idempotency ────────────────────────────

def test_weekly_pipeline_flow_execution_and_idempotency(seeded_telemetry_events):
    """Verify that running the flow twice for the same week is idempotent and produces no duplicates."""
    engine = seeded_telemetry_events

    # First execution
    result_1 = weekly_warehouse_client_performance_flow(
        target_week_start="2026-08-17",
        triggered_by="test_run",
        engine=engine,
    )
    assert result_1["execution_status"] == "COMPLETED"
    assert result_1["records_extracted"] == 8
    assert result_1["records_loaded"] == 2

    # Check database rows
    with Session(engine) as session:
        rows_1 = session.exec(SQLModel.metadata.tables["weekly_warehouse_client_performance"].select()).all()
        assert len(rows_1) == 2

    # Re-execute the flow (idempotency check)
    result_2 = weekly_warehouse_client_performance_flow(
        target_week_start="2026-08-17",
        triggered_by="test_run_recompute",
        engine=engine,
    )
    assert result_2["execution_status"] == "COMPLETED"

    # Verify still exactly 2 rows in target table (no duplicates)
    with Session(engine) as session:
        rows_2 = session.exec(SQLModel.metadata.tables["weekly_warehouse_client_performance"].select()).all()
        assert len(rows_2) == 2

        # Verify audit records in pipeline_runs
        runs = session.exec(SQLModel.metadata.tables["pipeline_runs"].select()).all()
        assert len(runs) >= 2


def test_optional_task_failure_isolation(reporting_test_engine):
    """Verify that simulated failure in the optional task does not fail the main flow."""
    result = weekly_warehouse_client_performance_flow(
        target_week_start="2026-08-17",
        simulate_optional_failure=True,
        engine=reporting_test_engine,
    )
    assert result["execution_status"] == "COMPLETED"


# ─── API Endpoint Tests ───────────────────────────────────────────────────────

def test_reporting_endpoints(seeded_telemetry_events, monkeypatch):
    """Test the 3 business reporting endpoints."""
    engine = seeded_telemetry_events

    # Patch database engine in the API to use the test engine
    monkeypatch.setattr("trackflow_api.database.get_inventory_engine", lambda: engine)
    monkeypatch.setattr("trackflow_api.reporting.service.get_inventory_engine", lambda: engine)
    monkeypatch.setattr("data.pipelines.pipeline.get_inventory_engine", lambda: engine)

    client = TestClient(app)

    # 1. Trigger manual pipeline run via POST /reporting/pipeline-runs
    post_res = client.post(
        "/reporting/pipeline-runs",
        json={"target_week_start": "2026-08-17", "force_recompute": True},
    )
    assert post_res.status_code == 200
    post_data = post_res.json()
    assert post_data["message"] == "Pipeline run triggered successfully"
    assert post_data["status"] == "COMPLETED"
    assert post_data["target_week_start"] == "2026-08-17"

    # 2. Query latest pipeline run via GET /reporting/pipeline-runs/latest
    latest_res = client.get("/reporting/pipeline-runs/latest")
    assert latest_res.status_code == 200
    latest_data = latest_res.json()
    assert latest_data["execution_status"] == "COMPLETED"
    assert latest_data["target_week_start"] == "2026-08-17"
    assert latest_data["records_extracted"] == 8
    assert latest_data["records_loaded"] == 2

    # 3. Query weekly performance KPIs via GET /reporting/weekly-warehouse-client-performance
    kpi_res = client.get("/reporting/weekly-warehouse-client-performance?week_start=2026-08-17")
    assert kpi_res.status_code == 200
    kpi_data = kpi_res.json()
    assert kpi_data["week_start"] == "2026-08-17"
    assert kpi_data["total_records"] == 2
    assert len(kpi_data["entries"]) == 2

    # Verify fashion-co entry
    fashion_entry = next(e for e in kpi_data["entries"] if e["client_id"] == "fashion-co")
    assert fashion_entry["warehouse"] == "los_angeles"
    assert fashion_entry["inbound_units_count"] == 250
    assert fashion_entry["outbound_orders_count"] == 2
    assert fashion_entry["stockout_events_count"] == 1
    assert fashion_entry["discrepancy_events_count"] == 1
    assert fashion_entry["discrepancy_rate"] == 0.5

    # Verify warehouse filter
    filter_res = client.get("/reporting/weekly-warehouse-client-performance?warehouse=zaragoza")
    assert filter_res.status_code == 200
    filter_data = filter_res.json()
    assert filter_data["total_records"] == 1
    assert filter_data["entries"][0]["warehouse"] == "zaragoza"
    assert filter_data["entries"][0]["client_id"] == "tech-gear"
