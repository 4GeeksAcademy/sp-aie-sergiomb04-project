"""Unit and integration tests for Milestone 9 - Part 2 (RFP Response Generation & Evaluation)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch
import pytest

from data.pipelines.rfp_intake.evaluation_models import EvaluationResult
from data.pipelines.rfp_intake.evaluators import (
    evaluate_compliance,
    evaluate_readability,
    evaluate_relevance,
    run_parallel_evaluation,
)
from data.pipelines.rfp_intake.generators import (
    LastMileProposalGenerator,
    ReverseLogisticsProposalGenerator,
    WarehouseProposalGenerator,
    generate_department_draft,
    get_generator_for_department,
)
from data.pipelines.rfp_intake.persistence import (
    create_rfp_ticket,
    get_rfp_ticket_bundle,
    mark_ticket_analysis_complete,
    update_department_section_draft,
    update_rfp_ticket_status,
    upsert_department_section,
    upsert_rfp_metadata,
)
from data.pipelines.rfp_intake.response_flow import (
    run_rfp_response_generation_async,
)
from trackflow_api.models import RFPTicketStatusEnum


@pytest.fixture(autouse=True)
def isolated_rfp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Use an isolated SQLite/SQLModel database per test while testing the full ORM layer."""
    db_file = tmp_path / "rfp_generation_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Generator Agent Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_warehouse_generator_produces_department_section():
    """Verify that WarehouseProposalGenerator produces a valid proposal section for Ana Whitfield."""
    generator = WarehouseProposalGenerator()
    shared_metadata = {
        "client_name": "ModaViva",
        "client_country": "Spain",
        "currency": "EUR",
        "monthly_volume": 6000,
    }
    key_aspects = {
        "summary": "Almacenamiento de moda en palets y picking de unidades.",
        "scope_items": ["Almacenamiento pallet", "Pick & pack"],
    }

    draft = generator.generate(
        key_aspects=key_aspects,
        shared_metadata=shared_metadata,
        iteration=1,
    )

    assert "Warehouse Operations" in draft
    assert "Ana Whitfield" in draft
    assert "ModaViva" in draft
    assert "EUR" in draft or "€" in draft
    assert "onboarding" in draft.lower()
    assert "|" in draft  # Markdown table present
    assert "98.5%" in draft  # SLA percentage present


def test_lastmile_generator_respects_no_internal_rates():
    """Verify LastMileProposalGenerator includes SLA %, volume discounts, and does NOT leak internal carrier rates."""
    generator = LastMileProposalGenerator()
    shared_metadata = {
        "client_name": "Luna Cosmetics",
        "client_country": "USA",
        "currency": "USD",
        "monthly_volume": 5000,
    }
    key_aspects = {
        "summary": "Distribución capilar multicarrier en Los Ángeles y costa oeste.",
        "scope_items": ["Envío estándar", "Envío express"],
    }

    draft = generator.generate(
        key_aspects=key_aspects,
        shared_metadata=shared_metadata,
        iteration=1,
    )

    assert "Carlos Vega" in draft
    assert "USD" in draft or "$" in draft
    assert "99.0%" in draft
    assert "tarifa negociada" not in draft.lower()
    assert "coste de compra" not in draft.lower()
    assert "|" in draft  # volume discount table


def test_reverse_generator_enforces_no_returns_under_48h():
    """Verify ReverseLogisticsProposalGenerator sets turnaround time >= 48 hours."""
    generator = ReverseLogisticsProposalGenerator()
    shared_metadata = {
        "client_name": "ModaViva",
        "client_country": "Spain",
        "currency": "EUR",
    }
    key_aspects = {
        "summary": "Procesamiento de prendas devueltas e inspección de calidad.",
        "scope_items": ["Inspección", "Devoluciones"],
    }

    draft = generator.generate(
        key_aspects=key_aspects,
        shared_metadata=shared_metadata,
        iteration=1,
    )

    assert "Sofía Ramos" in draft
    assert "48" in draft
    # Must not offer under 48h
    assert "24 horas" not in draft.lower()
    assert "mismo día" not in draft.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 2. Parallel Evaluators Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_run_parallel_evaluation_success():
    """Verify that running all three evaluators in parallel on a compliant draft returns overall_pass=True."""
    generator = WarehouseProposalGenerator()
    shared_metadata = {
        "client_name": "ModaViva",
        "client_country": "Spain",
        "currency": "EUR",
        "monthly_volume": 5000,
    }
    key_aspects = {
        "summary": "Almacenamiento pallet y preparación de pedidos.",
        "scope_items": ["Almacenamiento", "Picking"],
    }
    draft = generator.generate(
        key_aspects=key_aspects,
        shared_metadata=shared_metadata,
    )

    eval_result = asyncio.run(
        run_parallel_evaluation(
            draft=draft,
            department_id="warehouse",
            key_aspects=key_aspects,
            client_country="Spain",
        )
    )

    assert isinstance(eval_result, EvaluationResult)
    assert eval_result.overall_pass is True
    assert eval_result.readability.pass_ is True
    assert eval_result.relevance.pass_ is True
    assert eval_result.compliance.pass_ is True
    assert len(eval_result.compliance.violations) == 0


