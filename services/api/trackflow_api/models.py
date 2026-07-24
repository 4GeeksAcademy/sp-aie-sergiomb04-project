from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

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


class UserRole(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"


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


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1)
    phone: str = Field(min_length=1)
    address: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: EmailStr) -> str:
        return str(value).lower().strip()

    @field_validator("name", "phone", "address", mode="before")
    @classmethod
    def _strip_required_strings(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
        return value


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)
    is_active: bool | None = None
    role: UserRole | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("email")
    @classmethod
    def _normalize_optional_email(cls, value: EmailStr | None) -> str | None:
        if value is None:
            return None
        return str(value).lower().strip()


class UserRecord(BaseModel):
    id: str
    email: EmailStr
    hashed_password: str
    is_active: bool
    role: UserRole
    created_at: datetime

    model_config = ConfigDict(extra="forbid")


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    is_active: bool
    role: UserRole
    created_at: datetime

    model_config = ConfigDict(extra="forbid")


class ProfileBase(BaseModel):
    name: str = Field(min_length=1)
    phone: str = Field(min_length=1)
    address: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name", "phone", "address", mode="before")
    @classmethod
    def _strip_profile_strings(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
        return value


class ProfileUpdate(ProfileBase):
    pass


class ProfileRecord(ProfileBase):
    id: str
    user_id: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("email")
    @classmethod
    def _normalize_login_email(cls, value: EmailStr) -> str:
        return str(value).lower().strip()


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    model_config = ConfigDict(extra="forbid")

    @field_validator("email")
    @classmethod
    def _normalize_forgot_email(cls, value: EmailStr) -> str:
        return str(value).lower().strip()


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=16)
    new_password: str = Field(min_length=8)

    model_config = ConfigDict(extra="forbid")


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)

    model_config = ConfigDict(extra="forbid")


class MessageResponse(BaseModel):
    detail: str


class PasswordResetTokenRecord(BaseModel):
    id: str
    user_id: str
    token_hash: str
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthMeResponse(BaseModel):
    email: EmailStr
    role: UserRole
    profile: ProfileRecord


def user_record_from_create(payload: UserCreate, hashed_password: str) -> UserRecord:
    return UserRecord(
        id=str(uuid4()),
        email=payload.email,
        hashed_password=hashed_password,
        is_active=True,
        role=UserRole.USER,
        created_at=now_utc(),
    )


def profile_record_from_user_create(user_id: str, payload: UserCreate) -> ProfileRecord:
    return ProfileRecord(
        id=str(uuid4()),
        user_id=user_id,
        name=payload.name,
        phone=payload.phone,
        address=payload.address,
    )


def user_public_from_record(record: UserRecord) -> UserPublic:
    return UserPublic(
        id=record.id,
        email=record.email,
        is_active=record.is_active,
        role=record.role,
        created_at=record.created_at,
    )


def password_reset_token_record_from_create(
    user_id: str,
    token_hash: str,
    expires_at: datetime,
) -> PasswordResetTokenRecord:
    return PasswordResetTokenRecord(
        id=str(uuid4()),
        user_id=user_id,
        token_hash=token_hash,
        created_at=now_utc(),
        expires_at=expires_at,
        used_at=None,
    )


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def supplier_record_from_create(payload: SupplierCreate) -> Supplier:
    data = payload.model_dump()
    return Supplier(
        id=str(uuid4()),
        updated_at=now_utc(),
        **data,
    )
