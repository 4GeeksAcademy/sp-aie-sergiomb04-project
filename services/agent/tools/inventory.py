"""Typed read-only tool for querying TrackFlow inventory stock in real time."""

from __future__ import annotations

import logging
import os
import time
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlmodel import create_engine

# Ensure project root and services/api are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SERVICES_API_DIR = PROJECT_ROOT / "services" / "api"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SERVICES_API_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICES_API_DIR))

logger = logging.getLogger("trackflow.agent.tools.inventory")

DEFAULT_INVENTORY_TIMEOUT_SECONDS: float = 3.0


def _get_active_inventory_engine():
    """Return inventory database engine with graceful fallback to local SQLite."""
    from trackflow_api.database import get_inventory_engine

    sqlite_fallback_path = SERVICES_API_DIR / "trackflow_api" / "data" / "inventory.db"
    try:
        engine = get_inventory_engine()
        # Test connection quickly
        with engine.connect() as conn:
            pass
        return engine
    except Exception as exc:
        logger.warning("Remote inventory DB connection failed (%s), using local SQLite fallback", exc)
        return create_engine(
            f"sqlite:///{sqlite_fallback_path}",
            connect_args={"check_same_thread": False},
        )


@dataclass
class InventoryQueryInput:
    """Typed input contract for inventory stock query."""

    query: str
    warehouse: Optional[str] = None
    timeout: float = DEFAULT_INVENTORY_TIMEOUT_SECONDS


@dataclass
class InventoryToolOutput:
    """Typed output contract for inventory stock query."""

    success: bool
    product_query: str
    products: List[Dict[str, Any]] = field(default_factory=list)
    message: str = ""
    error: Optional[str] = None
    is_fallback: bool = False
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def check_inventory_stock(
    product_or_sku: str,
    *,
    warehouse: Optional[str] = None,
    timeout: float = DEFAULT_INVENTORY_TIMEOUT_SECONDS,
) -> InventoryToolOutput:
    """Query live product inventory stock from the inventory manager.

    Read-only operation with strict numerical timeout and honest fallback path.
    """
    t0 = time.perf_counter()
    clean_query = str(product_or_sku).strip()
    effective_timeout = float(timeout) if timeout is not None else DEFAULT_INVENTORY_TIMEOUT_SECONDS

    try:
        from sqlmodel import Session, select
        from trackflow_api.database import get_inventory_engine
        from trackflow_api.models import InboundOrder, OutboundOrder, Product

        engine = _get_active_inventory_engine()
        with Session(engine) as session:
            # Query products matching SKU or Name
            statement = select(Product)
            all_products = session.exec(statement).all()

            duration_ms = (time.perf_counter() - t0) * 1000.0
            if (duration_ms / 1000.0) > effective_timeout:
                return InventoryToolOutput(
                    success=False,
                    product_query=clean_query,
                    message="No pude verificar el stock en este momento porque el servicio de inventario excedió el tiempo de respuesta.",
                    error="Timeout exceeded",
                    is_fallback=True,
                    duration_ms=round(duration_ms, 2),
                )

            # Match products by SKU or Name
            q_lower = clean_query.lower()
            matched_products = []
            for p in all_products:
                if (
                    q_lower in p.sku.lower()
                    or q_lower in p.name.lower()
                    or p.sku.lower() in q_lower
                ):
                    if warehouse and p.warehouse.lower() != warehouse.lower():
                        continue
                    matched_products.append(p)

            if not matched_products:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                return InventoryToolOutput(
                    success=False,
                    product_query=clean_query,
                    message=f"No se encontró ningún producto con SKU o nombre '{clean_query}' en el inventario de TrackFlow.",
                    error="Product not found",
                    is_fallback=True,
                    duration_ms=round(duration_ms, 2),
                )

            # Calculate stock for matched products
            product_results = []
            lines = []
            for p in matched_products:
                inbound_qty = sum(
                    o.quantity
                    for o in session.exec(
                        select(InboundOrder).where(
                            InboundOrder.sku_id == p.id,
                            InboundOrder.warehouse == p.warehouse,
                        )
                    ).all()
                )
                outbound_qty = sum(
                    o.quantity
                    for o in session.exec(
                        select(OutboundOrder).where(
                            OutboundOrder.sku_id == p.id,
                            OutboundOrder.warehouse == p.warehouse,
                        )
                    ).all()
                )
                current_stock = inbound_qty - outbound_qty

                p_data = {
                    "id": p.id,
                    "sku": p.sku,
                    "name": p.name,
                    "warehouse": p.warehouse,
                    "current_stock": current_stock,
                }
                product_results.append(p_data)
                lines.append(
                    f"- {p.name} (SKU: {p.sku}) en almacén {p.warehouse}: {current_stock} unidades disponibles."
                )

            duration_ms = (time.perf_counter() - t0) * 1000.0
            message = "Información de stock en tiempo real:\n" + "\n".join(lines)

            return InventoryToolOutput(
                success=True,
                product_query=clean_query,
                products=product_results,
                message=message,
                is_fallback=False,
                duration_ms=round(duration_ms, 2),
            )

    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000.0
        logger.error(f"Error querying inventory for '{clean_query}': {exc}", exc_info=True)
        return InventoryToolOutput(
            success=False,
            product_query=clean_query,
            message="No pude verificar el stock en este momento debido a una indisponibilidad temporal en el servicio de inventario.",
            error=str(exc),
            is_fallback=True,
            duration_ms=round(duration_ms, 2),
        )
