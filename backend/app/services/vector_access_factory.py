from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, settings
from app.repositories.vector_repository import (
    VectorRepository,
    VectorRepositoryConfig,
    VectorRepositoryType,
    build_vector_repository,
)
from app.services.embedding_provider import (
    EmbeddingProvider,
    EmbeddingProviderConfig,
    EmbeddingProviderType,
    build_embedding_provider,
)
from app.services.vector_store_service import VectorStoreService
from app.services.vectorization_service import VectorizationService


@dataclass(frozen=True)
class VectorAccessRuntime:
    embedding_provider: EmbeddingProvider
    vector_repository: VectorRepository
    vectorization_service: VectorizationService
    vector_store_service: VectorStoreService


def build_vector_access_runtime(runtime_settings: Settings | None = None) -> VectorAccessRuntime:
    resolved_settings = runtime_settings or settings
    embedding_provider = build_embedding_provider(
        EmbeddingProviderConfig(
            provider_type=EmbeddingProviderType(resolved_settings.embedding_provider),
            model_name=resolved_settings.embedding_model,
            embedding_dim=resolved_settings.embedding_dim,
            api_key=resolved_settings.embedding_api_key,
            base_url=resolved_settings.embedding_base_url,
            request_timeout_ms=resolved_settings.embedding_request_timeout_ms,
            enable_real_provider=resolved_settings.embedding_provider_enable_real,
            fallback_to_mock=resolved_settings.embedding_provider_fallback_to_mock,
        )
    )
    vector_repository = build_vector_repository(
        VectorRepositoryConfig(
            repository_type=VectorRepositoryType(resolved_settings.vector_repository),
            db_url=resolved_settings.vector_db_url,
            table_name=resolved_settings.vector_table_name,
            enable_real_repository=resolved_settings.vector_repository_enable_real,
            fallback_to_in_memory=resolved_settings.vector_repository_fallback_to_in_memory,
        )
    )
    vectorization_service = VectorizationService(provider=embedding_provider)
    vector_store_service = VectorStoreService(
        repository=vector_repository,
        vectorization_service=vectorization_service,
    )
    return VectorAccessRuntime(
        embedding_provider=embedding_provider,
        vector_repository=vector_repository,
        vectorization_service=vectorization_service,
        vector_store_service=vector_store_service,
    )

