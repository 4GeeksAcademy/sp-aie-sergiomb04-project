"""FastAPI router for TrackFlow RFP Intake & Routing workflow (Milestone 9 - Part 1)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile, status

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data.pipelines.rfp_intake import (  # noqa: E402
    create_rfp_ticket,
    get_rfp_ticket_bundle,
    list_rfp_tickets,
    mark_ticket_discarded,
    run_rfp_intake_pipeline,
)
from trackflow_api.models import RFPTicketStatusEnum  # noqa: E402

logger = logging.getLogger("trackflow_api.routes.rfp")

router = APIRouter(prefix="/api/rfp", tags=["rfp"])


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
    except Exception as exc:
        logger.error("Error running background RFP pipeline for ticket_id=%s: %s", ticket_id, exc, exc_info=True)
        mark_ticket_discarded(
            ticket_id,
            f"Error procesando el archivo PDF en el pipeline: {exc}",
        )


@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload an RFP PDF, save to data/raw/<ticket_id>.pdf, create Ticket, and trigger async LangGraph pipeline",
)
async def upload_rfp_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Receive an RFP PDF, persist binary under data/raw/<ticket_id>.pdf, create DB Ticket in 'analizando' state, and launch background pipeline."""
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
        "original_filename": filename,
    }


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="List recent RFP intake tickets",
)
async def get_all_rfp_tickets(
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict[str, Any]]:
    """Return recent RFP tickets ordered by creation time."""
    return list_rfp_tickets(limit=limit)


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
