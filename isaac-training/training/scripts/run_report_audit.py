"""CLI entrypoint for Phase 7 unified CRE report generation."""

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
    parser = argparse.ArgumentParser(description="Run Phase 7 unified CRE report generation.")
    parser.add_argument("--static-bundle-dir", required=True, help="Static audit bundle directory.")
    parser.add_argument("--dynamic-bundle-dir", required=True, help="Dynamic analysis bundle directory.")
    parser.add_argument("--semantic-bundle-dir", required=True, help="Semantic analysis bundle directory.")
    parser.add_argument(
        "--spec-cfg-dir",
        default=str(_training_root() / "cfg" / "spec_cfg"),
        help="Directory containing machine-readable spec config YAMLs.",
    )
    parser.add_argument(
        "--env-cfg-dir",
        default=str(_training_root() / "cfg" / "env_cfg"),
        help="Directory containing scene family config YAMLs.",
    )
    parser.add_argument(
        "--detector-cfg-dir",
        default=str(_training_root() / "cfg" / "detector_cfg"),
        help="Directory containing detector threshold YAMLs.",
    )
    parser.add_argument(
        "--scene-families",
        default="nominal,boundary_critical,shifted",
        help="Comma-separated scene families to include in report context.",
    )
    parser.add_argument(
        "--reports-root",
        default=str(_training_root() / "reports"),
        help="Root reports directory used for namespaced report artifacts.",
    )
    parser.add_argument(
        "--bundle-name",
        default="report_latest",
        help="Bundle name under the report namespace.",
    )
    parser.add_argument(
        "--report-dir",
        default="",
        help="Optional explicit bundle directory override.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional extra output path for a standalone report.json copy.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _ensure_training_root_on_path()

    from analyzers.report_generator import run_report_generation_bundle

    scene_families = [item.strip() for item in args.scene_families.split(",") if item.strip()]
    report, bundle_paths = run_report_generation_bundle(
        static_bundle_dir=Path(args.static_bundle_dir),
        dynamic_bundle_dir=Path(args.dynamic_bundle_dir),
        semantic_bundle_dir=Path(args.semantic_bundle_dir),
        spec_cfg_dir=Path(args.spec_cfg_dir),
        env_cfg_dir=Path(args.env_cfg_dir),
        detector_cfg_dir=Path(args.detector_cfg_dir),
        scene_families=scene_families,
        reports_root=Path(args.reports_root),
        bundle_name=args.bundle_name,
        report_dir=Path(args.report_dir) if args.report_dir else None,
        output_path=Path(args.output) if args.output else None,
    )
    print(
        json.dumps(
            {
                "report_dir": str(bundle_paths["report_dir"]),
                "output": str(args.output) if args.output else "",
                "report_json_path": str(bundle_paths["report_json_path"]),
                "ranked_findings_path": str(bundle_paths["ranked_findings_path"]),
                "repair_handoff_path": str(bundle_paths["repair_handoff_path"]),
                "report_summary_path": str(bundle_paths["report_summary_path"]),
                "summary_path": str(bundle_paths["summary_path"]),
                "manifest_path": str(bundle_paths["manifest_path"]),
                "namespace_manifest_path": str(bundle_paths.get("namespace_manifest_path", "")),
                "namespace_contract_path": str(bundle_paths.get("namespace_contract_path", "")),
                "passed": report.passed,
                "max_severity": report.max_severity,
                "num_ranked_findings": report.num_ranked_findings,
                "primary_claim_type": report.root_cause_summary.get("primary_claim_type", ""),
                "repair_ready_claims": len(report.repair_handoff),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
