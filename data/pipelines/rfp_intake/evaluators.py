"""Parallel evaluation agents for Milestone 9 - Part 2 (Readability, Relevance, and Compliance)."""

from __future__ import annotations

import asyncio
import re
from typing import Any

from .evaluation_models import (
    ComplianceEvaluation,
    EvaluationResult,
    ReadabilityEvaluation,
    RelevanceEvaluation,
)
from .ingestion import compute_readability_metrics

RULE_IDS = [
    "currency_match",
    "delivery_sla_percentage",
    "no_returns_under_48h",
    "volume_discount_table",
    "no_carrier_negotiated_rates",
]


def evaluate_readability(draft: str) -> ReadabilityEvaluation:
    """Evaluate draft readability using py-readability-metrics and formal structure thresholds."""
    if not draft or not draft.strip():
        return ReadabilityEvaluation(
            pass_=False,
            score=0.0,
            details={"error": "Borrador vacío o sin contenido."},
        )

    metrics = compute_readability_metrics(draft)
    word_count = metrics.get("word_count", 0)
    sentence_count = metrics.get("sentence_count", 0)
    fre = metrics.get("flesch_reading_ease", 0.0)

    # A professional proposal section should have adequate depth and sentence structure
    violations = []
    if word_count < 50:
        violations.append(f"Longitud insuficiente ({word_count} palabras; mínimo requerido: 50).")
    if sentence_count < 2:
        violations.append("Estructura de oraciones incompleta (mínimo 2 oraciones).")

    is_pass = len(violations) == 0
    return ReadabilityEvaluation(
        pass_=is_pass,
        score=float(fre),
        details={
            "metrics": metrics,
            "violations": violations,
            "summary": "Legibilidad adecuada para propuesta formal" if is_pass else "; ".join(violations),
        },
    )


def evaluate_relevance(
    draft: str,
    department_id: str,
    key_aspects: dict[str, Any],
) -> RelevanceEvaluation:
    """Evaluate whether the draft responds specifically to the department's scope and client requirements."""
    if not draft or not draft.strip():
        return RelevanceEvaluation(
            pass_=False,
            missing_aspects=["El borrador está completamente vacío."],
        )

    draft_lower = draft.lower()
    missing_aspects: list[str] = []

    # Check department-specific core scope concepts
    if department_id == "warehouse":
        if not any(k in draft_lower for k in ("almacen", "almacenamiento", "pallet", "sku", "stock", "capacidad")):
            missing_aspects.append("No menciona capacidad de almacenamiento ni costo por pallet/SKU.")
        if not any(k in draft_lower for k in ("onboarding", "implantación", "tiempo de preparación", "inicio")):
            missing_aspects.append("Falta especificar el tiempo o proceso de onboarding.")
    elif department_id == "lastmile":
        if not any(k in draft_lower for k in ("envío", "envio", "entrega", "transporte", "carrier", "paquete")):
            missing_aspects.append("No detalla el costo por envío ni la operativa de última milla.")
        if not any(k in draft_lower for k in ("transportista", "carrier", "flota", "cobertura", "destino")):
            missing_aspects.append("No indica las opciones de transportistas disponibles según destino.")
    elif department_id == "reverse":
        if not any(k in draft_lower for k in ("devoluci", "retorno", "reverse", "inspección", "inspeccion")):
            missing_aspects.append("No describe el flujo ni el costo del procesamiento de devoluciones.")

    # Check key scope items from Part 1 analysis if present
    scope_items = key_aspects.get("scope_items", [])
    if isinstance(scope_items, list) and scope_items:
        unmatched = 0
        for item in scope_items:
            tokens = [t.lower() for t in re.findall(r"\b\w{4,}\b", item)]
            if tokens and not any(t in draft_lower for t in tokens):
                unmatched += 1
        if unmatched > len(scope_items) * 0.7:
            missing_aspects.append("No cubre los elementos clave del alcance acordado en el análisis de recepción.")

    is_pass = len(missing_aspects) == 0
    return RelevanceEvaluation(
        pass_=is_pass,
        missing_aspects=missing_aspects,
    )


