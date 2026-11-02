"""Human-in-the-Loop (HITL) gate for irreversible / high-impact actions (NIST Protect & Respond).

Implements section 5 of the TrackFlow security briefing. The following actions can be
*proposed* by an agent or an automated engine, but are only executed after explicit
confirmation by an authenticated human operator different from the requester:

- Aprobar una devolución por encima del umbral monetario definido por el equipo.
- Confirmar el despacho de un envío de alto valor.
- Cambiar el carrier asignado a un envío ya en tránsito.
- Compartir datos de volumen o incidentes de una marca cliente (B2B) con otra.
- Borrado de datos y envíos externos (irreversibles por definición).

Execution is only possible through `HumanApprovalGate.execute()`, which refuses to run
any action whose status is not APPROVED (or AUTO_APPROVED when the policy allows it).
Every transition is written to the structured audit log `trackflow.security.hitl`.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger("trackflow.security.hitl")

# Identities that represent automated actors: they can propose but never approve.
AUTOMATED_ACTOR_PREFIXES = ("agent:", "system:", "engine:", "support-agent", "trackflow-support-agent")


class CriticalActionType(str, Enum):
    """Catalogue of actions with irreversible or high economic/privacy impact."""

    RETURN_APPROVAL = "return_approval"
    HIGH_VALUE_DISPATCH = "high_value_dispatch"
    CARRIER_CHANGE = "carrier_change"
    CROSS_BRAND_DATA_SHARE = "cross_brand_data_share"
    DATA_DELETION = "data_deletion"
    EXTERNAL_SEND = "external_send"


class ActionStatus(str, Enum):
    AUTO_APPROVED = "auto_approved"
    PENDING_HUMAN_APPROVAL = "pending_human_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


class HumanApprovalRequiredError(PermissionError):
    """Raised when trying to execute an action that has not been approved by a human."""


class ApprovalPermissionError(PermissionError):
    """Raised when the approver is not allowed to decide on the action."""


class ActionRecord(BaseModel):
    """Persistent record of a critical action request and its decision trail."""

    action_id: str
    action_type: CriticalActionType
    payload: Dict[str, Any]
    requested_by: str
    reason: str = ""
    requires_human: bool
    policy_reason: str
    status: ActionStatus
    created_at: str
    decided_by: Optional[str] = None
    decided_at: Optional[str] = None
    decision_note: Optional[str] = None
    executed_at: Optional[str] = None
    history: List[Dict[str, Any]] = Field(default_factory=list)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def return_approval_threshold() -> float:
    """Monetary threshold (EUR/USD) above which a return requires human approval."""
    return _env_float("RETURN_APPROVAL_HITL_THRESHOLD", 150.0)


def high_value_dispatch_threshold() -> float:
    """Declared value (EUR/USD) from which a dispatch requires human confirmation."""
    return _env_float("HIGH_VALUE_DISPATCH_THRESHOLD", 1000.0)


def is_automated_actor(identity: str) -> bool:
    ident = (identity or "").strip().lower()
    return not ident or any(ident.startswith(p) for p in AUTOMATED_ACTOR_PREFIXES)


def evaluate_policy(action_type: CriticalActionType, payload: Dict[str, Any]) -> Tuple[bool, str]:
    """Return (requires_human, policy_reason) for a proposed action."""
    if action_type == CriticalActionType.RETURN_APPROVAL:
        amount = float(payload.get("amount", 0) or 0)
        threshold = return_approval_threshold()
        if payload.get("international"):
            return True, "Devolución internacional: gestión manual obligatoria (equipo de Sofía Ramos)."
        if amount > threshold:
            return True, f"Importe {amount:.2f} supera el umbral HITL de {threshold:.2f}."
        return False, f"Importe {amount:.2f} dentro del umbral automático ({threshold:.2f})."

    if action_type == CriticalActionType.HIGH_VALUE_DISPATCH:
        value = float(payload.get("declared_value", 0) or 0)
        threshold = high_value_dispatch_threshold()
        if value >= threshold:
            return True, f"Envío de alto valor ({value:.2f} >= {threshold:.2f}) requiere validación humana."
        return False, f"Valor declarado {value:.2f} por debajo del umbral ({threshold:.2f})."

    if action_type == CriticalActionType.CARRIER_CHANGE:
        status = str(payload.get("shipment_status", "")).lower()
        if status in {"in_transit", "en_transito", "en tránsito", "shipped", "out_for_delivery"}:
            return True, "Cambio de carrier en un envío ya en tránsito (aprobación de Carlos Vega)."
        return False, "Envío aún no despachado: reasignación reversible."

    if action_type == CriticalActionType.CROSS_BRAND_DATA_SHARE:
        return True, "Compartir datos B2B entre marcas cliente exige confirmación humana (confidencialidad contractual)."

    # DATA_DELETION and EXTERNAL_SEND are irreversible by definition
    return True, "Acción irreversible: requiere confirmación humana explícita."


def _audit(event: str, record: ActionRecord, **extra: Any) -> None:
    entry = {
        "event": event,
        "action_id": record.action_id,
        "action_type": record.action_type.value,
        "status": record.status.value,
        "requested_by": record.requested_by,
        "decided_by": record.decided_by,
        "requires_human": record.requires_human,
        "policy_reason": record.policy_reason,
        "timestamp": _now(),
    }
    entry.update(extra)
    logger.info("[HITL_AUDIT] %s", json.dumps(entry, ensure_ascii=False, default=str))


class HumanApprovalGate:
    """In-memory registry enforcing human confirmation before critical actions execute."""

    def __init__(self) -> None:
        self._records: Dict[str, ActionRecord] = {}
        self._lock = threading.Lock()

    def submit(
        self,
        action_type: CriticalActionType | str,
        payload: Dict[str, Any],
        *,
        requested_by: str,
        reason: str = "",
    ) -> ActionRecord:
        """Register a proposed action. It is auto-approved only if the policy allows it."""
        action_type = CriticalActionType(action_type)
        requires_human, policy_reason = evaluate_policy(action_type, payload)
        status = ActionStatus.PENDING_HUMAN_APPROVAL if requires_human else ActionStatus.AUTO_APPROVED
        record = ActionRecord(
            action_id=f"act_{uuid.uuid4().hex[:12]}",
            action_type=action_type,
            payload=dict(payload),
            requested_by=requested_by,
            reason=reason,
            requires_human=requires_human,
            policy_reason=policy_reason,
            status=status,
            created_at=_now(),
        )
        record.history.append({"status": status.value, "by": requested_by, "at": record.created_at})
        with self._lock:
            self._records[record.action_id] = record
        _audit("action_submitted", record)
        return record

    def get(self, action_id: str) -> ActionRecord:
        with self._lock:
            record = self._records.get(action_id)
        if record is None:
            raise KeyError(f"Acción '{action_id}' no encontrada.")
        return record

    def list_pending(self) -> List[ActionRecord]:
        with self._lock:
            return [r for r in self._records.values() if r.status == ActionStatus.PENDING_HUMAN_APPROVAL]

    def _decide(self, action_id: str, approver: str, note: Optional[str], approve: bool) -> ActionRecord:
        record = self.get(action_id)
        if record.status != ActionStatus.PENDING_HUMAN_APPROVAL:
            raise ApprovalPermissionError(
                f"La acción '{action_id}' no está pendiente de aprobación (estado: {record.status.value})."
            )
        if is_automated_actor(approver):
            _audit("approval_denied_automated_actor", record, attempted_by=approver)
            raise ApprovalPermissionError("Un agente o proceso automático no puede aprobar acciones críticas.")
        if approver.strip().lower() == record.requested_by.strip().lower():
            _audit("approval_denied_four_eyes", record, attempted_by=approver)
            raise ApprovalPermissionError("El solicitante no puede aprobar su propia acción (principio de cuatro ojos).")

        with self._lock:
            record.status = ActionStatus.APPROVED if approve else ActionStatus.REJECTED
            record.decided_by = approver
            record.decided_at = _now()
            record.decision_note = note
            record.history.append({"status": record.status.value, "by": approver, "at": record.decided_at})
        _audit("action_approved" if approve else "action_rejected", record, note=note)
        return record

    def approve(self, action_id: str, approver: str, note: Optional[str] = None) -> ActionRecord:
        return self._decide(action_id, approver, note, approve=True)

    def reject(self, action_id: str, approver: str, note: Optional[str] = None) -> ActionRecord:
        return self._decide(action_id, approver, note, approve=False)

    def execute(self, action_id: str, executor: Callable[[Dict[str, Any]], Any]) -> Any:
        """Run `executor(payload)` only if the action is approved. Never executes twice."""
        record = self.get(action_id)
        if record.status not in (ActionStatus.APPROVED, ActionStatus.AUTO_APPROVED):
            _audit("execution_blocked", record)
            raise HumanApprovalRequiredError(
                f"La acción '{action_id}' ({record.action_type.value}) requiere confirmación humana "
                f"antes de ejecutarse. Estado actual: {record.status.value}."
            )
        result = executor(dict(record.payload))
        with self._lock:
            record.status = ActionStatus.EXECUTED
            record.executed_at = _now()
            record.history.append({"status": record.status.value, "by": "executor", "at": record.executed_at})
        _audit("action_executed", record)
        return result

    def reset(self) -> None:
        with self._lock:
            self._records.clear()


approval_gate = HumanApprovalGate()
