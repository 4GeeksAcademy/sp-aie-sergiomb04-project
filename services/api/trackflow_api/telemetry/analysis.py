"""Telemetry analysis pipeline using Pandas and SQLModel/SQLAlchemy.

Computes operational and technical metrics from telemetry_events within UTC time windows.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

import pandas as pd
from sqlalchemy import text

from trackflow_api.database import get_inventory_engine


def _to_iso_utc(d: str | datetime) -> str:
    """Normalize input date to UTC ISO-8601 string."""
    if isinstance(d, datetime):
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        else:
            d = d.astimezone(timezone.utc)
        return d.isoformat()
    if isinstance(d, str):
        cleaned = d.strip()
        if " " in cleaned and ("+" not in cleaned and "Z" not in cleaned and "z" not in cleaned):
            parts = cleaned.rsplit(" ", 1)
            if len(parts) == 2 and ":" in parts[1]:
                cleaned = f"{parts[0]}+{parts[1]}"
        try:
            parsed = pd.to_datetime(cleaned, utc=True)
            if pd.isna(parsed):
                raise ValueError(f"Formato de fecha invalido: {d}")
            return parsed.isoformat()
        except Exception as exc:
            raise ValueError(f"Formato de fecha invalido: {d}") from exc
    raise ValueError(f"Tipo de fecha no soportado: {type(d)}")


def _resolve_engine(engine: Any = None):
    """Resolve database engine to use for queries."""
    if engine is not None:
        return engine
    return get_inventory_engine()


def events_per_day(
    start_date: str | datetime,
    end_date: str | datetime,
    engine: Any = None,
) -> list[dict[str, Any]]:
    """Compute total volume of telemetry events grouped by day.
    
    SQL window: timestamp >= :start AND timestamp < :end
    """
    start_iso = _to_iso_utc(start_date)
    end_iso = _to_iso_utc(end_date)
    db_engine = _resolve_engine(engine)

    query = text(
        "SELECT timestamp, event_type FROM telemetry_events "
        "WHERE timestamp >= :start AND timestamp < :end"
    )

    with db_engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"start": start_iso, "end": end_iso})

    if df.empty:
        return []

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["date"] = df["timestamp"].dt.strftime("%Y-%m-%d")

    grouped = (
        df.groupby("date")
        .agg(count=("event_type", "count"))
        .reset_index()
        .sort_values("date")
    )

    return json.loads(grouped.to_json(orient="records"))


def error_rate_by_type(
    start_date: str | datetime,
    end_date: str | datetime,
    engine: Any = None,
) -> list[dict[str, Any]]:
    """Compute error/rejection counts and proportion against total events by event_type.
    
    SQL window: timestamp >= :start AND timestamp < :end
    """
    start_iso = _to_iso_utc(start_date)
    end_iso = _to_iso_utc(end_date)
    db_engine = _resolve_engine(engine)

    query = text(
        "SELECT timestamp, event_type, tags FROM telemetry_events "
        "WHERE timestamp >= :start AND timestamp < :end"
    )

    with db_engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"start": start_iso, "end": end_iso})

    if df.empty:
        return []

    total_events = len(df)
    error_types = [
        "api_request_failed",
        "auth_login_failed",
        "user_login_failed",
        "direct_stock_edit_rejected",
        "outbound_order_rejected_insufficient_stock",
        "inventory_order_rejected_warehouse_mismatch",
        "inventory_form_validation_failed",
        "session_access_denied",
    ]

    error_df = df[df["event_type"].isin(error_types)]
    if error_df.empty:
        return []

    grouped = (
        error_df.groupby("event_type")
        .agg(count=("event_type", "count"))
        .reset_index()
    )
    grouped["total_events"] = total_events
    grouped["error_rate"] = (grouped["count"] / total_events).round(4)
    grouped = grouped.sort_values("count", ascending=False)

    return json.loads(grouped.to_json(orient="records"))


def auth_failure_rate(
    start_date: str | datetime,
    end_date: str | datetime,
    engine: Any = None,
) -> list[dict[str, Any]]:
    """Compute authentication failure rate per day (failed / (failed + succeeded)).
    
    SQL window: timestamp >= :start AND timestamp < :end
    Loads only auth event types in single SQL query.
    """
    start_iso = _to_iso_utc(start_date)
    end_iso = _to_iso_utc(end_date)
    db_engine = _resolve_engine(engine)

    query = text(
        "SELECT timestamp, event_type FROM telemetry_events "
        "WHERE event_type IN ('auth_login_failed', 'auth_login_succeeded', 'user_login_failed', 'user_login_succeeded') "
        "AND timestamp >= :start AND timestamp < :end"
    )

    with db_engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"start": start_iso, "end": end_iso})

    if df.empty:
        return []

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["date"] = df["timestamp"].dt.strftime("%Y-%m-%d")

    df["is_failed"] = df["event_type"].isin(["auth_login_failed", "user_login_failed"]).astype(int)
    df["is_succeeded"] = df["event_type"].isin(["auth_login_succeeded", "user_login_succeeded"]).astype(int)

    grouped = (
        df.groupby("date")
        .agg(
            failed=("is_failed", "sum"),
            succeeded=("is_succeeded", "sum"),
            total_attempts=("event_type", "count"),
        )
        .reset_index()
        .sort_values("date")
    )
    grouped["failure_rate"] = (grouped["failed"] / grouped["total_attempts"]).round(4)

    return json.loads(grouped.to_json(orient="records"))


def latency_by_route(
    start_date: str | datetime,
    end_date: str | datetime,
    engine: Any = None,
) -> list[dict[str, Any]]:
    """Compute average and p95 latency by endpoint route from sampled API latency events.
    
    SQL window: timestamp >= :start AND timestamp < :end
    """
    start_iso = _to_iso_utc(start_date)
    end_iso = _to_iso_utc(end_date)
    db_engine = _resolve_engine(engine)

    query = text(
        "SELECT timestamp, tags FROM telemetry_events "
        "WHERE event_type = 'api_request_latency_sampled' "
        "AND timestamp >= :start AND timestamp < :end"
    )

    with db_engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"start": start_iso, "end": end_iso})

    if df.empty:
        return []

    def _extract_field(val: Any, key: str) -> Any:
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except Exception:
                return None
        if isinstance(val, dict):
            return val.get(key)
        return None

    df["api_route"] = df["tags"].apply(lambda t: _extract_field(t, "api_route") or "unknown")
    df["method"] = df["tags"].apply(lambda t: _extract_field(t, "method") or "GET")
    df["latency_ms"] = pd.to_numeric(df["tags"].apply(lambda t: _extract_field(t, "latency_ms")), errors="coerce")

    df = df.dropna(subset=["latency_ms"])
    if df.empty:
        return []

    grouped = (
        df.groupby(["api_route", "method"])
        .agg(
            sample_count=("latency_ms", "count"),
            avg_latency_ms=("latency_ms", "mean"),
            min_latency_ms=("latency_ms", "min"),
            max_latency_ms=("latency_ms", "max"),
            p95_latency_ms=("latency_ms", lambda x: float(x.quantile(0.95))),
        )
        .reset_index()
    )

    grouped["avg_latency_ms"] = grouped["avg_latency_ms"].round(2)
    grouped["min_latency_ms"] = grouped["min_latency_ms"].round(2)
    grouped["max_latency_ms"] = grouped["max_latency_ms"].round(2)
    grouped["p95_latency_ms"] = grouped["p95_latency_ms"].round(2)

    return json.loads(grouped.to_json(orient="records"))


def generate_telemetry_report(
    start_date: str | datetime,
    end_date: str | datetime,
    engine: Any = None,
) -> dict[str, Any]:
    """Execute the full telemetry analytical pipeline across all operational metric functions."""
    start_iso = _to_iso_utc(start_date)
    end_iso = _to_iso_utc(end_date)

    return {
        "period": {
            "from": start_iso,
            "to": end_iso,
        },
        "metrics": {
            "events_per_day": events_per_day(start_iso, end_iso, engine),
            "error_rate_by_type": error_rate_by_type(start_iso, end_iso, engine),
            "auth_failure_rate": auth_failure_rate(start_iso, end_iso, engine),
            "latency_by_route": latency_by_route(start_iso, end_iso, engine),
        },
    }
