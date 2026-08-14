from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from tinydb import Query as TinyQuery

from trackflow_api.auth import get_current_user
from trackflow_api.cache import api_cache
from trackflow_api.database import get_tinydb
from trackflow_api.models import (
    Supplier,
    SupplierCategory,
    SupplierCountry,
    SupplierCreate,
    SupplierRateUpdate,
    SupplierStatusUpdate,
    UserRecord,
    now_utc,
    supplier_record_from_create,
)

router = APIRouter(
    prefix="/suppliers",
    tags=["suppliers"],
    dependencies=[Depends(get_current_user)],
)
_SUPPLIER_QUERY = TinyQuery()
_SUPPLIERS_LIST_TTL_SECONDS = 45
_SUPPLIERS_DETAIL_TTL_SECONDS = 30


def _supplier_list_cache_key(
    user_id: str,
    country: SupplierCountry | None,
    category: SupplierCategory | None,
) -> str:
    return f"suppliers:list:user={user_id}:country={country.value if country else 'all'}:category={category.value if category else 'all'}"


def _supplier_detail_cache_key(user_id: str, supplier_id: str) -> str:
    return f"suppliers:detail:user={user_id}:supplier_id={supplier_id}"


def _invalidate_suppliers_cache() -> None:
    api_cache.invalidate_prefix("suppliers:")


def _read_supplier_by_id(db, supplier_id: str) -> dict | None:
    return db.get(_SUPPLIER_QUERY.id == supplier_id)


@router.post("", response_model=Supplier, status_code=status.HTTP_201_CREATED)
def create_supplier(payload: SupplierCreate) -> Supplier:
    supplier = supplier_record_from_create(payload)
    try:
        db = get_tinydb()
        db.insert(supplier.model_dump(mode="json"))
    except Exception as error:
        db.close()
        raise HTTPException(status_code=500, detail="Error interno al crear proveedor") from error
    db.close()
    _invalidate_suppliers_cache()
    return supplier


@router.get("", response_model=list[Supplier], status_code=status.HTTP_200_OK)
def list_suppliers(
    country: SupplierCountry | None = Query(default=None),
    category: SupplierCategory | None = Query(default=None),
    current_user: UserRecord = Depends(get_current_user),
) -> list[Supplier]:
    cache_key = _supplier_list_cache_key(current_user.id, country, category)
    cached_payload = api_cache.get(cache_key)
    if cached_payload is not None:
        return [Supplier.model_validate(record) for record in cached_payload]

    db = None
    try:
        db = get_tinydb()
        records = db.all()
    except Exception as error:
        if db is not None:
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

    api_cache.set(cache_key, records, _SUPPLIERS_LIST_TTL_SECONDS)
    return [Supplier.model_validate(record) for record in records]


@router.get("/{supplier_id}", response_model=Supplier, status_code=status.HTTP_200_OK)
def get_supplier(
    supplier_id: str,
    current_user: UserRecord = Depends(get_current_user),
) -> Supplier:
    cache_key = _supplier_detail_cache_key(current_user.id, supplier_id)
    cached_record = api_cache.get(cache_key)
    if cached_record is not None:
        return Supplier.model_validate(cached_record)

    db = None
    try:
        db = get_tinydb()
        record = _read_supplier_by_id(db, supplier_id)
    except Exception as error:
        if db is not None:
            db.close()
        raise HTTPException(status_code=500, detail="Error interno al obtener proveedor") from error
    db.close()

    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")

    api_cache.set(cache_key, record, _SUPPLIERS_DETAIL_TTL_SECONDS)
    return Supplier.model_validate(record)


@router.patch("/{supplier_id}/rate", response_model=Supplier, status_code=status.HTTP_200_OK)
def patch_supplier_rate(supplier_id: str, payload: SupplierRateUpdate) -> Supplier:
    try:
        db = get_tinydb()
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

    _invalidate_suppliers_cache()
    return Supplier.model_validate(updated_record)


@router.patch("/{supplier_id}/status", response_model=Supplier, status_code=status.HTTP_200_OK)
def patch_supplier_status(supplier_id: str, payload: SupplierStatusUpdate) -> Supplier:
    try:
        db = get_tinydb()
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

    _invalidate_suppliers_cache()
    return Supplier.model_validate(updated_record)


@router.delete("/{supplier_id}", status_code=status.HTTP_200_OK)
def delete_supplier(supplier_id: str) -> dict[str, str]:
    try:
        db = get_tinydb()
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
    _invalidate_suppliers_cache()
    return {"detail": "Proveedor eliminado"}
