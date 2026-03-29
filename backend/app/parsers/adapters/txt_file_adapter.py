from __future__ import annotations

from pathlib import Path

from app.core.errors import AppError, ERROR_CODE
from app.parsers.adapters.base import ParseInput, ParserAdapter
from app.schemas.document_parse import StructuredBlock, StructuredBlockType, StructuredDocument, StructuredSection


class TxtFileParserAdapter(ParserAdapter):
    @property
    def adapter_name(self) -> str:
        return "txt_file_parser_adapter"

    def parse(self, parse_input: ParseInput) -> StructuredDocument:
        metadata = parse_input.metadata
        file_path = parse_input.file_path
        if not file_path:
            raise AppError(
                code=ERROR_CODE.DOC_PARSE_FAILED,
                message="missing file_path for txt real parser",
                status_code=400,
            )
        path = Path(file_path)
        if not path.exists():
            raise AppError(
                code=ERROR_CODE.DOC_PARSE_FAILED,
                message="txt source file not found",
                status_code=400,
                details={"file_path": file_path},
            )

        content = path.read_text(encoding="utf-8")
        paragraphs = [item.strip() for item in content.split("\n\n") if item.strip()]
        blocks = [
            StructuredBlock(
                block_id=f"{metadata.doc_id}_txt_blk_{index + 1}",
                block_type=StructuredBlockType.paragraph,
                content=paragraph,
                section_path=["TXT Root Section"],
            )
            for index, paragraph in enumerate(paragraphs)
        ]
        section = StructuredSection(
            section_id=f"{metadata.doc_id}_txt_sec_1",
            title="TXT Root Section",
            heading_level=1,
            section_path=["TXT Root Section"],
            blocks=blocks,
        )
        return StructuredDocument(**metadata.model_dump(), sections=[section])
