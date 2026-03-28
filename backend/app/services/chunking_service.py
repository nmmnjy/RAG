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
from app.schemas.document_parse import StructuredDocument
from app.services.chunking_rules import detect_special_structure, estimate_token_count, render_block_content


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
        return "2026.03.01"

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
            for block in section.blocks:
                content = render_block_content(block)
                if not content:
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
                block_section_path = block.section_path or section.section_path
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
                    continue

                if block_token_count > params.max_tokens_per_chunk:
                    flush_draft()
                    windows = self._split_long_content(
                        content=content,
                        max_tokens=params.max_tokens_per_chunk,
                        overlap_tokens=params.overlap_tokens,
                    )
                    for window in windows:
                        if estimate_token_count(window) < params.min_chunk_tokens and chunks:
                            previous = chunks[-1]
                            previous.content = f"{previous.content}\n\n{window}".strip()
                            previous.token_count = estimate_token_count(previous.content)
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
                    continue

                merged_content = "\n\n".join(draft.texts + [content]).strip()
                merged_token_count = estimate_token_count(merged_content)
                if merged_token_count > params.max_tokens_per_chunk and draft.texts:
                    flush_draft()

                draft.texts.append(content)
                draft.section_path = block_section_path
                draft.source_block_ids.append(block.block_id)

            flush_draft()
        return chunks

    def _split_long_content(self, content: str, max_tokens: int, overlap_tokens: int) -> list[str]:
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
