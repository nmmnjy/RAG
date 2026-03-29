from pathlib import Path

from app.services.offline_evaluator import OfflineEvaluator


def test_offline_evaluator_should_run_sample_dataset_and_build_report() -> None:
    root_dir = Path(__file__).resolve().parents[3]
    dataset_path = root_dir / "evaluation" / "datasets" / "sample_v1" / "manifest.json"

    evaluator = OfflineEvaluator()
    dataset = evaluator.load_dataset(dataset_path=dataset_path)
    report = evaluator.run_dataset(dataset)

    assert report.dataset_id == "sample_v1"
    assert report.summary.case_count >= 1
    assert report.summary.check_count > 0
    assert report.summary.check_passed_count > 0
    assert report.gate_results
    assert report.summary.answerable_case_count >= 1
    assert report.summary.answerable_case_passed_count >= 1
    check_names = {
        check.check_name
        for case_item in report.case_reports
        for check in case_item.checks
    }
    assert "answer_evidence_hit_for_answerable" in check_names
    gate_rule_names = {item.rule_name for item in report.gate_results}
    assert "gate_answerable_evidence_hit_must_pass" in gate_rule_names
