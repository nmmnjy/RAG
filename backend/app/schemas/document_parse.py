from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DocumentFormat(str, Enum):
    pdf = "pdf"
    word = "word"
    excel = "excel"
    markdown = "markdown"
    txt = "txt"


class DocumentStatus(str, Enum):
    pending = "pending"
    parsing = "parsing"
    succeeded = "succeeded"
    failed = "failed"
    retryable = "retryable"


class StructuredBlockType(str, Enum):
    paragraph = "paragraph"
    table = "table"


class DocumentMetadata(BaseModel):
    doc_id: str
    kb_id: str
    source: str
    format: DocumentFormat
    version: str
    status: DocumentStatus = DocumentStatus.pending


class StructuredBlock(BaseModel):
    block_id: str
    block_type: StructuredBlockType
    content: str = ""
    section_path: list[str] = Field(default_factory=list)
    page_no: int | None = None
    table_rows: list[list[str]] | None = None


class StructuredSection(BaseModel):
    section_id: str
    title: str
    heading_level: int = 1
    section_path: list[str] = Field(default_factory=list)
    page_start: int | None = None
    page_end: int | None = None
    blocks: list[StructuredBlock] = Field(default_factory=list)


class StructuredDocument(BaseModel):
    doc_id: str
    kb_id: str
    source: str
    format: DocumentFormat
    version: str
    status: DocumentStatus
    sections: list[StructuredSection] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParseTaskCreateRequest(BaseModel):
    doc_id: str
    kb_id: str
    source: str
    format: DocumentFormat
    version: str


class ParseUploadRequest(BaseModel):
    doc_id: str
    kb_id: str
    filename: str
    version: str
    file_content_base64: str


class ParseTask(BaseModel):
    task_id: str
    doc_id: str
    kb_id: str
    source: str
    format: DocumentFormat
    version: str
    status: DocumentStatus
    retry_count: int = 0
    error_code: str | None = None
    error_message: str | None = None
    structured_document: StructuredDocument | None = None


class ParseTaskTransition(BaseModel):
    from_status: DocumentStatus
    to_status: DocumentStatus
