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


def _resolve_stable_report_path(dataset_id: str) -> Path:
    project_root = Path(__file__).resolve().parents[3]
    report_dir = project_root / "evaluation" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir / f"{dataset_id}_report.json"


def _parse_optional_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean value: {value}")


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
    parser.add_argument(
        "--write-stable-report",
        action="store_true",
        help="Also write stable baseline report: evaluation/reports/<dataset_id>_report.json",
    )
    parser.add_argument(
        "--gate-pass-rate-min",
        type=float,
        default=0.9,
        help="Gate threshold for pass rate. Default=0.9",
    )
    parser.add_argument(
        "--declared-real-mode",
        required=False,
        help="Override runtime policy real mode: true/false",
    )
    parser.add_argument(
        "--forbid-fallback-when-real-mode",
        required=False,
        help="Override runtime policy: true/false",
    )
    args = parser.parse_args()

    evaluator = OfflineEvaluator()
    dataset_path = Path(args.dataset).resolve()
    dataset = evaluator.load_dataset(dataset_path=dataset_path)
    if args.declared_real_mode is not None:
        dataset.runtime_policy.declared_real_mode = _parse_optional_bool(args.declared_real_mode)
    if args.forbid_fallback_when_real_mode is not None:
        dataset.runtime_policy.forbid_fallback_when_real_mode = bool(
            _parse_optional_bool(args.forbid_fallback_when_real_mode)
        )
    report = evaluator.run_dataset(dataset, pass_rate_min=args.gate_pass_rate_min)

    output_path = Path(args.output).resolve() if args.output else _resolve_default_output_path(dataset.dataset_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    stable_report_path = None
    if args.write_stable_report:
        stable_report_path = _resolve_stable_report_path(report.dataset_id)
        stable_report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    refuse_case_count = sum(
        1 for case_item in report.case_reports if case_item.output_summary.get("answer_refuse_reason") is not None
    )
    evidence_hit_failed_count = sum(
        1
        for case_item in report.case_reports
        for check in case_item.checks
        if check.check_name == "answer_evidence_hit_for_answerable" and not check.passed
    )

    print(f"dataset_id={report.dataset_id}")
    print(f"report_id={report.report_id}")
    print(f"check_pass_rate={report.summary.pass_rate}")
    print(f"gate_pass_rate_min={args.gate_pass_rate_min}")
    print(f"release_blocked={report.release_blocked}")
    print(f"answer_refuse_case_count={refuse_case_count}")
    print(f"answer_evidence_hit_failed_count={evidence_hit_failed_count}")
    print(f"report_path={output_path}")
    if stable_report_path is not None:
        print(f"stable_report_path={stable_report_path}")


if __name__ == "__main__":
    main()
