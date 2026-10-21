"""Unit and integration smoke tests for TrackFlow RFP Intake & Routing pipeline (Milestone 9 - Part 1)."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from data.pipelines.rfp_intake import (
    classify_rfp_document,
    compute_readability_metrics,
    decompose_rfp_by_department,
    run_department_worker,
    run_rfp_intake_pipeline,
)
from scripts.generate_sample_rfps import generate_all_seed_pdfs

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def isolated_rfp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Use an isolated SQLite/SQLModel database per test while testing the full ORM layer."""
    db_file = tmp_path / "rfp_intake_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")


# ─── 1. Unit Tests: Classifier (Triage Agent) ──────────────────────────────────

def test_classifier_accepts_formal_and_informal_rfps() -> None:
    """Classifier must accept both formal RFP documents and informal client inquiry emails."""
    formal_text = (
        "SOLICITUD DE PROPUESTA (RFP) — ModaViva S.L. (España). "
        "Buscamos externalizar nuestra operación de almacenamiento (450 pallets, 1.800 SKUs) "
        "y gestión de devoluciones en Zaragoza para 12.000 pedidos/mes."
    )
    res_formal = classify_rfp_document(formal_text)
    assert res_formal.is_valid_rfp is True
    assert res_formal.document_type == "formal_rfp"

    informal_text = (
        "From: ops@lunacosmetics.com\nSubject: Logistics Partnership Inquiry / RFP\n"
        "Hi Miguel, we are Luna Cosmetics in Los Angeles, USA and would like to request a formal proposal "
        "to outsource our warehousing and US last mile delivery for ~5,000 orders/month."
    )
    res_informal = classify_rfp_document(informal_text)
    assert res_informal.is_valid_rfp is True
    assert res_informal.document_type == "informal_rfp"


def test_classifier_rejects_invalid_carrier_pitch_and_empty_docs() -> None:
    """Classifier must reject incoming carrier rate pitches and unrelated/empty documents."""
    pitch_text = (
        "PROPUESTA COMERCIAL DE SERVICIOS DE TRANSPORTE PARA TRACKFLOW TECH. "
        "Asunto: Presentación de Tarifas Mayoristas de Flota FTL/LTL 2026 (Pitch de Proveedor). "
        "Nos ponemos en contacto para que TrackFlow nos contrate como proveedor externo. "
        "NO somos una marca de e-commerce."
    )
    res_pitch = classify_rfp_document(pitch_text)
    assert res_pitch.is_valid_rfp is False
    assert res_pitch.document_type == "carrier_pitch"

    res_empty = classify_rfp_document("   ")
    assert res_empty.is_valid_rfp is False
    assert res_empty.document_type == "empty"


# ─── 2. Unit Tests: Isolated Departmental Workers & Orchestrator ───────────────

def test_isolated_warehouse_worker_extracts_metrics_and_registers_open_questions_when_missing() -> None:
    """Isolated warehouse worker must extract explicit metrics and never hallucinate missing ones."""
    # Case A: Explicit metrics present
    shared_meta_a = {
        "client_name": "ModaViva",
        "client_country": "Spain",
        "currency": "EUR",
        "monthly_volume": 12000,
        "deadline": "2026-11-30",
    }
    excerpt_a = (
        "Capacidad requerida: 450 pallets europeos y aproximadamente 1.800 SKUs activos en Zaragoza. "
        "Preparación de pedidos picking y packing con corte a las 17:00 CET."
    )
    aspects_a = run_department_worker(
        department_id="warehouse",
        shared_metadata=shared_meta_a,
        relevant_excerpt=excerpt_a,
    )
    assert aspects_a.department_id == "warehouse"
    assert aspects_a.contact_person == "Ana Whitfield"
    assert aspects_a.extracted_metrics["pallets_requested"] == 450
    assert aspects_a.extracted_metrics["skus_count"] == 1800
    assert aspects_a.extracted_metrics["monthly_volume_orders"] == 12000
    assert aspects_a.extracted_metrics["currency"] == "EUR"
    assert len(aspects_a.open_questions) == 0

    # Case B: Missing monthly_volume, pallets, and SKUs -> must NOT invent numbers; must record open questions
    shared_meta_b = {
        "client_name": "MysteryBrand",
        "client_country": "USA",
        "currency": "USD",
        "monthly_volume": None,
        "deadline": None,
    }
    excerpt_b = "We need storage and pick/pack fulfillment in your Los Angeles warehouse."
    aspects_b = run_department_worker(
        department_id="warehouse",
        shared_metadata=shared_meta_b,
        relevant_excerpt=excerpt_b,
    )
    assert aspects_b.extracted_metrics["pallets_requested"] is None
    assert aspects_b.extracted_metrics["skus_count"] is None
    assert aspects_b.extracted_metrics["monthly_volume_orders"] is None
    assert len(aspects_b.open_questions) >= 3
    assert any("monthly_volume" in q for q in aspects_b.open_questions)
    assert any("pallets" in q for q in aspects_b.open_questions)


