from app.core.config import Settings
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