def test_evaluate_readability_failure_on_short_text():
    """Verify that evaluate_readability fails when text is too short or malformed."""
    short_text = "Propuesta de almacén rápida."
    eval_res = evaluate_readability(short_text)
    assert eval_res.pass_ is False
    assert "insuficiente" in str(eval_res.details)


def test_evaluate_relevance_failure_on_missing_department_scope():
    """Verify that evaluate_relevance flags missing department core concepts."""
    unrelated_text = (
        "TrackFlow ofrece consultoría de marketing digital y diseño de packaging creativo para marcas de e-commerce. "
        "Nuestros consultores analizarán la identidad de marca durante dos semanas consecutivas."
    )
    eval_res = evaluate_relevance(
        draft=unrelated_text,
        department_id="warehouse",
        key_aspects={"scope_items": ["Almacenamiento de pallets", "Pick & pack"]},
    )
    assert eval_res.pass_ is False
    assert len(eval_res.missing_aspects) > 0


# ─────────────────────────────────────────────────────────────────────────────
# 3. Compliance Rule Failures Anchored to Briefing §5
# ─────────────────────────────────────────────────────────────────────────────

def test_compliance_failure_returns_under_48h():
    """Rule 3 violation (§5): Promise processing returns in 24 hours -> compliance.pass == False."""
    bad_draft = """### Propuesta Reverse Logistics
Sofía Ramos ofrece procesamiento exprés de devoluciones.
Garantizamos la inspección completa y turnaround de devoluciones en 24 horas desde la recepción.
SLA de entrega a tiempo del 99%.
Cotización en 4.50 € por unidad.

| Devoluciones | Descuento | Tarifa EUR |
| :--- | :--- | :--- |
| 1 - 500 | 0% | 4.50 € |
| > 500 | 10% | 4.05 € |
"""
    eval_res = evaluate_compliance(
        draft=bad_draft,
        department_id="reverse",
        client_country="Spain",
    )
    assert eval_res.pass_ is False
    assert any("no_returns_under_48h" in v for v in eval_res.violations)


def test_compliance_failure_currency_mismatch():
    """Rule 1 violation (§5): Client in Spain quoted in USD ($) instead of EUR (€)."""
    bad_draft = """### Propuesta Warehouse Operations
Ana Whitfield cotiza almacenamiento en Los Ángeles para cliente en España.
Coste por pallet mensual: $15.00 USD.
Tiempo de onboarding: 10 días hábiles.
SLA de entrega a tiempo del 98.5%.

| Volumen | Descuento | Precio USD |
| :--- | :--- | :--- |
| 1 - 1000 | 0% | $15.00 |
| > 1000 | 10% | $13.50 |
"""
    eval_res = evaluate_compliance(
        draft=bad_draft,
        department_id="warehouse",
        client_country="Spain",
    )
    assert eval_res.pass_ is False
    assert any("currency_match" in v for v in eval_res.violations)


def test_compliance_failure_missing_volume_discount_table():
    """Rule 4 violation (§5): Proposal lacks a volume discount table."""
    bad_draft = """### Propuesta Last Mile
Carlos Vega detalla la red de distribución para cliente en España.
Tarifa plana de 5.20 EUR por paquete entregado a domicilio.
SLA de entrega a tiempo comprometido del 99.0%.
No ofrecemos descuentos adicionales por volumen en esta fase inicial.
"""
    eval_res = evaluate_compliance(
        draft=bad_draft,
        department_id="lastmile",
        client_country="Spain",
    )
    assert eval_res.pass_ is False
    assert any("volume_discount_table" in v for v in eval_res.violations)


