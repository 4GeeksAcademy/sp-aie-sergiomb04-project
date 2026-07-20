from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from tinydb import TinyDB

_DATA_DIR: Final[Path] = Path(__file__).resolve().parent / "data"
_DB_PATH: Final[Path] = _DATA_DIR / "suppliers.json"


def _resolve_db_path() -> Path:
    configured_path = os.getenv("TRACKFLOW_DB_PATH")
    if configured_path:
        return Path(configured_path)
    return _DB_PATH


def get_db() -> TinyDB:
    db_path = _resolve_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return TinyDB(db_path)
