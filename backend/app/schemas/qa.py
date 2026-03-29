from __future__ import annotations

from pydantic import BaseModel, Field


class QAAnswerRequest(BaseModel):
    kb_id: str
    query_text: str = Field(min_length=1)
    doc_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=100)
    vector_top_k: int = Field(default=20, ge=1, le=100)
    keyword_top_k: int = Field(default=20, ge=1, le=100)
    enable_rerank: bool = False
    max_context_chunks: int = Field(default=5, ge=1, le=20)
    min_score_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    min_evidence_chunks: int = Field(default=1, ge=1, le=20)
