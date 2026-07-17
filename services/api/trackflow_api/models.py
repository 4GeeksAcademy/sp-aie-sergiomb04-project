from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

VALID_CATEGORIES = [
    "carrier_last_mile",
    "carrier_international",
    "warehouse_supplies",
    "packaging_materials",
    "reverse_logistics",
    "fleet_maintenance",
    "it_and_wms_software",
    "cleaning_and_facilities",
]

VALID_STATUSES = ["active", "suspended"]


class SupplierCategory(StrEnum):
    CARRIER_LAST_MILE = "carrier_last_mile"
    CARRIER_INTERNATIONAL = "carrier_international"
    WAREHOUSE_SUPPLIES = "warehouse_supplies"
    PACKAGING_MATERIALS = "packaging_materials"
    REVERSE_LOGISTICS = "reverse_logistics"
    FLEET_MAINTENANCE = "fleet_maintenance"
    IT_AND_WMS_SOFTWARE = "it_and_wms_software"
    CLEANING_AND_FACILITIES = "cleaning_and_facilities"


class SupplierStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class SupplierCountry(StrEnum):
    USA = "USA"
    SPAIN = "Spain"


class SupplierCurrency(StrEnum):
    USD = "USD"
    EUR = "EUR"


class SupplierBase(BaseModel):
    name: str = Field(min_length=1)
    country: SupplierCountry
    categories: list[SupplierCategory] = Field(min_length=1)
    rate_per_shipment: float = Field(gt=0)
    currency: SupplierCurrency
    status: SupplierStatus
    service_zone: str | None = None
    contact_email: str | None = None
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("service_zone", "notes", "contact_email", mode="before")
    @classmethod
    def _strip_optional_strings(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
            if value == "":
                return None
        return value

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        if value is None or value.strip() == "":
            raise ValueError("name no puede estar vacio")
        return value.strip()

    @field_validator("contact_email")
    @classmethod
    def _validate_contact_email(cls, value: str | None) -> str | None:
        if value is None:
            return None

        if "@" not in value:
            raise ValueError("contact_email debe ser un email valido")

        return value

    @model_validator(mode="after")
    def _validate_country_currency(self) -> "SupplierBase":
        if self.country == SupplierCountry.USA and self.currency != SupplierCurrency.USD:
            raise ValueError("Para country='USA' currency debe ser 'USD'")
        if self.country == SupplierCountry.SPAIN and self.currency != SupplierCurrency.EUR:
            raise ValueError("Para country='Spain' currency debe ser 'EUR'")
        return self


class SupplierCreate(SupplierBase):
    pass


class Supplier(SupplierBase):
    id: str
    updated_at: datetime


class SupplierRateUpdate(BaseModel):
    rate_per_shipment: float = Field(gt=0)

    model_config = ConfigDict(extra="forbid")


class SupplierStatusUpdate(BaseModel):
    status: SupplierStatus

    model_config = ConfigDict(extra="forbid")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def supplier_record_from_create(payload: SupplierCreate) -> Supplier:
    data = payload.model_dump()
    return Supplier(
        id=str(uuid4()),
        updated_at=now_utc(),
        **data,
    )
