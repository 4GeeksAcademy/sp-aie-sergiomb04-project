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
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        raise RuntimeError(f"Permiso denegado para crear directorio: {db_path.parent}")
    except OSError as error:
        raise RuntimeError(f"Error al crear directorio de BD: {error}") from error
    try:
        return TinyDB(db_path)
    except Exception as error:
        raise RuntimeError(f"Error al abrir la base de datos: {error}") from error
