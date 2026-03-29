import pytest

from app.core.config import Settings
from app.repositories.vector_repository import InMemoryVectorRepository
from app.services.embedding_provider import EmbeddingProviderError, MockEmbeddingProvider
from app.services.vector_access_factory import build_vector_access_runtime


def _build_settings(**overrides) -> Settings:
    base = Settings(
        app_env="test",
        app_port=8000,
        log_level="INFO",
        service_name="backend-test",
        parse_max_retry=3,
        embedding_provider="mock",
        embedding_model="mock-embedding-v1",
        embedding_dim=12,
        embedding_api_key="",
        embedding_base_url="",
        embedding_request_timeout_ms=10000,
        embedding_provider_enable_real=False,
        embedding_provider_fallback_to_mock=True,
        vector_repository="in_memory",
        vector_repository_enable_real=False,
        vector_repository_fallback_to_in_memory=True,
        vector_db_url="",
        vector_table_name="kb_vectors",
    )
    return Settings(**(base.__dict__ | overrides))


def test_vector_access_runtime_should_use_default_mock_and_in_memory() -> None:
    runtime = build_vector_access_runtime(_build_settings())
    assert isinstance(runtime.embedding_provider, MockEmbeddingProvider)
    assert isinstance(runtime.vector_repository, InMemoryVectorRepository)


def test_runtime_should_fallback_when_real_provider_or_repository_not_ready() -> None:
    runtime = build_vector_access_runtime(
        _build_settings(
            embedding_provider="openai_compatible",
            vector_repository="pgvector",
            embedding_provider_enable_real=False,
            vector_repository_enable_real=False,
        )
    )
    assert runtime.embedding_provider.provider_name == "mock"
    assert isinstance(runtime.vector_repository, InMemoryVectorRepository)


def test_runtime_should_raise_when_fallback_disabled_and_real_not_ready() -> None:
    with pytest.raises(EmbeddingProviderError):
        build_vector_access_runtime(
            _build_settings(
                embedding_provider="openai_compatible",
                embedding_provider_fallback_to_mock=False,
                embedding_provider_enable_real=False,
            )
        )
