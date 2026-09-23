"""Evaluation suite for TrackFlow LangGraph support agent.

Evaluates graph execution traces, conditional edge routing, checkpointing,
and grounding against TrackFlow company knowledge base.
"""

from __future__ import annotations

import pytest

from data.pipelines.rag import NO_CONTEXT_MESSAGE
from services.agent import (
    compile_agent_graph,
    get_compiled_agent,
    run_support_agent,
    trace_store,
)


class TestAgentEvals:
    """Agent evaluations asserting verifiable criteria on execution traces and answers."""

    def test_eval_trace_node_order_and_execution_sequence(self):
        """Eval 1: Verifies node execution order on trace for standard queries.

        Criterion: For a valid query with existing context, the node sequence must be
        strictly ['receive_question', 'retrieve_context', 'generate_answer_node'].
        retrieve_context MUST precede generation, and each step must record metrics.
        """
        question = "¿Cuál es el SLA comprometido de entrega estándar?"
        result = run_support_agent(question=question)

        # 1. Verify trace registration in trace store
        run_id = result["run_id"]
        stored_trace = trace_store.get_trace(run_id)
        assert stored_trace is not None, f"Trace was not persisted for run_id {run_id}"

        # 2. Assert verifiable criteria on the execution sequence
        nodes = stored_trace.nodes_executed
        assert nodes == [
            "receive_question",
            "retrieve_context",
            "generate_answer_node",
        ], f"Unexpected execution sequence: {nodes}"

        # 3. Assert retrieve_context executes strictly before generate_answer_node
        retrieve_idx = nodes.index("retrieve_context")
        gen_idx = nodes.index("generate_answer_node")
        assert retrieve_idx < gen_idx, "retrieve_context did not execute before generate_answer_node"

        # 4. Assert individual step trace payload integrity
        steps = stored_trace.steps
        assert len(steps) == 3
        assert steps[0]["node"] == "receive_question"
        assert steps[0]["output_summary"]["is_valid"] is True
        assert steps[1]["node"] == "retrieve_context"
        assert steps[1]["output_summary"]["retrieved_count"] > 0
        assert steps[2]["node"] == "generate_answer_node"
        assert "context_chunks_used" in steps[2]["output_summary"]
        assert stored_trace.total_duration_ms > 0

    def test_eval_conditional_edge_empty_question_bypasses_retrieval(self):
        """Eval 2: Verifies conditional edge routing on invalid/empty inputs.

        Criterion: Empty queries must be redirected to 'handle_error' and immediately
        terminate, completely bypassing 'retrieve_context' and 'generate_answer_node'.
        """
        empty_question = "     "
        result = run_support_agent(question=empty_question)

        stored_trace = trace_store.get_trace(result["run_id"])
        assert stored_trace is not None

        nodes = stored_trace.nodes_executed
        # Must only execute receive_question -> handle_error
        assert nodes == ["receive_question", "handle_error"]
        assert "retrieve_context" not in nodes
        assert "generate_answer_node" not in nodes
        assert result["is_valid"] is False
        assert "vacía" in result["answer"].lower() or "inválida" in result["answer"].lower()

    def test_eval_conditional_edge_no_context_admittance(self):
        """Eval 3: Verifies conditional routing to honest fallback when context is absent.

        Criterion: Queries yielding no qualifying chunks above min_score must route to
        'handle_no_context' and avoid ungrounded generation/hallucinations.
        """
        # Using a very high min_score threshold guarantees zero qualifying chunks
        out_of_scope_query = "¿Cuál es la receta tradicional de la paella valenciana?"
        result = run_support_agent(question=out_of_scope_query, min_score=0.99)

        stored_trace = trace_store.get_trace(result["run_id"])
        assert stored_trace is not None

        nodes = stored_trace.nodes_executed
        assert nodes == ["receive_question", "retrieve_context", "handle_no_context"]
        assert "generate_answer_node" not in nodes
        # The agent must answer with honest admittance
        assert result["answer"] == NO_CONTEXT_MESSAGE
        assert "no contiene información suficiente" in result["answer"]

    def test_eval_grounding_storage_pricing_context(self):
        """Eval 4: Verifies answer remains strictly grounded in TrackFlow knowledge base.

        Criterion: A pricing query must return exact figures defined in company docs
        (18 USD/m3 Los Angeles, 16 EUR/m3 Zaragoza) and verify context chunks were sourced.
        """
        question = "¿Cuáles son las tarifas estándar de almacenamiento por metro cúbico?"
        result = run_support_agent(question=question)

        answer = result["answer"]
        # Grounding assertions against TrackFlow business rules
        assert "18 USD" in answer
        assert "16 EUR" in answer
        assert "metro cúbico" in answer or "m³" in answer
        assert "Los Ángeles" in answer or "Los Angeles" in answer
        assert "Zaragoza" in answer

        # Check trace confirms chunks came from storage-pricing document
        context = result["context"]
        sources = [c.get("source_document") for c in context]
        assert any("storage-pricing" in str(s) for s in sources)

    def test_eval_grounding_international_returns_policy(self):
        """Eval 5: Verifies strict business constraints regarding returns policy.

        Criterion: International returns must not be described as automatic and must
        cite Sofia Ramos as required by CONTEXT and business persona rules.
        """
        question = "¿Cómo se procesan las devoluciones internacionales en TrackFlow?"
        result = run_support_agent(question=question)

        answer = result["answer"]
        assert "Sofía Ramos" in answer or "Sofia Ramos" in answer
        assert "manual" in answer.lower()

    def test_eval_checkpointing_state_persistence_and_inspection(self):
        """Eval 6: Verifies LangGraph checkpointing persists state across transitions.

        Criterion: Given a specific thread_id, the checkpointer must allow inspecting
        the exact state snapshot and history of transitions after execution.
        """
        thread_id = "eval_thread_checkpoint_test_001"
        app = get_compiled_agent()

        result = run_support_agent(
            question="¿Cuál es la ventana estándar de devolución?",
            thread_id=thread_id,
            compiled_graph=app,
        )

        assert result["thread_id"] == thread_id

        # Inspect latest checkpoint snapshot
        config = {"configurable": {"thread_id": thread_id}}
        state_snapshot = app.get_state(config)

        assert state_snapshot is not None
        assert "answer" in state_snapshot.values
        assert "30 días" in state_snapshot.values["answer"]
        assert state_snapshot.values["is_valid"] is True
        assert len(state_snapshot.values["context"]) > 0

        # Inspect state transition history
        history = list(app.get_state_history(config))
        # LangGraph saves a checkpoint at each step: START, receive, retrieve, generate, etc.
        assert len(history) >= 3, f"Expected at least 3 checkpoint transitions, got {len(history)}"

    def test_eval_graph_compilation_structural_validation(self):
        """Eval 7: Verifies graph compiles explicitly before runtime execution.

        Criterion: Compilation must return a valid CompiledStateGraph without errors.
        """
        compiled = compile_agent_graph()
        assert compiled is not None
        assert hasattr(compiled, "invoke")
        assert hasattr(compiled, "get_state")
