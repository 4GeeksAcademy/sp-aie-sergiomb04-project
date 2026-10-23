"""FastAPI router for TrackFlow RFP Intake, Routing, and Real-Time SSE Notifications (Milestone 9)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    File,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data.pipelines.rfp_intake import (  # noqa: E402
    ApprovalActionEnum,
    ApprovalDecision,
    compute_readability_metrics,
    convert_pdf_to_markdown,
    create_rfp_ticket,
    detect_and_resolve_conflicts,
    extract_base_metadata,
    get_final_document,
    get_rfp_ticket_bundle,
    initiate_ticket_approval_cycle,
    list_rfp_tickets,
    mark_ticket_discarded,
    resume_department_approval,
    run_rfp_intake_pipeline,
    run_rfp_response_generation_async,
    synthesize_final_proposal_document,
    update_rfp_ticket_status,
    upsert_rfp_metadata,
)
from trackflow_api.auth import get_current_user  # noqa: E402
from trackflow_api.models import RFPTicketStatusEnum, UserRecord  # noqa: E402
from trackflow_api.sse import (  # noqa: E402
    SSE_RESPONSE_HEADERS,
    rfp_sse_broker,
)

logger = logging.getLogger("trackflow_api.routes.rfp")

router = APIRouter(prefix="/api/rfp", tags=["rfp"])


class RFPTicketCreatePayload(BaseModel):
    """Structured payload for registering a new RFP ticket directly via JSON."""

    ticket_id: str | None = None
    rfp_id: str | None = None
    raw_pdf_path: str | None = None
    pdf_path: str | None = None
    original_filename: str | None = None
    client_name: str | None = None
    client_country: str | None = None
    currency: str | None = None
    services_requested: list[str] = Field(default_factory=list)
    monthly_volume: int | None = None
    deadline: str | None = None
    budget_range: str | None = None
    departments_needed: list[str] = Field(default_factory=list)
    raw_markdown: str | None = None


def _execute_rfp_pipeline_background(
    ticket_id: str,
    pdf_path: str,
    original_filename: str | None = None,
) -> None:
    """Background worker wrapper that executes the LangGraph RFP intake pipeline safely."""
    try:
        run_rfp_intake_pipeline(
            ticket_id=ticket_id,
            pdf_path=pdf_path,
            original_filename=original_filename,
        )
        bundle = get_rfp_ticket_bundle(ticket_id)
        if bundle is not None:
            rfp_sse_broker.publish_ticket_created(
                ticket=bundle,
                metadata=bundle.get("metadata"),
                readability_metrics=bundle.get("readability_metrics"),
                broadcast=False,
            )
    except Exception as exc:
        logger.error("Error running background RFP pipeline for ticket_id=%s: %s", ticket_id, exc, exc_info=True)
        mark_ticket_discarded(
            ticket_id,
            f"Error procesando el archivo PDF en el pipeline: {exc}",
        )


@router.get(
    "/stream",
    summary="Real-time SSE stream emitting `rfp_ticket_created` events (JWT protected)",
)
@router.get(
    "/events",
    include_in_schema=False,
)
@router.get(
    "/notifications/stream",
    include_in_schema=False,
)
async def stream_rfp_notifications(
    request: Request,
    last_event_id_header: str | None = Header(default=None, alias="Last-Event-ID"),
    last_event_id_query: str | None = Query(default=None, alias="last_event_id"),
    once: bool = Query(default=False, description="Close stream after flushing current events"),
    _current_user: UserRecord = Depends(get_current_user),
) -> StreamingResponse:
    """Stream real-time Server-Sent Events (`event: rfp_ticket_created`) protected by Backoffice JWT."""
    effective_last_event_id = last_event_id_header or last_event_id_query
    return StreamingResponse(
        rfp_sse_broker.stream(
            request,
            last_event_id=effective_last_event_id,
            once=once,
        ),
        media_type="text/event-stream",
        headers=SSE_RESPONSE_HEADERS,
    )


@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload an RFP PDF, save to data/raw/<ticket_id>.pdf, create Ticket, emit SSE, and trigger async pipeline",
)
async def upload_rfp_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Receive an RFP PDF, persist binary under data/raw/<ticket_id>.pdf, create DB Ticket in 'analizando' state, emit SSE event, and launch background pipeline."""
    filename = file.filename or "rfp-upload.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Formato incorrecto: el archivo debe tener extensión .pdf",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo PDF subido está vacío.",
        )

    ticket_id = str(uuid4())
    relative_pdf_path = f"data/raw/{ticket_id}.pdf"
    absolute_pdf_path = PROJECT_ROOT / "data" / "raw" / f"{ticket_id}.pdf"
    absolute_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_pdf_path.write_bytes(content)

    ticket = create_rfp_ticket(
        ticket_id=ticket_id,
        pdf_path=relative_pdf_path,
        original_filename=filename,
    )

    # Extract deterministic base metadata for immediate structured SSE emission (no LLM calls)
    extracted_meta: dict[str, Any] = {}
    extracted_readability: dict[str, Any] = {}
    try:
        raw_md = convert_pdf_to_markdown(absolute_pdf_path)
        extracted_meta = extract_base_metadata(raw_md)
        extracted_readability = compute_readability_metrics(raw_md)
        upsert_rfp_metadata(
            ticket_id=ticket.id,
            raw_markdown=raw_md,
            metadata=extracted_meta,
            readability_metrics=extracted_readability,
        )
    except Exception as exc:
        logger.debug("Initial PDF metadata extraction skipped or deferred for ticket %s: %s", ticket.id, exc)

    sse_payload = rfp_sse_broker.publish_ticket_created(
        ticket=ticket,
        metadata=extracted_meta,
        readability_metrics=extracted_readability,
    )

    background_tasks.add_task(
        _execute_rfp_pipeline_background,
        ticket_id=ticket.id,
        pdf_path=relative_pdf_path,
        original_filename=filename,
    )

    return {
        "ticket_id": ticket.id,
        "rfp_id": ticket.rfp_id,
        "status": RFPTicketStatusEnum.ANALIZANDO.value,
        "pdf_path": relative_pdf_path,
        "raw_pdf_path": relative_pdf_path,
        "original_filename": filename,
        "client_name": sse_payload.client_name,
        "client_country": sse_payload.client_country,
        "currency": sse_payload.currency,
        "services_requested": sse_payload.services_requested,
        "monthly_volume": sse_payload.monthly_volume,
        "deadline": sse_payload.deadline,
        "budget_range": sse_payload.budget_range,
        "departments_needed": sse_payload.departments_needed,
        "created_at": sse_payload.created_at,
        "updated_at": sse_payload.updated_at,
    }


