"""CLI entrypoint for Phase 8 repair candidate generation."""

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
    parser = argparse.ArgumentParser(description="Run Phase 8 repair candidate generation.")
    parser.add_argument(
        "--report-bundle-dir",
        required=True,
        help="Phase 7 report bundle directory under analysis/report/.",
    )
    parser.add_argument(
        "--reports-root",
        default=str(_training_root() / "reports"),
        help="Root reports directory used for namespaced repair artifacts.",
    )
    parser.add_argument(
        "--bundle-name",
        default="repair_latest",
        help="Bundle name under the repair namespace.",
    )
    parser.add_argument(
        "--repair-dir",
        default="",
        help="Optional explicit repair bundle directory override.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional extra output path for a standalone repair_plan.json copy.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _ensure_training_root_on_path()

    from analyzers.report_contract import DEFAULT_REPORT_MODE_ARTIFACTS, DEFAULT_REPORT_NAMESPACES
    from repair.acceptance import accept_repair
    from repair.patch_executor import run_repair_bundle_write
    from repair.repair_validator import build_phase9_validation_request, validate_repair
    from repair.rule_based_repair import propose_rule_based_repairs

    plan = propose_rule_based_repairs(report_bundle_dir=Path(args.report_bundle_dir))
    acceptance = accept_repair(plan.to_dict())
    repair_validation = validate_repair(plan.to_dict(), acceptance=acceptance)
    validation_request = build_phase9_validation_request(
        plan.to_dict(),
        repair_validation=repair_validation,
        acceptance=acceptance,
        bundle_name=args.bundle_name,
        repair_namespace=DEFAULT_REPORT_NAMESPACES["repair_generation"],
    )
    bundle_paths = run_repair_bundle_write(
        plan,
        acceptance,
        repair_validation=repair_validation,
        validation_request=validation_request,
        reports_root=Path(args.reports_root),
        bundle_name=args.bundle_name,
        repair_dir=Path(args.repair_dir) if args.repair_dir else None,
        namespaces=DEFAULT_REPORT_NAMESPACES,
        report_mode_artifacts=DEFAULT_REPORT_MODE_ARTIFACTS,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(plan.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    print(
        json.dumps(
            {
                "repair_dir": str(bundle_paths["repair_dir"]),
                "output": str(args.output) if args.output else "",
                "repair_plan_path": str(bundle_paths["repair_plan_path"]),
                "repair_candidates_path": str(bundle_paths["repair_candidates_path"]),
                "spec_patch_path": str(bundle_paths["spec_patch_path"]),
                "spec_patch_preview_path": str(bundle_paths["spec_patch_preview_path"]),
                "repair_summary_path": str(bundle_paths["repair_summary_path"]),
                "repair_summary_md_path": str(bundle_paths["repair_summary_md_path"]),
                "acceptance_path": str(bundle_paths["acceptance_path"]),
                "repair_validation_path": str(bundle_paths["repair_validation_path"]),
                "validation_request_path": str(bundle_paths["validation_request_path"]),
                "manifest_path": str(bundle_paths["manifest_path"]),
                "namespace_manifest_path": str(bundle_paths.get("namespace_manifest_path", "")),
                "namespace_contract_path": str(bundle_paths.get("namespace_contract_path", "")),
                "passed": bool(acceptance.get("passed", False)),
                "max_severity": str(acceptance.get("max_severity", "info")),
                "phase9_ready": bool(repair_validation.get("phase9_ready", False)),
                "primary_claim_type": plan.primary_claim_type,
                "selected_candidate_id": plan.selected_candidate_id,
                "candidate_count": len(plan.candidates),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
