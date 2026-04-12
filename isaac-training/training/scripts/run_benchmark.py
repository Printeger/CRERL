from __future__ import annotations

import argparse
import json
from pathlib import Path

from analyzers.dynamic_analyzer import DynamicReport
from analyzers.semantic_analyzer import run_semantic_analysis
from analyzers.static_analyzer import run_static_analysis


CASE_NAMES = ("clean_nominal", "injected_cr", "injected_ec", "injected_er")


def _case_spec_paths(case_dir: Path) -> tuple[str, str, str, str]:
    return (
        str(case_dir / "reward_spec_v1.yaml"),
        str(case_dir / "constraint_spec_v1.yaml"),
        str(case_dir / "policy_spec_v1.yaml"),
        str(case_dir / "env_spec_v1.yaml"),
    )


def _empty_dynamic_report(spec_versions: dict[str, str]) -> DynamicReport:
    return DynamicReport(
        spec_versions=dict(spec_versions),
        episode_count=0,
        issues=[],
        summary={},
        output_path=None,
    )


def _write_results(results: dict[str, dict], output_dir: str | None) -> None:
    if output_dir is None:
        return
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / "benchmark_results.json"
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")


def run_benchmark(
    benchmark_dir: str,
    output_dir: str | None = None,
) -> dict[str, dict]:
    benchmark_root = Path(benchmark_dir)
    results: dict[str, dict] = {}

    for case_name in CASE_NAMES:
        case_dir = benchmark_root / case_name
        reward_path, constraint_path, policy_path, env_path = _case_spec_paths(case_dir)
        static_report = run_static_analysis(
            reward_path,
            constraint_path,
            policy_path,
            env_path,
        )
        dynamic_report = _empty_dynamic_report(static_report.spec_versions)
        semantic_report = run_semantic_analysis(
            static_report,
            dynamic_report,
            reward_path,
            constraint_path,
        )
        results[case_name] = {
            "alarm": bool(semantic_report.summary["alarm"]),
            "psi_cre": float(semantic_report.psi_cre),
            "total_issues": int(semantic_report.summary["total"]),
        }

    _write_results(results, output_dir)
    return results


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CRE benchmark suite on benchmark spec cases.")
    parser.add_argument("--benchmark_dir", required=True, help="Path to cfg/benchmark_cfg root.")
    parser.add_argument(
        "--output_dir",
        default=None,
        help="Optional directory for benchmark_results.json.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    print(json.dumps(run_benchmark(args.benchmark_dir, args.output_dir), indent=2))
