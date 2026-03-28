from __future__ import annotations

from app.schemas.chunking import ChunkRecord
from app.schemas.vectorization import VectorRecord, VectorizationInput
from app.services.embedding_provider import EmbeddingProvider


class VectorizationService:
    def __init__(self, provider: EmbeddingProvider) -> None:
        self._provider = provider

    def vectorize_chunks(self, vectorization_input: VectorizationInput, chunks: list[ChunkRecord]) -> list[VectorRecord]:
        if not chunks:
            return []

        texts = [chunk.content for chunk in chunks]
        embeddings = self._provider.embed_texts(texts)
        records: list[VectorRecord] = []

        for chunk, embedding in zip(chunks, embeddings, strict=True):
            records.append(
                VectorRecord(
                    vector_id=f"vec_{vectorization_input.doc_id}_{chunk.chunk_id}",
                    kb_id=vectorization_input.kb_id,
                    doc_id=vectorization_input.doc_id,
                    chunk_id=chunk.chunk_id,
                    content=chunk.content,
                    token_count=chunk.token_count,
                    section_path=chunk.section_path,
                    source=vectorization_input.source,
                    format=vectorization_input.format,
                    version=vectorization_input.version,
                    chunk_index=chunk.chunk_index,
                    strategy_name=chunk.strategy_name.value,
                    strategy_version=chunk.strategy_version,
                    embedding_provider=self._provider.provider_name,
                    embedding_model=self._provider.model_name,
                    embedding_dim=self._provider.embedding_dim,
                    embedding=embedding,
                    content_hash=VectorRecord.build_content_hash(chunk),
                    metadata={
                        "source_block_ids": chunk.source_block_ids,
                        "special_structure": chunk.special_structure.value
                        if chunk.special_structure is not None
                        else None,
                    },
                )
            )

        return records