@router.post(
    "/tickets",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new RFP ticket with structured metadata and emit `rfp_ticket_created` SSE event",
)
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def register_rfp_ticket(
    payload: RFPTicketCreatePayload,
) -> dict[str, Any]:
    """Create a new RFP Ticket in PostgreSQL/SQLModel and immediately emit an `rfp_ticket_created` SSE event."""
    ticket_id = payload.ticket_id or str(uuid4())
    raw_pdf_path = (
        payload.raw_pdf_path
        or payload.pdf_path
        or f"data/raw/{ticket_id}.pdf"
    )
    ticket = create_rfp_ticket(
        ticket_id=ticket_id,
        pdf_path=raw_pdf_path,
        original_filename=payload.original_filename or f"{ticket_id}.pdf",
    )

    country = payload.client_country
    currency = payload.currency
    if not currency and country:
        if country.lower() in ("spain", "españa", "espana"):
            currency = "EUR"
        elif country.lower() in ("usa", "us", "united states"):
            currency = "USD"

    meta_dict: dict[str, Any] = {
        "client_name": payload.client_name,
        "client_country": country,
        "currency": currency,
        "services_requested": list(payload.services_requested or []),
        "monthly_volume": payload.monthly_volume,
        "deadline": payload.deadline,
        "budget_range": payload.budget_range,
        "departments_needed": list(payload.departments_needed or []),
    }
    readability_dict = compute_readability_metrics(payload.raw_markdown or "")

    upsert_rfp_metadata(
        ticket_id=ticket.id,
        raw_markdown=payload.raw_markdown or "",
        metadata=meta_dict,
        readability_metrics=readability_dict,
    )

    sse_payload = rfp_sse_broker.publish_ticket_created(
        ticket=ticket,
        metadata=meta_dict,
        readability_metrics=readability_dict,
    )
    return sse_payload.model_dump(mode="json")


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="List recent RFP intake tickets",
)
async def get_all_rfp_tickets(
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict[str, Any]]:
    """Return recent RFP tickets ordered by creation time with briefing metadata fields."""
    raw_list = list_rfp_tickets(limit=limit)
    enriched: list[dict[str, Any]] = []
    for item in raw_list:
        tid = str(item.get("ticket_id") or "")
        bundle = get_rfp_ticket_bundle(tid) if tid else None
        meta = (bundle.get("metadata") if bundle else None) or {}
        pdf_path = str(item.get("pdf_path") or f"data/raw/{tid}.pdf")
        enriched.append(
            {
                **item,
                "raw_pdf_path": pdf_path,
                "pdf_path": pdf_path,
                "client_name": item.get("client_name") or meta.get("client_name"),
                "client_country": item.get("client_country") or meta.get("client_country"),
                "currency": item.get("currency") or meta.get("currency"),
                "services_requested": list(meta.get("services_requested") or []),
                "monthly_volume": meta.get("monthly_volume"),
                "deadline": meta.get("deadline"),
                "budget_range": meta.get("budget_range"),
                "departments_needed": list(
                    item.get("departments_needed") or meta.get("departments_needed") or []
                ),
            }
        )
    return enriched


