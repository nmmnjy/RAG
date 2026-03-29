from dataclasses import dataclass, field
import os


@dataclass(frozen=True)
class Settings:
    app_env: str = "dev"
    app_port: int = 8000
    log_level: str = "INFO"
    service_name: str = "backend-document-parser"
    parse_max_retry: int = 3
    doc_parse_provider: str = "hybrid"
    doc_parse_real_formats: set[str] = field(default_factory=lambda: {"markdown", "txt"})
    doc_parse_enable_fallback: bool = True
    doc_parse_upload_dir: str = "backend/data/uploads"
    llm_provider: str = "mock"
    llm_model: str = "mock-llm"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_request_timeout_ms: int = 15000
    llm_provider_enable_real: bool = False
    llm_provider_fallback_to_mock: bool = True
    embedding_provider: str = "mock"
    embedding_model: str = "mock-embedding"
    embedding_dim: int = 384
    embedding_api_key: str = ""
    embedding_base_url: str = ""
    embedding_request_timeout_ms: int = 15000
    embedding_provider_enable_real: bool = False
    embedding_provider_fallback_to_mock: bool = True
    embedding_max_retry: int = 2
    vector_repository: str = "in_memory"
    vector_db_url: str = ""
    vector_table_name: str = "chunks"
    vector_repository_enable_real: bool = False
    vector_repository_fallback_to_in_memory: bool = True
    vector_repository_max_retry: int = 2


def _parse_bool(value: str, default: bool) -> bool:
    if value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    real_formats_raw = os.getenv("DOC_PARSE_REAL_FORMATS", "markdown,txt")
    real_formats = {item.strip() for item in real_formats_raw.split(",") if item.strip()}
    return Settings(
        app_env=os.getenv("APP_ENV", "dev"),
        app_port=int(os.getenv("APP_PORT", "8000")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        service_name=os.getenv("APP_SERVICE_NAME", "backend-document-parser"),
        parse_max_retry=int(os.getenv("DOC_PARSE_MAX_RETRY", "3")),
        doc_parse_provider=os.getenv("DOC_PARSE_PROVIDER", "hybrid"),
        doc_parse_real_formats=real_formats,
        doc_parse_enable_fallback=_parse_bool(os.getenv("DOC_PARSE_ENABLE_FALLBACK", "true"), default=True),
        doc_parse_upload_dir=os.getenv("DOC_PARSE_UPLOAD_DIR", "backend/data/uploads"),
        llm_provider=os.getenv("LLM_PROVIDER", "mock"),
        llm_model=os.getenv("LLM_MODEL", "mock-llm"),
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        llm_base_url=os.getenv("LLM_BASE_URL", ""),
        llm_request_timeout_ms=int(os.getenv("LLM_REQUEST_TIMEOUT_MS", "15000")),
        llm_provider_enable_real=_parse_bool(os.getenv("LLM_PROVIDER_ENABLE_REAL", "false"), default=False),
        llm_provider_fallback_to_mock=_parse_bool(os.getenv("LLM_PROVIDER_FALLBACK_TO_MOCK", "true"), default=True),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "mock"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "mock-embedding"),
        embedding_dim=int(os.getenv("EMBEDDING_DIM", "384")),
        embedding_api_key=os.getenv("EMBEDDING_API_KEY", ""),
        embedding_base_url=os.getenv("EMBEDDING_BASE_URL", ""),
        embedding_request_timeout_ms=int(os.getenv("EMBEDDING_REQUEST_TIMEOUT_MS", "15000")),
        embedding_provider_enable_real=_parse_bool(
            os.getenv("EMBEDDING_PROVIDER_ENABLE_REAL", "false"), default=False
        ),
        embedding_provider_fallback_to_mock=_parse_bool(
            os.getenv("EMBEDDING_PROVIDER_FALLBACK_TO_MOCK", "true"), default=True
        ),
        embedding_max_retry=max(int(os.getenv("EMBEDDING_MAX_RETRY", "2")), 1),
        vector_repository=os.getenv("VECTOR_REPOSITORY", "in_memory"),
        vector_db_url=os.getenv("VECTOR_DB_URL", ""),
        vector_table_name=os.getenv("VECTOR_TABLE_NAME", "chunks"),
        vector_repository_enable_real=_parse_bool(os.getenv("VECTOR_REPOSITORY_ENABLE_REAL", "false"), default=False),
        vector_repository_fallback_to_in_memory=_parse_bool(
            os.getenv("VECTOR_REPOSITORY_FALLBACK_TO_IN_MEMORY", "true"), default=True
        ),
        vector_repository_max_retry=max(int(os.getenv("VECTOR_REPOSITORY_MAX_RETRY", "2")), 1),
    )


settings = load_settings()
