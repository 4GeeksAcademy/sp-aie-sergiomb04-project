"""Tests for LangGraph support agent API router in services/api."""

from __future__ import annotations

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from trackflow_api.main import app

client = TestClient(app)


def test_agent_query_success():
    """Test successful query to /agent/query returning structured response."""
    with patch("trackflow_api.routes.agent.run_support_agent") as mock_agent:
        mock_agent.return_value = {
            "answer": "La ventana de devolución estándar en TrackFlow es de 30 días.",
            "thread_id": "test_thread_123",
            "run_id": "run_abc456",
            "is_valid": True,
            "nodes_executed": ["receive_question", "retrieve_context", "generate_answer_node"],
            "error": None,
            "context": [],
            "trace": [],
            "duration_ms": 45.2,
        }

        response = client.post(
            "/agent/query",
            json={"question": "¿Cuál es la ventana de devolución estándar?", "thread_id": "test_thread_123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "30 días" in data["answer"]
        assert data["thread_id"] == "test_thread_123"
        assert data["run_id"] == "run_abc456"
        assert data["nodes_executed"] == ["receive_question", "retrieve_context", "generate_answer_node"]
        assert data["is_valid"] is True
        assert data["error"] is None
        # Verify no raw tracebacks or raw chunk internals leaked in client response
        assert "Traceback" not in str(data)
        assert "_score" not in data


def test_agent_query_empty_question():
    """Test validation error when question is empty or whitespaces."""
    response = client.post(
        "/agent/query",
        json={"question": "    "},
    )
    assert response.status_code == 400
    assert "vacía" in response.json()["detail"].lower()


def test_agent_query_internal_error_handled_cleanly():
    """Test 500 error boundary: returns clean message without raw stack trace."""
    with patch(
        "trackflow_api.routes.agent.run_support_agent",
        side_effect=RuntimeError("Unexpected lower level failure in Qdrant/LangGraph"),
    ):
        response = client.post(
            "/agent/query",
            json={"question": "¿Cuál es la tarifa de almacenamiento?"},
        )
        assert response.status_code == 500
        detail = response.json()["detail"]
        assert "Error interno procesando la consulta" in detail
        # Ensure raw stack trace is never leaked
        assert "Traceback" not in detail
        assert "Unexpected lower level failure" not in detail


def test_agent_get_trace_success():
    """Test retrieval of structured trace via GET /agent/traces/{run_id}."""
    from services.agent.tracing import AgentRunTrace, trace_store

    sample_trace = AgentRunTrace(
        run_id="run_test_trace_1",
        thread_id="thread_test_1",
        question="¿SLA de entrega?",
        nodes_executed=["receive_question", "retrieve_context", "generate_answer_node"],
        steps=[
            {
                "node": "receive_question",
                "timestamp": "2026-09-23T12:00:00Z",
                "duration_ms": 1.2,
                "output_summary": {"is_valid": True},
            }
        ],
        answer="SLA del 90%",
        total_duration_ms=15.4,
    )
    trace_store.save_trace(sample_trace)

    response = client.get("/agent/traces/run_test_trace_1")
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == "run_test_trace_1"
    assert data["nodes_executed"] == ["receive_question", "retrieve_context", "generate_answer_node"]
    assert len(data["steps"]) == 1


def test_agent_get_trace_not_found():
    """Test 404 response for nonexistent run_id."""
    response = client.get("/agent/traces/nonexistent_run_id")
    assert response.status_code == 404
    assert "No se encontró trace" in response.json()["detail"]
