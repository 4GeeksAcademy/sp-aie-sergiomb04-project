"""TrackFlow Agent Memory package.

Provides persistent memory, self-evaluation, proposal workflows, user confirmation classifiers,
auditable logging, and consolidation isolated from enterprise RAG collections.
"""

from __future__ import annotations

from services.agent.memory.classifier import (
    IntentClassificationResult,
    ProposalIntentClassifier,
    intent_classifier,
)
from services.agent.memory.consolidator import (
    MemoryConsolidator,
    memory_consolidator,
)
from services.agent.memory.evaluator import (
    MemoryEvaluationResult,
    MemoryEvaluator,
    memory_evaluator,
)
from services.agent.memory.models import (
    ConsolidationReport,
    MemoryAuditRecord,
    MemoryCategory,
    MemoryProposal,
    MemoryRecord,
    MemoryStatus,
    ProposalIntent,
)
from services.agent.memory.store import (
    AgentMemoryStore,
    memory_store,
)

__all__ = [
    "AgentMemoryStore",
    "memory_store",
    "MemoryCategory",
    "MemoryStatus",
    "ProposalIntent",
    "MemoryProposal",
    "MemoryRecord",
    "MemoryAuditRecord",
    "ConsolidationReport",
    "MemoryEvaluator",
    "memory_evaluator",
    "MemoryEvaluationResult",
    "ProposalIntentClassifier",
    "intent_classifier",
    "IntentClassificationResult",
    "MemoryConsolidator",
    "memory_consolidator",
]
