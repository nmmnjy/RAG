from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
import socket
from urllib import error, request as urllib_request


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


class EmbeddingProviderError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class EmbeddingErrorCode(str, Enum):
    request_failed = "EMBEDDING_REQUEST_FAILED"
    invalid_response = "EMBEDDING_INVALID_RESPONSE"
    dim_mismatch = "EMBEDDING_DIM_MISMATCH"


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

    @property
    def model_version(self) -> str:
        return self.model_name

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
        if not texts:
            return []
        if not self._api_key:
            raise EmbeddingProviderError(
                code=EmbeddingErrorCode.request_failed.value,
                message="Embedding provider is missing api key.",
            )
        if not self._base_url:
            raise EmbeddingProviderError(
                code=EmbeddingErrorCode.request_failed.value,
                message="Embedding provider is missing base url.",
            )
        payload = {"model": self._model_name, "input": texts}
        endpoint = f"{self._base_url.rstrip('/')}/embeddings"
        req = urllib_request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        timeout_seconds = max(self._request_timeout_ms / 1000.0, 0.1)
        try:
            with urllib_request.urlopen(req, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
                response_payload = json.loads(body)
        except error.HTTPError as exc:
            if exc.code in (401, 403):
                raise EmbeddingProviderError(
                    code=EmbeddingErrorCode.request_failed.value,
                    message="Embedding provider authentication failed.",
                ) from exc
            if exc.code == 429:
                raise EmbeddingProviderError(
                    code=EmbeddingErrorCode.request_failed.value,
                    message="Embedding provider rate limited.",
                ) from exc
            if exc.code >= 500:
                raise EmbeddingProviderError(
                    code=EmbeddingErrorCode.request_failed.value,
                    message="Embedding provider service unavailable.",
                ) from exc
            raise EmbeddingProviderError(
                code=EmbeddingErrorCode.request_failed.value,
                message=f"Embedding provider HTTP error: {exc.code}.",
            ) from exc
        except (socket.timeout, TimeoutError) as exc:
            raise EmbeddingProviderError(
                code=EmbeddingErrorCode.request_failed.value,
                message="Embedding provider request timeout.",
            ) from exc
        except error.URLError as exc:
            reason = getattr(exc, "reason", None)
            if isinstance(reason, socket.timeout):
                raise EmbeddingProviderError(
                    code=EmbeddingErrorCode.request_failed.value,
                    message="Embedding provider request timeout.",
                ) from exc
            raise EmbeddingProviderError(
                code=EmbeddingErrorCode.request_failed.value,
                message="Embedding provider network error.",
            ) from exc
        except json.JSONDecodeError as exc:
            raise EmbeddingProviderError(
                code=EmbeddingErrorCode.invalid_response.value,
                message="Embedding provider returned invalid JSON response.",
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise EmbeddingProviderError(
                code=EmbeddingErrorCode.request_failed.value,
                message="Embedding provider internal error.",
            ) from exc

        return self._parse_embeddings(response_payload=response_payload, expected_count=len(texts))

    def _parse_embeddings(self, response_payload: dict, expected_count: int) -> list[list[float]]:
        data = response_payload.get("data")
        if not isinstance(data, list) or not data:
            raise EmbeddingProviderError(
                code=EmbeddingErrorCode.invalid_response.value,
                message="Embedding provider returned empty or invalid data field.",
            )
        if len(data) != expected_count:
            raise EmbeddingProviderError(
                code=EmbeddingErrorCode.invalid_response.value,
                message=f"Embedding provider returned {len(data)} vectors, expected {expected_count}.",
            )

        vectors: list[list[float]] = []
        for item in data:
            if not isinstance(item, dict):
                raise EmbeddingProviderError(
                    code=EmbeddingErrorCode.invalid_response.value,
                    message="Embedding provider returned malformed embedding item.",
                )
            embedding = item.get("embedding")
            if not isinstance(embedding, list) or not embedding:
                raise EmbeddingProviderError(
                    code=EmbeddingErrorCode.invalid_response.value,
                    message="Embedding provider returned empty embedding vector.",
                )
            if len(embedding) != self._embedding_dim:
                raise EmbeddingProviderError(
                    code=EmbeddingErrorCode.dim_mismatch.value,
                    message="Embedding dimension mismatch: "
                    f"expected {self._embedding_dim}, got {len(embedding)}.",
                )
            parsed_vector: list[float] = []
            for value in embedding:
                if not isinstance(value, (float, int)):
                    raise EmbeddingProviderError(
                        code=EmbeddingErrorCode.invalid_response.value,
                        message="Embedding provider returned non-numeric vector value.",
                    )
                parsed_vector.append(float(value))
            vectors.append(parsed_vector)
        return vectors


class FallbackEmbeddingProvider(EmbeddingProvider):
    def __init__(self, primary: EmbeddingProvider, fallback: EmbeddingProvider) -> None:
        self._primary = primary
        self._fallback = fallback
        self._active_provider = primary

    @property
    def provider_name(self) -> str:
        return self._active_provider.provider_name

    @property
    def model_name(self) -> str:
        return self._active_provider.model_name

    @property
    def embedding_dim(self) -> int:
        return self._active_provider.embedding_dim

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        try:
            vectors = self._primary.embed_texts(texts)
            self._active_provider = self._primary
            return vectors
        except Exception as exc:  # noqa: BLE001
            try:
                vectors = self._fallback.embed_texts(texts)
                self._active_provider = self._fallback
                return vectors
            except Exception as fallback_exc:  # noqa: BLE001
                raise EmbeddingProviderError(
                    code=EmbeddingErrorCode.request_failed.value,
                    message="Embedding provider failed on both primary and fallback providers.",
                ) from fallback_exc


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
            real_provider = OpenAICompatibleEmbeddingProvider(
                model_name=config.model_name,
                embedding_dim=config.embedding_dim,
                api_key=config.api_key,
                base_url=config.base_url,
                request_timeout_ms=config.request_timeout_ms,
            )
            if config.fallback_to_mock:
                return FallbackEmbeddingProvider(
                    primary=real_provider,
                    fallback=MockEmbeddingProvider(
                        model_name=config.model_name,
                        embedding_dim=config.embedding_dim,
                    ),
                )
            return real_provider
        if config.fallback_to_mock:
            return MockEmbeddingProvider(model_name=config.model_name, embedding_dim=config.embedding_dim)
        raise EmbeddingProviderError(
            code=EmbeddingErrorCode.request_failed.value,
            message="real embedding provider is not ready and fallback_to_mock is disabled",
        )

    if config.fallback_to_mock:
        return MockEmbeddingProvider(model_name=config.model_name, embedding_dim=config.embedding_dim)
    raise EmbeddingProviderError(
        code=EmbeddingErrorCode.request_failed.value,
        message=f"unsupported embedding provider type: {config.provider_type}",
    )
