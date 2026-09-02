"""Unit Test Suite for TrackFlow Business Performance Pipeline.

Location: tests/pipelines/test_pipeline.py
Focus: In-memory unit tests for Prefect subflows, tasks, and data processing logic.
Zero external database or network dependencies.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd
import pytest

# Ensure repository root and services/api are in sys.path
_TEST_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TEST_DIR.parents[1]
_API_DIR = _REPO_ROOT / "services" / "api"

for path in [_REPO_ROOT, _API_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from data.pipelines.pipeline import (
    extract_telemetry_events_flow,
    load_reporting_metrics_flow,
    optional_notification_subflow,
    transform_warehouse_client_metrics_flow,
    transform_warehouse_client_metrics_task,
    weekly_warehouse_client_performance_flow,
)
from data.process.weekly_performance import (
    calculate_weekly_performance,
    extract_event_payload,
    normalize_raw_events_dataframe,
    resolve_week_range,
)


# ─── Fixtures: In-Memory Telemetry Datasets ───────────────────────────────────

@pytest.fixture
def mock_telemetry_raw_df() -> pd.DataFrame:
    """Fixture providing in-memory telemetry events replicating CONTEXT domain."""
    events = [
        # --- Los Angeles: fashion-co ---
        {
            "event_id": "la-in-1",
            "timestamp": "2026-08-17T10:00:00Z",
            "event_type": "inbound_order_created",
            "service": "backoffice",
            "tags": {"warehouse": "los_angeles", "client_id": "fashion-co", "quantity": 120},
        },
        {
            "event_id": "la-in-2",
            "timestamp": "2026-08-17T14:30:00Z",
            "event_type": "inbound_order_created",
            "service": "backoffice",
            "tags": json.dumps({"warehouse": "los_angeles", "client_id": "fashion-co", "quantity": 180}),
        },
        {
            "event_id": "la-out-1",
            "timestamp": "2026-08-18T09:15:00Z",
            "event_type": "outbound_order_created",
            "service": "backoffice",
            "tags": {"warehouse": "los_angeles", "client_id": "fashion-co", "quantity": 10},
        },
        {
            "event_id": "la-out-2",
            "timestamp": "2026-08-18T16:45:00Z",
            "event_type": "outbound_order_created",
            "service": "backoffice",
            "tags": {"warehouse": "los_angeles", "client_id": "fashion-co", "quantity": 15},
        },
        {
            "event_id": "la-out-3",
            "timestamp": "2026-08-19T11:00:00Z",
            "event_type": "outbound_order_created",
            "service": "backoffice",
            "tags": {"warehouse": "los_angeles", "client_id": "fashion-co", "quantity": 5},
        },
        {
            "event_id": "la-out-4",
            "timestamp": "2026-08-19T14:20:00Z",
            "event_type": "outbound_order_created",
            "service": "backoffice",
            "tags": {"warehouse": "los_angeles", "client_id": "fashion-co", "quantity": 8},
        },
        {
            "event_id": "la-stock-1",
            "timestamp": "2026-08-20T08:00:00Z",
            "event_type": "stock_threshold_triggered",
            "service": "backoffice",
            "tags": {"warehouse": "los_angeles", "client_id": "fashion-co", "deficit_units": 15},
        },
        {
            "event_id": "la-stock-2",
            "timestamp": "2026-08-20T13:30:00Z",
            "event_type": "stock_threshold_triggered",
            "service": "backoffice",
            "tags": {"warehouse": "los_angeles", "client_id": "fashion-co", "deficit_units": 20},
        },
        {
            "event_id": "la-disc-1",
            "timestamp": "2026-08-21T10:00:00Z",
            "event_type": "inventory_discrepancy_detected",
            "service": "backoffice",
            "tags": {"warehouse": "los_angeles", "client_id": "fashion-co", "discrepancy_units": 2},
        },

        # --- Zaragoza: tech-gear ---
        {
            "event_id": "zgz-in-1",
            "timestamp": "2026-08-17T08:00:00Z",
            "event_type": "inbound_order_created",
            "service": "backoffice",
            "tags": {"warehouse": "zaragoza", "client_id": "tech-gear", "quantity": 500},
        },
        {
            "event_id": "zgz-out-1",
            "timestamp": "2026-08-18T10:00:00Z",
            "event_type": "outbound_order_created",
            "service": "backoffice",
            "tags": {"warehouse": "zaragoza", "client_id": "tech-gear", "quantity": 50},
        },
        {
            "event_id": "zgz-out-2",
            "timestamp": "2026-08-19T10:00:00Z",
            "event_type": "outbound_order_created",
            "service": "backoffice",
            "tags": {"warehouse": "zaragoza", "client_id": "tech-gear", "quantity": 50},
        },
        # (Zero stockouts, zero discrepancies for tech-gear)

        # --- Zaragoza: beauty-box (Edge case: 0 outbound orders, 1 discrepancy) ---
        {
            "event_id": "zgz-bb-in-1",
            "timestamp": "2026-08-17T11:00:00Z",
            "event_type": "inbound_order_created",
            "service": "backoffice",
            "tags": {"warehouse": "zaragoza", "client_id": "beauty-box", "quantity": 75},
        },
        {
            "event_id": "zgz-bb-disc-1",
            "timestamp": "2026-08-20T15:00:00Z",
            "event_type": "inventory_discrepancy_detected",
            "service": "backoffice",
            "tags": {"warehouse": "zaragoza", "client_id": "beauty-box", "discrepancy_units": 1},
        },
    ]
    return pd.DataFrame(events)


# ─── Test Unitario 1: KPI #1 (Inbound Units Count) ────────────────────────────

def test_kpi1_inbound_units_count(mock_telemetry_raw_df: pd.DataFrame):
    """Test KPI #1: Inbound volume must accurately sum the quantities from inbound_order_created."""
    metrics_df = transform_warehouse_client_metrics_task.fn(
        raw_df=mock_telemetry_raw_df,
        target_week_start="2026-08-17",
    )

    # 1. Los Angeles - fashion-co: 120 + 180 = 300
    la_fashion = metrics_df[
        (metrics_df["warehouse"] == "los_angeles") & (metrics_df["client_id"] == "fashion-co")
    ].iloc[0]
    assert la_fashion["inbound_units_count"] == 300

    # 2. Zaragoza - tech-gear: 500
    zgz_tech = metrics_df[
        (metrics_df["warehouse"] == "zaragoza") & (metrics_df["client_id"] == "tech-gear")
    ].iloc[0]
    assert zgz_tech["inbound_units_count"] == 500

    # 3. Zaragoza - beauty-box: 75
    zgz_beauty = metrics_df[
        (metrics_df["warehouse"] == "zaragoza") & (metrics_df["client_id"] == "beauty-box")
    ].iloc[0]
    assert zgz_beauty["inbound_units_count"] == 75


