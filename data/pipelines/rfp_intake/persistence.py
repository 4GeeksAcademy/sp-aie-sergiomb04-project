"""PostgreSQL / SQLModel persistence layer for the TrackFlow RFP Intake & Routing workflow."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlmodel import Session, SQLModel, select

# Ensure services/api is importable from root or pipeline execution
PROJECT_ROOT = Path(__file__).resolve().parents[3]
API_DIR = PROJECT_ROOT / "services" / "api"
for p in (str(PROJECT_ROOT), str(API_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from trackflow_api.database import get_inventory_engine, init_inventory_db  # noqa: E402
from trackflow_api.models import (  # noqa: E402
    DepartmentSection,
    RFP_OFFICIAL_DEPARTMENTS,
    RFPFinalDocument,
    RFPMetadata,
    RFPTicket,
    RFPTicketStatusEnum,
    now_utc,
)


def ensure_rfp_tables() -> None:
    """Ensure RFP SQLModel tables exist in the configured SQL database."""
    init_inventory_db()
    SQLModel.metadata.create_all(get_inventory_engine())


def create_rfp_ticket(
    *,
    ticket_id: str | None = None,
    pdf_path: str,
    original_filename: str | None = None,
    allow_existing: bool = False,
) -> RFPTicket:
    """Create a new RFPTicket record in PostgreSQL/SQLModel with status='analizando'.

    By default (`allow_existing=False`), rejects duplicate `ticket_id` values with
    `FileExistsError` so caller-supplied IDs cannot reset existing tickets or overwrite metadata.
    """
    ensure_rfp_tables()
    tid = ticket_id or str(uuid4())
    now = now_utc()
    ticket = RFPTicket(
        id=tid,
        rfp_id=f"RFP-{tid.replace('-', '')[:6].upper()}",
        status=RFPTicketStatusEnum.ANALIZANDO.value,
        pdf_path=pdf_path,
        original_filename=original_filename,
        created_at=now,
        updated_at=now,
    )
    with Session(get_inventory_engine()) as session:
        existing = session.get(RFPTicket, tid)
        if existing is not None:
            if not allow_existing:
                raise FileExistsError(
                    f"El ticket RFP con id '{tid}' ya existe y no puede ser reiniciado."
                )
            return existing

        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        return ticket


def upsert_rfp_metadata(
    *,
    ticket_id: str,
    raw_markdown: str,
    metadata: dict[str, Any],
    readability_metrics: dict[str, Any],
) -> RFPMetadata:
    """Persist or update RFPMetadata for a given ticket_id."""
    ensure_rfp_tables()
    with Session(get_inventory_engine()) as session:
        stmt = select(RFPMetadata).where(RFPMetadata.ticket_id == ticket_id)
        existing = session.exec(stmt).first()

        client_name = metadata.get("client_name")
        client_country = metadata.get("client_country")
        currency = metadata.get("currency")
        services_requested = list(metadata.get("services_requested") or [])
        monthly_volume = metadata.get("monthly_volume")
        deadline = metadata.get("deadline")
        budget_range = metadata.get("budget_range")
        departments_needed = list(metadata.get("departments_needed") or [])

        if existing is not None:
            existing.raw_markdown = raw_markdown
            existing.client_name = client_name
            existing.client_country = client_country
            existing.currency = currency
            existing.services_requested = services_requested
            existing.monthly_volume = monthly_volume
            existing.deadline = deadline
            existing.budget_range = budget_range
            existing.departments_needed = departments_needed
            existing.metadata_json = metadata
            existing.readability_metrics = readability_metrics
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing

        record = RFPMetadata(
            ticket_id=ticket_id,
            raw_markdown=raw_markdown,
            client_name=client_name,
            client_country=client_country,
            currency=currency,
            services_requested=services_requested,
            monthly_volume=monthly_volume,
            deadline=deadline,
            budget_range=budget_range,
            departments_needed=departments_needed,
            metadata_json=metadata,
            readability_metrics=readability_metrics,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record


def update_rfp_departments_needed(ticket_id: str, departments_needed: list[str]) -> None:
    """Update the departments_needed list in RFPMetadata after Orchestrator decomposition."""
    ensure_rfp_tables()
    with Session(get_inventory_engine()) as session:
        stmt = select(RFPMetadata).where(RFPMetadata.ticket_id == ticket_id)
        record = session.exec(stmt).first()
        if record is not None:
            record.departments_needed = list(departments_needed)
            updated_meta = dict(record.metadata_json or {})
            updated_meta["departments_needed"] = list(departments_needed)
            record.metadata_json = updated_meta
            session.add(record)
            session.commit()


def mark_ticket_discarded(ticket_id: str, reason: str) -> RFPTicket | None:
    """Update Ticket.status = 'descartado' when Classifier rejects a document."""
    ensure_rfp_tables()
    with Session(get_inventory_engine()) as session:
        ticket = session.get(RFPTicket, ticket_id)
        if ticket is None:
            return None
        ticket.status = RFPTicketStatusEnum.DESCARTADO.value
        ticket.rejection_reason = reason
        ticket.updated_at = now_utc()
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        return ticket


def upsert_department_section(
    *,
    ticket_id: str,
    department_id: str,
    key_aspects: dict[str, Any],
    handoff_payload: dict[str, Any] | None = None,
) -> DepartmentSection:
    """Persist or update a DepartmentSection row produced by a Department Worker."""
    ensure_rfp_tables()
    dept_info = RFP_OFFICIAL_DEPARTMENTS.get(
        department_id,
        {
            "department_id": department_id,
            "department": department_id,
            "contact_person": "Unassigned",
        },
    )
    now = now_utc()
    with Session(get_inventory_engine()) as session:
        stmt = select(DepartmentSection).where(
            DepartmentSection.ticket_id == ticket_id,
            DepartmentSection.department_id == department_id,
        )
        existing = session.exec(stmt).first()
        if existing is not None:
            existing.department = dept_info["department"]
            existing.contact_person = dept_info["contact_person"]
            existing.key_aspects = key_aspects
            if handoff_payload is not None:
                existing.handoff_payload = handoff_payload
            existing.updated_at = now
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing

        section = DepartmentSection(
            ticket_id=ticket_id,
            department_id=department_id,
            department=dept_info["department"],
            contact_person=dept_info["contact_person"],
            key_aspects=key_aspects,
            handoff_payload=handoff_payload,
            created_at=now,
            updated_at=now,
        )
        session.add(section)
        session.commit()
        session.refresh(section)
        return section


def mark_ticket_analysis_complete(
    *,
    ticket_id: str,
    executive_summary: str,
    handoff_payload: dict[str, Any],
) -> RFPTicket | None:
    """Update Ticket.status = 'analisis_completo' and store synthesizer handoff payload."""
    ensure_rfp_tables()
    now = now_utc()
    with Session(get_inventory_engine()) as session:
        ticket = session.get(RFPTicket, ticket_id)
        if ticket is None:
            return None
        ticket.status = RFPTicketStatusEnum.ANALISIS_COMPLETO.value
        ticket.executive_summary = executive_summary
        ticket.handoff_payload = handoff_payload
        ticket.updated_at = now
        session.add(ticket)

        # Also attach per-department handoff payload to each DepartmentSection
        dept_briefs = handoff_payload.get("department_briefs", {})
        stmt = select(DepartmentSection).where(DepartmentSection.ticket_id == ticket_id)
        sections = session.exec(stmt).all()
        for sec in sections:
            sec.handoff_payload = dept_briefs.get(sec.department_id, handoff_payload)
            sec.updated_at = now
            session.add(sec)

        session.commit()
        session.refresh(ticket)
        return ticket


def get_rfp_ticket_bundle(ticket_id: str) -> dict[str, Any] | None:
    """Retrieve complete ticket state, metadata, readability metrics, and department breakdown."""
    ensure_rfp_tables()
    with Session(get_inventory_engine()) as session:
        ticket = session.get(RFPTicket, ticket_id)
        if ticket is None:
            return None

        meta_stmt = select(RFPMetadata).where(RFPMetadata.ticket_id == ticket_id)
        meta_record = session.exec(meta_stmt).first()

        sec_stmt = (
            select(DepartmentSection)
            .where(DepartmentSection.ticket_id == ticket_id)
            .order_by(DepartmentSection.department_id)
        )
        sections = session.exec(sec_stmt).all()

        metadata_dict: dict[str, Any] = {}
        readability_dict: dict[str, Any] = {}
        raw_md = ""
        if meta_record is not None:
            raw_md = meta_record.raw_markdown
            readability_dict = dict(meta_record.readability_metrics or {})
            metadata_dict = dict(meta_record.metadata_json or {})
            metadata_dict.update(
                {
                    "client_name": meta_record.client_name,
                    "client_country": meta_record.client_country,
                    "currency": meta_record.currency,
                    "services_requested": list(meta_record.services_requested or []),
                    "monthly_volume": meta_record.monthly_volume,
                    "deadline": meta_record.deadline,
                    "budget_range": meta_record.budget_range,
                    "departments_needed": list(meta_record.departments_needed or []),
                }
            )

        department_sections_payload = [
            {
                "id": sec.id,
                "ticket_id": sec.ticket_id,
                "department_id": sec.department_id,
                "department": sec.department,
                "contact_person": sec.contact_person,
                "key_aspects": sec.key_aspects,
                "handoff_payload": sec.handoff_payload,
                "draft_content": sec.draft_content,
                "evaluation_results": sec.evaluation_results,
                "approval_status": sec.approval_status,
                "approver": sec.approver,
                "approved_at": sec.approved_at.isoformat() if sec.approved_at else None,
                "updated_at": sec.updated_at.isoformat() if sec.updated_at else None,
            }
            for sec in sections
        ]

        return {
            "ticket_id": ticket.id,
            "id": ticket.id,
            "rfp_id": ticket.rfp_id,
            "status": ticket.status,
            "pdf_path": ticket.pdf_path,
            "raw_pdf_path": ticket.pdf_path,
            "original_filename": ticket.original_filename,
            "rejection_reason": ticket.rejection_reason,
            "executive_summary": ticket.executive_summary,
            "handoff_payload": ticket.handoff_payload,
            "metadata": metadata_dict,
            "readability_metrics": readability_dict,
            "raw_markdown": raw_md,
            "department_sections": department_sections_payload,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
        }


def list_rfp_tickets(limit: int = 50) -> list[dict[str, Any]]:
    """List recent RFP tickets with summary metadata for the Backoffice UI using a single batch query."""
    ensure_rfp_tables()
    with Session(get_inventory_engine()) as session:
        stmt = select(RFPTicket).order_by(RFPTicket.created_at.desc()).limit(limit)
        tickets = session.exec(stmt).all()
        if not tickets:
            return []

        ticket_ids = [t.id for t in tickets]
        meta_stmt = select(RFPMetadata).where(RFPMetadata.ticket_id.in_(ticket_ids))
        meta_rows = session.exec(meta_stmt).all()
        meta_by_ticket_id: dict[str, RFPMetadata] = {
            m.ticket_id: m for m in meta_rows
        }

        results: list[dict[str, Any]] = []
        for t in tickets:
            meta = meta_by_ticket_id.get(t.id)
            meta_json = dict(meta.metadata_json or {}) if meta else {}
            pdf_path = str(t.pdf_path or f"data/raw/{t.id}.pdf")
            results.append(
                {
                    "ticket_id": t.id,
                    "rfp_id": t.rfp_id,
                    "status": t.status,
                    "pdf_path": pdf_path,
                    "raw_pdf_path": pdf_path,
                    "original_filename": t.original_filename,
                    "rejection_reason": t.rejection_reason,
                    "client_name": (
                        meta.client_name if meta and meta.client_name else meta_json.get("client_name")
                    ),
                    "client_country": (
                        meta.client_country if meta and meta.client_country else meta_json.get("client_country")
                    ),
                    "currency": (
                        meta.currency if meta and meta.currency else meta_json.get("currency")
                    ),
                    "services_requested": list(
                        (meta.services_requested if meta and meta.services_requested else meta_json.get("services_requested"))
                        or []
                    ),
                    "monthly_volume": (
                        meta.monthly_volume
                        if meta and meta.monthly_volume is not None
                        else meta_json.get("monthly_volume")
                    ),
                    "deadline": (
                        meta.deadline if meta and meta.deadline else meta_json.get("deadline")
                    ),
                    "budget_range": (
                        meta.budget_range if meta and meta.budget_range else meta_json.get("budget_range")
                    ),
                    "departments_needed": list(
                        (meta.departments_needed if meta and meta.departments_needed else meta_json.get("departments_needed"))
                        or []
                    ),
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                }
            )
        return results


def update_rfp_ticket_status(ticket_id: str, status: str) -> RFPTicket | None:
    """Update Ticket.status for lifecycle progression in Parts 2 and 3."""
    ensure_rfp_tables()
    with Session(get_inventory_engine()) as session:
        ticket = session.get(RFPTicket, ticket_id)
        if ticket is None:
            return None
        ticket.status = status
        ticket.updated_at = now_utc()
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        return ticket


def update_department_section_draft(
    *,
    ticket_id: str,
    department_id: str,
    draft_content: str,
    evaluation_results: dict[str, Any] | None = None,
    approval_status: str | None = None,
) -> DepartmentSection | None:
    """Persist generated draft and evaluation results in DepartmentSection."""
    ensure_rfp_tables()
    with Session(get_inventory_engine()) as session:
        stmt = select(DepartmentSection).where(
            DepartmentSection.ticket_id == ticket_id,
            DepartmentSection.department_id == department_id,
        )
        section = session.exec(stmt).first()
        if section is None:
            return None
        section.draft_content = draft_content
        if evaluation_results is not None:
            section.evaluation_results = evaluation_results
        if approval_status is not None:
            section.approval_status = approval_status
        section.updated_at = now_utc()
        session.add(section)
        session.commit()
        session.refresh(section)
        return section


def update_department_approval(
    *,
    ticket_id: str,
    department_id: str,
    action: str,  # approve, reject, request_changes
    approver: str,
    notes: str | None = None,
) -> DepartmentSection | None:
    """Record human approval decision (HITL) for a department section."""
    ensure_rfp_tables()
    status_map = {
        "approve": "approved",
        "reject": "rejected",
        "request_changes": "changes_requested",
    }
    approval_status = status_map.get(action.lower(), action)
    now = now_utc()

    with Session(get_inventory_engine()) as session:
        stmt = select(DepartmentSection).where(
            DepartmentSection.ticket_id == ticket_id,
            DepartmentSection.department_id == department_id,
        )
        section = session.exec(stmt).first()
        if section is None:
            return None

        section.approval_status = approval_status
        section.approver = approver
        if approval_status == "approved":
            section.approved_at = now
        section.updated_at = now

        # If notes were provided, record them in key_aspects or handoff_payload
        if notes:
            hp = dict(section.handoff_payload or {})
            hp["approval_notes"] = notes
            section.handoff_payload = hp

        session.add(section)
        session.commit()
        session.refresh(section)
        return section


def check_all_sections_approved(ticket_id: str) -> bool:
    """Check whether all active department sections for this ticket have been approved."""
    ensure_rfp_tables()
    with Session(get_inventory_engine()) as session:
        stmt = select(DepartmentSection).where(DepartmentSection.ticket_id == ticket_id)
        sections = session.exec(stmt).all()
        if not sections:
            return False
        return all(s.approval_status == "approved" for s in sections)


def save_final_document(
    *,
    ticket_id: str,
    sections: dict[str, Any],
    currency: str = "USD",
) -> RFPFinalDocument:
    """Persist the consolidated proposal document in the database and update ticket status to 'terminado'."""
    ensure_rfp_tables()
    now = now_utc()
    with Session(get_inventory_engine()) as session:
        stmt = select(RFPFinalDocument).where(RFPFinalDocument.ticket_id == ticket_id)
        existing = session.exec(stmt).first()
        if existing is not None:
            existing.sections = sections
            existing.currency = currency
            existing.generated_at = now
            session.add(existing)
            session.commit()
            session.refresh(existing)
            final_doc = existing
        else:
            final_doc = RFPFinalDocument(
                ticket_id=ticket_id,
                sections=sections,
                currency=currency,
                generated_at=now,
            )
            session.add(final_doc)
            session.commit()
            session.refresh(final_doc)

        # Mark ticket as terminado
        ticket = session.get(RFPTicket, ticket_id)
        if ticket is not None:
            ticket.status = RFPTicketStatusEnum.TERMINADO.value
            ticket.updated_at = now
            session.add(ticket)
            session.commit()

        return final_doc


def get_final_document(ticket_id: str) -> dict[str, Any] | None:
    """Retrieve the generated final document for a ticket, if it exists."""
    ensure_rfp_tables()
    with Session(get_inventory_engine()) as session:
        stmt = select(RFPFinalDocument).where(RFPFinalDocument.ticket_id == ticket_id)
        record = session.exec(stmt).first()
        if record is None:
            return None
        return {
            "id": record.id,
            "ticket_id": record.ticket_id,
            "sections": record.sections,
            "currency": record.currency,
            "generated_at": record.generated_at.isoformat() if record.generated_at else None,
        }
