import socket
from urllib.error import HTTPError

import pytest

from app.core.config import Settings
from app.schemas.answer_generation import LLMGenerateRequest
from app.services import llm_provider


def _build_settings(**overrides) -> Settings:
    base = {
        "app_env": "test",
        "app_port": 8000,
        "log_level": "INFO",
        "service_name": "backend-test",
        "parse_max_retry": 3,
        "embedding_provider": "mock",
        "embedding_model": "mock-embedding-v1",
        "embedding_dim": 12,
        "embedding_api_key": "",
        "embedding_base_url": "",
        "embedding_request_timeout_ms": 10000,
        "embedding_provider_enable_real": False,
        "embedding_provider_fallback_to_mock": True,
        "llm_provider": "mock",
        "llm_model": "mock-qa-v1",
        "llm_api_key": "",
        "llm_base_url": "",
        "llm_request_timeout_ms": 15000,
        "llm_provider_enable_real": False,
        "llm_provider_fallback_to_mock": True,
        "vector_repository": "in_memory",
        "vector_repository_enable_real": False,
        "vector_repository_fallback_to_in_memory": True,
        "vector_db_url": "",
        "vector_table_name": "kb_vectors",
    }
    base.update(overrides)
    return Settings(**base)


def test_build_llm_provider_should_use_mock_by_default(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(llm_provider, "settings", _build_settings(llm_provider="mock"))
    provider = llm_provider.build_llm_provider()
    assert provider.provider_name == "mock"


def test_build_llm_provider_should_fallback_to_mock_when_real_disabled(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        llm_provider,
        "settings",
        _build_settings(
            llm_provider="openai_compatible",
            llm_provider_enable_real=False,
            llm_provider_fallback_to_mock=True,
        ),
    )
    provider = llm_provider.build_llm_provider()
    assert provider.provider_name == "mock"


def test_build_llm_provider_should_return_real_provider_when_enabled(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        llm_provider,
        "settings",
        _build_settings(
            llm_provider="openai_compatible",
            llm_provider_enable_real=True,
            llm_api_key="***",
            llm_base_url="https://example.com/v1",
            llm_model="demo-model",
        ),
    )
    provider = llm_provider.build_llm_provider()
    assert provider.provider_name == "openai_compatible"
    assert provider.model_name == "demo-model"


def test_openai_compatible_provider_should_parse_answer_from_response(monkeypatch) -> None:  # noqa: ANN001
    provider = llm_provider.OpenAICompatibleLLMProvider(
        model_name="demo-model",
        api_key="***",
        base_url="https://example.com/v1",
        request_timeout_ms=5000,
    )
    monkeypatch.setattr(
        provider,
        "_request_chat_completion",
        lambda payload: {  # noqa: ARG005
            "choices": [{"message": {"content": "这是来自真实 provider 的回答"}}]
        },
    )
    result = provider.generate(
        LLMGenerateRequest(query_text="q", context_blocks=["c1", "c2"], instructions="ins")
    )
    assert result.answer_text == "这是来自真实 provider 的回答"
    assert result.confidence_hint > 0


def test_openai_compatible_provider_should_map_auth_error_to_llm_provider_error(monkeypatch) -> None:  # noqa: ANN001
    provider = llm_provider.OpenAICompatibleLLMProvider(
        model_name="demo-model",
        api_key="***",
        base_url="https://example.com/v1",
        request_timeout_ms=5000,
    )

    def _raise_auth_error(req, timeout):  # noqa: ANN001, ARG001
        raise HTTPError(url=req.full_url, code=401, msg="unauthorized", hdrs=None, fp=None)

    monkeypatch.setattr(llm_provider.urllib_request, "urlopen", _raise_auth_error)
    with pytest.raises(llm_provider.LLMProviderError, match="authentication failed"):
        provider.generate(LLMGenerateRequest(query_text="q", context_blocks=["ctx"]))


def test_openai_compatible_provider_should_map_timeout_to_llm_provider_error(monkeypatch) -> None:  # noqa: ANN001
    provider = llm_provider.OpenAICompatibleLLMProvider(
        model_name="demo-model",
        api_key="***",
        base_url="https://example.com/v1",
        request_timeout_ms=5000,
    )

    def _raise_timeout(req, timeout):  # noqa: ANN001, ARG001
        raise socket.timeout("timed out")

    monkeypatch.setattr(llm_provider.urllib_request, "urlopen", _raise_timeout)
    with pytest.raises(llm_provider.LLMProviderError, match="request timeout"):
        provider.generate(LLMGenerateRequest(query_text="q", context_blocks=["ctx"]))
