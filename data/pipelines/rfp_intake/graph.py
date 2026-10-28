"""LangGraph Orchestrator-Worker-Synthesizer pipeline for TrackFlow RFP Intake & Routing."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send

from data.pipelines.rfp_intake.nodes import (
    classifier_node,
    department_worker_node,
    ingest_document_node,
    orchestrator_node,
    route_after_classifier,
    synthesizer_node,
)
from data.pipelines.rfp_intake.persistence import (
    create_rfp_ticket,
    get_rfp_ticket_bundle,
    mark_ticket_discarded,
)
from data.pipelines.rfp_intake.state import DepartmentWorkerInput, RFPIntakeState
from trackflow_api.models import RFPTicketStatusEnum

logger = logging.getLogger("trackflow.rfp_intake.graph")

_compiled_rfp_graph: CompiledStateGraph | None = None


def dispatch_department_workers(state: RFPIntakeState) -> list[Send] | str:
    """Fan-out edge from Orchestrator to active Department Workers in parallel using LangGraph Send."""
    departments_needed = state.get("departments_needed") or []
    if not departments_needed:
        return "synthesizer"

    ticket_id = state.get("ticket_id", "")
    metadata = state.get("metadata") or {}
    slices = state.get("department_slices") or {}

    shared_metadata = {
        "client_name": metadata.get("client_name"),
        "client_country": metadata.get("client_country"),
        "currency": metadata.get("currency"),
        "services_requested": metadata.get("services_requested"),
        "monthly_volume": metadata.get("monthly_volume"),
        "deadline": metadata.get("deadline"),
        "budget_range": metadata.get("budget_range"),
        "departments_needed": departments_needed,
    }

    sends: list[Send] = []
    for dept_id in departments_needed:
        worker_input: DepartmentWorkerInput = {
            "ticket_id": ticket_id,
            "department_id": dept_id,
            "shared_metadata": shared_metadata,
            "relevant_excerpt": slices.get(dept_id, ""),
        }
        sends.append(Send("department_worker", worker_input))
    return sends


def build_rfp_intake_graph() -> StateGraph:
    """Build the dedicated LangGraph StateGraph for RFP Intake & Routing (isolated from CX agent)."""
    workflow = StateGraph(RFPIntakeState)

    # Step 0: Conversion & Ingestion
    workflow.add_node("ingest_document", ingest_document_node)
    # Node 1: Classifier (Triage Agent)
    workflow.add_node("classifier", classifier_node)
    # Node 2: Orchestrator (Decomposition)
    workflow.add_node("orchestrator", orchestrator_node)
    # Nodes 3..N: Parallel Department Workers
    workflow.add_node("department_worker", department_worker_node)
    # Node 4: Synthesizer Agent
    workflow.add_node("synthesizer", synthesizer_node)

    # Edges
    workflow.add_edge(START, "ingest_document")
    workflow.add_edge("ingest_document", "classifier")

    workflow.add_conditional_edges(
        "classifier",
        route_after_classifier,
        {
            "orchestrator": "orchestrator",
            "end_discarded": END,
        },
    )

    workflow.add_conditional_edges(
        "orchestrator",
        dispatch_department_workers,
        ["department_worker", "synthesizer"],
    )

    workflow.add_edge("department_worker", "synthesizer")
    workflow.add_edge("synthesizer", END)

    return workflow


def compile_rfp_intake_graph() -> CompiledStateGraph:
    """Compile the RFP Intake StateGraph."""
    global _compiled_rfp_graph
    if _compiled_rfp_graph is None:
        workflow = build_rfp_intake_graph()
        _compiled_rfp_graph = workflow.compile()
    return _compiled_rfp_graph


def run_rfp_intake_pipeline(
    *,
    ticket_id: str | None = None,
    pdf_path: str | Path | None = None,
    raw_markdown: str | None = None,
    original_filename: str | None = None,
    preextracted_metadata: dict[str, Any] | None = None,
    preextracted_readability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute the end-to-end RFP Intake & Routing pipeline and persist state in PostgreSQL/SQLModel."""
    tid = ticket_id or str(uuid4())
    pdf_str = str(pdf_path) if pdf_path else f"data/raw/{tid}.pdf"

    ticket = create_rfp_ticket(
        ticket_id=tid,
        pdf_path=pdf_str,
        original_filename=original_filename,
        allow_existing=True,
    )

    app = compile_rfp_intake_graph()
    initial_state: RFPIntakeState = {
        "ticket_id": ticket.id,
        "rfp_id": ticket.rfp_id,
        "pdf_path": pdf_str,
        "raw_markdown": raw_markdown or "",
        "readability_metrics": dict(preextracted_readability or {}),
        "metadata": dict(preextracted_metadata or {}),
        "is_valid_rfp": False,
        "classification": {},
        "rejection_reason": None,
        "departments_needed": [],
        "department_slices": {},
        "worker_outputs": {},
        "executive_summary": "",
        "handoff_payload": {},
        "status": RFPTicketStatusEnum.ANALIZANDO.value,
        "nodes_executed": [],
        "error": None,
    }

    try:
        final_state = app.invoke(initial_state)
    except Exception as exc:
        logger.error("Mid-pipeline failure for ticket_id=%s: %s", ticket.id, exc, exc_info=True)
        mark_ticket_discarded(ticket.id, f"Pipeline error: {exc}")
        raise

    bundle = get_rfp_ticket_bundle(ticket.id)
    if bundle is not None:
        bundle["nodes_executed"] = final_state.get("nodes_executed", [])
        bundle["classification"] = final_state.get("classification", {})
        return bundle

    return dict(final_state)
