"""Pipeline and Orchestration for Milestone 9 - Part 2: Departmental Response Generation and Evaluation Loop."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from trackflow_api.models import RFPTicketStatusEnum

from .evaluators import run_parallel_evaluation
from .generators import generate_department_draft
from .persistence import (
    get_rfp_ticket_bundle,
    update_department_section_draft,
    update_rfp_ticket_status,
)

logger = logging.getLogger("trackflow.rfp_intake.response_flow")


async def run_rfp_response_generation_async(
    *,
    ticket_id: str,
    max_iterations: int = 3,
) -> dict[str, Any]:
    """Execute response generation and parallel evaluation loop across all active departments.

    Consumes Part 1 handoff contract (ticket_id + synthesizer payload / key_aspects)
    from PostgreSQL without re-parsing raw PDF.
    """
    logger.info("Starting response generation for ticket_id=%s (max_iterations=%d)", ticket_id, max_iterations)

    bundle = get_rfp_ticket_bundle(ticket_id)
    if bundle is None:
        raise ValueError(f"Ticket with ID '{ticket_id}' not found in database.")

    status = bundle.get("status")
    allowed_statuses = {
        RFPTicketStatusEnum.ANALISIS_COMPLETO.value,
        RFPTicketStatusEnum.GENERANDO_BORRADOR.value,
        RFPTicketStatusEnum.EN_EVALUACION.value,
        RFPTicketStatusEnum.NEEDS_HUMAN_REVIEW.value,
    }
    if status not in allowed_statuses:
        raise ValueError(
            f"Ticket {ticket_id} status is '{status}'. It must be in 'analisis_completo' "
            f"to start Part 2 response generation."
        )

    # 1. Update status to generando_borrador
    update_rfp_ticket_status(ticket_id, RFPTicketStatusEnum.GENERANDO_BORRADOR.value)

    shared_metadata = bundle.get("metadata") or {}
    client_country = shared_metadata.get("client_country") or "Spain"
    dept_sections = bundle.get("department_sections") or []

    if not dept_sections:
        logger.warning("Ticket %s has no active department sections", ticket_id)
        update_rfp_ticket_status(ticket_id, RFPTicketStatusEnum.ANALISIS_COMPLETO.value)
        return {"ticket_id": ticket_id, "status": "no_active_sections", "results": {}}

    results_by_dept: dict[str, Any] = {}
    any_needs_human_review = False

    # Process departments concurrently or sequentially per department
    # Note: Evaluators run in parallel for each department section
    for sec in dept_sections:
        dept_id = sec["department_id"]
        sec_id = sec.get("id")
        key_aspects = sec.get("key_aspects") or {}

        logger.info("Generating and evaluating proposal section for department '%s'", dept_id)

        feedback: str | None = None
        latest_draft: str = ""
        latest_eval: dict[str, Any] = {}
        passed = False
        iteration_count = 0

        # Generator-Evaluator Loop with iteration limit
        for iter_num in range(1, max_iterations + 1):
            iteration_count = iter_num
            # Generate draft
            latest_draft = generate_department_draft(
                department_id=dept_id,
                key_aspects=key_aspects,
                shared_metadata=shared_metadata,
                feedback_for_generator=feedback,
                iteration=iter_num,
            )

            # Update ticket status to en_evaluación during evaluation
            update_rfp_ticket_status(ticket_id, RFPTicketStatusEnum.EN_EVALUACION.value)

            # Run parallel evaluators (readability, relevance, compliance)
            eval_result = await run_parallel_evaluation(
                draft=latest_draft,
                department_id=dept_id,
                key_aspects=key_aspects,
                client_country=client_country,
                section_id=sec_id,
            )

            latest_eval = eval_result.to_dict()

            if eval_result.overall_pass:
                passed = True
                logger.info(
                    "Department '%s' passed evaluation on iteration %d",
                    dept_id,
                    iter_num,
                )
                break
            else:
                feedback = eval_result.feedback_for_generator
                logger.warning(
                    "Department '%s' failed evaluation on iteration %d: %s",
                    dept_id,
                    iter_num,
                    feedback,
                )

        approval_status = "evaluated_pass" if passed else "needs_human_review"
        if not passed:
            any_needs_human_review = True
            logger.warning(
                "Department '%s' exhausted %d iterations without passing evaluation. Marked as needs_human_review.",
                dept_id,
                max_iterations,
            )

        # Persist draft and evaluation result in PostgreSQL
        update_department_section_draft(
            ticket_id=ticket_id,
            department_id=dept_id,
            draft_content=latest_draft,
            evaluation_results=latest_eval,
            approval_status=approval_status,
        )

        results_by_dept[dept_id] = {
            "department_id": dept_id,
            "passed": passed,
            "iterations": iteration_count,
            "draft_content": latest_draft,
            "evaluation_results": latest_eval,
            "approval_status": approval_status,
        }

    # Final ticket lifecycle status transition
    final_status = (
        RFPTicketStatusEnum.NEEDS_HUMAN_REVIEW.value
        if any_needs_human_review
        else RFPTicketStatusEnum.EN_EVALUACION.value
    )
    update_rfp_ticket_status(ticket_id, final_status)
    logger.info("Completed response generation for ticket %s. Final status: %s", ticket_id, final_status)

    return {
        "ticket_id": ticket_id,
        "status": final_status,
        "results": results_by_dept,
    }


def run_rfp_response_generation_pipeline(
    *,
    ticket_id: str,
    max_iterations: int = 3,
) -> dict[str, Any]:
    """Synchronous entry point for response generation pipeline."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        # Running inside an active loop (e.g. FastAPI async context)
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(
                asyncio.run,
                run_rfp_response_generation_async(
                    ticket_id=ticket_id,
                    max_iterations=max_iterations,
                ),
            ).result()
    else:
        return loop.run_until_complete(
            run_rfp_response_generation_async(
                ticket_id=ticket_id,
                max_iterations=max_iterations,
            )
        )
