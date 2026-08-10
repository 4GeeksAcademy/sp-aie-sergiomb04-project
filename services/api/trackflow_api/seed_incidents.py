from __future__ import annotations

from itertools import cycle

from trackflow_api.database import get_incidents_db
from trackflow_api.models import IncidentCreate, IncidentOriginEnum, incident_record_from_create

_INCIDENTS_TABLE = "incidents"
_DEFAULT_TARGET_TOTAL = 240

_CATEGORY_SEQUENCE = [
    "carrier_last_mile",
    "carrier_international",
    "warehouse_operations",
    "reverse_logistics",
    "customer_experience",
    "commercial",
    "technology",
    "executive",
]
_BRANCH_SEQUENCE = ["los_angeles", "zaragoza"]
_ORIGIN_SEQUENCE = [
    IncidentOriginEnum.CUSTOMER,
    IncidentOriginEnum.BRANCH,
    IncidentOriginEnum.INTERNAL,
]


def seed_incidents(target_total: int = _DEFAULT_TARGET_TOTAL) -> tuple[int, int]:
    db = get_incidents_db()
    table = db.table(_INCIDENTS_TABLE)
    existing = table.all()
    existing_total = len(existing)

    if existing_total >= target_total:
        db.close()
        return (0, existing_total)

    to_insert = target_total - existing_total
    category_iterator = cycle(_CATEGORY_SEQUENCE)
    branch_iterator = cycle(_BRANCH_SEQUENCE)
    origin_iterator = cycle(_ORIGIN_SEQUENCE)

    inserted = 0
    for index in range(to_insert):
        sequence_number = existing_total + index + 1
        payload = IncidentCreate(
            title=f"Incidencia seeded #{sequence_number}",
            description=(
                "Evento generado para pruebas de volumen y benchmarking de latencia. "
                f"Serie {sequence_number}."
            ),
            category=next(category_iterator),
            origin=next(origin_iterator),
            branch=next(branch_iterator),
        )
        incident = incident_record_from_create(payload)
        table.insert(incident.model_dump(mode="json"))
        inserted += 1

    final_total = existing_total + inserted
    db.close()
    return (inserted, final_total)


def main() -> None:
    inserted, total = seed_incidents()
    print(f"Inserted incidents: {inserted}")
    print(f"Total incidents: {total}")


if __name__ == "__main__":
    main()
