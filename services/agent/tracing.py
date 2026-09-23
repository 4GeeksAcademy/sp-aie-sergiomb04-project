"""Structured tracing and inspection manager for TrackFlow LangGraph agent runs."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("trackflow.agent.tracing")


@dataclass
class AgentRunTrace:
    """Complete trace of an agent execution."""

    run_id: str
    thread_id: str
    question: str
    nodes_executed: List[str] = field(default_factory=list)
    steps: List[Dict[str, Any]] = field(default_factory=list)
    answer: str = ""
    error: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    total_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to serializable dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert trace to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class TraceStore:
    """Thread-safe in-memory store for agent traces."""

    def __init__(self) -> None:
        self._traces_by_run_id: Dict[str, AgentRunTrace] = {}
        self._traces_by_thread_id: Dict[str, List[str]] = {}

    def save_trace(self, trace: AgentRunTrace) -> None:
        """Persist a completed run trace in store."""
        self._traces_by_run_id[trace.run_id] = trace
        if trace.thread_id not in self._traces_by_thread_id:
            self._traces_by_thread_id[trace.thread_id] = []
        self._traces_by_thread_id[trace.thread_id].append(trace.run_id)
        logger.info(
            "Saved agent trace run_id=%s thread_id=%s nodes=%s",
            trace.run_id,
            trace.thread_id,
            trace.nodes_executed,
        )

    def get_trace(self, run_id: str) -> Optional[AgentRunTrace]:
        """Retrieve a specific run trace by run_id."""
        return self._traces_by_run_id.get(run_id)

    def get_traces_by_thread(self, thread_id: str) -> List[AgentRunTrace]:
        """Retrieve all run traces for a given thread_id."""
        run_ids = self._traces_by_thread_id.get(thread_id, [])
        return [self._traces_by_run_id[r] for r in run_ids if r in self._traces_by_run_id]

    def list_recent_traces(self, limit: int = 50) -> List[AgentRunTrace]:
        """List recent traces in reverse chronological order."""
        traces = list(self._traces_by_run_id.values())
        return sorted(traces, key=lambda t: t.created_at, reverse=True)[:limit]

    def clear(self) -> None:
        """Clear all stored traces (useful for tests)."""
        self._traces_by_run_id.clear()
        self._traces_by_thread_id.clear()


# Default singleton instance
trace_store = TraceStore()