@router.get(
    "/{ticket_id}",
    status_code=status.HTTP_200_OK,
    summary="Query RFP ticket status, metadata, readability metrics, and department breakdown",
)
async def get_rfp_ticket(ticket_id: str) -> dict[str, Any]:
    """Retrieve the current status and full breakdown for a given RFP ticket_id."""
    bundle = get_rfp_ticket_bundle(ticket_id)
    if bundle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró el ticket RFP con id '{ticket_id}'.",
        )
    return bundle


def _execute_rfp_generation_background(ticket_id: str, max_iterations: int = 3) -> None:
    """Background worker wrapper that executes the response generation and evaluation loop."""
    import asyncio
    try:
        asyncio.run(
            run_rfp_response_generation_async(
                ticket_id=ticket_id,
                max_iterations=max_iterations,
            )
        )
    except Exception as exc:
        logger.error(
            "Error running background response generation for ticket_id=%s: %s",
            ticket_id,
            exc,
            exc_info=True,
        )
        update_rfp_ticket_status(ticket_id, RFPTicketStatusEnum.NEEDS_HUMAN_REVIEW.value)


@router.post(
    "/{ticket_id}/generate",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger departmental response generation and evaluation loop (Milestone 9 - Part 2)",
)
async def generate_rfp_response(
    ticket_id: str,
    background_tasks: BackgroundTasks,
    response: Response,
    sync: bool = Query(default=False, description="If True, execute synchronously and return final result"),
    max_iterations: int = Query(default=3, ge=1, le=10, description="Max generator-evaluator iterations"),
) -> dict[str, Any]:
    """Consume Part 1 handoff payload, run generator agents per department, and execute parallel evaluation loop."""
    bundle = get_rfp_ticket_bundle(ticket_id)
    if bundle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró el ticket RFP con id '{ticket_id}'.",
        )

    current_status = bundle.get("status")
    allowed_statuses = {
        RFPTicketStatusEnum.ANALISIS_COMPLETO.value,
        RFPTicketStatusEnum.GENERANDO_BORRADOR.value,
        RFPTicketStatusEnum.EN_EVALUACION.value,
        RFPTicketStatusEnum.NEEDS_HUMAN_REVIEW.value,
    }
    if current_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"El ticket está en estado '{current_status}'. Para generar la propuesta debe "
                f"encontrarse en 'analisis_completo'."
            ),
        )

    # Immediately mark as generando_borrador
    update_rfp_ticket_status(ticket_id, RFPTicketStatusEnum.GENERANDO_BORRADOR.value)

    if sync:
        try:
            result = await run_rfp_response_generation_async(
                ticket_id=ticket_id,
                max_iterations=max_iterations,
            )
            response.status_code = status.HTTP_200_OK
            updated_bundle = get_rfp_ticket_bundle(ticket_id)
            return {
                "ticket_id": ticket_id,
                "status": result.get("status"),
                "results": result.get("results"),
                "bundle": updated_bundle,
            }
        except Exception as exc:
            logger.error("Error in sync response generation: %s", exc, exc_info=True)
            update_rfp_ticket_status(ticket_id, RFPTicketStatusEnum.NEEDS_HUMAN_REVIEW.value)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error durante la generación de la propuesta: {exc}",
            )

    background_tasks.add_task(
        _execute_rfp_generation_background,
        ticket_id=ticket_id,
        max_iterations=max_iterations,
    )

    return {
        "ticket_id": ticket_id,
        "rfp_id": bundle.get("rfp_id"),
        "status": RFPTicketStatusEnum.GENERANDO_BORRADOR.value,
        "message": "Generación y evaluación de propuesta económica iniciada en segundo plano.",
    }


