from app.parsers.adapters.pdf_adapter import PdfParserAdapter


class MarkdownParserAdapter(PdfParserAdapter):
    @property
    def adapter_name(self) -> str:
        return "markdown_parser_adapter"
