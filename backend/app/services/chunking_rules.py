from __future__ import annotations

import re

from app.schemas.chunking import SpecialStructureType
from app.schemas.document_parse import StructuredBlock, StructuredBlockType


_LIST_PREFIX_PATTERN = re.compile(r"^(\-|\*|\+|\d+\.)\s+")
_CODE_FENCE_PATTERN = re.compile(r"^```")


def estimate_token_count(text: str) -> int:
    normalized = text.strip()
    if not normalized:
        return 0
    return len(normalized.split())


def detect_special_structure(block: StructuredBlock) -> SpecialStructureType | None:
    if block.block_type == StructuredBlockType.table:
        return SpecialStructureType.table

    content = block.content.strip()
    if not content:
        return None
    if content.startswith("```") and content.endswith("```"):
        return SpecialStructureType.code
    if _LIST_PREFIX_PATTERN.match(content):
        return SpecialStructureType.list
    return None


def is_code_fence_line(content: str) -> bool:
    return bool(_CODE_FENCE_PATTERN.match(content.strip()))


def split_text_to_sentence_units(content: str) -> list[str]:
    normalized = content.strip()
    if not normalized:
        return []
    parts = re.split(r"(?<=[。！？!?；;.])\s*", normalized)
    return [item.strip() for item in parts if item.strip()]


def render_block_content(block: StructuredBlock) -> str:
    if block.block_type == StructuredBlockType.table and block.table_rows:
        rows = [" | ".join(row) for row in block.table_rows]
        return "\n".join(rows)
    return block.content.strip()
