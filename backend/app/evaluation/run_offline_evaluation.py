from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from app.services.offline_evaluator import OfflineEvaluator


def _resolve_default_output_path(dataset_id: str) -> Path:
    project_root = Path(__file__).resolve().parents[3]
    report_dir = project_root / "evaluation" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return report_dir / f"{dataset_id}_{ts}.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run offline evaluation for module-07 skeleton.")
    parser.add_argument(
        "--dataset",
        required=True,
        help="Dataset manifest json path, e.g. ../evaluation/datasets/sample_v1/manifest.json",
    )
    parser.add_argument(
        "--output",
        required=False,
        help="Output report path. If omitted, output to evaluation/reports/<dataset_id>_<ts>.json",
    )
    args = parser.parse_args()

    evaluator = OfflineEvaluator()
    dataset_path = Path(args.dataset).resolve()
    dataset = evaluator.load_dataset(dataset_path=dataset_path)
    report = evaluator.run_dataset(dataset)

    output_path = Path(args.output).resolve() if args.output else _resolve_default_output_path(dataset.dataset_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    print(f"dataset_id={report.dataset_id}")
    print(f"report_id={report.report_id}")
    print(f"check_pass_rate={report.summary.pass_rate}")
    print(f"release_blocked={report.release_blocked}")
    print(f"report_path={output_path}")


if __name__ == "__main__":
    main()
