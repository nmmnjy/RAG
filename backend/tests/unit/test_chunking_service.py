import json
from pathlib import Path

import pytest

from app.core.errors import AppError
from app.schemas.chunking import ChunkBuildParams, SpecialStructureType
from app.schemas.document_parse import StructuredDocument
from app.services.chunking_service import chunking_service


def _load_document_from_fixture(file_name: str) -> StructuredDocument:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "02_semantic_chunking"
        / file_name
    )
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    return StructuredDocument(**payload)


def _load_sample_document() -> StructuredDocument:
    return _load_document_from_fixture("structured_document_sample.json")


def test_default_chunking_strategy_can_build_chunks() -> None:
    document = _load_sample_document()
    result = chunking_service.build_chunks(document)

    assert result.doc_id == document.doc_id
    assert result.kb_id == document.kb_id
    assert result.strategy_name == "structured_window"
    assert result.strategy_version == "2026.03.02"
    assert result.chunk_count > 0
    for chunk in result.chunks:
        assert chunk.chunk_id
        assert chunk.doc_id == document.doc_id
        assert chunk.content
        assert chunk.token_count > 0
        assert isinstance(chunk.section_path, list)


def test_table_block_should_be_preserved_as_special_chunk() -> None:
    document = _load_sample_document()
    result = chunking_service.build_chunks(document)

    table_chunks = [item for item in result.chunks if item.special_structure == SpecialStructureType.table]
    assert table_chunks
    assert "字段 | 说明" in table_chunks[0].content


def test_invalid_chunk_params_should_raise_validation_error() -> None:
    document = _load_sample_document()
    params = ChunkBuildParams(max_tokens_per_chunk=100, overlap_tokens=100)
    with pytest.raises(AppError):
        chunking_service.build_chunks(document, params=params)


def test_markdown_real_like_output_should_keep_heading_boundary_and_code_fence_chunk() -> None:
    document = _load_document_from_fixture("structured_document_markdown_real_like.json")
    params = ChunkBuildParams(max_tokens_per_chunk=64, overlap_tokens=8, preserve_code_block=True)
    result = chunking_service.build_chunks(document, params=params)

    assert result.chunk_count >= 2
    code_chunks = [chunk for chunk in result.chunks if chunk.special_structure == SpecialStructureType.code]
    assert code_chunks
    assert "```python" in code_chunks[0].content
    assert "print('hello from fenced code')" in code_chunks[0].content
    assert code_chunks[0].section_path == ["H1:Intro"]

    details_chunks = [chunk for chunk in result.chunks if chunk.section_path == ["H2:Details"]]
    assert details_chunks


def test_txt_real_like_output_should_split_long_paragraph_into_multiple_chunks() -> None:
    document = _load_document_from_fixture("structured_document_txt_real_like.json")
    params = ChunkBuildParams(max_tokens_per_chunk=32, overlap_tokens=4)
    result = chunking_service.build_chunks(document, params=params)

    assert result.chunk_count >= 2
    assert "Sentence one" in result.chunks[0].content
    for chunk in result.chunks:
        assert chunk.token_count <= 32
