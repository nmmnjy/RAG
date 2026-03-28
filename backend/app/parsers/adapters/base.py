from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.document_parse import DocumentMetadata, StructuredDocument


class ParserAdapter(ABC):
    @property
    @abstractmethod
    def adapter_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def parse(self, metadata: DocumentMetadata) -> StructuredDocument:
        raise NotImplementedError
