"""Conditional routing edges for TrackFlow LangGraph support agent."""

from __future__ import annotations

import logging
import re
from services.agent.state import AgentState

logger = logging.getLogger("trackflow.agent.edges")


def is_incident_query(question: str) -> bool:
    """Detect if question is asking about a specific incident/ticket."""
    q_lower = question.lower()

    # Pattern for ticket identifiers: TRF-000001, ticket 123, #123, UUID
    if re.search(r"trf-\d{3,6}", q_lower) or re.search(r"(?:ticket|incidente|caso|reclamación|reclamacion)\s*#?\s*\d+", q_lower):
        return True

    # General phrases referring to tickets or incidents status
    ticket_indicators = [
        "estado del ticket",
        "estado de mi ticket",
        "estado de la incidencia",
        "estado del incidente",
        "consultar ticket",
        "consultar incidente",
        "mi ticket",
        "ticket número",
        "ticket numero",
    ]
    return any(indicator in q_lower for indicator in ticket_indicators)


def is_inventory_query(question: str) -> bool:
    """Detect if question is asking about inventory stock / product availability."""
    q_lower = question.lower()

    # Pattern for SKU format (e.g., CLT-SNK-W-42, TEC-EAR-001)
    if re.search(r"[a-z]{3}-[a-z]{3}-[a-z0-9\-]+", q_lower):
        return True

    inventory_indicators = [
        "stock",
        "existencias",
        "unidades disponibles",
        "cuántas unidades",
        "cuantas unidades",
        "cantidad disponible",
        "tenemos stock",
        "hay stock",
        "stock disponible",
        "quedan en almacén",
        "quedan en almacen",
    ]
    return any(indicator in q_lower for indicator in inventory_indicators)


def route_after_receive(state: AgentState) -> str:
    """Conditional edge: Route autonomously based on question content.

    Decides dynamically between:
    - handle_error: if query is empty or invalid
    - incident_tool_node: if query is an operational ticket inquiry
    - inventory_tool_node: if query is an operational stock inquiry
    - retrieve_context: for procedural, policy, SLA and commercial knowledge (RAG)
    """
    if not state.get("is_valid", False):
        logger.debug("Question invalid: routing to handle_error")
        return "handle_error"

    question = state.get("question", "")

    if is_incident_query(question):
        logger.info("Autonomously routing question to incident_tool_node: %s", question)
        return "incident_tool_node"

    if is_inventory_query(question):
        logger.info("Autonomously routing question to inventory_tool_node: %s", question)
        return "inventory_tool_node"

    logger.info("Autonomously routing question to retrieve_context (RAG): %s", question)
    return "retrieve_context"


def route_after_retrieve(state: AgentState) -> str:
    """Conditional edge: Route based on retrieval context availability.

    If qualifying context chunks were found -> generate_answer_node.
    If no context chunks survived threshold -> handle_no_context.
    """
    context = state.get("context", [])
    if context and len(context) > 0:
        logger.debug(f"Retrieved {len(context)} chunks: routing to generate_answer_node")
        return "generate_answer_node"

    logger.debug("No context chunks found: routing to handle_no_context")
    return "handle_no_context"
