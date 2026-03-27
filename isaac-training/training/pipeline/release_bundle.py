"""Phase 11 release bundle builder."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from analyzers.report_contract import (
    DEFAULT_REPORT_MODE_ARTIFACTS,
    DEFAULT_REPORT_NAMESPACES,
    RELEASE_PACKAGING_MODE,
    resolve_report_namespace_root,
    write_namespace_manifest,
    write_report_namespace_contract,
)
from analyzers.spec_ir import load_policy_spec
from pipeline.benchmark_suite import (
    DEFAULT_BENCHMARK_CFG_DIR,
    DEFAULT_ENV_CFG_DIR,
    DEFAULT_SPEC_CFG_DIR,
    TRAINING_ROOT,
    run_benchmark_suite_bundle,
)


RELEASE_NAMESPACE = DEFAULT_REPORT_NAMESPACES[RELEASE_PACKAGING_MODE]


def _load_json_file(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON file at {path} must load to a dict.")
    return payload


def _load_benchmark_bundle(benchmark_dir: Path) -> Dict[str, Dict[str, Any]]:
    return {
        "benchmark_manifest": _load_json_file(benchmark_dir / "benchmark_manifest.json"),
        "benchmark_cases": _load_json_file(benchmark_dir / "benchmark_cases.json"),
        "benchmark_matrix": _load_json_file(benchmark_dir / "benchmark_matrix.json"),
        "benchmark_summary": _load_json_file(benchmark_dir / "benchmark_summary.json"),
        "benchmark_bundle_manifest": _load_json_file(benchmark_dir / "manifest.json"),
    }


def _load_optional_integration_bundles(
    bundle_dirs: Sequence[str | Path],
) -> list[Dict[str, Any]]:
    bundles: list[Dict[str, Any]] = []
    for entry in bundle_dirs:
        bundle_dir = Path(entry)
        acceptance_path = bundle_dir / "integration_acceptance.json"
        manifest_path = bundle_dir / "manifest.json"
        consumer_path = bundle_dir / "native_execution_consumer.json"
        if not (acceptance_path.exists() and manifest_path.exists()):
            bundles.append(
                {
                    "bundle_dir": str(bundle_dir),
                    "exists": False,
                    "acceptance_passed": False,
                    "comparison_ready_modes": [],
                    "consumer_contract": "",
                }
            )
            continue
        acceptance = _load_json_file(acceptance_path)
        manifest = _load_json_file(manifest_path)
        consumer = _load_json_file(consumer_path) if consumer_path.exists() else {}
        bundles.append(
            {
                "bundle_dir": str(bundle_dir),
                "exists": True,
                "manifest_path": str(manifest_path),
                "acceptance_path": str(acceptance_path),
                "consumer_path": str(consumer_path) if consumer_path.exists() else "",
                "acceptance_passed": bool(acceptance.get("passed", False)),
                "comparison_ready_modes": list(acceptance.get("comparison_ready_modes", []) or []),
                "native_ready_modes": list(acceptance.get("native_ready_modes", []) or []),
                "consumer_contract": str(consumer.get("consumer_contract", "")),
                "bundle_type": str(manifest.get("bundle_type", "")),
            }
        )
    return bundles


def _build_demo_story(case_record: Mapping[str, Any]) -> str:
    inconsistency_type = str(case_record.get("inconsistency_type", ""))
    if inconsistency_type == "clean":
        return "clean baseline -> evidence collection -> stable benchmark replay"
    if inconsistency_type == "C-R":
        return "detect static/semantic conflict -> report -> reward-side repair -> validate"
    if inconsistency_type == "E-C":
        return "detect coverage mismatch -> report -> environment-side repair -> validate"
    if inconsistency_type == "E-R":
        return "detect robustness gap -> report -> shifted-scene repair -> validate"
    return "benchmark replay -> analyze -> repair -> validate"


def _build_demo_matrix(
    *,
    case_records: Sequence[Mapping[str, Any]],
    benchmark_matrix: Mapping[str, Any],
) -> Dict[str, Any]:
    execution_rows = list(benchmark_matrix.get("execution_rows", []) or [])
    comparison_rows = list(benchmark_matrix.get("comparison_rows", []) or [])
    rows = []
    for case in case_records:
        release_cfg = dict(case.get("release", {}) or {})
        if not bool(release_cfg.get("include_in_cre_v1_demo", False)):
            continue
        case_id = str(case.get("case_id", ""))
        case_execution_rows = [row for row in execution_rows if str(row.get("case_id", "")) == case_id]
        case_comparison_rows = [row for row in comparison_rows if str(row.get("case_id", "")) == case_id]
        rows.append(
            {
                "demo_id": f"{case_id}::cre_v1_demo",
                "case_id": case_id,
                "title": str(case.get("title", case_id)),
                "benchmark_class": str(case.get("benchmark_class", "")),
                "inconsistency_type": str(case.get("inconsistency_type", "")),
                "scene_family": str(case.get("scene_family", "")),
                "scene_cfg_name": str(case.get("scene_cfg_name", "")),
                "execution_modes": list(case.get("execution_modes", []) or []),
                "analysis_modes": list(case.get("analysis_modes", []) or []),
                "required_namespaces": dict(case.get("required_namespaces", {}) or {}),
                "expected_validation_targets": list(case.get("expected_validation_targets", []) or []),
                "expected_primary_claim_type": str(case.get("expected_primary_claim_type", "")),
                "native_phase10_ready": bool(case.get("native_phase10_ready", False)),
                "release_demo_ready": bool(
                    case.get("case_ready", False)
                    and case.get("native_phase10_ready", False)
                    and all(bool(row.get("replay_ready", False)) for row in case_execution_rows)
                ),
                "execution_task_ids": [str(row.get("task_id", "")) for row in case_execution_rows],
                "comparison_ids": [str(row.get("comparison_id", "")) for row in case_comparison_rows],
                "demo_story": _build_demo_story(case),
            }
        )
    return {
        "matrix_type": "phase11_release_demo_matrix.v1",
        "rows": rows,
    }


def _build_release_plan(
    *,
    suite_name: str,
    suite_version: str,
    benchmark_dir: Path,
    demo_matrix: Mapping[str, Any],
    benchmark_summary: Mapping[str, Any],
    policy_runtime_expectations: Mapping[str, Any],
    integration_bundles: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    rows = list(demo_matrix.get("rows", []) or [])
    required_namespaces = sorted(
        {
            str(namespace)
            for row in rows
            for namespace in dict(row.get("required_namespaces", {}) or {}).values()
            if str(namespace)
        }
    )
    required_namespaces.append(DEFAULT_REPORT_NAMESPACES[RELEASE_PACKAGING_MODE])
    required_namespaces = sorted(set(required_namespaces))
    return {
        "plan_type": "phase11_release_plan.v1",
        "release_name": "cre_v1_release_demo",
        "suite_name": suite_name,
        "suite_version": suite_version,
        "benchmark_bundle_dir": str(benchmark_dir),
        "packaged_case_ids": [str(row.get("case_id", "")) for row in rows],
        "demo_case_ids": [str(row.get("case_id", "")) for row in rows],
        "required_namespaces": required_namespaces,
        "phase10_native_ready_case_count": int(
            benchmark_summary.get("phase10_native_ready_case_count", 0)
        ),
        "integration_proof_bundle_count": len(list(integration_bundles)),
        "provider_mode": str(policy_runtime_expectations.get("release_default_provider_mode", "mock")),
        "api_key_required_by_default": bool(
            policy_runtime_expectations.get("release_api_key_required_by_default", False)
        ),
    }


def _build_release_artifacts(
    *,
    benchmark_dir: Path,
    benchmark_bundle: Mapping[str, Mapping[str, Any]],
    demo_matrix: Mapping[str, Any],
    policy_runtime_expectations: Mapping[str, Any],
    integration_bundles: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    benchmark_artifacts = {
        "benchmark_manifest_path": str(benchmark_dir / "benchmark_manifest.json"),
        "benchmark_cases_path": str(benchmark_dir / "benchmark_cases.json"),
        "benchmark_matrix_path": str(benchmark_dir / "benchmark_matrix.json"),
        "benchmark_summary_path": str(benchmark_dir / "benchmark_summary.json"),
        "benchmark_summary_md_path": str(benchmark_dir / "benchmark_summary.md"),
        "benchmark_bundle_manifest_path": str(benchmark_dir / "manifest.json"),
    }
    cases = list(benchmark_bundle["benchmark_cases"].get("cases", []) or [])
    included_case_records = {
        str(case.get("case_id", "")): {
            "case_id": str(case.get("case_id", "")),
            "required_namespaces": dict(case.get("required_namespaces", {}) or {}),
            "expected_validation_targets": list(case.get("expected_validation_targets", []) or []),
            "patch_targets": list(dict(case.get("injection", {}) or {}).get("patch_targets", []) or []),
            "include_in_cre_v1_demo": bool(dict(case.get("release", {}) or {}).get("include_in_cre_v1_demo", False)),
        }
        for case in cases
        if str(case.get("case_id", "")) in {
            str(row.get("case_id", "")) for row in list(demo_matrix.get("rows", []) or [])
        }
    }
    return {
        "artifacts_type": "phase11_release_artifacts.v1",
        "benchmark_bundle_dir": str(benchmark_dir),
        "benchmark_artifacts": benchmark_artifacts,
        "release_required_artifacts": list(
            policy_runtime_expectations.get("release_packaging_required_artifacts", []) or []
        ),
        "integration_proof_bundles": list(integration_bundles),
        "included_case_artifacts": list(included_case_records.values()),
    }


def _build_release_summary(
    *,
    suite_name: str,
    suite_version: str,
    demo_matrix: Mapping[str, Any],
    release_plan: Mapping[str, Any],
    release_artifacts: Mapping[str, Any],
) -> Dict[str, Any]:
    rows = list(demo_matrix.get("rows", []) or [])
    return {
        "summary_type": "phase11_release_summary.v1",
        "release_name": str(release_plan.get("release_name", "cre_v1_release_demo")),
        "suite_name": suite_name,
        "suite_version": suite_version,
        "demo_case_count": len(rows),
        "release_ready_case_count": sum(bool(row.get("release_demo_ready", False)) for row in rows),
        "native_phase10_ready_case_count": sum(bool(row.get("native_phase10_ready", False)) for row in rows),
        "integration_proof_bundle_count": len(
            list(release_artifacts.get("integration_proof_bundles", []) or [])
        ),
        "api_key_required_by_default": bool(release_plan.get("api_key_required_by_default", False)),
        "provider_mode": str(release_plan.get("provider_mode", "mock")),
        "packaged_inconsistency_types": sorted(
            {str(row.get("inconsistency_type", "")) for row in rows if str(row.get("inconsistency_type", ""))}
        ),
        "packaged_namespaces": sorted(set(list(release_plan.get("required_namespaces", []) or []))),
        "release_ready": all(bool(row.get("release_demo_ready", False)) for row in rows),
    }


def _build_release_summary_md(
    *,
    release_plan: Mapping[str, Any],
    release_summary: Mapping[str, Any],
    demo_matrix: Mapping[str, Any],
) -> str:
    lines = [
        "# Phase 11 Release Summary",
        "",
        f"- Release: `{release_plan['release_name']}`",
        f"- Suite: `{release_plan['suite_name']}`",
        f"- Version: `{release_plan['suite_version']}`",
        f"- Demo cases: `{release_summary['demo_case_count']}`",
        f"- Release-ready demo cases: `{release_summary['release_ready_case_count']}`",
        f"- Native Phase-10 ready demo cases: `{release_summary['native_phase10_ready_case_count']}`",
        f"- Provider mode: `{release_summary['provider_mode']}`",
        f"- API key required by default: `{release_summary['api_key_required_by_default']}`",
        "",
        "## Demo Matrix",
        "",
    ]
    for row in list(demo_matrix.get("rows", []) or []):
        lines.extend(
            [
                f"### {row['case_id']}",
                f"- inconsistency: `{row['inconsistency_type']}`",
                f"- execution modes: `{', '.join(row['execution_modes'])}`",
                f"- validation targets: `{', '.join(row['expected_validation_targets'])}`",
                f"- release ready: `{row['release_demo_ready']}`",
                f"- story: {row['demo_story']}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


@dataclass
class ReleaseBundleAudit:
    suite_name: str
    suite_version: str
    release_plan: Dict[str, Any]
    release_artifacts: Dict[str, Any]
    demo_matrix: Dict[str, Any]
    release_summary: Dict[str, Any]


def write_release_bundle(
    audit: ReleaseBundleAudit,
    *,
    report_dir: str | Path,
    namespaces: Mapping[str, str] | None = None,
    report_mode_artifacts: Mapping[str, Sequence[str]] | None = None,
) -> Dict[str, Path]:
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    release_plan_path = report_dir / "release_plan.json"
    release_artifacts_path = report_dir / "release_artifacts.json"
    demo_matrix_path = report_dir / "demo_matrix.json"
    release_summary_path = report_dir / "release_summary.json"
    release_summary_md_path = report_dir / "release_summary.md"
    manifest_path = report_dir / "manifest.json"

    release_plan_path.write_text(json.dumps(audit.release_plan, indent=2, sort_keys=True), encoding="utf-8")
    release_artifacts_path.write_text(
        json.dumps(audit.release_artifacts, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    demo_matrix_path.write_text(json.dumps(audit.demo_matrix, indent=2, sort_keys=True), encoding="utf-8")
    release_summary_path.write_text(
        json.dumps(audit.release_summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    release_summary_md_path.write_text(
        _build_release_summary_md(
            release_plan=audit.release_plan,
            release_summary=audit.release_summary,
            demo_matrix=audit.demo_matrix,
        ),
        encoding="utf-8",
    )

    bundle_paths = {
        "report_dir": report_dir,
        "release_plan_path": release_plan_path,
        "release_artifacts_path": release_artifacts_path,
        "demo_matrix_path": demo_matrix_path,
        "release_summary_path": release_summary_path,
        "release_summary_md_path": release_summary_md_path,
        "summary_path": release_summary_path,
        "manifest_path": manifest_path,
    }

    namespace_root = resolve_report_namespace_root(
        report_dir.parents[2],
        RELEASE_PACKAGING_MODE,
        namespaces=namespaces,
    )
    namespace_manifest_path = write_namespace_manifest(
        namespace_root,
        bundle_name=report_dir.name,
        report_mode=RELEASE_PACKAGING_MODE,
        namespace=(namespaces or DEFAULT_REPORT_NAMESPACES)[RELEASE_PACKAGING_MODE],
        bundle_paths=bundle_paths,
        report_summary=audit.release_summary,
    )
    namespace_contract_path = write_report_namespace_contract(
        report_dir.parents[2],
        namespaces=namespaces,
        report_mode_artifacts=report_mode_artifacts,
    )

    manifest_payload = {
        "bundle_type": "phase11_release_bundle.v1",
        "release_name": audit.release_plan["release_name"],
        "suite_name": audit.suite_name,
        "suite_version": audit.suite_version,
        "release_plan_path": str(release_plan_path),
        "release_artifacts_path": str(release_artifacts_path),
        "demo_matrix_path": str(demo_matrix_path),
        "release_summary_path": str(release_summary_path),
        "release_summary_md_path": str(release_summary_md_path),
        "namespace_manifest_path": str(namespace_manifest_path),
        "namespace_contract_path": str(namespace_contract_path),
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True), encoding="utf-8")

    bundle_paths["namespace_manifest_path"] = namespace_manifest_path
    bundle_paths["namespace_contract_path"] = namespace_contract_path
    return bundle_paths


def build_release_bundle_audit(
    *,
    benchmark_bundle_dir: str | Path,
    spec_cfg_dir: str | Path = DEFAULT_SPEC_CFG_DIR,
    integration_bundle_dirs: Sequence[str | Path] = (),
) -> ReleaseBundleAudit:
    benchmark_dir = Path(benchmark_bundle_dir)
    benchmark_bundle = _load_benchmark_bundle(benchmark_dir)
    benchmark_manifest = benchmark_bundle["benchmark_manifest"]
    benchmark_cases = benchmark_bundle["benchmark_cases"]
    benchmark_matrix = benchmark_bundle["benchmark_matrix"]
    benchmark_summary = benchmark_bundle["benchmark_summary"]

    policy_spec = load_policy_spec(spec_cfg_dir=spec_cfg_dir)
    policy_runtime_expectations = dict(policy_spec.raw.get("runtime_expectations", {}) or {})
    integration_bundles = _load_optional_integration_bundles(integration_bundle_dirs)
    demo_matrix = _build_demo_matrix(
        case_records=list(benchmark_cases.get("cases", []) or []),
        benchmark_matrix=benchmark_matrix,
    )
    release_plan = _build_release_plan(
        suite_name=str(benchmark_manifest.get("suite_name", "")),
        suite_version=str(benchmark_manifest.get("suite_version", "")),
        benchmark_dir=benchmark_dir,
        demo_matrix=demo_matrix,
        benchmark_summary=benchmark_summary,
        policy_runtime_expectations=policy_runtime_expectations,
        integration_bundles=integration_bundles,
    )
    release_artifacts = _build_release_artifacts(
        benchmark_dir=benchmark_dir,
        benchmark_bundle=benchmark_bundle,
        demo_matrix=demo_matrix,
        policy_runtime_expectations=policy_runtime_expectations,
        integration_bundles=integration_bundles,
    )
    release_summary = _build_release_summary(
        suite_name=str(benchmark_manifest.get("suite_name", "")),
        suite_version=str(benchmark_manifest.get("suite_version", "")),
        demo_matrix=demo_matrix,
        release_plan=release_plan,
        release_artifacts=release_artifacts,
    )
    return ReleaseBundleAudit(
        suite_name=str(benchmark_manifest.get("suite_name", "")),
        suite_version=str(benchmark_manifest.get("suite_version", "")),
        release_plan=release_plan,
        release_artifacts=release_artifacts,
        demo_matrix=demo_matrix,
        release_summary=release_summary,
    )


def run_release_packaging_bundle(
    *,
    benchmark_bundle_dir: str | Path | None = None,
    benchmark_cfg_dir: str | Path = DEFAULT_BENCHMARK_CFG_DIR,
    suite_name: str = "benchmark_suite_v1",
    reports_root: str | Path = TRAINING_ROOT / "reports",
    bundle_name: Optional[str] = None,
    release_dir: str | Path | None = None,
    namespaces: Mapping[str, str] | None = None,
    report_mode_artifacts: Mapping[str, Sequence[str]] | None = None,
    spec_cfg_dir: str | Path = DEFAULT_SPEC_CFG_DIR,
    env_cfg_dir: str | Path = DEFAULT_ENV_CFG_DIR,
    integration_bundle_dirs: Sequence[str | Path] = (),
) -> tuple[ReleaseBundleAudit, Dict[str, Path]]:
    benchmark_dir = Path(benchmark_bundle_dir) if benchmark_bundle_dir is not None else None
    generated_benchmark_dir: Optional[Path] = None
    if benchmark_dir is None:
        _, benchmark_paths = run_benchmark_suite_bundle(
            benchmark_cfg_dir=benchmark_cfg_dir,
            suite_name=suite_name,
            reports_root=reports_root,
            bundle_name=f"{bundle_name or 'release_benchmark'}_benchmark",
            namespaces=namespaces,
            report_mode_artifacts=report_mode_artifacts,
            spec_cfg_dir=spec_cfg_dir,
            env_cfg_dir=env_cfg_dir,
        )
        benchmark_dir = Path(benchmark_paths["benchmark_dir"])
        generated_benchmark_dir = benchmark_dir

    audit = build_release_bundle_audit(
        benchmark_bundle_dir=benchmark_dir,
        spec_cfg_dir=spec_cfg_dir,
        integration_bundle_dirs=integration_bundle_dirs,
    )
    if release_dir is None:
        namespace_root = resolve_report_namespace_root(
            reports_root,
            RELEASE_PACKAGING_MODE,
            namespaces=namespaces,
        )
        target_bundle_name = bundle_name or "release_bundle_latest"
        release_dir = namespace_root / target_bundle_name
    bundle_paths = write_release_bundle(
        audit,
        report_dir=release_dir,
        namespaces=namespaces,
        report_mode_artifacts=report_mode_artifacts,
    )
    bundle_paths["release_dir"] = bundle_paths["report_dir"]
    bundle_paths["benchmark_dir"] = benchmark_dir
    if generated_benchmark_dir is not None:
        bundle_paths["generated_benchmark_dir"] = generated_benchmark_dir
    return audit, bundle_paths


__all__ = [
    "RELEASE_NAMESPACE",
    "ReleaseBundleAudit",
    "build_release_bundle_audit",
    "run_release_packaging_bundle",
    "write_release_bundle",
]
