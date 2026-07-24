#!/usr/bin/env python3
"""
Seed script to import incidents from the existing CSV into the API database.

Usage:
    python3 scripts/seed_incidents.py

Reads incidents-trackflow.csv, maps its fields to the Incident model,
assigns origin="customer" to all records, and inserts them into the
TinyDB database used by the API. Idempotent: skips records whose
incident_id (from CSV) already exist.
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

# Ensure shared package is accessible
_SHARED_DIR = Path(__file__).resolve().parents[1] / "packages" / "shared"
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

# Ensure the API package is accessible
_API_DIR = Path(__file__).resolve().parents[1] / "services" / "api"
if str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))

# Ensure the API package itself is importable
_API_PKG = _API_DIR / "trackflow_api"
if str(_API_PKG.parent) not in sys.path:
    sys.path.insert(0, str(_API_PKG.parent))

from trackflow_api.database import get_db
from trackflow_api.models import (
    INCIDENT_BRANCHES,
    INCIDENT_CATEGORIES,
    Incident,
    IncidentOriginEnum,
    IncidentStatusEnum,
)

# ─── Constants ─────────────────────────────────────────────────────────────────

CSV_DIR = Path(__file__).resolve().parent / "incidents-analysis"
CSV_PATH = CSV_DIR / "incidents-trackflow.csv"
INCIDENTS_TABLE = "incidents"

# ─── Mapping: CSV categories → our category enum ──────────────────────────────
# The CSV uses different category names; map them to our domain categories.
CSV_CATEGORY_MAP: dict[str, str] = {
    "LOST_PARCEL": "carrier_last_mile",
    "DELAYED_DELIVERY": "carrier_last_mile",
    "WRONG_ADDRESS": "carrier_last_mile",
    "RETURN_REQUEST": "reverse_logistics",
    "DAMAGE": "warehouse_operations",
}

# ─── Mapping: CSV statuses → our status enum ──────────────────────────────────
CSV_STATUS_MAP: dict[str, str] = {
    "OPEN": "open",
    "CLOSED": "resolved",
    "DISCARDED": "discarded",
}

# ─── Mapping: CSV country → our branch ────────────────────────────────────────
CSV_COUNTRY_BRANCH_MAP: dict[str, str] = {
    "US": "los_angeles",
    "ES": "zaragoza",
}

# ─── CSV column names ─────────────────────────────────────────────────────────
CSV_ID_FIELD = "incident_id"
CSV_DATE_FIELD = "date"
CSV_COUNTRY_FIELD = "country"
CSV_CATEGORY_FIELD = "category"
CSV_DESCRIPTION_FIELD = "description"
CSV_STATUS_FIELD = "status"

REQUIRED_CSV_FIELDS = [
    CSV_ID_FIELD,
    CSV_DATE_FIELD,
    CSV_COUNTRY_FIELD,
    CSV_CATEGORY_FIELD,
    CSV_DESCRIPTION_FIELD,
    CSV_STATUS_FIELD,
]


# ─── Helpers ───────────────────────────────────────────────────────────────────


def _normalize(value: object) -> str:
    return str(value or "").strip()


def _validate_and_map_row(row: dict[str, str], row_num: int) -> dict[str, Any] | str | None:
    """Validate a CSV row and return mapped data, None to skip, or an error string."""
    # Check required fields exist
    for field in REQUIRED_CSV_FIELDS:
        if field not in row:
            return f"Fila {row_num}: falta columna '{field}'"

    csv_id = _normalize(row.get(CSV_ID_FIELD, ""))
    if not csv_id:
        return None  # Skip rows without ID

    category_csv = _normalize(row.get(CSV_CATEGORY_FIELD, ""))
    description = _normalize(row.get(CSV_DESCRIPTION_FIELD, ""))
    status_csv = _normalize(row.get(CSV_STATUS_FIELD, ""))
    country = _normalize(row.get(CSV_COUNTRY_FIELD, ""))

    # Map category
    mapped_category = CSV_CATEGORY_MAP.get(category_csv)
    if mapped_category is None or mapped_category not in INCIDENT_CATEGORIES:
        return None  # Skip unmappable categories silently

    # Map status
    mapped_status = CSV_STATUS_MAP.get(status_csv)
    if mapped_status is None:
        return None  # Skip unmappable statuses silently

    # Map branch from country
    mapped_branch = CSV_COUNTRY_BRANCH_MAP.get(country)
    if mapped_branch is None:
        return None  # Skip unmappable countries

    # Build title from CSV data
    title = f"Incidente {csv_id} - {category_csv}"

    return {
        "csv_id": csv_id,
        "title": title,
        "description": description,
        "category": mapped_category,
        "status": mapped_status,
        "origin": "customer",  # All CSV records are from customers
        "branch": mapped_branch,
    }


# ─── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    if not CSV_PATH.is_file():
        print(f"Error: No se encuentra el CSV en: {CSV_PATH}", file=sys.stderr)
        sys.exit(1)

    print(f"Leyendo CSV: {CSV_PATH}")

    # Read CSV rows
    rows: list[dict[str, str]] = []
    try:
        with CSV_PATH.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                print("Error: El CSV no tiene encabezados", file=sys.stderr)
                sys.exit(1)

            # Check for required fields
            missing = [f for f in REQUIRED_CSV_FIELDS if f not in reader.fieldnames]
            if missing:
                print(
                    f"Error: Faltan columnas requeridas en el CSV: {', '.join(missing)}",
                    file=sys.stderr,
                )
                sys.exit(1)

            for row in reader:
                rows.append({k: _normalize(v) for k, v in row.items()})
    except Exception as e:
        print(f"Error al leer CSV: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Total filas en CSV: {len(rows)}")

    # Validate and map rows
    mapped_rows: list[dict[str, Any]] = []
    skipped: list[str] = []

    for i, row in enumerate(rows, start=2):  # start=2 because header is row 1
        result = _validate_and_map_row(row, i)
        if result is None:
            continue
        if isinstance(result, str):
            skipped.append(result)
            continue
        mapped_rows.append(result)

    print(f"Filas válidas para insertar: {len(mapped_rows)}")
    if skipped:
        print(f"Filas omitidas: {len(skipped)}")
        for s in skipped:
            print(f"  - {s}")

    # Insert into database (idempotent)
    db = get_db()
    table = db.table(INCIDENTS_TABLE)

    # Build set of existing CSV IDs (we store them in a helper field for idempotency)
    existing_records = table.all()
    existing_csv_ids: set[str] = set()
    for rec in existing_records:
        csv_id = rec.get("_csv_id", "")
        if csv_id:
            existing_csv_ids.add(csv_id)

    print(f"Registros existentes en BD: {len(existing_records)}")

    inserted = 0
    duplicates = 0

    for mapped in mapped_rows:
        if mapped["csv_id"] in existing_csv_ids:
            duplicates += 1
            continue

        now = datetime.now(timezone.utc)
        incident = Incident(
            id=str(uuid4()),
            title=mapped["title"],
            description=mapped["description"],
            category=mapped["category"],
            status=IncidentStatusEnum(mapped["status"]),
            origin=IncidentOriginEnum(mapped["origin"]),
            branch=mapped["branch"],
            created_at=now,
            updated_at=now,
        )

        record_data = incident.model_dump(mode="json")
        record_data["_csv_id"] = mapped["csv_id"]  # Store CSV ID for idempotency
        table.insert(record_data)
        inserted += 1

    db.close()

    print(f"\nResumen:")
    print(f"  Insertados:  {inserted}")
    print(f"  Duplicados:  {duplicates}")
    print(f"  Omitidos:    {len(skipped)}")
    print(f"  Total BD:    {len(existing_records) + inserted}")


if __name__ == "__main__":
    main()