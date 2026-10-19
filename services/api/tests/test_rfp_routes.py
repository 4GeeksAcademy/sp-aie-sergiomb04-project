"""API integration tests for /api/rfp/upload and /api/rfp/{ticket_id} endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from scripts.generate_sample_rfps import generate_all_seed_pdfs

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_post_rfp_upload_returns_202_and_processes_formal_rfp(
    monkeypatch_env: None,
    client: TestClient,
) -> None:
    """POST /api/rfp/upload saves PDF to data/raw/<ticket_id>.pdf, returns 202, and GET /api/rfp/{ticket_id} returns analisis_completo."""
    generate_all_seed_pdfs()
    pdf_path = PROJECT_ROOT / "rfp-requests" / "trackflow" / "trackflow-request-1.pdf"

    with pdf_path.open("rb") as f:
        resp = client.post(
            "/api/rfp/upload",
            files={"file": ("trackflow-request-1.pdf", f, "application/pdf")},
        )

    assert resp.status_code == 202
    payload = resp.json()
    assert payload["status"] == "analizando"
    ticket_id = payload["ticket_id"]
    saved_pdf = PROJECT_ROOT / "data" / "raw" / f"{ticket_id}.pdf"
    assert saved_pdf.exists()

    try:
        # BackgroundTasks in Starlette TestClient execute right after response is produced
        detail_resp = client.get(f"/api/rfp/{ticket_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["ticket_id"] == ticket_id
        assert detail["status"] == "analisis_completo"
        assert detail["metadata"]["client_name"] == "ModaViva"
        assert detail["metadata"]["currency"] == "EUR"
        assert detail["metadata"]["departments_needed"] == ["warehouse", "reverse"]
        assert detail["handoff_payload"]["ready_for_part_2"] is True
    finally:
        saved_pdf.unlink(missing_ok=True)


def test_post_rfp_upload_invalid_document_transitions_to_descartado(
    monkeypatch_env: None,
    client: TestClient,
) -> None:
    """Uploading the invalid carrier pitch PDF transitions the ticket to 'descartado'."""
    generate_all_seed_pdfs()
    pdf_path = PROJECT_ROOT / "rfp-requests" / "trackflow" / "trackflow-request-3.pdf"

    with pdf_path.open("rb") as f:
        resp = client.post(
            "/api/rfp/upload",
            files={"file": ("trackflow-request-3.pdf", f, "application/pdf")},
        )

    assert resp.status_code == 202
    ticket_id = resp.json()["ticket_id"]
    saved_pdf = PROJECT_ROOT / "data" / "raw" / f"{ticket_id}.pdf"

    try:
        detail_resp = client.get(f"/api/rfp/{ticket_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["status"] == "descartado"
        assert detail["rejection_reason"] is not None
        assert detail["department_sections"] == []
    finally:
        saved_pdf.unlink(missing_ok=True)