# ─── Test Unitario 2: KPI #2 (Outbound Orders Count) ───────────────────────────

def test_kpi2_outbound_orders_count(mock_telemetry_raw_df: pd.DataFrame):
    """Test KPI #2: Outbound throughput must count distinct outbound_order_created events."""
    metrics_df = transform_warehouse_client_metrics_task.fn(
        raw_df=mock_telemetry_raw_df,
        target_week_start="2026-08-17",
    )

    # 1. Los Angeles - fashion-co: 4 distinct orders
    la_fashion = metrics_df[
        (metrics_df["warehouse"] == "los_angeles") & (metrics_df["client_id"] == "fashion-co")
    ].iloc[0]
    assert la_fashion["outbound_orders_count"] == 4

    # 2. Zaragoza - tech-gear: 2 distinct orders
    zgz_tech = metrics_df[
        (metrics_df["warehouse"] == "zaragoza") & (metrics_df["client_id"] == "tech-gear")
    ].iloc[0]
    assert zgz_tech["outbound_orders_count"] == 2

    # 3. Zaragoza - beauty-box: 0 orders
    zgz_beauty = metrics_df[
        (metrics_df["warehouse"] == "zaragoza") & (metrics_df["client_id"] == "beauty-box")
    ].iloc[0]
    assert zgz_beauty["outbound_orders_count"] == 0


# ─── Test Unitario 3: KPI #3, #4, #5 (Stockouts, Discrepancies & Rate) ─────────

