from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.retrieval import HybridRetrieveHit, RerankRequest


class Reranker(ABC):
    @property
    @abstractmethod
    def reranker_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def rerank(self, request: RerankRequest) -> list[HybridRetrieveHit]:
        """
        Rerank candidates without changing retrieval contract fields.
        Implementations should preserve `chunk_id`, `score_vector`, `score_keyword`,
        and only adjust order or `score_final` when needed.
        """
        raise NotImplementedError


class NoopReranker(Reranker):
    @property
    def reranker_name(self) -> str:
        return "noop"

    def rerank(self, request: RerankRequest) -> list[HybridRetrieveHit]:
        return request.hits[: request.top_k]
