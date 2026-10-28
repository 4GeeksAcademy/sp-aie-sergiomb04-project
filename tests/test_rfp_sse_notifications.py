"""Automated tests for the TrackFlow RFP SSE Notifications endpoint (`GET /api/rfp/stream`).

Validates:
1. `Content-Type: text/event-stream` and SSE headers + `: keep-alive` comment frames.
2. JWT authentication protection using the same Backoffice JWT (`/auth/login`).
3. Explicit event name (`event: rfp_ticket_created`).
4. Structured JSON payload in `data:` aligned with `company-BRIEFING.md` (`trackflow-BRIEFING.es.md`).
5. Missed event recovery via `Last-Event-ID` without duplication.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from trackflow_api.auth import get_password_hash
from trackflow_api.database import get_users_db, init_inventory_db
from trackflow_api.main import app
from trackflow_api.sse import RFP_TICKET_CREATED_EVENT, rfp_sse_broker

PROJECT_ROOT = Path(__file__).resolve().parents[1]

OFFICIAL_DEPARTMENTS = {"warehouse", "lastmile", "reverse"}
VALID_TICKET_STATUSES = {
    "analizando",
    "descartado",
    "analisis_completo",
    "generando_borrador",
    "en_evaluación",
    "needs_human_review",
    "esperando_aprobación",
    "terminado",
}


def _parse_sse_frames(raw_stream: str) -> list[dict[str, Any]]:
    """Parse raw SSE stream text into structured frames (`id`, `event`, `data`, `comments`)."""
    frames: list[dict[str, Any]] = []
    blocks = [b for b in raw_stream.split("\n\n") if b.strip()]
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if all(line.startswith(":") for line in lines):
            frames.append({"type": "comment", "raw": block.strip()})
            continue

        event_id: str | None = None
        event_name = "message"
        data_lines: list[str] = []

        for line in lines:
            if line.startswith(":"):
                continue
            if line.startswith("id:"):
                event_id = line[len("id:") :].strip()
            elif line.startswith("event:"):
                event_name = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:") :].strip())

        raw_data = "\n".join(data_lines)
        parsed_json = json.loads(raw_data) if raw_data else None
        frames.append(
            {
                "type": "event",
                "id": event_id,
                "event": event_name,
                "data": parsed_json,
                "raw_data": raw_data,
            }
        )
    return frames


@pytest.fixture
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Configure isolated test databases and JWT secret for SSE tests."""
    monkeypatch.setenv("TRACKFLOW_SUPPLIERS_DB_PATH", str(tmp_path / "suppliers-sse-test.json"))
    monkeypatch.setenv("TRACKFLOW_USERS_DB_PATH", str(tmp_path / "users-sse-test.json"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'trackflow-sse-test.db'}")
    monkeypatch.setenv("SECRET_KEY", "trackflow-sse-test-secret")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    init_inventory_db()
    rfp_sse_broker.clear()


@pytest.fixture
def client(isolated_env: None) -> TestClient:
    """Return a FastAPI TestClient bound to the isolated test environment."""
    return TestClient(app)


@pytest.fixture
def backoffice_jwt(client: TestClient) -> str:
    """Create a Backoffice user and obtain a real JWT via POST /auth/login."""
    db = get_users_db()
    db.table("users").insert(
        {
            "id": "miguel-torres-1",
            "email": "miguel.torres@trackflow.com",
            "hashed_password": get_password_hash("TrackFlow2026!"),
            "is_active": True,
            "role": "manager",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    )
    db.table("profiles").insert(
        {
            "id": "profile-miguel-1",
            "user_id": "miguel-torres-1",
            "name": "Miguel Torres",
            "phone": "+34 976 000 111",
            "address": "Zaragoza Logistics Hub",
        }
    )
    db.close()

    resp = client.post(
        "/auth/login",
        json={"email": "miguel.torres@trackflow.com", "password": "TrackFlow2026!"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_sse_stream_requires_valid_backoffice_jwt(client: TestClient) -> None:
    """SSE endpoint must reject unauthenticated requests or invalid JWTs with 401."""
    unauth_resp = client.get("/api/rfp/stream")
    assert unauth_resp.status_code == 401

    invalid_resp = client.get(
        "/api/rfp/stream",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert invalid_resp.status_code == 401


def test_sse_stream_headers_event_name_and_payload_structure_on_ticket_creation(
    client: TestClient,
    backoffice_jwt: str,
) -> None:
    """Validate `Content-Type: text/event-stream`, `event: rfp_ticket_created`, and JSON payload fields per company-BRIEFING.md."""
    # Register a new RFP ticket for ModaViva (Spain, EUR, warehouse + reverse)
    create_resp = client.post(
        "/api/rfp/tickets",
        json={
            "client_name": "ModaViva",
            "client_country": "Spain",
            "currency": "EUR",
            "services_requested": ["warehousing", "reverse_logistics"],
            "monthly_volume": 12000,
            "deadline": "2026-11-15",
            "budget_range": "45,000 - 60,000 EUR/mes",
            "departments_needed": ["warehouse", "reverse"],
            "original_filename": "trackflow-request-1.pdf",
        },
        headers={"Authorization": f"Bearer {backoffice_jwt}"},
    )
    assert create_resp.status_code == 201
    created_ticket = create_resp.json()

    # Consume SSE stream with valid Backoffice JWT
    with client.stream(
        "GET",
        "/api/rfp/stream",
        headers={"Authorization": f"Bearer {backoffice_jwt}"},
    ) as sse_resp:
        assert sse_resp.status_code == 200
        content_type = sse_resp.headers.get("content-type", "")
        assert content_type.startswith("text/event-stream")
        assert "no-cache" in sse_resp.headers.get("cache-control", "")

        raw_body = "".join(sse_resp.iter_text())

    # Verify explicit event line and keep-alive comment frame
    assert ": keep-alive" in raw_body
    assert f"event: {RFP_TICKET_CREATED_EVENT}" in raw_body

    frames = _parse_sse_frames(raw_body)
    event_frames = [f for f in frames if f["type"] == "event"]
    assert len(event_frames) >= 1

    target_frame = next(
        (f for f in event_frames if f["data"]["ticket_id"] == created_ticket["ticket_id"]),
        event_frames[-1],
    )
    assert target_frame["event"] == "rfp_ticket_created"
    assert target_frame["id"] is not None

    data = target_frame["data"]
    assert isinstance(data, dict)

    # Validate Ticket fields defined in company-BRIEFING.md §2.3
    for required_ticket_field in (
        "ticket_id",
        "rfp_id",
        "status",
        "raw_pdf_path",
        "created_at",
        "updated_at",
    ):
        assert required_ticket_field in data, f"Missing required Ticket field: {required_ticket_field}"
        assert data[required_ticket_field] is not None

    assert data["ticket_id"] == created_ticket["ticket_id"]
    assert data["rfp_id"].startswith("RFP-")
    assert data["status"] in VALID_TICKET_STATUSES
    assert data["raw_pdf_path"].endswith(".pdf")

    # Validate RFP metadata fields defined in company-BRIEFING.md §2.1 & §2.3
    for required_meta_field in (
        "client_name",
        "client_country",
        "currency",
        "services_requested",
        "monthly_volume",
        "deadline",
        "budget_range",
        "departments_needed",
    ):
        assert required_meta_field in data, f"Missing required metadata field: {required_meta_field}"
        assert required_meta_field in data["metadata"]

    assert data["client_name"] == "ModaViva"
    assert data["client_country"] == "Spain"
    assert data["currency"] == "EUR"
    assert data["monthly_volume"] == 12000
    assert set(data["departments_needed"]).issubset(OFFICIAL_DEPARTMENTS)
    assert data["departments_needed"] == ["warehouse", "reverse"]


def test_sse_stream_emits_event_on_pdf_upload_and_supports_last_event_id_recovery(
    client: TestClient,
    backoffice_jwt: str,
) -> None:
    """Uploading an RFP PDF via POST /api/rfp/upload emits `rfp_ticket_created` and `Last-Event-ID` recovers only missed events."""
    pdf_1 = PROJECT_ROOT / "rfp-requests" / "trackflow" / "trackflow-request-1.pdf"
    pdf_2 = PROJECT_ROOT / "rfp-requests" / "trackflow" / "trackflow-request-2.pdf"

    saved_files: list[Path] = []
    try:
        with pdf_1.open("rb") as f1:
            up1 = client.post(
                "/api/rfp/upload",
                files={"file": ("trackflow-request-1.pdf", f1, "application/pdf")},
            )
        assert up1.status_code == 202
        t1_id = up1.json()["ticket_id"]
        saved_files.append(PROJECT_ROOT / "data" / "raw" / f"{t1_id}.pdf")

        with pdf_2.open("rb") as f2:
            up2 = client.post(
                "/api/rfp/upload",
                files={"file": ("trackflow-request-2.pdf", f2, "application/pdf")},
            )
        assert up2.status_code == 202
        t2_id = up2.json()["ticket_id"]
        saved_files.append(PROJECT_ROOT / "data" / "raw" / f"{t2_id}.pdf")

        # Reconnect providing Last-Event-ID of ticket 1 -> should only receive ticket 2
        sse_resp = client.get(
            "/api/rfp/stream",
            headers={
                "Authorization": f"Bearer {backoffice_jwt}",
                "Last-Event-ID": f"evt-{t1_id}",
            },
        )
        assert sse_resp.status_code == 200
        assert sse_resp.headers["content-type"].startswith("text/event-stream")

        frames = _parse_sse_frames(sse_resp.text)
        event_frames = [f for f in frames if f["type"] == "event"]
        returned_ticket_ids = [f["data"]["ticket_id"] for f in event_frames]

        assert t1_id not in returned_ticket_ids
        assert t2_id in returned_ticket_ids

        t2_frame = next(f for f in event_frames if f["data"]["ticket_id"] == t2_id)
        assert t2_frame["event"] == "rfp_ticket_created"
        assert t2_frame["data"]["client_name"] == "Luna Cosmetics"
        assert t2_frame["data"]["client_country"] == "USA"
        assert t2_frame["data"]["currency"] == "USD"
        assert set(t2_frame["data"]["departments_needed"]) == {"warehouse", "lastmile"}
    finally:
        for fpath in saved_files:
            fpath.unlink(missing_ok=True)
