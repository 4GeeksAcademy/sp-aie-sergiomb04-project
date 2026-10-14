"""Single-responsibility nodes for TrackFlow LangGraph support agent with Guardrails Harness and Memory."""

from __future__ import annotations

import logging
import time
import uuid
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
from services.agent.memory import (
    MemoryAuditRecord,
    ProposalIntent,
    intent_classifier,
    memory_consolidator,
    memory_evaluator,
    memory_store,
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
    """Node: Receive, inspect and validate the user question.

    Single responsibility: Ensure question is non-empty and well-formed.
    Evaluates deterministic input guardrails (Jailbreak, Personal Task, Session Auth,
    Cross-Country, Casual Scope).
    If passed, evaluates pending memory proposals against user intent if one is unresolved.
    """
    t0 = time.perf_counter()
    raw_question = state.get("question", "")
    clean_question = raw_question.strip() if isinstance(raw_question, str) else ""

    thread_id = state.get("thread_id", "")
    session_user = state.get("session_user")
    authorized_orders = state.get("authorized_orders")

    # 1. Guardrails evaluation on input
    is_blocked = False
    guardrail_action = "PASSED"
    guardrail_failure_type = None
    guardrail_reason = None
    direct_answer: Optional[str] = None
    source_route: Optional[str] = state.get("source_route")

    if clean_question:
        guard_res = evaluate_input_guards(
            clean_question,
            authorized_orders=authorized_orders,
            session_user=session_user,
        )
        guardrail_action = guard_res.action.value
        if not guard_res.passed:
            is_blocked = True
            direct_answer = guard_res.response_message or ""
            guardrail_failure_type = (
                guard_res.failure_type.value if guard_res.failure_type else None
            )
            guardrail_reason = guard_res.reason
        elif guard_res.action == GuardrailAction.REDIRECTED:
            source_route = "casual"
            direct_answer = guard_res.response_message or ""
            guardrail_failure_type = (
                guard_res.failure_type.value if guard_res.failure_type else None
            )
            guardrail_reason = guard_res.reason

    # 2. If blocked or casual, prevent memory poisoning by skipping memory proposal resolution
    proposal_decision: Optional[Dict[str, Any]] = None
    if not is_blocked and source_route != "casual":
        pending_proposal = memory_store.get_pending_proposal(thread_id) if thread_id else None
        if pending_proposal and clean_question:
            intent_res = intent_classifier.classify(clean_question, pending_proposal.summary)
            decision_intent = intent_res.intent
            now_iso = datetime.now(timezone.utc).isoformat()
            audit_id = f"aud_{uuid.uuid4().hex[:10]}"

            if decision_intent == ProposalIntent.APPROVE:
                exp = memory_consolidator.calculate_expiration(pending_proposal)
                saved_record = memory_store.save_approved_memory(
                    proposal=pending_proposal,
                    authorized_by="user",
                    expires_at=exp,
                )
                audit_entry = MemoryAuditRecord(
                    audit_id=audit_id,
                    proposal_id=pending_proposal.proposal_id,
                    thread_id=thread_id,
                    timestamp=now_iso,
                    trigger_message=pending_proposal.trigger_message,
                    proposed_content=pending_proposal.proposed_content,
                    category=pending_proposal.category.value,
                    user_decision_message=clean_question,
                    decision_intent=ProposalIntent.APPROVE,
                    outcome="approved",
                    authorized_by="user",
                    notes=f"Memory approved and saved under entity_key '{saved_record.entity_key}'.",
                )
                memory_store.record_audit(audit_entry)
                memory_store.clear_pending_proposal(thread_id)
                confirmation_note = "Entendido, he guardado esta regla en la memoria operativa para futuras consultas."

            elif decision_intent == ProposalIntent.REJECT:
                audit_entry = MemoryAuditRecord(
                    audit_id=audit_id,
                    proposal_id=pending_proposal.proposal_id,
                    thread_id=thread_id,
                    timestamp=now_iso,
                    trigger_message=pending_proposal.trigger_message,
                    proposed_content=pending_proposal.proposed_content,
                    category=pending_proposal.category.value,
                    user_decision_message=clean_question,
                    decision_intent=ProposalIntent.REJECT,
                    outcome="rejected",
                    authorized_by=None,
                    notes="User rejected memory proposal. Proposal discarded.",
                )
                memory_store.record_audit(audit_entry)
                memory_store.clear_pending_proposal(thread_id)
                confirmation_note = "Entendido, he descartado la propuesta y no se guardará en memoria."

            elif decision_intent == ProposalIntent.EDIT:
                exp = memory_consolidator.calculate_expiration(pending_proposal)
                saved_record = memory_store.save_approved_memory(
                    proposal=pending_proposal,
                    authorized_by="user",
                    modified_content=intent_res.edited_content,
                    expires_at=exp,
                )
                audit_entry = MemoryAuditRecord(
                    audit_id=audit_id,
                    proposal_id=pending_proposal.proposal_id,
                    thread_id=thread_id,
                    timestamp=now_iso,
                    trigger_message=pending_proposal.trigger_message,
                    proposed_content=pending_proposal.proposed_content,
                    category=pending_proposal.category.value,
                    user_decision_message=clean_question,
                    decision_intent=ProposalIntent.EDIT,
                    outcome="edited_and_approved",
                    authorized_by="user",
                    notes=f"Memory edited and approved: {intent_res.edited_content}",
                )
                memory_store.record_audit(audit_entry)
                memory_store.clear_pending_proposal(thread_id)
                confirmation_note = f"Entendido, he actualizado y guardado la regla en memoria operativa: '{intent_res.edited_content}'."

            else:
                audit_entry = MemoryAuditRecord(
                    audit_id=audit_id,
                    proposal_id=pending_proposal.proposal_id,
                    thread_id=thread_id,
                    timestamp=now_iso,
                    trigger_message=pending_proposal.trigger_message,
                    proposed_content=pending_proposal.proposed_content,
                    category=pending_proposal.category.value,
                    user_decision_message=clean_question,
                    decision_intent=ProposalIntent.AMBIGUOUS_OR_UNRELATED,
                    outcome="discarded_ambiguous",
                    authorized_by=None,
                    notes="Ambiguity or topic change: pending proposal discarded by default.",
                )
                memory_store.record_audit(audit_entry)
                memory_store.clear_pending_proposal(thread_id)
                confirmation_note = None

            proposal_decision = {
                "intent": decision_intent.value,
                "confirmation_note": confirmation_note,
                "proposal_id": pending_proposal.proposal_id,
            }

            if intent_res.remaining_query:
                clean_question = intent_res.remaining_query
            elif confirmation_note:
                direct_answer = confirmation_note

    is_valid = bool(clean_question) or bool(direct_answer)
    error = None if is_valid else "La pregunta no puede estar vacía o contener solo espacios."

    trace = _record_step(
        state.get("trace", []),
        node_name="receive_question",
        start_time=t0,
        summary={
            "is_valid": is_valid,
            "question_length": len(clean_question),
            "had_pending_proposal": (
                bool(thread_id and memory_store.get_pending_proposal(thread_id))
            ),
            "proposal_decision": proposal_decision.get("intent") if proposal_decision else None,
            "guardrail_action": guardrail_action,
            "is_blocked": is_blocked,
        },
    )

    return {
        "question": clean_question,
        "is_valid": is_valid,
        "error": error,
        "answer": direct_answer or "",
        "proposal_decision": proposal_decision,
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
    """Node: Retrieve relevant chunks from the knowledge base using vector search.

    Single responsibility: Execute retrieve() strictly without generation.
    Also augments context with relevant active memories from the persistent store,
    keeping enterprise RAG collections strictly read-only, and wraps chunks in untrusted XML tags.
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
        chunks = wrap_untrusted_context(raw_chunks)
    except Exception as exc:
        logger.error(f"Error during context retrieval: {exc}", exc_info=True)
        chunks = []

    # Augment with active relevant memories
    active_memories: List[Dict[str, Any]] = []
    try:
        found_mems = memory_store.search_memories(question, limit=3)
        for m in found_mems:
            active_memories.append(m.model_dump())
            chunks.append(
                {
                    "source_document": f"memory:{m.category.value}",
                    "section": f"operational_rule:{m.entity_key}",
                    "text": m.content,
                    "is_memory": True,
                }
            )
    except Exception as exc:
        logger.error(f"Error searching active memories: {exc}", exc_info=True)

    trace = _record_step(
        state.get("trace", []),
        node_name="retrieve_context",
        start_time=t0,
        summary={
            "retrieved_count": len(chunks),
            "memories_count": len(active_memories),
            "sources": list(
                {c.get("source_document") for c in chunks if c.get("source_document")}
            ),
        },
    )

    return {
        "context": chunks,
        "relevant_memories": active_memories,
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
    proposal_decision = state.get("proposal_decision")
    thread_id = state.get("thread_id", "")

    result = execute_mcp_incident_query(question)
    raw_message = result.message

    if proposal_decision and proposal_decision.get("confirmation_note"):
        raw_message = f"{proposal_decision['confirmation_note']}\n\n{raw_message}"

    # Output guardrail validation
    answer, _ = validate_agent_output(raw_message)

    # Self-evaluation for memorable incident patterns
    new_proposal = None
    if thread_id and question:
        has_pending = memory_store.get_pending_proposal(thread_id) is not None
        eval_result = memory_evaluator.evaluate(
            message=question,
            thread_id=thread_id,
            has_pending_proposal=has_pending,
        )
        if eval_result.is_memorable and eval_result.proposal:
            if memory_store.set_pending_proposal(thread_id, eval_result.proposal):
                new_proposal = eval_result.proposal.model_dump()
                answer = f"{answer}\n\n---\n{eval_result.proposal.prompt_question}"

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
            "has_new_proposal": new_proposal is not None,
        },
    )

    return {
        "answer": answer,
        "source_route": "incident_tool",
        "tool_used": "incidents",
        "tool_result": result.to_dict(),
        "new_proposal": new_proposal,
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
    proposal_decision = state.get("proposal_decision")
    thread_id = state.get("thread_id", "")

    result = execute_mcp_inventory_query(question)
    raw_message = result.message

    if proposal_decision and proposal_decision.get("confirmation_note"):
        raw_message = f"{proposal_decision['confirmation_note']}\n\n{raw_message}"

    # Output guardrail validation
    answer, _ = validate_agent_output(raw_message)

    # Self-evaluation for memorable context
    new_proposal = None
    if thread_id and question:
        has_pending = memory_store.get_pending_proposal(thread_id) is not None
        eval_result = memory_evaluator.evaluate(
            message=question,
            thread_id=thread_id,
            has_pending_proposal=has_pending,
        )
        if eval_result.is_memorable and eval_result.proposal:
            if memory_store.set_pending_proposal(thread_id, eval_result.proposal):
                new_proposal = eval_result.proposal.model_dump()
                answer = f"{answer}\n\n---\n{eval_result.proposal.prompt_question}"

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
            "has_new_proposal": new_proposal is not None,
        },
    )

    return {
        "answer": answer,
        "source_route": "inventory_tool",
        "tool_used": "inventory",
        "tool_result": result.to_dict(),
        "new_proposal": new_proposal,
        "trace": trace,
    }


def generate_answer_node(state: AgentState) -> Dict[str, Any]:
    """Node: Synthesize final answer grounded on the pre-retrieved context and apply Output Guardrails.

    Single responsibility: Invoke generate_answer(question, context) with
    the exact context produced by retrieve_context. Also evaluates interaction
    for memorable operational facts and issues user-facing proposals.
    """
    t0 = time.perf_counter()
    question = state.get("question", "")
    context = state.get("context", [])
    thread_id = state.get("thread_id", "")
    proposal_decision = state.get("proposal_decision")

    # If direct answer was already formulated in receive_question
    if state.get("answer"):
        raw_answer = state.get("answer", "")
    else:
        raw_answer = generate_answer(question=question, context=context)
        if proposal_decision and proposal_decision.get("confirmation_note"):
            raw_answer = f"{proposal_decision['confirmation_note']}\n\n{raw_answer}"

    # Validate output through output guardrails (structural, prompt leak, sensitive data)
    final_answer, output_guard_result = validate_agent_output(raw_answer)

    # Self-evaluation for new memorable context (only if valid output)
    new_proposal = None
    if output_guard_result.passed and thread_id and question:
        has_pending = memory_store.get_pending_proposal(thread_id) is not None
        eval_result = memory_evaluator.evaluate(
            message=question,
            thread_id=thread_id,
            has_pending_proposal=has_pending,
        )
        if eval_result.is_memorable and eval_result.proposal:
            success = memory_store.set_pending_proposal(thread_id, eval_result.proposal)
            if success:
                new_proposal = eval_result.proposal.model_dump()
                final_answer = f"{final_answer}\n\n---\n{eval_result.proposal.prompt_question}"

    trace = _record_step(
        state.get("trace", []),
        node_name="generate_answer_node",
        start_time=t0,
        summary={
            "context_chunks_used": len(context),
            "answer_preview": (
                final_answer[:80] + "..." if len(final_answer) > 80 else final_answer
            ),
            "has_new_proposal": new_proposal is not None,
            "output_guard_action": output_guard_result.action.value,
            "output_guard_passed": output_guard_result.passed,
        },
    )

    return {
        "answer": final_answer,
        "new_proposal": new_proposal,
        "trace": trace,
    }


def handle_no_context(state: AgentState) -> Dict[str, Any]:
    """Node: Provide honest consultative fallback when no qualifying context is found.

    Single responsibility: Prevent hallucination on empty retrieval by explicitly
    communicating lack of data and directing to the appropriate human team.
    """
    t0 = time.perf_counter()
    question = state.get("question", "")
    thread_id = state.get("thread_id", "")
    answer = NO_CONTEXT_MESSAGE

    new_proposal = None
    if thread_id and question:
        has_pending = memory_store.get_pending_proposal(thread_id) is not None
        eval_result = memory_evaluator.evaluate(
            message=question,
            thread_id=thread_id,
            has_pending_proposal=has_pending,
        )
        if eval_result.is_memorable and eval_result.proposal:
            if memory_store.set_pending_proposal(thread_id, eval_result.proposal):
                new_proposal = eval_result.proposal.model_dump()
                answer = f"{answer}\n\n---\n{eval_result.proposal.prompt_question}"

    trace = _record_step(
        state.get("trace", []),
        node_name="handle_no_context",
        start_time=t0,
        summary={
            "action": "fallback_no_context",
            "message": "Honest admittance of missing documentation",
            "has_new_proposal": new_proposal is not None,
        },
    )

    return {
        "answer": answer,
        "new_proposal": new_proposal,
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
