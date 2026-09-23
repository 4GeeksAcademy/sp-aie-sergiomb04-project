"""Conditional routing edges for TrackFlow LangGraph support agent."""

from __future__ import annotations

import logging
from services.agent.state import AgentState

logger = logging.getLogger("trackflow.agent.edges")


def route_after_receive(state: AgentState) -> str:
    """Conditional edge: Route based on question validation.

    If question is empty or invalid -> handle_error.
    If question is valid -> retrieve_context.
    """
    is_valid = state.get("is_valid", False)
    if is_valid:
        logger.debug("Question valid: routing to retrieve_context")
        return "retrieve_context"

    logger.debug("Question invalid: routing to handle_error")
    return "handle_error"


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
