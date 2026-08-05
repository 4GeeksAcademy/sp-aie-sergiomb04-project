from __future__ import annotations

import os

from collections.abc import Generator
from pathlib import Path
from typing import Final

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine
from tinydb import TinyDB

_DATA_DIR: Final[Path] = Path(__file__).resolve().parent / "data"
_API_ROOT_DIR: Final[Path] = Path(__file__).resolve().parents[1]
_ENV_FILE_PATH: Final[Path] = _API_ROOT_DIR / ".env"
_SUPPLIERS_DB_PATH: Final[Path] = _DATA_DIR / "suppliers.json"
_USERS_DB_PATH: Final[Path] = _DATA_DIR / "users.json"
_INCIDENTS_DB_PATH: Final[Path] = _DATA_DIR / "incidents.json"
_INVENTORY_SQLITE_PATH: Final[Path] = _DATA_DIR / "inventory.db"
_inventory_engine = None
_inventory_engine_url = ""

load_dotenv(dotenv_path=_ENV_FILE_PATH, override=False)


def _resolve_inventory_database_url() -> str:
    configured_url = os.getenv("DATABASE_URL")
    if configured_url:
        # Normaliza esquemas de Postgres al driver instalado (psycopg v3).
        if configured_url.startswith("postgresql+psycopg2://"):
            return configured_url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
        if configured_url.startswith("postgresql://") and "+" not in configured_url.split("://", 1)[0]:
            return configured_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return configured_url
    return f"sqlite:///{_INVENTORY_SQLITE_PATH}"


def _build_inventory_engine(database_url: str):
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)


def get_inventory_engine():
    global _inventory_engine
    global _inventory_engine_url

    resolved_url = _resolve_inventory_database_url()
    if _inventory_engine is None or _inventory_engine_url != resolved_url:
        _inventory_engine = _build_inventory_engine(resolved_url)
        _inventory_engine_url = resolved_url
    return _inventory_engine


def _resolve_suppliers_db_path() -> Path:
    configured_path = os.getenv("TRACKFLOW_SUPPLIERS_DB_PATH") or os.getenv("TRACKFLOW_DB_PATH")
    if configured_path:
        return Path(configured_path)
    return _SUPPLIERS_DB_PATH


def _resolve_users_db_path() -> Path:
    configured_path = os.getenv("TRACKFLOW_USERS_DB_PATH")
    if configured_path:
        return Path(configured_path)
    return _USERS_DB_PATH


def _resolve_incidents_db_path() -> Path:
    configured_path = os.getenv("TRACKFLOW_INCIDENTS_DB_PATH")
    if configured_path:
        return Path(configured_path)
    return _INCIDENTS_DB_PATH


def _open_tinydb(db_path: Path) -> TinyDB:
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


def get_suppliers_db() -> TinyDB:
    return _open_tinydb(_resolve_suppliers_db_path())


def get_users_db() -> TinyDB:
    return _open_tinydb(_resolve_users_db_path())


def get_incidents_db() -> TinyDB:
    return _open_tinydb(_resolve_incidents_db_path())


def get_tinydb() -> TinyDB:
    return get_suppliers_db()


def init_inventory_db() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(get_inventory_engine())


def get_db() -> Generator[Session, None, None]:
    with Session(get_inventory_engine()) as session:
        yield session
