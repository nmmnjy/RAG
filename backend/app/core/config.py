from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_env: str
    app_port: int
    log_level: str
    service_name: str
    parse_max_retry: int


def load_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "dev"),
        app_port=int(os.getenv("APP_PORT", "8000")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        service_name=os.getenv("APP_SERVICE_NAME", "backend-document-parser"),
        parse_max_retry=int(os.getenv("DOC_PARSE_MAX_RETRY", "3")),
    )


settings = load_settings()