def test_kpi3_stockout_discrepancies_and_rate(mock_telemetry_raw_df: pd.DataFrame):
    """Test KPIs #3, #4, #5: Stockout count, Discrepancy count, and Discrepancy Rate."""
    metrics_df = transform_warehouse_client_metrics_task.fn(
        raw_df=mock_telemetry_raw_df,
        target_week_start="2026-08-17",
    )

    # 1. Los Angeles - fashion-co: 2 stockouts, 1 discrepancy, rate = 1 / 4 = 0.25
    la_fashion = metrics_df[
        (metrics_df["warehouse"] == "los_angeles") & (metrics_df["client_id"] == "fashion-co")
    ].iloc[0]
    assert la_fashion["stockout_events_count"] == 2
    assert la_fashion["discrepancy_events_count"] == 1
    assert la_fashion["discrepancy_rate"] == 0.25

    # 2. Zaragoza - tech-gear: 0 stockouts, 0 discrepancies, rate = 0 / 2 = 0.0
    zgz_tech = metrics_df[
        (metrics_df["warehouse"] == "zaragoza") & (metrics_df["client_id"] == "tech-gear")
    ].iloc[0]
    assert zgz_tech["stockout_events_count"] == 0
    assert zgz_tech["discrepancy_events_count"] == 0
    assert zgz_tech["discrepancy_rate"] == 0.0

    # 3. Zaragoza - beauty-box: 0 stockouts, 1 discrepancy, 0 outbound orders -> rate = 0.0 (safe division)
    zgz_beauty = metrics_df[
        (metrics_df["warehouse"] == "zaragoza") & (metrics_df["client_id"] == "beauty-box")
    ].iloc[0]
    assert zgz_beauty["stockout_events_count"] == 0
    assert zgz_beauty["discrepancy_events_count"] == 1
    assert zgz_beauty["discrepancy_rate"] == 0.0


# ─── Test Defensivo: Datos Malformados, Nulos y Tipos Inválidos ───────────────

def test_defensive_data_handling():
    """Test Defensive: Ensure tasks handle malformed entries, nulls, invalid tags, and duplicates safely."""
    # 1. Empty DataFrame produces expected empty schema
    empty_res = calculate_weekly_performance(pd.DataFrame(), "2026-08-17")
    assert isinstance(empty_res, pd.DataFrame)
    assert empty_res.empty
    assert "inbound_units_count" in empty_res.columns
    assert "discrepancy_rate" in empty_res.columns

    # 2. DataFrame with missing tags, invalid JSON, nulls, and duplicate event_ids
    dirty_data = pd.DataFrame([
        # Valid entry
        {
            "event_id": "valid-1",
            "timestamp": "2026-08-17T10:00:00Z",
            "event_type": "inbound_order_created",
            "tags": {"warehouse": "los_angeles", "client_id": "client-clean", "quantity": 100},
        },
        # Duplicate of valid-1 (must be deduplicated)
        {
            "event_id": "valid-1",
            "timestamp": "2026-08-17T10:00:00Z",
            "event_type": "inbound_order_created",
            "tags": {"warehouse": "los_angeles", "client_id": "client-clean", "quantity": 100},
        },
        # Malformed JSON string in tags
        {
            "event_id": "dirty-1",
            "timestamp": "2026-08-17T11:00:00Z",
            "event_type": "inbound_order_created",
            "tags": "{invalid-json-string",
        },
        # None tags
        {
            "event_id": "dirty-2",
            "timestamp": "2026-08-17T12:00:00Z",
            "event_type": "outbound_order_created",
            "tags": None,
        },
        # Missing warehouse/client_id in tags
        {
            "event_id": "dirty-3",
            "timestamp": "2026-08-17T13:00:00Z",
            "event_type": "inbound_order_created",
            "tags": {"quantity": 50},
        },
        # Non-numeric quantity
        {
            "event_id": "dirty-4",
            "timestamp": "2026-08-17T14:00:00Z",
            "event_type": "inbound_order_created",
            "tags": {"warehouse": "los_angeles", "client_id": "client-clean", "quantity": "invalid_qty"},
        },
    ])

    metrics_df = calculate_weekly_performance(dirty_data, "2026-08-17")
    assert len(metrics_df) == 1
    clean_row = metrics_df.iloc[0]
    assert clean_row["client_id"] == "client-clean"
    # 100 from valid-1 + 0 from invalid_qty (coerced safely) = 100
    assert clean_row["inbound_units_count"] == 100


# ─── Test de Validación Matemática: Fórmulas Teóricas vs Calculadas ───────────