def test_compliance_failure_leaking_carrier_negotiated_rates():
    """Rule 5 violation (§5): Disclosing internal carrier negotiated rates."""
    bad_draft = """### Propuesta Last Mile
Carlos Vega presenta la tarifa al cliente en España (EUR).
Nuestra tarifa negociada con SEUR es de 2.80 EUR, y añadimos un margen de transporte de 1.50 EUR.
SLA de entrega a tiempo del 98.0%.

| Volumen | Descuento | Tarifa EUR |
| :--- | :--- | :--- |
| 1 - 1000 | 0% | 4.30 € |
| > 1000 | 5% | 4.08 € |
"""
    eval_res = evaluate_compliance(
        draft=bad_draft,
        department_id="lastmile",
        client_country="Spain",
    )
    assert eval_res.pass_ is False
    assert any("no_carrier_negotiated_rates" in v for v in eval_res.violations)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Generator-Evaluator Loop & Iteration Limit (needs_human_review)
# ─────────────────────────────────────────────────────────────────────────────

def test_generator_evaluator_loop_exhausts_iterations_to_needs_human_review():
    """When a generator continuously fails evaluation, after max_iterations it marks section and ticket as needs_human_review and NEVER discards the ticket."""
    ticket = create_rfp_ticket(pdf_path="data/raw/test_loop.pdf")
    upsert_rfp_metadata(
        ticket_id=ticket.id,
        raw_markdown="# RFP Test",
        metadata={
            "client_name": "Test Brand",
            "client_country": "Spain",
            "currency": "EUR",
            "departments_needed": ["warehouse"],
        },
        readability_metrics={},
    )
    upsert_department_section(
        ticket_id=ticket.id,
        department_id="warehouse",
        key_aspects={"summary": "Aspectos de warehouse", "scope_items": ["Almacenamiento"]},
    )
    mark_ticket_analysis_complete(
        ticket_id=ticket.id,
        executive_summary="Resumen inicial",
        handoff_payload={"ready_for_part_2": True},
    )

    # Mock generator to return an invalid draft that always violates compliance (currency USD in Spain)
    invalid_draft = "Short bad draft $10 USD without SLA and without table."
    with patch("data.pipelines.rfp_intake.response_flow.generate_department_draft", return_value=invalid_draft):
        res = asyncio.run(
            run_rfp_response_generation_async(
                ticket_id=ticket.id,
                max_iterations=2,
            )
        )

    assert res["status"] == RFPTicketStatusEnum.NEEDS_HUMAN_REVIEW.value
    bundle = get_rfp_ticket_bundle(ticket.id)
    assert bundle is not None
    # Verify ticket is NOT discarded
    assert bundle["status"] == RFPTicketStatusEnum.NEEDS_HUMAN_REVIEW.value
    assert bundle["rejection_reason"] is None
    # Verify section draft and evaluation results are retained
    sections = bundle["department_sections"]
    assert len(sections) == 1
    assert sections[0]["draft_content"] == invalid_draft
    assert sections[0]["approval_status"] == "needs_human_review"
    assert sections[0]["evaluation_results"]["overall_pass"] is False


def test_generator_evaluator_loop_success():
    """Verify that standard generation across active departments succeeds and persists drafts in PostgreSQL."""
    ticket = create_rfp_ticket(pdf_path="data/raw/test_success.pdf")
    upsert_rfp_metadata(
        ticket_id=ticket.id,
        raw_markdown="# RFP Luna Cosmetics",
        metadata={
            "client_name": "Luna Cosmetics",
            "client_country": "USA",
            "currency": "USD",
            "departments_needed": ["warehouse", "lastmile"],
        },
        readability_metrics={},
    )
    upsert_department_section(
        ticket_id=ticket.id,
        department_id="warehouse",
        key_aspects={"summary": "Almacén en LA", "scope_items": ["Almacenamiento", "Picking"]},
    )
    upsert_department_section(
        ticket_id=ticket.id,
        department_id="lastmile",
        key_aspects={"summary": "Última milla multicarrier", "scope_items": ["Envíos"]},
    )
    mark_ticket_analysis_complete(
        ticket_id=ticket.id,
        executive_summary="Resumen para Ventas",
        handoff_payload={"ready_for_part_2": True},
    )

    res = asyncio.run(
        run_rfp_response_generation_async(
            ticket_id=ticket.id,
            max_iterations=3,
        )
    )

    assert res["status"] == RFPTicketStatusEnum.EN_EVALUACION.value
    bundle = get_rfp_ticket_bundle(ticket.id)
    assert bundle is not None
    assert bundle["status"] == RFPTicketStatusEnum.EN_EVALUACION.value

    sections = bundle["department_sections"]
    assert len(sections) == 2
    for sec in sections:
        assert sec["draft_content"] is not None
        assert len(sec["draft_content"]) > 100
        assert sec["evaluation_results"] is not None
        assert sec["evaluation_results"]["overall_pass"] is True
        assert sec["approval_status"] == "evaluated_pass"
