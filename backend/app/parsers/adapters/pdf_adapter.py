from app.parsers.adapters.base import ParseInput, ParserAdapter
from app.schemas.document_parse import (
    StructuredBlock,
    StructuredBlockType,
    StructuredDocument,
    StructuredSection,
)


class PdfParserAdapter(ParserAdapter):
    @property
    def adapter_name(self) -> str:
        return "pdf_parser_adapter"

    def parse(self, parse_input: ParseInput) -> StructuredDocument:
        metadata = parse_input.metadata
        section = StructuredSection(
            section_id=f"{metadata.doc_id}_sec_1",
            title="PDF Root Section",
            heading_level=1,
            section_path=["PDF Root Section"],
            page_start=1,
            page_end=1,
            blocks=[
                StructuredBlock(
                    block_id=f"{metadata.doc_id}_blk_1",
                    block_type=StructuredBlockType.paragraph,
                    content="placeholder extracted text from pdf",
                    section_path=["PDF Root Section"],
                    page_no=1,
                )
            ],
        )
        return StructuredDocument(**metadata.model_dump(), sections=[section])
