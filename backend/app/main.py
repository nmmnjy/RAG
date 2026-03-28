from fastapi import FastAPI

from app.api.v1.router import api_v1_router
from app.core.context import RequestContextMiddleware
from app.core.errors import register_exception_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="RAG Backend", version="1.0.0")
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    app.include_router(api_v1_router, prefix="/api/v1")
    return app


app = create_app()
