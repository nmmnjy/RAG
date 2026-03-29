from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.document_parse import DocumentFormat


class ChunkStrategyName(str, Enum):
    structured_window = "structured_window"


class SpecialStructureType(str, Enum):
    table = "table"
    list = "list"
    code = "code"


class ChunkBuildParams(BaseModel):
    strategy_name: ChunkStrategyName = ChunkStrategyName.structured_window
    strategy_version: str = "2026.03.02"
    max_tokens_per_chunk: int = Field(default=220, ge=32, le=4096)
    overlap_tokens: int = Field(default=30, ge=0, le=1024)
    min_chunk_tokens: int = Field(default=20, ge=1, le=1024)
    preserve_table_block: bool = True
    preserve_list_block: bool = False
    preserve_code_block: bool = True
    split_on_section_path_change: bool = True
    sentence_boundary_fallback_split: bool = True


class ChunkRecord(BaseModel):
    chunk_id: str
    doc_id: str
    kb_id: str
    content: str
    token_count: int
    section_path: list[str] = Field(default_factory=list)
    chunk_index: int
    strategy_name: ChunkStrategyName
    strategy_version: str
    source_block_ids: list[str] = Field(default_factory=list)
    special_structure: SpecialStructureType | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChunkBuildResult(BaseModel):
    doc_id: str
    kb_id: str
    source: str
    format: DocumentFormat
    version: str
    strategy_name: ChunkStrategyName
    strategy_version: str
    params: ChunkBuildParams
    chunk_count: int
    chunks: list[ChunkRecord] = Field(default_factory=list)
