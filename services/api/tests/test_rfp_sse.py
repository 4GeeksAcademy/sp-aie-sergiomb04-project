"""SSE endpoint tests for TrackFlow API (`services/api/tests/test_rfp_sse.py`)."""

from __future__ import annotations

import json
from typing import Any

from fastapi.testclient import TestClient

from trackflow_api.sse import rfp_sse_broker


def _extract_sse_events(raw_text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for block in raw_text.split("\n\n"):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip() and not ln.strip().startswith(":")]
        if not lines:
            continue
        ev_name = "message"
        ev_id = None
        data_str = ""
        for ln in lines:
            if ln.startswith("id:"):
                ev_id = ln[3:].strip()
            elif ln.startswith("event:"):
                ev_name = ln[6:].strip()
            elif ln.startswith("data:"):
                data_str = ln[5:].strip()
        if data_str:
            events.append({"id": ev_id, "event": ev_name, "data": json.loads(data_str)})
    return events


def test_rfp_sse_endpoint_validates_jwt_and_emits_rfp_ticket_created(
    monkeypatch_env: None,
    client: TestClient,
    user_token: str,
) -> None:
    """Verify SSE headers, JWT requirement, `event: rfp_ticket_created`, and JSON payload structure."""
    rfp_sse_broker.clear()

    # Without JWT -> 401
    unauth = client.get("/api/rfp/stream")
    assert unauth.status_code == 401

    # Register ticket
    created = client.post(
        "/api/rfp/tickets",
        json={
            "client_name": "Luna Cosmetics",
            "client_country": "USA",
            "currency": "USD",
            "services_requested": ["warehousing", "last_mile"],
            "monthly_volume": 5000,
            "deadline": "2026-12-01",
            "budget_range": "25,000 - 35,000 USD/month",
            "departments_needed": ["warehouse", "lastmile"],
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert created.status_code == 201
    ticket_id = created.json()["ticket_id"]

    resp = client.get(
        "/api/rfp/stream",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert "event: rfp_ticket_created" in resp.text

    events = _extract_sse_events(resp.text)
    assert len(events) >= 1
    ev = next(e for e in events if e["data"]["ticket_id"] == ticket_id)
    assert ev["event"] == "rfp_ticket_created"
    payload = ev["data"]
    assert payload["ticket_id"] == ticket_id
    assert payload["rfp_id"].startswith("RFP-")
    assert payload["status"] == "analizando"
    assert payload["raw_pdf_path"].endswith(".pdf")
    assert payload["client_name"] == "Luna Cosmetics"
    assert payload["client_country"] == "USA"
    assert payload["currency"] == "USD"
    assert payload["departments_needed"] == ["warehouse", "lastmile"]
    assert "created_at" in payload
    assert "updated_at" in payload
