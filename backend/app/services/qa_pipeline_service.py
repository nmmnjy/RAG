from __future__ import annotations

from app.repositories.document_parse_repository import document_parse_repository
from app.schemas.answer_generation import AnswerGenerationRequest, AnswerGenerationResult
from app.schemas.chunking import ChunkRecord
from app.schemas.document_parse import DocumentStatus, StructuredDocument
from app.schemas.qa import QAAnswerRequest
from app.schemas.retrieval import HybridRetrieveRequest
from app.schemas.vectorization import VectorWriteMode, VectorWriteRequest, VectorizationInput
from app.services.answer_generation_service import AnswerGenerationService
from app.services.chunking_service import chunking_service
from app.services.hybrid_retrieval_service import HybridRetrievalService
from app.services.keyword_retriever import InMemoryKeywordRetriever
from app.services.vector_access_factory import build_vector_access_runtime


class QAPipelineService:
    """Main QA pipeline for API: sync index -> retrieve -> answer."""

    def __init__(self) -> None:
        runtime = build_vector_access_runtime()
        self._embedding_provider = runtime.embedding_provider
        self._vector_store_service = runtime.vector_store_service
        self._keyword_retriever = InMemoryKeywordRetriever()
        self._hybrid_retrieval_service = HybridRetrievalService(
            vector_store_service=self._vector_store_service,
            keyword_retriever=self._keyword_retriever,
            embedding_provider=self._embedding_provider,
        )
        self._answer_generation_service = AnswerGenerationService()

    def answer(self, request: QAAnswerRequest) -> AnswerGenerationResult:
        self._sync_indices(kb_id=request.kb_id, doc_id=request.doc_id)
        retrieval_result = self._hybrid_retrieval_service.retrieve(
            HybridRetrieveRequest(
                kb_id=request.kb_id,
                doc_id=request.doc_id,
                query_text=request.query_text,
                top_k=request.top_k,
                vector_top_k=request.vector_top_k,
                keyword_top_k=request.keyword_top_k,
                enable_rerank=request.enable_rerank,
            )
        )
        return self._answer_generation_service.generate(
            AnswerGenerationRequest(
                kb_id=request.kb_id,
                query_text=request.query_text,
                retrieval_result=retrieval_result,
                max_context_chunks=request.max_context_chunks,
                min_score_threshold=request.min_score_threshold,
                min_evidence_chunks=request.min_evidence_chunks,
            )
        )

    def _sync_indices(self, kb_id: str, doc_id: str | None) -> None:
        tasks = document_parse_repository.list(kb_id=kb_id, status=DocumentStatus.succeeded)
        if doc_id is not None:
            tasks = [item for item in tasks if item.doc_id == doc_id]

        keyword_documents: list[dict] = []
        for task in tasks:
            document = task.structured_document
            if document is None:
                continue
            chunk_result = chunking_service.build_chunks(document)
            self._vector_store_service.write_vectors(
                VectorWriteRequest(
                    mode=VectorWriteMode.rebuild,
                    vectorization_input=VectorizationInput(**chunk_result.model_dump()),
                )
            )
            keyword_documents.extend(self._build_keyword_documents(document, chunk_result.chunks))

        self._keyword_retriever = InMemoryKeywordRetriever()
        if keyword_documents:
            self._keyword_retriever.index_documents(keyword_documents)
        self._hybrid_retrieval_service = HybridRetrievalService(
            vector_store_service=self._vector_store_service,
            keyword_retriever=self._keyword_retriever,
            embedding_provider=self._embedding_provider,
        )

    @staticmethod
    def _build_keyword_documents(document: StructuredDocument, chunks: list[ChunkRecord]) -> list[dict]:
        return [
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
            for chunk in chunks
        ]


qa_pipeline_service = QAPipelineService()
