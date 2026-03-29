from __future__ import annotations

from app.core.errors import AppError, ERROR_CODE
from app.repositories.vector_repository import VectorRepository
from app.schemas.vectorization import (
    VectorQueryHit,
    VectorQueryRequest,
    VectorRecord,
    VectorWriteMode,
    VectorWriteRequest,
    VectorWriteResult,
)
from app.services.embedding_provider import EmbeddingErrorCode, EmbeddingProviderError
from app.services.vectorization_service import VectorizationService


class VectorStoreService:
    def __init__(
        self,
        repository: VectorRepository,
        vectorization_service: VectorizationService,
        embedding_max_retry: int = 2,
        repository_max_retry: int = 2,
    ) -> None:
        self._repository = repository
        self._vectorization_service = vectorization_service
        self._embedding_max_retry = max(embedding_max_retry, 1)
        self._repository_max_retry = max(repository_max_retry, 1)

    def write_vectors(self, request: VectorWriteRequest) -> VectorWriteResult:
        vectorization_input = request.vectorization_input
        requested_chunk_count = len(vectorization_input.chunks)
        existing_records = self._run_repo_with_retry(
            op=self._repository.list_by_doc_id,
            args=(vectorization_input.kb_id, vectorization_input.doc_id),
            error_code=ERROR_CODE.VECTOR_WRITE_FAILED,
            message="vector write failed when listing existing records",
        )
        existing_by_chunk_id = {item.chunk_id: item for item in existing_records}
        input_chunk_ids = {item.chunk_id for item in vectorization_input.chunks}

        deleted_count = 0
        if request.mode == VectorWriteMode.rebuild:
            deleted_count += self._run_repo_with_retry(
                op=self._repository.delete_by_doc_id,
                args=(vectorization_input.kb_id, vectorization_input.doc_id),
                error_code=ERROR_CODE.VECTOR_DELETE_FAILED,
                message="vector delete by doc failed",
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
                deleted_count += self._run_repo_with_retry(
                    op=self._repository.delete_by_chunk_ids,
                    args=(vectorization_input.kb_id, vectorization_input.doc_id, stale_chunk_ids),
                    error_code=ERROR_CODE.VECTOR_DELETE_FAILED,
                    message="vector delete by chunk ids failed",
                )
        else:
            candidate_chunks = vectorization_input.chunks

        records_to_upsert = self._vectorize_with_retry(
            request=request,
            chunks=candidate_chunks,
        )
        upserted_count = self._run_repo_with_retry(
            op=self._repository.upsert_many,
            args=(records_to_upsert,),
            error_code=ERROR_CODE.VECTOR_UPSERT_FAILED,
            message="vector upsert failed",
        )
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

    def _vectorize_with_retry(self, request: VectorWriteRequest, chunks: list) -> list[VectorRecord]:
        last_error: Exception | None = None
        for _ in range(self._embedding_max_retry):
            try:
                return self._vectorization_service.vectorize_chunks(
                    vectorization_input=request.vectorization_input,
                    chunks=chunks,
                )
            except EmbeddingProviderError as exc:
                last_error = exc
                error_code = self._map_embedding_error_code(exc.code)
                app_error = AppError(
                    code=error_code,
                    message=exc.message,
                    status_code=502,
                    details={"mode": request.mode.value},
                )
                last_error = app_error
            except Exception as exc:  # noqa: BLE001
                last_error = AppError(
                    code=ERROR_CODE.EMBEDDING_REQUEST_FAILED,
                    message="embedding request failed",
                    status_code=502,
                    details={"mode": request.mode.value},
                )
        assert last_error is not None
        if isinstance(last_error, AppError):
            raise last_error
        raise AppError(
            code=ERROR_CODE.EMBEDDING_REQUEST_FAILED,
            message="embedding request failed",
            status_code=502,
        ) from last_error

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

    def _run_repo_with_retry(
        self,
        *,
        op,
        args: tuple,
        error_code: str,
        message: str,
    ):
        last_exception: Exception | None = None
        for _ in range(self._repository_max_retry):
            try:
                return op(*args)
            except Exception as exc:  # noqa: BLE001
                last_exception = exc
        raise AppError(
            code=error_code,
            message=message,
            status_code=500,
        ) from last_exception

    @staticmethod
    def _map_embedding_error_code(code: str) -> str:
        if code == EmbeddingErrorCode.dim_mismatch.value:
            return ERROR_CODE.EMBEDDING_DIM_MISMATCH
        if code == EmbeddingErrorCode.invalid_response.value:
            return ERROR_CODE.EMBEDDING_INVALID_RESPONSE
        return ERROR_CODE.EMBEDDING_REQUEST_FAILED
