"""CLI entrypoint for Phase 9 repair-validation bundle generation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _training_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ensure_training_root_on_path() -> None:
    root = _training_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 9 repair validation.")
    parser.add_argument("--repair-bundle-dir", required=True, help="Phase 8 repair bundle directory.")
    parser.add_argument(
        "--logs-root",
        default=str(_training_root() / "logs"),
        help="Logs root used when discovering original accepted runs.",
    )
    parser.add_argument(
        "--original-run-dir",
        action="append",
        default=[],
        help="Explicit original accepted run directory. Repeat to add multiple runs.",
    )
    parser.add_argument(
        "--repaired-run-dir",
        action="append",
        default=[],
        help="Explicit repaired accepted run directory. Repeat to add multiple runs.",
    )
    parser.add_argument(
        "--trigger-rerun",
        action="store_true",
        help="Trigger preview-mode targeted reruns when repaired run directories are not provided.",
    )
    parser.add_argument(
        "--rerun-mode",
        choices=("preview", "auto", "subprocess"),
        default="auto",
        help="Validation rerun driver mode. 'auto' tries bounded subprocess execution and falls back to preview.",
    )
    parser.add_argument(
        "--repaired-logs-root",
        default="",
        help="Optional output root for triggered repaired run directories.",
    )
    parser.add_argument(
        "--reports-root",
        default=str(_training_root() / "reports"),
        help="Root reports directory used for namespaced validation artifacts.",
    )
    parser.add_argument(
        "--bundle-name",
        default="validation_latest",
        help="Bundle name under the validation namespace.",
    )
    parser.add_argument(
        "--validation-dir",
        default="",
        help="Optional explicit validation bundle directory override.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional extra output path for a standalone validation_decision.json copy.",
    )
    parser.add_argument(
        "--performance-regression-epsilon",
        type=float,
        default=0.05,
        help="Allowed negative performance delta before rejection.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _ensure_training_root_on_path()

    from analyzers.report_contract import DEFAULT_REPORT_MODE_ARTIFACTS, DEFAULT_REPORT_NAMESPACES
    from repair.comparison import compare_validation_runs
    from repair.decision import decide_validation
    from repair.validation_runner import prepare_validation_runs, run_validation_bundle_write

    prepared = prepare_validation_runs(
        repair_bundle_dir=Path(args.repair_bundle_dir),
        logs_root=Path(args.logs_root),
        original_run_dirs=[Path(item) for item in args.original_run_dir],
        repaired_run_dirs=[Path(item) for item in args.repaired_run_dir],
        trigger_rerun=bool(args.trigger_rerun),
        rerun_mode=str(args.rerun_mode),
        repaired_logs_root=Path(args.repaired_logs_root) if args.repaired_logs_root else None,
    )
    validation_input = prepared["validation_input"]
    validation_plan = prepared["validation_plan"]
    validation_runs = prepared["validation_runs"]
    original_runs = prepared["original_runs"]
    repaired_runs = prepared["repaired_runs"]

    comparison = compare_validation_runs(
        primary_claim_type=str(validation_input.get("primary_claim_type", "")),
        validation_targets=validation_input.get("validation_targets", []),
        original_runs=original_runs,
        repaired_runs=repaired_runs,
    )
    decision = decide_validation(
        comparison,
        performance_regression_epsilon=float(args.performance_regression_epsilon),
    )
    bundle_paths = run_validation_bundle_write(
        validation_plan=validation_plan,
        validation_runs=validation_runs,
        comparison=comparison,
        decision=decision,
        reports_root=Path(args.reports_root),
        bundle_name=args.bundle_name,
        validation_dir=Path(args.validation_dir) if args.validation_dir else None,
        namespaces=DEFAULT_REPORT_NAMESPACES,
        report_mode_artifacts=DEFAULT_REPORT_MODE_ARTIFACTS,
    )

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(decision, indent=2, sort_keys=True), encoding="utf-8")

    print(
        json.dumps(
            {
                "validation_dir": str(bundle_paths["validation_dir"]),
                "output": str(args.output) if args.output else "",
                "validation_plan_path": str(bundle_paths["validation_plan_path"]),
                "validation_runs_path": str(bundle_paths["validation_runs_path"]),
                "comparison_path": str(bundle_paths["comparison_path"]),
                "validation_decision_path": str(bundle_paths["validation_decision_path"]),
                "post_repair_evidence_path": str(bundle_paths["post_repair_evidence_path"]),
                "validation_summary_path": str(bundle_paths["validation_summary_path"]),
                "validation_summary_md_path": str(bundle_paths["validation_summary_md_path"]),
                "manifest_path": str(bundle_paths["manifest_path"]),
                "namespace_manifest_path": str(bundle_paths.get("namespace_manifest_path", "")),
                "namespace_contract_path": str(bundle_paths.get("namespace_contract_path", "")),
                "decision_status": str(decision.get("decision_status", "")),
                "accepted": bool(decision.get("accepted", False)),
                "primary_claim_type": str(validation_plan.get("primary_claim_type", "")),
                "original_run_count": int(comparison.get("original_run_count", 0) or 0),
                "repaired_run_count": int(comparison.get("repaired_run_count", 0) or 0),
                "trigger_rerun": bool(args.trigger_rerun),
                "requested_rerun_mode": str(args.rerun_mode),
                "blocked_by": list(decision.get("blocked_by", []) or []),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