def test_mathematical_validation_hand_calculated():
    """Test Mathematical Validation: Verify calculated numbers against exact hand-calculated ground truth.

    Formulas from CONTEXT:
    - inbound_units_count = SUM(quantity) of inbound_order_created
    - outbound_orders_count = COUNT(event_id) of outbound_order_created
    - stockout_events_count = COUNT(event_id) of stock_threshold_triggered
    - discrepancy_events_count = COUNT(event_id) of inventory_discrepancy_detected
    - discrepancy_rate = discrepancy_events_count / outbound_orders_count (if outbound_orders_count > 0 else 0.0)
    """
    hand_crafted_events = pd.DataFrame([
        # Warehouse: zaragoza | Client: apex-store
        {"event_id": "e1", "timestamp": "2026-08-17T01:00:00Z", "event_type": "inbound_order_created", "tags": {"warehouse": "zaragoza", "client_id": "apex-store", "quantity": 340}},
        {"event_id": "e2", "timestamp": "2026-08-17T02:00:00Z", "event_type": "inbound_order_created", "tags": {"warehouse": "zaragoza", "client_id": "apex-store", "quantity": 160}},
        {"event_id": "e3", "timestamp": "2026-08-18T05:00:00Z", "event_type": "outbound_order_created", "tags": {"warehouse": "zaragoza", "client_id": "apex-store", "quantity": 25}},
        {"event_id": "e4", "timestamp": "2026-08-18T06:00:00Z", "event_type": "outbound_order_created", "tags": {"warehouse": "zaragoza", "client_id": "apex-store", "quantity": 15}},
        {"event_id": "e5", "timestamp": "2026-08-18T07:00:00Z", "event_type": "outbound_order_created", "tags": {"warehouse": "zaragoza", "client_id": "apex-store", "quantity": 10}},
        {"event_id": "e6", "timestamp": "2026-08-18T08:00:00Z", "event_type": "outbound_order_created", "tags": {"warehouse": "zaragoza", "client_id": "apex-store", "quantity": 30}},
        {"event_id": "e7", "timestamp": "2026-08-18T09:00:00Z", "event_type": "outbound_order_created", "tags": {"warehouse": "zaragoza", "client_id": "apex-store", "quantity": 20}},
        {"event_id": "e8", "timestamp": "2026-08-19T10:00:00Z", "event_type": "stock_threshold_triggered", "tags": {"warehouse": "zaragoza", "client_id": "apex-store"}},
        {"event_id": "e9", "timestamp": "2026-08-19T11:00:00Z", "event_type": "stock_threshold_triggered", "tags": {"warehouse": "zaragoza", "client_id": "apex-store"}},
        {"event_id": "e10", "timestamp": "2026-08-19T12:00:00Z", "event_type": "stock_threshold_triggered", "tags": {"warehouse": "zaragoza", "client_id": "apex-store"}},
        {"event_id": "e11", "timestamp": "2026-08-20T13:00:00Z", "event_type": "inventory_discrepancy_detected", "tags": {"warehouse": "zaragoza", "client_id": "apex-store"}},
    ])

    # Theoretical Values calculated manually:
    # inbound_units_count: 340 + 160 = 500
    # outbound_orders_count: 5 orders
    # stockout_events_count: 3 events
    # discrepancy_events_count: 1 event
    # discrepancy_rate: 1 / 5 = 0.2000 (20.0%)

    result_df = calculate_weekly_performance(hand_crafted_events, target_week_start="2026-08-17")
    assert len(result_df) == 1
    row = result_df.iloc[0]

    assert row["warehouse"] == "zaragoza"
    assert row["client_id"] == "apex-store"
    assert row["week_start"] == "2026-08-17"
    assert row["inbound_units_count"] == 500
    assert row["outbound_orders_count"] == 5
    assert row["stockout_events_count"] == 3
    assert row["discrepancy_events_count"] == 1
    assert np.isclose(row["discrepancy_rate"], 0.2, atol=1e-4)


# ─── Test Prefect Subflows in Isolation ───────────────────────────────────────

def test_subflows_in_isolation(mock_telemetry_raw_df: pd.DataFrame):
    """Verify that Prefect subflows execute with typed signatures and produce valid outputs."""
    # 1. Transform subflow
    transformed_df = transform_warehouse_client_metrics_flow(
        raw_df=mock_telemetry_raw_df,
        target_week_start="2026-08-17",
    )
    assert isinstance(transformed_df, pd.DataFrame)
    assert len(transformed_df) == 3

    # 2. Optional notification subflow
    summary = {"records_loaded": len(transformed_df), "target_week_start": "2026-08-17"}
    notif_res = optional_notification_subflow(summary_data=summary, simulate_failure=False)
    assert notif_res["notified"] is True
    assert notif_res["records_processed"] == 3
    assert notif_res["target_week_start"] == "2026-08-17"
