from __future__ import annotations

import base64
from binascii import Error as BinasciiError
from pathlib import Path
import uuid

from app.core.config import settings
from app.core.errors import AppError, ERROR_CODE
from app.core.logging import build_log_payload, get_logger
from app.parsers.adapters.base import ParseInput
from app.parsers.registry import parser_registry
from app.repositories.document_parse_repository import document_parse_repository
from app.schemas.document_parse import (
    DocumentMetadata,
    DocumentFormat,
    DocumentStatus,
    ParseTask,
    ParseTaskCreateRequest,
    ParseUploadRequest,
)
from app.services.parse_task_state_machine import state_machine


logger = get_logger(__name__)


class DocumentParseService:
    _format_mapping: dict[str, DocumentFormat] = {
        ".pdf": DocumentFormat.pdf,
        ".md": DocumentFormat.markdown,
        ".markdown": DocumentFormat.markdown,
        ".txt": DocumentFormat.txt,
        ".doc": DocumentFormat.word,
        ".docx": DocumentFormat.word,
        ".xls": DocumentFormat.excel,
        ".xlsx": DocumentFormat.excel,
    }

    _doc_error_http_mapping: dict[str, int] = {
        ERROR_CODE.DOC_NOT_FOUND: 404,
        ERROR_CODE.DOC_PARSE_FAILED: 500,
        ERROR_CODE.DOC_UNSUPPORTED_FORMAT: 400,
        ERROR_CODE.DOC_SOURCE_INVALID: 400,
        ERROR_CODE.DOC_SOURCE_NOT_FOUND: 404,
        ERROR_CODE.DOC_RETRY_NOT_ALLOWED: 409,
    }

    def create_task(self, payload: ParseTaskCreateRequest) -> ParseTask:
        task = ParseTask(
            task_id=f"task_{uuid.uuid4().hex[:16]}",
            doc_id=payload.doc_id,
            kb_id=payload.kb_id,
            source=payload.source,
            format=payload.format,
            version=payload.version,
            status=DocumentStatus.pending,
        )
        logger.info(build_log_payload(task_id=task.task_id, task_type="document_parse", stage="create"))
        return document_parse_repository.save(task)

    def upload_and_parse(self, payload: ParseUploadRequest) -> ParseTask:
        source_path = self._save_upload_file(payload)
        fmt = self._infer_format(payload.filename)
        created_task = self.create_task(
            ParseTaskCreateRequest(
                doc_id=payload.doc_id,
                kb_id=payload.kb_id,
                source=f"file://{source_path}",
                format=fmt,
                version=payload.version,
            )
        )
        return self.run_task(created_task.task_id)

    def get_task(self, task_id: str) -> ParseTask:
        task = document_parse_repository.get(task_id)
        if not task:
            raise AppError(
                code=ERROR_CODE.DOC_NOT_FOUND,
                message="parse task not found",
                status_code=404,
                details={"task_id": task_id},
            )
        return task

    def list_tasks(self, kb_id: str | None, status: DocumentStatus | None) -> list[ParseTask]:
        return document_parse_repository.list(kb_id=kb_id, status=status)

    def run_task(self, task_id: str) -> ParseTask:
        task = self.get_task(task_id)
        state_machine.assert_transition(task.status, DocumentStatus.parsing)
        task.status = DocumentStatus.parsing
        document_parse_repository.save(task)
        metadata = DocumentMetadata(
            doc_id=task.doc_id,
            kb_id=task.kb_id,
            source=task.source,
            format=task.format,
            version=task.version,
            status=task.status,
        )
        try:
            parse_input = ParseInput(metadata=metadata, file_path=self._resolve_file_path(task.source))
            structured_document, parser_mode = parser_registry.parse(parse_input)
            state_machine.assert_transition(task.status, DocumentStatus.succeeded)
            task.status = DocumentStatus.succeeded
            structured_document.status = DocumentStatus.succeeded
            task.structured_document = structured_document
            task.error_code = None
            task.error_message = None
            logger.info(
                build_log_payload(
                    task_id=task.task_id,
                    task_type="document_parse",
                    stage="parser_selected",
                    parser_mode=parser_mode,
                    parser_provider=settings.doc_parse_provider,
                    kb_id=task.kb_id,
                    doc_id=task.doc_id,
                )
            )
        except AppError as exc:
            task.retry_count += 1
            task.error_code = self._map_doc_error_code(exc)
            task.error_message = exc.message
            self._set_failure_status(task)
        except Exception:
            task.retry_count += 1
            task.error_code = ERROR_CODE.DOC_PARSE_FAILED
            task.error_message = "parse failed"
            self._set_failure_status(task)
        logger.info(
            build_log_payload(
                task_id=task.task_id,
                task_type="document_parse",
                stage="run",
                retry_count=task.retry_count,
                result=task.status.value,
                kb_id=task.kb_id,
                doc_id=task.doc_id,
            )
        )
        return document_parse_repository.save(task)

    def retry_task(self, task_id: str) -> ParseTask:
        task = self.get_task(task_id)
        if task.status not in {DocumentStatus.retryable, DocumentStatus.failed}:
            raise AppError(
                code=ERROR_CODE.DOC_RETRY_NOT_ALLOWED,
                message="retry is allowed only for retryable or failed task",
                status_code=self._doc_error_http_mapping[ERROR_CODE.DOC_RETRY_NOT_ALLOWED],
                details={"task_id": task_id, "status": task.status},
            )
        if task.status == DocumentStatus.failed:
            state_machine.assert_transition(task.status, DocumentStatus.retryable)
            task.status = DocumentStatus.retryable
            document_parse_repository.save(task)
        return self.run_task(task_id)

    def get_doc_error_http_mapping(self) -> dict[str, int]:
        return dict(self._doc_error_http_mapping)

    def _set_failure_status(self, task: ParseTask) -> None:
        target_status = (
            DocumentStatus.retryable if task.retry_count < settings.parse_max_retry else DocumentStatus.failed
        )
        state_machine.assert_transition(task.status, target_status)
        task.status = target_status

    def _map_doc_error_code(self, exc: AppError) -> str:
        if exc.code.startswith("DOC_"):
            return exc.code
        return ERROR_CODE.DOC_PARSE_FAILED

    def _resolve_file_path(self, source: str) -> str | None:
        if source.startswith("file://"):
            return source.replace("file://", "", 1)
        if source.startswith("/") or ":\\" in source:
            return source
        return None

    def _infer_format(self, filename: str) -> DocumentFormat:
        suffix = Path(filename).suffix.lower()
        fmt = self._format_mapping.get(suffix)
        if not fmt:
            raise AppError(
                code=ERROR_CODE.DOC_UNSUPPORTED_FORMAT,
                message="unsupported file format",
                status_code=self._doc_error_http_mapping[ERROR_CODE.DOC_UNSUPPORTED_FORMAT],
                details={"filename": filename},
            )
        return fmt

    def _save_upload_file(self, payload: ParseUploadRequest) -> str:
        target_dir = Path(settings.doc_parse_upload_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            file_bytes = base64.b64decode(payload.file_content_base64, validate=True)
        except BinasciiError as exc:
            raise AppError(
                code=ERROR_CODE.DOC_SOURCE_INVALID,
                message="invalid base64 upload payload",
                status_code=self._doc_error_http_mapping[ERROR_CODE.DOC_SOURCE_INVALID],
                details={"reason": str(exc)},
            ) from exc

        if not file_bytes:
            raise AppError(
                code=ERROR_CODE.DOC_SOURCE_INVALID,
                message="empty upload payload",
                status_code=self._doc_error_http_mapping[ERROR_CODE.DOC_SOURCE_INVALID],
            )

        file_name = f"{payload.doc_id}_{uuid.uuid4().hex[:8]}_{payload.filename}"
        file_path = target_dir / file_name
        file_path.write_bytes(file_bytes)
        return str(file_path.resolve())


document_parse_service = DocumentParseService()
