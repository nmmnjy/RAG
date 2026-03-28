from fastapi import APIRouter, Query

from app.core.response import success_response
from app.schemas.document_parse import DocumentStatus, ParseTaskCreateRequest
from app.services.document_parse_service import document_parse_service


router = APIRouter(prefix="/document-parse")


@router.post("/tasks")
def create_parse_task(payload: ParseTaskCreateRequest) -> dict:
    task = document_parse_service.create_task(payload)
    return success_response(task.model_dump())


@router.post("/tasks/{task_id}/run")
def run_parse_task(task_id: str) -> dict:
    task = document_parse_service.run_task(task_id)
    return success_response(task.model_dump())


@router.get("/tasks/{task_id}")
def get_parse_task(task_id: str) -> dict:
    task = document_parse_service.get_task(task_id)
    return success_response(task.model_dump())


@router.get("/tasks")
def list_parse_tasks(
    kb_id: str | None = Query(default=None),
    status: DocumentStatus | None = Query(default=None),
) -> dict:
    tasks = document_parse_service.list_tasks(kb_id=kb_id, status=status)
    return success_response([task.model_dump() for task in tasks])
