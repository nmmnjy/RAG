from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.retrieval import HybridRetrieveHit, RerankRequest


class Reranker(ABC):
    @abstractmethod
    def rerank(self, request: RerankRequest) -> list[HybridRetrieveHit]:
        raise NotImplementedError


class NoopReranker(Reranker):
    def rerank(self, request: RerankRequest) -> list[HybridRetrieveHit]:
        return request.hits[: request.top_k]

