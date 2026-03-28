from __future__ import annotations

from app.repositories.vector_repository import VectorRepository
from app.schemas.vectorization import (
    VectorQueryHit,
    VectorQueryRequest,
    VectorRecord,
    VectorWriteMode,
    VectorWriteRequest,
    VectorWriteResult,
)
from app.services.vectorization_service import VectorizationService


class VectorStoreService:
    def __init__(self, repository: VectorRepository, vectorization_service: VectorizationService) -> None:
        self._repository = repository
        self._vectorization_service = vectorization_service

    def write_vectors(self, request: VectorWriteRequest) -> VectorWriteResult:
        vectorization_input = request.vectorization_input
        requested_chunk_count = len(vectorization_input.chunks)
        existing_records = self._repository.list_by_doc_id(
            kb_id=vectorization_input.kb_id,
            doc_id=vectorization_input.doc_id,
        )
        existing_by_chunk_id = {item.chunk_id: item for item in existing_records}
        input_chunk_ids = {item.chunk_id for item in vectorization_input.chunks}

        deleted_count = 0
        if request.mode == VectorWriteMode.rebuild:
            deleted_count += self._repository.delete_by_doc_id(
                kb_id=vectorization_input.kb_id,
                doc_id=vectorization_input.doc_id,
            )
            candidate_chunks = vectorization_input.chunks
        elif request.mode == VectorWriteMode.incremental_update:
            candidate_chunks = self._select_incremental_chunks(
                request=request,
                existing_by_chunk_id=existing_by_chunk_id,
            )
            stale_chunk_ids = [
                item.chunk_id for item in existing_records if item.chunk_id not in input_chunk_ids
            ]
            if stale_chunk_ids:
                deleted_count += self._repository.delete_by_chunk_ids(
                    kb_id=vectorization_input.kb_id,
                    doc_id=vectorization_input.doc_id,
                    chunk_ids=stale_chunk_ids,
                )
        else:
            candidate_chunks = vectorization_input.chunks

        records_to_upsert = self._vectorization_service.vectorize_chunks(
            vectorization_input=vectorization_input,
            chunks=candidate_chunks,
        )
        upserted_count = self._repository.upsert_many(records_to_upsert)
        skipped_count = requested_chunk_count - len(candidate_chunks)

        return VectorWriteResult(
            mode=request.mode,
            kb_id=vectorization_input.kb_id,
            doc_id=vectorization_input.doc_id,
            requested_chunk_count=requested_chunk_count,
            embedded_chunk_count=len(candidate_chunks),
            upserted_count=upserted_count,
            deleted_count=deleted_count,
            skipped_count=max(skipped_count, 0),
        )

    def query_similar(self, request: VectorQueryRequest) -> list[VectorQueryHit]:
        return self._repository.query_similar(request)

    def _select_incremental_chunks(
        self,
        request: VectorWriteRequest,
        existing_by_chunk_id: dict[str, VectorRecord],
    ) -> list:
        vectorization_input = request.vectorization_input
        changed_chunk_id_set = set(request.changed_chunk_ids)
        selected = []
        for chunk in vectorization_input.chunks:
            if changed_chunk_id_set:
                if chunk.chunk_id in changed_chunk_id_set:
                    selected.append(chunk)
                continue
            existing = existing_by_chunk_id.get(chunk.chunk_id)
            if existing is None:
                selected.append(chunk)
                continue
            current_hash = VectorRecord.build_content_hash(chunk)
            if existing.content_hash != current_hash:
                selected.append(chunk)
        return selected

