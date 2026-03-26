"""CLI entrypoint for Phase 4 static CRE analysis."""

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
    parser = argparse.ArgumentParser(description="Run Phase 4 static CRE analysis.")
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
        help="Comma-separated scene families to include in the static audit.",
    )
    parser.add_argument(
        "--checks",
        default="",
        help="Optional comma-separated subset of static checks to run.",
    )
    parser.add_argument(
        "--reports-root",
        default=str(_training_root() / "reports"),
        help="Root reports directory used for namespaced static audit artifacts.",
    )
    parser.add_argument(
        "--bundle-name",
        default="static_audit_latest",
        help="Bundle name under the static audit namespace.",
    )
    parser.add_argument(
        "--report-dir",
        default="",
        help="Optional explicit bundle directory override.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional extra output path for a standalone static_report.json copy.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _ensure_training_root_on_path()

    from analyzers.detector_runner import run_static_analysis_bundle

    scene_families = [item.strip() for item in args.scene_families.split(",") if item.strip()]
    checks = [item.strip() for item in args.checks.split(",") if item.strip()]
    report, bundle_paths = run_static_analysis_bundle(
        spec_cfg_dir=Path(args.spec_cfg_dir),
        env_cfg_dir=Path(args.env_cfg_dir),
        detector_cfg_dir=Path(args.detector_cfg_dir),
        scene_families=scene_families,
        check_ids=checks or None,
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
                "static_report_path": str(bundle_paths["static_report_path"]),
                "summary_path": str(bundle_paths["summary_path"]),
                "manifest_path": str(bundle_paths["manifest_path"]),
                "namespace_manifest_path": str(bundle_paths.get("namespace_manifest_path", "")),
                "passed": report.passed,
                "max_severity": report.max_severity,
                "num_findings": report.num_findings,
                "scene_family_set": report.scene_family_set,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
