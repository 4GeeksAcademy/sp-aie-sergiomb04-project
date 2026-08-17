from __future__ import annotations

from fastapi.testclient import TestClient


def test_telemetry_events_stub_endpoint(client: TestClient) -> None:
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
    assert response.json() == {"received": 2}


def test_telemetry_events_validation_error(client: TestClient) -> None:
    # Missing required envelope fields
    payload = {
        "events": [
            {
                "event_type": "invalid_event",
            }
        ]
    }

    response = client.post("/telemetry/events", json=payload)
    assert response.status_code == 400 or response.status_code == 422
