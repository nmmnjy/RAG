from app.parsers.adapters.pdf_adapter import PdfParserAdapter


class WordParserAdapter(PdfParserAdapter):
    @property
    def adapter_name(self) -> str:
        return "word_parser_adapter"
