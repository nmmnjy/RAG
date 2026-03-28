from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.answer_generation import AnswerGenerationResult
from app.schemas.chunking import ChunkBuildResult
from app.schemas.document_parse import StructuredDocument
from app.schemas.retrieval import HybridRetrieveResult


class EvaluationDimension(str, Enum):
    parse_structured = "parse_structured"
    chunk_quality = "chunk_quality"
    retrieval_quality = "retrieval_quality"
    answer_quality = "answer_quality"


class GateRuleType(str, Enum):
    pass_rate_min = "pass_rate_min"
    dimension_must_pass = "dimension_must_pass"


class RetrievalEvalConfig(BaseModel):
    top_k: int = Field(default=5, ge=1, le=100)
    vector_top_k: int = Field(default=20, ge=1, le=100)
    keyword_top_k: int = Field(default=20, ge=1, le=100)
    enable_rerank: bool = False
    use_doc_filter: bool = True


class AnswerEvalConfig(BaseModel):
    max_context_chunks: int = Field(default=5, ge=1, le=20)
    min_score_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    min_evidence_chunks: int = Field(default=1, ge=1, le=20)
    refusal_answer_text: str = "抱歉，我当前无法基于现有检索证据可靠回答这个问题。"


class EvaluationAssertions(BaseModel):
    min_section_count: int = Field(default=1, ge=0)
    min_chunk_count: int = Field(default=1, ge=0)
    min_retrieval_hits: int = Field(default=1, ge=0)
    expected_refuse_reason: str | None = None
    expected_top_hit_chunk_id: str | None = None
    require_non_empty_citations: bool = True


class OfflineEvaluationCaseInput(BaseModel):
    case_id: str
    case_name: str
    query_text: str
    structured_document: StructuredDocument
    retrieve_config: RetrievalEvalConfig = Field(default_factory=RetrievalEvalConfig)
    answer_config: AnswerEvalConfig = Field(default_factory=AnswerEvalConfig)
    assertions: EvaluationAssertions = Field(default_factory=EvaluationAssertions)


class OfflineEvaluationDatasetInput(BaseModel):
    dataset_id: str
    dataset_version: str
    description: str = ""
    cases: list[OfflineEvaluationCaseInput] = Field(default_factory=list)


class OfflineEvaluationCaseOutput(BaseModel):
    chunk_build_result: ChunkBuildResult
    retrieval_result: HybridRetrieveResult
    answer_result: AnswerGenerationResult


class EvaluationCheckResult(BaseModel):
    check_name: str
    dimension_name: EvaluationDimension
    passed: bool
    metric_value: float | int | str | None = None
    assertion_result: str | None = None
    failure_reason: str | None = None


class EvaluationDimensionResult(BaseModel):
    dimension_name: EvaluationDimension
    passed: bool
    checks: list[EvaluationCheckResult] = Field(default_factory=list)


class OfflineEvaluationCaseReport(BaseModel):
    case_id: str
    case_name: str
    passed: bool
    dimensions: list[EvaluationDimensionResult] = Field(default_factory=list)
    checks: list[EvaluationCheckResult] = Field(default_factory=list)
    output_summary: dict[str, Any] = Field(default_factory=dict)


class ReleaseGateRule(BaseModel):
    rule_name: str
    rule_type: GateRuleType
    threshold_value: float | None = None
    target_dimension: EvaluationDimension | None = None
    description: str = ""
    enabled: bool = True


class ReleaseGateResult(BaseModel):
    rule_name: str
    passed: bool
    metric_value: float | int | str | None = None
    assertion_result: str | None = None
    failure_reason: str | None = None


class OfflineEvaluationSummary(BaseModel):
    case_count: int
    case_passed_count: int
    check_count: int
    check_passed_count: int
    check_failed_count: int
    pass_rate: float


class OfflineEvaluationReport(BaseModel):
    report_id: str
    dataset_id: str
    dataset_version: str
    generated_at: datetime
    summary: OfflineEvaluationSummary
    gate_results: list[ReleaseGateResult] = Field(default_factory=list)
    release_blocked: bool
    case_reports: list[OfflineEvaluationCaseReport] = Field(default_factory=list)
