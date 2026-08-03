from __future__ import annotations

from fastapi.testclient import TestClient


def _create_product(client: TestClient, token: str, sku: str = "CLT-SNK-W-42") -> dict:
    response = client.post(
        "/inventory/products",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Zapatilla blanca clasica - Talla 42",
            "sku": sku,
            "client_name": "PureStep Footwear",
            "category": "fashion",
            "warehouse": "LA",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_inventory_products_flow(monkeypatch_env: None, client: TestClient, user_token: str) -> None:
    created = _create_product(client, user_token)

    list_response = client.get("/inventory/products")
    assert list_response.status_code == 200
    products = list_response.json()
    assert len(products) == 1
    assert products[0]["current_stock"] == 0

    product_id = created["id"]
    get_response = client.get(f"/inventory/products/{product_id}")
    assert get_response.status_code == 200
    product = get_response.json()
    assert product["sku"] == "CLT-SNK-W-42"
    assert product["warehouse"] == "LA"
    assert product["current_stock"] == 0


def test_inventory_outbound_rejects_negative_stock(monkeypatch_env: None, client: TestClient, user_token: str) -> None:
    created = _create_product(client, user_token, sku="TEC-EAR-001")

    outbound_response = client.post(
        "/inventory/orders/outbound",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "sku_id": created["id"],
            "quantity": 5,
            "exit_type": "dispatch",
            "tracking_number": "1Z999AA10123456784",
            "warehouse": "LA",
        },
    )

    assert outbound_response.status_code == 400
    assert "Insufficient stock for SKU 'TEC-EAR-001'" in outbound_response.json()["detail"]


def test_inventory_tracking_validation(monkeypatch_env: None, client: TestClient, user_token: str) -> None:
    created = _create_product(client, user_token, sku="CSM-SRM-030")

    missing_tracking = client.post(
        "/inventory/orders/outbound",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "sku_id": created["id"],
            "quantity": 1,
            "exit_type": "dispatch",
            "warehouse": "LA",
        },
    )
    assert missing_tracking.status_code == 400

    invalid_tracking_for_loss = client.post(
        "/inventory/orders/outbound",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "sku_id": created["id"],
            "quantity": 1,
            "exit_type": "loss",
            "tracking_number": "TRACK-123",
            "warehouse": "LA",
        },
    )
    assert invalid_tracking_for_loss.status_code == 400


def test_inventory_orders_persist_user_uuid(monkeypatch_env: None, client: TestClient, user_token: str) -> None:
    created = _create_product(client, user_token, sku="CLT-CHN-N-32")

    inbound_response = client.post(
        "/inventory/orders/inbound",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "sku_id": created["id"],
            "quantity": 12,
            "reference": "PO-2024-0098",
            "warehouse": "LA",
        },
    )
    assert inbound_response.status_code == 201
    inbound_payload = inbound_response.json()
    assert inbound_payload["user_uuid"]

    outbound_response = client.post(
        "/inventory/orders/outbound",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "sku_id": created["id"],
            "quantity": 4,
            "exit_type": "dispatch",
            "tracking_number": "1Z999AA10123456784",
            "warehouse": "LA",
        },
    )
    assert outbound_response.status_code == 201
    outbound_payload = outbound_response.json()
    assert outbound_payload["user_uuid"] == inbound_payload["user_uuid"]

    orders_response = client.get("/inventory/orders")
    assert orders_response.status_code == 200
    orders = orders_response.json()["orders"]
    assert len(orders) == 2

    product_response = client.get(f"/inventory/products/{created['id']}")
    assert product_response.status_code == 200
    assert product_response.json()["current_stock"] == 8
