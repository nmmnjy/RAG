from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime, timezone
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="")


def get_request_id() -> str:
    return request_id_ctx.get()


def get_trace_id() -> str:
    return trace_id_ctx.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex[:12]}"
        trace_id = request.headers.get("x-trace-id") or f"trace_{uuid.uuid4().hex[:12]}"
        request_id_ctx.set(request_id)
        trace_id_ctx.set(trace_id)
        request.state.request_started_at = datetime.now(timezone.utc)
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        response.headers["x-trace-id"] = trace_id
        return response
