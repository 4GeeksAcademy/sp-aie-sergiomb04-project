"""Celery application re-export for services package."""

from __future__ import annotations

from pathlib import Path
import sys

_CURRENT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _CURRENT_DIR.parent if _CURRENT_DIR.name == "services" else _CURRENT_DIR.parents[1]
_API_DIR = _REPO_ROOT / "services" / "api"

for path in [_REPO_ROOT, _API_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from trackflow_api.celery_app import celery_app

__all__ = ["celery_app"]
