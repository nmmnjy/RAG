from pathlib import Path

from app.core.config import Settings
from app.repositories.vector_repository import InMemoryVectorRepository
from app.schemas.answer_generation import LLMGenerateRequest, LLMGenerateResult
from app.services.embedding_provider import EmbeddingProvider
from app.services.llm_provider import LLMProvider, LLMProviderError
from app.services.offline_evaluator import OfflineEvaluator
from app.services.vector_access_factory import VectorAccessRuntime
from app.services.vector_store_service import VectorStoreService
from app.services.vectorization_service import VectorizationService


class _FakeRealEmbeddingProvider(EmbeddingProvider):
    @property
    def provider_name(self) -> str:
        return "openai_compatible"

    @property
    def model_name(self) -> str:
        return "text-embedding-real"

    @property
    def embedding_dim(self) -> int:
        return 8

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.2] * self.embedding_dim for _ in texts]


class _FakeFallbackEmbeddingProvider(_FakeRealEmbeddingProvider):
    @property
    def provider_name(self) -> str:
        return "mock"


class _FakeRealLLMProvider(LLMProvider):
    @property
    def provider_name(self) -> str:
        return "openai_compatible"

    @property
    def model_name(self) -> str:
        return "gpt-real"

    def generate(self, request: LLMGenerateRequest) -> LLMGenerateResult:
        return LLMGenerateResult(
            answer_text=f"真实链路回答：{request.context_blocks[0] if request.context_blocks else ''}",
            confidence_hint=0.7,
        )


class _FakeFailingRealLLMProvider(_FakeRealLLMProvider):
    def generate(self, request: LLMGenerateRequest) -> LLMGenerateResult:
        raise LLMProviderError("forced failure for fallback test")


def _build_vector_runtime(provider: EmbeddingProvider) -> VectorAccessRuntime:
    repository = InMemoryVectorRepository()
    vectorization_service = VectorizationService(provider=provider)
    return VectorAccessRuntime(
        embedding_provider=provider,
        vector_repository=repository,
        vectorization_service=vectorization_service,
        vector_store_service=VectorStoreService(
            repository=repository,
            vectorization_service=vectorization_service,
        ),
    )


def test_offline_evaluator_should_run_sample_dataset_and_build_report() -> None:
    root_dir = Path(__file__).resolve().parents[3]
    dataset_path = root_dir / "evaluation" / "datasets" / "sample_v1" / "manifest.json"

    evaluator = OfflineEvaluator()
    dataset = evaluator.load_dataset(dataset_path=dataset_path)
    report = evaluator.run_dataset(dataset)

    assert report.dataset_id == "sample_v1"
    assert report.summary.case_count >= 1
    assert report.summary.check_count > 0
    assert report.summary.check_passed_count > 0
    assert report.gate_results
    assert report.summary.answerable_case_count >= 1
    assert report.summary.answerable_case_passed_count >= 1
    check_names = {
        check.check_name
        for case_item in report.case_reports
        for check in case_item.checks
    }
    assert "answer_evidence_hit_for_answerable" in check_names
    gate_rule_names = {item.rule_name for item in report.gate_results}
    assert "gate_answerable_evidence_hit_must_pass" in gate_rule_names


def test_offline_evaluator_real_mode_should_pass_without_fallback() -> None:
    root_dir = Path(__file__).resolve().parents[3]
    dataset_path = root_dir / "evaluation" / "datasets" / "qa_demo_v1" / "manifest.json"
    runtime_settings = Settings(
        embedding_provider="openai_compatible",
        embedding_provider_enable_real=True,
        llm_provider="openai_compatible",
        llm_provider_enable_real=True,
    )
    evaluator = OfflineEvaluator(
        runtime_settings=runtime_settings,
        llm_provider=_FakeRealLLMProvider(),
        allow_llm_fallback_to_mock=True,
        vector_runtime_builder=lambda s: _build_vector_runtime(_FakeRealEmbeddingProvider()),
    )
    dataset = evaluator.load_dataset(dataset_path=dataset_path)
    dataset.runtime_policy.declared_real_mode = True
    dataset.runtime_policy.forbid_fallback_when_real_mode = True

    report = evaluator.run_dataset(dataset)

    assert report.release_blocked is False
    provider_runtime = report.case_reports[0].output_summary["provider_runtime"]
    assert provider_runtime["embedding"]["active_provider"] == "openai_compatible"
    assert provider_runtime["llm"]["active_provider"] == "openai_compatible"
    assert provider_runtime["any_fallback_occurred"] is False


def test_offline_evaluator_real_mode_with_fallback_should_be_visible() -> None:
    root_dir = Path(__file__).resolve().parents[3]
    dataset_path = root_dir / "evaluation" / "datasets" / "qa_demo_v1" / "manifest.json"
    runtime_settings = Settings(
        embedding_provider="openai_compatible",
        embedding_provider_enable_real=True,
        llm_provider="openai_compatible",
        llm_provider_enable_real=True,
    )
    evaluator = OfflineEvaluator(
        runtime_settings=runtime_settings,
        llm_provider=_FakeFailingRealLLMProvider(),
        allow_llm_fallback_to_mock=True,
        vector_runtime_builder=lambda s: _build_vector_runtime(_FakeRealEmbeddingProvider()),
    )
    dataset = evaluator.load_dataset(dataset_path=dataset_path)
    dataset.runtime_policy.declared_real_mode = True
    dataset.runtime_policy.forbid_fallback_when_real_mode = False

    report = evaluator.run_dataset(dataset)

    assert report.release_blocked is False
    provider_runtime = report.case_reports[0].output_summary["provider_runtime"]
    assert provider_runtime["llm"]["fallback_occurred"] is True
    assert provider_runtime["llm"]["fallback_to"] == "mock"
    assert provider_runtime["fallback_visible"] is True


def test_offline_evaluator_real_mode_forbid_fallback_should_fail_gate() -> None:
    root_dir = Path(__file__).resolve().parents[3]
    dataset_path = root_dir / "evaluation" / "datasets" / "qa_demo_v1" / "manifest.json"
    runtime_settings = Settings(
        embedding_provider="openai_compatible",
        embedding_provider_enable_real=True,
        llm_provider="openai_compatible",
        llm_provider_enable_real=True,
    )
    evaluator = OfflineEvaluator(
        runtime_settings=runtime_settings,
        llm_provider=_FakeFailingRealLLMProvider(),
        allow_llm_fallback_to_mock=True,
        vector_runtime_builder=lambda s: _build_vector_runtime(_FakeRealEmbeddingProvider()),
    )
    dataset = evaluator.load_dataset(dataset_path=dataset_path)
    dataset.runtime_policy.declared_real_mode = True
    dataset.runtime_policy.forbid_fallback_when_real_mode = True

    report = evaluator.run_dataset(dataset)
    target_gate = next(item for item in report.gate_results if item.rule_name == "gate_real_mode_forbid_fallback")

    assert target_gate.passed is False
    assert report.release_blocked is True
