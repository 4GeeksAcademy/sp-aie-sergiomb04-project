"""Script to run the Celery worker independently from the FastAPI process."""

from __future__ import annotations

from pathlib import Path
import sys

_CURRENT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _CURRENT_DIR.parent
_API_DIR = _REPO_ROOT / "services" / "api"

for path in [_REPO_ROOT, _API_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from trackflow_api.worker import main

if __name__ == "__main__":
    main()
