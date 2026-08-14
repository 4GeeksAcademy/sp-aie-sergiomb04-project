from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from trackflow_api.cache import api_cache
from trackflow_api.routes import incidents as incidents_routes
from trackflow_api.routes import suppliers as suppliers_routes


def _create_user_and_token(client: TestClient, email: str) -> str:
    response = client.post(
        "/users",
        json={
            "email": email,
            "password": "Secret123",
            "name": "Test User",
            "phone": "+1 555 000 0000",
            "address": "Address",
        },
    )
    assert response.status_code == 201

    login = client.post("/auth/login", json={"email": email, "password": "Secret123"})
    assert login.status_code == 200
    return login.json()["access_token"]


def _create_supplier(client: TestClient, token: str, name: str) -> str:
    response = client.post(
        "/suppliers",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "country": "USA",
            "categories": ["carrier_last_mile"],
            "rate_per_shipment": 7.5,
            "currency": "USD",
            "status": "active",
            "service_zone": "West Coast",
            "contact_email": f"{name.lower().replace(' ', '')}@example.com",
            "notes": "seed",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_incident(client: TestClient, token: str, title: str) -> str:
    response = client.post(
        "/api/incidents",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": title,
            "description": "Descripcion de prueba",
            "category": "carrier_last_mile",
            "origin": "customer",
            "branch": "los_angeles",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


class _BrokenTinyDb:
    def all(self):
        raise RuntimeError("forced db failure")

    def close(self):
        return None


class _BrokenIncidentsDb:
    class _BrokenTable:
        @staticmethod
        def all():
            raise RuntimeError("forced db failure")

    def table(self, _name: str):
        return self._BrokenTable()

    def close(self):
        return None


def test_suppliers_cache_hit_and_timing_header(
    client: TestClient,
    monkeypatch_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api_cache.clear()
    token = _create_user_and_token(client, "cache-hit@example.com")
    _create_supplier(client, token, "Cache Supplier A")

    first = client.get("/suppliers", headers={"Authorization": f"Bearer {token}"})
    assert first.status_code == 200
    assert first.headers.get("x-process-time-ms") is not None

    def _fail_db():
        raise RuntimeError("DB should not be called on cache hit")

    monkeypatch.setattr(suppliers_routes, "get_tinydb", _fail_db)
    second = client.get("/suppliers", headers={"Authorization": f"Bearer {token}"})
    assert second.status_code == 200
    assert len(second.json()) == len(first.json())


def test_suppliers_cache_invalidation_after_write(
    client: TestClient,
    monkeypatch_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api_cache.clear()
    token = _create_user_and_token(client, "cache-invalidate@example.com")
    supplier_id = _create_supplier(client, token, "Cache Supplier B")

    cached = client.get("/suppliers", headers={"Authorization": f"Bearer {token}"})
    assert cached.status_code == 200

    updated = client.patch(
        f"/suppliers/{supplier_id}/rate",
        headers={"Authorization": f"Bearer {token}"},
        json={"rate_per_shipment": 9.1},
    )
    assert updated.status_code == 200

    def _fail_db():
        return _BrokenTinyDb()

    monkeypatch.setattr(suppliers_routes, "get_tinydb", _fail_db)
    after_write = client.get("/suppliers", headers={"Authorization": f"Bearer {token}"})
    assert after_write.status_code == 500


def test_suppliers_cache_is_user_scoped(
    client: TestClient,
    monkeypatch_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api_cache.clear()
    token_a = _create_user_and_token(client, "cache-user-a@example.com")
    token_b = _create_user_and_token(client, "cache-user-b@example.com")
    _create_supplier(client, token_a, "Cache Supplier Shared")

    warm = client.get("/suppliers", headers={"Authorization": f"Bearer {token_a}"})
    assert warm.status_code == 200

    def _fail_db():
        return _BrokenTinyDb()

    monkeypatch.setattr(suppliers_routes, "get_tinydb", _fail_db)
    isolated = client.get("/suppliers", headers={"Authorization": f"Bearer {token_b}"})
    assert isolated.status_code == 500


def test_incidents_summary_cache_hit_and_invalidation(
    client: TestClient,
    monkeypatch_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api_cache.clear()
    token = _create_user_and_token(client, "cache-incidents@example.com")
    incident_id = _create_incident(client, token, "Incidente cache")

    first_summary = client.get("/api/incidents/summary", headers={"Authorization": f"Bearer {token}"})
    assert first_summary.status_code == 200
    assert first_summary.json()["total"] >= 1

    original_get_incidents_db = incidents_routes.get_incidents_db

    def _fail_db():
        return _BrokenIncidentsDb()

    monkeypatch.setattr(incidents_routes, "get_incidents_db", _fail_db)
    second_summary = client.get("/api/incidents/summary", headers={"Authorization": f"Bearer {token}"})
    assert second_summary.status_code == 200

    monkeypatch.setattr(incidents_routes, "get_incidents_db", original_get_incidents_db)

    changed = client.patch(
        f"/api/incidents/{incident_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "in_progress"},
    )
    assert changed.status_code == 200

    monkeypatch.setattr(incidents_routes, "get_incidents_db", _fail_db)
    after_write = client.get("/api/incidents/summary", headers={"Authorization": f"Bearer {token}"})
    assert after_write.status_code == 500
