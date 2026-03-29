from __future__ import annotations

from fastapi import APIRouter

from app.core.response import success_response
from app.schemas.qa import QAAnswerRequest
from app.services.qa_pipeline_service import qa_pipeline_service


router = APIRouter(prefix="/qa")


@router.post("/answers")
def create_answer(payload: QAAnswerRequest) -> dict:
    result = qa_pipeline_service.answer(payload)
    return success_response(result.model_dump())