def evaluate_compliance(
    draft: str,
    department_id: str,
    client_country: str,
) -> ComplianceEvaluation:
    """Evaluate compliance against the 5 business guidelines defined in §5 of trackflow-BRIEFING.es.md.

    Rule 1: currency_match (USD for US, EUR for Spain based on client_country).
    Rule 2: delivery_sla_percentage (Must explicitly state an on-time delivery SLA %).
    Rule 3: no_returns_under_48h (Cannot promise returns turnaround in under 48 hours).
    Rule 4: volume_discount_table (Must include a volume discount table).
    Rule 5: no_carrier_negotiated_rates (Cannot disclose internal negotiated carrier rates).
    """
    if not draft or not draft.strip():
        return ComplianceEvaluation(
            pass_=False,
            rule_ids=RULE_IDS,
            violations=["Borrador vacío."],
        )

    violations: list[str] = []
    draft_lower = draft.lower()

    # Normalization of country
    country_norm = (client_country or "").strip().lower()
    is_spain = "spain" in country_norm or "españa" in country_norm or "es" == country_norm
    is_usa = "usa" in country_norm or "united states" in country_norm or "ee. uu." in country_norm or "us" == country_norm

    # 1. currency_match
    has_eur = "eur" in draft_lower or "€" in draft
    has_usd = "usd" in draft_lower or "$" in draft

    if is_spain:
        if has_usd and not has_eur:
            violations.append("currency_match: El cliente opera en España; la cotización debe ser en EUR (€), no en USD ($).")
        elif not has_eur:
            violations.append("currency_match: No se detecta la moneda obligatoria EUR (€) para operación en España.")
    elif is_usa:
        if has_eur and not has_usd:
            violations.append("currency_match: El cliente opera en EE. UU.; la cotización debe ser en USD ($), no en EUR (€).")
        elif not has_usd:
            violations.append("currency_match: No se detecta la moneda obligatoria USD ($) para operación en EE. UU.")

    # 2. delivery_sla_percentage
    # Toda propuesta debe indicar el SLA de entrega a tiempo (%) que TrackFlow se compromete a cumplir.
    sla_percentage_pattern = re.compile(r"(?:sla|entrega\s+a\s+tiempo|on-time|cumplimiento).{0,50}?\b(\d{2}(?:\.\d+)?\s*%)", re.IGNORECASE)
    generic_percentage_pattern = re.compile(r"\b(9[0-9]|100)\s*%", re.IGNORECASE)

    has_sla_percentage = bool(sla_percentage_pattern.search(draft) or (
        ("sla" in draft_lower or "entrega" in draft_lower or "tiempo" in draft_lower) and generic_percentage_pattern.search(draft)
    ))
    if not has_sla_percentage:
        violations.append("delivery_sla_percentage: La propuesta debe indicar explícitamente el SLA de entrega a tiempo con porcentaje (p. ej. 98% de entregas a tiempo).")

    # 3. no_returns_under_48h
    # Ninguna propuesta puede prometer procesamiento de devoluciones en menos de 48 horas.
    has_under_48h_promise = False

    quick_turnaround_patterns = [
        re.compile(r"(?:devoluci\w*|retorno\w*|turnaround|resoluci\w*).{0,50}?\b(?:24\s*(?:h|horas)|12\s*(?:h|horas)|mismo\s+d[ií]a|same\s*day|inmediat\w*)", re.IGNORECASE),
        re.compile(r"\b(?:24\s*(?:h|horas)|12\s*(?:h|horas)|mismo\s+d[ií]a)\b.{0,50}?(?:devoluci\w*|retorno\w*)", re.IGNORECASE),
    ]
    for p in quick_turnaround_patterns:
        if p.search(draft):
            has_under_48h_promise = True
            break

    if not has_under_48h_promise:
        # Check for promises under 48h without negative qualifiers like "ningún", "no", "nunca"
        for m in re.finditer(r"(?:en\s+menos\s+de\s+48|bajo\s+48|< 48|menor\s+(?:a|de)\s+48)", draft, re.IGNORECASE):
            start = max(0, m.start() - 30)
            prefix = draft[start:m.start()].lower()
            if not any(neg in prefix for neg in ("no ", "no se", "ningún", "ningun", "nunca", "jamás", "jamas", "prohíb", "prohib")):
                has_under_48h_promise = True
                break

    if has_under_48h_promise:
        violations.append("no_returns_under_48h: Ninguna propuesta puede prometer procesamiento de devoluciones en menos de 48 horas (viola §5).")


    # 4. volume_discount_table
    # Toda propuesta debe incluir una tabla de descuentos por volumen.
    has_table_syntax = "|" in draft and re.search(r"\|.*\|.*\n\s*\|?[\s\-:|]+\|", draft)
    has_discount_terms = any(t in draft_lower for t in ("descuento", "descuentos", "volumen", "escalado", "tiers", "rango"))
    if not (has_table_syntax and has_discount_terms):
        violations.append("volume_discount_table: Toda propuesta debe incluir una tabla formal de descuentos por volumen (formato markdown con columnas y filas).")

    # 5. no_carrier_negotiated_rates
    # Ninguna propuesta puede revelar tarifas negociadas con transportistas específicos — solo el costo final ofrecido al cliente.
    forbidden_carrier_rates = [
        re.compile(r"tarifa\s+negociada\s+con\s+(?:seur|fedex|ups|dhl|correos|gls|mrw)", re.IGNORECASE),
        re.compile(r"tarifa\s+interna\s+(?:de\s+compra|con|del\s+transportista)", re.IGNORECASE),
        re.compile(r"coste\s+(?:de\s+compra|interno)\s+(?:con\s+transportista|de\s+porte)", re.IGNORECASE),
        re.compile(r"margen\s+de\s+(?:reventa|transporte)\s+del?\s+\d+", re.IGNORECASE),
    ]
    for pattern in forbidden_carrier_rates:
        if pattern.search(draft):
            violations.append("no_carrier_negotiated_rates: No se pueden divulgar tarifas internas negociadas con transportistas específicos; solo el costo final ofrecido al cliente.")
            break

    is_pass = len(violations) == 0
    return ComplianceEvaluation(
        pass_=is_pass,
        rule_ids=RULE_IDS,
        violations=violations,
    )


