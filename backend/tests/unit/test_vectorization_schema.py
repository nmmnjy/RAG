import json
from pathlib import Path

from app.schemas.document_parse import StructuredDocument
from app.schemas.vectorization import VectorRecord, VectorizationInput
from app.services.chunking_service import chunking_service
from app.services.embedding_provider import MockEmbeddingProvider


def _load_sample_document() -> StructuredDocument:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "02_semantic_chunking"
        / "structured_document_sample.json"
    )
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    return StructuredDocument(**payload)


def test_vectorization_input_should_directly_consume_chunk_build_result() -> None:
    document = _load_sample_document()
    chunk_result = chunking_service.build_chunks(document)
    vector_input = VectorizationInput(**chunk_result.model_dump())
    assert vector_input.doc_id == chunk_result.doc_id
    assert vector_input.chunks[0].chunk_id == chunk_result.chunks[0].chunk_id


def test_vector_record_should_keep_minimum_linking_fields() -> None:
    document = _load_sample_document()
    chunk_result = chunking_service.build_chunks(document)
    chunk = chunk_result.chunks[0]
    embedding = MockEmbeddingProvider(embedding_dim=6).embed_texts([chunk.content])[0]
    record = VectorRecord(
        vector_id=f"vec_{document.doc_id}_{chunk.chunk_id}",
        kb_id=document.kb_id,
        doc_id=document.doc_id,
        chunk_id=chunk.chunk_id,
        content=chunk.content,
        token_count=chunk.token_count,
        section_path=chunk.section_path,
        source=document.source,
        format=document.format,
        version=document.version,
        chunk_index=chunk.chunk_index,
        strategy_name=chunk.strategy_name.value,
        strategy_version=chunk.strategy_version,
        embedding_provider="mock",
        embedding_model="mock-embedding-v1",
        embedding_dim=6,
        embedding=embedding,
        content_hash=VectorRecord.build_content_hash(chunk),
    )
    assert record.doc_id == document.doc_id
    assert record.chunk_id == chunk.chunk_id
    assert record.embedding_dim == 6

