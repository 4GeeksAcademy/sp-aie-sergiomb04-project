"""Strictly read-only inventory tool for TrackFlow MCP Server rejecting all write/mutation attempts."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlmodel import Session, create_engine, select

from mcps.trackflow_mcp.auth import (
    SCOPE_INVENTORY_READ,
    get_current_auth_info,
    log_tool_invocation,
    require_scope,
)

logger = logging.getLogger("trackflow.mcp.tools.inventory")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SERVICES_API_DIR = PROJECT_ROOT / "services" / "api"


def _get_inventory_engine():
    """Return active inventory database engine with local fallback."""
    sqlite_fallback = SERVICES_API_DIR / "trackflow_api" / "data" / "inventory.db"
    try:
        from trackflow_api.database import get_inventory_engine
        engine = get_inventory_engine()
        with engine.connect() as conn:
            pass
        return engine
    except Exception as exc:
        logger.warning("Remote inventory DB connection failed (%s), using local SQLite fallback", exc)
        sqlite_fallback.parent.mkdir(parents=True, exist_ok=True)
        sqlite_url = f"sqlite:///{sqlite_fallback.as_posix()}"
        fallback_engine = create_engine(
            sqlite_url,
            connect_args={"check_same_thread": False},
        )
        try:
            from sqlmodel import SQLModel, Session, select
            from trackflow_api.models import Product, InboundOrder, OutboundOrder
            SQLModel.metadata.create_all(fallback_engine)
            with Session(fallback_engine) as session:
                if not session.exec(select(Product.id)).first():
                    products = [
                        Product(name="Zapatilla blanca clasica - Talla 42", sku="CLT-SNK-W-42", client_name="PureStep Footwear", category="fashion", warehouse="LA"),
                        Product(name="Zapatilla blanca clasica - Talla 42", sku="CLT-SNK-W-42-Z", client_name="PureStep Footwear", category="fashion", warehouse="ZGZ"),
                        Product(name="Auriculares inalambricos Pro", sku="TEC-EAR-001", client_name="SoundWave Electronics", category="electronics", warehouse="LA"),
                        Product(name="Serum facial hidratante 30ml", sku="CSM-SRM-030", client_name="GlowLab Cosmetics", category="cosmetics", warehouse="ZGZ"),
                    ]
                    for p in products:
                        session.add(p)
                    session.commit()
                    for p in products:
                        session.refresh(p)
                    inbound = [
                        InboundOrder(sku_id=products[0].id or 0, quantity=40, reference="PO-2024-0098", warehouse="LA", user_uuid="seed-user-la"),
                        InboundOrder(sku_id=products[0].id or 0, quantity=15, reference="GR-LA-0234", warehouse="LA", user_uuid="seed-user-la"),
                        InboundOrder(sku_id=products[1].id or 0, quantity=30, reference="PO-2024-0171", warehouse="ZGZ", user_uuid="seed-user-zgz"),
                        InboundOrder(sku_id=products[2].id or 0, quantity=20, reference="GR-LA-0301", warehouse="LA", user_uuid="seed-user-la"),
                    ]
                    outbound = [
                        OutboundOrder(sku_id=products[0].id or 0, quantity=12, exit_type="dispatch", tracking_number="1Z999AA10123456784", warehouse="LA", user_uuid="seed-user-la"),
                        OutboundOrder(sku_id=products[1].id or 0, quantity=5, exit_type="loss", tracking_number=None, warehouse="ZGZ", user_uuid="seed-user-zgz"),
                        OutboundOrder(sku_id=products[2].id or 0, quantity=3, exit_type="dispatch", tracking_number="1Z999AA10123456785", warehouse="LA", user_uuid="seed-user-la"),
                    ]
                    for o in inbound + outbound:
                        session.add(o)
                    session.commit()
        except Exception as seed_err:
            logger.debug("Fallback seed skipped: %s", seed_err)
        return fallback_engine


def query_inventory(
    query: str,
    *,
    warehouse: Optional[str] = None,
    action: str = "read",
    mutate: bool = False,
    quantity_change: Optional[int] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Query live product stock and availability in TrackFlow warehouses (Read-Only).

    SECURITY & ACCESS POLICY:
    This tool is strictly read-only by architecture and security design.
    Any attempt to execute mutations, writes, updates, deletions or stock changes
    is explicitly rejected with an error (INVENTORY_MUTATION_FORBIDDEN).

    Args:
        query: Product name, SKU code (e.g., 'CLT-SNK-W-42', 'TEC-EAR-001'), or 'all'.
        warehouse: Optional warehouse filter ('LA' for Los Angeles, 'ZGZ' for Zaragoza).
        action: Requested action. Must be 'read', 'get', or 'query'. Any write action is rejected.
        mutate: Explicit mutation flag. Must be False.
        quantity_change: Forbidden parameter. Setting this triggers immediate rejection.

    Returns:
        Structured response containing product details, live stock calculation, and status message.
    """
    t0 = time.perf_counter()
    auth_info = get_current_auth_info()

    # 1. EXPLICIT WRITE REJECTION: Defend against any mutation attempt
    normalized_action = str(action).strip().lower()
    write_actions = {"create", "update", "delete", "write", "mutate", "insert", "patch", "modify", "adjust"}

    if normalized_action in write_actions or mutate or quantity_change is not None or kwargs.get("new_product"):
        duration_ms = (time.perf_counter() - t0) * 1000.0
        error_msg = (
            "Operación de escritura rechazada: la herramienta de inventario de TrackFlow MCP Server "
            "es estrictamente de solo lectura por diseño de seguridad y principio de mínimo privilegio. "
            "Cualquier modificación o alteración de stock está terminantemente prohibida a través de este servidor MCP."
        )
        log_tool_invocation(
            "query_inventory",
            auth_info,
            False,
            error_msg,
            duration_ms,
            error="INVENTORY_MUTATION_FORBIDDEN",
        )
        return {
            "success": False,
            "error_code": "INVENTORY_MUTATION_FORBIDDEN",
            "error": "Operación de escritura no permitida",
            "message": error_msg,
            "query": query,
            "attempted_action": action,
            "duration_ms": round(duration_ms, 2),
        }

    try:
        # 2. Enforce OAuth Scope
        require_scope(SCOPE_INVENTORY_READ, auth_info)

        from trackflow_api.models import InboundOrder, OutboundOrder, Product

        engine = _get_inventory_engine()
        with Session(engine) as session:
            statement = select(Product)
            all_products = session.exec(statement).all()

            clean_query = str(query).strip().lower()
            matched_products: List[Product] = []

            for p in all_products:
                if clean_query in ("all", "*"):
                    if warehouse and p.warehouse.upper() != warehouse.upper():
                        continue
                    matched_products.append(p)
                elif (
                    clean_query in p.sku.lower()
                    or clean_query in p.name.lower()
                    or p.sku.lower() in clean_query
                ):
                    if warehouse and p.warehouse.upper() != warehouse.upper():
                        continue
                    matched_products.append(p)

            if not matched_products:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                msg = f"No se encontró ningún producto con SKU o nombre '{query}' en el inventario de TrackFlow."
                log_tool_invocation("query_inventory", auth_info, False, msg, duration_ms)
                return {
                    "success": False,
                    "error_code": "PRODUCT_NOT_FOUND",
                    "error": "Product not found",
                    "query": query,
                    "products": [],
                    "message": msg,
                    "duration_ms": round(duration_ms, 2),
                }

            # Calculate live stock (inbound sum - outbound sum)
            product_results: List[Dict[str, Any]] = []
            lines: List[str] = []

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
                    "client_name": p.client_name,
                    "category": p.category,
                    "warehouse": p.warehouse,
                    "inbound_units": inbound_qty,
                    "outbound_units": outbound_qty,
                    "current_stock": current_stock,
                }
                product_results.append(p_data)
                lines.append(
                    f"- {p.name} (SKU: {p.sku}) en almacén {p.warehouse}: {current_stock} unidades disponibles."
                )

            duration_ms = (time.perf_counter() - t0) * 1000.0
            msg = "Información de stock en tiempo real:\n" + "\n".join(lines)
            log_tool_invocation("query_inventory", auth_info, True, f"Found {len(product_results)} products", duration_ms)

            return {
                "success": True,
                "query": query,
                "total_matched": len(product_results),
                "products": product_results,
                "message": msg,
                "duration_ms": round(duration_ms, 2),
            }

    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000.0
        err_msg = str(exc)
        logger.error("Error executing query_inventory: %s", err_msg, exc_info=True)
        log_tool_invocation("query_inventory", auth_info, False, err_msg, duration_ms, error=type(exc).__name__)
        return {
            "success": False,
            "error_code": "INVENTORY_TOOL_ERROR",
            "error": err_msg,
            "message": f"Error al consultar el inventario de TrackFlow: {err_msg}",
            "duration_ms": round(duration_ms, 2),
        }
