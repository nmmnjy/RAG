from fastapi import APIRouter

from app.api.v1.endpoints.document_parse import router as document_parse_router
from app.api.v1.endpoints.qa import router as qa_router


api_v1_router = APIRouter()
api_v1_router.include_router(document_parse_router, tags=["document-parse"])
api_v1_router.include_router(qa_router, tags=["qa"])
