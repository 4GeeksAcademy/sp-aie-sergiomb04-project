from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, func, select

from trackflow_api.auth import get_current_user
from trackflow_api.database import get_db
from trackflow_api.models import InboundOrder, OutboundOrder, Product, UserRecord
from trackflow_api.schemas import (
    InboundOrderCreateSchema,
    InboundOrderResponseSchema,
    InventoryOrderReadSchema,
    InventoryOrdersResponseSchema,
    OutboundOrderCreateSchema,
    OutboundOrderResponseSchema,
    ProductCreateSchema,
    ProductResponseSchema,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _get_product_or_404(db: Session, sku_id: int) -> Product:
    product = db.get(Product, sku_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SKU not found")
    return product


def _calculate_current_stock(db: Session, sku_id: int, warehouse: str) -> int:
    inbound_total = db.exec(
        select(func.coalesce(func.sum(InboundOrder.quantity), 0)).where(
            InboundOrder.sku_id == sku_id,
            InboundOrder.warehouse == warehouse,
        )
    ).one()

    outbound_total = db.exec(
        select(func.coalesce(func.sum(OutboundOrder.quantity), 0)).where(
            OutboundOrder.sku_id == sku_id,
            OutboundOrder.warehouse == warehouse,
        )
    ).one()

    return int(inbound_total - outbound_total)


def _build_product_response(db: Session, product: Product) -> ProductResponseSchema:
    stock = _calculate_current_stock(db, product.id or 0, product.warehouse)
    return ProductResponseSchema(
        id=product.id or 0,
        name=product.name,
        sku=product.sku,
        client_name=product.client_name,
        category=product.category,
        warehouse=product.warehouse,
        current_stock=stock,
    )


def _build_stock_map(db: Session) -> dict[tuple[int, str], int]:
    inbound_rows = db.exec(
        select(InboundOrder.sku_id, InboundOrder.warehouse, func.sum(InboundOrder.quantity))
        .group_by(InboundOrder.sku_id, InboundOrder.warehouse)
    ).all()

    outbound_rows = db.exec(
        select(OutboundOrder.sku_id, OutboundOrder.warehouse, func.sum(OutboundOrder.quantity))
        .group_by(OutboundOrder.sku_id, OutboundOrder.warehouse)
    ).all()

    stock_map: dict[tuple[int, str], int] = {}

    for sku_id, warehouse, total in inbound_rows:
        stock_map[(int(sku_id), str(warehouse))] = int(total or 0)

    for sku_id, warehouse, total in outbound_rows:
        key = (int(sku_id), str(warehouse))
        stock_map[key] = stock_map.get(key, 0) - int(total or 0)

    return stock_map


@router.get("/products", response_model=list[ProductResponseSchema], status_code=status.HTTP_200_OK)
def list_products(db: Session = Depends(get_db)) -> list[ProductResponseSchema]:
    products = db.exec(select(Product).order_by(Product.id)).all()
    stock_map = _build_stock_map(db)
    return [
        ProductResponseSchema(
            id=product.id or 0,
            name=product.name,
            sku=product.sku,
            client_name=product.client_name,
            category=product.category,
            warehouse=product.warehouse,
            current_stock=stock_map.get((product.id or 0, product.warehouse), 0),
        )
        for product in products
    ]


@router.post("/products", response_model=ProductResponseSchema, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreateSchema,
    db: Session = Depends(get_db),
    _: UserRecord = Depends(get_current_user),
) -> ProductResponseSchema:
    existing = db.exec(select(Product).where(Product.sku == payload.sku)).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SKU already exists")

    product = Product(
        name=payload.name.strip(),
        sku=payload.sku.strip(),
        client_name=payload.client_name.strip(),
        category=payload.category,
        warehouse=payload.warehouse,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    return _build_product_response(db, product)


@router.get("/products/{sku_id}", response_model=ProductResponseSchema, status_code=status.HTTP_200_OK)
def get_product(sku_id: int, db: Session = Depends(get_db)) -> ProductResponseSchema:
    product = _get_product_or_404(db, sku_id)
    return _build_product_response(db, product)


@router.post("/orders/inbound", response_model=InboundOrderResponseSchema, status_code=status.HTTP_201_CREATED)
def create_inbound_order(
    payload: InboundOrderCreateSchema,
    db: Session = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
) -> InboundOrderResponseSchema:
    product = _get_product_or_404(db, payload.sku_id)

    if product.warehouse != payload.warehouse:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Warehouse mismatch for SKU and stock entry.",
        )

    order = InboundOrder(
        sku_id=payload.sku_id,
        quantity=payload.quantity,
        reference=payload.reference.strip(),
        warehouse=payload.warehouse,
        user_uuid=current_user.id,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    return InboundOrderResponseSchema(
        id=order.id or 0,
        sku_id=order.sku_id,
        quantity=order.quantity,
        reference=order.reference,
        warehouse=order.warehouse,
        created_at=order.created_at,
        user_uuid=order.user_uuid,
    )


@router.post("/orders/outbound", response_model=OutboundOrderResponseSchema, status_code=status.HTTP_201_CREATED)
def create_outbound_order(
    payload: OutboundOrderCreateSchema,
    db: Session = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
) -> OutboundOrderResponseSchema:
    product = _get_product_or_404(db, payload.sku_id)

    if product.warehouse != payload.warehouse:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Warehouse mismatch for SKU and stock exit.",
        )

    available = _calculate_current_stock(db, payload.sku_id, payload.warehouse)
    if payload.quantity > available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Insufficient stock for SKU '{product.sku}'. "
                f"Available: {available}, requested: {payload.quantity}."
            ),
        )

    order = OutboundOrder(
        sku_id=payload.sku_id,
        quantity=payload.quantity,
        exit_type=payload.exit_type,
        tracking_number=payload.tracking_number,
        warehouse=payload.warehouse,
        user_uuid=current_user.id,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    return OutboundOrderResponseSchema(
        id=order.id or 0,
        sku_id=order.sku_id,
        quantity=order.quantity,
        exit_type=order.exit_type,
        tracking_number=order.tracking_number,
        warehouse=order.warehouse,
        created_at=order.created_at,
        user_uuid=order.user_uuid,
    )


@router.get("/orders", response_model=InventoryOrdersResponseSchema, status_code=status.HTTP_200_OK)
def list_orders(db: Session = Depends(get_db)) -> InventoryOrdersResponseSchema:
    inbound_orders = db.exec(
        select(InboundOrder, Product)
        .join(Product, Product.id == InboundOrder.sku_id)
        .order_by(InboundOrder.created_at.desc())
    ).all()
    outbound_orders = db.exec(
        select(OutboundOrder, Product)
        .join(Product, Product.id == OutboundOrder.sku_id)
        .order_by(OutboundOrder.created_at.desc())
    ).all()

    items: list[InventoryOrderReadSchema] = []

    for inbound, product in inbound_orders:
        items.append(
            InventoryOrderReadSchema(
                id=inbound.id or 0,
                order_type="inbound",
                sku_id=inbound.sku_id,
                sku=product.sku,
                product_name=product.name,
                quantity=inbound.quantity,
                warehouse=inbound.warehouse,
                created_at=inbound.created_at,
                user_uuid=inbound.user_uuid,
                reference=inbound.reference,
            )
        )

    for outbound, product in outbound_orders:
        items.append(
            InventoryOrderReadSchema(
                id=outbound.id or 0,
                order_type="outbound",
                sku_id=outbound.sku_id,
                sku=product.sku,
                product_name=product.name,
                quantity=outbound.quantity,
                warehouse=outbound.warehouse,
                created_at=outbound.created_at,
                user_uuid=outbound.user_uuid,
                exit_type=outbound.exit_type,
                tracking_number=outbound.tracking_number,
            )
        )

    items.sort(key=lambda item: item.created_at, reverse=True)
    return InventoryOrdersResponseSchema(orders=items)
