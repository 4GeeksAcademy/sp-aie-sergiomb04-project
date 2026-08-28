"""Nightly Telemetry Export & Execution Control Script (Ticket #DEV-53).

Orchestrates nightly telemetry raw CSV backup export and triggers data pipeline execution
with state-machine idempotency and distributed locking via database state in `job_runs`.

Usage:
    python scripts/nightly_export.py [--target-date YYYY-MM-DD]
Or set TARGET_DATE environment variable.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Callable

# Ensure repository root and services/api are in sys.path
_CURRENT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _CURRENT_DIR.parent
_API_DIR = _REPO_ROOT / "services" / "api"

for path in [_REPO_ROOT, _API_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import pandas as pd
from sqlalchemy import text
from sqlmodel import Session

from services.job_runner import (
    create_job_run,
    has_completed_for_date,
    has_processing_lock,
    mark_as_completed,
    mark_as_failed,
)
from trackflow_api.database import get_inventory_engine
from trackflow_api.models import JobRunStatusEnum

JOB_NAME = "nightly_export"

# Logger formatting matching specification
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(JOB_NAME)


def resolve_target_date(cli_date: str | None = None) -> date:
    """Resolve target date from CLI argument, TARGET_DATE env var, or yesterday UTC."""
    if cli_date and cli_date.strip():
        return date.fromisoformat(cli_date.strip())
    env_date = os.getenv("TARGET_DATE")
    if env_date and env_date.strip():
        return date.fromisoformat(env_date.strip())
    return (datetime.now(timezone.utc) - timedelta(days=1)).date()


def export_telemetry_csv(
    target_date: date,
    raw_dir: Path | None = None,
    engine: Any = None,
) -> Path:
    """Export telemetry_events for target_date into data/raw/telemetry_<target_date>.csv if not already present.
    
    Backup snapshot only (Pipeline subprocesos read directly from DB).
    """
    target_dir = raw_dir or (_REPO_ROOT / "data" / "raw")
    target_dir.mkdir(parents=True, exist_ok=True)
    csv_file = target_dir / f"telemetry_{target_date.isoformat()}.csv"

    if csv_file.exists():
        logger.info(
            "[%s] [target_date=%s] Backup CSV already exists at %s, skipping raw generation.",
            JOB_NAME,
            target_date,
            csv_file,
        )
        return csv_file

    start_iso = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=timezone.utc).isoformat()
    end_iso = (datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=timezone.utc) + timedelta(days=1)).isoformat()

    db_engine = engine or get_inventory_engine()
    query = text(
        "SELECT event_id, event_type, user_id, timestamp, tags "
        "FROM telemetry_events "
        "WHERE timestamp >= :start AND timestamp < :end "
        "ORDER BY timestamp ASC"
    )

    with db_engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"start": start_iso, "end": end_iso})

    if df.empty:
        # Create empty CSV with proper headers
        export_df = pd.DataFrame(columns=["event_id", "event_name", "user_id", "timestamp", "payload"])
    else:
        def _serialize_payload(tags_val: Any) -> str:
            if isinstance(tags_val, dict):
                return json.dumps(tags_val)
            if isinstance(tags_val, str):
                try:
                    # Validate and re-dump to ensure clean JSON string format
                    parsed = json.loads(tags_val)
                    return json.dumps(parsed)
                except Exception:
                    return tags_val
            return "{}"

        export_df = pd.DataFrame()
        export_df["event_id"] = df["event_id"]
        export_df["event_name"] = df["event_type"]
        export_df["user_id"] = df["user_id"].fillna("")
        export_df["timestamp"] = df["timestamp"]
        export_df["payload"] = df["tags"].apply(_serialize_payload)

    export_df.to_csv(csv_file, index=False)
    logger.info(
        "[%s] [target_date=%s] Exported %d telemetry events to %s",
        JOB_NAME,
        target_date,
        len(export_df),
        csv_file,
    )
    return csv_file


def default_subprocess_runner(
    target_date: date,
    repo_root: Path,
) -> None:
    """Execute the data pipeline subprocess."""
    cmd = [
        sys.executable,
        "-m",
        "data.pipelines.telemetry_kpi_daily.run",
        "--no-prefect",
        "--target-date",
        target_date.isoformat(),
    ]
    env = os.environ.copy()
    env["TARGET_DATE"] = target_date.isoformat()

    logger.info(
        "[%s] [target_date=%s] Triggering pipeline subprocess: %s",
        JOB_NAME,
        target_date,
        " ".join(cmd),
    )

    result = subprocess.run(
        cmd,
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        error_msg = f"Pipeline subprocess failed with exit code {result.returncode}:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        logger.error("[%s] [target_date=%s] %s", JOB_NAME, target_date, error_msg)
        raise RuntimeError(error_msg)

    logger.info(
        "[%s] [target_date=%s] Pipeline subprocess completed successfully.",
        JOB_NAME,
        target_date,
    )


def run_nightly_export(
    target_date: date | str | None = None,
    engine: Any = None,
    raw_dir: Path | None = None,
    subprocess_runner: Callable[[date, Path], None] | None = None,
) -> dict[str, Any]:
    """Execute the full nightly export workflow with locking, idempotency and anti-zombie guarantee."""
    start_time = time.time()
    resolved_date = resolve_target_date(str(target_date) if target_date is not None else None)
    db_engine = engine or get_inventory_engine()
    runner = subprocess_runner or default_subprocess_runner

    # 1. Check Distributed Lock
    if has_processing_lock(job_name=JOB_NAME, engine=db_engine):
        logger.info(
            "[%s] [target_date=%s] Status: locked - Another %s job is currently processing. Aborting quietly.",
            JOB_NAME,
            resolved_date,
            JOB_NAME,
        )
        return {
            "status": "locked",
            "target_date": resolved_date.isoformat(),
            "job_id": None,
        }

    # 2. Check Idempotency for Target Date
    if has_completed_for_date(job_name=JOB_NAME, target_date=resolved_date, engine=db_engine):
        logger.info(
            "[%s] [target_date=%s] Status: skipped - Job already completed for target date.",
            JOB_NAME,
            resolved_date,
        )
        return {
            "status": "skipped",
            "target_date": resolved_date.isoformat(),
            "job_id": None,
        }

    # 3. Create Job Run in PROCESSING state
    job_run = create_job_run(
        job_name=JOB_NAME,
        target_date=resolved_date,
        status=JobRunStatusEnum.PROCESSING.value,
        engine=db_engine,
    )
    job_id = job_run.id

    logger.info(
        "[%s] [target_date=%s] Status: processing - Exporting CSV & triggering pipeline (job_id=%s)",
        JOB_NAME,
        resolved_date,
        job_id,
    )

    # 4. Execute Workflow with Anti-Zombie Protection
    try:
        # Step A: Export CSV backup snapshot
        csv_path = export_telemetry_csv(
            target_date=resolved_date,
            raw_dir=raw_dir,
            engine=db_engine,
        )

        # Step B: Trigger data pipeline subprocess
        runner(resolved_date, _REPO_ROOT)

        # Step C: Transition to COMPLETED
        mark_as_completed(job_id=job_id, engine=db_engine)
        elapsed_seconds = round(time.time() - start_time, 2)
        logger.info(
            "[%s] [target_date=%s] Status: completed - Finished successfully in %.1fs",
            JOB_NAME,
            resolved_date,
            elapsed_seconds,
        )
        return {
            "status": "completed",
            "target_date": resolved_date.isoformat(),
            "job_id": job_id,
            "csv_path": str(csv_path),
            "elapsed_seconds": elapsed_seconds,
        }

    except Exception as exc:
        elapsed_seconds = round(time.time() - start_time, 2)
        error_msg = str(exc)
        logger.error(
            "[%s] [target_date=%s] Status: failed - Error encountered: %s (elapsed %.1fs)",
            JOB_NAME,
            resolved_date,
            error_msg,
            elapsed_seconds,
        )
        # Anti-Zombie: Guarantee transition to failed with finished_at and error_message
        mark_as_failed(job_id=job_id, error_message=error_msg, engine=db_engine)
        raise


def main():
    parser = argparse.ArgumentParser(description="Nightly Telemetry Export & Execution Control CLI")
    parser.add_argument(
        "--target-date",
        type=str,
        default=None,
        help="Target date to export (YYYY-MM-DD). Defaults to yesterday UTC or TARGET_DATE env var.",
    )

    args = parser.parse_args()

    try:
        result = run_nightly_export(target_date=args.target_date)
        sys.exit(0)
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()
