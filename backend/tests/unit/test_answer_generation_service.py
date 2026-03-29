import pytest

from app.schemas.answer_generation import AnswerGenerationRequest
from app.schemas.retrieval import HybridRetrieveHit, HybridRetrieveResult
from app.services.answer_generation_service import AnswerGenerationService
from app.services.llm_provider import LLMProvider, LLMProviderError


def _build_retrieval_result(*, score_final: float = 0.78) -> HybridRetrieveResult:
    return HybridRetrieveResult(
        kb_id="kb_01",
        query_text="RAG 如何做溯源",
        top_k=3,
        hits=[
            HybridRetrieveHit(
                chunk_id="chunk_01",
                doc_id="doc_01",
                kb_id="kb_01",
                content="答案生成必须绑定 citation，确保前端可追溯。",
                section_path=["规范", "问答"],
                score_vector=0.8,
                score_keyword=0.7,
                score_final=score_final,
                citation={
                    "source": "specs/qa.md",
                    "chunk_id": "chunk_01",
                    "doc_id": "doc_01",
                },
                metadata={"lang": "zh"},
            )
        ],
        debug={},
    )


def test_answer_generation_should_return_stable_fields() -> None:
    service = AnswerGenerationService()
    request = AnswerGenerationRequest(
        kb_id="kb_01",
        query_text="RAG 如何做溯源",
        retrieval_result=_build_retrieval_result(),
    )

    result = service.generate(request)
    payload = result.model_dump()

    assert payload["answer"]
    assert payload["citations"]
    assert isinstance(payload["confidence"], float)
    assert payload["refuse_reason"] is None


def test_answer_generation_should_refuse_when_evidence_is_insufficient() -> None:
    service = AnswerGenerationService()
    request = AnswerGenerationRequest(
        kb_id="kb_01",
        query_text="RAG 如何做溯源",
        retrieval_result=_build_retrieval_result(score_final=0.1),
        min_score_threshold=0.5,
    )

    result = service.generate(request)
    assert result.answer
    assert result.citations == []
    assert result.confidence == 0.0
    assert result.refuse_reason == "QA_EVIDENCE_INSUFFICIENT"


def test_answer_generation_should_refuse_when_no_hits() -> None:
    service = AnswerGenerationService()
    request = AnswerGenerationRequest(
        kb_id="kb_01",
        query_text="RAG 如何做溯源",
        retrieval_result=HybridRetrieveResult(
            kb_id="kb_01",
            query_text="RAG 如何做溯源",
            top_k=3,
            hits=[],
            debug={},
        ),
    )

    result = service.generate(request)
    assert result.answer
    assert result.citations == []
    assert result.confidence == 0.0
    assert result.refuse_reason == "QA_CONTEXT_EMPTY"


class _FailingLLMProvider(LLMProvider):
    @property
    def provider_name(self) -> str:
        return "failing"

    @property
    def model_name(self) -> str:
        return "failing-v1"

    def generate(self, request):  # noqa: ANN001
        raise LLMProviderError("synthetic llm error")


def test_answer_generation_should_fallback_to_mock_when_provider_failed() -> None:
    service = AnswerGenerationService(
        llm_provider=_FailingLLMProvider(),
        allow_provider_fallback_to_mock=True,
    )
    request = AnswerGenerationRequest(
        kb_id="kb_01",
        query_text="RAG 如何做溯源",
        retrieval_result=_build_retrieval_result(),
    )

    result = service.generate(request)
    assert result.answer
    assert result.citations
    assert result.confidence > 0
    assert result.refuse_reason is None
    assert result.debug.get("provider_fallback_to") == "mock"


def test_answer_generation_should_raise_when_provider_failed_and_no_fallback() -> None:
    service = AnswerGenerationService(
        llm_provider=_FailingLLMProvider(),
        allow_provider_fallback_to_mock=False,
    )
    request = AnswerGenerationRequest(
        kb_id="kb_01",
        query_text="RAG 如何做溯源",
        retrieval_result=_build_retrieval_result(),
    )

    with pytest.raises(LLMProviderError):
        service.generate(request)
