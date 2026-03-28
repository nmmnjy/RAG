from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.repositories.vector_repository import InMemoryVectorRepository
from app.schemas.answer_generation import AnswerGenerationRequest
from app.schemas.evaluation import (
    EvaluationCheckResult,
    EvaluationDimension,
    EvaluationDimensionResult,
    GateRuleType,
    OfflineEvaluationCaseInput,
    OfflineEvaluationCaseOutput,
    OfflineEvaluationCaseReport,
    OfflineEvaluationDatasetInput,
    OfflineEvaluationReport,
    OfflineEvaluationSummary,
    ReleaseGateResult,
    ReleaseGateRule,
)
from app.schemas.retrieval import HybridRetrieveRequest
from app.schemas.vectorization import VectorWriteMode, VectorWriteRequest, VectorizationInput
from app.services.answer_generation_service import AnswerGenerationService
from app.services.chunking_service import chunking_service
from app.services.embedding_provider import MockEmbeddingProvider
from app.services.hybrid_retrieval_service import HybridRetrievalService
from app.services.keyword_retriever import InMemoryKeywordRetriever
from app.services.vector_store_service import VectorStoreService
from app.services.vectorization_service import VectorizationService


class OfflineEvaluator:
    def __init__(self, embedding_dim: int = 12) -> None:
        self._embedding_provider = MockEmbeddingProvider(embedding_dim=embedding_dim)

    def run_dataset(
        self,
        dataset: OfflineEvaluationDatasetInput,
        gate_rules: list[ReleaseGateRule] | None = None,
    ) -> OfflineEvaluationReport:
        case_reports: list[OfflineEvaluationCaseReport] = []
        for case_item in dataset.cases:
            case_reports.append(self._evaluate_case(case_item))

        summary = self._build_summary(case_reports)
        resolved_rules = gate_rules or self._build_default_gate_rules()
        gate_results = self._evaluate_gate_rules(summary=summary, case_reports=case_reports, rules=resolved_rules)

        return OfflineEvaluationReport(
            report_id=f"eval_{uuid4().hex[:12]}",
            dataset_id=dataset.dataset_id,
            dataset_version=dataset.dataset_version,
            generated_at=datetime.now(timezone.utc),
            summary=summary,
            gate_results=gate_results,
            release_blocked=any(not item.passed for item in gate_results),
            case_reports=case_reports,
        )

    @staticmethod
    def load_dataset(dataset_path: Path) -> OfflineEvaluationDatasetInput:
        payload = dataset_path.read_text(encoding="utf-8")
        return OfflineEvaluationDatasetInput.model_validate_json(payload)

    def _evaluate_case(self, case_item: OfflineEvaluationCaseInput) -> OfflineEvaluationCaseReport:
        output = self._run_pipeline(case_item)

        parse_checks = self._check_parse_structured(case_item)
        chunk_checks = self._check_chunk_quality(case_item, output)
        retrieval_checks = self._check_retrieval_quality(case_item, output)
        answer_checks = self._check_answer_quality(case_item, output)

        dimensions = [
            EvaluationDimensionResult(
                dimension_name=EvaluationDimension.parse_structured,
                passed=all(item.passed for item in parse_checks),
                checks=parse_checks,
            ),
            EvaluationDimensionResult(
                dimension_name=EvaluationDimension.chunk_quality,
                passed=all(item.passed for item in chunk_checks),
                checks=chunk_checks,
            ),
            EvaluationDimensionResult(
                dimension_name=EvaluationDimension.retrieval_quality,
                passed=all(item.passed for item in retrieval_checks),
                checks=retrieval_checks,
            ),
            EvaluationDimensionResult(
                dimension_name=EvaluationDimension.answer_quality,
                passed=all(item.passed for item in answer_checks),
                checks=answer_checks,
            ),
        ]
        all_checks = [*parse_checks, *chunk_checks, *retrieval_checks, *answer_checks]

        return OfflineEvaluationCaseReport(
            case_id=case_item.case_id,
            case_name=case_item.case_name,
            passed=all(item.passed for item in dimensions),
            dimensions=dimensions,
            checks=all_checks,
            output_summary={
                "chunk_count": output.chunk_build_result.chunk_count,
                "retrieval_hit_count": len(output.retrieval_result.hits),
                "answer_refuse_reason": output.answer_result.refuse_reason,
                "answer_citation_count": len(output.answer_result.citations),
            },
        )

    def _run_pipeline(self, case_item: OfflineEvaluationCaseInput) -> OfflineEvaluationCaseOutput:
        chunk_build_result = chunking_service.build_chunks(case_item.structured_document)
        vector_store_service = VectorStoreService(
            repository=InMemoryVectorRepository(),
            vectorization_service=VectorizationService(provider=self._embedding_provider),
        )
        vector_store_service.write_vectors(
            VectorWriteRequest(
                mode=VectorWriteMode.initial_build,
                vectorization_input=VectorizationInput(**chunk_build_result.model_dump()),
            )
        )

        keyword_retriever = InMemoryKeywordRetriever()
        keyword_retriever.index_documents(
            [
                {
                    "chunk_id": item.chunk_id,
                    "doc_id": item.doc_id,
                    "kb_id": item.kb_id,
                    "content": item.content,
                    "section_path": item.section_path,
                    "citation": {
                        "source": case_item.structured_document.source,
                        "doc_id": item.doc_id,
                        "chunk_id": item.chunk_id,
                        "section_path": item.section_path,
                    },
                    "metadata": item.metadata,
                }
                for item in chunk_build_result.chunks
            ]
        )

        retrieval_service = HybridRetrievalService(
            vector_store_service=vector_store_service,
            keyword_retriever=keyword_retriever,
            embedding_provider=self._embedding_provider,
        )
        retrieval_result = retrieval_service.retrieve(
            HybridRetrieveRequest(
                kb_id=case_item.structured_document.kb_id,
                query_text=case_item.query_text,
                top_k=case_item.retrieve_config.top_k,
                vector_top_k=case_item.retrieve_config.vector_top_k,
                keyword_top_k=case_item.retrieve_config.keyword_top_k,
                enable_rerank=case_item.retrieve_config.enable_rerank,
                doc_id=(
                    case_item.structured_document.doc_id
                    if case_item.retrieve_config.use_doc_filter
                    else None
                ),
            )
        )

        answer_result = AnswerGenerationService().generate(
            AnswerGenerationRequest(
                kb_id=case_item.structured_document.kb_id,
                query_text=case_item.query_text,
                retrieval_result=retrieval_result,
                max_context_chunks=case_item.answer_config.max_context_chunks,
                min_score_threshold=case_item.answer_config.min_score_threshold,
                min_evidence_chunks=case_item.answer_config.min_evidence_chunks,
                refusal_answer_text=case_item.answer_config.refusal_answer_text,
            )
        )
        return OfflineEvaluationCaseOutput(
            chunk_build_result=chunk_build_result,
            retrieval_result=retrieval_result,
            answer_result=answer_result,
        )

    def _check_parse_structured(self, case_item: OfflineEvaluationCaseInput) -> list[EvaluationCheckResult]:
        parse_result = case_item.structured_document
        section_count = len(parse_result.sections)
        block_count = sum(len(section.blocks) for section in parse_result.sections)
        non_empty_block_count = sum(
            1
            for section in parse_result.sections
            for block in section.blocks
            if block.content.strip() or block.table_rows
        )
        return [
            self._build_check(
                check_name="parse_status_succeeded",
                dimension_name=EvaluationDimension.parse_structured,
                passed=parse_result.status.value == "succeeded",
                assertion_result=f"status={parse_result.status.value}",
                failure_reason=(
                    None
                    if parse_result.status.value == "succeeded"
                    else "structured_document.status 必须为 succeeded"
                ),
            ),
            self._build_check(
                check_name="parse_section_count_min",
                dimension_name=EvaluationDimension.parse_structured,
                passed=section_count >= case_item.assertions.min_section_count,
                metric_value=section_count,
                assertion_result=f">={case_item.assertions.min_section_count}",
                failure_reason=(
                    None
                    if section_count >= case_item.assertions.min_section_count
                    else "sections 数量不足"
                ),
            ),
            self._build_check(
                check_name="parse_blocks_non_empty",
                dimension_name=EvaluationDimension.parse_structured,
                passed=block_count > 0 and non_empty_block_count == block_count,
                metric_value=non_empty_block_count,
                assertion_result=f"non_empty_blocks={non_empty_block_count}/{block_count}",
                failure_reason=(
                    None
                    if block_count > 0 and non_empty_block_count == block_count
                    else "blocks 为空或存在空 content 且无 table_rows"
                ),
            ),
        ]

    def _check_chunk_quality(
        self,
        case_item: OfflineEvaluationCaseInput,
        output: OfflineEvaluationCaseOutput,
    ) -> list[EvaluationCheckResult]:
        chunk_result = output.chunk_build_result
        chunks = chunk_result.chunks
        required_field_ok = all(
            item.chunk_id and item.doc_id and item.content and item.token_count > 0 for item in chunks
        )
        return [
            self._build_check(
                check_name="chunk_count_min",
                dimension_name=EvaluationDimension.chunk_quality,
                passed=chunk_result.chunk_count >= case_item.assertions.min_chunk_count,
                metric_value=chunk_result.chunk_count,
                assertion_result=f">={case_item.assertions.min_chunk_count}",
                failure_reason=(
                    None
                    if chunk_result.chunk_count >= case_item.assertions.min_chunk_count
                    else "chunk_count 未达到最小要求"
                ),
            ),
            self._build_check(
                check_name="chunk_contract_required_fields",
                dimension_name=EvaluationDimension.chunk_quality,
                passed=required_field_ok,
                assertion_result="chunk_id/doc_id/content/token_count 必须有效",
                failure_reason=(None if required_field_ok else "存在不满足冻结字段要求的 chunk"),
            ),
            self._build_check(
                check_name="chunk_section_path_presence",
                dimension_name=EvaluationDimension.chunk_quality,
                passed=all(len(item.section_path) > 0 for item in chunks),
                assertion_result="section_path 必须非空",
                failure_reason=(
                    None
                    if all(len(item.section_path) > 0 for item in chunks)
                    else "存在 section_path 为空的 chunk"
                ),
            ),
        ]

    def _check_retrieval_quality(
        self,
        case_item: OfflineEvaluationCaseInput,
        output: OfflineEvaluationCaseOutput,
    ) -> list[EvaluationCheckResult]:
        hits = output.retrieval_result.hits
        hit_count = len(hits)
        required_field_ok = all(
            item.chunk_id and isinstance(item.score_vector, float) and isinstance(item.score_keyword, float)
            for item in hits
        )
        top_hit_chunk_id = hits[0].chunk_id if hits else None
        expected_top_hit = case_item.assertions.expected_top_hit_chunk_id
        top_hit_expected_ok = expected_top_hit is None or top_hit_chunk_id == expected_top_hit
        return [
            self._build_check(
                check_name="retrieval_hit_count_min",
                dimension_name=EvaluationDimension.retrieval_quality,
                passed=hit_count >= case_item.assertions.min_retrieval_hits,
                metric_value=hit_count,
                assertion_result=f">={case_item.assertions.min_retrieval_hits}",
                failure_reason=(
                    None
                    if hit_count >= case_item.assertions.min_retrieval_hits
                    else "检索命中数不足"
                ),
            ),
            self._build_check(
                check_name="retrieval_contract_required_fields",
                dimension_name=EvaluationDimension.retrieval_quality,
                passed=required_field_ok,
                assertion_result="chunk_id/score_vector/score_keyword 必须存在",
                failure_reason=(None if required_field_ok else "存在检索命中缺失冻结字段"),
            ),
            self._build_check(
                check_name="retrieval_expected_top_hit",
                dimension_name=EvaluationDimension.retrieval_quality,
                passed=top_hit_expected_ok,
                metric_value=top_hit_chunk_id,
                assertion_result=f"expected={expected_top_hit}",
                failure_reason=(None if top_hit_expected_ok else "top hit 与预期 chunk_id 不一致"),
            ),
        ]

    def _check_answer_quality(
        self,
        case_item: OfflineEvaluationCaseInput,
        output: OfflineEvaluationCaseOutput,
    ) -> list[EvaluationCheckResult]:
        answer_result = output.answer_result
        answer_field_ok = (
            bool(answer_result.answer)
            and answer_result.citations is not None
            and answer_result.confidence is not None
        )
        expected_refuse_reason = case_item.assertions.expected_refuse_reason
        refusal_behavior_ok = (
            answer_result.refuse_reason == expected_refuse_reason
            if expected_refuse_reason is not None
            else answer_result.refuse_reason is None
        )
        citation_required_ok = (
            len(answer_result.citations) > 0
            if case_item.assertions.require_non_empty_citations and answer_result.refuse_reason is None
            else True
        )
        return [
            self._build_check(
                check_name="answer_contract_required_fields",
                dimension_name=EvaluationDimension.answer_quality,
                passed=answer_field_ok,
                assertion_result="answer/citations/confidence/refuse_reason 必须可解析",
                failure_reason=(None if answer_field_ok else "答案输出结构不完整"),
            ),
            self._build_check(
                check_name="answer_refusal_behavior",
                dimension_name=EvaluationDimension.answer_quality,
                passed=refusal_behavior_ok,
                metric_value=answer_result.refuse_reason,
                assertion_result=f"expected={expected_refuse_reason}",
                failure_reason=(None if refusal_behavior_ok else "拒答行为与预期不一致"),
            ),
            self._build_check(
                check_name="answer_citations_non_empty_when_answered",
                dimension_name=EvaluationDimension.answer_quality,
                passed=citation_required_ok,
                metric_value=len(answer_result.citations),
                assertion_result="answered 场景 citations >= 1",
                failure_reason=(
                    None
                    if citation_required_ok
                    else "可答场景 citations 为空，不满足溯源基础要求"
                ),
            ),
        ]

    @staticmethod
    def _build_check(
        *,
        check_name: str,
        dimension_name: EvaluationDimension,
        passed: bool,
        metric_value: float | int | str | None = None,
        assertion_result: str | None = None,
        failure_reason: str | None = None,
    ) -> EvaluationCheckResult:
        return EvaluationCheckResult(
            check_name=check_name,
            dimension_name=dimension_name,
            passed=passed,
            metric_value=metric_value,
            assertion_result=assertion_result,
            failure_reason=failure_reason if not passed else None,
        )

    @staticmethod
    def _build_summary(case_reports: list[OfflineEvaluationCaseReport]) -> OfflineEvaluationSummary:
        checks = [check for case_item in case_reports for check in case_item.checks]
        check_count = len(checks)
        check_passed_count = sum(1 for item in checks if item.passed)
        case_count = len(case_reports)
        case_passed_count = sum(1 for item in case_reports if item.passed)
        pass_rate = round(check_passed_count / check_count, 4) if check_count else 0.0
        return OfflineEvaluationSummary(
            case_count=case_count,
            case_passed_count=case_passed_count,
            check_count=check_count,
            check_passed_count=check_passed_count,
            check_failed_count=max(check_count - check_passed_count, 0),
            pass_rate=pass_rate,
        )

    @staticmethod
    def _build_default_gate_rules() -> list[ReleaseGateRule]:
        return [
            ReleaseGateRule(
                rule_name="gate_pass_rate_min_0_90",
                rule_type=GateRuleType.pass_rate_min,
                threshold_value=0.9,
                description="总检查通过率至少 0.90",
            ),
            ReleaseGateRule(
                rule_name="gate_parse_dimension_must_pass",
                rule_type=GateRuleType.dimension_must_pass,
                target_dimension=EvaluationDimension.parse_structured,
                description="每个 case 的解析维度必须通过",
            ),
            ReleaseGateRule(
                rule_name="gate_retrieval_dimension_must_pass",
                rule_type=GateRuleType.dimension_must_pass,
                target_dimension=EvaluationDimension.retrieval_quality,
                description="每个 case 的检索维度必须通过",
            ),
            ReleaseGateRule(
                rule_name="gate_answer_dimension_must_pass",
                rule_type=GateRuleType.dimension_must_pass,
                target_dimension=EvaluationDimension.answer_quality,
                description="每个 case 的答案维度必须通过",
            ),
        ]

    def _evaluate_gate_rules(
        self,
        *,
        summary: OfflineEvaluationSummary,
        case_reports: list[OfflineEvaluationCaseReport],
        rules: list[ReleaseGateRule],
    ) -> list[ReleaseGateResult]:
        results: list[ReleaseGateResult] = []
        for rule_item in rules:
            if not rule_item.enabled:
                continue
            if rule_item.rule_type == GateRuleType.pass_rate_min:
                threshold_value = rule_item.threshold_value or 0.0
                passed = summary.pass_rate >= threshold_value
                results.append(
                    ReleaseGateResult(
                        rule_name=rule_item.rule_name,
                        passed=passed,
                        metric_value=summary.pass_rate,
                        assertion_result=f">={threshold_value}",
                        failure_reason=(None if passed else "总检查通过率未达门禁阈值"),
                    )
                )
                continue

            if rule_item.rule_type == GateRuleType.dimension_must_pass and rule_item.target_dimension:
                failed_case_count = 0
                for case_item in case_reports:
                    dimension_map = {item.dimension_name: item for item in case_item.dimensions}
                    dimension_result = dimension_map.get(rule_item.target_dimension)
                    if not dimension_result or not dimension_result.passed:
                        failed_case_count += 1
                passed = failed_case_count == 0
                results.append(
                    ReleaseGateResult(
                        rule_name=rule_item.rule_name,
                        passed=passed,
                        metric_value=failed_case_count,
                        assertion_result="failed_case_count == 0",
                        failure_reason=(None if passed else "存在未通过指定维度的 case"),
                    )
                )
        return results
