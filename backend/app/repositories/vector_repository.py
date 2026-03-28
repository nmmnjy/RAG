from __future__ import annotations

from abc import ABC, abstractmethod
from math import sqrt

from app.schemas.vectorization import VectorQueryHit, VectorQueryRequest, VectorRecord


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    numerator = sum(x * y for x, y in zip(left, right, strict=False))
    left_norm = sqrt(sum(x * x for x in left))
    right_norm = sqrt(sum(y * y for y in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


class VectorRepository(ABC):
    @abstractmethod
    def upsert_many(self, records: list[VectorRecord]) -> int:
        raise NotImplementedError

    @abstractmethod
    def list_by_doc_id(self, kb_id: str, doc_id: str) -> list[VectorRecord]:
        raise NotImplementedError

    @abstractmethod
    def delete_by_doc_id(self, kb_id: str, doc_id: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def delete_by_chunk_ids(self, kb_id: str, doc_id: str, chunk_ids: list[str]) -> int:
        raise NotImplementedError

    @abstractmethod
    def query_similar(self, request: VectorQueryRequest) -> list[VectorQueryHit]:
        raise NotImplementedError


class InMemoryVectorRepository(VectorRepository):
    def __init__(self) -> None:
        self._records: dict[str, VectorRecord] = {}

    def upsert_many(self, records: list[VectorRecord]) -> int:
        for record in records:
            self._records[record.vector_id] = record
        return len(records)

    def list_by_doc_id(self, kb_id: str, doc_id: str) -> list[VectorRecord]:
        return [
            item
            for item in self._records.values()
            if item.kb_id == kb_id and item.doc_id == doc_id
        ]

    def delete_by_doc_id(self, kb_id: str, doc_id: str) -> int:
        keys = [
            key
            for key, record in self._records.items()
            if record.kb_id == kb_id and record.doc_id == doc_id
        ]
        for key in keys:
            del self._records[key]
        return len(keys)

    def delete_by_chunk_ids(self, kb_id: str, doc_id: str, chunk_ids: list[str]) -> int:
        chunk_id_set = set(chunk_ids)
        keys = [
            key
            for key, record in self._records.items()
            if record.kb_id == kb_id
            and record.doc_id == doc_id
            and record.chunk_id in chunk_id_set
        ]
        for key in keys:
            del self._records[key]
        return len(keys)

    def query_similar(self, request: VectorQueryRequest) -> list[VectorQueryHit]:
        candidates = [
            item
            for item in self._records.values()
            if item.kb_id == request.kb_id and (request.doc_id is None or item.doc_id == request.doc_id)
        ]
        hits: list[VectorQueryHit] = []
        for record in candidates:
            score = _cosine_similarity(request.query_embedding, record.embedding)
            hits.append(
                VectorQueryHit(
                    chunk_id=record.chunk_id,
                    doc_id=record.doc_id,
                    kb_id=record.kb_id,
                    content=record.content,
                    section_path=record.section_path,
                    score_vector=score,
                    citation={
                        "source": record.source,
                        "doc_id": record.doc_id,
                        "chunk_id": record.chunk_id,
                        "section_path": record.section_path,
                    },
                    metadata=record.metadata,
                )
            )
        hits.sort(key=lambda item: item.score_vector, reverse=True)
        return hits[: request.top_k]


vector_repository = InMemoryVectorRepository()

