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
