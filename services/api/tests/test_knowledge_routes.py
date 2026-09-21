"""Tests for knowledge query API router in services/api."""

from __future__ import annotations

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from trackflow_api.main import app

client = TestClient(app)


def test_knowledge_query_success():
    """Test successful query to /knowledge/query."""
    with patch("trackflow_api.routes.knowledge.rag_query") as mock_rag:
        mock_rag.return_value = "La ventana de devolución estándar es de 30 días."

        response = client.post(
            "/knowledge/query",
            json={"question": "¿Cuál es la ventana de devolución?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["answer"] == "La ventana de devolución estándar es de 30 días."
        # Never return raw chunks or scores
        assert "_score" not in data
        assert "chunks" not in data


def test_knowledge_query_empty_question():
    """Test validation error when question is empty."""
    response = client.post(
        "/knowledge/query",
        json={"question": "   "},
    )
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"].lower()


def test_knowledge_query_internal_error():
    """Test 500 handling on internal processing error."""
    with patch("trackflow_api.routes.knowledge.rag_query", side_effect=RuntimeError("Engine failure")):
        response = client.post(
            "/knowledge/query",
            json={"question": "¿Qué transportista cubre Aragón?"},
        )
        assert response.status_code == 500
        assert "Error processing knowledge base query" in response.json()["detail"]
