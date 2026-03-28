from __future__ import annotations

from pydantic import BaseModel

from app.schemas.retrieval import HybridRetrieveHit


class RefusalDecision(BaseModel):
    should_refuse: bool
    refuse_reason: str | None = None


class RefusalPolicy:
    """Basic refusal rules for evidence-grounded answering."""

    def evaluate(
        self,
        hits: list[HybridRetrieveHit],
        *,
        min_score_threshold: float,
        min_evidence_chunks: int,
    ) -> RefusalDecision:
        if not hits:
            return RefusalDecision(should_refuse=True, refuse_reason="QA_CONTEXT_EMPTY")

        evidence_hits = [item for item in hits if item.score_final >= min_score_threshold]
        if len(evidence_hits) < min_evidence_chunks:
            return RefusalDecision(should_refuse=True, refuse_reason="QA_EVIDENCE_INSUFFICIENT")

        return RefusalDecision(should_refuse=False, refuse_reason=None)
