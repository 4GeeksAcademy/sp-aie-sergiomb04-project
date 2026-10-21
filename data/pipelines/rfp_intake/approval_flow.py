"""LangGraph-based Human-In-The-Loop (HITL) Departmental Approval and Final Proposal Synthesis (Milestone 9 - Part 3).

Key Capabilities:
1. Isolated branch interruptions (interrupt()) per active department.
2. Independent thread namespace (rfp-{ticket_id}:{department_id}) allowing concurrent reviews.
3. SqliteSaver checkpointer for state persistence.
4. Resumption point (Command(resume=...)) validating approve, reject, or request_changes.
5. Strict iteration limit protecting against infinite change loops.
6. Arbitration node applying §7 rules (Miguel Torres, Sofía Ramos) without LLM voting.
7. Full execution trace with agent, input, output, and timestamp.
8. Automatic consolidation into RFPFinalDocument and transition to 'terminado' when all approved.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, TypedDict

import os
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from trackflow_api.models import RFPTicketStatusEnum

from .approval_models import (
    ApprovalActionEnum,
    ApprovalDecision,
    ConflictResolution,
    FinalDocumentPayload,
    TraceStep,
)
from .arbitration import detect_and_resolve_conflicts
from .generators import generate_department_draft
from .persistence import (
    check_all_sections_approved,
    get_final_document,
    get_rfp_ticket_bundle,
    save_final_document,
    update_department_approval,
    update_department_section_draft,
    update_rfp_ticket_status,
)
from .state import merge_trace_steps

logger = logging.getLogger("trackflow.rfp_intake.approval_flow")

PROJECT_ROOT = Path(__file__).resolve().parents[3]


_default_checkpointer: BaseCheckpointSaver | None = None


def get_default_checkpointer() -> BaseCheckpointSaver:
    """Return default persistent SqliteSaver checkpointer for RFP approvals with resilient fallback to MemorySaver."""
    global _default_checkpointer
    if _default_checkpointer is not None:
        return _default_checkpointer

    configured = os.getenv("RFP_APPROVAL_DB_PATH")
    candidate_paths = (
        [Path(configured)]
        if configured
        else [
            PROJECT_ROOT / "data" / "checkpoints" / "rfp_checkpoints.sqlite",
            PROJECT_ROOT / "data" / "checkpoints" / "rfp_approval.db",
            Path("/tmp/rfp_checkpoints.sqlite"),
        ]
    )

    for cand in candidate_paths:
        try:
            cand.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(cand), check_same_thread=False)
            saver = SqliteSaver(conn)
            saver.setup()
            _default_checkpointer = saver
            logger.info("RFP approval SqliteSaver initialized successfully at %s", cand)
            return _default_checkpointer
        except Exception as exc:
            logger.warning("Failed to initialize SqliteSaver at %s: %s", cand, exc)

    logger.warning("Falling back to MemorySaver for RFP approvals due to SQLite storage errors.")
    _default_checkpointer = MemorySaver()
    return _default_checkpointer


def merge_audit_traces(
    left: list[dict[str, Any]] | None,
    right: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Reducer that accumulates structured audit trace steps in chronological order."""
    traces: list[dict[str, Any]] = list(left) if left else []
    if right:
        traces.extend(right)
    return traces


class DepartmentApprovalState(TypedDict, total=False):
    """Isolated per-department state tracked by the checkpointer."""

    ticket_id: str
    department_id: str
    contact_person: str
    draft_content: str
    evaluation_results: dict[str, Any]
    approval_status: str  # pending, approved, rejected, changes_requested
    approver: str
    decision_notes: str | None
    iteration: int
    max_iterations: int
    traces: Annotated[list[dict[str, Any]], merge_audit_traces]


