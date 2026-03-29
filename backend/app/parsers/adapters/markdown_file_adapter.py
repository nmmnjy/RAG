from __future__ import annotations

from pathlib import Path

from app.core.errors import AppError, ERROR_CODE
from app.parsers.adapters.base import ParseInput, ParserAdapter
from app.schemas.document_parse import StructuredBlock, StructuredBlockType, StructuredDocument, StructuredSection


class MarkdownFileParserAdapter(ParserAdapter):
    @property
    def adapter_name(self) -> str:
        return "markdown_file_parser_adapter"

    def parse(self, parse_input: ParseInput) -> StructuredDocument:
        metadata = parse_input.metadata
        file_path = parse_input.file_path
        if not file_path:
            raise AppError(
                code=ERROR_CODE.DOC_SOURCE_INVALID,
                message="missing file_path for markdown real parser",
                status_code=400,
            )
        path = Path(file_path)
        if not path.exists():
            raise AppError(
                code=ERROR_CODE.DOC_SOURCE_NOT_FOUND,
                message="markdown source file not found",
                status_code=404,
                details={"file_path": file_path},
            )

        lines = path.read_text(encoding="utf-8").splitlines()
        sections: list[StructuredSection] = []
        current_title = "Root"
        current_path = [current_title]
        blocks: list[StructuredBlock] = []
        section_index = 1
        block_index = 1

        def flush_section() -> None:
            nonlocal blocks, section_index
            if not blocks:
                return
            sections.append(
                StructuredSection(
                    section_id=f"{metadata.doc_id}_md_sec_{section_index}",
                    title=current_title,
                    heading_level=max(1, len(current_path)),
                    section_path=list(current_path),
                    blocks=blocks,
                )
            )
            section_index += 1
            blocks = []

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("#"):
                flush_section()
                heading = line.lstrip("#").strip() or "Untitled"
                level = len(line) - len(line.lstrip("#"))
                current_title = heading
                current_path = [f"H{level}:{heading}"]
                continue
            blocks.append(
                StructuredBlock(
                    block_id=f"{metadata.doc_id}_md_blk_{block_index}",
                    block_type=StructuredBlockType.paragraph,
                    content=line,
                    section_path=list(current_path),
                )
            )
            block_index += 1

        flush_section()
        if not sections:
            sections = [
                StructuredSection(
                    section_id=f"{metadata.doc_id}_md_sec_1",
                    title="Root",
                    heading_level=1,
                    section_path=["Root"],
                    blocks=[],
                )
            ]
        return StructuredDocument(**metadata.model_dump(), sections=sections)
