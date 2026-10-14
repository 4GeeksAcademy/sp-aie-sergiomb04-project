"""TrackFlow LangGraph Support Agent package with Guardrails Harness and Persistent Memory."""

from __future__ import annotations

from services.agent.graph import (
    build_agent_graph,
    compile_agent_graph,
    get_compiled_agent,
    run_support_agent,
)
from services.agent.guardrails import (
    FailureType,
    GuardrailAction,
    GuardrailResult,
    guardrail_metrics,
)
from services.agent.memory import (
    AgentMemoryStore,
    MemoryAuditRecord,
    MemoryCategory,
    MemoryConsolidator,
    MemoryEvaluator,
    MemoryProposal,
    MemoryRecord,
    MemoryStatus,
    ProposalIntent,
    ProposalIntentClassifier,
    intent_classifier,
    memory_consolidator,
    memory_evaluator,
    memory_store,
)
from services.agent.state import AgentState, AgentStepTrace
from services.agent.tracing import AgentRunTrace, TraceStore, trace_store

__all__ = [
    "AgentState",
    "AgentStepTrace",
    "AgentRunTrace",
    "TraceStore",
    "trace_store",
    "build_agent_graph",
    "compile_agent_graph",
    "get_compiled_agent",
    "run_support_agent",
    "AgentMemoryStore",
    "memory_store",
    "MemoryCategory",
    "MemoryStatus",
    "ProposalIntent",
    "MemoryProposal",
    "MemoryRecord",
    "MemoryAuditRecord",
    "MemoryEvaluator",
    "memory_evaluator",
    "ProposalIntentClassifier",
    "intent_classifier",
    "MemoryConsolidator",
    "memory_consolidator",
    "FailureType",
    "GuardrailAction",
    "GuardrailResult",
    "guardrail_metrics",
]