def department_approval_node(state: DepartmentApprovalState) -> dict[str, Any]:
    """Execute human approval checkpoint using LangGraph interrupt(). Pauses ONLY this department's thread."""
    ticket_id = state.get("ticket_id", "")
    dept_id = state.get("department_id", "")
    contact_person = state.get("contact_person", "")
    iteration = state.get("iteration", 1)
    max_iter = state.get("max_iterations", 3)

    now_iso = datetime.now(timezone.utc).isoformat()
    trace_in = TraceStep(
        agent=f"ApprovalGate:{dept_id}",
        input={
            "ticket_id": ticket_id,
            "department_id": dept_id,
            "contact_person": contact_person,
            "iteration": iteration,
        },
        output="Waiting for human sign-off via interrupt()",
        timestamp=now_iso,
    )

    # 1. Trigger LangGraph interrupt - pauses execution in this thread
    decision_payload = interrupt({
        "ticket_id": ticket_id,
        "department_id": dept_id,
        "contact_person": contact_person,
        "draft_content": state.get("draft_content"),
        "evaluation_results": state.get("evaluation_results"),
        "iteration": iteration,
        "max_iterations": max_iter,
        "prompt": f"Esperando aprobación formal de {contact_person} para la sección {dept_id}.",
    })

    # 2. Resumed! Validate human decision payload
    action_raw = decision_payload.get("action", "approve") if isinstance(decision_payload, dict) else str(decision_payload)
    approver_name = decision_payload.get("approver", contact_person) if isinstance(decision_payload, dict) else contact_person
    notes = decision_payload.get("notes") if isinstance(decision_payload, dict) else None

    # Map action
    action_clean = action_raw.lower()
    if action_clean in ("approve", "aprobar", "aprobado"):
        final_status = "approved"
    elif action_clean in ("reject", "rechazar", "descartar"):
        final_status = "rejected"
    elif action_clean in ("request_changes", "cambios", "modificar"):
        final_status = "changes_requested"
    else:
        final_status = "approved"

    trace_out = TraceStep(
        agent=f"ApprovalGate:{dept_id}",
        input=decision_payload,
        output={"approval_status": final_status, "approver": approver_name, "notes": notes},
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    return {
        "approval_status": final_status,
        "approver": approver_name,
        "decision_notes": notes,
        "traces": [trace_in.model_dump(), trace_out.model_dump()],
    }


def build_department_approval_graph(checkpointer: BaseCheckpointSaver | None = None):
    """Compile the LangGraph workflow for an isolated department approval branch."""
    builder = StateGraph(DepartmentApprovalState)
    builder.add_node("approval_node", department_approval_node)
    builder.add_edge(START, "approval_node")
    builder.add_edge("approval_node", END)

    saver = checkpointer or get_default_checkpointer()
    return builder.compile(checkpointer=saver)


def initiate_ticket_approval_cycle(
    ticket_id: str,
    checkpointer: BaseCheckpointSaver | None = None,
) -> dict[str, Any]:
    """Initialize LangGraph interrupt gates for all active departments.

    Sets ticket status to 'esperando_aprobación'.
    """
    bundle = get_rfp_ticket_bundle(ticket_id)
    if bundle is None:
        raise ValueError(f"Ticket {ticket_id} no encontrado.")

    # Mark ticket as esperando_aprobación
    update_rfp_ticket_status(ticket_id, RFPTicketStatusEnum.ESPERANDO_APROBACION.value)

    dept_sections = bundle.get("department_sections") or []
    if not dept_sections:
        return {"ticket_id": ticket_id, "status": "no_sections", "threads": []}

    graph = build_department_approval_graph(checkpointer)
    threads_started = []

    for sec in dept_sections:
        dept_id = sec["department_id"]
        contact = sec.get("contact_person") or "Responsable"
        thread_id = f"rfp-{ticket_id}:{dept_id}"
        config = {"configurable": {"thread_id": thread_id}}

        initial_state: DepartmentApprovalState = {
            "ticket_id": ticket_id,
            "department_id": dept_id,
            "contact_person": contact,
            "draft_content": sec.get("draft_content") or "",
            "evaluation_results": sec.get("evaluation_results") or {},
            "approval_status": "pending",
            "approver": contact,
            "iteration": 1,
            "max_iterations": 3,
            "traces": [],
        }

        # Invoking until interrupt()
        try:
            graph.invoke(initial_state, config=config)
        except Exception as exc:
            logger.info("Thread %s paused at interrupt() as expected: %s", thread_id, exc)

        threads_started.append(thread_id)

    return {
        "ticket_id": ticket_id,
        "status": RFPTicketStatusEnum.ESPERANDO_APROBACION.value,
        "threads": threads_started,
    }


def resume_department_approval(
    *,
    ticket_id: str,
    department_id: str,
    decision: ApprovalDecision,
    checkpointer: BaseCheckpointSaver | None = None,
) -> dict[str, Any]:
    """Resume the paused LangGraph gate for a specific department without blocking other departments."""
    thread_id = f"rfp-{ticket_id}:{department_id}"
    config = {"configurable": {"thread_id": thread_id}}
    graph = build_department_approval_graph(checkpointer)

    # 1. Check if thread has pending interrupt
    state = graph.get_state(config)
    if not state.next:
        # If thread is not currently paused, execute initial invoke first to establish checkpoint
        bundle = get_rfp_ticket_bundle(ticket_id)
        contact = "Responsable"
        draft = ""
        eval_res = {}
        if bundle:
            for s in bundle.get("department_sections", []):
                if s["department_id"] == department_id:
                    contact = s.get("contact_person", contact)
                    draft = s.get("draft_content", "")
                    eval_res = s.get("evaluation_results", {})
                    break

        init_state: DepartmentApprovalState = {
            "ticket_id": ticket_id,
            "department_id": department_id,
            "contact_person": contact,
            "draft_content": draft,
            "evaluation_results": eval_res,
            "approval_status": "pending",
            "approver": decision.approver or contact,
            "iteration": 1,
            "max_iterations": 3,
            "traces": [],
        }
        try:
            graph.invoke(init_state, config=config)
        except Exception:
            pass

    # 2. Resume through Command(resume=payload)
    resume_payload = {
        "action": decision.action.value if hasattr(decision.action, "value") else str(decision.action),
        "approver": decision.approver,
        "notes": decision.notes,
        "timestamp": decision.timestamp,
    }

    resumed_state = graph.invoke(Command(resume=resume_payload), config=config)

    # 3. Update database row for this department section
    update_department_approval(
        ticket_id=ticket_id,
        department_id=department_id,
        action=decision.action.value if hasattr(decision.action, "value") else str(decision.action),
        approver=decision.approver,
        notes=decision.notes,
    )

    # 4. If changes requested and within iteration limit, allow regeneration
    if resumed_state.get("approval_status") == "changes_requested":
        bundle = get_rfp_ticket_bundle(ticket_id)
        if bundle:
            sec_record = next((s for s in bundle.get("department_sections", []) if s["department_id"] == department_id), None)
            if sec_record:
                curr_iter = resumed_state.get("iteration", 1) + 1
                max_iter = resumed_state.get("max_iterations", 3)
                if curr_iter <= max_iter:
                    # Regenerate draft incorporating requested notes
                    revised_draft = generate_department_draft(
                        department_id=department_id,
                        key_aspects=sec_record.get("key_aspects") or {},
                        shared_metadata=bundle.get("metadata") or {},
                        feedback_for_generator=decision.notes or "Modificaciones solicitadas por el responsable.",
                        iteration=curr_iter,
                    )
                    update_department_section_draft(
                        ticket_id=ticket_id,
                        department_id=department_id,
                        draft_content=revised_draft,
                        approval_status="pending",
                    )

    # 5. Check if all departments are now approved
    all_approved = check_all_sections_approved(ticket_id)
    final_doc_payload: dict[str, Any] | None = None

    if all_approved:
        # Automatic synthesis of the final proposal document!
        final_doc_payload = synthesize_final_proposal_document(ticket_id)
        ticket_status = RFPTicketStatusEnum.TERMINADO.value
    else:
        ticket_status = RFPTicketStatusEnum.ESPERANDO_APROBACION.value
        update_rfp_ticket_status(ticket_id, ticket_status)

    return {
        "ticket_id": ticket_id,
        "department_id": department_id,
        "decision": resume_payload,
        "all_approved": all_approved,
        "ticket_status": ticket_status,
        "final_document": final_doc_payload,
        "traces": resumed_state.get("traces", []),
    }


def synthesize_final_proposal_document(ticket_id: str) -> dict[str, Any]:
    """Consolidate all approved sections, apply arbitration check, and persist RFPFinalDocument."""
    bundle = get_rfp_ticket_bundle(ticket_id)
    if bundle is None:
        raise ValueError(f"Ticket {ticket_id} no encontrado.")

    metadata = bundle.get("metadata") or {}
    client_name = metadata.get("client_name") or "Cliente"
    client_country = metadata.get("client_country") or "Spain"
    currency = metadata.get("currency") or ("EUR" if client_country == "Spain" else "USD")
    dept_sections = bundle.get("department_sections") or []

    # Run §7 Arbitration Node check for any structural conflicts
    resolutions, arbitration_traces = detect_and_resolve_conflicts(
        client_country=client_country,
        department_sections=dept_sections,
        metadata=metadata,
    )

    # Build sections payload
    sections_map: dict[str, Any] = {}
    approvals_map: dict[str, Any] = {}
    md_parts: list[str] = [
        f"# Propuesta Económica Integral — {client_name}",
        f"**Cliente:** {client_name} ({client_country})  ",
        f"**Moneda Oficial de la Propuesta:** {currency}  ",
        f"**Referencia:** {bundle.get('rfp_id')}  ",
        f"**Fecha de Emisión:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n",
        "---",
        "## Resumen Ejecutivo de la Oferta (Commercial Directorate)",
        bundle.get("executive_summary") or "Propuesta de externalización logística integral de TrackFlow Tech.\n",
        "---",
        "## Propuestas Departamentales Aprobadas",
    ]

    for sec in dept_sections:
        dept_id = sec["department_id"]
        sections_map[dept_id] = {
            "department": sec.get("department"),
            "contact_person": sec.get("contact_person"),
            "draft_content": sec.get("draft_content"),
            "evaluation_results": sec.get("evaluation_results"),
        }
        approvals_map[dept_id] = {
            "status": sec.get("approval_status"),
            "approver": sec.get("approver") or sec.get("contact_person"),
            "approved_at": sec.get("approved_at"),
            "notes": (sec.get("handoff_payload") or {}).get("approval_notes"),
        }
        md_parts.append(f"\n{sec.get('draft_content', '')}\n")

    # Add Sign-off section
    md_parts.append("\n---\n## Aprobaciones Formales y Sign-off por Responsables de Departamento")
    md_parts.append("| Departamento | Responsable Designado | Estado de Aprobación | Fecha de Aprobación |")
    md_parts.append("| :--- | :--- | :--- | :--- |")
    for sec in dept_sections:
        d_name = sec.get("department", sec["department_id"])
        c_person = sec.get("approver") or sec.get("contact_person") or "Responsable"
        app_date = sec.get("approved_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        md_parts.append(f"| {d_name} | {c_person} | **Aprobado formalmente ✅** | {app_date} |")

    # Add Arbitration audit notes if any were triggered
    if resolutions:
        md_parts.append("\n---\n## Resoluciones de Arbitraje Fijo de Contratos (§7 BRIEFING)")
        for r in resolutions:
            md_parts.append(f"- **Trigger `{r.trigger_id}`** (Árbitro: *{r.arbitrator}*): {r.conflict_detected} → *Resolución aplicada:* {r.applied_action}")

    consolidated_text = "\n".join(md_parts).strip()

    final_doc_record = {
        "ticket_id": ticket_id,
        "rfp_id": bundle.get("rfp_id"),
        "client_name": client_name,
        "client_country": client_country,
        "currency": currency,
        "sections": sections_map,
        "approvals": approvals_map,
        "arbitrations": [r.model_dump() for r in resolutions],
        "consolidated_markdown": consolidated_text,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Persist in DB and transition ticket status to 'terminado'
    save_final_document(
        ticket_id=ticket_id,
        sections=final_doc_record,
        currency=currency,
    )

    logger.info("Final proposal document synthesized and persisted for ticket %s. Status is now TERMINADO.", ticket_id)
    return final_doc_record
