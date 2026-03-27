"""CLI entrypoint for Phase 11 benchmark suite packaging."""

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
    parser = argparse.ArgumentParser(description="Run Phase 11 benchmark suite packaging.")
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
        help="Root reports directory used for namespaced benchmark artifacts.",
    )
    parser.add_argument(
        "--bundle-name",
        default="benchmark_suite_latest",
        help="Bundle name under the benchmark namespace.",
    )
    parser.add_argument(
        "--benchmark-dir",
        default="",
        help="Optional explicit benchmark bundle directory override.",
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
        help="Optional extra output path for a standalone benchmark_summary.json copy.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _ensure_training_root_on_path()

    from analyzers.report_contract import DEFAULT_REPORT_MODE_ARTIFACTS, DEFAULT_REPORT_NAMESPACES
    from pipeline.benchmark_suite import run_benchmark_suite_bundle

    audit, bundle_paths = run_benchmark_suite_bundle(
        benchmark_cfg_dir=Path(args.benchmark_cfg_dir),
        suite_name=args.suite_name,
        reports_root=Path(args.reports_root),
        bundle_name=args.bundle_name,
        benchmark_dir=Path(args.benchmark_dir) if args.benchmark_dir else None,
        namespaces=DEFAULT_REPORT_NAMESPACES,
        report_mode_artifacts=DEFAULT_REPORT_MODE_ARTIFACTS,
        spec_cfg_dir=Path(args.spec_cfg_dir),
        env_cfg_dir=Path(args.env_cfg_dir),
    )

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(audit.benchmark_summary, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    print(
        json.dumps(
            {
                "benchmark_dir": str(bundle_paths["benchmark_dir"]),
                "benchmark_manifest_path": str(bundle_paths["benchmark_manifest_path"]),
                "benchmark_cases_path": str(bundle_paths["benchmark_cases_path"]),
                "benchmark_matrix_path": str(bundle_paths["benchmark_matrix_path"]),
                "benchmark_summary_path": str(bundle_paths["benchmark_summary_path"]),
                "benchmark_summary_md_path": str(bundle_paths["benchmark_summary_md_path"]),
                "manifest_path": str(bundle_paths["manifest_path"]),
                "namespace_manifest_path": str(bundle_paths.get("namespace_manifest_path", "")),
                "namespace_contract_path": str(bundle_paths.get("namespace_contract_path", "")),
                "suite_name": audit.suite_name,
                "suite_version": audit.suite_version,
                "case_count": int(audit.benchmark_summary.get("case_count", 0)),
                "ready_case_count": int(audit.benchmark_summary.get("ready_case_count", 0)),
                "phase10_native_ready_case_count": int(
                    audit.benchmark_summary.get("phase10_native_ready_case_count", 0)
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
