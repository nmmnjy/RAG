import json
from pathlib import Path

from app.repositories.vector_repository import InMemoryVectorRepository
from app.schemas.document_parse import StructuredDocument
from app.schemas.retrieval import (
    HybridRetrieveRequest,
    KeywordQueryRequest,
    ScoreNormalizationMethod,
)
from app.schemas.vectorization import VectorWriteMode, VectorWriteRequest, VectorizationInput
from app.services.chunking_service import chunking_service
from app.services.embedding_provider import MockEmbeddingProvider
from app.services.hybrid_fusion import fuse_scores, normalize_scores
from app.services.hybrid_retrieval_service import HybridRetrievalService
from app.services.keyword_retriever import InMemoryKeywordRetriever
from app.services.vector_store_service import VectorStoreService
from app.services.vectorization_service import VectorizationService


def _load_sample_document() -> StructuredDocument:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "02_semantic_chunking"
        / "structured_document_sample.json"
    )
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    return StructuredDocument(**payload)


def _as_vectorization_input(chunk_result) -> VectorizationInput:
    return VectorizationInput(**chunk_result.model_dump())


def _build_hybrid_service(document: StructuredDocument) -> HybridRetrievalService:
    chunk_result = chunking_service.build_chunks(document)
    embedding_provider = MockEmbeddingProvider(embedding_dim=12)
    vector_store_service = VectorStoreService(
        repository=InMemoryVectorRepository(),
        vectorization_service=VectorizationService(provider=embedding_provider),
    )
    vector_store_service.write_vectors(
        VectorWriteRequest(
            mode=VectorWriteMode.initial_build,
            vectorization_input=_as_vectorization_input(chunk_result),
        )
    )

    keyword_retriever = InMemoryKeywordRetriever()
    keyword_retriever.index_documents(
        [
            {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "kb_id": chunk.kb_id,
                "content": chunk.content,
                "section_path": chunk.section_path,
                "citation": {
                    "source": document.source,
                    "doc_id": chunk.doc_id,
                    "chunk_id": chunk.chunk_id,
                    "section_path": chunk.section_path,
                },
                "metadata": chunk.metadata,
            }
            for chunk in chunk_result.chunks
        ]
    )
    return HybridRetrievalService(
        vector_store_service=vector_store_service,
        keyword_retriever=keyword_retriever,
        embedding_provider=embedding_provider,
    )


def test_keyword_search_should_return_score_keyword() -> None:
    retriever = InMemoryKeywordRetriever()
    retriever.index_documents(
        [
            {"chunk_id": "c1", "doc_id": "d1", "kb_id": "k1", "content": "rag retrieval fusion"},
            {"chunk_id": "c2", "doc_id": "d1", "kb_id": "k1", "content": "frontend dashboard"},
        ]
    )
    hits = retriever.search(KeywordQueryRequest(kb_id="k1", query_text="retrieval", top_k=5))
    assert hits
    assert hits[0].chunk_id == "c1"
    assert hits[0].score_keyword > 0


def test_normalize_and_fuse_should_apply_min_max_and_weighted_sum() -> None:
    normalized = normalize_scores({"c1": 2.0, "c2": 4.0}, method=ScoreNormalizationMethod.min_max)
    assert normalized["c1"] == 0.0
    assert normalized["c2"] == 1.0

    fused = fuse_scores(
        vector_scores={"c1": 0.2, "c2": 0.8},
        keyword_scores={"c1": 0.9, "c2": 0.1},
        config=HybridRetrieveRequest(kb_id="k1", query_text="q").fusion_config,
    )
    assert set(fused.keys()) == {"c1", "c2"}
    assert all(score >= 0 for score in fused.values())


def test_hybrid_retrieval_should_return_stable_contract_for_qa() -> None:
    document = _load_sample_document()
    service = _build_hybrid_service(document)
    request = HybridRetrieveRequest(
        kb_id=document.kb_id,
        doc_id=document.doc_id,
        query_text="质检 文档 规范",
        top_k=3,
        vector_top_k=6,
        keyword_top_k=6,
    )
    result = service.retrieve(request)

    assert result.hits
    hit = result.hits[0]
    assert hit.chunk_id
    assert isinstance(hit.score_vector, float)
    assert isinstance(hit.score_keyword, float)
    assert isinstance(hit.score_final, float)
    assert hit.citation
    assert hit.content
