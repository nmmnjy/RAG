from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.config import settings
from app.schemas.answer_generation import LLMGenerateRequest, LLMGenerateResult


class LLMProviderError(RuntimeError):
    pass


class LLMProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def model_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate(self, request: LLMGenerateRequest) -> LLMGenerateResult:
        raise NotImplementedError


class MockLLMProvider(LLMProvider):
    """Deterministic provider for local run and tests."""

    def __init__(self, model_name: str = "mock-qa-v1") -> None:
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(self, request: LLMGenerateRequest) -> LLMGenerateResult:
        if not request.context_blocks:
            return LLMGenerateResult(answer_text="未提供可用上下文。", confidence_hint=0.0)

        top_context = request.context_blocks[0]
        answer = (
            f"基于检索证据，关于“{request.query_text}”的结论如下："
            f"{top_context[:180]}"
        )
        return LLMGenerateResult(answer_text=answer, confidence_hint=0.68)


class OpenAICompatibleLLMProvider(LLMProvider):
    """
    Real-provider integration slot.
    Current stage provides boundary checks and explicit error paths only.
    """

    def __init__(
        self,
        *,
        model_name: str,
        api_key: str,
        base_url: str,
        request_timeout_ms: int,
    ) -> None:
        self._model_name = model_name
        self._api_key = api_key
        self._base_url = base_url
        self._request_timeout_ms = request_timeout_ms

    @property
    def provider_name(self) -> str:
        return "openai_compatible"

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(self, request: LLMGenerateRequest) -> LLMGenerateResult:
        if not self._api_key:
            raise LLMProviderError("LLM provider is missing api key.")
        if not self._base_url:
            raise LLMProviderError("LLM provider is missing base url.")
        raise LLMProviderError(
            "Real LLM invocation is not implemented in current stage. "
            "Please wire HTTP client in OpenAICompatibleLLMProvider.generate."
        )


def build_llm_provider() -> LLMProvider:
    provider_name = settings.llm_provider.strip().lower()
    if provider_name == "mock":
        return MockLLMProvider(model_name=settings.llm_model)

    if provider_name == "openai_compatible":
        if not settings.llm_provider_enable_real:
            if settings.llm_provider_fallback_to_mock:
                return MockLLMProvider(model_name=settings.llm_model)
            raise LLMProviderError(
                "LLM provider selected openai_compatible but LLM_PROVIDER_ENABLE_REAL is false."
            )
        return OpenAICompatibleLLMProvider(
            model_name=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            request_timeout_ms=settings.llm_request_timeout_ms,
        )

    if settings.llm_provider_fallback_to_mock:
        return MockLLMProvider(model_name=settings.llm_model)
    raise LLMProviderError(f"Unsupported llm provider: {settings.llm_provider}")
