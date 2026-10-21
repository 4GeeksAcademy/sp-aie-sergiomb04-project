"""Unit and integration tests for Milestone 9 - Part 3: HITL Approvals, Arbitration, and Final Synthesis."""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4
import pytest
from langgraph.checkpoint.memory import MemorySaver

from data.pipelines.rfp_intake.approval_models import (
    ApprovalActionEnum,
    ApprovalDecision,
    ConflictTriggerId,
)
from data.pipelines.rfp_intake.approval_flow import (
    build_department_approval_graph,
    initiate_ticket_approval_cycle,
    resume_department_approval,
    synthesize_final_proposal_document,
)
from data.pipelines.rfp_intake.arbitration import detect_and_resolve_conflicts
from data.pipelines.rfp_intake.persistence import (
    create_rfp_ticket,
    get_final_document,
    get_rfp_ticket_bundle,
    mark_ticket_analysis_complete,
    update_department_section_draft,
    update_rfp_ticket_status,
    upsert_department_section,
    upsert_rfp_metadata,
)
from data.pipelines.rfp_intake.response_flow import run_rfp_response_generation_async
from trackflow_api.models import RFPTicketStatusEnum


@pytest.fixture(autouse=True)
def isolated_rfp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Use an isolated SQLite/SQLModel database per test for ORM persistence."""
    db_file = tmp_path / "rfp_approval_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Unit Tests: Interruption & Resumption (LangGraph HITL)
# ─────────────────────────────────────────────────────────────────────────────

def test_department_approval_graph_pauses_at_interrupt():
    """Verify that build_department_approval_graph pauses execution at interrupt() gate."""
    checkpointer = MemorySaver()
    graph = build_department_approval_graph(checkpointer=checkpointer)

    ticket_id = str(uuid4())
    thread_id = f"rfp-{ticket_id}:warehouse"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "ticket_id": ticket_id,
        "department_id": "warehouse",
        "contact_person": "Ana Whitfield",
        "draft_content": "### Propuesta Warehouse\nAlmacén de 5000 pallets.",
        "evaluation_results": {"overall_pass": True},
        "approval_status": "pending",
        "approver": "Ana Whitfield",
        "iteration": 1,
        "max_iterations": 3,
        "traces": [],
    }

    # First invoke enters node and pauses at interrupt()
    graph.invoke(initial_state, config=config)
    state = graph.get_state(config)

    # Next step should be awaiting resumption in 'approval_node'
    assert state.next == ("approval_node",)
    assert len(state.tasks) > 0
    assert len(state.tasks[0].interrupts) > 0


def test_department_approval_resumption_with_approve():
    """Verify that resuming with 'approve' updates state and persists approval in DB."""
    checkpointer = MemorySaver()

    ticket = create_rfp_ticket(pdf_path="data/raw/test_hitl.pdf")
    upsert_department_section(
        ticket_id=ticket.id,
        department_id="warehouse",
        key_aspects={"summary": "Almacén"},
    )
    update_department_section_draft(
        ticket_id=ticket.id,
        department_id="warehouse",
        draft_content="Propuesta aprobable",
        evaluation_results={"overall_pass": True},
    )

    decision = ApprovalDecision(
        department_id="warehouse",
        action=ApprovalActionEnum.APPROVE,
        approver="Ana Whitfield",
        notes="Propuesta revisada y conforme.",
    )

    result = resume_department_approval(
        ticket_id=ticket.id,
        department_id="warehouse",
        decision=decision,
        checkpointer=checkpointer,
    )

    assert result["decision"]["action"] == "approve"
    assert result["decision"]["approver"] == "Ana Whitfield"

    bundle = get_rfp_ticket_bundle(ticket.id)
    assert bundle is not None
    sec = next(s for s in bundle["department_sections"] if s["department_id"] == "warehouse")
    assert sec["approval_status"] == "approved"
    assert sec["approver"] == "Ana Whitfield"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Parallelism & Isolation Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_parallelism_approving_department_b_while_a_remains_interrupted():
    """Verify that Department B (lastmile) can be approved while Department A (warehouse) remains interrupted."""
    checkpointer = MemorySaver()

    ticket = create_rfp_ticket(pdf_path="data/raw/test_parallel.pdf")
    upsert_rfp_metadata(
        ticket_id=ticket.id,
        raw_markdown="# RFP",
        metadata={"client_name": "Luna Cosmetics", "client_country": "USA", "currency": "USD"},
        readability_metrics={},
    )
    upsert_department_section(
        ticket_id=ticket.id,
        department_id="warehouse",
        key_aspects={"summary": "Almacén LA"},
    )
    upsert_department_section(
        ticket_id=ticket.id,
        department_id="lastmile",
        key_aspects={"summary": "Distribución multicarrier"},
    )
    update_department_section_draft(
        ticket_id=ticket.id,
        department_id="warehouse",
        draft_content="Borrador Warehouse",
    )
    update_department_section_draft(
        ticket_id=ticket.id,
        department_id="lastmile",
        draft_content="Borrador Lastmile",
    )

    # Initiate approval cycle for both departments
    initiate_ticket_approval_cycle(ticket.id, checkpointer=checkpointer)

    bundle_init = get_rfp_ticket_bundle(ticket.id)
    assert bundle_init["status"] == RFPTicketStatusEnum.ESPERANDO_APROBACION.value

    # Approve only Department B (lastmile - Carlos Vega)
    decision_b = ApprovalDecision(
        department_id="lastmile",
        action=ApprovalActionEnum.APPROVE,
        approver="Carlos Vega",
        notes="Tarifas de transporte validadas.",
    )
    res_b = resume_department_approval(
        ticket_id=ticket.id,
        department_id="lastmile",
        decision=decision_b,
        checkpointer=checkpointer,
    )

    # Verify Department B is approved
    assert res_b["all_approved"] is False  # Because warehouse is still pending!
    assert res_b["ticket_status"] == RFPTicketStatusEnum.ESPERANDO_APROBACION.value

    bundle_mid = get_rfp_ticket_bundle(ticket.id)
    sec_wh = next(s for s in bundle_mid["department_sections"] if s["department_id"] == "warehouse")
    sec_lm = next(s for s in bundle_mid["department_sections"] if s["department_id"] == "lastmile")

    # Department A is still pending and untouched
    assert sec_wh["approval_status"] in (None, "pending")
    # Department B is approved
    assert sec_lm["approval_status"] == "approved"
    assert sec_lm["approver"] == "Carlos Vega"

    # Now approve Department A (warehouse - Ana Whitfield)
    decision_a = ApprovalDecision(
        department_id="warehouse",
        action=ApprovalActionEnum.APPROVE,
        approver="Ana Whitfield",
    )
    res_a = resume_department_approval(
        ticket_id=ticket.id,
        department_id="warehouse",
        decision=decision_a,
        checkpointer=checkpointer,
    )

    # Now ALL departments are approved -> automatic synthesis to terminado!
    assert res_a["all_approved"] is True
    assert res_a["ticket_status"] == RFPTicketStatusEnum.TERMINADO.value

    bundle_final = get_rfp_ticket_bundle(ticket.id)
    assert bundle_final["status"] == RFPTicketStatusEnum.TERMINADO.value


# ─────────────────────────────────────────────────────────────────────────────
# 3. Unit Tests: Arbitration Node (§7 Conflict Triggers)
# ─────────────────────────────────────────────────────────────────────────────

def test_arbitration_trigger_currency_mismatch():
    """Trigger 'currency-mismatch': Sections quote different currencies -> Arbitrator: Miguel Torres."""
    sections = [
        {"department_id": "warehouse", "draft_content": "Cotización en 15.00 EUR por pallet."},
        {"department_id": "lastmile", "draft_content": "Cotización en $5.50 USD por envío."},
    ]
    resolutions, traces = detect_and_resolve_conflicts(
        client_country="Spain",
        department_sections=sections,
    )

    trigger_ids = [r.trigger_id for r in resolutions]
    assert ConflictTriggerId.CURRENCY_MISMATCH.value in trigger_ids
    r = next(res for res in resolutions if res.trigger_id == ConflictTriggerId.CURRENCY_MISMATCH.value)
    assert "Miguel Torres" in r.arbitrator
    assert "EUR" in r.applied_action
    assert len(traces) > 0
    assert traces[0].agent == "ArbitrationNode:currency-mismatch"


def test_arbitration_trigger_returns_sla_breach():
    """Trigger 'returns-sla-breach': Reverse promises 24 hours turnaround -> Arbitrator: Sofía Ramos."""
    sections = [
        {"department_id": "reverse", "draft_content": "Garantizamos turnaround de devoluciones en 24 horas hábiles."},
    ]
    resolutions, traces = detect_and_resolve_conflicts(
        client_country="Spain",
        department_sections=sections,
    )

    trigger_ids = [r.trigger_id for r in resolutions]
    assert ConflictTriggerId.RETURNS_SLA_BREACH.value in trigger_ids
    r = next(res for res in resolutions if res.trigger_id == ConflictTriggerId.RETURNS_SLA_BREACH.value)
    assert "Sofía Ramos" in r.arbitrator
    assert "request_changes" in r.applied_action


def test_arbitration_trigger_volume_vs_capacity():
    """Trigger 'volume-vs-capacity': Warehouse capacity < Lastmile monthly volume -> Arbitrator: Miguel Torres."""
    sections = [
        {
            "department_id": "warehouse",
            "key_aspects": {"extracted_metrics": {"max_monthly_capacity": 3000}},
            "draft_content": "Capacidad máxima 3,000 unidades.",
        },
        {
            "department_id": "lastmile",
            "key_aspects": {"extracted_metrics": {"monthly_volume": 8000}},
            "draft_content": "Distribución calculada para 8,000 unidades.",
        },
    ]
    resolutions, traces = detect_and_resolve_conflicts(
        client_country="Spain",
        department_sections=sections,
    )

    trigger_ids = [r.trigger_id for r in resolutions]
    assert ConflictTriggerId.VOLUME_VS_CAPACITY.value in trigger_ids
    r = next(res for res in resolutions if res.trigger_id == ConflictTriggerId.VOLUME_VS_CAPACITY.value)
    assert "Miguel Torres" in r.arbitrator
    assert "capacidad de warehouse" in r.resolution_rule


# ─────────────────────────────────────────────────────────────────────────────
# 4. Reproducible End-to-End Integration Test (Part 1 to Part 3)
# ─────────────────────────────────────────────────────────────────────────────

def test_e2e_full_rfp_lifecycle_intake_to_approval_completion():
    """Full reproducible end-to-end flow: Intake -> Generation -> HITL Approval Resumes -> RFPFinalDocument."""
    checkpointer = MemorySaver()

    # Step 1: Ingest RFP Ticket (ModaViva - Spain)
    ticket = create_rfp_ticket(pdf_path="data/raw/modaviva_e2e.pdf", original_filename="modaviva.pdf")
    upsert_rfp_metadata(
        ticket_id=ticket.id,
        raw_markdown="# ModaViva RFP\nAlmacén y devoluciones en España.",
        metadata={
            "client_name": "ModaViva",
            "client_country": "Spain",
            "currency": "EUR",
            "monthly_volume": 12000,
            "departments_needed": ["warehouse", "reverse"],
        },
        readability_metrics={"word_count": 120},
    )
    upsert_department_section(
        ticket_id=ticket.id,
        department_id="warehouse",
        key_aspects={"summary": "Almacén y picking en Zaragoza", "scope_items": ["Almacenamiento pallet", "Picking"]},
    )
    upsert_department_section(
        ticket_id=ticket.id,
        department_id="reverse",
        key_aspects={"summary": "Logística inversa y control de calidad", "scope_items": ["Inspección", "Devoluciones"]},
    )
    mark_ticket_analysis_complete(
        ticket_id=ticket.id,
        executive_summary="Síntesis comercial para ModaViva.",
        handoff_payload={"ready_for_part_2": True},
    )

    bundle_part1 = get_rfp_ticket_bundle(ticket.id)
    assert bundle_part1["status"] == RFPTicketStatusEnum.ANALISIS_COMPLETO.value

    # Step 2: Part 2 Response Generation & Parallel Evaluation
    gen_result = asyncio.run(
        run_rfp_response_generation_async(
            ticket_id=ticket.id,
            max_iterations=3,
        )
    )
    assert gen_result["status"] == RFPTicketStatusEnum.EN_EVALUACION.value
    bundle_part2 = get_rfp_ticket_bundle(ticket.id)
    for sec in bundle_part2["department_sections"]:
        assert sec["draft_content"] is not None
        assert sec["evaluation_results"]["overall_pass"] is True

    # Step 3: Part 3 Initiate Approval Cycle (HITL interrupt gates)
    init_res = initiate_ticket_approval_cycle(ticket.id, checkpointer=checkpointer)
    assert init_res["status"] == RFPTicketStatusEnum.ESPERANDO_APROBACION.value
    assert len(init_res["threads"]) == 2

    # Step 4: Resume Approval for Warehouse (Ana Whitfield)
    res_wh = resume_department_approval(
        ticket_id=ticket.id,
        department_id="warehouse",
        decision=ApprovalDecision(
            department_id="warehouse",
            action=ApprovalActionEnum.APPROVE,
            approver="Ana Whitfield",
            notes="Capacidad confirmada para Zaragoza.",
        ),
        checkpointer=checkpointer,
    )
    assert res_wh["all_approved"] is False

    # Step 5: Resume Approval for Reverse (Sofía Ramos)
    res_rev = resume_department_approval(
        ticket_id=ticket.id,
        department_id="reverse",
        decision=ApprovalDecision(
            department_id="reverse",
            action=ApprovalActionEnum.APPROVE,
            approver="Sofía Ramos",
            notes="Protocolo de inspección 48-72h aprobado.",
        ),
        checkpointer=checkpointer,
    )

    # Step 6: Verify Automatic Final Synthesis and Terminado status
    assert res_rev["all_approved"] is True
    assert res_rev["ticket_status"] == RFPTicketStatusEnum.TERMINADO.value

    bundle_final = get_rfp_ticket_bundle(ticket.id)
    assert bundle_final["status"] == RFPTicketStatusEnum.TERMINADO.value

    final_doc = get_final_document(ticket.id)
    assert final_doc is not None
    assert final_doc["ticket_id"] == ticket.id
    assert final_doc["currency"] == "EUR"
    assert "warehouse" in final_doc["sections"]["sections"]
    assert "reverse" in final_doc["sections"]["sections"]
    assert "Ana Whitfield" in final_doc["sections"]["consolidated_markdown"]
    assert "Sofía Ramos" in final_doc["sections"]["consolidated_markdown"]
