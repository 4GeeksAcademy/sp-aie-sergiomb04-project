"""Consolidation and cleanup engine for TrackFlow agent memory.

Consolidates carrier rules by (carrier, country) to prevent fragmentation across 8 carriers
operating in Spain and USA, and applies a strict 7-day TTL policy to transient incident contexts.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from services.agent.memory.models import ConsolidationReport, MemoryCategory, MemoryProposal
from services.agent.memory.store import AgentMemoryStore, memory_store

logger = logging.getLogger("trackflow.agent.memory.consolidator")

# Default TTL for transient incident contexts (e.g. port strikes, weather delays)
DEFAULT_INCIDENT_TTL_DAYS = 7


class MemoryConsolidator:
    """Manages memory lifecycle, carrier rule consolidation, deduplication, and TTL expiration."""

    def __init__(self, store: Optional[AgentMemoryStore] = None):
        self.store = store or memory_store

    def calculate_expiration(self, proposal: MemoryProposal) -> Optional[str]:
        """Determine expiration timestamp based on memory category policy.

        - incident_context: 7-day TTL (transient operational disruption).
        - carrier_rule: Persistent until superseded by operations.
        - b2b_preference: Persistent until superseded by client account changes.
        """
        if proposal.category == MemoryCategory.INCIDENT_CONTEXT:
            expires_dt = datetime.now(timezone.utc) + timedelta(days=DEFAULT_INCIDENT_TTL_DAYS)
            return expires_dt.isoformat()
        return None

    def run_consolidation(self) -> ConsolidationReport:
        """Execute scheduled or on-demand consolidation and cleanup.

        1. Identifies and marks expired transient incident memories as 'expired'.
        2. Aggregates carrier assignment rules by (carrier, country) so that rules remain unified.
        3. Returns an auditable ConsolidationReport.
        """
        logger.info("Executing TrackFlow agent memory consolidation and cleanup...")
        report = self.store.consolidate()
        logger.info(
            f"Consolidation completed: active_before={report.active_before}, "
            f"active_after={report.active_after}, expired={report.expired_count}, merged={report.merged_count}"
        )
        return report


# Singleton consolidator
memory_consolidator = MemoryConsolidator()
