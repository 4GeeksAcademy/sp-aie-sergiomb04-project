"""Nodes and isolated agent logic for the TrackFlow RFP Intake & Routing LangGraph pipeline."""

from __future__ import annotations

import logging
import re
from typing import Any

from data.pipelines.rfp_intake.ingestion import (
    compute_readability_metrics,
    convert_pdf_to_markdown,
    detect_departments_and_services,
    extract_base_metadata,
)
from data.pipelines.rfp_intake.persistence import (
    mark_ticket_analysis_complete,
    mark_ticket_discarded,
    update_rfp_departments_needed,
    upsert_department_section,
    upsert_rfp_metadata,
)
from data.pipelines.rfp_intake.state import (
    ClassificationResult,
    DepartmentWorkerInput,
    RFPIntakeState,
    WorkerKeyAspects,
)
from trackflow_api.models import RFP_OFFICIAL_DEPARTMENTS, RFPTicketStatusEnum

logger = logging.getLogger("trackflow.rfp_intake.nodes")


# ─── Paso 0: Conversión e Ingesta ──────────────────────────────────────────────

def ingest_document_node(state: RFPIntakeState) -> dict[str, Any]:
    """Step 0: Convert PDF to Markdown (MarkItDown), compute readability metrics, and persist base metadata."""
    ticket_id = state.get("ticket_id", "")
    pdf_path = state.get("pdf_path", "")
    raw_markdown = state.get("raw_markdown") or ""

    if not raw_markdown and pdf_path:
        raw_markdown = convert_pdf_to_markdown(pdf_path)

    readability_metrics = compute_readability_metrics(raw_markdown)
    metadata = extract_base_metadata(raw_markdown)

    if ticket_id:
        upsert_rfp_metadata(
            ticket_id=ticket_id,
            raw_markdown=raw_markdown,
            metadata=metadata,
            readability_metrics=readability_metrics,
        )

    return {
        "raw_markdown": raw_markdown,
        "readability_metrics": readability_metrics,
        "metadata": metadata,
        "nodes_executed": ["ingest_document"],
    }


# ─── Nodo 1: Clasificador (Triage Agent) ───────────────────────────────────────

def classify_rfp_document(
    markdown_text: str,
    metadata: dict[str, Any] | None = None,
) -> ClassificationResult:
    """Evaluate if the Markdown text is a valid TrackFlow client RFP (formal or informal) or an invalid document."""
    cleaned = (markdown_text or "").strip()
    if len(cleaned) < 25:
        return ClassificationResult(
            is_valid_rfp=False,
            document_type="empty",
            confidence=0.99,
            reason="Documento vacío o con texto insuficiente para constituir una solicitud de propuesta (RFP).",
        )

    lower = cleaned.lower()

    # Detect incoming supplier/carrier sales pitches targeting TrackFlow as a buyer
    carrier_pitch_indicators = [
        "pitch de proveedor",
        "tarifas mayoristas de flota",
        "propuesta comercial de servicios de transporte para trackflow",
        "ofrecerles nuestras nuevas tarifas mayoristas",
        "trackflow nos contrate como proveedor",
        "convertirnos en uno de los transportistas subcontratados por trackflow",
        "no somos una marca de e-commerce",
        "dar de alta a transiberia freight como proveedor",
        "inbound carrier rate pitch",
        "supplier rate sheet for trackflow",
    ]
    matched_pitch = [ind for ind in carrier_pitch_indicators if ind in lower]
    if matched_pitch:
        return ClassificationResult(
            is_valid_rfp=False,
            document_type="carrier_pitch",
            confidence=0.98,
            reason=(
                "Documento descartado: corresponde a un pitch comercial entrante de tarifas de transportista/proveedor "
                "hacia TrackFlow, no a una RFP de cliente de e-commerce solicitando servicios logísticos."
            ),
        )

    # Check if document requests at least one valid TrackFlow logistics service
    meta = metadata or extract_base_metadata(cleaned)
    departments_needed = meta.get("departments_needed") or []
    services_requested = meta.get("services_requested") or []

    rfp_intent_keywords = [
        "solicitud de propuesta",
        "rfp",
        "request a formal proposal",
        "request for proposal",
        "logistics partnership inquiry",
        "outsource our fulfillment",
        "externalizar nuestra operación",
        "cotización",
        "propuesta logística",
        "buscamos externalizar",
        "would like to request",
    ]
    has_rfp_intent = any(kw in lower for kw in rfp_intent_keywords)

    if not departments_needed and not services_requested:
        return ClassificationResult(
            is_valid_rfp=False,
            document_type="unrelated",
            confidence=0.92,
            reason=(
                "Documento descartado: no solicita ninguno de los servicios logísticos de TrackFlow "
                "(almacenamiento, última milla o logística inversa)."
            ),
        )

    if not has_rfp_intent and len(departments_needed) == 0:
        return ClassificationResult(
            is_valid_rfp=False,
            document_type="unrelated",
            confidence=0.90,
            reason="Documento descartado: no presenta intención de solicitud de propuesta (RFP) de cliente.",
        )

    is_informal_email = any(
        hdr in lower for hdr in ("from:", "subject:", "hi miguel", "best regards")
    )
    doc_type = "informal_rfp" if is_informal_email else "formal_rfp"
    client_label = meta.get("client_name") or "Cliente E-Commerce"
    country_label = meta.get("client_country") or "N/D"

    return ClassificationResult(
        is_valid_rfp=True,
        document_type=doc_type,
        confidence=0.96,
        reason=(
            f"RFP válida ({doc_type}) identificada para {client_label} ({country_label}). "
            f"Departamentos requeridos: {', '.join(departments_needed)}."
        ),
    )


