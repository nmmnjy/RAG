from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.retrieval import HybridRetrieveResult


class AnswerCitation(BaseModel):
    """Frontend-consumable citation item derived from module-04 retrieval hit."""

    citation_id: str
    chunk_id: str
    doc_id: str
    kb_id: str
    section_path: list[str] = Field(default_factory=list)
    snippet: str
    score_final: float
    source: str | None = None
    citation: dict[str, Any] = Field(default_factory=dict)


class AnswerGenerationRequest(BaseModel):
    kb_id: str
    query_text: str
    retrieval_result: HybridRetrieveResult
    max_context_chunks: int = Field(default=5, ge=1, le=20)
    min_score_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    min_evidence_chunks: int = Field(default=1, ge=1, le=20)
    refusal_answer_text: str = "抱歉，我当前无法基于现有检索证据可靠回答这个问题。"


class AnswerGenerationResult(BaseModel):
    answer: str
    citations: list[AnswerCitation] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    refuse_reason: str | None = None
    debug: dict[str, Any] = Field(default_factory=dict)


class LLMGenerateRequest(BaseModel):
    query_text: str
    context_blocks: list[str] = Field(default_factory=list)
    instructions: str = (
        "请严格依据提供的上下文回答。若证据不足，请明确说明无法回答，不要编造。"
    )


class LLMGenerateResult(BaseModel):
    answer_text: str
    confidence_hint: float = Field(default=0.5, ge=0.0, le=1.0)
