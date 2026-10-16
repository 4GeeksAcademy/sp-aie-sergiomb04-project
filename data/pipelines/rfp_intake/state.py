"""State definitions and typed contracts for the TrackFlow RFP Intake & Routing LangGraph pipeline."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict
from pydantic import BaseModel, Field


def merge_worker_outputs(
    left: dict[str, dict[str, Any]] | None,
    right: dict[str, dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    """Reducer that merges parallel department worker outputs into a single dict keyed by department_id."""
    merged: dict[str, dict[str, Any]] = {}
    if left:
        merged.update(left)
    if right:
        merged.update(right)
    return merged


def merge_trace_steps(
    left: list[str] | None,
    right: list[str] | None,
) -> list[str]:
    """Reducer that appends executed node names in order."""
    combined: list[str] = list(left) if left else []
    if right:
        for item in right:
            combined.append(item)
    return combined


class ClassificationResult(BaseModel):
    """Structured output of the Triage / Classifier Agent (Node 1)."""

    is_valid_rfp: bool = Field(
        ...,
        description="True if the document is a legitimate client RFP (formal or informal) for TrackFlow logistics.",
    )
    document_type: str = Field(
        ...,
        description="Classified type: 'formal_rfp', 'informal_rfp', 'carrier_pitch', 'unrelated', or 'empty'.",
    )
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    reason: str = Field(..., description="Explanation of why the document was accepted or rejected.")


class WorkerKeyAspects(BaseModel):
    """Structured analysis produced by an isolated Department Worker (Nodes 3..N)."""

    department_id: str = Field(..., description="Official department ID: warehouse, lastmile, or reverse.")
    department_name: str = Field(..., description="Official department name.")
    contact_person: str = Field(..., description="Department head: Ana Whitfield, Carlos Vega, or Sofía Ramos.")
    summary: str = Field(..., description="Concise summary of what this department must quote/deliver.")
    scope_items: list[str] = Field(default_factory=list, description="Specific operational scope items extracted.")
    constraints: list[str] = Field(default_factory=list, description="Business and operational constraints.")
    resources_required: list[str] = Field(default_factory=list, description="Facilities, carriers, or capabilities needed.")
    extracted_metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Explicit metrics found in the slice (never hallucinated; None if absent).",
    )
    open_questions: list[str] = Field(
        default_factory=list,
        description="Questions for Sales to clarify when volume, pallets, SKUs, or specs are missing.",
    )
    what_to_contribute: str = Field(
        ...,
        description="Official deliverable required from this department per CONTEXT-trackflow.es.md §2.1.",
    )
    relevant_excerpt: str = Field(
        default="",
        description="The segmented text slice analyzed by this worker.",
    )


class DepartmentWorkerInput(TypedDict):
    """Payload dispatched via LangGraph Send() to a single parallel department worker."""

    ticket_id: str
    department_id: str
    shared_metadata: dict[str, Any]
    relevant_excerpt: str


class RFPIntakeState(TypedDict, total=False):
    """State dictionary for the TrackFlow RFP Intake & Routing LangGraph workflow."""

    ticket_id: str
    rfp_id: str
    pdf_path: str
    raw_markdown: str
    readability_metrics: dict[str, Any]
    metadata: dict[str, Any]
    is_valid_rfp: bool
    classification: dict[str, Any]
    rejection_reason: str | None
    departments_needed: list[str]
    department_slices: dict[str, str]
    worker_outputs: Annotated[dict[str, dict[str, Any]], merge_worker_outputs]
    executive_summary: str
    handoff_payload: dict[str, Any]
    status: str
    nodes_executed: Annotated[list[str], merge_trace_steps]
    error: str | None
