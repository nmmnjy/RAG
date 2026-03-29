import json
from pathlib import Path

from app.repositories.vector_repository import InMemoryVectorRepository
from app.schemas.document_parse import StructuredDocument
from app.schemas.retrieval import (
    HybridFusionConfig,
    HybridRetrieveRequest,
    HybridRetrieveTuningConfig,
    FusionStrategyName,
    KeywordQueryRequest,
    KeywordQueryHit,
    RerankRequest,
    ScoreNormalizationMethod,
)
from app.schemas.vectorization import VectorQueryHit
from app.schemas.vectorization import VectorWriteMode, VectorWriteRequest, VectorizationInput
from app.services.chunking_service import chunking_service
from app.services.embedding_provider import EmbeddingProvider, MockEmbeddingProvider
from app.services.hybrid_fusion import fuse_scores, normalize_scores
from app.services.hybrid_retrieval_service import HybridRetrievalService
from app.services.keyword_retriever import InMemoryKeywordRetriever, KeywordRetriever
from app.services.reranker import Reranker
from app.services.vector_store_service import VectorStoreService
from app.services.vectorization_service import VectorizationService


class _StaticVectorStoreService:
    def __init__(self, hits: list[VectorQueryHit]) -> None:
        self._hits = hits

    def query_similar(self, request) -> list[VectorQueryHit]:
        return self._hits[: request.top_k]


class _StaticKeywordRetriever(KeywordRetriever):
    def __init__(self, hits: list[KeywordQueryHit]) -> None:
        self._hits = hits

    def index_documents(self, documents: list[dict]) -> None:
        return None

    def search(self, request: KeywordQueryRequest) -> list[KeywordQueryHit]:
        return self._hits[: request.top_k]


class _ConstantEmbeddingProvider(EmbeddingProvider):
    @property
    def provider_name(self) -> str:
        return "test"

    @property
    def model_name(self) -> str:
        return "test-model"

    @property
    def embedding_dim(self) -> int:
        return 2

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]


class _FailingReranker(Reranker):
    @property
    def reranker_name(self) -> str:
        return "failing-reranker"

    def rerank(self, request: RerankRequest):
        raise RuntimeError("reranker unavailable")


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


def test_fuse_scores_should_change_ranking_when_weights_change() -> None:
    vector_scores = {"c1": 0.9, "c2": 0.2}
    keyword_scores = {"c1": 0.1, "c2": 0.95}
    vector_heavy = HybridFusionConfig(
        strategy_name=FusionStrategyName.weighted_sum,
        vector_weight=0.9,
        keyword_weight=0.1,
    )
    keyword_heavy = HybridFusionConfig(
        strategy_name=FusionStrategyName.weighted_sum,
        vector_weight=0.1,
        keyword_weight=0.9,
    )

    result_vector_heavy = fuse_scores(vector_scores, keyword_scores, config=vector_heavy)
    result_keyword_heavy = fuse_scores(vector_scores, keyword_scores, config=keyword_heavy)

    top_vector_heavy = max(result_vector_heavy.items(), key=lambda item: item[1])[0]
    top_keyword_heavy = max(result_keyword_heavy.items(), key=lambda item: item[1])[0]
    assert top_vector_heavy != top_keyword_heavy


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


def test_hybrid_retrieval_should_use_tuning_config_top_k() -> None:
    document = _load_sample_document()
    service = _build_hybrid_service(document)
    request = HybridRetrieveRequest(
        kb_id=document.kb_id,
        doc_id=document.doc_id,
        query_text="文档 规范",
        tuning_config=HybridRetrieveTuningConfig(
            top_k=1,
            vector_top_k=6,
            keyword_top_k=6,
            enable_rerank=False,
        ),
    )

    result = service.retrieve(request)
    assert len(result.hits) == 1
    assert result.top_k == 1


