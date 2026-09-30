"""Data models for TrackFlow agent memory, proposals, audits, and consolidation."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MemoryCategory(str, Enum):
    """Permitted memory categories for TrackFlow support agent."""

    CARRIER_RULE = "carrier_rule"
    INCIDENT_CONTEXT = "incident_context"
    B2B_PREFERENCE = "b2b_preference"


class MemoryStatus(str, Enum):
    """Lifecycle status for persisted memory records."""

    ACTIVE = "active"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


class ProposalIntent(str, Enum):
    """Classified user intent regarding a pending memory proposal."""

    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"
    AMBIGUOUS_OR_UNRELATED = "ambiguous_or_unrelated"


class MemoryProposal(BaseModel):
    """Structured proposal generated when agent detects memorable operational context."""

    proposal_id: str = Field(..., description="Unique proposal identifier.")
    thread_id: str = Field(..., description="Conversation thread where proposal was made.")
    trigger_message: str = Field(..., description="Original user message that prompted proposal.")
    category: MemoryCategory = Field(..., description="Category of the proposal.")
    entity_key: str = Field(..., description="Consolidation key (e.g. 'carrier:seur:es').")
    carrier: Optional[str] = Field(None, description="Carrier identifier if applicable (e.g. 'SEUR').")
    country: Optional[str] = Field(None, description="Country code ('ES' or 'US') if applicable.")
    client_id: Optional[str] = Field(None, description="B2B client identifier if applicable.")
    summary: str = Field(..., description="Concise statement of the fact to remember.")
    proposed_content: str = Field(..., description="Detailed content of the rule or fact.")
    reason: str = Field(..., description="Justification for why this is worth remembering.")
    prompt_question: str = Field(..., description="User-facing confirmation prompt.")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp.",
    )
    status: str = Field("pending", description="Status: pending, approved, rejected, discarded.")


class MemoryRecord(BaseModel):
    """Consolidated persistent memory record in the TrackFlow memory store."""

    memory_id: str = Field(..., description="Unique memory record ID.")
    category: MemoryCategory = Field(..., description="Category of memory.")
    entity_key: str = Field(..., description="Consolidation key.")
    content: str = Field(..., description="Consolidated memory content.")
    carrier: Optional[str] = Field(None, description="Carrier identifier.")
    country: Optional[str] = Field(None, description="Country code ('ES' or 'US').")
    client_id: Optional[str] = Field(None, description="B2B client identifier.")
    status: MemoryStatus = Field(MemoryStatus.ACTIVE, description="Lifecycle status.")
    created_at: str = Field(..., description="ISO 8601 UTC creation timestamp.")
    updated_at: str = Field(..., description="ISO 8601 UTC last update timestamp.")
    expires_at: Optional[str] = Field(None, description="ISO 8601 UTC expiration timestamp.")
    authorized_by: str = Field(..., description="Identifier of the user who authorized this memory.")
    proposal_id: str = Field(..., description="Reference to the originating proposal.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata.")


class MemoryAuditRecord(BaseModel):
    """Immutable audit entry recording a memory proposal and the resulting decision."""

    audit_id: str = Field(..., description="Unique audit record ID.")
    proposal_id: str = Field(..., description="Proposal ID.")
    thread_id: str = Field(..., description="Conversation thread ID.")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of decision.",
    )
    trigger_message: str = Field(..., description="User message that triggered the proposal.")
    proposed_content: str = Field(..., description="Content that was proposed.")
    category: str = Field(..., description="Category of memory proposed.")
    user_decision_message: Optional[str] = Field(
        None, description="User message responding to the proposal (or None if topic changed)."
    )
    decision_intent: ProposalIntent = Field(
        ..., description="Explicit classified intent (approve, reject, edit, ambiguous_or_unrelated)."
    )
    outcome: str = Field(
        ..., description="Outcome: approved, rejected, discarded_ambiguous, edited_and_approved."
    )
    authorized_by: Optional[str] = Field(None, description="User identifier who authorized if approved.")
    notes: Optional[str] = Field(None, description="Additional context or reason for decision.")


class ConsolidationReport(BaseModel):
    """Summary of memory consolidation and cleanup execution."""

    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of consolidation.",
    )
    active_before: int = Field(0, description="Active records before consolidation.")
    active_after: int = Field(0, description="Active records after consolidation.")
    expired_count: int = Field(0, description="Records marked expired due to TTL.")
    merged_count: int = Field(0, description="Records merged/superseded by carrier+country.")
    consolidated_keys: List[str] = Field(default_factory=list, description="Entity keys affected.")
