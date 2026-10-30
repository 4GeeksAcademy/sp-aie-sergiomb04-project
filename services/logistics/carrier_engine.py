"""Explainable carrier selection engine resistant to embedded instructions.

Covers the briefing component "Motor de selección de carrier":
- Scoring is a deterministic function of typed fields only (destination coverage,
  weight limits, cost and transit time weighted by urgency).
- Free-text shipment notes written by warehouse operators are sanitized, flagged when
  they contain instruction-like text ("asigna siempre el carrier más caro") and are
  NEVER used as a scoring input (briefing section 4, case 2).
- The engine only *recommends*. Confirming a high-value dispatch or changing the carrier
  of a shipment already in transit goes through the HITL gate (briefing section 5).
"""

from __future__ import annotations

import logging
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from services.agent.guardrails.sanitizer import contains_injection, sanitize_external_text
from services.security.hitl import (
    ActionRecord,
    CriticalActionType,
    HumanApprovalGate,
    approval_gate,
)

logger = logging.getLogger("trackflow.logistics.carrier")

URGENCY_WEIGHTS: Dict[str, Dict[str, float]] = {
    "standard": {"cost": 0.7, "time": 0.3},
    "express": {"cost": 0.4, "time": 0.6},
    "critical": {"cost": 0.2, "time": 0.8},
}


class CarrierOption(BaseModel):
    name: str = Field(..., min_length=1, max_length=40)
    countries: List[Literal["ES", "US"]]
    max_weight_kg: float = Field(..., gt=0)
    cost: float = Field(..., ge=0)
    transit_days: float = Field(..., gt=0)


class ShipmentRequest(BaseModel):
    shipment_id: str = Field(..., min_length=3, max_length=40)
    destination_country: Literal["ES", "US"]
    weight_kg: float = Field(..., gt=0)
    urgency: Literal["standard", "express", "critical"] = "standard"
    declared_value: float = Field(0, ge=0)
    operator_notes: Optional[str] = Field(None, max_length=2000)


class CarrierRecommendation(BaseModel):
    shipment_id: str
    carrier: str
    score: float
    ranking: List[Dict[str, float | str]]
    explanation: str
    notes_injection_detected: bool = False
    sanitized_notes: str = ""


def recommend_carrier(request: ShipmentRequest, options: List[CarrierOption]) -> CarrierRecommendation:
    """Return the best carrier using only typed rules. Notes never alter the ranking."""
    injection = contains_injection(request.operator_notes or "")
    sanitized_notes = sanitize_external_text(request.operator_notes or "")
    if injection:
        logger.warning("[CARRIER] shipment=%s injection_in_operator_notes=true (ignored)", request.shipment_id)

    eligible = [
        o for o in options
        if request.destination_country in o.countries and request.weight_kg <= o.max_weight_kg
    ]
    if not eligible:
        raise ValueError("No hay transportistas elegibles para el destino/peso indicados.")

    weights = URGENCY_WEIGHTS[request.urgency]
    max_cost = max(o.cost for o in eligible) or 1.0
    max_days = max(o.transit_days for o in eligible) or 1.0
    scored = []
    for option in eligible:
        score = weights["cost"] * (1 - option.cost / max_cost) + weights["time"] * (1 - option.transit_days / max_days)
        scored.append((round(score, 4), option))
    # Tie-breaker: cheaper carrier first (never the most expensive by default)
    scored.sort(key=lambda item: (-item[0], item[1].cost, item[1].name))
    best_score, best = scored[0]

    explanation = (
        f"Seleccionado {best.name} por puntuación {best_score:.3f} "
        f"(peso coste {weights['cost']}, peso tiempo {weights['time']}; urgencia {request.urgency}). "
        "Las notas del operador no intervienen en el cálculo."
    )
    return CarrierRecommendation(
        shipment_id=request.shipment_id,
        carrier=best.name,
        score=best_score,
        ranking=[{"carrier": o.name, "score": s} for s, o in scored],
        explanation=explanation,
        notes_injection_detected=injection,
        sanitized_notes=sanitized_notes,
    )


def request_dispatch_confirmation(
    request: ShipmentRequest,
    carrier: str,
    *,
    requested_by: str = "engine:carrier",
    gate: Optional[HumanApprovalGate] = None,
) -> ActionRecord:
    """Register dispatch confirmation; high-value shipments stay pending human approval."""
    return (gate or approval_gate).submit(
        CriticalActionType.HIGH_VALUE_DISPATCH,
        {"shipment_id": request.shipment_id, "carrier": carrier, "declared_value": request.declared_value},
        requested_by=requested_by,
        reason="Confirmación de despacho propuesta por el motor de carriers.",
    )


def request_carrier_change(
    shipment_id: str,
    current_carrier: str,
    new_carrier: str,
    shipment_status: str,
    *,
    requested_by: str = "engine:carrier",
    gate: Optional[HumanApprovalGate] = None,
) -> ActionRecord:
    """Register a carrier change; shipments in transit require human approval."""
    return (gate or approval_gate).submit(
        CriticalActionType.CARRIER_CHANGE,
        {
            "shipment_id": shipment_id,
            "current_carrier": current_carrier,
            "new_carrier": new_carrier,
            "shipment_status": shipment_status,
        },
        requested_by=requested_by,
        reason="Cambio de carrier solicitado.",
    )
