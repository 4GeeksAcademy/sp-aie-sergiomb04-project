"""Reporting service functions for querying KPIs and pipeline runs."""

from __future__ import annotations

import logging
from pathlib import Path
import sys
from typing import Any

# Ensure repository root and /workspace are in sys.path
_CURRENT_DIR = Path(__file__).resolve().parent
_CANDIDATE_PATHS = [
    Path("/workspace"),
    Path("/workspace/data"),
    _CURRENT_DIR.parent.parent.parent.parent,
    _CURRENT_DIR.parent.parent.parent,
]

for candidate in _CANDIDATE_PATHS:
    if candidate and candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from sqlmodel import Session, col, desc, select

from trackflow_api.database import get_inventory_engine
from trackflow_api.models import PipelineRunRecord, WeeklyWarehouseClientPerformance

logger = logging.getLogger("trackflow_api.reporting.service")


def get_latest_pipeline_run(
    pipeline_name: str = "weekly_warehouse_client_performance_pipeline",
    engine: Any = None,
) -> dict[str, Any] | None:
    """Retrieve the latest pipeline run record."""
    db_engine = engine or get_inventory_engine()
    with Session(db_engine) as session:
        statement = (
            select(PipelineRunRecord)
            .where(PipelineRunRecord.pipeline_name == pipeline_name)
            .order_by(desc(PipelineRunRecord.started_at))
            .limit(1)
        )
        run = session.exec(statement).first()
        if not run:
            return None

        return {
            "run_id": run.run_id,
            "pipeline_name": run.pipeline_name,
            "execution_status": run.execution_status,
            "target_week_start": run.target_week_start,
            "records_extracted": run.records_extracted,
            "records_loaded": run.records_loaded,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "duration_seconds": run.duration_seconds,
            "triggered_by": run.triggered_by,
            "error_details": run.error_details,
        }


def trigger_pipeline_run(
    target_week_start: str | None = None,
    force_recompute: bool = False,
    triggered_by: str = "manual_api",
    engine: Any = None,
) -> dict[str, Any]:
    """Trigger an execution of the weekly business performance pipeline."""
    try:
        from data.pipelines.pipeline import weekly_warehouse_client_performance_flow
    except ImportError:
        for candidate in [
            Path("/workspace"),
            _CURRENT_DIR.parents[3],
            _CURRENT_DIR.parents[4] if len(_CURRENT_DIR.parents) > 4 else None,
        ]:
            if candidate and str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
        from data.pipelines.pipeline import weekly_warehouse_client_performance_flow

    db_engine = engine or get_inventory_engine()
    result = weekly_warehouse_client_performance_flow(
        target_week_start=target_week_start,
        triggered_by=triggered_by,
        engine=db_engine,
    )
    return {
        "message": "Pipeline run triggered successfully",
        "run_id": result["run_id"],
        "target_week_start": result["target_week_start"],
        "status": result["execution_status"],
    }


def get_weekly_performance_report(
    week_start: str | None = None,
    warehouse: str | None = None,
    client_id: str | None = None,
    engine: Any = None,
) -> dict[str, Any]:
    """Retrieve aggregated warehouse and client performance KPI entries."""
    db_engine = engine or get_inventory_engine()
    with Session(db_engine) as session:
        # If week_start is omitted, resolve latest week_start in the table
        resolved_week = week_start
        if not resolved_week:
            latest_row = session.exec(
                select(WeeklyWarehouseClientPerformance.week_start)
                .order_by(desc(WeeklyWarehouseClientPerformance.week_start))
                .limit(1)
            ).first()
            resolved_week = latest_row or ""

        statement = select(WeeklyWarehouseClientPerformance)
        if resolved_week:
            statement = statement.where(WeeklyWarehouseClientPerformance.week_start == resolved_week)
        if warehouse:
            statement = statement.where(col(WeeklyWarehouseClientPerformance.warehouse).ilike(warehouse.strip()))
        if client_id:
            statement = statement.where(WeeklyWarehouseClientPerformance.client_id == client_id.strip())

        statement = statement.order_by(
            WeeklyWarehouseClientPerformance.warehouse,
            WeeklyWarehouseClientPerformance.client_id,
        )

        rows = session.exec(statement).all()

        entries = [
            {
                "warehouse": row.warehouse,
                "client_id": row.client_id,
                "inbound_units_count": row.inbound_units_count,
                "outbound_orders_count": row.outbound_orders_count,
                "stockout_events_count": row.stockout_events_count,
                "discrepancy_events_count": row.discrepancy_events_count,
                "discrepancy_rate": row.discrepancy_rate,
            }
            for row in rows
        ]

        return {
            "week_start": resolved_week,
            "total_records": len(entries),
            "entries": entries,
        }
