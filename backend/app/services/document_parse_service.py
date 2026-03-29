from __future__ import annotations

import uuid

from app.core.config import settings
from app.core.errors import AppError, ERROR_CODE
from app.core.logging import build_log_payload, get_logger
from app.parsers.adapters.base import ParseInput
from app.parsers.registry import parser_registry
from app.repositories.document_parse_repository import document_parse_repository
from app.schemas.document_parse import (
    DocumentMetadata,
    DocumentStatus,
    ParseTask,
    ParseTaskCreateRequest,
)
from app.services.parse_task_state_machine import state_machine


logger = get_logger(__name__)


class DocumentParseService:
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
            task.error_code = exc.code
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

    def _set_failure_status(self, task: ParseTask) -> None:
        target_status = (
            DocumentStatus.retryable if task.retry_count < settings.parse_max_retry else DocumentStatus.failed
        )
        state_machine.assert_transition(task.status, target_status)
        task.status = target_status

    def _resolve_file_path(self, source: str) -> str | None:
        if source.startswith("file://"):
            return source.replace("file://", "", 1)
        if source.startswith("/") or ":\\" in source:
            return source
        return None


document_parse_service = DocumentParseService()
