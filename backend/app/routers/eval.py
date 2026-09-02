"""DocMind RAG Evaluation API Router.

Provides endpoints to evaluate RAG retrieval precision/recall, lexical faithfulness,
and answer relevance deterministically without external LLM judges.
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.rag_evaluator import (
    evaluate_rag_turn,
    evaluate_rag_batch,
    calculate_chunk_recall,
    calculate_chunk_precision,
    calculate_lexical_faithfulness,
    calculate_answer_relevance,
)

logger = logging.getLogger("docmind.eval")

router = APIRouter(prefix="/api/eval", tags=["evaluation"])


class RAGEvalTurnRequest(BaseModel):
    query: str = Field(..., description="User question / prompt")
    answer: str = Field(..., description="Generated answer string")
    context_chunks: List[str] = Field(
        default_factory=list, description="Retrieved context chunks used for generation"
    )
    retrieved_chunk_ids: List[str] = Field(
        default_factory=list, description="IDs of retrieved chunks"
    )
    ground_truth_chunk_ids: Optional[List[str]] = Field(
        default=None, description="Known ground truth relevant chunk IDs (optional)"
    )


class RAGEvalResponse(BaseModel):
    chunk_recall: Optional[float] = Field(
        default=None, description="Proportion of ground-truth chunks retrieved"
    )
    chunk_precision: Optional[float] = Field(
        default=None, description="Proportion of retrieved chunks that are relevant"
    )
    lexical_faithfulness: float = Field(
        ..., description="Lexical grounding score of the answer in context"
    )
    answer_relevance: float = Field(
        ..., description="Keyword and overlap relevance score of answer to query"
    )
    overall_score: float = Field(
        ..., description="Weighted composite score between 0.0 and 1.0"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Diagnostic and metadata details"
    )


class RAGEvalBatchRequest(BaseModel):
    turns: List[RAGEvalTurnRequest] = Field(
        ..., description="List of RAG turns to evaluate in batch"
    )


class RAGEvalBatchResponse(BaseModel):
    total_turns: int
    mean_recall: Optional[float] = None
    mean_precision: Optional[float] = None
    mean_faithfulness: float
    mean_relevance: float
    mean_overall_score: float
    results: List[RAGEvalResponse]


@router.get("/health")
async def eval_health():
    """Health check endpoint for the evaluation router."""
    return {
        "status": "online",
        "service": "rag_evaluator",
        "mode": "deterministic_offline",
    }


@router.post("/rag", response_model=RAGEvalResponse)
async def evaluate_rag_turn_endpoint(request: RAGEvalTurnRequest):
    """Evaluate a single RAG turn with deterministic offline metrics."""
    try:
        result = evaluate_rag_turn(
            query=request.query,
            answer=request.answer,
            context_chunks=request.context_chunks,
            retrieved_chunk_ids=request.retrieved_chunk_ids,
            ground_truth_chunk_ids=request.ground_truth_chunk_ids,
        )
        return RAGEvalResponse(**result)
    except Exception as e:
        logger.error(f"Error evaluating RAG turn: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate RAG turn: {str(e)}",
        )


@router.post("/rag/batch", response_model=RAGEvalBatchResponse)
async def evaluate_rag_batch_endpoint(request: RAGEvalBatchRequest):
    """Evaluate a batch of RAG turns and return aggregated metrics."""
    try:
        turns_data = [turn.model_dump() for turn in request.turns]
        batch_result = evaluate_rag_batch(turns_data)
        return RAGEvalBatchResponse(**batch_result)
    except Exception as e:
        logger.error(f"Error evaluating RAG batch: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate RAG batch: {str(e)}",
        )
