"""CLI Entrypoint for Daily Telemetry KPI Pipeline.

Computes daily operational telemetry metrics and aggregations from database events.
Supports direct execution with --no-prefect flag.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any

# Ensure project roots and services/api are in sys.path
_CURRENT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _CURRENT_DIR.parents[2]
_API_DIR = _REPO_ROOT / "services" / "api"

for path in [_REPO_ROOT, _API_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from services.telemetry.analysis import generate_telemetry_report
from trackflow_api.database import get_inventory_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("telemetry_kpi_daily")


def run_daily_pipeline(
    target_date: date | str | None = None,
    no_prefect: bool = True,
    engine: Any = None,
) -> dict[str, Any]:
    """Execute the daily telemetry KPI pipeline."""
    if target_date is None:
        env_date = os.getenv("TARGET_DATE")
        if env_date:
            resolved_date = date.fromisoformat(env_date.strip())
        else:
            resolved_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    elif isinstance(target_date, str):
        resolved_date = date.fromisoformat(target_date.strip())
    elif isinstance(target_date, datetime):
        resolved_date = target_date.date()
    else:
        resolved_date = target_date

    start_iso = datetime(resolved_date.year, resolved_date.month, resolved_date.day, 0, 0, 0, tzinfo=timezone.utc).isoformat()
    end_iso = (datetime(resolved_date.year, resolved_date.month, resolved_date.day, 0, 0, 0, tzinfo=timezone.utc) + timedelta(days=1)).isoformat()

    logger.info("Executing daily telemetry KPI pipeline for target_date=%s [window: %s to %s]", resolved_date, start_iso, end_iso)

    db_engine = engine or get_inventory_engine()
    report = generate_telemetry_report(start_date=start_iso, end_date=end_iso, engine=db_engine)

    total_events = sum(item.get("count", 0) for item in report.get("metrics", {}).get("events_per_day", []))
    logger.info("Pipeline processed successfully: target_date=%s total_events=%d", resolved_date, total_events)

    return {
        "status": "success",
        "target_date": str(resolved_date),
        "total_events": total_events,
        "metrics_summary": report["metrics"],
    }


def main():
    parser = argparse.ArgumentParser(description="Daily Telemetry KPI Pipeline CLI")
    parser.add_argument(
        "--target-date",
        type=str,
        default=None,
        help="Target date for telemetry processing (YYYY-MM-DD). Defaults to yesterday UTC.",
    )
    parser.add_argument(
        "--no-prefect",
        action="store_true",
        default=False,
        help="Execute directly without Prefect orchestration engine.",
    )

    args = parser.parse_args()

    try:
        result = run_daily_pipeline(
            target_date=args.target_date,
            no_prefect=args.no_prefect,
        )
        print(json.dumps(result, indent=2))
        sys.exit(0)
    except Exception as exc:
        logger.exception("Daily telemetry KPI pipeline execution failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
