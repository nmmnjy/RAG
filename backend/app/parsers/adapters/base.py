from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.schemas.document_parse import DocumentMetadata, StructuredDocument


@dataclass(frozen=True)
class ParseInput:
    metadata: DocumentMetadata
    file_path: str | None = None


class ParserAdapter(ABC):
    @property
    @abstractmethod
    def adapter_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def parse(self, parse_input: ParseInput) -> StructuredDocument:
        raise NotImplementedError
