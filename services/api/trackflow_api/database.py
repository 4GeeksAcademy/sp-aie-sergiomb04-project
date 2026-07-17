from __future__ import annotations

from pathlib import Path
from typing import Final

from tinydb import TinyDB

_DATA_DIR: Final[Path] = Path(__file__).resolve().parent / "data"
_DB_PATH: Final[Path] = _DATA_DIR / "suppliers.json"


def get_db() -> TinyDB:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    return TinyDB(_DB_PATH)
