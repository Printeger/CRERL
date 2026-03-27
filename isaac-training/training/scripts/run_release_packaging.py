"""CLI entrypoint for Phase 11 release bundle packaging."""

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
    parser = argparse.ArgumentParser(description="Run Phase 11 release bundle packaging.")
    parser.add_argument(
        "--benchmark-bundle-dir",
        default="",
        help="Optional existing benchmark bundle directory to package into a release bundle.",
    )
    parser.add_argument(
        "--benchmark-cfg-dir",
        default=str(_training_root() / "cfg" / "benchmark_cfg"),
        help="Directory containing Phase 11 benchmark case YAMLs.",
    )
    parser.add_argument(
        "--suite-name",
        default="benchmark_suite_v1",
        help="Benchmark suite manifest name or path.",
    )
    parser.add_argument(
        "--reports-root",
        default=str(_training_root() / "reports"),
        help="Root reports directory used for namespaced release artifacts.",
    )
    parser.add_argument(
        "--bundle-name",
        default="release_bundle_latest",
        help="Bundle name under the release namespace.",
    )
    parser.add_argument(
        "--release-dir",
        default="",
        help="Optional explicit release bundle directory override.",
    )
    parser.add_argument(
        "--integration-bundle-dir",
        action="append",
        default=[],
        help="Optional integration bundle directories to include as proof inputs.",
    )
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
        "--output",
        default="",
        help="Optional extra output path for a standalone release_summary.json copy.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _ensure_training_root_on_path()

    from analyzers.report_contract import DEFAULT_REPORT_MODE_ARTIFACTS, DEFAULT_REPORT_NAMESPACES
    from pipeline.release_bundle import run_release_packaging_bundle

    audit, bundle_paths = run_release_packaging_bundle(
        benchmark_bundle_dir=Path(args.benchmark_bundle_dir) if args.benchmark_bundle_dir else None,
        benchmark_cfg_dir=Path(args.benchmark_cfg_dir),
        suite_name=args.suite_name,
        reports_root=Path(args.reports_root),
        bundle_name=args.bundle_name,
        release_dir=Path(args.release_dir) if args.release_dir else None,
        namespaces=DEFAULT_REPORT_NAMESPACES,
        report_mode_artifacts=DEFAULT_REPORT_MODE_ARTIFACTS,
        spec_cfg_dir=Path(args.spec_cfg_dir),
        env_cfg_dir=Path(args.env_cfg_dir),
        integration_bundle_dirs=[Path(item) for item in args.integration_bundle_dir],
    )

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(audit.release_summary, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    print(
        json.dumps(
            {
                "release_dir": str(bundle_paths["release_dir"]),
                "benchmark_dir": str(bundle_paths["benchmark_dir"]),
                "release_plan_path": str(bundle_paths["release_plan_path"]),
                "release_artifacts_path": str(bundle_paths["release_artifacts_path"]),
                "demo_matrix_path": str(bundle_paths["demo_matrix_path"]),
                "demo_consumer_path": str(bundle_paths["demo_consumer_path"]),
                "release_acceptance_path": str(bundle_paths["release_acceptance_path"]),
                "release_summary_path": str(bundle_paths["release_summary_path"]),
                "release_summary_md_path": str(bundle_paths["release_summary_md_path"]),
                "manifest_path": str(bundle_paths["manifest_path"]),
                "namespace_manifest_path": str(bundle_paths.get("namespace_manifest_path", "")),
                "namespace_contract_path": str(bundle_paths.get("namespace_contract_path", "")),
                "suite_name": audit.suite_name,
                "suite_version": audit.suite_version,
                "demo_case_count": int(audit.release_summary.get("demo_case_count", 0)),
                "release_ready_case_count": int(audit.release_summary.get("release_ready_case_count", 0)),
                "phase11_exit_ready": bool(audit.release_summary.get("phase11_exit_ready", False)),
                "api_key_required_by_default": bool(
                    audit.release_summary.get("api_key_required_by_default", False)
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
