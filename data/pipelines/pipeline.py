"""Resilient Business Performance Data Pipeline (TrackFlow).

Orchestrates weekly warehouse and client performance metric calculations from telemetry_events
into reporting tables using Prefect 3 subflows, with vectorized Pandas transformations, caching,
retry policies, error isolation and atomic idempotent UPSERT.

Scheduled Execution: Weekly on Mondays at 05:00:00 UTC (Cron: 0 5 * * 1)
CLI Execution: python data/pipelines/pipeline.py [--week-start YYYY-MM-DD] [--triggered-by cli]
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

# Ensure project roots and services/api are in sys.path for direct CLI and module execution
_CURRENT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _CURRENT_DIR.parents[1]
_API_DIR = _REPO_ROOT / "services" / "api"

for path in [_REPO_ROOT, _API_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import pandas as pd
from prefect import flow, task
from prefect.cache_policies import NO_CACHE
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session, select

from data.process.weekly_performance import (
    calculate_weekly_performance,
    resolve_week_range,
)
from trackflow_api.database import get_inventory_engine, init_inventory_db
from trackflow_api.models import PipelineRunRecord, WeeklyWarehouseClientPerformance

logger = logging.getLogger("trackflow.pipelines.weekly_performance")


# ─── Cache Key Function for Transformation Task ───────────────────────────────

def _transformation_cache_key(context: Any, parameters: dict[str, Any]) -> str:
    """Generate deterministic cache key for the transformation task.

    Parameters:
    - `context`: Prefect execution context (contains run metadata and timestamps).
    - `parameters`: Dictionary with task arguments (`raw_df` and `target_week_start`).

    The hash combines the target week start and the row count / schema of raw events
    so that identical input telemetry datasets for the same week avoid re-running
    expensive aggregations within the cache TTL window (15 minutes).
    """
    raw_df: pd.DataFrame = parameters.get("raw_df", pd.DataFrame())
    week_start: str = str(parameters.get("target_week_start", ""))
    df_shape = f"{len(raw_df)}x{len(raw_df.columns)}"
    df_checksum = hashlib.sha256(f"{week_start}_{df_shape}_{list(raw_df.columns)}".encode()).hexdigest()[:16]
    return f"weekly_transform_{week_start}_{df_checksum}"


# ─── Prefect Tasks ────────────────────────────────────────────────────────────

@task(
    name="extract_telemetry_events",
    retries=3,
    retry_delay_seconds=5,
    cache_policy=NO_CACHE,
    description="Extract raw operational events from telemetry_events within the specified UTC window with retry backoff.",
)
def extract_telemetry_events_task(
    start_iso: str,
    end_iso: str,
    engine: Any = None,
) -> pd.DataFrame:
    """Extract operational telemetry events for the target week window.

    Resilience note: Configured with 3 retries and 5-second delay to withstand
    transient database network hiccups or connection pool contention during peak operations.
    """
    db_engine = engine or get_inventory_engine()
    query = text(
        "SELECT event_id, timestamp, event_type, service, tags "
        "FROM telemetry_events "
        "WHERE timestamp >= :start AND timestamp < :end "
        "AND event_type IN ('inbound_order_created', 'outbound_order_created', 'stock_threshold_triggered', 'inventory_discrepancy_detected') "
        "ORDER BY timestamp ASC"
    )

    with db_engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"start": start_iso, "end": end_iso})

    logger.info(
        "Extracted %d telemetry events for window %s to %s",
        len(df),
        start_iso,
        end_iso,
    )
    return df


@task(
    name="transform_warehouse_client_metrics",
    cache_key_fn=_transformation_cache_key,
    cache_expiration=timedelta(minutes=15),
    description="Vectorized transformation of raw events into weekly performance KPIs with 15-min cache.",
)
def transform_warehouse_client_metrics_task(
    raw_df: pd.DataFrame,
    target_week_start: str,
) -> pd.DataFrame:
    """Transform raw events into structured weekly KPIs per warehouse and client.

    Caching note: `cache_expiration=timedelta(minutes=15)` caches computation results
    when re-running for the same week window with identical raw event counts.
    """
    metrics_df = calculate_weekly_performance(raw_df, target_week_start)
    logger.info(
        "Computed %d aggregated rows for week_start %s",
        len(metrics_df),
        target_week_start,
    )
    return metrics_df


@task(
    name="load_reporting_metrics",
    retries=2,
    retry_delay_seconds=3,
    cache_policy=NO_CACHE,
    description="Load aggregated metrics into weekly_warehouse_client_performance using atomic idempotent UPSERT.",
)
def load_reporting_metrics_task(
    metrics_df: pd.DataFrame,
    engine: Any = None,
) -> int:
    """Persist aggregated metrics idempotently.

    Resilience and Idempotency note:
    Uses dialect-aware ON CONFLICT DO UPDATE on `(warehouse, client_id, week_start)`
    to ensure re-executing 1 or 100 times updates existing values without duplicating rows.
    Configured with 2 retries and 3-second delay against database locks.
    """
    if metrics_df.empty:
        logger.info("No metric rows to persist.")
        return 0

    db_engine = engine or get_inventory_engine()
    records = metrics_df.to_dict(orient="records")
    dialect_name = db_engine.dialect.name
    table = WeeklyWarehouseClientPerformance.__table__

    with db_engine.begin() as conn:
        if dialect_name == "sqlite":
            stmt = sqlite_insert(table).values(records)
            stmt = stmt.on_conflict_do_update(
                index_elements=["warehouse", "client_id", "week_start"],
                set_={
                    "inbound_units_count": stmt.excluded.inbound_units_count,
                    "outbound_orders_count": stmt.excluded.outbound_orders_count,
                    "stockout_events_count": stmt.excluded.stockout_events_count,
                    "discrepancy_events_count": stmt.excluded.discrepancy_events_count,
                    "discrepancy_rate": stmt.excluded.discrepancy_rate,
                    "computed_at": stmt.excluded.computed_at,
                },
            )
            conn.execute(stmt)
        elif dialect_name == "postgresql":
            stmt = pg_insert(table).values(records)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_weekly_warehouse_client",
                set_={
                    "inbound_units_count": stmt.excluded.inbound_units_count,
                    "outbound_orders_count": stmt.excluded.outbound_orders_count,
                    "stockout_events_count": stmt.excluded.stockout_events_count,
                    "discrepancy_events_count": stmt.excluded.discrepancy_events_count,
                    "discrepancy_rate": stmt.excluded.discrepancy_rate,
                    "computed_at": stmt.excluded.computed_at,
                },
            )
            conn.execute(stmt)
        else:
            # Generic fallback using SQLModel session merge
            with Session(db_engine) as session:
                for rec in records:
                    existing = session.exec(
                        select(WeeklyWarehouseClientPerformance).where(
                            WeeklyWarehouseClientPerformance.warehouse == rec["warehouse"],
                            WeeklyWarehouseClientPerformance.client_id == rec["client_id"],
                            WeeklyWarehouseClientPerformance.week_start == rec["week_start"],
                        )
                    ).first()
                    if existing:
                        for k, v in rec.items():
                            setattr(existing, k, v)
                    else:
                        session.add(WeeklyWarehouseClientPerformance(**rec))
                session.commit()

    logger.info("Successfully loaded %d records into weekly_warehouse_client_performance", len(records))
    return len(records)


@task(
    name="optional_pipeline_notification",
    cache_policy=NO_CACHE,
    description="Non-critical step to dispatch notification or export summary. Handled with return_state=True.",
)
def optional_pipeline_notification_task(
    summary_data: dict[str, Any],
    simulate_failure: bool = False,
) -> dict[str, Any]:
    """Optional non-critical task for alerting or webhook dispatch.

    Error Isolation note: If this task encounters an issue or external webhook timeout,
    its execution state is inspected in the flow via `return_state=True` without failing the main pipeline.
    """
    if simulate_failure:
        raise ConnectionError("Simulated external notification service downtime")
    return {
        "notified": True,
        "records_processed": summary_data.get("records_loaded", 0),
        "target_week_start": summary_data.get("target_week_start", ""),
    }


# ─── Prefect Subflows ─────────────────────────────────────────────────────────

@flow(
    name="extract-telemetry-events-subflow",
    description="Subflow for extracting operational telemetry events within the target UTC window.",
)
def extract_telemetry_events_flow(
    start_iso: str,
    end_iso: str,
    engine: Any = None,
) -> pd.DataFrame:
    """Extraction Subflow: queries raw events from telemetry_events with retry policies."""
    logger.info("Starting extraction subflow for window: %s to %s", start_iso, end_iso)
    raw_df = extract_telemetry_events_task(
        start_iso=start_iso,
        end_iso=end_iso,
        engine=engine,
    )
    return raw_df


@flow(
    name="transform-warehouse-client-metrics-subflow",
    description="Subflow for calculating weekly warehouse and client performance KPIs using vectorized Pandas.",
)
def transform_warehouse_client_metrics_flow(
    raw_df: pd.DataFrame,
    target_week_start: str,
) -> pd.DataFrame:
    """Transformation Subflow: transforms raw telemetry events into aggregated weekly KPIs."""
    logger.info("Starting transformation subflow for week_start: %s", target_week_start)
    metrics_df = transform_warehouse_client_metrics_task(
        raw_df=raw_df,
        target_week_start=target_week_start,
    )
    return metrics_df


@flow(
    name="load-reporting-metrics-subflow",
    description="Subflow for atomically loading aggregated metrics into reporting tables with idempotent UPSERT.",
)
def load_reporting_metrics_flow(
    metrics_df: pd.DataFrame,
    engine: Any = None,
) -> int:
    """Loading Subflow: executes idempotent upsert into weekly_warehouse_client_performance."""
    logger.info("Starting load subflow for %d metric records", len(metrics_df))
    records_loaded = load_reporting_metrics_task(
        metrics_df=metrics_df,
        engine=engine,
    )
    return records_loaded


@flow(
    name="optional-notification-subflow",
    description="Non-critical subflow for dispatching alerts or webhook notifications.",
)
def optional_notification_subflow(
    summary_data: dict[str, Any],
    simulate_failure: bool = False,
) -> dict[str, Any]:
    """Auxiliary Subflow: handles alerts without risking main pipeline failure."""
    return optional_pipeline_notification_task(
        summary_data=summary_data,
        simulate_failure=simulate_failure,
    )


# ─── Audit Recording Helpers ──────────────────────────────────────────────────

def _record_run_start(
    run_id: str,
    target_week_start: str,
    triggered_by: str,
    engine: Any = None,
) -> None:
    """Create initial RUNNING record in pipeline_runs."""
    db_engine = engine or get_inventory_engine()
    now_iso = datetime.now(timezone.utc).isoformat()
    record = PipelineRunRecord(
        run_id=run_id,
        pipeline_name="weekly_warehouse_client_performance_pipeline",
        execution_status="RUNNING",
        target_week_start=target_week_start,
        records_extracted=0,
        records_loaded=0,
        started_at=now_iso,
        triggered_by=triggered_by,
    )
    with Session(db_engine) as session:
        session.add(record)
        session.commit()


def _record_run_completion(
    run_id: str,
    status: str,
    records_extracted: int,
    records_loaded: int,
    started_at_dt: datetime,
    error_details: dict[str, Any] | None = None,
    engine: Any = None,
) -> None:
    """Update pipeline_runs record with final status and timing."""
    db_engine = engine or get_inventory_engine()
    completed_at_dt = datetime.now(timezone.utc)
    completed_iso = completed_at_dt.isoformat()
    duration_seconds = round((completed_at_dt - started_at_dt).total_seconds(), 3)

    with Session(db_engine) as session:
        run = session.get(PipelineRunRecord, run_id)
        if run:
            run.execution_status = status
            run.records_extracted = records_extracted
            run.records_loaded = records_loaded
            run.completed_at = completed_iso
            run.duration_seconds = duration_seconds
            run.error_details = error_details
            session.add(run)
            session.commit()


# ─── Main Flow (Orchestrator) ─────────────────────────────────────────────────

@flow(
    name="weekly-warehouse-client-performance-flow",
    description="End-to-end resilient business performance pipeline flow orchestrating extraction, transformation, load, and notification subflows.",
)
def weekly_warehouse_client_performance_flow(
    target_week_start: str | None = None,
    triggered_by: str = "scheduler",
    simulate_optional_failure: bool = False,
    engine: Any = None,
) -> dict[str, Any]:
    """Execute the full business performance ETL pipeline via modular subflows.

    Flow Steps:
    1. Resolve target week Monday and extraction window.
    2. Initialize database schemas & audit record in `pipeline_runs`.
    3. Extract operational events via `extract_telemetry_events_flow` (Subflow 1).
    4. Transform raw events vectorially via `transform_warehouse_client_metrics_flow` (Subflow 2).
    5. Persist aggregated metrics using atomic UPSERT via `load_reporting_metrics_flow` (Subflow 3).
    6. Execute optional notification step using `return_state=True` to isolate failures.
    7. Finalize audit record with timing and status.
    """
    init_inventory_db()
    db_engine = engine or get_inventory_engine()

    week_start, start_iso, end_iso = resolve_week_range(target_week_start)
    run_id = str(uuid4())
    started_at_dt = datetime.now(timezone.utc)

    # Step 1: Record run start
    _record_run_start(run_id, week_start, triggered_by, engine=db_engine)

    records_extracted = 0
    records_loaded = 0

    try:
        # Step 2: Extraction Subflow
        raw_df = extract_telemetry_events_flow(
            start_iso=start_iso,
            end_iso=end_iso,
            engine=db_engine,
        )
        records_extracted = len(raw_df)

        # Step 3: Transformation Subflow
        metrics_df = transform_warehouse_client_metrics_flow(
            raw_df=raw_df,
            target_week_start=week_start,
        )

        # Step 4: Idempotent Load Subflow
        records_loaded = load_reporting_metrics_flow(
            metrics_df=metrics_df,
            engine=db_engine,
        )

        # Step 5: Optional non-critical step handled with return_state=True
        optional_state = optional_notification_subflow(
            summary_data={"records_loaded": records_loaded, "target_week_start": week_start},
            simulate_failure=simulate_optional_failure,
            return_state=True,
        )

        if optional_state.is_failed():
            logger.warning(
                "Optional notification subflow failed (isolated, main flow succeeds): %s",
                optional_state.message,
            )
        else:
            logger.info("Optional notification subflow completed successfully.")

        # Step 6: Mark pipeline run as COMPLETED
        _record_run_completion(
            run_id=run_id,
            status="COMPLETED",
            records_extracted=records_extracted,
            records_loaded=records_loaded,
            started_at_dt=started_at_dt,
            error_details=None,
            engine=db_engine,
        )

        return {
            "run_id": run_id,
            "pipeline_name": "weekly_warehouse_client_performance_pipeline",
            "execution_status": "COMPLETED",
            "target_week_start": week_start,
            "records_extracted": records_extracted,
            "records_loaded": records_loaded,
            "started_at": started_at_dt.isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": round((datetime.now(timezone.utc) - started_at_dt).total_seconds(), 3),
            "triggered_by": triggered_by,
        }

    except Exception as exc:
        logger.exception("Pipeline execution failed for run_id %s: %s", run_id, exc)
        error_details = {
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
        _record_run_completion(
            run_id=run_id,
            status="FAILED",
            records_extracted=records_extracted,
            records_loaded=records_loaded,
            started_at_dt=started_at_dt,
            error_details=error_details,
            engine=db_engine,
        )
        raise


# ─── CLI Entrypoint ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run TrackFlow Resilient Weekly Business Performance Pipeline"
    )
    parser.add_argument(
        "--week-start",
        type=str,
        default=None,
        help="Target week start date (YYYY-MM-DD). Defaults to previous Monday.",
    )
    parser.add_argument(
        "--triggered-by",
        type=str,
        default="cli",
        help="Trigger source tag (default: 'cli').",
    )

    args = parser.parse_args()

    print(f"\n🚀 Running TrackFlow Business Performance Pipeline for week: {args.week_start or 'auto (previous Monday)'}...")
    result = weekly_warehouse_client_performance_flow(
        target_week_start=args.week_start,
        triggered_by=args.triggered_by,
    )
    print("\n✅ Pipeline completed successfully!")
    print(json.dumps(result, indent=2))
