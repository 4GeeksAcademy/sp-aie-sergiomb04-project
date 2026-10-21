"""Typed data models and contracts for Milestone 9 - Part 3: Approval, Arbitration, and Final Synthesis."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, Field


class ApprovalActionEnum(StrEnum):
    """Permitted human approval actions."""

    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"


class ApprovalDecision(BaseModel):
    """Structured human input submitted to resume an interrupted approval node."""

    department_id: str = Field(..., description="Target department identifier.")
    action: ApprovalActionEnum = Field(..., description="Decision: approve, reject, or request_changes.")
    approver: str = Field(..., description="Name of the department head or arbitrator.")
    notes: str | None = Field(default=None, description="Optional feedback or required changes.")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO timestamp of when the human decision was registered.",
    )


class TraceStep(BaseModel):
    """Audit trace record for node execution ensuring full traceability."""

    agent: str = Field(..., description="Name or role of the executing agent or node.")
    input: Any = Field(..., description="Input received by the node.")
    output: Any = Field(..., description="Output produced by the node.")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC ISO timestamp of the trace event.",
    )


class ConflictTriggerId(StrEnum):
    """Official conflict trigger IDs defined in trackflow-BRIEFING.es.md §7."""

    VOLUME_VS_CAPACITY = "volume-vs-capacity"
    RETURNS_SLA_BREACH = "returns-sla-breach"
    CURRENCY_MISMATCH = "currency-mismatch"


class ConflictResolution(BaseModel):
    """Structured record of conflict detection and fixed arbitration per §7."""

    trigger_id: str = Field(..., description="Trigger ID: volume-vs-capacity, returns-sla-breach, currency-mismatch.")
    arbitrator: str = Field(..., description="Fixed designated human arbitrator (Miguel Torres, Sofía Ramos).")
    conflict_detected: str = Field(..., description="Explanation of contradiction detected in structured state.")
    resolution_rule: str = Field(..., description="Exact resolution rule applied per §7.")
    applied_action: str = Field(..., description="Concrete outcome or instruction dispatched to affected sections.")
    resolved: bool = Field(default=True, description="Whether conflict was resolved by the rule.")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO timestamp of arbitration resolution.",
    )


class FinalDocumentPayload(BaseModel):
    """Consolidated economic proposal document produced upon full departmental sign-off."""

    ticket_id: str
    rfp_id: str
    client_name: str
    client_country: str
    currency: str
    sections: dict[str, dict[str, Any]]
    approvals: dict[str, dict[str, Any]]
    arbitrations: list[dict[str, Any]] = Field(default_factory=list)
    consolidated_markdown: str
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
