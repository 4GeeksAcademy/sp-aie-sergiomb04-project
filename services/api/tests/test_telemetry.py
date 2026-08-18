from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from trackflow_api.database import get_inventory_engine
from trackflow_api.models import TelemetryEventRecord


def test_telemetry_events_valid_batch(monkeypatch_env: None, client: TestClient) -> None:
    payload = {
        "events": [
            {
                "eventId": "11111111-1111-4111-8111-111111111111",
                "timestamp": "2026-08-14T18:30:00.000Z",
                "sessionId": "22222222-2222-4222-8222-222222222222",
                "userId": "user-123",
                "event_type": "inbound_order_created",
                "schemaVersion": "1.0.0",
                "requestId": "33333333-3333-4333-8333-333333333333",
                "properties": {
                    "warehouse": "los_angeles",
                    "client_id": "PureStep Footwear",
                    "product_id": "CLT-SNK-W-42",
                    "product_category": "fashion",
                    "quantity": 10,
                    "order_id": "1",
                    "reference": "PO-2024-0098",
                    "user_uuid": "user-123",
                },
            },
            {
                "eventId": "44444444-4444-4444-8444-444444444444",
                "timestamp": "2026-08-14T18:30:05.000Z",
                "sessionId": "22222222-2222-4222-8222-222222222222",
                "userId": None,
                "event_type": "auth_login_failed",
                "schemaVersion": "1.0.0",
                "requestId": "55555555-5555-4555-8555-555555555555",
                "properties": {
                    "auth_method": "password",
                    "failure_reason": "Credenciales invalidas",
                    "failure_code": "invalid_credentials",
                    "identity_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    "device_type": "desktop",
                },
            },
        ]
    }

    response = client.post("/telemetry/events", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data == {"received": 2, "stored": 2, "rejected": 0}

    with Session(get_inventory_engine()) as db:
        ev1 = db.get(TelemetryEventRecord, "11111111-1111-4111-8111-111111111111")
        assert ev1 is not None
        assert ev1.event_type == "inbound_order_created"
        assert ev1.session_id == "22222222-2222-4222-8222-222222222222"
        assert ev1.user_id == "user-123"
        assert ev1.service == "backoffice"
        assert ev1.request_id == "33333333-3333-4333-8333-333333333333"
        assert ev1.tags["warehouse"] == "los_angeles"
        assert ev1.tags["quantity"] == 10

        ev2 = db.get(TelemetryEventRecord, "44444444-4444-4444-8444-444444444444")
        assert ev2 is not None
        assert ev2.event_type == "auth_login_failed"
        assert ev2.user_id is None
        assert ev2.tags["auth_method"] == "password"


def test_telemetry_events_mixed_batch(monkeypatch_env: None, client: TestClient) -> None:
    payload = {
        "events": [
            {
                "eventId": "aaaaaaa1-aaaa-4aaa-8aaa-aaaaaaaaaaa1",
                "timestamp": "2026-08-14T19:00:00.000Z",
                "sessionId": "session-mix-1",
                "userId": "user-mix-1",
                "event_type": "outbound_order_created",
                "schemaVersion": "1.0.0",
                "requestId": "req-mix-1",
                "properties": {
                    "warehouse": "los_angeles",
                    "client_id": "PureStep Footwear",
                    "product_id": "CLT-SNK-W-42",
                    "product_category": "fashion",
                    "quantity": 5,
                    "order_id": "100",
                    "exit_type": "dispatch",
                    "tracking_number_present": True,
                    "user_uuid": "user-mix-1",
                },
            },
            {
                # Corrupted / invalid event (missing required envelope fields)
                "event_type": "invalid_corrupted_event",
            },
            {
                "eventId": "aaaaaaa2-aaaa-4aaa-8aaa-aaaaaaaaaaa2",
                "timestamp": "2026-08-14T19:00:01.000Z",
                "sessionId": "session-mix-1",
                "userId": "user-mix-1",
                "event_type": "stock_threshold_triggered",
                "schemaVersion": "1.0.0",
                "requestId": "req-mix-2",
                "properties": {
                    "warehouse": "los_angeles",
                    "client_id": "PureStep Footwear",
                    "product_id": "CLT-SNK-W-42",
                    "product_category": "fashion",
                    "quantity": 2,
                    "minimum_threshold": 10,
                    "deficit_units": 8,
                },
            },
        ]
    }

    response = client.post("/telemetry/events", json=payload)
    assert response.status_code == 200
    assert response.json() == {"received": 3, "stored": 2, "rejected": 1}

    with Session(get_inventory_engine()) as db:
        ev1 = db.get(TelemetryEventRecord, "aaaaaaa1-aaaa-4aaa-8aaa-aaaaaaaaaaa1")
        assert ev1 is not None
        assert ev1.event_type == "outbound_order_created"

        ev2 = db.get(TelemetryEventRecord, "aaaaaaa2-aaaa-4aaa-8aaa-aaaaaaaaaaa2")
        assert ev2 is not None
        assert ev2.event_type == "stock_threshold_triggered"


def test_telemetry_events_all_invalid(monkeypatch_env: None, client: TestClient) -> None:
    payload = {
        "events": [
            {"invalid": 1},
            {"bad_data": True},
        ]
    }

    response = client.post("/telemetry/events", json=payload)
    assert response.status_code == 200
    assert response.json() == {"received": 2, "stored": 0, "rejected": 2}


def test_telemetry_events_allowlist_filtering(monkeypatch_env: None, client: TestClient) -> None:
    payload = {
        "events": [
            {
                "eventId": "bbbbbbb1-bbbb-4bbb-8bbb-bbbbbbbbbbb1",
                "timestamp": "2026-08-14T19:30:00.000Z",
                "sessionId": "session-filter-1",
                "userId": "user-filter-1",
                "event_type": "inbound_order_created",
                "schemaVersion": "1.0.0",
                "requestId": "req-filter-1",
                "properties": {
                    "warehouse": "los_angeles",
                    "client_id": "PureStep Footwear",
                    "product_id": "CLT-SNK-W-42",
                    "product_category": "fashion",
                    "quantity": 10,
                    "order_id": "1",
                    "reference": "PO-2024-0098",
                    "user_uuid": "user-123",
                    # The following extra/forbidden fields must be filtered out of tags:
                    "unauthorized_field": "secret_data",
                    "credit_card": "4111-2222-3333-4444",
                },
            }
        ]
    }

    response = client.post("/telemetry/events", json=payload)
    assert response.status_code == 200
    assert response.json() == {"received": 1, "stored": 1, "rejected": 0}

    with Session(get_inventory_engine()) as db:
        ev = db.get(TelemetryEventRecord, "bbbbbbb1-bbbb-4bbb-8bbb-bbbbbbbbbbb1")
        assert ev is not None
        assert "unauthorized_field" not in ev.tags
        assert "credit_card" not in ev.tags
        assert ev.tags["warehouse"] == "los_angeles"
        assert ev.tags["quantity"] == 10


def test_telemetry_options_preflight(client: TestClient) -> None:
    response = client.options("/telemetry/events")
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert "POST" in response.headers["Access-Control-Allow-Methods"]

