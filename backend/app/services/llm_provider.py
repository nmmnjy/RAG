from __future__ import annotations

from abc import ABC, abstractmethod
import json
import socket
from urllib import error, request as urllib_request

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
        payload = self._build_payload(request)
        response_payload = self._request_chat_completion(payload)
        answer_text = self._extract_answer_text(response_payload)
        if not answer_text:
            raise LLMProviderError("LLM provider returned empty answer content.")
        return LLMGenerateResult(answer_text=answer_text, confidence_hint=0.65)

    def _request_chat_completion(self, payload: dict) -> dict:
        endpoint = f"{self._base_url.rstrip('/')}/chat/completions"
        req = urllib_request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        timeout_seconds = max(self._request_timeout_ms / 1000.0, 0.1)
        try:
            with urllib_request.urlopen(req, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)
        except error.HTTPError as exc:
            if exc.code in (401, 403):
                raise LLMProviderError("LLM provider authentication failed.") from exc
            if exc.code == 429:
                raise LLMProviderError("LLM provider rate limited.") from exc
            if exc.code >= 500:
                raise LLMProviderError("LLM provider service unavailable.") from exc
            raise LLMProviderError(f"LLM provider HTTP error: {exc.code}.") from exc
        except (socket.timeout, TimeoutError) as exc:
            raise LLMProviderError("LLM provider request timeout.") from exc
        except error.URLError as exc:
            reason = getattr(exc, "reason", None)
            if isinstance(reason, socket.timeout):
                raise LLMProviderError("LLM provider request timeout.") from exc
            raise LLMProviderError("LLM provider network error.") from exc
        except json.JSONDecodeError as exc:
            raise LLMProviderError("LLM provider returned invalid JSON response.") from exc
        except Exception as exc:  # noqa: BLE001
            raise LLMProviderError("LLM provider internal error.") from exc

    def _build_payload(self, request: LLMGenerateRequest) -> dict:
        context_text = "\n\n".join(request.context_blocks)
        user_prompt = (
            f"用户问题：{request.query_text}\n\n"
            f"Prompt模板：{request.prompt_template_name}@{request.prompt_template_version}\n\n"
            f"检索证据：\n{context_text}\n\n"
            "请仅基于检索证据回答，不要编造。"
        )
        return {
            "model": self._model_name,
            "messages": [
                {"role": "system", "content": request.instructions},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": request.temperature,
        }

    @staticmethod
    def _extract_answer_text(payload: dict) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0] or {}
        message = first.get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            text_parts: list[str] = []
            for part in content:
                if isinstance(part, dict):
                    maybe_text = part.get("text")
                    if isinstance(maybe_text, str):
                        text_parts.append(maybe_text)
            return "\n".join(text_parts).strip()
        return ""


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