def test_isolated_lastmile_and_reverse_workers_enforce_business_constraints() -> None:
    """Isolated lastmile and reverse workers must include §5 compliance constraints and official owners."""
    lastmile_aspects = run_department_worker(
        department_id="lastmile",
        shared_metadata={
            "client_name": "Luna Cosmetics",
            "client_country": "USA",
            "currency": "USD",
            "monthly_volume": 5000,
            "deadline": "2026-11-15",
        },
        relevant_excerpt="We ship 5,000 B2C parcels per month across California, average weight 0.8 lbs.",
    )
    assert lastmile_aspects.contact_person == "Carlos Vega"
    assert any("SLA" in c for c in lastmile_aspects.constraints)
    assert any("tarifas negociadas" in c for c in lastmile_aspects.constraints)

    reverse_aspects = run_department_worker(
        department_id="reverse",
        shared_metadata={
            "client_name": "ModaViva",
            "client_country": "Spain",
            "currency": "EUR",
            "monthly_volume": 12000,
            "deadline": "2026-11-30",
        },
        relevant_excerpt="Tasa media de devoluciones: 18% (~2.160 devoluciones mensuales en Zaragoza).",
    )
    assert reverse_aspects.contact_person == "Sofía Ramos"
    assert reverse_aspects.extracted_metrics["return_rate_pct"] == 18.0
    assert reverse_aspects.extracted_metrics["estimated_monthly_returns"] == 2160
    assert any("48 horas" in c for c in reverse_aspects.constraints)


def test_orchestrator_decomposition_respects_negated_and_non_existent_departments() -> None:
    """Orchestrator must only activate official BRIEFING departments and ignore non-existent ones."""
    text = (
        "ModaViva (España) solicita almacenamiento en Zaragoza, despacho aduanero (customs brokerage), "
        "campañas de marketing digital y logística inversa de devoluciones. "
        "ModaViva NO solicita servicios de transporte de última milla (transportista propio para última milla)."
    )
    depts, slices = decompose_rfp_by_department(text)
    assert depts == ["warehouse", "reverse"]
    assert "lastmile" not in depts
    assert "customs_brokerage" not in depts
    assert "marketing" not in depts
    assert "warehouse" in slices and "reverse" in slices


# ─── 3. Smoke & Integration Tests with Official TrackFlow Seed PDFs ───────────

