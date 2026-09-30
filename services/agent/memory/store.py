"""Persistent memory store for TrackFlow support agent.

Isolated from corporate RAG vector collections (strictly separate from Qdrant trackflow_knowledge).
Provides an explicit typed read/write interface with SQLite persistence and atomic audit logging.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.agent.memory.models import (
    ConsolidationReport,
    MemoryAuditRecord,
    MemoryCategory,
    MemoryProposal,
    MemoryRecord,
    MemoryStatus,
    ProposalIntent,
)

logger = logging.getLogger("trackflow.agent.memory.store")

DEFAULT_STORAGE_DIR = Path("data/agent_memory")
DEFAULT_DB_FILENAME = "agent_memory.db"
DEFAULT_SNAPSHOT_FILENAME = "memory_store.json"
DEFAULT_AUDIT_FILENAME = "audit_log.json"


class AgentMemoryStore:
    """Persistent storage engine for TrackFlow agent memory, proposals, and audit logs.

    Architectural Invariant:
    This store operates entirely independently of corporate RAG vector databases.
    Under no circumstances does this class write to or modify Qdrant collection 'trackflow_knowledge'.
    """

    def __init__(self, storage_dir: Optional[Path] = None, in_memory: bool = False):
        self.in_memory = in_memory
        if self.in_memory:
            self.storage_dir = Path(":memory:")
            self.db_path = ":memory:"
        else:
            self.storage_dir = storage_dir or DEFAULT_STORAGE_DIR
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(self.storage_dir / DEFAULT_DB_FILENAME)

        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a connection with row factory enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self) -> None:
        """Initialize tables for active memory, pending proposals, and audit trail."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Active and historical memory records
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    entity_key TEXT NOT NULL,
                    content TEXT NOT NULL,
                    carrier TEXT,
                    country TEXT,
                    client_id TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT,
                    authorized_by TEXT NOT NULL,
                    proposal_id TEXT NOT NULL,
                    metadata_json TEXT
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_entity ON memories(entity_key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_status ON memories(status)")

            # 2. Ephemeral pending proposals (strictly 1 active per thread)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_proposals (
                    thread_id TEXT PRIMARY KEY,
                    proposal_id TEXT NOT NULL,
                    trigger_message TEXT NOT NULL,
                    category TEXT NOT NULL,
                    entity_key TEXT NOT NULL,
                    carrier TEXT,
                    country TEXT,
                    client_id TEXT,
                    summary TEXT NOT NULL,
                    proposed_content TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    prompt_question TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )

            # 3. Immutable audit log for all proposals and user decisions
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_audit (
                    audit_id TEXT PRIMARY KEY,
                    proposal_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    trigger_message TEXT NOT NULL,
                    proposed_content TEXT NOT NULL,
                    category TEXT NOT NULL,
                    user_decision_message TEXT,
                    decision_intent TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    authorized_by TEXT,
                    notes TEXT
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_thread ON memory_audit(thread_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_proposal ON memory_audit(proposal_id)")
            conn.commit()

    # -------------------------------------------------------------------------
    # Pending Proposal Management (Strictly 1 at a time per thread)
    # -------------------------------------------------------------------------

    def get_pending_proposal(self, thread_id: str) -> Optional[MemoryProposal]:
        """Fetch the current pending proposal for a given conversation thread, if any."""
        if not thread_id:
            return None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM pending_proposals WHERE thread_id = ? AND status = 'pending'",
                (thread_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return MemoryProposal(
                proposal_id=row["proposal_id"],
                thread_id=row["thread_id"],
                trigger_message=row["trigger_message"],
                category=MemoryCategory(row["category"]),
                entity_key=row["entity_key"],
                carrier=row["carrier"],
                country=row["country"],
                client_id=row["client_id"],
                summary=row["summary"],
                proposed_content=row["proposed_content"],
                reason=row["reason"],
                prompt_question=row["prompt_question"],
                created_at=row["created_at"],
                status=row["status"],
            )

    def set_pending_proposal(self, thread_id: str, proposal: MemoryProposal) -> bool:
        """Register a new pending proposal for a thread.

        Enforces constraint: Only one pending proposal is allowed at a time per thread.
        If an unresolved proposal already exists, returns False without overwriting.
        """
        if not thread_id:
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT proposal_id FROM pending_proposals WHERE thread_id = ? AND status = 'pending'",
                (thread_id,),
            )
            existing = cursor.fetchone()
            if existing:
                logger.warning(
                    f"Thread {thread_id} already has pending proposal {existing['proposal_id']}. Skipping new proposal."
                )
                return False

            cursor.execute(
                """
                INSERT OR REPLACE INTO pending_proposals (
                    thread_id, proposal_id, trigger_message, category, entity_key,
                    carrier, country, client_id, summary, proposed_content, reason,
                    prompt_question, created_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    thread_id,
                    proposal.proposal_id,
                    proposal.trigger_message,
                    proposal.category.value,
                    proposal.entity_key,
                    proposal.carrier,
                    proposal.country,
                    proposal.client_id,
                    proposal.summary,
                    proposal.proposed_content,
                    proposal.reason,
                    proposal.prompt_question,
                    proposal.created_at,
                    "pending",
                ),
            )
            conn.commit()
            return True

    def clear_pending_proposal(self, thread_id: str) -> None:
        """Clear/remove the pending proposal for a thread once resolved or discarded."""
        if not thread_id:
            return
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pending_proposals WHERE thread_id = ?", (thread_id,))
            conn.commit()

    # -------------------------------------------------------------------------
    # Read/Write Interface for Approved Memories
    # -------------------------------------------------------------------------

    def save_approved_memory(
        self,
        proposal: MemoryProposal,
        authorized_by: str,
        modified_content: Optional[str] = None,
        expires_at: Optional[str] = None,
    ) -> MemoryRecord:
        """Persist an explicitly approved memory proposal into the persistent store.

        If a memory with the same entity_key exists, updates and supersedes it to maintain
        a consolidated rule set rather than creating unbounded duplicate fragments.
        """
        now = datetime.now(timezone.utc).isoformat()
        content_to_save = modified_content or proposal.proposed_content

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Check if an active record already exists for this entity_key
            cursor.execute(
                "SELECT memory_id, created_at FROM memories WHERE entity_key = ? AND status = 'active'",
                (proposal.entity_key,),
            )
            existing = cursor.fetchone()

            if existing:
                memory_id = existing["memory_id"]
                created_at = existing["created_at"]
                cursor.execute(
                    """
                    UPDATE memories SET
                        content = ?,
                        updated_at = ?,
                        expires_at = ?,
                        authorized_by = ?,
                        proposal_id = ?,
                        carrier = ?,
                        country = ?,
                        client_id = ?,
                        category = ?
                    WHERE memory_id = ?
                    """,
                    (
                        content_to_save,
                        now,
                        expires_at,
                        authorized_by,
                        proposal.proposal_id,
                        proposal.carrier,
                        proposal.country,
                        proposal.client_id,
                        proposal.category.value,
                        memory_id,
                    ),
                )
            else:
                memory_id = f"mem_{uuid.uuid4().hex[:12]}"
                created_at = now
                cursor.execute(
                    """
                    INSERT INTO memories (
                        memory_id, category, entity_key, content, carrier,
                        country, client_id, status, created_at, updated_at,
                        expires_at, authorized_by, proposal_id, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        memory_id,
                        proposal.category.value,
                        proposal.entity_key,
                        content_to_save,
                        proposal.carrier,
                        proposal.country,
                        proposal.client_id,
                        MemoryStatus.ACTIVE.value,
                        created_at,
                        now,
                        expires_at,
                        authorized_by,
                        proposal.proposal_id,
                        json.dumps({"summary": proposal.summary}),
                    ),
                )

            conn.commit()

        self._export_snapshots()

        return MemoryRecord(
            memory_id=memory_id,
            category=proposal.category,
            entity_key=proposal.entity_key,
            content=content_to_save,
            carrier=proposal.carrier,
            country=proposal.country,
            client_id=proposal.client_id,
            status=MemoryStatus.ACTIVE,
            created_at=created_at,
            updated_at=now,
            expires_at=expires_at,
            authorized_by=authorized_by,
            proposal_id=proposal.proposal_id,
            metadata={"summary": proposal.summary},
        )

    def read_memories(
        self,
        category: Optional[MemoryCategory] = None,
        carrier: Optional[str] = None,
        country: Optional[str] = None,
        client_id: Optional[str] = None,
        query: Optional[str] = None,
        include_expired: bool = False,
    ) -> List[MemoryRecord]:
        """Query active memories using explicit business filters.

        Ensures expired TTL records are excluded by default.
        """
        now = datetime.now(timezone.utc).isoformat()
        conditions = ["status = 'active'"]
        params: List[Any] = []

        if not include_expired:
            conditions.append("(expires_at IS NULL OR expires_at > ?)")
            params.append(now)

        if category:
            cat_val = category.value if isinstance(category, MemoryCategory) else str(category)
            conditions.append("category = ?")
            params.append(cat_val)

        if carrier:
            conditions.append("LOWER(carrier) = ?")
            params.append(carrier.lower())

        if country:
            conditions.append("LOWER(country) = ?")
            params.append(country.lower())

        if client_id:
            conditions.append("LOWER(client_id) = ?")
            params.append(client_id.lower())

        where_clause = " AND ".join(conditions)
        sql = f"SELECT * FROM memories WHERE {where_clause} ORDER BY updated_at DESC"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        results: List[MemoryRecord] = []
        for r in rows:
            meta = {}
            if r["metadata_json"]:
                try:
                    meta = json.loads(r["metadata_json"])
                except Exception:
                    pass

            rec = MemoryRecord(
                memory_id=r["memory_id"],
                category=MemoryCategory(r["category"]),
                entity_key=r["entity_key"],
                content=r["content"],
                carrier=r["carrier"],
                country=r["country"],
                client_id=r["client_id"],
                status=MemoryStatus(r["status"]),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                expires_at=r["expires_at"],
                authorized_by=r["authorized_by"],
                proposal_id=r["proposal_id"],
                metadata=meta,
            )

            # Optional query keyword filter in content/entity_key
            if query:
                q_terms = [t for t in query.lower().split() if len(t) > 2]
                text_to_search = f"{rec.content} {rec.entity_key} {rec.carrier or ''}".lower()
                if not any(t in text_to_search for t in q_terms):
                    continue

            results.append(rec)

        return results

    # -------------------------------------------------------------------------
    # Immutable Audit Logging
    # -------------------------------------------------------------------------

    def record_audit(self, audit_entry: MemoryAuditRecord) -> None:
        """Insert an auditable record of a proposed memory and its outcome."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO memory_audit (
                    audit_id, proposal_id, thread_id, timestamp, trigger_message,
                    proposed_content, category, user_decision_message,
                    decision_intent, outcome, authorized_by, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_entry.audit_id,
                    audit_entry.proposal_id,
                    audit_entry.thread_id,
                    audit_entry.timestamp,
                    audit_entry.trigger_message,
                    audit_entry.proposed_content,
                    audit_entry.category,
                    audit_entry.user_decision_message,
                    audit_entry.decision_intent.value
                    if isinstance(audit_entry.decision_intent, ProposalIntent)
                    else str(audit_entry.decision_intent),
                    audit_entry.outcome,
                    audit_entry.authorized_by,
                    audit_entry.notes,
                ),
            )
            conn.commit()

        self._export_snapshots()

    def get_audit_log(
        self, thread_id: Optional[str] = None, limit: int = 100
    ) -> List[MemoryAuditRecord]:
        """Fetch audit history for inspection and evaluation."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if thread_id:
                cursor.execute(
                    "SELECT * FROM memory_audit WHERE thread_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (thread_id, limit),
                )
            else:
                cursor.execute(
                    "SELECT * FROM memory_audit ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                )
            rows = cursor.fetchall()

        records = []
        for r in rows:
            records.append(
                MemoryAuditRecord(
                    audit_id=r["audit_id"],
                    proposal_id=r["proposal_id"],
                    thread_id=r["thread_id"],
                    timestamp=r["timestamp"],
                    trigger_message=r["trigger_message"],
                    proposed_content=r["proposed_content"],
                    category=r["category"],
                    user_decision_message=r["user_decision_message"],
                    decision_intent=ProposalIntent(r["decision_intent"]),
                    outcome=r["outcome"],
                    authorized_by=r["authorized_by"],
                    notes=r["notes"],
                )
            )
        return records

    # -------------------------------------------------------------------------
    # Consolidation and Cleanup Engine
    # -------------------------------------------------------------------------

    def consolidate(self) -> ConsolidationReport:
        """Run consolidation and expiration cleanup.

        1. Marks records past TTL expires_at as 'expired'.
        2. Aggregates carrier rules by (carrier, country) keeping the most recent consolidated entry.
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Active before
            cursor.execute("SELECT COUNT(*) as cnt FROM memories WHERE status = 'active'")
            active_before = cursor.fetchone()["cnt"]

            # 1. Clean expired records
            cursor.execute(
                """
                UPDATE memories SET status = 'expired'
                WHERE status = 'active' AND expires_at IS NOT NULL AND expires_at <= ?
                """,
                (now,),
            )
            expired_count = cursor.rowcount

            # 2. Consolidate carrier rules by carrier+country
            cursor.execute(
                """
                SELECT carrier, country, COUNT(*) as cnt
                FROM memories
                WHERE status = 'active' AND category = 'carrier_rule' AND carrier IS NOT NULL
                GROUP BY carrier, country
                HAVING cnt > 1
                """
            )
            duplicates = cursor.fetchall()
            merged_count = 0
            consolidated_keys = []

            for d in duplicates:
                carrier = d["carrier"]
                country = d["country"]
                cursor.execute(
                    """
                    SELECT memory_id, content, updated_at FROM memories
                    WHERE status = 'active' AND category = 'carrier_rule'
                      AND carrier = ? AND country = ?
                    ORDER BY updated_at DESC
                    """,
                    (carrier, country),
                )
                carrier_records = cursor.fetchall()
                if len(carrier_records) > 1:
                    primary_id = carrier_records[0]["memory_id"]
                    # Mark older duplicates as superseded
                    for older in carrier_records[1:]:
                        cursor.execute(
                            "UPDATE memories SET status = 'superseded' WHERE memory_id = ?",
                            (older["memory_id"],),
                        )
                        merged_count += 1
                    consolidated_keys.append(f"carrier:{carrier.lower()}:{country.lower()}")

            cursor.execute("SELECT COUNT(*) as cnt FROM memories WHERE status = 'active'")
            active_after = cursor.fetchone()["cnt"]
            conn.commit()

        self._export_snapshots()

        return ConsolidationReport(
            timestamp=now,
            active_before=active_before,
            active_after=active_after,
            expired_count=expired_count,
            merged_count=merged_count,
            consolidated_keys=consolidated_keys,
        )

    # -------------------------------------------------------------------------
    # Human-Readable Snapshots and Utility Helpers
    # -------------------------------------------------------------------------

    def _export_snapshots(self) -> None:
        """Export JSON snapshots for easy inspection, audit review, and repo tracking."""
        if self.in_memory:
            return
        try:
            active_memories = [m.model_dump() for m in self.read_memories(include_expired=True)]
            snapshot_path = self.storage_dir / DEFAULT_SNAPSHOT_FILENAME
            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(active_memories, f, indent=2, ensure_ascii=False)

            audit_entries = [a.model_dump() for a in self.get_audit_log(limit=500)]
            audit_path = self.storage_dir / DEFAULT_AUDIT_FILENAME
            with open(audit_path, "w", encoding="utf-8") as f:
                json.dump(audit_entries, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.debug(f"Failed exporting JSON snapshot: {exc}")

    def clear_all(self) -> None:
        """Utility method to clear all tables (used primarily in test teardowns)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories")
            cursor.execute("DELETE FROM pending_proposals")
            cursor.execute("DELETE FROM memory_audit")
            conn.commit()
        self._export_snapshots()


# Singleton instance
memory_store = AgentMemoryStore()
