"""Knowledge base query router for TrackFlow RAG assistant."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

# Ensure project root is available to import data.pipelines.rag
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data.pipelines.rag import query as rag_query

logger = logging.getLogger("trackflow_api.knowledge")

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeQueryRequest(BaseModel):
    """Request payload for RAG knowledge query."""

    question: str = Field(..., min_length=1, description="Question asked by user/account manager.")


class KnowledgeQueryResponse(BaseModel):
    """Response payload containing generated answer."""

    answer: str = Field(..., description="Generated answer grounded on knowledge base context.")


@router.post(
    "/query",
    response_model=KnowledgeQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Query TrackFlow knowledge base using RAG",
)
async def query_knowledge_base(payload: KnowledgeQueryRequest) -> KnowledgeQueryResponse:
    """Answer questions regarding TrackFlow SLA, returns, carrier coverage and storage pricing.

    Orchestrates vector retrieval and LLM generation. Never returns raw chunks to the client.
    """
    clean_question = payload.question.strip()
    if not clean_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty or whitespace.",
        )

    try:
        answer = rag_query(clean_question)
        return KnowledgeQueryResponse(answer=answer)
    except Exception as exc:
        logger.error(f"Error executing knowledge query: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing knowledge base query.",
        )
