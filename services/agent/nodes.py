"""Single-responsibility nodes for TrackFlow LangGraph support agent with Guardrails Harness."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from data.pipelines.rag import (
    DEFAULT_MIN_SCORE,
    NO_CONTEXT_MESSAGE,
    generate_answer,
    retrieve,
)
from services.agent.guardrails import (
    GuardrailAction,
    evaluate_input_guards,
    validate_agent_output,
    wrap_untrusted_context,
)
from services.agent.mcp_client import (
    execute_mcp_incident_query,
    execute_mcp_inventory_query,
)
from services.agent.state import AgentState

logger = logging.getLogger("trackflow.agent.nodes")


def _record_step(
    trace: List[Dict[str, Any]],
    node_name: str,
    start_time: float,
    summary: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Helper to record a standardized step trace."""
    duration_ms = (time.perf_counter() - start_time) * 1000.0
    entry = {
        "node": node_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "duration_ms": round(duration_ms, 2),
        "output_summary": summary,
    }
    return list(trace or []) + [entry]


def receive_question(state: AgentState) -> Dict[str, Any]:
    """Node: Receive, inspect, validate user question and evaluate input guardrails.

    Single responsibility: Ensure question is non-empty and well-formed,
    and apply deterministic input guardrails (Jailbreak, Personal Task, Session Auth,
    Cross-Country, Casual Scope).
    """
    t0 = time.perf_counter()
    raw_question = state.get("question", "")
    clean_question = raw_question.strip() if isinstance(raw_question, str) else ""

    is_valid = bool(clean_question)
    error = None if is_valid else "La pregunta no puede estar vacía o contener solo espacios."

    is_blocked = False
    guardrail_action = "PASSED"
    guardrail_failure_type = None
    guardrail_reason = None
    answer = state.get("answer", "")
    source_route = state.get("source_route")

    if is_valid:
        guard_result = evaluate_input_guards(
            clean_question,
            authorized_orders=state.get("authorized_orders"),
            session_user=state.get("session_user"),
        )
        guardrail_action = guard_result.action.value
        if not guard_result.passed:
            is_blocked = True
            answer = guard_result.response_message or ""
            guardrail_failure_type = (
                guard_result.failure_type.value if guard_result.failure_type else None
            )
            guardrail_reason = guard_result.reason
        elif guard_result.action == GuardrailAction.REDIRECTED:
            source_route = "casual"
            answer = guard_result.response_message or ""
            guardrail_failure_type = (
                guard_result.failure_type.value if guard_result.failure_type else None
            )
            guardrail_reason = guard_result.reason

    trace = _record_step(
        state.get("trace", []),
        node_name="receive_question",
        start_time=t0,
        summary={
            "is_valid": is_valid,
            "question_length": len(clean_question),
            "guardrail_action": guardrail_action,
            "is_blocked": is_blocked,
        },
    )

    return {
        "question": clean_question,
        "is_valid": is_valid,
        "error": error,
        "answer": answer,
        "is_blocked": is_blocked,
        "source_route": source_route,
        "guardrail_action": guardrail_action,
        "guardrail_failure_type": guardrail_failure_type,
        "guardrail_reason": guardrail_reason,
        "trace": trace,
    }


def guardrail_block_node(state: AgentState) -> Dict[str, Any]:
    """Node: Return firm refusal for input guardrail security/content blocks."""
    t0 = time.perf_counter()
    answer = state.get("answer", "Solicitud bloqueada por directivas de seguridad de TrackFlow.")
    trace = _record_step(
        state.get("trace", []),
        node_name="guardrail_block_node",
        start_time=t0,
        summary={
            "action": "blocked",
            "failure_type": state.get("guardrail_failure_type"),
            "reason": state.get("guardrail_reason"),
        },
    )
    return {
        "answer": answer,
        "trace": trace,
    }


def casual_response_node(state: AgentState) -> Dict[str, Any]:
    """Node: Return brief casual response with obligatory redirection to TrackFlow CX."""
    t0 = time.perf_counter()
    answer = state.get("answer", "Hola. ¿En qué puedo ayudarte respecto a tus envíos en TrackFlow?")
    trace = _record_step(
        state.get("trace", []),
        node_name="casual_response_node",
        start_time=t0,
        summary={
            "action": "redirected",
            "reason": state.get("guardrail_reason"),
        },
    )
    return {
        "answer": answer,
        "trace": trace,
    }


def retrieve_context(state: AgentState) -> Dict[str, Any]:
    """Node: Retrieve relevant chunks from the knowledge base using vector search and sanitize.

    Single responsibility: Execute retrieve() strictly without generation.
    Sanitizes and wraps context in untrusted non-executable tags to prevent prompt injection.
    """
    t0 = time.perf_counter()
    question = state.get("question", "")
    k = state.get("k", 5) or 5
    min_score = state.get("min_score", DEFAULT_MIN_SCORE)
    if min_score is None:
        min_score = DEFAULT_MIN_SCORE
    collection_name = state.get("collection_name")

    try:
        raw_chunks = retrieve(
            query=question,
            k=k,
            min_score=min_score,
            collection_name=collection_name,
        )
        # Sanitize and isolate retrieved context to ensure it is treated strictly as reference data
        sanitized_chunks = wrap_untrusted_context(raw_chunks)
    except Exception as exc:
        logger.error(f"Error during context retrieval: {exc}", exc_info=True)
        raw_chunks = []
        sanitized_chunks = []

    trace = _record_step(
        state.get("trace", []),
        node_name="retrieve_context",
        start_time=t0,
        summary={
            "retrieved_count": len(sanitized_chunks),
            "sources": list(
                {c.get("source_document") for c in sanitized_chunks if c.get("source_document")}
            ),
        },
    )

    return {
        "context": sanitized_chunks,
        "source_route": "rag",
        "tool_used": None,
        "trace": trace,
    }