@router.post(
    "/{ticket_id}/approval/initiate",
    status_code=status.HTTP_200_OK,
    summary="Initiate departmental approval cycle (HITL) and transition to 'esperando_aprobación'",
)
async def initiate_approval_cycle(ticket_id: str) -> dict[str, Any]:
    """Launch LangGraph isolated approval branches with interrupt() gates per department."""
    bundle = get_rfp_ticket_bundle(ticket_id)
    if bundle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró el ticket RFP con id '{ticket_id}'.",
        )

    try:
        res = initiate_ticket_approval_cycle(ticket_id)
        return res
    except Exception as exc:
        logger.error("Error initiating approval cycle for ticket %s: %s", ticket_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error iniciando el ciclo de aprobaciones: {exc}",
        )


@router.post(
    "/{ticket_id}/approval/{department_id}",
    status_code=status.HTTP_200_OK,
    summary="Submit human approval decision (HITL resume) for a department section",
)
async def submit_department_approval(
    ticket_id: str,
    department_id: str,
    decision_payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    """Resume the paused LangGraph gate for this department and check if final document should be generated."""
    bundle = get_rfp_ticket_bundle(ticket_id)
    if bundle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró el ticket RFP con id '{ticket_id}'.",
        )

    action_str = decision_payload.get("action", "approve")
    approver = decision_payload.get("approver", "Responsable")
    notes = decision_payload.get("notes")

    try:
        action_enum = ApprovalActionEnum(action_str.lower())
    except ValueError:
        action_enum = ApprovalActionEnum.APPROVE

    decision = ApprovalDecision(
        department_id=department_id,
        action=action_enum,
        approver=approver,
        notes=notes,
    )

    try:
        res = resume_department_approval(
            ticket_id=ticket_id,
            department_id=department_id,
            decision=decision,
        )
        return res
    except Exception as exc:
        logger.error("Error resuming approval for department %s in ticket %s: %s", department_id, ticket_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registrando aprobación: {exc}",
        )


@router.get(
    "/{ticket_id}/final-document",
    status_code=status.HTTP_200_OK,
    summary="Retrieve final consolidated proposal document (Milestone 9 - Part 3)",
)
async def get_ticket_final_document(ticket_id: str) -> dict[str, Any]:
    """Retrieve the synthesized RFPFinalDocument when the ticket is in 'terminado' status."""
    bundle = get_rfp_ticket_bundle(ticket_id)
    if bundle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró el ticket RFP con id '{ticket_id}'.",
        )

    final_doc = get_final_document(ticket_id)
    if final_doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aún no se ha generado el documento final para el ticket '{ticket_id}'.",
        )
    return final_doc


@router.post(
    "/{ticket_id}/arbitrate",
    status_code=status.HTTP_200_OK,
    summary="Trigger §7 fixed arbitration conflict check across active department sections",
)
async def arbitrate_ticket_conflicts(ticket_id: str) -> dict[str, Any]:
    """Inspect structured state for volume-vs-capacity, returns-sla-breach, or currency-mismatch triggers."""
    bundle = get_rfp_ticket_bundle(ticket_id)
    if bundle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró el ticket RFP con id '{ticket_id}'.",
        )

    metadata = bundle.get("metadata") or {}
    resolutions, traces = detect_and_resolve_conflicts(
        client_country=metadata.get("client_country"),
        department_sections=bundle.get("department_sections") or [],
        metadata=metadata,
    )

    return {
        "ticket_id": ticket_id,
        "conflict_count": len(resolutions),
        "resolutions": [r.model_dump() for r in resolutions],
        "traces": [t.model_dump() for t in traces],
    }
