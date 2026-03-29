from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

from app.core.config import Settings, settings
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
    RuntimeEvalPolicy,
    ReleaseGateResult,
    ReleaseGateRule,
)
from app.schemas.retrieval import HybridRetrieveRequest
from app.schemas.vectorization import VectorWriteMode, VectorWriteRequest, VectorizationInput
from app.services.answer_generation_service import AnswerGenerationService
from app.services.chunking_service import chunking_service
from app.services.embedding_provider import EmbeddingProvider, MockEmbeddingProvider
from app.services.hybrid_retrieval_service import HybridRetrievalService
from app.services.keyword_retriever import InMemoryKeywordRetriever
from app.services.llm_provider import (
    LLMProvider,
    LLMProviderError,
    MockLLMProvider,
    build_llm_provider,
)
from app.services.vector_access_factory import VectorAccessRuntime, build_vector_access_runtime
from app.services.vector_store_service import VectorStoreService
from app.services.vectorization_service import VectorizationService


class OfflineEvaluator:
    def __init__(
        self,
        embedding_dim: int = 12,
        runtime_settings: Settings | None = None,
        llm_provider: LLMProvider | None = None,
        allow_llm_fallback_to_mock: bool | None = None,
        vector_runtime_builder: Callable[[Settings], VectorAccessRuntime] | None = None,
    ) -> None:
        self._embedding_dim = embedding_dim
        self._runtime_settings = runtime_settings or settings
        self._llm_provider = llm_provider
        self._allow_llm_fallback_to_mock = allow_llm_fallback_to_mock
        self._vector_runtime_builder = vector_runtime_builder or build_vector_access_runtime

    def run_dataset(
        self,
        dataset: OfflineEvaluationDatasetInput,
        gate_rules: list[ReleaseGateRule] | None = None,
        pass_rate_min: float = 0.9,
    ) -> OfflineEvaluationReport:
        runtime_policy = dataset.runtime_policy
        case_reports: list[OfflineEvaluationCaseReport] = []
        for case_item in dataset.cases:
            case_reports.append(self._evaluate_case(case_item, runtime_policy))

        summary = self._build_summary(case_reports)
        resolved_rules = gate_rules or self._build_default_gate_rules(runtime_policy, pass_rate_min)
        gate_results = self._evaluate_gate_rules(
            summary=summary,
            case_reports=case_reports,
            rules=resolved_rules,
            runtime_policy=runtime_policy,
        )

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

    def _evaluate_case(
        self,
        case_item: OfflineEvaluationCaseInput,
        runtime_policy: RuntimeEvalPolicy,
    ) -> OfflineEvaluationCaseReport:
        output = self._run_pipeline(case_item, runtime_policy)

        parse_checks = self._check_parse_structured(case_item)
        chunk_checks = self._check_chunk_quality(case_item, output)
        retrieval_checks = self._check_retrieval_quality(case_item, output)
        answer_checks = self._check_answer_quality(case_item, output)
        provider_checks = self._check_provider_runtime(output.provider_runtime)
        answer_checks_all = [*answer_checks, *provider_checks]

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
                passed=all(item.passed for item in answer_checks_all),
                checks=answer_checks_all,
            ),
        ]
        all_checks = [
            *parse_checks,
            *chunk_checks,
            *retrieval_checks,
            *answer_checks_all,
        ]

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
                "is_expected_answerable": case_item.assertions.expected_refuse_reason is None,
                "is_must_hit_evidence_case": case_item.assertions.require_evidence_hit,
                "answerable_chain_passed": all(
                    item.passed
                    for item in answer_checks_all
                    if item.check_name
                    in {
                        "answer_non_empty_for_answerable",
                        "answer_citations_non_empty_when_answered",
                        "answer_confidence_min_for_answerable",
                        "answer_refusal_behavior",
                        "answer_evidence_hit_for_answerable",
                    }
                ),
                "provider_runtime": output.provider_runtime,
            },
        )

    def _run_pipeline(
        self,
        case_item: OfflineEvaluationCaseInput,
        runtime_policy: RuntimeEvalPolicy,
    ) -> OfflineEvaluationCaseOutput:
        chunk_build_result = chunking_service.build_chunks(case_item.structured_document)
        runtime = self._vector_runtime_builder(self._runtime_settings)
        embedding_provider = self._resolve_embedding_provider(runtime.embedding_provider)
        vector_store_service = VectorStoreService(
            repository=runtime.vector_repository,
            vectorization_service=VectorizationService(provider=embedding_provider),
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
            embedding_provider=embedding_provider,
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

        llm_runtime = self._build_llm_runtime()
        answer_service = AnswerGenerationService(
            llm_provider=llm_runtime,
            allow_provider_fallback_to_mock=False,
        )
        answer_result = answer_service.generate(
            AnswerGenerationRequest(
                kb_id=case_item.structured_document.kb_id,
                query_text=case_item.query_text,
                retrieval_result=retrieval_result,
                max_context_chunks=case_item.answer_config.max_context_chunks,
                min_score_threshold=case_item.answer_config.min_score_threshold,
                min_evidence_chunks=case_item.answer_config.min_evidence_chunks,
                refusal_answer_text=case_item.answer_config.refusal_answer_text,
                enable_debug=True,
            )
        )
        provider_runtime = self._build_provider_runtime(
            embedding_provider=embedding_provider,
            llm_runtime=llm_runtime,
            runtime_policy=runtime_policy,
        )
        return OfflineEvaluationCaseOutput(
            chunk_build_result=chunk_build_result,
            retrieval_result=retrieval_result,
            answer_result=answer_result,
            provider_runtime=provider_runtime,
        )

    def _resolve_embedding_provider(self, provider: EmbeddingProvider) -> EmbeddingProvider:
        if provider.provider_name == "mock":
            return MockEmbeddingProvider(
                model_name=provider.model_name,
                embedding_dim=self._embedding_dim,
            )
        return provider

    def _build_provider_runtime(
        self,
        *,
        embedding_provider: EmbeddingProvider,
        llm_runtime: "_TrackedLLMProvider",
        runtime_policy: RuntimeEvalPolicy,
    ) -> dict:
        settings_ref = self._runtime_settings
        embedding_real_mode_declared = (
            settings_ref.embedding_provider == "openai_compatible"
            and settings_ref.embedding_provider_enable_real
        )
        llm_real_mode_declared = (
            settings_ref.llm_provider == "openai_compatible"
            and settings_ref.llm_provider_enable_real
        )
        effective_real_mode_declared = (
            runtime_policy.declared_real_mode
            if runtime_policy.declared_real_mode is not None
            else (embedding_real_mode_declared or llm_real_mode_declared)
        )

        embedding_active_provider = embedding_provider.provider_name
        embedding_fallback_occurred = (
            embedding_real_mode_declared
            and settings_ref.embedding_provider == "openai_compatible"
            and embedding_active_provider != "openai_compatible"
        )

        llm_active_provider = llm_runtime.active_provider_name
        llm_fallback_to = llm_runtime.fallback_to
        llm_fallback_occurred = llm_runtime.fallback_occurred

        any_fallback_occurred = embedding_fallback_occurred or llm_fallback_occurred
        fallback_visible = not any_fallback_occurred or bool(llm_fallback_to or embedding_fallback_occurred)
        return {
            "effective_real_mode_declared": effective_real_mode_declared,
            "embedding": {
                "declared_provider": settings_ref.embedding_provider,
                "active_provider": embedding_active_provider,
                "model_name": embedding_provider.model_name,
                "real_mode_declared": embedding_real_mode_declared,
                "fallback_occurred": embedding_fallback_occurred,
                "fallback_to": ("mock" if embedding_fallback_occurred else None),
            },
            "llm": {
                "declared_provider": settings_ref.llm_provider,
                "active_provider": llm_active_provider,
                "model_name": llm_runtime.active_model_name,
                "real_mode_declared": llm_real_mode_declared,
                "fallback_occurred": llm_fallback_occurred,
                "fallback_to": llm_fallback_to,
            },
            "any_fallback_occurred": any_fallback_occurred,
            "fallback_visible": fallback_visible,
        }

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
        is_expected_answerable = case_item.assertions.expected_refuse_reason is None
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
        answer_non_empty_ok = (len(answer_result.answer.strip()) > 0) if is_expected_answerable else True
        confidence_min_ok = (
            answer_result.confidence >= case_item.assertions.min_answer_confidence
            if is_expected_answerable
            else True
        )

        evidence_text = (case_item.assertions.evidence_text or "").strip()
        if not is_expected_answerable or not case_item.assertions.require_evidence_hit:
            evidence_hit_ok = True
            evidence_hit_result = "skipped"
        elif not evidence_text:
            evidence_hit_ok = False
            evidence_hit_result = "missing_evidence_text"
        else:
            answer_hit = evidence_text in answer_result.answer
            citation_hit = any(evidence_text in item.snippet for item in answer_result.citations)
            evidence_hit_ok = answer_hit or citation_hit
            if answer_hit:
                evidence_hit_result = "answer"
            elif citation_hit:
                evidence_hit_result = "citation_snippet"
            else:
                evidence_hit_result = "none"

        return [
            self._build_check(
                check_name="answer_contract_required_fields",
                dimension_name=EvaluationDimension.answer_quality,
                passed=answer_field_ok,
                assertion_result="answer/citations/confidence/refuse_reason 必须可解析",
                failure_reason=(None if answer_field_ok else "答案输出结构不完整"),
            ),
            self._build_check(
                check_name="answer_non_empty_for_answerable",
                dimension_name=EvaluationDimension.answer_quality,
                passed=answer_non_empty_ok,
                metric_value=len(answer_result.answer.strip()),
                assertion_result="answerable 场景 answer 长度 > 0",
                failure_reason=(None if answer_non_empty_ok else "可答场景 answer 为空"),
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
            self._build_check(
                check_name="answer_confidence_min_for_answerable",
                dimension_name=EvaluationDimension.answer_quality,
                passed=confidence_min_ok,
                metric_value=round(answer_result.confidence, 4),
                assertion_result=f">={case_item.assertions.min_answer_confidence}",
                failure_reason=(None if confidence_min_ok else "可答场景 confidence 低于阈值"),
            ),
            self._build_check(
                check_name="answer_evidence_hit_for_answerable",
                dimension_name=EvaluationDimension.answer_quality,
                passed=evidence_hit_ok,
                metric_value=evidence_hit_result,
                assertion_result="answer 或 citation.snippet 命中 evidence_text",
                failure_reason=(
                    None
                    if evidence_hit_ok
                    else "可答场景未命中证据文本，无法确认答案受证据约束"
                ),
            ),
        ]

    def _check_provider_runtime(self, provider_runtime: dict) -> list[EvaluationCheckResult]:
        effective_real_mode_declared = bool(provider_runtime.get("effective_real_mode_declared"))
        any_fallback_occurred = bool(provider_runtime.get("any_fallback_occurred"))
        fallback_visible = bool(provider_runtime.get("fallback_visible"))
        embedding_runtime = provider_runtime.get("embedding", {})
        llm_runtime = provider_runtime.get("llm", {})
        provider_summary = (
            f"embedding={embedding_runtime.get('active_provider')};"
            f"llm={llm_runtime.get('active_provider')}"
        )
        return [
            self._build_check(
                check_name="provider_runtime_info_visible",
                dimension_name=EvaluationDimension.answer_quality,
                passed=bool(embedding_runtime) and bool(llm_runtime),
                metric_value=provider_summary,
                assertion_result="报告必须输出 embedding/llm provider 运行信息",
                failure_reason=(
                    None
                    if bool(embedding_runtime) and bool(llm_runtime)
                    else "provider 运行信息缺失，无法判定 real/fallback 路径"
                ),
            ),
            self._build_check(
                check_name="provider_fallback_detected_in_real_mode",
                dimension_name=EvaluationDimension.answer_quality,
                passed=True,
                metric_value=(
                    f"real_mode={effective_real_mode_declared};"
                    f"fallback={any_fallback_occurred}"
                ),
                assertion_result="real 模式是否发生 fallback（可观测检查）",
            ),
            self._build_check(
                check_name="provider_fallback_visibility_when_occurred",
                dimension_name=EvaluationDimension.answer_quality,
                passed=(not any_fallback_occurred) or fallback_visible,
                metric_value=fallback_visible,
                assertion_result="fallback 发生时必须在报告中可见",
                failure_reason=(
                    None
                    if (not any_fallback_occurred) or fallback_visible
                    else "检测到 fallback，但报告中无可见标记"
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
        answerable_case_reports = [
            item for item in case_reports if item.output_summary.get("is_must_hit_evidence_case") is True
        ]
        answerable_case_count = len(answerable_case_reports)
        answerable_case_passed_count = sum(
            1
            for item in answerable_case_reports
            if item.output_summary.get("answerable_chain_passed") is True
        )
        pass_rate = round(check_passed_count / check_count, 4) if check_count else 0.0
        return OfflineEvaluationSummary(
            case_count=case_count,
            case_passed_count=case_passed_count,
            answerable_case_count=answerable_case_count,
            answerable_case_passed_count=answerable_case_passed_count,
            check_count=check_count,
            check_passed_count=check_passed_count,
            check_failed_count=max(check_count - check_passed_count, 0),
            pass_rate=pass_rate,
        )

    @staticmethod
    def _build_default_gate_rules(
        runtime_policy: RuntimeEvalPolicy,
        pass_rate_min: float,
    ) -> list[ReleaseGateRule]:
        return [
            ReleaseGateRule(
                rule_name="gate_pass_rate_min",
                rule_type=GateRuleType.pass_rate_min,
                threshold_value=pass_rate_min,
                description=f"总检查通过率至少 {pass_rate_min:.2f}",
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
            ReleaseGateRule(
                rule_name="gate_answerable_evidence_hit_must_pass",
                rule_type=GateRuleType.check_name_must_pass,
                target_check_name="answer_evidence_hit_for_answerable",
                description="可答样本必须命中证据文本（answer 或 citation.snippet）",
            ),
            ReleaseGateRule(
                rule_name="gate_real_mode_forbid_fallback",
                rule_type=GateRuleType.real_mode_no_fallback,
                description="real 模式禁止 fallback（可配置）",
            ),
        ]

    def _evaluate_gate_rules(
        self,
        *,
        summary: OfflineEvaluationSummary,
        case_reports: list[OfflineEvaluationCaseReport],
        rules: list[ReleaseGateRule],
        runtime_policy: RuntimeEvalPolicy,
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
                continue

            if rule_item.rule_type == GateRuleType.check_name_must_pass and rule_item.target_check_name:
                target_checks = [
                    check
                    for case_item in case_reports
                    for check in case_item.checks
                    if check.check_name == rule_item.target_check_name and check.metric_value != "skipped"
                ]
                failed_check_count = sum(1 for check in target_checks if not check.passed)
                passed = bool(target_checks) and failed_check_count == 0
                results.append(
                    ReleaseGateResult(
                        rule_name=rule_item.rule_name,
                        passed=passed,
                        metric_value=failed_check_count,
                        assertion_result="failed_check_count == 0",
                        failure_reason=(
                            None
                            if passed
                            else "可答样本关键检查未通过或未纳入评测输入"
                        ),
                    )
                )
                continue

            if rule_item.rule_type == GateRuleType.real_mode_no_fallback:
                if not runtime_policy.forbid_fallback_when_real_mode:
                    results.append(
                        ReleaseGateResult(
                            rule_name=rule_item.rule_name,
                            passed=True,
                            metric_value="skipped_not_enforced",
                            assertion_result="runtime_policy.forbid_fallback_when_real_mode=false",
                        )
                    )
                    continue
                effective_real_mode_declared = (
                    runtime_policy.declared_real_mode
                    if runtime_policy.declared_real_mode is not None
                    else any(
                        bool(case_item.output_summary.get("provider_runtime", {}).get("effective_real_mode_declared"))
                        for case_item in case_reports
                    )
                )
                if not effective_real_mode_declared:
                    results.append(
                        ReleaseGateResult(
                            rule_name=rule_item.rule_name,
                            passed=True,
                            metric_value="skipped_non_real_mode",
                            assertion_result="仅 real 模式启用",
                        )
                    )
                    continue
                fallback_case_count = sum(
                    1
                    for case_item in case_reports
                    if bool(case_item.output_summary.get("provider_runtime", {}).get("any_fallback_occurred"))
                )
                passed = fallback_case_count == 0
                results.append(
                    ReleaseGateResult(
                        rule_name=rule_item.rule_name,
                        passed=passed,
                        metric_value=fallback_case_count,
                        assertion_result="fallback_case_count == 0",
                        failure_reason=(
                            None
                            if passed
                            else "real 模式检测到 fallback，按门禁策略阻断发布"
                        ),
                    )
                )
        return results

    def _build_llm_runtime(self) -> "_TrackedLLMProvider":
        primary_provider = self._llm_provider or build_llm_provider()
        allow_fallback = (
            self._allow_llm_fallback_to_mock
            if self._allow_llm_fallback_to_mock is not None
            else self._runtime_settings.llm_provider_fallback_to_mock
        )
        fallback_provider = MockLLMProvider(model_name=self._runtime_settings.llm_model)
        return _TrackedLLMProvider(
            primary=primary_provider,
            fallback=fallback_provider,
            allow_fallback=allow_fallback,
        )


class _TrackedLLMProvider(LLMProvider):
    def __init__(self, primary: LLMProvider, fallback: LLMProvider, allow_fallback: bool) -> None:
        self._primary = primary
        self._fallback = fallback
        self._allow_fallback = allow_fallback
        self._active_provider = primary
        self._fallback_occurred = False
        self._fallback_to: str | None = None

    @property
    def provider_name(self) -> str:
        return self._active_provider.provider_name

    @property
    def model_name(self) -> str:
        return self._active_provider.model_name

    @property
    def active_provider_name(self) -> str:
        return self._active_provider.provider_name

    @property
    def active_model_name(self) -> str:
        return self._active_provider.model_name

    @property
    def fallback_occurred(self) -> bool:
        return self._fallback_occurred

    @property
    def fallback_to(self) -> str | None:
        return self._fallback_to

    def generate(self, request) -> object:
        self._active_provider = self._primary
        self._fallback_occurred = False
        self._fallback_to = None
        try:
            return self._primary.generate(request)
        except LLMProviderError:
            if not self._allow_fallback or self._primary.provider_name == "mock":
                raise
            result = self._fallback.generate(request)
            self._active_provider = self._fallback
            self._fallback_occurred = True
            self._fallback_to = self._fallback.provider_name
            return result
