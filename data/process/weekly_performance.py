"""Pure vectorized business performance transformation logic for TrackFlow.

Computes weekly warehouse and client KPIs from raw telemetry events using Pandas.
No database or orchestration framework dependencies for maximum testability.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
from typing import Any

import numpy as np
import pandas as pd


def resolve_week_range(
    target_date: str | date | datetime | None = None,
) -> tuple[str, str, str]:
    """Resolve week_start (YYYY-MM-DD Monday) and UTC timestamp window [start_iso, end_iso).

    Parameters:
        target_date: Target date/datetime or string. If None, defaults to the previous Monday.

    Returns:
        tuple of (week_start_str, start_iso_utc, end_iso_utc)
    """
    if target_date is None:
        # Default to previous week's Monday
        now = datetime.now(timezone.utc)
        current_monday = (now - timedelta(days=now.weekday())).date()
        target_monday = current_monday - timedelta(days=7)
    elif isinstance(target_date, str):
        cleaned = target_date.strip()
        parsed = pd.to_datetime(cleaned, utc=True)
        if pd.isna(parsed):
            raise ValueError(f"Fecha invalida: {target_date}")
        target_monday = (parsed.date() - timedelta(days=parsed.weekday()))
    elif isinstance(target_date, datetime):
        if target_date.tzinfo is None:
            target_date = target_date.replace(tzinfo=timezone.utc)
        target_monday = (target_date.date() - timedelta(days=target_date.weekday()))
    elif isinstance(target_date, date):
        target_monday = (target_date - timedelta(days=target_date.weekday()))
    else:
        raise ValueError(f"Tipo de fecha no soportado: {type(target_date)}")

    week_start_str = target_monday.strftime("%Y-%m-%d")
    start_dt = datetime(target_monday.year, target_monday.month, target_monday.day, 0, 0, 0, tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(days=7)

    return week_start_str, start_dt.isoformat(), end_dt.isoformat()


def extract_event_payload(tags_val: Any) -> dict[str, Any]:
    """Safely parse tags field from string, dict, or JSON."""
    if isinstance(tags_val, dict):
        return tags_val
    if isinstance(tags_val, str) and tags_val.strip():
        try:
            parsed = json.loads(tags_val)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


def normalize_raw_events_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Extract and normalize dimensions from raw telemetry DataFrame."""
    if raw_df.empty:
        return pd.DataFrame(
            columns=["event_id", "timestamp", "event_type", "warehouse", "client_id", "quantity"]
        )

    df = raw_df.copy()

    # Ensure required columns exist
    for col in ["event_id", "timestamp", "event_type"]:
        if col not in df.columns:
            raise ValueError(f"Columna requerida faltante: {col}")

    # Deduplicate deterministically by event_id
    df = df.drop_duplicates(subset=["event_id"])

    # Extract tags properties if not already extracted
    if "tags" in df.columns:
        parsed_tags = df["tags"].apply(extract_event_payload)
        if "warehouse" not in df.columns:
            df["warehouse"] = parsed_tags.apply(lambda p: str(p.get("warehouse", "")).strip().lower())
        if "client_id" not in df.columns:
            df["client_id"] = parsed_tags.apply(lambda p: str(p.get("client_id", "")).strip())
        if "quantity" not in df.columns:
            df["quantity"] = pd.to_numeric(parsed_tags.apply(lambda p: p.get("quantity", 0)), errors="coerce").fillna(0).astype(int)
    else:
        if "warehouse" not in df.columns:
            df["warehouse"] = ""
        if "client_id" not in df.columns:
            df["client_id"] = ""
        if "quantity" not in df.columns:
            df["quantity"] = 0

    # Normalize warehouse and client_id
    df["warehouse"] = df["warehouse"].astype(str).str.strip().str.lower()
    df["client_id"] = df["client_id"].astype(str).str.strip()
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)

    # Filter out records without valid warehouse or client_id
    valid_mask = (df["warehouse"] != "") & (df["client_id"] != "")
    df = df[valid_mask]

    return df


def calculate_weekly_performance(
    raw_df: pd.DataFrame,
    target_week_start: str,
) -> pd.DataFrame:
    """Calculate aggregated weekly warehouse and client KPIs vectorially using Pandas.

    Target KPIs:
    - inbound_units_count: SUM(quantity) of inbound_order_created
    - outbound_orders_count: COUNT(event_id) of outbound_order_created
    - stockout_events_count: COUNT(event_id) of stock_threshold_triggered
    - discrepancy_events_count: COUNT(event_id) of inventory_discrepancy_detected
    - discrepancy_rate: discrepancy_events_count / outbound_orders_count (0.0 if outbound_orders_count == 0)

    Returns:
        DataFrame with columns:
        [warehouse, client_id, week_start, inbound_units_count, outbound_orders_count,
         stockout_events_count, discrepancy_events_count, discrepancy_rate, computed_at]
    """
    output_columns = [
        "warehouse",
        "client_id",
        "week_start",
        "inbound_units_count",
        "outbound_orders_count",
        "stockout_events_count",
        "discrepancy_events_count",
        "discrepancy_rate",
        "computed_at",
    ]

    if raw_df.empty:
        return pd.DataFrame(columns=output_columns)

    df = normalize_raw_events_dataframe(raw_df)
    if df.empty:
        return pd.DataFrame(columns=output_columns)

    now_iso = datetime.now(timezone.utc).isoformat()

    # Pre-calculate indicator and quantity columns
    df["is_inbound"] = (df["event_type"] == "inbound_order_created").astype(int)
    df["inbound_units"] = np.where(df["event_type"] == "inbound_order_created", df["quantity"], 0)
    df["is_outbound"] = (df["event_type"] == "outbound_order_created").astype(int)
    df["is_stockout"] = (df["event_type"] == "stock_threshold_triggered").astype(int)
    df["is_discrepancy"] = (df["event_type"] == "inventory_discrepancy_detected").astype(int)

    # Group by warehouse and client_id
    grouped = df.groupby(["warehouse", "client_id"]).agg(
        inbound_units_count=("inbound_units", "sum"),
        outbound_orders_count=("is_outbound", "sum"),
        stockout_events_count=("is_stockout", "sum"),
        discrepancy_events_count=("is_discrepancy", "sum"),
    ).reset_index()

    grouped["week_start"] = target_week_start

    # Safe vectorized division for discrepancy_rate
    grouped["discrepancy_rate"] = np.where(
        grouped["outbound_orders_count"] > 0,
        (grouped["discrepancy_events_count"] / grouped["outbound_orders_count"]).round(4),
        0.0,
    )

    grouped["computed_at"] = now_iso

    # Ensure correct integer types
    for int_col in [
        "inbound_units_count",
        "outbound_orders_count",
        "stockout_events_count",
        "discrepancy_events_count",
    ]:
        grouped[int_col] = grouped[int_col].astype(int)

    grouped["discrepancy_rate"] = grouped["discrepancy_rate"].astype(float)

    # Sort deterministically
    grouped = grouped.sort_values(["warehouse", "client_id"]).reset_index(drop=True)

    return grouped[output_columns]
