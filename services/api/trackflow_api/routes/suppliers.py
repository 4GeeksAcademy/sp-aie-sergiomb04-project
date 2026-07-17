from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from tinydb import Query as TinyQuery

from trackflow_api.database import get_db
from trackflow_api.models import (
    Supplier,
    SupplierCategory,
    SupplierCountry,
    SupplierCreate,
    SupplierRateUpdate,
    SupplierStatusUpdate,
    now_utc,
    supplier_record_from_create,
)

router = APIRouter(prefix="/suppliers", tags=["suppliers"])
_SUPPLIER_QUERY = TinyQuery()


def _read_supplier_by_id(db, supplier_id: str) -> dict | None:
    return db.get(_SUPPLIER_QUERY.id == supplier_id)


@router.post("", response_model=Supplier, status_code=status.HTTP_201_CREATED)
def create_supplier(payload: SupplierCreate) -> Supplier:
    db = get_db()
    supplier = supplier_record_from_create(payload)
    db.insert(supplier.model_dump(mode="json"))
    db.close()
    return supplier


@router.get("", response_model=list[Supplier], status_code=status.HTTP_200_OK)
def list_suppliers(
    country: SupplierCountry | None = Query(default=None),
    category: SupplierCategory | None = Query(default=None),
) -> list[Supplier]:
    db = get_db()
    records = db.all()
    db.close()

    if country is not None:
        records = [record for record in records if record.get("country") == country.value]

    if category is not None:
        records = [
            record
            for record in records
            if category.value in record.get("categories", [])
        ]

    return [Supplier.model_validate(record) for record in records]


@router.get("/{supplier_id}", response_model=Supplier, status_code=status.HTTP_200_OK)
def get_supplier(supplier_id: str) -> Supplier:
    db = get_db()
    record = _read_supplier_by_id(db, supplier_id)
    db.close()

    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")

    return Supplier.model_validate(record)


@router.patch("/{supplier_id}/rate", response_model=Supplier, status_code=status.HTTP_200_OK)
def patch_supplier_rate(supplier_id: str, payload: SupplierRateUpdate) -> Supplier:
    db = get_db()
    record = _read_supplier_by_id(db, supplier_id)

    if record is None:
        db.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")

    updated_payload = {
        "rate_per_shipment": payload.rate_per_shipment,
        "updated_at": now_utc().isoformat(),
    }
    db.update(updated_payload, _SUPPLIER_QUERY.id == supplier_id)
    updated_record = _read_supplier_by_id(db, supplier_id)
    db.close()

    if updated_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")

    return Supplier.model_validate(updated_record)


@router.patch("/{supplier_id}/status", response_model=Supplier, status_code=status.HTTP_200_OK)
def patch_supplier_status(supplier_id: str, payload: SupplierStatusUpdate) -> Supplier:
    db = get_db()
    record = _read_supplier_by_id(db, supplier_id)

    if record is None:
        db.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")

    db.update({"status": payload.status.value}, _SUPPLIER_QUERY.id == supplier_id)
    updated_record = _read_supplier_by_id(db, supplier_id)
    db.close()

    if updated_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")

    return Supplier.model_validate(updated_record)


@router.delete("/{supplier_id}", status_code=status.HTTP_200_OK)
def delete_supplier(supplier_id: str) -> dict[str, str]:
    db = get_db()
    record = _read_supplier_by_id(db, supplier_id)

    if record is None:
        db.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")

    db.remove(_SUPPLIER_QUERY.id == supplier_id)
    db.close()
    return {"detail": "Supplier deleted"}
