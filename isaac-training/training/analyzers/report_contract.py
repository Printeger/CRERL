"""Shared report namespace contract for static, dynamic, and semantic analyzers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Mapping, Sequence

STATIC_AUDIT_MODE = "static_audit"
DYNAMIC_ANALYSIS_MODE = "dynamic_analysis"
SEMANTIC_ANALYSIS_MODE = "semantic_analysis"
REPORT_GENERATION_MODE = "report_generation"
REPAIR_GENERATION_MODE = "repair_generation"
VALIDATION_GENERATION_MODE = "validation_generation"
INTEGRATION_AUDIT_MODE = "integration_audit"
BENCHMARK_SUITE_MODE = "benchmark_suite"
RELEASE_PACKAGING_MODE = "release_packaging"

DEFAULT_REPORT_NAMESPACES = {
    STATIC_AUDIT_MODE: "analysis/static",
    DYNAMIC_ANALYSIS_MODE: "analysis/dynamic",
    SEMANTIC_ANALYSIS_MODE: "analysis/semantic",
    REPORT_GENERATION_MODE: "analysis/report",
    REPAIR_GENERATION_MODE: "analysis/repair",
    VALIDATION_GENERATION_MODE: "analysis/validation",
    INTEGRATION_AUDIT_MODE: "analysis/integration",
    BENCHMARK_SUITE_MODE: "analysis/benchmark",
    RELEASE_PACKAGING_MODE: "analysis/release",
}

DEFAULT_REPORT_MODE_ARTIFACTS = {
    STATIC_AUDIT_MODE: (
        "static_report.json",
        "summary.json",
        "manifest.json",
        "namespace_manifest.json",
    ),
    DYNAMIC_ANALYSIS_MODE: (
        "dynamic_report.json",
        "dynamic_evidence.json",
        "semantic_inputs.json",
        "summary.json",
        "manifest.json",
        "namespace_manifest.json",
    ),
    SEMANTIC_ANALYSIS_MODE: (
        "semantic_report.json",
        "semantic_claims.json",
        "semantic_input.json",
        "semantic_summary.md",
        "semantic_merge_input.json",
        "claim_consumer.json",
        "summary.json",
        "manifest.json",
        "namespace_manifest.json",
    ),
    REPORT_GENERATION_MODE: (
        "report.json",
        "ranked_findings.json",
        "repair_handoff.json",
        "report_summary.md",
        "summary.json",
        "manifest.json",
        "namespace_manifest.json",
    ),
    REPAIR_GENERATION_MODE: (
        "repair_plan.json",
        "repair_candidates.json",
        "spec_patch.json",
        "spec_patch_preview.json",
        "validation_context_preview.json",
        "repair_summary.json",
        "repair_summary.md",
        "acceptance.json",
        "repair_validation.json",
        "validation_request.json",
        "manifest.json",
        "namespace_manifest.json",
    ),
    VALIDATION_GENERATION_MODE: (
        "validation_plan.json",
        "validation_runs.json",
        "comparison.json",
        "validation_decision.json",
        "post_repair_evidence.json",
        "validation_summary.json",
        "validation_summary.md",
        "manifest.json",
        "namespace_manifest.json",
    ),
    INTEGRATION_AUDIT_MODE: (
        "integration_plan.json",
        "execution_matrix.json",
        "run_binding.json",
        "native_execution_consumer.json",
        "integration_acceptance.json",
        "integration_summary.json",
        "integration_summary.md",
        "manifest.json",
        "namespace_manifest.json",
    ),
    BENCHMARK_SUITE_MODE: (
        "benchmark_manifest.json",
        "benchmark_cases.json",
        "benchmark_matrix.json",
        "benchmark_summary.json",
        "benchmark_summary.md",
        "manifest.json",
        "namespace_manifest.json",
    ),
    RELEASE_PACKAGING_MODE: (
        "release_plan.json",
        "release_artifacts.json",
        "demo_matrix.json",
        "demo_consumer.json",
        "release_acceptance.json",
        "release_summary.json",
        "release_summary.md",
        "manifest.json",
        "namespace_manifest.json",
    ),
}


def resolve_report_namespace_root(
    reports_root: str | Path,
    report_mode: str,
    namespaces: Mapping[str, str] | None = None,
) -> Path:
    namespace_map = dict(namespaces or DEFAULT_REPORT_NAMESPACES)
    namespace = namespace_map.get(report_mode)
    if not namespace:
        raise ValueError(f"No report namespace registered for mode '{report_mode}'.")
    return Path(reports_root) / Path(namespace)


def write_namespace_manifest(
    namespace_root: str | Path,
    *,
    bundle_name: str,
    report_mode: str,
    namespace: str,
    bundle_paths: Mapping[str, Path],
    report_summary: Mapping[str, object],
) -> Path:
    namespace_root = Path(namespace_root)
    namespace_root.mkdir(parents=True, exist_ok=True)
    manifest_path = namespace_root / "namespace_manifest.json"
    payload = {
        "namespace_type": "analysis_namespace.v1",
        "report_mode": report_mode,
        "namespace": namespace,
        "latest_bundle": bundle_name,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "bundle_dir": str(bundle_paths["report_dir"]),
        "bundle_relative_dir": bundle_name,
        "report_path": str(
            bundle_paths.get("static_report_path")
            or bundle_paths.get("dynamic_report_path")
            or bundle_paths.get("semantic_report_path")
            or bundle_paths.get("report_json_path")
            or bundle_paths.get("repair_plan_path")
            or bundle_paths.get("validation_plan_path")
            or bundle_paths.get("benchmark_manifest_path")
            or bundle_paths.get("release_plan_path")
            or ""
        ),
        "summary_path": str(bundle_paths.get("summary_path", "")),
        "manifest_path": str(bundle_paths.get("manifest_path", "")),
        **dict(report_summary),
    }
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return manifest_path


def write_report_namespace_contract(
    reports_root: str | Path,
    *,
    namespaces: Mapping[str, str] | None = None,
    report_mode_artifacts: Mapping[str, Sequence[str]] | None = None,
) -> Path:
    analysis_root = Path(reports_root) / "analysis"
    analysis_root.mkdir(parents=True, exist_ok=True)
    contract_path = analysis_root / "report_namespace_contract.json"
    payload = {
        "contract_type": "report_namespace_contract.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "report_namespaces": dict(namespaces or DEFAULT_REPORT_NAMESPACES),
        "report_mode_artifacts": {
            key: list(value)
            for key, value in (report_mode_artifacts or DEFAULT_REPORT_MODE_ARTIFACTS).items()
        },
    }
    contract_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return contract_path
