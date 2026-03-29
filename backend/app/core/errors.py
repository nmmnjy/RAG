from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.response import error_response


@dataclass(frozen=True)
class ErrorCode:
    COMMON_INVALID_ARGUMENT: str = "COMMON_INVALID_ARGUMENT"
    COMMON_NOT_FOUND: str = "COMMON_NOT_FOUND"
    COMMON_CONFLICT: str = "COMMON_CONFLICT"
    COMMON_INTERNAL_ERROR: str = "COMMON_INTERNAL_ERROR"
    DOC_NOT_FOUND: str = "DOC_NOT_FOUND"
    DOC_PARSE_FAILED: str = "DOC_PARSE_FAILED"
    DOC_UNSUPPORTED_FORMAT: str = "DOC_UNSUPPORTED_FORMAT"
    DOC_SOURCE_INVALID: str = "DOC_SOURCE_INVALID"
    DOC_SOURCE_NOT_FOUND: str = "DOC_SOURCE_NOT_FOUND"
    DOC_RETRY_NOT_ALLOWED: str = "DOC_RETRY_NOT_ALLOWED"
    CHUNK_BUILD_FAILED: str = "CHUNK_BUILD_FAILED"
    EMBEDDING_REQUEST_FAILED: str = "EMBEDDING_REQUEST_FAILED"
    EMBEDDING_INVALID_RESPONSE: str = "EMBEDDING_INVALID_RESPONSE"
    EMBEDDING_DIM_MISMATCH: str = "EMBEDDING_DIM_MISMATCH"
    VECTOR_WRITE_FAILED: str = "VECTOR_WRITE_FAILED"
    VECTOR_UPSERT_FAILED: str = "VECTOR_UPSERT_FAILED"
    VECTOR_DELETE_FAILED: str = "VECTOR_DELETE_FAILED"


ERROR_CODE = ErrorCode()


@dataclass
class AppError(Exception):
    code: str
    message: str
    status_code: int
    details: dict[str, Any] = field(default_factory=dict)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(code=exc.code, message=exc.message, details=exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=error_response(
                code=ERROR_CODE.COMMON_INVALID_ARGUMENT,
                message="invalid request data",
                details={"errors": exc.errors()},
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unknown_error(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=error_response(
                code=ERROR_CODE.COMMON_INTERNAL_ERROR,
                message="internal server error",
                details={"safe_message": str(exc)},
            ),
        )
