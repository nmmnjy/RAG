from __future__ import annotations

from app.schemas.answer_generation import (
    AnswerGenerationRequest,
    AnswerGenerationResult,
    LLMGenerateRequest,
)
from app.schemas.retrieval import HybridRetrieveHit
from app.services.citation_builder import CitationBuilder
from app.services.llm_provider import LLMProvider, MockLLMProvider
from app.services.refusal_policy import RefusalPolicy


class AnswerGenerationService:
    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        citation_builder: CitationBuilder | None = None,
        refusal_policy: RefusalPolicy | None = None,
    ) -> None:
        self._llm_provider = llm_provider or MockLLMProvider()
        self._citation_builder = citation_builder or CitationBuilder()
        self._refusal_policy = refusal_policy or RefusalPolicy()

    def generate(self, request: AnswerGenerationRequest) -> AnswerGenerationResult:
        sorted_hits = sorted(
            request.retrieval_result.hits,
            key=lambda item: item.score_final,
            reverse=True,
        )
        selected_hits = sorted_hits[: request.max_context_chunks]

        refusal = self._refusal_policy.evaluate(
            selected_hits,
            min_score_threshold=request.min_score_threshold,
            min_evidence_chunks=request.min_evidence_chunks,
        )
        if refusal.should_refuse:
            return AnswerGenerationResult(
                answer=request.refusal_answer_text,
                citations=[],
                confidence=0.0,
                refuse_reason=refusal.refuse_reason,
                debug={"selected_hit_count": len(selected_hits)},
            )

        context_blocks = self._build_context_blocks(selected_hits)
        llm_output = self._llm_provider.generate(
            LLMGenerateRequest(query_text=request.query_text, context_blocks=context_blocks)
        )
        citations = self._citation_builder.build(selected_hits)

        confidence = self._compute_confidence(selected_hits, llm_output.confidence_hint)
        return AnswerGenerationResult(
            answer=llm_output.answer_text,
            citations=citations,
            confidence=confidence,
            refuse_reason=None,
            debug={
                "selected_hit_count": len(selected_hits),
                "provider_name": self._llm_provider.provider_name,
                "model_name": self._llm_provider.model_name,
            },
        )

    @staticmethod
    def _build_context_blocks(hits: list[HybridRetrieveHit]) -> list[str]:
        blocks: list[str] = []
        for index, hit in enumerate(hits, start=1):
            section = " / ".join(hit.section_path) if hit.section_path else "-"
            blocks.append(
                f"[C{index}] doc_id={hit.doc_id}; chunk_id={hit.chunk_id}; "
                f"section={section}; content={hit.content}"
            )
        return blocks

    @staticmethod
    def _compute_confidence(hits: list[HybridRetrieveHit], confidence_hint: float) -> float:
        if not hits:
            return 0.0
        top_score = max(hit.score_final for hit in hits)
        blended = (top_score * 0.7) + (confidence_hint * 0.3)
        return max(0.0, min(1.0, round(blended, 4)))
