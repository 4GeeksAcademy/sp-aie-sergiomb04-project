"""Job runner service re-export for trackflow_api namespace."""

from __future__ import annotations

from pathlib import Path
import sys

_CURRENT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _CURRENT_DIR.parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from services.job_runner import (
    create_job_run,
    get_job_run_by_id,
    has_completed_for_date,
    has_processing_lock,
    mark_as_completed,
    mark_as_failed,
)

__all__ = [
    "has_processing_lock",
    "has_completed_for_date",
    "create_job_run",
    "mark_as_completed",
    "mark_as_failed",
    "get_job_run_by_id",
]
