"""Dedicated Arbitration Node and Conflict Resolvers for Milestone 9 - Part 3.

Strictly implements §7 of trackflow-BRIEFING.es.md:
- Fixed non-LLM arbitrators (Miguel Torres, Sofía Ramos)
- Deterministic conflict detection based on structured state
- Zero LLM consensus / zero agent negotiation
- Full audit trace with timestamps
"""

from __future__ import annotations

import logging
import re
from typing import Any

from .approval_models import (
    ConflictResolution,
    ConflictTriggerId,
    TraceStep,
)

logger = logging.getLogger("trackflow.rfp_intake.arbitration")


def detect_and_resolve_conflicts(
    *,
    client_country: str | None,
    department_sections: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> tuple[list[ConflictResolution], list[TraceStep]]:
    """Inspect structured department sections and metadata for §7 conflict triggers and apply fixed arbitration rules."""
    resolutions: list[ConflictResolution] = []
    traces: list[TraceStep] = []

    country_norm = (client_country or "").strip().lower()
    is_spain = "spain" in country_norm or "españa" in country_norm or "es" == country_norm
    is_usa = "usa" in country_norm or "united states" in country_norm or "ee. uu." in country_norm or "us" == country_norm
    expected_currency = "EUR" if is_spain else ("USD" if is_usa else "EUR")

    sec_by_id = {s["department_id"]: s for s in department_sections}

    # ─────────────────────────────────────────────────────────────────────────
    # Trigger 1: currency-mismatch
    # Dos secciones activas cotizan monedas distintas, o la moneda != mapeo de client_country
    # Árbitro fijo: Miguel Torres (Director Comercial)
    # Regla: Reescribir las secciones ofensoras a la moneda del país
    # ─────────────────────────────────────────────────────────────────────────
    currencies_found: dict[str, set[str]] = {}
    for sec in department_sections:
        draft = sec.get("draft_content") or ""
        dept_id = sec["department_id"]
        currencies_found[dept_id] = set()
        if "eur" in draft.lower() or "€" in draft:
            currencies_found[dept_id].add("EUR")
        if "usd" in draft.lower() or "$" in draft:
            currencies_found[dept_id].add("USD")

    all_detected_currencies = set().union(*currencies_found.values()) if currencies_found else set()
    has_currency_mismatch = (
        len(all_detected_currencies) > 1
        or (len(all_detected_currencies) == 1 and expected_currency not in all_detected_currencies)
    )

    if has_currency_mismatch:
        conflict_msg = (
            f"Conflicto de divisa detectado: Monedas encontradas={list(all_detected_currencies)} "
            f"frente a moneda oficial esperada={expected_currency} para país '{client_country}'."
        )
        rule_desc = "Reescribir las secciones ofensoras a la moneda del país; rechazar si no se resuelve tras el límite de iteraciones."
        action_desc = f"Miguel Torres ordena normalizar todas las cotizaciones estrictamente a {expected_currency}."

        res = ConflictResolution(
            trigger_id=ConflictTriggerId.CURRENCY_MISMATCH.value,
            arbitrator="Miguel Torres (Director Comercial)",
            conflict_detected=conflict_msg,
            resolution_rule=rule_desc,
            applied_action=action_desc,
            resolved=True,
        )
        resolutions.append(res)
        traces.append(
            TraceStep(
                agent="ArbitrationNode:currency-mismatch",
                input={"currencies_found": {k: list(v) for k, v in currencies_found.items()}, "expected": expected_currency},
                output=res.model_dump(),
            )
        )
        logger.info("Arbitration trigger '%s' resolved by Miguel Torres", ConflictTriggerId.CURRENCY_MISMATCH.value)

    # ─────────────────────────────────────────────────────────────────────────
    # Trigger 2: returns-sla-breach
    # reverse (u otra sección) promete turnaround de devoluciones bajo 48 horas (viola §5)
    # Árbitro fijo: Sofía Ramos rechaza su sección; si otro depto aún embebe esa promesa, Miguel Torres
    # Regla: Forzar request_changes en toda sección que diga devoluciones en menos de 48h; sin documento final hasta cumplir
    # ─────────────────────────────────────────────────────────────────────────
    for sec in department_sections:
        dept_id = sec["department_id"]
        draft = sec.get("draft_content") or ""

        # Check for under 48h promise (not negated)
        has_breach = False
        if re.search(r"(?:devoluci\w*|retorno\w*|turnaround).{0,50}?\b(?:24\s*(?:h|horas)|12\s*(?:h|horas)|mismo\s+d[ií]a)", draft, re.IGNORECASE):
            has_breach = True
        else:
            for m in re.finditer(r"(?:en\s+menos\s+de\s+48|bajo\s+48|< 48)", draft, re.IGNORECASE):
                prefix = draft[max(0, m.start() - 25):m.start()].lower()
                if not any(neg in prefix for neg in ("no ", "no se", "ningún", "ningun", "nunca", "jamás")):
                    has_breach = True
                    break

        if has_breach:
            arbitrator = "Sofía Ramos (Reverse Logistics Lead)" if dept_id == "reverse" else "Miguel Torres (Director Comercial)"
            conflict_msg = f"La sección '{dept_id}' incluye compromiso de procesamiento de devoluciones en menos de 48 horas, violando §5."
            rule_desc = "Forzar request_changes en toda sección que diga devoluciones en menos de 48h; sin documento final hasta cumplir."
            action_desc = f"{arbitrator} fuerza estado 'request_changes' sobre '{dept_id}'. Se exige turnaround >= 48 horas."

            res = ConflictResolution(
                trigger_id=ConflictTriggerId.RETURNS_SLA_BREACH.value,
                arbitrator=arbitrator,
                conflict_detected=conflict_msg,
                resolution_rule=rule_desc,
                applied_action=action_desc,
                resolved=True,
            )
            resolutions.append(res)
            traces.append(
                TraceStep(
                    agent="ArbitrationNode:returns-sla-breach",
                    input={"department_id": dept_id, "draft_snippet": draft[:100]},
                    output=res.model_dump(),
                )
            )
            logger.info("Arbitration trigger '%s' applied by %s to '%s'", ConflictTriggerId.RETURNS_SLA_BREACH.value, arbitrator, dept_id)

    # ─────────────────────────────────────────────────────────────────────────
    # Trigger 3: volume-vs-capacity
    # La capacidad comprometida de warehouse no soporta el volumen mensual asumido por lastmile
    # Árbitro fijo: Miguel Torres (Director Comercial)
    # Regla: Limitar el volumen de la propuesta a la capacidad de warehouse; lastmile debe revisar volumen/costo a la baja
    # ─────────────────────────────────────────────────────────────────────────
    if "warehouse" in sec_by_id and "lastmile" in sec_by_id:
        wh_aspects = sec_by_id["warehouse"].get("key_aspects") or {}
        lm_aspects = sec_by_id["lastmile"].get("key_aspects") or {}

        wh_metrics = wh_aspects.get("extracted_metrics") or {}
        lm_metrics = lm_aspects.get("extracted_metrics") or {}

        wh_max_cap = wh_metrics.get("max_monthly_capacity") or wh_metrics.get("capacity_limit")
        lm_req_vol = lm_metrics.get("monthly_volume") or (metadata.get("monthly_volume") if metadata else None)

        # Check if an explicit constraint or numbers demonstrate volume > capacity
        has_volume_conflict = False
        if wh_max_cap is not None and lm_req_vol is not None and int(lm_req_vol) > int(wh_max_cap):
            has_volume_conflict = True
        elif any("capacidad insuficiente" in c.lower() or "excede capacidad" in c.lower() for c in wh_aspects.get("constraints", [])):
            has_volume_conflict = True

        if has_volume_conflict:
            conflict_msg = (
                f"Capacidad comprometida de warehouse ({wh_max_cap or 'límite superado'}) no soporta "
                f"el volumen mensual asumido por lastmile ({lm_req_vol})."
            )
            rule_desc = "Limitar el volumen de la propuesta a la capacidad de warehouse; lastmile debe revisar volumen/costo a la baja."
            action_desc = "Miguel Torres instruye ajustar el volumen del acuerdo al tope operativo del almacén; lastmile recalcula tarifas."

            res = ConflictResolution(
                trigger_id=ConflictTriggerId.VOLUME_VS_CAPACITY.value,
                arbitrator="Miguel Torres (Director Comercial)",
                conflict_detected=conflict_msg,
                resolution_rule=rule_desc,
                applied_action=action_desc,
                resolved=True,
            )
            resolutions.append(res)
            traces.append(
                TraceStep(
                    agent="ArbitrationNode:volume-vs-capacity",
                    input={"warehouse_capacity": wh_max_cap, "lastmile_volume": lm_req_vol},
                    output=res.model_dump(),
                )
            )
            logger.info("Arbitration trigger '%s' resolved by Miguel Torres", ConflictTriggerId.VOLUME_VS_CAPACITY.value)

    return resolutions, traces