def test_retrieve_should_support_semantic_keyword_hybrid_paths() -> None:
    vector_hits = [
        VectorQueryHit(
            chunk_id="chunk_semantic",
            doc_id="doc_1",
            kb_id="kb_1",
            content="semantic content",
            section_path=["s1"],
            score_vector=0.9,
            citation={"chunk_id": "chunk_semantic"},
        )
    ]
    keyword_hits = [
        KeywordQueryHit(
            chunk_id="chunk_keyword",
            doc_id="doc_1",
            kb_id="kb_1",
            content="keyword content",
            section_path=["s1"],
            score_keyword=0.9,
            citation={"chunk_id": "chunk_keyword"},
        )
    ]
    service = HybridRetrievalService(
        vector_store_service=_StaticVectorStoreService(vector_hits),  # type: ignore[arg-type]
        keyword_retriever=_StaticKeywordRetriever(keyword_hits),
        embedding_provider=_ConstantEmbeddingProvider(),
    )

    semantic_only = service.retrieve(
        HybridRetrieveRequest(
            kb_id="kb_1",
            query_text="q",
            tuning_config=HybridRetrieveTuningConfig(
                top_k=1,
                vector_top_k=5,
                keyword_top_k=0,
                fusion_config=HybridFusionConfig(vector_weight=1.0, keyword_weight=0.0),
            ),
        )
    )
    keyword_only = service.retrieve(
        HybridRetrieveRequest(
            kb_id="kb_1",
            query_text="q",
            tuning_config=HybridRetrieveTuningConfig(
                top_k=1,
                vector_top_k=0,
                keyword_top_k=5,
                fusion_config=HybridFusionConfig(vector_weight=0.0, keyword_weight=1.0),
            ),
        )
    )
    hybrid = service.retrieve(
        HybridRetrieveRequest(
            kb_id="kb_1",
            query_text="q",
            tuning_config=HybridRetrieveTuningConfig(
                top_k=2,
                vector_top_k=5,
                keyword_top_k=5,
                fusion_config=HybridFusionConfig(vector_weight=0.5, keyword_weight=0.5),
            ),
        )
    )

    assert semantic_only.hits[0].chunk_id == "chunk_semantic"
    assert keyword_only.hits[0].chunk_id == "chunk_keyword"
    assert {item.chunk_id for item in hybrid.hits} == {"chunk_semantic", "chunk_keyword"}


def test_hybrid_retrieval_should_keep_stable_order_for_tied_scores() -> None:
    vector_hits = [
        VectorQueryHit(
            chunk_id="chunk_b",
            doc_id="doc_1",
            kb_id="kb_1",
            content="content b",
            section_path=[],
            score_vector=0.8,
            citation={"chunk_id": "chunk_b"},
        ),
        VectorQueryHit(
            chunk_id="chunk_a",
            doc_id="doc_1",
            kb_id="kb_1",
            content="content a",
            section_path=[],
            score_vector=0.8,
            citation={"chunk_id": "chunk_a"},
        ),
    ]
    service = HybridRetrievalService(
        vector_store_service=_StaticVectorStoreService(vector_hits),  # type: ignore[arg-type]
        keyword_retriever=_StaticKeywordRetriever([]),
        embedding_provider=_ConstantEmbeddingProvider(),
    )
    result = service.retrieve(
        HybridRetrieveRequest(
            kb_id="kb_1",
            query_text="q",
            tuning_config=HybridRetrieveTuningConfig(top_k=2, vector_top_k=2, keyword_top_k=0),
        )
    )
    assert [item.chunk_id for item in result.hits] == ["chunk_a", "chunk_b"]


def test_hybrid_retrieval_should_fallback_when_rerank_failed() -> None:
    vector_hits = [
        VectorQueryHit(
            chunk_id="chunk_1",
            doc_id="doc_1",
            kb_id="kb_1",
            content="content 1",
            section_path=[],
            score_vector=0.8,
            citation={"chunk_id": "chunk_1"},
        )
    ]
    service = HybridRetrievalService(
        vector_store_service=_StaticVectorStoreService(vector_hits),  # type: ignore[arg-type]
        keyword_retriever=_StaticKeywordRetriever([]),
        embedding_provider=_ConstantEmbeddingProvider(),
        reranker=_FailingReranker(),
    )
    result = service.retrieve(
        HybridRetrieveRequest(
            kb_id="kb_1",
            query_text="q",
            tuning_config=HybridRetrieveTuningConfig(
                top_k=1,
                vector_top_k=1,
                keyword_top_k=0,
                enable_rerank=True,
            ),
        )
    )
    assert result.hits
    assert result.debug["rerank_status"] == "fallback"
    assert result.debug["reranker_name"] == "failing-reranker"


def test_hybrid_should_improve_over_keyword_on_offline_cases() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "04_hybrid_retrieval"
        / "hybrid_eval_cases_v1.json"
    )
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    cases = payload["cases"]

    def _top_chunk(vector_scores: dict[str, float], keyword_scores: dict[str, float], config: HybridFusionConfig) -> str:
        fused = fuse_scores(vector_scores=vector_scores, keyword_scores=keyword_scores, config=config)
        return sorted(fused.items(), key=lambda item: (-item[1], item[0]))[0][0]

    keyword_only_config = HybridFusionConfig(vector_weight=0.0, keyword_weight=1.0)
    hybrid_default_config = HybridFusionConfig(vector_weight=0.6, keyword_weight=0.4)
    keyword_hit = 0
    hybrid_hit = 0
    for item in cases:
        if _top_chunk(item["vector_scores"], item["keyword_scores"], keyword_only_config) == item["expected_top_chunk_id"]:
            keyword_hit += 1
        if _top_chunk(item["vector_scores"], item["keyword_scores"], hybrid_default_config) == item["expected_top_chunk_id"]:
            hybrid_hit += 1

    keyword_rate = keyword_hit / len(cases)
    hybrid_rate = hybrid_hit / len(cases)
    assert keyword_rate == 0.0
    assert hybrid_rate == 1.0
