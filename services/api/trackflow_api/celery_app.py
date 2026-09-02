"""Celery application configuration for TrackFlow."""

from __future__ import annotations

import os
from pathlib import Path
import sys
from dotenv import load_dotenv
from celery import Celery

_API_ROOT_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENV_FILE_PATH = _API_ROOT_DIR / ".env"

for candidate in [_REPO_ROOT, _API_ROOT_DIR]:
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

load_dotenv(dotenv_path=_ENV_FILE_PATH, override=False)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "trackflow",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["trackflow_api.tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    result_expires=3600,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    task_time_limit=300,
    task_soft_time_limit=240,
)
