from __future__ import annotations

from app.core.config import settings
from app.core.errors import AppError, ERROR_CODE
from app.parsers.adapters.base import ParseInput, ParserAdapter
from app.parsers.adapters.excel_adapter import ExcelParserAdapter
from app.parsers.adapters.markdown_file_adapter import MarkdownFileParserAdapter
from app.parsers.adapters.markdown_adapter import MarkdownParserAdapter
from app.parsers.adapters.pdf_adapter import PdfParserAdapter
from app.parsers.adapters.txt_file_adapter import TxtFileParserAdapter
from app.parsers.adapters.txt_adapter import TxtParserAdapter
from app.parsers.adapters.word_adapter import WordParserAdapter
from app.schemas.document_parse import DocumentFormat, StructuredDocument


class AdapterMode:
    placeholder = "placeholder"
    real = "real"


class ParserRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, dict[DocumentFormat, ParserAdapter]] = {
            AdapterMode.placeholder: {
                DocumentFormat.pdf: PdfParserAdapter(),
                DocumentFormat.word: WordParserAdapter(),
                DocumentFormat.excel: ExcelParserAdapter(),
                DocumentFormat.markdown: MarkdownParserAdapter(),
                DocumentFormat.txt: TxtParserAdapter(),
            },
            AdapterMode.real: {
                DocumentFormat.markdown: MarkdownFileParserAdapter(),
                DocumentFormat.txt: TxtFileParserAdapter(),
            },
        }

    def _get_mode(self, fmt: DocumentFormat) -> str:
        provider = settings.doc_parse_provider
        if provider == "placeholder":
            return AdapterMode.placeholder
        if provider == "real" and fmt in settings.doc_parse_real_formats:
            return AdapterMode.real
        if provider == "hybrid" and fmt in settings.doc_parse_real_formats:
            return AdapterMode.real
        return AdapterMode.placeholder

    def get(self, fmt: DocumentFormat) -> ParserAdapter:
        mode = self._get_mode(fmt)
        adapter = self._adapters.get(mode, {}).get(fmt)
        if not adapter:
            raise AppError(
                code=ERROR_CODE.COMMON_INVALID_ARGUMENT,
                message=f"unsupported format: {fmt}",
                status_code=400,
            )
        return adapter

    def parse(self, parse_input: ParseInput) -> tuple[StructuredDocument, str]:
        fmt = parse_input.metadata.format
        mode = self._get_mode(fmt)
        adapter = self.get(fmt)
        if mode == AdapterMode.real and settings.doc_parse_enable_fallback:
            try:
                return adapter.parse(parse_input), mode
            except Exception:
                fallback_adapter = self._adapters[AdapterMode.placeholder][fmt]
                return fallback_adapter.parse(parse_input), AdapterMode.placeholder
        return adapter.parse(parse_input), mode


parser_registry = ParserRegistry()
