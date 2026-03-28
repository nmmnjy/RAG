from __future__ import annotations

from app.schemas.document_parse import DocumentStatus, ParseTask


class InMemoryDocumentParseRepository:
    def __init__(self) -> None:
        self._tasks: dict[str, ParseTask] = {}

    def save(self, task: ParseTask) -> ParseTask:
        self._tasks[task.task_id] = task
        return task

    def get(self, task_id: str) -> ParseTask | None:
        return self._tasks.get(task_id)

    def list(self, kb_id: str | None = None, status: DocumentStatus | None = None) -> list[ParseTask]:
        tasks = list(self._tasks.values())
        if kb_id:
            tasks = [item for item in tasks if item.kb_id == kb_id]
        if status:
            tasks = [item for item in tasks if item.status == status]
        return tasks


document_parse_repository = InMemoryDocumentParseRepository()
