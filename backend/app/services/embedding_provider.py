from __future__ import annotations

from abc import ABC, abstractmethod
from hashlib import sha256


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def model_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic mock provider for local development and tests."""

    def __init__(self, model_name: str = "mock-embedding-v1", embedding_dim: int = 8) -> None:
        self._model_name = model_name
        self._embedding_dim = embedding_dim

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            digest = sha256(text.encode("utf-8")).digest()
            vector: list[float] = []
            for index in range(self._embedding_dim):
                raw = digest[index % len(digest)]
                vector.append((raw / 255.0) * 2.0 - 1.0)
            vectors.append(vector)
        return vectors