async def run_parallel_evaluation(
    *,
    draft: str,
    department_id: str,
    key_aspects: dict[str, Any],
    client_country: str,
    section_id: str | None = None,
) -> EvaluationResult:
    """Execute readability, relevance, and compliance evaluations concurrently and build EvaluationResult."""
    # Run the three evaluation agents in parallel via asyncio
    readability_task = asyncio.to_thread(evaluate_readability, draft)
    relevance_task = asyncio.to_thread(evaluate_relevance, draft, department_id, key_aspects)
    compliance_task = asyncio.to_thread(evaluate_compliance, draft, department_id, client_country)

    readability, relevance, compliance = await asyncio.gather(
        readability_task,
        relevance_task,
        compliance_task,
    )

    overall_pass = bool(readability.pass_ and relevance.pass_ and compliance.pass_)

    feedback_parts: list[str] = []
    if not readability.pass_:
        feedback_parts.append(f"[Legibilidad]: {readability.details.get('summary', 'Mejorar estructura y extensión')}")
    if not relevance.pass_:
        feedback_parts.append(f"[Pertinencia]: Falta abordar los siguientes aspectos clave: {'; '.join(relevance.missing_aspects)}")
    if not compliance.pass_:
        feedback_parts.append(f"[Cumplimiento de Lineamientos §5]: Corregir las siguientes infracciones: {'; '.join(compliance.violations)}")

    feedback = "\n".join(feedback_parts) if feedback_parts else "La sección cumple con todos los lineamientos de legibilidad, pertinencia y cumplimiento."

    return EvaluationResult(
        department_id=department_id,
        section_id=section_id,
        readability=readability,
        relevance=relevance,
        compliance=compliance,
        overall_pass=overall_pass,
        feedback_for_generator=feedback,
    )