def incident_tool_node(state: AgentState) -> Dict[str, Any]:
    """Node: Query real-time incident status using the TrackFlow MCP Server client.

    Single responsibility: Execute execute_mcp_incident_query() with explicit numerical timeout
    and honest fallback if not found or on timeout. Consumes Incidents Manager via MCP Server.
    Validates output before returning.
    """
    t0 = time.perf_counter()
    question = state.get("question", "")

    result = execute_mcp_incident_query(question)
    final_message, _ = validate_agent_output(result.message)

    trace = _record_step(
        state.get("trace", []),
        node_name="incident_tool_node",
        start_time=t0,
        summary={
            "tool": "mcp:manage_incidents",
            "success": result.success,
            "ticket_id": result.ticket_id,
            "is_fallback": result.is_fallback,
            "duration_ms": result.duration_ms,
        },
    )

    return {
        "answer": final_message,
        "source_route": "incident_tool",
        "tool_used": "incidents",
        "tool_result": result.to_dict(),
        "trace": trace,
    }


def inventory_tool_node(state: AgentState) -> Dict[str, Any]:
    """Node: Query real-time product stock using the TrackFlow MCP Server client.

    Single responsibility: Execute execute_mcp_inventory_query() with explicit numerical timeout
    and honest fallback if not found or on timeout. Read-only operation via MCP Server.
    Validates output before returning.
    """
    t0 = time.perf_counter()
    question = state.get("question", "")

    result = execute_mcp_inventory_query(question)
    final_message, _ = validate_agent_output(result.message)

    trace = _record_step(
        state.get("trace", []),
        node_name="inventory_tool_node",
        start_time=t0,
        summary={
            "tool": "mcp:query_inventory",
            "success": result.success,
            "product_query": result.product_query,
            "is_fallback": result.is_fallback,
            "duration_ms": result.duration_ms,
        },
    )

    return {
        "answer": final_message,
        "source_route": "inventory_tool",
        "tool_used": "inventory",
        "tool_result": result.to_dict(),
        "trace": trace,
    }


def generate_answer_node(state: AgentState) -> Dict[str, Any]:
    """Node: Synthesize final answer grounded on the pre-retrieved context and apply Output Guardrails.

    Single responsibility: Invoke generate_answer(question, context) with
    the exact context produced by retrieve_context and pass through validate_agent_output.
    """
    t0 = time.perf_counter()
    question = state.get("question", "")
    context = state.get("context", [])

    raw_answer = generate_answer(question=question, context=context)

    # Validate output through output guardrails (structural, prompt leak, sensitive data)
    final_answer, output_guard_result = validate_agent_output(raw_answer)

    trace = _record_step(
        state.get("trace", []),
        node_name="generate_answer_node",
        start_time=t0,
        summary={
            "context_chunks_used": len(context),
            "answer_preview": (
                final_answer[:80] + "..." if len(final_answer) > 80 else final_answer
            ),
            "output_guard_action": output_guard_result.action.value,
            "output_guard_passed": output_guard_result.passed,
        },
    )

    return {
        "answer": final_answer,
        "trace": trace,
    }


def handle_no_context(state: AgentState) -> Dict[str, Any]:
    """Node: Provide honest consultative fallback when no qualifying context is found.

    Single responsibility: Prevent hallucination on empty retrieval by explicitly
    communicating lack of data and directing to the appropriate human team.
    """
    t0 = time.perf_counter()
    answer = NO_CONTEXT_MESSAGE

    trace = _record_step(
        state.get("trace", []),
        node_name="handle_no_context",
        start_time=t0,
        summary={
            "action": "fallback_no_context",
            "message": "Honest admittance of missing documentation",
        },
    )

    return {
        "answer": answer,
        "trace": trace,
    }


def handle_error(state: AgentState) -> Dict[str, Any]:
    """Node: Formulate controlled error message for invalid input or failure.

    Single responsibility: Return safe, polite error without exposing stack traces.
    """
    t0 = time.perf_counter()
    error_msg = state.get("error") or "La consulta no pudo ser procesada."
    safe_answer = (
        "No fue posible procesar tu consulta porque la pregunta está vacía o es inválida. "
        "Por favor escribe una consulta detallada sobre las operaciones de TrackFlow."
    )

    trace = _record_step(
        state.get("trace", []),
        node_name="handle_error",
        start_time=t0,
        summary={
            "action": "handle_error",
            "error_detail": error_msg,
        },
    )

    return {
        "answer": safe_answer,
        "error": error_msg,
        "trace": trace,
    }
