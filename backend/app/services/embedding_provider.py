from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
from hashlib import sha256


class EmbeddingProviderType(str, Enum):
    mock = "mock"
    openai_compatible = "openai_compatible"


@dataclass(frozen=True)
class EmbeddingProviderConfig:
    provider_type: EmbeddingProviderType = EmbeddingProviderType.mock
    model_name: str = "mock-embedding-v1"
    embedding_dim: int = 12
    api_key: str = ""
    base_url: str = ""
    request_timeout_ms: int = 10000
    enable_real_provider: bool = False
    fallback_to_mock: bool = True


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


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    """
    Real provider integration slot.

    This class defines the boundary and config contract for a real embedding backend.
    The actual HTTP client call is intentionally left as a follow-up task.
    """

    def __init__(
        self,
        model_name: str,
        embedding_dim: int,
        api_key: str,
        base_url: str,
        request_timeout_ms: int = 10000,
    ) -> None:
        self._model_name = model_name
        self._embedding_dim = embedding_dim
        self._api_key = api_key
        self._base_url = base_url
        self._request_timeout_ms = request_timeout_ms

    @property
    def provider_name(self) -> str:
        return EmbeddingProviderType.openai_compatible.value

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError(
            "openai_compatible embedding provider wiring is not implemented yet; "
            "enable fallback or keep EMBEDDING_PROVIDER=mock"
        )


def build_embedding_provider(config: EmbeddingProviderConfig) -> EmbeddingProvider:
    if config.provider_type == EmbeddingProviderType.mock:
        return MockEmbeddingProvider(model_name=config.model_name, embedding_dim=config.embedding_dim)

    if config.provider_type == EmbeddingProviderType.openai_compatible:
        is_ready = (
            config.enable_real_provider
            and bool(config.api_key.strip())
            and bool(config.base_url.strip())
        )
        if is_ready:
            return OpenAICompatibleEmbeddingProvider(
                model_name=config.model_name,
                embedding_dim=config.embedding_dim,
                api_key=config.api_key,
                base_url=config.base_url,
                request_timeout_ms=config.request_timeout_ms,
            )
        if config.fallback_to_mock:
            return MockEmbeddingProvider(model_name=config.model_name, embedding_dim=config.embedding_dim)
        raise ValueError("real embedding provider is not ready and fallback_to_mock is disabled")

    if config.fallback_to_mock:
        return MockEmbeddingProvider(model_name=config.model_name, embedding_dim=config.embedding_dim)
    raise ValueError(f"unsupported embedding provider type: {config.provider_type}")
