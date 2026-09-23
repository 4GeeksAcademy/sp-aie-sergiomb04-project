"""Minimal and explicit state definition for the TrackFlow support agent."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class AgentStepTrace(TypedDict, total=False):
    """Execution trace entry for a single node."""

    node: str
    timestamp: str
    duration_ms: float
    output_summary: Dict[str, Any]


class AgentState(TypedDict, total=False):
    """Explicit minimal state flowing between agent graph nodes.

    Contains only what each node needs to decide the next step, avoiding
    unnecessary conversation history bloat.
    """

    question: str
    is_valid: bool
    context: List[Dict[str, Any]]
    answer: str
    error: Optional[str]
    trace: List[Dict[str, Any]]
    # Routing and tool metadata
    source_route: Optional[str]
    tool_used: Optional[str]
    tool_result: Optional[Dict[str, Any]]
    # Optional runtime parameters
    k: Optional[int]
    min_score: Optional[float]
    collection_name: Optional[str]