def classifier_node(state: RFPIntakeState) -> dict[str, Any]:
    """Node 1: Classify whether the ingested document is a valid TrackFlow RFP."""
    ticket_id = state.get("ticket_id", "")
    raw_markdown = state.get("raw_markdown", "")
    metadata = state.get("metadata") or {}

    result = classify_rfp_document(raw_markdown, metadata)

    if not result.is_valid_rfp:
        updated_meta = dict(metadata)
        updated_meta["departments_needed"] = []
        updated_meta["services_requested"] = []
        if ticket_id:
            update_rfp_departments_needed(ticket_id, [])
            mark_ticket_discarded(ticket_id, result.reason)
        return {
            "is_valid_rfp": False,
            "classification": result.model_dump(),
            "rejection_reason": result.reason,
            "departments_needed": [],
            "metadata": updated_meta,
            "status": RFPTicketStatusEnum.DESCARTADO.value,
            "nodes_executed": ["classifier"],
        }

    return {
        "is_valid_rfp": True,
        "classification": result.model_dump(),
        "rejection_reason": None,
        "nodes_executed": ["classifier"],
    }


def route_after_classifier(state: RFPIntakeState) -> str:
    """Conditional edge after Node 1: route to 'orchestrator' if valid RFP, else terminate."""
    if state.get("is_valid_rfp"):
        return "orchestrator"
    return "end_discarded"


# ─── Nodo 2: Orquestador (Decomposition) ───────────────────────────────────────