def test_smoke_seed_pdf_1_formal_rfp_modaviva_completa_and_handoff() -> None:
    """trackflow-request-1.pdf (ModaViva, Spain) -> analisis_completo, EUR, warehouse + reverse only."""
    generate_all_seed_pdfs()
    src_pdf = PROJECT_ROOT / "rfp-requests" / "trackflow" / "trackflow-request-1.pdf"
    tid = str(uuid4())
    raw_pdf = PROJECT_ROOT / "data" / "raw" / f"{tid}.pdf"
    raw_pdf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src_pdf, raw_pdf)

    try:
        bundle = run_rfp_intake_pipeline(
            ticket_id=tid,
            pdf_path=f"data/raw/{tid}.pdf",
            original_filename=src_pdf.name,
        )

        assert bundle["status"] == "analisis_completo"
        assert bundle["metadata"]["client_name"] == "ModaViva"
        assert bundle["metadata"]["client_country"] == "Spain"
        assert bundle["metadata"]["currency"] == "EUR"
        assert bundle["metadata"]["departments_needed"] == ["warehouse", "reverse"]
        assert "lastmile" not in bundle["metadata"]["departments_needed"]

        # Readability metrics populated
        metrics = bundle["readability_metrics"]
        assert metrics["word_count"] > 100
        assert "flesch_kincaid_grade" in metrics
        assert "gunning_fog" in metrics

        # Department sections persisted
        sec_ids = [s["department_id"] for s in bundle["department_sections"]]
        assert set(sec_ids) == {"warehouse", "reverse"}

        # Handoff contract verified
        handoff = bundle["handoff_payload"]
        assert handoff is not None
        assert handoff["ready_for_part_2"] is True
        assert handoff["ticket_id"] == tid
        assert handoff["currency"] == "EUR"
        assert set(handoff["department_briefs"].keys()) == {"warehouse", "reverse"}
    finally:
        raw_pdf.unlink(missing_ok=True)


def test_smoke_seed_pdf_2_informal_rfp_luna_cosmetics_completa_and_handoff() -> None:
    """trackflow-request-2.pdf (Luna Cosmetics, USA) -> analisis_completo, USD, warehouse + lastmile only."""
    generate_all_seed_pdfs()
    src_pdf = PROJECT_ROOT / "rfp-requests" / "trackflow" / "trackflow-request-2.pdf"
    tid = str(uuid4())
    raw_pdf = PROJECT_ROOT / "data" / "raw" / f"{tid}.pdf"
    raw_pdf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src_pdf, raw_pdf)

    try:
        bundle = run_rfp_intake_pipeline(
            ticket_id=tid,
            pdf_path=f"data/raw/{tid}.pdf",
            original_filename=src_pdf.name,
        )

        assert bundle["status"] == "analisis_completo"
        assert bundle["metadata"]["client_name"] == "Luna Cosmetics"
        assert bundle["metadata"]["client_country"] == "USA"
        assert bundle["metadata"]["currency"] == "USD"
        assert bundle["metadata"]["monthly_volume"] == 5000
        assert bundle["metadata"]["departments_needed"] == ["warehouse", "lastmile"]
        assert "reverse" not in bundle["metadata"]["departments_needed"]

        sec_ids = [s["department_id"] for s in bundle["department_sections"]]
        assert set(sec_ids) == {"warehouse", "lastmile"}

        handoff = bundle["handoff_payload"]
        assert handoff["ready_for_part_2"] is True
        assert handoff["ticket_id"] == tid
        assert handoff["currency"] == "USD"
        assert set(handoff["department_briefs"].keys()) == {"warehouse", "lastmile"}
    finally:
        raw_pdf.unlink(missing_ok=True)


def test_smoke_seed_pdf_3_invalid_carrier_pitch_descartado() -> None:
    """trackflow-request-3.pdf (Carrier rate pitch) -> descartado without running workers."""
    generate_all_seed_pdfs()
    src_pdf = PROJECT_ROOT / "rfp-requests" / "trackflow" / "trackflow-request-3.pdf"
    tid = str(uuid4())
    raw_pdf = PROJECT_ROOT / "data" / "raw" / f"{tid}.pdf"
    raw_pdf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src_pdf, raw_pdf)

    try:
        bundle = run_rfp_intake_pipeline(
            ticket_id=tid,
            pdf_path=f"data/raw/{tid}.pdf",
            original_filename=src_pdf.name,
        )

        assert bundle["status"] == "descartado"
        assert bundle["rejection_reason"] is not None
        assert bundle["department_sections"] == []
        assert bundle["nodes_executed"] == ["ingest_document", "classifier"]
        assert compute_readability_metrics(bundle["raw_markdown"])["word_count"] > 50
    finally:
        raw_pdf.unlink(missing_ok=True)
