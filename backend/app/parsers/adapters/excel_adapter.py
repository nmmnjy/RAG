from app.parsers.adapters.base import ParserAdapter
from app.schemas.document_parse import (
    DocumentMetadata,
    StructuredBlock,
    StructuredBlockType,
    StructuredDocument,
    StructuredSection,
)


class ExcelParserAdapter(ParserAdapter):
    @property
    def adapter_name(self) -> str:
        return "excel_parser_adapter"

    def parse(self, metadata: DocumentMetadata) -> StructuredDocument:
        section = StructuredSection(
            section_id=f"{metadata.doc_id}_sheet_1",
            title="Sheet1",
            heading_level=1,
            section_path=["Sheet1"],
            blocks=[
                StructuredBlock(
                    block_id=f"{metadata.doc_id}_tbl_1",
                    block_type=StructuredBlockType.table,
                    section_path=["Sheet1"],
                    table_rows=[["col_1", "col_2"], ["val_1", "val_2"]],
                )
            ],
        )
        return StructuredDocument(**metadata.model_dump(), sections=[section])
