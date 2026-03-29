from __future__ import annotations

from enum import Enum
from hashlib import sha1
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.chunking import ChunkBuildResult, ChunkRecord
from app.schemas.document_parse import DocumentFormat


class VectorWriteMode(str, Enum):
    initial_build = "initial_build"
    rebuild = "rebuild"
    incremental_update = "incremental_update"


class VectorizationInput(ChunkBuildResult):
    """Directly consumes the frozen chunk contract from module 02."""


class VectorRecord(BaseModel):
    vector_id: str
    kb_id: str
    doc_id: str
    chunk_id: str
    content: str
    token_count: int
    section_path: list[str] = Field(default_factory=list)
    source: str
    format: DocumentFormat
    version: str
    chunk_index: int
    strategy_name: str
    strategy_version: str
    embedding_provider: str
    embedding_model: str
    embedding_model_version: str
    embedding_dim: int
    embedding: list[float] = Field(default_factory=list)
    content_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @staticmethod
    def build_content_hash(chunk: ChunkRecord) -> str:
        payload = f"{chunk.chunk_id}|{chunk.content}".encode("utf-8")
        return sha1(payload).hexdigest()


class VectorWriteRequest(BaseModel):
    mode: VectorWriteMode = VectorWriteMode.initial_build
    vectorization_input: VectorizationInput
    changed_chunk_ids: list[str] = Field(default_factory=list)


class VectorWriteResult(BaseModel):
    mode: VectorWriteMode
    kb_id: str
    doc_id: str
    requested_chunk_count: int
    embedded_chunk_count: int
    upserted_count: int
    deleted_count: int
    skipped_count: int


class VectorQueryRequest(BaseModel):
    kb_id: str
    query_embedding: list[float]
    top_k: int = Field(default=5, ge=1, le=100)
    doc_id: str | None = None


class VectorQueryHit(BaseModel):
    chunk_id: str
    doc_id: str
    kb_id: str
    content: str
    section_path: list[str] = Field(default_factory=list)
    score_vector: float
    citation: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
