import json
from pathlib import Path

import pytest

from app.core.errors import AppError, ERROR_CODE
from app.repositories.vector_repository import InMemoryVectorRepository
from app.schemas.vectorization import (
    VectorQueryRequest,
    VectorWriteMode,
    VectorWriteRequest,
    VectorizationInput,
)
from app.schemas.document_parse import StructuredDocument
from app.services.chunking_service import chunking_service
from app.services.embedding_provider import (
    EmbeddingErrorCode,
    EmbeddingProvider,
    EmbeddingProviderError,
    MockEmbeddingProvider,
)
from app.services.vector_store_service import VectorStoreService
from app.services.vectorization_service import VectorizationService


def _load_sample_document() -> StructuredDocument:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "02_semantic_chunking"
        / "structured_document_sample.json"
    )
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    return StructuredDocument(**payload)


def _build_store_service() -> tuple[VectorStoreService, InMemoryVectorRepository]:
    repository = InMemoryVectorRepository()
    vectorization_service = VectorizationService(provider=MockEmbeddingProvider(embedding_dim=12))
    return VectorStoreService(repository=repository, vectorization_service=vectorization_service), repository


def _as_vectorization_input(chunk_result) -> VectorizationInput:
    return VectorizationInput(**chunk_result.model_dump())


def test_initial_build_should_write_all_chunks() -> None:
    document = _load_sample_document()
    chunk_result = chunking_service.build_chunks(document)
    store_service, repository = _build_store_service()

    result = store_service.write_vectors(
        VectorWriteRequest(
            mode=VectorWriteMode.initial_build,
            vectorization_input=_as_vectorization_input(chunk_result),
        )
    )

    stored = repository.list_by_doc_id(kb_id=document.kb_id, doc_id=document.doc_id)
    assert result.upserted_count == chunk_result.chunk_count
    assert result.deleted_count == 0
    assert result.skipped_count == 0
    assert len(stored) == chunk_result.chunk_count
    assert stored[0].embedding_dim == 12


def test_rebuild_should_replace_existing_vectors() -> None:
    document = _load_sample_document()
    chunk_result = chunking_service.build_chunks(document)
    store_service, repository = _build_store_service()

    store_service.write_vectors(
        VectorWriteRequest(
            mode=VectorWriteMode.initial_build,
            vectorization_input=_as_vectorization_input(chunk_result),
        )
    )
    mutated = chunk_result.model_copy(deep=True)
    mutated.chunks = mutated.chunks[:2]
    mutated.chunk_count = len(mutated.chunks)

    result = store_service.write_vectors(
        VectorWriteRequest(
            mode=VectorWriteMode.rebuild,
            vectorization_input=_as_vectorization_input(mutated),
        )
    )

    stored = repository.list_by_doc_id(kb_id=document.kb_id, doc_id=document.doc_id)
    assert result.deleted_count > 0
    assert result.upserted_count == 2
    assert len(stored) == 2


def test_incremental_update_should_only_upsert_changed_chunks_and_cleanup_stale() -> None:
    document = _load_sample_document()
    chunk_result = chunking_service.build_chunks(document)
    store_service, repository = _build_store_service()

    store_service.write_vectors(
        VectorWriteRequest(
            mode=VectorWriteMode.initial_build,
            vectorization_input=_as_vectorization_input(chunk_result),
        )
    )

    mutated = chunk_result.model_copy(deep=True)
    mutated.chunks[0].content = f"{mutated.chunks[0].content}\n\n新增内容"
    mutated.chunks = mutated.chunks[:-1]
    mutated.chunk_count = len(mutated.chunks)

    result = store_service.write_vectors(
        VectorWriteRequest(
            mode=VectorWriteMode.incremental_update,
            vectorization_input=_as_vectorization_input(mutated),
        )
    )

    assert result.upserted_count == 1
    assert result.deleted_count == 1
    assert result.skipped_count == len(mutated.chunks) - 1

    query_text = mutated.chunks[0].content
    query_embedding = MockEmbeddingProvider(embedding_dim=12).embed_texts([query_text])[0]
    hits = store_service.query_similar(
        VectorQueryRequest(kb_id=document.kb_id, doc_id=document.doc_id, query_embedding=query_embedding, top_k=1)
    )
    assert hits
    assert hits[0].chunk_id == mutated.chunks[0].chunk_id
    assert hits[0].score_vector > 0


def test_repeated_initial_build_should_be_idempotent_on_vector_primary_key() -> None:
    document = _load_sample_document()
    chunk_result = chunking_service.build_chunks(document)
    store_service, repository = _build_store_service()
    vector_input = _as_vectorization_input(chunk_result)

    first = store_service.write_vectors(
        VectorWriteRequest(mode=VectorWriteMode.initial_build, vectorization_input=vector_input)
    )
    second = store_service.write_vectors(
        VectorWriteRequest(mode=VectorWriteMode.initial_build, vectorization_input=vector_input)
    )

    stored = repository.list_by_doc_id(kb_id=document.kb_id, doc_id=document.doc_id)
    assert first.upserted_count == chunk_result.chunk_count
    assert second.upserted_count == chunk_result.chunk_count
    assert len(stored) == chunk_result.chunk_count


class _AlwaysFailEmbeddingProvider(EmbeddingProvider):
    @property
    def provider_name(self) -> str:
        return "failing"

    @property
    def model_name(self) -> str:
        return "failing-model"

    @property
    def embedding_dim(self) -> int:
        return 3

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingProviderError(
            code=EmbeddingErrorCode.dim_mismatch.value,
            message="Embedding dimension mismatch: expected 3, got 2.",
        )


def test_write_vectors_should_raise_embedding_dim_mismatch_error_code_after_retry() -> None:
    document = _load_sample_document()
    chunk_result = chunking_service.build_chunks(document)
    repository = InMemoryVectorRepository()
    vectorization_service = VectorizationService(provider=_AlwaysFailEmbeddingProvider())
    store_service = VectorStoreService(
        repository=repository,
        vectorization_service=vectorization_service,
        embedding_max_retry=2,
    )

    with pytest.raises(AppError) as exc_info:
        store_service.write_vectors(
            VectorWriteRequest(
                mode=VectorWriteMode.initial_build,
                vectorization_input=_as_vectorization_input(chunk_result),
            )
        )

    assert exc_info.value.code == ERROR_CODE.EMBEDDING_DIM_MISMATCH
