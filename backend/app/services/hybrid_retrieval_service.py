from __future__ import annotations

from app.schemas.retrieval import (
    HybridRetrieveHit,
    HybridRetrieveRequest,
    HybridRetrieveResult,
    KeywordQueryRequest,
    RerankRequest,
)
from app.schemas.vectorization import VectorQueryHit, VectorQueryRequest
from app.services.embedding_provider import EmbeddingProvider
from app.services.hybrid_fusion import fuse_scores
from app.services.keyword_retriever import KeywordRetriever
from app.services.reranker import NoopReranker, Reranker
from app.services.vector_store_service import VectorStoreService


class HybridRetrievalService:
    def __init__(
        self,
        vector_store_service: VectorStoreService,
        keyword_retriever: KeywordRetriever,
        embedding_provider: EmbeddingProvider,
        reranker: Reranker | None = None,
    ) -> None:
        self._vector_store_service = vector_store_service
        self._keyword_retriever = keyword_retriever
        self._embedding_provider = embedding_provider
        self._reranker = reranker or NoopReranker()

    def retrieve(self, request: HybridRetrieveRequest) -> HybridRetrieveResult:
        query_embedding = self._embedding_provider.embed_texts([request.query_text])[0]
        vector_hits = self._vector_store_service.query_similar(
            VectorQueryRequest(
                kb_id=request.kb_id,
                doc_id=request.doc_id,
                query_embedding=query_embedding,
                top_k=request.vector_top_k,
            )
        )
        keyword_hits = self._keyword_retriever.search(
            KeywordQueryRequest(
                kb_id=request.kb_id,
                doc_id=request.doc_id,
                query_text=request.query_text,
                top_k=request.keyword_top_k,
            )
        )

        vector_by_chunk_id = {item.chunk_id: item for item in vector_hits}
        keyword_by_chunk_id = {item.chunk_id: item for item in keyword_hits}

        fused_scores = fuse_scores(
            vector_scores={item.chunk_id: item.score_vector for item in vector_hits},
            keyword_scores={item.chunk_id: item.score_keyword for item in keyword_hits},
            config=request.fusion_config,
        )

        merged_hits = self._merge_hits(
            kb_id=request.kb_id,
            vector_by_chunk_id=vector_by_chunk_id,
            keyword_by_chunk_id=keyword_by_chunk_id,
            fused_scores=fused_scores,
        )
        merged_hits.sort(key=lambda item: item.score_final, reverse=True)

        if request.enable_rerank:
            reranked = self._reranker.rerank(
                RerankRequest(query_text=request.query_text, hits=merged_hits, top_k=request.top_k)
            )
            final_hits = reranked[: request.top_k]
        else:
            final_hits = merged_hits[: request.top_k]

        return HybridRetrieveResult(
            kb_id=request.kb_id,
            query_text=request.query_text,
            top_k=request.top_k,
            hits=final_hits,
            debug={
                "vector_hit_count": len(vector_hits),
                "keyword_hit_count": len(keyword_hits),
                "merged_hit_count": len(merged_hits),
            },
        )

    def _merge_hits(
        self,
        kb_id: str,
        vector_by_chunk_id: dict[str, VectorQueryHit],
        keyword_by_chunk_id: dict,
        fused_scores: dict[str, float],
    ) -> list[HybridRetrieveHit]:
        results: list[HybridRetrieveHit] = []
        for chunk_id, score_final in fused_scores.items():
            vector_hit = vector_by_chunk_id.get(chunk_id)
            keyword_hit = keyword_by_chunk_id.get(chunk_id)
            base_hit = vector_hit or keyword_hit
            if base_hit is None:
                continue
            citation = {}
            if vector_hit and vector_hit.citation:
                citation = vector_hit.citation
            elif keyword_hit and keyword_hit.citation:
                citation = keyword_hit.citation
            else:
                citation = {
                    "kb_id": kb_id,
                    "doc_id": base_hit.doc_id,
                    "chunk_id": chunk_id,
                    "section_path": base_hit.section_path,
                }
            merged_metadata = {}
            if vector_hit:
                merged_metadata.update(vector_hit.metadata)
            if keyword_hit:
                merged_metadata.update(keyword_hit.metadata)
            results.append(
                HybridRetrieveHit(
                    chunk_id=chunk_id,
                    doc_id=base_hit.doc_id,
                    kb_id=base_hit.kb_id,
                    content=base_hit.content,
                    section_path=base_hit.section_path,
                    score_vector=vector_hit.score_vector if vector_hit else 0.0,
                    score_keyword=keyword_hit.score_keyword if keyword_hit else 0.0,
                    score_final=score_final,
                    citation=citation,
                    metadata=merged_metadata,
                )
            )
        return results

