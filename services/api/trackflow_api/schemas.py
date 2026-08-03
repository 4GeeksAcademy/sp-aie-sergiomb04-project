from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trackflow_api.models import INVENTORY_CATEGORIES, INVENTORY_WAREHOUSES, STOCK_EXIT_TYPES


class ProductBaseSchema(BaseModel):
    name: str = Field(min_length=1)
    sku: str = Field(min_length=1)
    client_name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    warehouse: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_category_and_warehouse(self) -> "ProductBaseSchema":
        if self.category not in INVENTORY_CATEGORIES:
            raise ValueError(
                f"Invalid category. Allowed values: {', '.join(INVENTORY_CATEGORIES)}"
            )
        if self.warehouse not in INVENTORY_WAREHOUSES:
            raise ValueError(
                f"Invalid warehouse. Allowed values: {', '.join(INVENTORY_WAREHOUSES)}"
            )
        return self


class ProductCreateSchema(ProductBaseSchema):
    pass


class ProductResponseSchema(ProductBaseSchema):
    id: int
    current_stock: int


class InboundOrderCreateSchema(BaseModel):
    sku_id: int
    quantity: int = Field(gt=0)
    reference: str = Field(min_length=1)
    warehouse: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_warehouse(self) -> "InboundOrderCreateSchema":
        if self.warehouse not in INVENTORY_WAREHOUSES:
            raise ValueError(
                f"Invalid warehouse. Allowed values: {', '.join(INVENTORY_WAREHOUSES)}"
            )
        return self


class InboundOrderResponseSchema(BaseModel):
    id: int
    sku_id: int
    quantity: int
    reference: str
    warehouse: str
    created_at: datetime
    user_uuid: str


class OutboundOrderCreateSchema(BaseModel):
    sku_id: int
    quantity: int = Field(gt=0)
    exit_type: str = Field(min_length=1)
    tracking_number: str | None = None
    warehouse: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_constraints(self) -> "OutboundOrderCreateSchema":
        if self.exit_type not in STOCK_EXIT_TYPES:
            raise ValueError(
                f"Invalid exit_type. Allowed values: {', '.join(STOCK_EXIT_TYPES)}"
            )

        if self.warehouse not in INVENTORY_WAREHOUSES:
            raise ValueError(
                f"Invalid warehouse. Allowed values: {', '.join(INVENTORY_WAREHOUSES)}"
            )

        if self.exit_type == "dispatch" and not self.tracking_number:
            raise ValueError("tracking_number is required when exit_type is 'dispatch'")

        if self.exit_type == "loss" and self.tracking_number is not None:
            raise ValueError("tracking_number must be null when exit_type is 'loss'")

        return self


class OutboundOrderResponseSchema(BaseModel):
    id: int
    sku_id: int
    quantity: int
    exit_type: str
    tracking_number: str | None
    warehouse: str
    created_at: datetime
    user_uuid: str


class InventoryOrderReadSchema(BaseModel):
    id: int
    order_type: str
    sku_id: int
    sku: str
    product_name: str
    quantity: int
    warehouse: str
    created_at: datetime
    user_uuid: str
    reference: str | None = None
    exit_type: str | None = None
    tracking_number: str | None = None


class InventoryOrdersResponseSchema(BaseModel):
    orders: list[InventoryOrderReadSchema]
