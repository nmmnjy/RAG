from datetime import datetime, timezone

from app.schemas.evaluation import (
    EvaluationCheckResult,
    EvaluationDimension,
    OfflineEvaluationCaseReport,
    OfflineEvaluationReport,
    OfflineEvaluationSummary,
)


def test_evaluation_check_result_should_contain_required_fields() -> None:
    check = EvaluationCheckResult(
        check_name="retrieval_hit_count_min",
        dimension_name=EvaluationDimension.retrieval_quality,
        passed=True,
        metric_value=3,
        assertion_result=">=1",
    )

    payload = check.model_dump()
    assert payload["check_name"] == "retrieval_hit_count_min"
    assert payload["passed"] is True
    assert payload["metric_value"] == 3
    assert payload["failure_reason"] is None


def test_offline_evaluation_report_should_be_serializable() -> None:
    report = OfflineEvaluationReport(
        report_id="eval_001",
        dataset_id="sample_v1",
        dataset_version="2026.03.28",
        generated_at=datetime.now(timezone.utc),
        summary=OfflineEvaluationSummary(
            case_count=1,
            case_passed_count=1,
            check_count=4,
            check_passed_count=4,
            check_failed_count=0,
            pass_rate=1.0,
        ),
        release_blocked=False,
        case_reports=[
            OfflineEvaluationCaseReport(
                case_id="case_001",
                case_name="demo",
                passed=True,
                dimensions=[],
                checks=[],
                output_summary={},
            )
        ],
    )
    assert "sample_v1" in report.model_dump_json()
