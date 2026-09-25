"""Evaluation suite for TrackFlow LangGraph external tools and autonomous routing.

Evaluates autonomous intent routing between RAG and operational tools (incidents & inventory),
typed contracts, read-only guarantees, explicit numerical timeouts, and honest fallbacks.
"""

from __future__ import annotations

from unittest.mock import patch
import pytest

from services.agent import run_support_agent, trace_store
from services.agent.tools import (
    DEFAULT_INCIDENT_TIMEOUT_SECONDS,
    DEFAULT_INVENTORY_TIMEOUT_SECONDS,
    IncidentToolOutput,
    InventoryToolOutput,
    check_inventory_stock,
    get_incident_ticket,
)


class TestAgentToolsEvals:
    """Agent evaluations verifying autonomous tool selection, execution traces, and fallbacks."""

    def test_eval_autonomous_routing_to_incident_tool(self):
        """Eval 1: Verifies autonomous routing to incident tool without explicit user directive.

        Criterion: A question asking for the status of an incident (e.g., TRF-000003) must route
        to 'incident_tool_node' and bypass the RAG retrieval flow completely.
        The answer must report live data from the incidents system (status: open).
        """
        question = "¿En qué estado se encuentra el ticket TRF-000003?"
        result = run_support_agent(question=question)

        # 1. Assert trace routing
        nodes = result["nodes_executed"]
        assert nodes == ["receive_question", "incident_tool_node"], f"Unexpected nodes: {nodes}"
        assert "retrieve_context" not in nodes, "RAG retrieve should not execute for incident queries"
        assert "generate_answer_node" not in nodes

        # 2. Assert source route and tool metadata
        assert result["source_route"] == "incident_tool"
        assert result["tool_used"] == "incidents"

        # 3. Assert live operational data is returned (not hallucinated)
        answer = result["answer"]
        assert "TRF-000003" in answer
        assert "open" in answer.lower()
        assert "carrier_last_mile" in answer

        # 4. Verify trace stored in TraceStore
        stored_trace = trace_store.get_trace(result["run_id"])
        assert stored_trace is not None
        assert stored_trace.source_route == "incident_tool"
        assert stored_trace.tool_used == "incidents"

    def test_eval_autonomous_routing_to_rag_knowledge_base(self):
        """Eval 2: Verifies autonomous routing to RAG for procedural and policy questions.

        Criterion: A question asking about company storage pricing in Zaragoza must route
        to RAG ('retrieve_context' -> 'generate_answer_node') and NOT use external tools.
        """
        question = "¿Cuáles son las tarifas de almacenamiento en Zaragoza?"
        result = run_support_agent(question=question)

        # 1. Assert trace routing
        nodes = result["nodes_executed"]
        assert nodes == [
            "receive_question",
            "retrieve_context",
            "generate_answer_node",
        ], f"Unexpected nodes for RAG query: {nodes}"
        assert "incident_tool_node" not in nodes
        assert "inventory_tool_node" not in nodes

        # 2. Assert metadata
        assert result["source_route"] == "rag"
        assert result["tool_used"] is None

        # 3. Assert answer grounding
        answer = result["answer"]
        assert "16 EUR" in answer
        assert "Zaragoza" in answer

    def test_eval_autonomous_routing_to_inventory_tool(self):
        """Eval 3: Verifies autonomous routing to inventory stock tool.

        Criterion: A question asking for available stock of a product SKU must route
        to 'inventory_tool_node' and report live stock counts.
        """
        question = "¿Tenemos stock disponible del SKU CLT-SNK-W-42?"
        result = run_support_agent(question=question)

        # 1. Assert trace routing
        nodes = result["nodes_executed"]
        assert nodes == ["receive_question", "inventory_tool_node"], f"Unexpected nodes: {nodes}"
        assert "retrieve_context" not in nodes

        # 2. Assert metadata
        assert result["source_route"] == "inventory_tool"
        assert result["tool_used"] == "inventory"

        # 3. Assert stock answer includes real SKU data
        answer = result["answer"]
        assert "CLT-SNK-W-42" in answer
        assert "unidades disponibles" in answer

    def test_eval_incident_fallback_on_nonexistent_ticket(self):
        """Eval 4: Verifies honest fallback when an incident ticket is not found.

        Criterion: If a ticket ID does not exist in the incident manager (e.g., TRF-999999),
        the agent must never invent a status and must return an honest explanation.
        """
        question = "¿Cuál es el estado del ticket TRF-999999?"
        result = run_support_agent(question=question)

        assert result["source_route"] == "incident_tool"
        assert result["tool_used"] == "incidents"
        assert result["tool_result"]["is_fallback"] is True
        assert result["tool_result"]["success"] is False

        answer = result["answer"]
        assert "no existe ningún registro" in answer.lower() or "no pude confirmar" in answer.lower()
        # Verify no fabricated status
        assert "se encuentra actualmente en estado: 'open'" not in answer
        assert "se encuentra actualmente en estado: 'resolved'" not in answer

    def test_eval_incident_tool_explicit_numeric_timeout_fallback(self):
        """Eval 5: Verifies explicit numerical timeout handling and fallback path.

        Criterion: The incident tool specifies a numerical timeout (e.g., 3.0s). If the service
        exceeds this limit or experiences a failure, the fallback route is engaged safely.
        """
        assert isinstance(DEFAULT_INCIDENT_TIMEOUT_SECONDS, (int, float))
        assert DEFAULT_INCIDENT_TIMEOUT_SECONDS == 3.0

        # Simulate timeout by injecting an ultra-low threshold
        output = get_incident_ticket("TRF-000003", timeout=0.000001)

        assert isinstance(output, IncidentToolOutput)
        # Must activate fallback due to timeout without crashing
        assert output.is_fallback is True
        assert output.success is False
        assert "tiempo de espera" in output.message.lower() or "timeout" in str(output.error).lower()

    def test_eval_inventory_tool_contract_and_fallback(self):
        """Eval 6: Verifies inventory tool typed contracts and nonexistent product fallback.

        Criterion: The inventory tool has an explicit timeout and returns a typed output
        with an honest fallback when querying an unknown product.
        """
        assert isinstance(DEFAULT_INVENTORY_TIMEOUT_SECONDS, (int, float))
        assert DEFAULT_INVENTORY_TIMEOUT_SECONDS == 3.0

        output = check_inventory_stock("producto-inexistente-aleatorio-9999")

        assert isinstance(output, InventoryToolOutput)
        assert output.success is False
        assert output.is_fallback is True
        assert "No se encontró ningún producto" in output.message
