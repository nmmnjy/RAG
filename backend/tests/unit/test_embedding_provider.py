import json
from urllib import error

import pytest

from app.services import embedding_provider


class _FakeHTTPResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_openai_compatible_provider_should_parse_embeddings(monkeypatch) -> None:  # noqa: ANN001
    provider = embedding_provider.OpenAICompatibleEmbeddingProvider(
        model_name="text-embedding-3-small",
        embedding_dim=4,
        api_key="sk-test",
        base_url="https://example.com/v1",
        request_timeout_ms=5000,
    )

    def _ok_response(req, timeout):  # noqa: ANN001, ARG001
        return _FakeHTTPResponse(
            {"data": [{"embedding": [0.1, 0.2, 0.3, 0.4]}, {"embedding": [0.5, 0.6, 0.7, 0.8]}]}
        )

    monkeypatch.setattr(embedding_provider.urllib_request, "urlopen", _ok_response)
    vectors = provider.embed_texts(["a", "b"])
    assert len(vectors) == 2
    assert vectors[0][0] == 0.1


def test_openai_compatible_provider_should_raise_on_dimension_mismatch(monkeypatch) -> None:  # noqa: ANN001
    provider = embedding_provider.OpenAICompatibleEmbeddingProvider(
        model_name="text-embedding-3-small",
        embedding_dim=4,
        api_key="sk-sensitive",
        base_url="https://example.com/v1",
        request_timeout_ms=5000,
    )

    def _bad_dim_response(req, timeout):  # noqa: ANN001, ARG001
        return _FakeHTTPResponse({"data": [{"embedding": [0.1, 0.2]}]})

    monkeypatch.setattr(embedding_provider.urllib_request, "urlopen", _bad_dim_response)
    with pytest.raises(embedding_provider.EmbeddingProviderError, match="dimension mismatch"):
        provider.embed_texts(["a"])


def test_build_provider_should_fallback_to_mock_when_real_call_fails(monkeypatch) -> None:  # noqa: ANN001
    provider = embedding_provider.build_embedding_provider(
        embedding_provider.EmbeddingProviderConfig(
            provider_type=embedding_provider.EmbeddingProviderType.openai_compatible,
            model_name="text-embedding-3-small",
            embedding_dim=4,
            api_key="sk-test",
            base_url="https://example.com/v1",
            enable_real_provider=True,
            fallback_to_mock=True,
        )
    )

    def _network_error(req, timeout):  # noqa: ANN001, ARG001
        raise error.URLError("network down")

    monkeypatch.setattr(embedding_provider.urllib_request, "urlopen", _network_error)
    vectors = provider.embed_texts(["fallback-check"])
    assert len(vectors) == 1
    assert len(vectors[0]) == 4
    assert provider.provider_name == "mock"


def test_real_provider_should_raise_when_call_fails_and_fallback_disabled(monkeypatch) -> None:  # noqa: ANN001
    provider = embedding_provider.build_embedding_provider(
        embedding_provider.EmbeddingProviderConfig(
            provider_type=embedding_provider.EmbeddingProviderType.openai_compatible,
            model_name="text-embedding-3-small",
            embedding_dim=4,
            api_key="sk-test",
            base_url="https://example.com/v1",
            enable_real_provider=True,
            fallback_to_mock=False,
        )
    )

    def _network_error(req, timeout):  # noqa: ANN001, ARG001
        raise error.URLError("network down")

    monkeypatch.setattr(embedding_provider.urllib_request, "urlopen", _network_error)
    with pytest.raises(embedding_provider.EmbeddingProviderError, match="network error"):
        provider.embed_texts(["raise-check"])
