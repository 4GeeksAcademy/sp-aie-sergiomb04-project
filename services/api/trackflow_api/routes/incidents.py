from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from tinydb import Query as TinyQuery
from tinydb.table import Table

from trackflow_api.auth import get_current_user
from trackflow_api.database import get_tinydb
from trackflow_api.models import (
    Incident,
    IncidentCreate,
    IncidentStatusEnum,
    IncidentStatusUpdate,
    IncidentSummary,
    STATUS_TRANSITIONS,
    incident_record_from_create,
)

router = APIRouter(
    prefix="/api/incidents",
    tags=["incidents"],
    dependencies=[Depends(get_current_user)],
)

_INCIDENTS_TABLE = "incidents"
_INCIDENT_QUERY = TinyQuery()


def _get_table(db) -> Table:
    return db.table(_INCIDENTS_TABLE)


def _read_by_id(db, incident_id: str) -> dict | None:
    return _get_table(db).get(_INCIDENT_QUERY.id == incident_id)


@router.post("", response_model=Incident, status_code=status.HTTP_201_CREATED)
def create_incident(payload: IncidentCreate) -> Incident:
    incident = incident_record_from_create(payload)
    try:
        db = get_tinydb()
        _get_table(db).insert(incident.model_dump(mode="json"))
    except Exception as error:
        db.close()
        raise HTTPException(status_code=500, detail="Error interno al crear incidencia") from error
    db.close()
    return incident


@router.get("", response_model=list[Incident], status_code=status.HTTP_200_OK)
def list_incidents(
    status: str | None = Query(default=None),
    origin: str | None = Query(default=None),
    branch: str | None = Query(default=None),
    category: str | None = Query(default=None),
) -> list[Incident]:
    try:
        db = get_tinydb()
        records = _get_table(db).all()
    except Exception as error:
        db.close()
        raise HTTPException(status_code=500, detail="Error interno al listar incidencias") from error
    db.close()

    if status is not None:
        records = [r for r in records if r.get("status") == status]
    if origin is not None:
        records = [r for r in records if r.get("origin") == origin]
    if branch is not None:
        records = [r for r in records if r.get("branch") == branch]
    if category is not None:
        records = [r for r in records if r.get("category") == category]

    return [Incident.model_validate(r) for r in records]


@router.get("/summary", response_model=IncidentSummary, status_code=status.HTTP_200_OK)
def get_incidents_summary() -> IncidentSummary:
    try:
        db = get_tinydb()
        records = _get_table(db).all()
    except Exception as error:
        db.close()
        raise HTTPException(status_code=500, detail="Error interno al obtener resumen") from error
    db.close()

    total = len(records)
    by_status: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_origin: dict[str, int] = {}
    by_branch: dict[str, int] = {}

    for r in records:
        s = r.get("status", "unknown")
        by_status[s] = by_status.get(s, 0) + 1

        c = r.get("category", "unknown")
        by_category[c] = by_category.get(c, 0) + 1

        o = r.get("origin", "unknown")
        by_origin[o] = by_origin.get(o, 0) + 1

        b = r.get("branch", "unknown")
        by_branch[b] = by_branch.get(b, 0) + 1

    return IncidentSummary(
        total=total,
        by_status=by_status,
        by_category=by_category,
        by_origin=by_origin,
        by_branch=by_branch,
    )


@router.get("/{incident_id}", response_model=Incident, status_code=status.HTTP_200_OK)
def get_incident(incident_id: str) -> Incident:
    try:
        db = get_tinydb()
        record = _read_by_id(db, incident_id)
    except Exception as error:
        db.close()
        raise HTTPException(status_code=500, detail="Error interno al obtener incidencia") from error
    db.close()

    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")

    return Incident.model_validate(record)


@router.patch("/{incident_id}/status", response_model=Incident, status_code=status.HTTP_200_OK)
def patch_incident_status(incident_id: str, payload: IncidentStatusUpdate) -> Incident:
    try:
        db = get_tinydb()
        record = _read_by_id(db, incident_id)
    except Exception as error:
        db.close()
        raise HTTPException(status_code=500, detail="Error interno al acceder a la base de datos") from error

    if record is None:
        db.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")

    current_status = IncidentStatusEnum(record["status"])
    new_status = payload.status

    allowed = STATUS_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        db.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "field": "status",
                "message": (
                    f"No se puede cambiar de '{current_status.value}' a '{new_status.value}'. "
                    f"Transiciones permitidas: {[s.value for s in allowed]}"
                ),
            },
        )

    try:
        _get_table(db).update(
            {"status": new_status.value, "updated_at": datetime.now(timezone.utc).isoformat()},
            _INCIDENT_QUERY.id == incident_id,
        )
        updated_record = _read_by_id(db, incident_id)
    except Exception as error:
        db.close()
        raise HTTPException(status_code=500, detail="Error interno al actualizar estado") from error
    db.close()

    if updated_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")

    return Incident.model_validate(updated_record)