def _extract_department_slice(markdown_text: str, department_id: str) -> str:
    """Extract only the paragraphs/sections relevant to a specific department.

    Prevents passing irrelevant department sections to workers, avoiding cross-contamination
    and hallucinations as required by instrucciones_t_cnicas_netto_rfp_intake_agent.md §5.3.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", markdown_text or "") if p.strip()]
    if not paragraphs:
        return ""

    dept_keywords: dict[str, tuple[str, ...]] = {
        "warehouse": (
            "warehouse",
            "warehousing",
            "almacenamiento",
            "almacén",
            "pallets",
            "skus",
            "sku",
            "picking",
            "packing",
            "inbound",
            "recepción",
            "storage",
            "onboarding",
            "lot/expiry",
            "zaragoza",
            "los angeles",
        ),
        "lastmile": (
            "last mile",
            "última milla",
            "ultima milla",
            "carrier",
            "transportista",
            "shipping",
            "envío",
            "parcels",
            "sla",
            "delivery",
            "entrega",
            "b2c",
            "destination",
            "weight",
        ),
        "reverse": (
            "reverse",
            "inversa",
            "devoluciones",
            "devolución",
            "returns",
            "prendas devueltas",
            "re-embolsado",
            "reintegración",
            "48 horas",
            "48h",
            "inspección",
        ),
    }

    # Section headings that belong exclusively to OTHER departments
    other_dept_headings: dict[str, tuple[str, ...]] = {
        "warehouse": (
            "requerimientos de logística inversa",
            "last mile & carrier management requirements",
            "requerimientos de última milla",
        ),
        "lastmile": (
            "requerimientos de almacenamiento",
            "warehouse operations requirements",
            "requerimientos de logística inversa",
        ),
        "reverse": (
            "requerimientos de almacenamiento",
            "warehouse operations requirements",
            "last mile & carrier management requirements",
        ),
    }

    target_kws = dept_keywords.get(department_id, ())
    excluded_headings = other_dept_headings.get(department_id, ())

    selected: list[str] = []
    for para in paragraphs:
        p_lower = para.lower()
        # Skip paragraphs that are dedicated headings/blocks of another department
        if any(ex_h in p_lower for ex_h in excluded_headings):
            continue
        if any(kw in p_lower for kw in target_kws):
            selected.append(para)

    if not selected:
        # If no paragraph matched specific keywords, provide only the header/summary paragraph
        selected = paragraphs[:2]

    return "\n\n".join(selected)


def decompose_rfp_by_department(
    markdown_text: str,
    metadata: dict[str, Any] | None = None,
) -> tuple[list[str], dict[str, str]]:
    """Map RFP requirements to official TrackFlow departments and segment relevant text slices."""
    meta = dict(metadata or {})
    _, detected_depts = detect_departments_and_services(markdown_text)

    departments_needed = list(meta.get("departments_needed") or detected_depts)
    # Keep canonical order: warehouse, lastmile, reverse
    canonical_order = ["warehouse", "lastmile", "reverse"]
    ordered_depts = [d for d in canonical_order if d in departments_needed]

    slices: dict[str, str] = {}
    for dept_id in ordered_depts:
        slices[dept_id] = _extract_department_slice(markdown_text, dept_id)

    return ordered_depts, slices


def orchestrator_node(state: RFPIntakeState) -> dict[str, Any]:
    """Node 2: Decompose RFP into active department workstreams and segmented text slices."""
    ticket_id = state.get("ticket_id", "")
    raw_markdown = state.get("raw_markdown", "")
    metadata = dict(state.get("metadata") or {})

    departments_needed, department_slices = decompose_rfp_by_department(raw_markdown, metadata)
    metadata["departments_needed"] = departments_needed

    if ticket_id:
        update_rfp_departments_needed(ticket_id, departments_needed)

    return {
        "departments_needed": departments_needed,
        "department_slices": department_slices,
        "metadata": metadata,
        "nodes_executed": ["orchestrator"],
    }


# ─── Nodos 3..N: Workers por Departamento (Paralelo) ───────────────────────────

def _extract_int_metric(pattern: str, text: str) -> int | None:
    """Extract an integer metric from text if explicitly stated; return None if absent."""
    m = re.search(pattern, text, flags=re.IGNORECASE)
    if not m:
        return None
    raw = m.group(1).replace(".", "").replace(",", "").strip()
    return int(raw) if raw.isdigit() else None


def run_department_worker(
    department_id: str,
    shared_metadata: dict[str, Any],
    relevant_excerpt: str,
    ticket_id: str | None = None,
) -> WorkerKeyAspects:
    """Isolated Departmental Worker analysis (Nodes 3..N).

    Receives ONLY shared_metadata + relevant_excerpt for its department.
    NEVER invents pallets, SKUs, or monthly orders not present in the input;
    registers open questions whenever key figures are missing.
    """
    if department_id not in RFP_OFFICIAL_DEPARTMENTS:
        raise ValueError(
            f"Invalid department_id '{department_id}'. Must be one of: {list(RFP_OFFICIAL_DEPARTMENTS.keys())}"
        )

    dept_info = RFP_OFFICIAL_DEPARTMENTS[department_id]
    dept_name = dept_info["department"]
    contact_person = dept_info["contact_person"]
    contribution = dept_info["contribution"]

    client_name = shared_metadata.get("client_name") or "Cliente no especificado"
    client_country = shared_metadata.get("client_country")
    currency = shared_metadata.get("currency") or (
        "EUR" if client_country == "Spain" else ("USD" if client_country == "USA" else "Por definir")
    )
    monthly_volume = shared_metadata.get("monthly_volume")
    deadline = shared_metadata.get("deadline")
    budget_range = shared_metadata.get("budget_range")

    excerpt = (relevant_excerpt or "").strip()
    excerpt_lower = excerpt.lower()

    open_questions: list[str] = []
    if monthly_volume is None:
        open_questions.append(
            "Volumen mensual de pedidos (monthly_volume) no especificado en la RFP: solicitar estimación de pedidos/mes al cliente."
        )
    if not client_country:
        open_questions.append(
            "País de operación (client_country) no identificado: confirmar si la operación es en EE. UU. (USD) o España (EUR)."
        )
    if not deadline:
        open_questions.append(
            "Fecha límite de entrega de propuesta (deadline) no indicada: confirmar fecha objetivo con Comercial."
        )

    scope_items: list[str] = []
    constraints: list[str] = [
        f"Cotizar exclusivamente en moneda {currency} según país del cliente ({client_country or 'pendiente'}).",
        "Incluir obligatoriamente tabla de descuentos por volumen (§5).",
    ]
    resources_required: list[str] = []
    extracted_metrics: dict[str, Any] = {
        "monthly_volume_orders": monthly_volume,
        "currency": currency,
    }

    if department_id == "warehouse":
        pallets = _extract_int_metric(r"(\d[\d.,]*)\s*pallets", excerpt)
        skus = _extract_int_metric(r"(\d[\d.,]*)\s*(?:active\s+cosmetic\s+)?skus", excerpt)
        extracted_metrics["pallets_requested"] = pallets
        extracted_metrics["skus_count"] = skus

        facility = (
            "Almacén Zaragoza (España)"
            if client_country == "Spain" or "zaragoza" in excerpt_lower
            else "Almacén Los Ángeles (EE. UU.)"
        )
        resources_required.append(f"Capacidad operativa y WMS en {facility} (Responsable: {contact_person}).")

        if pallets is not None:
            scope_items.append(f"Almacenamiento estimado de {pallets} pallets en {facility}.")
        else:
            open_questions.append(
                "Cantidad de pallets requeridos no especificada: confirmar volumen de ocupación en almacén."
            )

        if skus is not None:
            scope_items.append(f"Gestión de inventario y catálogo para {skus} SKUs activos.")
        else:
            open_questions.append(
                "Número de SKUs activos no especificado: solicitar detalle de catálogo al cliente."
            )

        if "lot" in excerpt_lower or "expiry" in excerpt_lower or "caducidad" in excerpt_lower:
            scope_items.append("Control de lote y fecha de caducidad (lot/expiry tracking) en WMS.")
            resources_required.append("Módulo de trazabilidad por lote/caducidad y temperatura controlada.")

        if "picking" in excerpt_lower or "packing" in excerpt_lower or "pick/pack" in excerpt_lower:
            scope_items.append(
                f"Preparación de pedidos (picking y packing) para {monthly_volume if monthly_volume is not None else 'N/D'} pedidos/mes."
            )

        if "17:00" in excerpt_lower:
            constraints.append("Hora de corte (cut-off) de preparación de pedidos a las 17:00 CET.")

        summary = (
            f"Dimensionamiento de almacenamiento y fulfillment para {client_name} en {facility}: "
            f"pallets={pallets if pallets is not None else 'no indicado'}, "
            f"SKUs={skus if skus is not None else 'no indicado'}, "
            f"volumen={monthly_volume if monthly_volume is not None else 'no indicado'} pedidos/mes ({currency})."
        )

    elif department_id == "lastmile":
        parcels = _extract_int_metric(r"([\d.,]+)\s*(?:b2c\s+)?(?:parcels|pedidos|orders)", excerpt)
        if parcels is None:
            parcels = monthly_volume
        weight_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:lbs|kg)", excerpt, flags=re.IGNORECASE)
        avg_weight = weight_match.group(0).strip() if weight_match else None

        extracted_metrics["monthly_shipments"] = parcels
        extracted_metrics["avg_parcel_weight"] = avg_weight

        if avg_weight is None:
            open_questions.append(
                "Peso y dimensiones promedio por paquete no especificados: solicitar perfil volumétrico para tarifario de última milla."
            )

        zone_desc = (
            "Distribución nacional EE. UU. (60% California / 40% resto continental)"
            if "california" in excerpt_lower or client_country == "USA"
            else "Distribución peninsular y nacional España"
        )
        scope_items.append(f"Cobertura de transporte de última milla: {zone_desc}.")
        if parcels is not None:
            scope_items.append(f"Despacho estimado de {parcels} envíos B2C mensuales.")

        constraints.extend(
            [
                "Indicar explícitamente el SLA de entrega a tiempo (%) que TrackFlow se compromete a cumplir (§5).",
                "PROHIBIDO revelar tarifas negociadas con transportistas específicos — mostrar únicamente el costo final ofrecido al cliente (§5).",
            ]
        )
        resources_required.append(
            f"Pool de transportistas homologados según destino y motor de asignación (Responsable: {contact_person})."
        )
        summary = (
            f"Cotización de última milla y SLA de entrega para {client_name} ({zone_desc}): "
            f"{parcels if parcels is not None else 'N/D'} envíos/mes, peso medio={avg_weight or 'no indicado'} ({currency})."
        )

    else:  # reverse
        return_rate_match = re.search(r"(\d+(?:[.,]\d+)?)\s*%", excerpt)
        return_rate_pct = float(return_rate_match.group(1).replace(",", ".")) if return_rate_match else None
        est_returns = _extract_int_metric(r"~?\s*([\d.,]+)\s*devoluciones\s*mensuales", excerpt)

        extracted_metrics["return_rate_pct"] = return_rate_pct
        extracted_metrics["estimated_monthly_returns"] = est_returns

        if return_rate_pct is None and est_returns is None:
            open_questions.append(
                "Tasa o volumen estimado de devoluciones mensuales no especificado: confirmar porcentaje esperado de logística inversa."
            )

        scope_items.append(
            "Recepción, inspección de calidad, reacondicionamiento y reintegración de stock de devoluciones."
        )
        if est_returns is not None:
            scope_items.append(f"Procesamiento estimado de ~{est_returns} devoluciones mensuales ({return_rate_pct}% tasa media).")

        constraints.extend(
            [
                "RESTRICCIÓN DURA (§5): Ninguna propuesta puede prometer procesamiento de devoluciones en menos de 48 horas (SLA mínimo >= 48h).",
            ]
        )
        resources_required.append(
            f"Estación de inspección y logística inversa en almacén (Responsable: {contact_person})."
        )
        summary = (
            f"Operativa de logística inversa para {client_name}: "
            f"volumen estimado={est_returns if est_returns is not None else 'no indicado'} devoluciones/mes "
            f"(tasa={f'{return_rate_pct}%' if return_rate_pct is not None else 'no indicada'}), SLA >= 48h ({currency})."
        )

    if budget_range:
        extracted_metrics["client_budget_range"] = budget_range

    key_aspects = WorkerKeyAspects(
        department_id=department_id,
        department_name=dept_name,
        contact_person=contact_person,
        summary=summary,
        scope_items=scope_items,
        constraints=constraints,
        resources_required=resources_required,
        extracted_metrics=extracted_metrics,
        open_questions=open_questions,
        what_to_contribute=contribution,
        relevant_excerpt=excerpt,
    )

    if ticket_id:
        upsert_department_section(
            ticket_id=ticket_id,
            department_id=department_id,
            key_aspects=key_aspects.model_dump(),
        )

    return key_aspects


def department_worker_node(payload: DepartmentWorkerInput) -> dict[str, Any]:
    """LangGraph parallel worker node invoked via Send('department_worker', payload)."""
    dept_id = payload["department_id"]
    ticket_id = payload.get("ticket_id", "")
    shared_metadata = payload.get("shared_metadata") or {}
    relevant_excerpt = payload.get("relevant_excerpt") or ""

    aspects = run_department_worker(
        department_id=dept_id,
        shared_metadata=shared_metadata,
        relevant_excerpt=relevant_excerpt,
        ticket_id=ticket_id,
    )
    return {
        "worker_outputs": {dept_id: aspects.model_dump()},
        "nodes_executed": [f"worker_{dept_id}"],
    }


# ─── Nodo 4: Sintetizador (Synthesizer Agent) ──────────────────────────────────

def _detect_cross_worker_conflicts(
    client_country: str,
    expected_currency: str,
    worker_outputs: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    """Detect structured contradictions across workers for downstream arbitration (§7)."""
    conflicts: list[dict[str, str]] = []

    # 1. currency-mismatch check
    currencies_seen = set()
    for dept_id, w_data in worker_outputs.items():
        w_curr = (w_data.get("extracted_metrics") or {}).get("currency")
        if w_curr:
            currencies_seen.add(w_curr)
            if expected_currency in ("USD", "EUR") and w_curr != expected_currency:
                conflicts.append(
                    {
                        "trigger_id": "currency-mismatch",
                        "department_id": dept_id,
                        "arbiter": "Miguel Torres",
                        "detail": f"Sección {dept_id} cotiza en {w_curr} pero client_country={client_country} exige {expected_currency}.",
                    }
                )
    if len(currencies_seen) > 1:
        conflicts.append(
            {
                "trigger_id": "currency-mismatch",
                "department_id": "multiple",
                "arbiter": "Miguel Torres",
                "detail": f"Múltiples monedas detectadas entre workers activos: {sorted(currencies_seen)}.",
            }
        )

    # 2. volume-vs-capacity check between warehouse and lastmile
    wh_metrics = (worker_outputs.get("warehouse") or {}).get("extracted_metrics") or {}
    lm_metrics = (worker_outputs.get("lastmile") or {}).get("extracted_metrics") or {}
    wh_vol = wh_metrics.get("monthly_volume_orders")
    lm_vol = lm_metrics.get("monthly_shipments")
    if wh_vol is not None and lm_vol is not None and lm_vol > wh_vol:
        conflicts.append(
            {
                "trigger_id": "volume-vs-capacity",
                "department_id": "warehouse,lastmile",
                "arbiter": "Miguel Torres (Director Comercial)",
                "detail": f"Last Mile asume {lm_vol} envíos/mes pero la capacidad reportada en Warehouse es {wh_vol} pedidos/mes.",
            }
        )

    return conflicts


def synthesize_rfp_analysis(
    *,
    ticket_id: str,
    rfp_id: str,
    metadata: dict[str, Any],
    readability_metrics: dict[str, Any],
    departments_needed: list[str],
    worker_outputs: dict[str, dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    """Consolidate department worker analyses into Sales executive summary and Part 2 handoff contract."""
    client_name = metadata.get("client_name") or "Cliente E-Commerce"
    client_country = metadata.get("client_country") or "Por definir"
    currency = metadata.get("currency") or ("EUR" if client_country == "Spain" else "USD")
    monthly_volume = metadata.get("monthly_volume")
    deadline = metadata.get("deadline") or "No especificada"
    budget_range = metadata.get("budget_range") or "No especificado"
    unsupported_departments = list(metadata.get("unsupported_departments") or [])

    all_depts = ["warehouse", "lastmile", "reverse"]
    excluded_depts = [d for d in all_depts if d not in departments_needed]

    summary_lines = [
        f"### Resumen Ejecutivo para Ventas (Miguel Torres) — {client_name} ({client_country} / {currency})",
        f"- **Volumen mensual estimado:** {f'{monthly_volume:,} pedidos/mes' if monthly_volume else 'No especificado (ver preguntas abiertas)'}",
        f"- **Fecha límite (Deadline):** {deadline} | **Presupuesto de referencia:** {budget_range}",
        f"- **Departamentos activos ({len(departments_needed)}):** {', '.join(departments_needed)}",
    ]
    if excluded_depts:
        summary_lines.append(
            f"- **Departamentos excluidos por alcance del cliente:** {', '.join(excluded_depts)} (no requeridos en esta propuesta)"
        )
    if unsupported_departments:
        summary_lines.append(
            f"- **Solicitudes fuera de catálogo ignoradas por el orquestador:** {', '.join(unsupported_departments)} (no forman parte de los departamentos oficiales de TrackFlow)"
        )

    summary_lines.append("\n#### ¿Qué pedirle a qué departamento?")

    what_to_ask: dict[str, dict[str, Any]] = {}
    department_briefs: dict[str, dict[str, Any]] = {}

    for dept_id in departments_needed:
        worker_data = worker_outputs.get(dept_id, {})
        dept_meta = RFP_OFFICIAL_DEPARTMENTS.get(dept_id, {})
        contact = worker_data.get("contact_person") or dept_meta.get("contact_person", "")
        dept_title = worker_data.get("department_name") or dept_meta.get("department", dept_id)
        contribution = worker_data.get("what_to_contribute") or dept_meta.get("contribution", "")
        open_qs = worker_data.get("open_questions") or []

        summary_lines.append(
            f"1. **{dept_title} (`{dept_id}`) — Responsable: {contact}**:\n"
            f"   - **Solicitar:** {contribution}.\n"
            f"   - **Alcance detectado:** {worker_data.get('summary', '')}"
        )
        if open_qs:
            summary_lines.append(f"   - **Preguntas abiertas a validar:** {'; '.join(open_qs)}")

        what_to_ask[dept_id] = {
            "department_id": dept_id,
            "department_name": dept_title,
            "contact_person": contact,
            "deliverable_requested": contribution,
            "open_questions": open_qs,
        }
        department_briefs[dept_id] = {
            "ticket_id": ticket_id,
            "department_id": dept_id,
            "department_name": dept_title,
            "approver": contact,
            "currency": currency,
            "client_name": client_name,
            "client_country": client_country,
            "shared_metadata": metadata,
            "key_aspects": worker_data,
        }

    potential_conflicts = _detect_cross_worker_conflicts(
        client_country=client_country,
        expected_currency=currency,
        worker_outputs=worker_outputs,
    )

    executive_summary = "\n".join(summary_lines)

    handoff_payload: dict[str, Any] = {
        "contract_version": "1.0",
        "ready_for_part_2": True,
        "ticket_id": ticket_id,
        "rfp_id": rfp_id,
        "client_name": client_name,
        "client_country": client_country,
        "currency": currency,
        "departments_needed": departments_needed,
        "excluded_departments": excluded_depts,
        "unsupported_departments": unsupported_departments,
        "shared_metadata": metadata,
        "readability_metrics": readability_metrics,
        "executive_summary": executive_summary,
        "what_to_ask_each_department": what_to_ask,
        "department_briefs": department_briefs,
        "potential_conflicts": potential_conflicts,
        "compliance_guidelines": {
            "required_currency": currency,
            "must_include_on_time_delivery_sla_pct": True,
            "min_returns_processing_hours": 48,
            "must_include_volume_discount_table": True,
            "forbid_carrier_negotiated_rates_disclosure": True,
        },
    }

    return executive_summary, handoff_payload


def synthesizer_node(state: RFPIntakeState) -> dict[str, Any]:
    """Node 4: Consolidate worker outputs, produce Sales executive summary & Part 2 handoff contract."""
    ticket_id = state.get("ticket_id", "")
    rfp_id = state.get("rfp_id") or (f"RFP-{ticket_id[:6].upper()}" if ticket_id else "RFP-LOCAL")
    metadata = state.get("metadata") or {}
    readability_metrics = state.get("readability_metrics") or {}
    departments_needed = state.get("departments_needed") or []
    worker_outputs = state.get("worker_outputs") or {}

    executive_summary, handoff_payload = synthesize_rfp_analysis(
        ticket_id=ticket_id,
        rfp_id=rfp_id,
        metadata=metadata,
        readability_metrics=readability_metrics,
        departments_needed=departments_needed,
        worker_outputs=worker_outputs,
    )

    if ticket_id:
        mark_ticket_analysis_complete(
            ticket_id=ticket_id,
            executive_summary=executive_summary,
            handoff_payload=handoff_payload,
        )

    return {
        "executive_summary": executive_summary,
        "handoff_payload": handoff_payload,
        "status": RFPTicketStatusEnum.ANALISIS_COMPLETO.value,
        "nodes_executed": ["synthesizer"],
    }
