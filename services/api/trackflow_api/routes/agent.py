"""FastAPI router exposing the TrackFlow LangGraph support agent with Guardrails Harness."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

# Ensure project root is available in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.agent import (
    get_compiled_agent,
    guardrail_metrics,
    run_support_agent,
    trace_store,
)

logger = logging.getLogger("trackflow_api.agent")

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentQueryRequest(BaseModel):
    """Payload for querying the LangGraph support agent."""

    question: str = Field(..., description="User question regarding TrackFlow operations.")
    thread_id: Optional[str] = Field(
        None, description="Optional conversation/thread ID for checkpoint tracking."
    )
    session_user: Optional[str] = Field(
        None, description="Authenticated username/ID for session access control."
    )
    authorized_orders: Optional[List[str]] = Field(
        None, description="List of tracking/order IDs authorized for this session."
    )


class AgentQueryResponse(BaseModel):
    """Clean response model for agent queries."""

    answer: str = Field(..., description="Generated or fallback answer from the agent.")
    thread_id: str = Field(..., description="Thread ID used for checkpointing.")
    run_id: str = Field(..., description="Unique run ID for audit and tracing.")
    nodes_executed: List[str] = Field(
        ..., description="Ordered list of graph nodes traversed during execution."
    )
    is_valid: bool = Field(..., description="Whether the question was valid.")
    error: Optional[str] = Field(None, description="Controlled error message if any.")
    source_route: Optional[str] = Field(
        None, description="Routing choice made by agent (rag, incident_tool, inventory_tool, casual)."
    )
    tool_used: Optional[str] = Field(None, description="External tool invoked if applicable.")
    guardrail_action: Optional[str] = Field(
        None, description="Guardrail action: PASSED, REDIRECTED, or BLOCKED."
    )
    guardrail_failure_type: Optional[str] = Field(
        None, description="Failure category if triggered: ESTRUCTURAL, CONTENIDO, or SEGURIDAD."
    )
    guardrail_reason: Optional[str] = Field(
        None, description="Reason for guardrail block or redirection."
    )


class TraceResponse(BaseModel):
    """Structured trace detail response."""

    run_id: str
    thread_id: str
    question: str
    nodes_executed: List[str]
    steps: List[Dict[str, Any]]
    answer: str
    error: Optional[str] = None
    source_route: Optional[str] = None
    tool_used: Optional[str] = None
    created_at: str
    total_duration_ms: float


class GuardrailsSummaryResponse(BaseModel):
    """Observability summary of guardrail activations."""

    total_checks: int
    total_passed: int
    total_blocked: int
    total_redirected: int
    activations_by_failure_type: Dict[str, int]
    activations_by_guard: Dict[str, int]
    recent_events: List[Dict[str, Any]]


@router.post(
    "/query",
    response_model=AgentQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Query TrackFlow Support Agent (LangGraph)",
)
async def query_support_agent(payload: AgentQueryRequest) -> AgentQueryResponse:
    """Invoke the compiled LangGraph support agent with guardrails harness.

    The endpoint contains zero business logic; it strictly orchestrates
    agent invocation and provides safe error boundaries.
    """
    clean_question = payload.question.strip() if payload.question else ""
    if not clean_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La pregunta no puede estar vacía o contener solo espacios.",
        )

    try:
        result = run_support_agent(
            question=clean_question,
            thread_id=payload.thread_id,
            session_user=payload.session_user,
            authorized_orders=payload.authorized_orders,
        )

        return AgentQueryResponse(
            answer=result["answer"],
            thread_id=result["thread_id"],
            run_id=result["run_id"],
            nodes_executed=result["nodes_executed"],
            is_valid=result["is_valid"],
            error=result["error"],
            source_route=result.get("source_route"),
            tool_used=result.get("tool_used"),
            guardrail_action=result.get("guardrail_action"),
            guardrail_failure_type=result.get("guardrail_failure_type"),
            guardrail_reason=result.get("guardrail_reason"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Internal error processing agent query: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno procesando la consulta en el agente de soporte.",
        )


@router.get(
    "/guardrails/summary",
    response_model=GuardrailsSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Summary of guardrail activations and failure types",
)
async def get_guardrails_summary() -> GuardrailsSummaryResponse:
    """Retrieve observability metrics on guardrail activations, blocks and redirections."""
    summary_data = guardrail_metrics.get_summary()
    return GuardrailsSummaryResponse(**summary_data)


@router.get(
    "/guardrails/metrics",
    response_model=GuardrailsSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Alias for guardrails metrics summary",
)
async def get_guardrails_metrics() -> GuardrailsSummaryResponse:
    """Retrieve observability metrics on guardrail activations."""
    return await get_guardrails_summary()


@router.post(
    "/guardrails/reset",
    status_code=status.HTTP_200_OK,
    summary="Reset guardrail metrics (for test sessions)",
)
async def reset_guardrails_metrics() -> Dict[str, str]:
    """Reset accumulated guardrail metrics."""
    guardrail_metrics.reset()
    return {"message": "Guardrail metrics reset successfully"}


@router.get(
    "/traces/{run_id}",
    response_model=TraceResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve structured trace for a specific agent execution",
)
async def get_agent_trace(run_id: str) -> TraceResponse:
    """Retrieve execution trace for audit, debugging or evaluation inspection."""
    trace = trace_store.get_trace(run_id)
    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró trace para run_id: {run_id}",
        )
    return TraceResponse(**trace.to_dict())


@router.get(
    "/threads/{thread_id}/state",
    status_code=status.HTTP_200_OK,
    summary="Inspect latest checkpointed state for a thread",
)
async def get_thread_checkpoint_state(thread_id: str) -> Dict[str, Any]:
    """Inspect LangGraph checkpoint state for a specific thread."""
    app = get_compiled_agent()
    config = {"configurable": {"thread_id": thread_id}}
    state_snapshot = app.get_state(config)
    if not state_snapshot or not state_snapshot.values:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró checkpoint para thread_id: {thread_id}",
        )

    return {
        "thread_id": thread_id,
        "values": state_snapshot.values,
        "next": list(state_snapshot.next),
        "created_at": getattr(state_snapshot, "created_at", None),
    }
