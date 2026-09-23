"""Graph compilation and execution pipeline for TrackFlow LangGraph support agent."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from services.agent.edges import route_after_receive, route_after_retrieve
from services.agent.nodes import (
    generate_answer_node,
    handle_error,
    handle_no_context,
    receive_question,
    retrieve_context,
)
from services.agent.state import AgentState
from services.agent.tracing import AgentRunTrace, trace_store

logger = logging.getLogger("trackflow.agent.graph")

# Module-level default checkpointer and compiled graph instance
default_checkpointer = MemorySaver()
_compiled_agent: Optional[CompiledStateGraph] = None


def build_agent_graph() -> StateGraph:
    """Build the state graph with explicit nodes, edges and conditions.

    Does not compile the graph; provides the raw StateGraph definition
    to allow inspection or custom checkpointers.
    """
    workflow = StateGraph(AgentState)

    # 1. Register single-responsibility nodes
    workflow.add_node("receive_question", receive_question)
    workflow.add_node("retrieve_context", retrieve_context)
    workflow.add_node("generate_answer_node", generate_answer_node)
    workflow.add_node("handle_no_context", handle_no_context)
    workflow.add_node("handle_error", handle_error)

    # 2. Register flow entrypoint
    workflow.add_edge(START, "receive_question")

    # 3. Register conditional edges with explicit branches
    workflow.add_conditional_edges(
        "receive_question",
        route_after_receive,
        {
            "retrieve_context": "retrieve_context",
            "handle_error": "handle_error",
        },
    )

    workflow.add_conditional_edges(
        "retrieve_context",
        route_after_retrieve,
        {
            "generate_answer_node": "generate_answer_node",
            "handle_no_context": "handle_no_context",
        },
    )

    # 4. Register terminal transitions
    workflow.add_edge("generate_answer_node", END)
    workflow.add_edge("handle_no_context", END)
    workflow.add_edge("handle_error", END)

    return workflow


def compile_agent_graph(
    checkpointer: Optional[BaseCheckpointSaver] = None,
) -> CompiledStateGraph:
    """Compile the state graph with a checkpointer for runtime execution.

    Fails early and explicitly if there are structural errors in the graph.
    """
    saver = checkpointer if checkpointer is not None else default_checkpointer
    workflow = build_agent_graph()
    try:
        compiled = workflow.compile(checkpointer=saver)
        logger.info("Successfully compiled TrackFlow LangGraph support agent.")
        return compiled
    except Exception as exc:
        logger.critical(f"Fatal error compiling LangGraph support agent: {exc}", exc_info=True)
        raise RuntimeError(f"Structural error in agent graph definition: {exc}") from exc


def get_compiled_agent(
    checkpointer: Optional[BaseCheckpointSaver] = None,
    force_recompile: bool = False,
) -> CompiledStateGraph:
    """Return singleton compiled agent instance or create new one."""
    global _compiled_agent
    if _compiled_agent is None or force_recompile or checkpointer is not None:
        compiled = compile_agent_graph(checkpointer=checkpointer)
        if checkpointer is None:
            _compiled_agent = compiled
        return compiled
    return _compiled_agent


def run_support_agent(
    question: str,
    *,
    thread_id: Optional[str] = None,
    k: Optional[int] = None,
    min_score: Optional[float] = None,
    collection_name: Optional[str] = None,
    checkpointer: Optional[BaseCheckpointSaver] = None,
    compiled_graph: Optional[CompiledStateGraph] = None,
) -> Dict[str, Any]:
    """Execute the compiled LangGraph support agent and record structured trace.

    Args:
        question: User query to process.
        thread_id: Conversation thread ID for checkpointing and state tracking.
        k: Maximum number of context chunks to retrieve.
        min_score: Minimum similarity score filter.
        collection_name: Vector store collection name.
        checkpointer: Custom checkpointer instance if not using default.
        compiled_graph: Custom precompiled graph instance if provided.

    Returns:
        Dictionary with answer, thread_id, run_id, nodes_executed, trace and context.
    """
    t_start = time.perf_counter()
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    active_thread_id = thread_id or f"thread_{uuid.uuid4().hex[:12]}"

    app = compiled_graph or get_compiled_agent(checkpointer=checkpointer)

    initial_state: AgentState = {
        "question": question,
        "is_valid": False,
        "context": [],
        "answer": "",
        "error": None,
        "trace": [],
        "k": k,
        "min_score": min_score,
        "collection_name": collection_name,
    }

    config = {"configurable": {"thread_id": active_thread_id}}

    try:
        final_state = app.invoke(initial_state, config=config)
        total_duration = (time.perf_counter() - t_start) * 1000.0

        trace_steps = final_state.get("trace", [])
        nodes_executed = [s.get("node") for s in trace_steps if s.get("node")]

        # Persist structured trace
        agent_trace = AgentRunTrace(
            run_id=run_id,
            thread_id=active_thread_id,
            question=question,
            nodes_executed=nodes_executed,
            steps=trace_steps,
            answer=final_state.get("answer", ""),
            error=final_state.get("error"),
            total_duration_ms=round(total_duration, 2),
        )
        trace_store.save_trace(agent_trace)

        return {
            "answer": final_state.get("answer", ""),
            "thread_id": active_thread_id,
            "run_id": run_id,
            "is_valid": final_state.get("is_valid", False),
            "nodes_executed": nodes_executed,
            "error": final_state.get("error"),
            "context": final_state.get("context", []),
            "trace": trace_steps,
            "duration_ms": round(total_duration, 2),
        }
    except Exception as exc:
        logger.error(f"Unexpected error executing agent run_id={run_id}: {exc}", exc_info=True)
        total_duration = (time.perf_counter() - t_start) * 1000.0
        safe_error_msg = "Error interno procesando la consulta en el agente de soporte."

        error_trace = AgentRunTrace(
            run_id=run_id,
            thread_id=active_thread_id,
            question=question,
            nodes_executed=[],
            steps=[],
            answer=safe_error_msg,
            error=str(exc),
            total_duration_ms=round(total_duration, 2),
        )
        trace_store.save_trace(error_trace)

        return {
            "answer": safe_error_msg,
            "thread_id": active_thread_id,
            "run_id": run_id,
            "is_valid": False,
            "nodes_executed": [],
            "error": safe_error_msg,
            "context": [],
            "trace": [],
            "duration_ms": round(total_duration, 2),
        }
