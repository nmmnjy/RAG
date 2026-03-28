from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.core.context import get_request_id, get_trace_id


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(settings.log_level.upper())
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    return logger


def build_log_payload(**extra: Any) -> dict[str, Any]:
    payload = {
        "timestamp": extra.pop("timestamp", None),
        "level": extra.pop("level", "INFO"),
        "service": settings.service_name,
        "env": settings.app_env,
        "request_id": get_request_id(),
        "trace_id": get_trace_id(),
        "span_id": extra.pop("span_id", ""),
        "user_id": extra.pop("user_id", ""),
        "kb_id": extra.pop("kb_id", ""),
        "doc_id": extra.pop("doc_id", ""),
    }
    payload.update(extra)
    return payload
