from app.core.errors import AppError, ERROR_CODE
from app.parsers.adapters.base import ParserAdapter
from app.parsers.adapters.excel_adapter import ExcelParserAdapter
from app.parsers.adapters.markdown_adapter import MarkdownParserAdapter
from app.parsers.adapters.pdf_adapter import PdfParserAdapter
from app.parsers.adapters.txt_adapter import TxtParserAdapter
from app.parsers.adapters.word_adapter import WordParserAdapter
from app.schemas.document_parse import DocumentFormat


class ParserRegistry:
    def __init__(self) -> None:
        self._adapters: dict[DocumentFormat, ParserAdapter] = {
            DocumentFormat.pdf: PdfParserAdapter(),
            DocumentFormat.word: WordParserAdapter(),
            DocumentFormat.excel: ExcelParserAdapter(),
            DocumentFormat.markdown: MarkdownParserAdapter(),
            DocumentFormat.txt: TxtParserAdapter(),
        }

    def get(self, fmt: DocumentFormat) -> ParserAdapter:
        adapter = self._adapters.get(fmt)
        if not adapter:
            raise AppError(
                code=ERROR_CODE.COMMON_INVALID_ARGUMENT,
                message=f"unsupported format: {fmt}",
                status_code=400,
            )
        return adapter


parser_registry = ParserRegistry()
