from __future__ import annotations

from sqlmodel import Session, select

from trackflow_api.database import get_inventory_engine, init_inventory_db
from trackflow_api.models import InboundOrder, OutboundOrder, Product


def seed_inventory_data() -> None:
    init_inventory_db()

    with Session(get_inventory_engine()) as db:
        existing = db.exec(select(Product.id)).first()
        if existing is not None:
            return

        products = [
            Product(
                name="Zapatilla blanca clasica - Talla 42",
                sku="CLT-SNK-W-42",
                client_name="PureStep Footwear",
                category="fashion",
                warehouse="LA",
            ),
            Product(
                name="Zapatilla blanca clasica - Talla 42",
                sku="CLT-SNK-W-42-Z",
                client_name="PureStep Footwear",
                category="fashion",
                warehouse="ZGZ",
            ),
            Product(
                name="Auriculares inalambricos Pro",
                sku="TEC-EAR-001",
                client_name="SoundWave Electronics",
                category="electronics",
                warehouse="LA",
            ),
            Product(
                name="Serum facial hidratante 30ml",
                sku="CSM-SRM-030",
                client_name="GlowLab Cosmetics",
                category="cosmetics",
                warehouse="ZGZ",
            ),
            Product(
                name="Chino slim fit - marino 32/32",
                sku="CLT-CHN-N-32",
                client_name="UrbanThread",
                category="fashion",
                warehouse="LA",
            ),
            Product(
                name="Cargador rapido USB-C 65W",
                sku="TEC-CHG-065",
                client_name="SoundWave Electronics",
                category="electronics",
                warehouse="ZGZ",
            ),
        ]

        for product in products:
            db.add(product)
        db.commit()

        for product in products:
            db.refresh(product)

        inbound_orders = [
            InboundOrder(
                sku_id=products[0].id or 0,
                quantity=40,
                reference="PO-2024-0098",
                warehouse="LA",
                user_uuid="seed-user-ops-la",
            ),
            InboundOrder(
                sku_id=products[0].id or 0,
                quantity=15,
                reference="GR-LA-0234",
                warehouse="LA",
                user_uuid="seed-user-ops-la",
            ),
            InboundOrder(
                sku_id=products[1].id or 0,
                quantity=30,
                reference="PO-2024-0171",
                warehouse="ZGZ",
                user_uuid="seed-user-ops-zgz",
            ),
            InboundOrder(
                sku_id=products[2].id or 0,
                quantity=20,
                reference="GR-LA-0301",
                warehouse="LA",
                user_uuid="seed-user-ops-la",
            ),
        ]

        outbound_orders = [
            OutboundOrder(
                sku_id=products[0].id or 0,
                quantity=12,
                exit_type="dispatch",
                tracking_number="1Z999AA10123456784",
                warehouse="LA",
                user_uuid="seed-user-logistics-la",
            ),
            OutboundOrder(
                sku_id=products[1].id or 0,
                quantity=5,
                exit_type="loss",
                tracking_number=None,
                warehouse="ZGZ",
                user_uuid="seed-user-logistics-zgz",
            ),
            OutboundOrder(
                sku_id=products[2].id or 0,
                quantity=3,
                exit_type="dispatch",
                tracking_number="1Z999AA10123456785",
                warehouse="LA",
                user_uuid="seed-user-logistics-la",
            ),
        ]

        for order in inbound_orders:
            db.add(order)
        for order in outbound_orders:
            db.add(order)

        db.commit()


def main() -> None:
    seed_inventory_data()
    print("Inventory seed completed.")


if __name__ == "__main__":
    main()
