from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from tinydb import Query as TinyQuery

from trackflow_api.auth import get_current_user
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

router = APIRouter(
    prefix="/suppliers",
    tags=["suppliers"],
    dependencies=[Depends(get_current_user)],
)
_SUPPLIER_QUERY = TinyQuery()


def _read_supplier_by_id(db, supplier_id: str) -> dict | None:
    return db.get(_SUPPLIER_QUERY.id == supplier_id)


@router.post("", response_model=Supplier, status_code=status.HTTP_201_CREATED)
def create_supplier(payload: SupplierCreate) -> Supplier:
    supplier = supplier_record_from_create(payload)
    try:
        db = get_db()
        db.insert(supplier.model_dump(mode="json"))
    except Exception as error:
        db.close()
        raise HTTPException(status_code=500, detail="Error interno al crear proveedor") from error
    db.close()
    return supplier


@router.get("", response_model=list[Supplier], status_code=status.HTTP_200_OK)
def list_suppliers(
    country: SupplierCountry | None = Query(default=None),
    category: SupplierCategory | None = Query(default=None),
) -> list[Supplier]:
    try:
        db = get_db()
        records = db.all()
    except Exception as error:
        db.close()
        raise HTTPException(status_code=500, detail="Error interno al listar proveedores") from error
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
    try:
        db = get_db()
        record = _read_supplier_by_id(db, supplier_id)
    except Exception as error:
        db.close()
        raise HTTPException(status_code=500, detail="Error interno al obtener proveedor") from error
    db.close()

    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")

    return Supplier.model_validate(record)


@router.patch("/{supplier_id}/rate", response_model=Supplier, status_code=status.HTTP_200_OK)
def patch_supplier_rate(supplier_id: str, payload: SupplierRateUpdate) -> Supplier:
    try:
        db = get_db()
        record = _read_supplier_by_id(db, supplier_id)
    except Exception as error:
        db.close()
        raise HTTPException(status_code=500, detail="Error interno al acceder a la base de datos") from error

    if record is None:
        db.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")

    try:
        updated_payload = {
            "rate_per_shipment": payload.rate_per_shipment,
            "updated_at": now_utc().isoformat(),
        }
        db.update(updated_payload, _SUPPLIER_QUERY.id == supplier_id)
        updated_record = _read_supplier_by_id(db, supplier_id)
    except Exception as error:
        db.close()
        raise HTTPException(status_code=500, detail="Error interno al actualizar tarifa") from error
    db.close()

    if updated_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")

    return Supplier.model_validate(updated_record)


@router.patch("/{supplier_id}/status", response_model=Supplier, status_code=status.HTTP_200_OK)
def patch_supplier_status(supplier_id: str, payload: SupplierStatusUpdate) -> Supplier:
    try:
        db = get_db()
        record = _read_supplier_by_id(db, supplier_id)
    except Exception as error:
        db.close()
        raise HTTPException(status_code=500, detail="Error interno al acceder a la base de datos") from error

    if record is None:
        db.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")

    try:
        db.update({"status": payload.status.value}, _SUPPLIER_QUERY.id == supplier_id)
        updated_record = _read_supplier_by_id(db, supplier_id)
    except Exception as error:
        db.close()
        raise HTTPException(status_code=500, detail="Error interno al actualizar estado") from error
    db.close()

    if updated_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")

    return Supplier.model_validate(updated_record)


@router.delete("/{supplier_id}", status_code=status.HTTP_200_OK)
def delete_supplier(supplier_id: str) -> dict[str, str]:
    try:
        db = get_db()
        record = _read_supplier_by_id(db, supplier_id)
    except Exception as error:
        db.close()
        raise HTTPException(status_code=500, detail="Error interno al acceder a la base de datos") from error

    if record is None:
        db.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")

    try:
        db.remove(_SUPPLIER_QUERY.id == supplier_id)
    except Exception as error:
        db.close()
        raise HTTPException(status_code=500, detail="Error interno al eliminar proveedor") from error
    db.close()
    return {"detail": "Proveedor eliminado"}
