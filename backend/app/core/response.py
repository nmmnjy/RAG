from datetime import datetime, timezone
from typing import Any

from app.core.context import get_request_id, get_trace_id


def success_response(data: Any, message: str = "success", code: str = "OK") -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "data": data,
        "request_id": get_request_id(),
        "trace_id": get_trace_id(),
        "ts": datetime.now(timezone.utc).isoformat(),
    }


def error_response(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "details": details or {},
        "request_id": get_request_id(),
        "trace_id": get_trace_id(),
    }
