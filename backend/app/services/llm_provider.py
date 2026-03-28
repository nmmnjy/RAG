from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.answer_generation import LLMGenerateRequest, LLMGenerateResult


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
