from app.parsers.adapters.pdf_adapter import PdfParserAdapter


class TxtParserAdapter(PdfParserAdapter):
    @property
    def adapter_name(self) -> str:
        return "txt_parser_adapter"
