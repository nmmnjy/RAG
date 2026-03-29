from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.errors import AppError, ERROR_CODE
from app.schemas.chunking import (
    ChunkBuildParams,
    ChunkBuildResult,
    ChunkRecord,
    ChunkStrategyName,
    SpecialStructureType,
)
from app.schemas.document_parse import StructuredBlock, StructuredDocument
from app.services.chunking_rules import (
    detect_special_structure,
    estimate_token_count,
    is_code_fence_line,
    render_block_content,
    split_text_to_sentence_units,
)


def _split_tokens(text: str) -> list[str]:
    normalized = text.strip()
    if not normalized:
        return []
    return normalized.split()


@dataclass
class _ChunkDraft:
    texts: list[str]
    section_path: list[str]
    source_block_ids: list[str]

    def token_count(self) -> int:
        return estimate_token_count(" ".join(self.texts))

    def content(self) -> str:
        return "\n\n".join([item for item in self.texts if item])


class ChunkingStrategy(ABC):
    @property
    @abstractmethod
    def strategy_name(self) -> ChunkStrategyName:
        raise NotImplementedError

    @property
    @abstractmethod
    def strategy_version(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def build(self, document: StructuredDocument, params: ChunkBuildParams) -> list[ChunkRecord]:
        raise NotImplementedError


class StructuredWindowChunkingStrategy(ChunkingStrategy):
    @property
    def strategy_name(self) -> ChunkStrategyName:
        return ChunkStrategyName.structured_window

    @property
    def strategy_version(self) -> str:
        return "2026.03.02"

    def build(self, document: StructuredDocument, params: ChunkBuildParams) -> list[ChunkRecord]:
        chunks: list[ChunkRecord] = []
        draft = _ChunkDraft(texts=[], section_path=[], source_block_ids=[])
        chunk_index = 0

        def flush_draft() -> None:
            nonlocal chunk_index
            if not draft.texts:
                return
            content = draft.content()
            token_count = draft.token_count()
            if token_count == 0:
                draft.texts.clear()
                draft.section_path.clear()
                draft.source_block_ids.clear()
                return
            chunks.append(
                self._to_chunk_record(
                    document=document,
                    chunk_index=chunk_index,
                    content=content,
                    token_count=token_count,
                    section_path=draft.section_path,
                    source_block_ids=draft.source_block_ids,
                    special_structure=None,
                    params=params,
                )
            )
            chunk_index += 1
            draft.texts.clear()
            draft.section_path.clear()
            draft.source_block_ids.clear()

        for section in document.sections:
            block_cursor = 0
            while block_cursor < len(section.blocks):
                block = section.blocks[block_cursor]
                content = render_block_content(block)
                if not content:
                    block_cursor += 1
                    continue

                block_section_path = block.section_path or section.section_path
                if params.split_on_section_path_change and draft.texts and draft.section_path != block_section_path:
                    flush_draft()

                code_fence_chunk = self._collect_code_fence_chunk(
                    section_blocks=section.blocks,
                    start_index=block_cursor,
                    section_path=block_section_path,
                )
                if code_fence_chunk and params.preserve_code_block:
                    merged_code_content, consumed_block_ids, consumed_blocks = code_fence_chunk
                    flush_draft()
                    chunks.append(
                        self._to_chunk_record(
                            document=document,
                            chunk_index=chunk_index,
                            content=merged_code_content,
                            token_count=estimate_token_count(merged_code_content),
                            section_path=block_section_path,
                            source_block_ids=consumed_block_ids,
                            special_structure=SpecialStructureType.code,
                            params=params,
                        )
                    )
                    chunk_index += 1
                    block_cursor += consumed_blocks
                    continue

                special_structure = detect_special_structure(block)
                should_preserve = (
                    special_structure == SpecialStructureType.table
                    and params.preserve_table_block
                    or special_structure == SpecialStructureType.list
                    and params.preserve_list_block
                    or special_structure == SpecialStructureType.code
                    and params.preserve_code_block
                )
                block_token_count = estimate_token_count(content)

                if should_preserve:
                    flush_draft()
                    chunks.append(
                        self._to_chunk_record(
                            document=document,
                            chunk_index=chunk_index,
                            content=content,
                            token_count=block_token_count,
                            section_path=block_section_path,
                            source_block_ids=[block.block_id],
                            special_structure=special_structure,
                            params=params,
                        )
                    )
                    chunk_index += 1
                    block_cursor += 1
                    continue

                if block_token_count > params.max_tokens_per_chunk:
                    flush_draft()
                    windows = self._split_long_content(
                        content=content,
                        max_tokens=params.max_tokens_per_chunk,
                        overlap_tokens=params.overlap_tokens,
                        sentence_boundary_first=params.sentence_boundary_fallback_split,
                    )
                    for window in windows:
                        if estimate_token_count(window) < params.min_chunk_tokens and chunks:
                            previous = chunks[-1]
                            merged_content = f"{previous.content}\n\n{window}".strip()
                            merged_tokens = estimate_token_count(merged_content)
                            if merged_tokens <= params.max_tokens_per_chunk:
                                previous.content = merged_content
                                previous.token_count = merged_tokens
                                continue
                        chunks.append(
                            self._to_chunk_record(
                                document=document,
                                chunk_index=chunk_index,
                                content=window,
                                token_count=estimate_token_count(window),
                                section_path=block_section_path,
                                source_block_ids=[block.block_id],
                                special_structure=None,
                                params=params,
                            )
                        )
                        chunk_index += 1
                    block_cursor += 1
                    continue

                merged_content = "\n\n".join(draft.texts + [content]).strip()
                merged_token_count = estimate_token_count(merged_content)
                if merged_token_count > params.max_tokens_per_chunk and draft.texts:
                    flush_draft()

                draft.texts.append(content)
                draft.section_path = block_section_path
                draft.source_block_ids.append(block.block_id)
                block_cursor += 1

            flush_draft()
        return chunks

    def _split_long_content(
        self,
        content: str,
        max_tokens: int,
        overlap_tokens: int,
        sentence_boundary_first: bool,
    ) -> list[str]:
        if sentence_boundary_first:
            sentence_units = split_text_to_sentence_units(content)
            if sentence_units:
                windows = self._split_by_sentence_units(
                    sentence_units,
                    max_tokens=max_tokens,
                    overlap_tokens=overlap_tokens,
                )
                if windows:
                    return windows
        return self._split_by_fixed_token_window(content, max_tokens=max_tokens, overlap_tokens=overlap_tokens)

    def _split_by_sentence_units(
        self,
        sentence_units: list[str],
        max_tokens: int,
        overlap_tokens: int,
    ) -> list[str]:
        del overlap_tokens
        windows: list[str] = []
        unit_cursor = 0
        while unit_cursor < len(sentence_units):
            draft_units: list[str] = []
            while unit_cursor < len(sentence_units):
                candidate_units = draft_units + [sentence_units[unit_cursor]]
                if estimate_token_count(" ".join(candidate_units)) <= max_tokens:
                    draft_units = candidate_units
                    unit_cursor += 1
                else:
                    break

            if not draft_units:
                fixed_windows = self._split_by_fixed_token_window(
                    sentence_units[unit_cursor],
                    max_tokens=max_tokens,
                    overlap_tokens=overlap_tokens,
                )
                windows.extend(fixed_windows)
                unit_cursor += 1
                continue

            windows.append(" ".join(draft_units))
            if unit_cursor >= len(sentence_units):
                break
        return windows

    def _split_by_fixed_token_window(self, content: str, max_tokens: int, overlap_tokens: int) -> list[str]:
        tokens = _split_tokens(content)
        if not tokens:
            return []

        windows: list[str] = []
        start = 0
        while start < len(tokens):
            end = min(start + max_tokens, len(tokens))
            windows.append(" ".join(tokens[start:end]))
            if end >= len(tokens):
                break
            start = end - overlap_tokens
        return windows

    def _collect_code_fence_chunk(
        self,
        section_blocks: list[StructuredBlock],
        start_index: int,
        section_path: list[str],
    ) -> tuple[str, list[str], int] | None:
        start_block = section_blocks[start_index]
        start_content = render_block_content(start_block)
        if not is_code_fence_line(start_content):
            return None

        start_fence_count = sum(1 for line in start_content.splitlines() if is_code_fence_line(line))
        if start_fence_count >= 2:
            return start_content.strip(), [start_block.block_id], 1

        collected_texts = [start_content]
        collected_block_ids = [start_block.block_id]
        consumed_count = 1
        found_closing_fence = False

        for scan_index in range(start_index + 1, len(section_blocks)):
            scan_block = section_blocks[scan_index]
            scan_content = render_block_content(scan_block)
            if not scan_content:
                continue
            if (scan_block.section_path or section_path) != section_path:
                break
            collected_texts.append(scan_content)
            collected_block_ids.append(scan_block.block_id)
            consumed_count += 1
            if is_code_fence_line(scan_content):
                found_closing_fence = True
                break

        if not found_closing_fence:
            return None
        return "\n".join(collected_texts).strip(), collected_block_ids, consumed_count

    def _to_chunk_record(
        self,
        document: StructuredDocument,
        chunk_index: int,
        content: str,
        token_count: int,
        section_path: list[str],
        source_block_ids: list[str],
        special_structure: SpecialStructureType | None,
        params: ChunkBuildParams,
    ) -> ChunkRecord:
        return ChunkRecord(
            chunk_id=f"chk_{document.doc_id}_{chunk_index:04d}",
            doc_id=document.doc_id,
            kb_id=document.kb_id,
            content=content,
            token_count=token_count,
            section_path=section_path,
            chunk_index=chunk_index,
            strategy_name=params.strategy_name,
            strategy_version=params.strategy_version,
            source_block_ids=source_block_ids,
            special_structure=special_structure,
        )


class ChunkingService:
    def __init__(self) -> None:
        self._strategies: dict[ChunkStrategyName, ChunkingStrategy] = {
            ChunkStrategyName.structured_window: StructuredWindowChunkingStrategy()
        }

    def build_chunks(
        self,
        document: StructuredDocument,
        params: ChunkBuildParams | None = None,
    ) -> ChunkBuildResult:
        resolved_params = params or ChunkBuildParams()
        self._validate_params(resolved_params)
        strategy = self._strategies.get(resolved_params.strategy_name)
        if not strategy:
            raise AppError(
                code=ERROR_CODE.COMMON_INVALID_ARGUMENT,
                message="unsupported chunk strategy",
                status_code=400,
                details={"strategy_name": resolved_params.strategy_name.value},
            )

        try:
            chunks = strategy.build(document, resolved_params)
        except AppError:
            raise
        except Exception as exc:
            raise AppError(
                code=ERROR_CODE.CHUNK_BUILD_FAILED,
                message="chunk build failed",
                status_code=500,
                details={"safe_message": str(exc)},
            ) from exc

        return ChunkBuildResult(
            doc_id=document.doc_id,
            kb_id=document.kb_id,
            source=document.source,
            format=document.format,
            version=document.version,
            strategy_name=resolved_params.strategy_name,
            strategy_version=resolved_params.strategy_version,
            params=resolved_params,
            chunk_count=len(chunks),
            chunks=chunks,
        )

    def _validate_params(self, params: ChunkBuildParams) -> None:
        if params.overlap_tokens >= params.max_tokens_per_chunk:
            raise AppError(
                code=ERROR_CODE.COMMON_INVALID_ARGUMENT,
                message="overlap_tokens must be less than max_tokens_per_chunk",
                status_code=400,
            )
        if params.min_chunk_tokens > params.max_tokens_per_chunk:
            raise AppError(
                code=ERROR_CODE.COMMON_INVALID_ARGUMENT,
                message="min_chunk_tokens must be less than or equal to max_tokens_per_chunk",
                status_code=400,
            )


chunking_service = ChunkingService()
