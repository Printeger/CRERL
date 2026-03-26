"""Rollout-based dynamic analyzer for Phase 5 CRE witness metrics."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from analyzers.dynamic_evidence import (
    build_dynamic_evidence_objects,
    build_semantic_diagnosis_inputs,
)
from analyzers.dynamic_metrics import DynamicWitnessResult, compute_dynamic_metrics
from analyzers.report_contract import (
    DEFAULT_REPORT_NAMESPACES,
    DYNAMIC_ANALYSIS_MODE,
    resolve_report_namespace_root,
    write_namespace_manifest,
    write_report_namespace_contract,
)
from analyzers.spec_ir import SpecIR, load_spec_ir
from runtime_logging.episode_writer import (
    discover_accepted_run_directories,
    load_run_directories,
)


DYNAMIC_ANALYSIS_NAMESPACE = DEFAULT_REPORT_NAMESPACES[DYNAMIC_ANALYSIS_MODE]
GROUPING_KEYS = ("source", "scenario_type", "scene_cfg_name")


@dataclass
class DynamicFindingRecord:
    """Machine-readable finding emitted by the dynamic analyzer."""

    finding_id: str
    witness_id: str
    severity: str
    summary: str
    score: float
    details: Dict[str, Any] = field(default_factory=dict)
    evidence_refs: List[str] = field(default_factory=list)


@dataclass
class DynamicAnalyzerReport:
    """Phase 5 dynamic analyzer report."""

    report_type: str
    spec_version: str
    primary_run_ids: List[str]
    comparison_run_ids: List[str]
    passed: bool
    max_severity: str
    num_findings: int
    witnesses: List[Dict[str, Any]] = field(default_factory=list)
    findings: List[DynamicFindingRecord] = field(default_factory=list)
    group_summaries: Dict[str, Any] = field(default_factory=dict)
    failure_summaries: Dict[str, Any] = field(default_factory=dict)
    static_context: Dict[str, Any] = field(default_factory=dict)
    evidence_objects: List[Dict[str, Any]] = field(default_factory=list)
    semantic_inputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["findings"] = [asdict(item) for item in self.findings]
        return payload


SEVERITY_ORDER = {
    "info": 0,
    "warning": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def _severity_rank(value: str) -> int:
    return SEVERITY_ORDER.get(str(value).lower(), 0)


def _max_severity(findings: Sequence[DynamicFindingRecord]) -> str:
    if not findings:
        return "info"
    return max(findings, key=lambda item: _severity_rank(item.severity)).severity


def _witness_to_finding(result: DynamicWitnessResult, index: int) -> DynamicFindingRecord:
    evidence_refs = []
    for run_id in result.details.get("primary_run_ids", []):
        evidence_refs.append(str(run_id))
    for run_id in result.details.get("comparison_run_ids", []):
        evidence_refs.append(str(run_id))
    return DynamicFindingRecord(
        finding_id=f"{result.witness_id}:{index}",
        witness_id=result.witness_id,
        severity=result.severity,
        summary=result.summary,
        score=float(result.score),
        details=dict(result.details),
        evidence_refs=evidence_refs,
    )


def build_dynamic_report(
    *,
    spec_version: str,
    primary_run_ids: Iterable[str],
    comparison_run_ids: Iterable[str],
    witness_results: Sequence[DynamicWitnessResult],
    group_summaries: Optional[Mapping[str, Any]] = None,
    failure_summaries: Optional[Mapping[str, Any]] = None,
    static_context: Optional[Mapping[str, Any]] = None,
    evidence_objects: Optional[Sequence[Mapping[str, Any]]] = None,
    semantic_inputs: Optional[Mapping[str, Any]] = None,
    metadata: Optional[Mapping[str, Any]] = None,
) -> DynamicAnalyzerReport:
    findings = [
        _witness_to_finding(result, idx)
        for idx, result in enumerate(witness_results, start=1)
    ]
    blocking = [
        finding for finding in findings if _severity_rank(finding.severity) >= _severity_rank("high")
    ]
    return DynamicAnalyzerReport(
        report_type="dynamic_analyzer_report.v1",
        spec_version=str(spec_version),
        primary_run_ids=sorted(str(item) for item in primary_run_ids),
        comparison_run_ids=sorted(str(item) for item in comparison_run_ids),
        passed=not blocking,
        max_severity=_max_severity(findings),
        num_findings=len(findings),
        witnesses=[result.to_dict() for result in witness_results],
        findings=findings,
        group_summaries=dict(group_summaries or {}),
        failure_summaries=dict(failure_summaries or {}),
        static_context=dict(static_context or {}),
        evidence_objects=[dict(item) for item in (evidence_objects or [])],
        semantic_inputs=dict(semantic_inputs or {}),
        metadata=dict(metadata or {}),
    )


def write_dynamic_report(report: DynamicAnalyzerReport, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return path


def _json_load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_summary_value(run_payload: Mapping[str, Any], key: str) -> float:
    summary = run_payload.get("summary") or {}
    value = summary.get(key)
    return float(value) if value is not None else 0.0


def _collect_run_field(run_payload: Mapping[str, Any], key: str) -> List[str]:
    manifest = run_payload.get("manifest") or {}
    episodes = run_payload.get("episodes") or []
    values: List[str] = []
    if key == "source":
        manifest_source = manifest.get("source")
        if manifest_source not in (None, ""):
            values.append(str(manifest_source))
    for episode in episodes:
        value = episode.get(key)
        if value not in (None, ""):
            values.append(str(value))
    return sorted(set(values))


def summarize_run_group(run_payloads: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    if not run_payloads:
        return {
            "run_count": 0,
            "run_ids": [],
            "sources": [],
            "scenario_types": [],
            "scene_cfg_names": [],
            "episode_count": 0,
            "success_rate": 0.0,
            "collision_rate": 0.0,
            "min_distance": None,
            "average_return": 0.0,
            "near_violation_ratio": 0.0,
        }

    run_ids = [str(item.get("run_id", "")) for item in run_payloads]
    sources = sorted({value for payload in run_payloads for value in _collect_run_field(payload, "source")})
    scenario_types = sorted({value for payload in run_payloads for value in _collect_run_field(payload, "scenario_type")})
    scene_cfg_names = sorted({value for payload in run_payloads for value in _collect_run_field(payload, "scene_cfg_name")})
    min_distance_values = [
        summary.get("min_distance")
        for summary in (payload.get("summary") or {} for payload in run_payloads)
        if (summary.get("min_distance") is not None)
    ]
    return {
        "run_count": len(run_payloads),
        "run_ids": sorted(run_ids),
        "sources": sources,
        "scenario_types": scenario_types,
        "scene_cfg_names": scene_cfg_names,
        "episode_count": int(sum(int((payload.get("summary") or {}).get("episode_count", 0) or 0) for payload in run_payloads)),
        "success_rate": sum(_run_summary_value(payload, "success_rate") for payload in run_payloads) / len(run_payloads),
        "collision_rate": sum(_run_summary_value(payload, "collision_rate") for payload in run_payloads) / len(run_payloads),
        "min_distance": min(float(value) for value in min_distance_values) if min_distance_values else None,
        "average_return": sum(_run_summary_value(payload, "average_return") for payload in run_payloads) / len(run_payloads),
        "near_violation_ratio": sum(_run_summary_value(payload, "near_violation_ratio") for payload in run_payloads) / len(run_payloads),
    }


def build_group_summaries(
    run_payloads: Sequence[Mapping[str, Any]],
    *,
    grouping_keys: Sequence[str] = GROUPING_KEYS,
) -> Dict[str, Dict[str, Any]]:
    group_summaries: Dict[str, Dict[str, Any]] = {}
    for grouping_key in grouping_keys:
        grouped: Dict[str, List[Mapping[str, Any]]] = {}
        for payload in run_payloads:
            values = _collect_run_field(payload, grouping_key)
            if not values:
                values = ["unknown"]
            for value in values:
                grouped.setdefault(str(value), []).append(payload)
        group_summaries[f"by_{grouping_key}"] = {
            group_name: summarize_run_group(group_payloads)
            for group_name, group_payloads in sorted(grouped.items())
        }
    return group_summaries


def _failure_pressure(summary: Mapping[str, Any]) -> float:
    min_distance = summary.get("min_distance")
    min_distance_gap = 0.0
    if min_distance is not None:
        min_distance_gap = max(0.0, 1.0 - float(min_distance))
    pressure = (
        max(0.0, 1.0 - float(summary.get("success_rate", 0.0) or 0.0))
        + float(summary.get("collision_rate", 0.0) or 0.0)
        + float(summary.get("near_violation_ratio", 0.0) or 0.0)
        + min_distance_gap
    ) / 4.0
    return max(0.0, min(1.0, pressure))


def build_failure_summaries(
    run_payloads: Sequence[Mapping[str, Any]],
    *,
    grouping_keys: Sequence[str] = GROUPING_KEYS,
) -> Dict[str, Dict[str, Any]]:
    failure_summaries: Dict[str, Dict[str, Any]] = {}
    for grouping_name, grouped in build_group_summaries(
        run_payloads,
        grouping_keys=grouping_keys,
    ).items():
        failure_summaries[grouping_name] = {}
        for group_name, summary in grouped.items():
            enriched_summary = dict(summary)
            enriched_summary["failure_pressure"] = _failure_pressure(summary)
            failure_summaries[grouping_name][group_name] = enriched_summary
    return failure_summaries


def load_static_bundle_context(
    *,
    static_bundle_dir: str | Path | None = None,
    reports_root: str | Path | None = None,
    static_bundle_name: str | None = None,
) -> Dict[str, Any]:
    resolved_reports_root = Path(reports_root) if reports_root is not None else None
    resolved_bundle_dir: Optional[Path] = Path(static_bundle_dir) if static_bundle_dir is not None else None

    if resolved_bundle_dir is None and resolved_reports_root is not None:
        static_root = resolve_report_namespace_root(
            resolved_reports_root,
            "static_audit",
        )
        if static_bundle_name:
            candidate = static_root / static_bundle_name
            if candidate.exists():
                resolved_bundle_dir = candidate
        else:
            namespace_manifest_path = static_root / "namespace_manifest.json"
            if namespace_manifest_path.exists():
                namespace_manifest = _json_load(namespace_manifest_path)
                latest_bundle = namespace_manifest.get("latest_bundle")
                if latest_bundle:
                    candidate = static_root / str(latest_bundle)
                    if candidate.exists():
                        resolved_bundle_dir = candidate

    if resolved_reports_root is None and resolved_bundle_dir is not None:
        try:
            analysis_root = next(parent for parent in resolved_bundle_dir.parents if parent.name == "analysis")
            resolved_reports_root = analysis_root.parent
        except StopIteration:
            resolved_reports_root = None

    static_report = {}
    static_summary = {}
    static_manifest = {}
    namespace_contract = {}
    namespace_manifest = {}

    if resolved_bundle_dir is not None:
        if (resolved_bundle_dir / "static_report.json").exists():
            static_report = _json_load(resolved_bundle_dir / "static_report.json")
        if (resolved_bundle_dir / "summary.json").exists():
            static_summary = _json_load(resolved_bundle_dir / "summary.json")
        if (resolved_bundle_dir / "manifest.json").exists():
            static_manifest = _json_load(resolved_bundle_dir / "manifest.json")

        namespace_manifest_path = resolved_bundle_dir.parent / "namespace_manifest.json"
        if namespace_manifest_path.exists():
            namespace_manifest = _json_load(namespace_manifest_path)

    if resolved_reports_root is not None:
        contract_path = Path(resolved_reports_root) / "analysis" / "report_namespace_contract.json"
        if contract_path.exists():
            namespace_contract = _json_load(contract_path)

    return {
        "bundle_dir": str(resolved_bundle_dir) if resolved_bundle_dir is not None else "",
        "bundle_name": resolved_bundle_dir.name if resolved_bundle_dir is not None else "",
        "spec_version": static_report.get("spec_version") or static_manifest.get("spec_version") or "",
        "passed": static_report.get("passed", static_summary.get("passed")),
        "max_severity": static_report.get("max_severity", static_summary.get("max_severity")),
        "num_findings": static_report.get("num_findings", static_summary.get("num_findings")),
        "report_path": str(resolved_bundle_dir / "static_report.json") if resolved_bundle_dir is not None else "",
        "summary_path": str(resolved_bundle_dir / "summary.json") if resolved_bundle_dir is not None else "",
        "manifest_path": str(resolved_bundle_dir / "manifest.json") if resolved_bundle_dir is not None else "",
        "namespace_manifest": namespace_manifest,
        "namespace_contract": namespace_contract,
    }


def resolve_primary_and_comparison_runs(
    *,
    run_dirs: Sequence[str | Path] | None = None,
    compare_run_dirs: Sequence[str | Path] | None = None,
    logs_root: str | Path | None = None,
    sources: Sequence[str] | None = None,
    compare_sources: Sequence[str] | None = None,
    scenario_types: Sequence[str] | None = None,
    compare_scenario_types: Sequence[str] | None = None,
    scene_cfg_names: Sequence[str] | None = None,
    compare_scene_cfg_names: Sequence[str] | None = None,
) -> tuple[List[Path], List[Path]]:
    primary = [Path(item) for item in (run_dirs or [])]
    comparison = [Path(item) for item in (compare_run_dirs or [])]
    if logs_root is not None:
        if not primary:
            primary = discover_accepted_run_directories(
                logs_root,
                sources=sources,
                scenario_types=scenario_types,
                scene_cfg_names=scene_cfg_names,
                require_passed=True,
            )
        if not comparison and (compare_sources or compare_scenario_types or compare_scene_cfg_names):
            comparison = discover_accepted_run_directories(
                logs_root,
                sources=compare_sources,
                scenario_types=compare_scenario_types,
                scene_cfg_names=compare_scene_cfg_names,
                require_passed=True,
            )
    return primary, comparison


def run_dynamic_analysis(
    *,
    run_dirs: Sequence[str | Path] | None = None,
    compare_run_dirs: Sequence[str | Path] | None = None,
    logs_root: str | Path | None = None,
    sources: Sequence[str] | None = None,
    compare_sources: Sequence[str] | None = None,
    scenario_types: Sequence[str] | None = None,
    compare_scenario_types: Sequence[str] | None = None,
    scene_cfg_names: Sequence[str] | None = None,
    compare_scene_cfg_names: Sequence[str] | None = None,
    spec_ir: Optional[SpecIR] = None,
    spec_cfg_dir=None,
    env_cfg_dir=None,
    detector_cfg_dir=None,
    scene_families: Sequence[str] | None = None,
    output_path: str | Path | None = None,
    static_bundle_dir: str | Path | None = None,
    static_bundle_name: str | None = None,
    reports_root: str | Path | None = None,
) -> DynamicAnalyzerReport:
    effective_spec_ir = spec_ir or load_spec_ir(
        spec_cfg_dir=spec_cfg_dir,
        env_cfg_dir=env_cfg_dir,
        detector_cfg_dir=detector_cfg_dir,
        scene_families=scene_families or ("nominal", "boundary_critical", "shifted"),
    )
    resolved_run_dirs, resolved_compare_run_dirs = resolve_primary_and_comparison_runs(
        run_dirs=run_dirs,
        compare_run_dirs=compare_run_dirs,
        logs_root=logs_root,
        sources=sources,
        compare_sources=compare_sources,
        scenario_types=scenario_types,
        compare_scenario_types=compare_scenario_types,
        scene_cfg_names=scene_cfg_names,
        compare_scene_cfg_names=compare_scene_cfg_names,
    )
    if not resolved_run_dirs:
        raise ValueError("No accepted primary run directories were resolved for dynamic analysis.")

    primary_runs = load_run_directories(resolved_run_dirs, require_passed=True)
    comparison_runs = load_run_directories(resolved_compare_run_dirs or (), require_passed=True)
    static_context = load_static_bundle_context(
        static_bundle_dir=static_bundle_dir,
        reports_root=reports_root,
        static_bundle_name=static_bundle_name,
    )

    witness_results = compute_dynamic_metrics(
        primary_runs,
        comparison_run_payloads=comparison_runs or None,
        spec_ir=effective_spec_ir,
        detector_thresholds=effective_spec_ir.detector_thresholds,
        witness_weights=effective_spec_ir.witness_weights,
    )
    primary_group_summaries = build_group_summaries(primary_runs)
    comparison_group_summaries = build_group_summaries(comparison_runs)
    group_summaries = {
        "primary": primary_group_summaries,
        "comparison": comparison_group_summaries,
        "grouping_keys": list(GROUPING_KEYS),
    }
    failure_summaries = {
        "primary": build_failure_summaries(primary_runs),
        "comparison": build_failure_summaries(comparison_runs),
        "grouping_keys": list(GROUPING_KEYS),
    }
    provisional_report_payload = {
        "report_type": "dynamic_analyzer_report.v1",
        "spec_version": effective_spec_ir.spec_version,
        "primary_run_ids": [item["run_id"] for item in primary_runs],
        "comparison_run_ids": [item["run_id"] for item in comparison_runs],
        "passed": True,
        "max_severity": "info",
        "num_findings": len(witness_results),
        "witnesses": [result.to_dict() for result in witness_results],
        "group_summaries": group_summaries,
        "failure_summaries": failure_summaries,
        "static_context": static_context,
    }
    evidence_objects = build_dynamic_evidence_objects(provisional_report_payload)
    semantic_inputs = build_semantic_diagnosis_inputs(
        provisional_report_payload,
        spec_ir=effective_spec_ir,
    )
    report = build_dynamic_report(
        spec_version=effective_spec_ir.spec_version,
        primary_run_ids=[item["run_id"] for item in primary_runs],
        comparison_run_ids=[item["run_id"] for item in comparison_runs],
        witness_results=witness_results,
        group_summaries=group_summaries,
        failure_summaries=failure_summaries,
        static_context=static_context,
        evidence_objects=evidence_objects,
        semantic_inputs=semantic_inputs,
        metadata={
            "detector_type": "dynamic",
            "source_paths": dict(effective_spec_ir.source_paths),
            "report_namespace": effective_spec_ir.runtime_schema.report_namespaces.get(
                DYNAMIC_ANALYSIS_MODE,
                DYNAMIC_ANALYSIS_NAMESPACE,
            ),
            "report_artifacts": list(
                effective_spec_ir.runtime_schema.report_mode_artifacts.get(DYNAMIC_ANALYSIS_MODE, ())
            ),
            "primary_run_dirs": [str(item["run_dir"]) for item in primary_runs],
            "comparison_run_dirs": [str(item["run_dir"]) for item in comparison_runs],
            "primary_group_summaries": primary_group_summaries,
            "comparison_group_summaries": comparison_group_summaries,
            "primary_failure_summaries": failure_summaries["primary"],
            "comparison_failure_summaries": failure_summaries["comparison"],
            "grouping_keys": list(GROUPING_KEYS),
            "static_bundle_dir": str(static_bundle_dir) if static_bundle_dir else "",
            "static_context": static_context,
        },
    )
    if output_path is not None:
        write_dynamic_report(report, output_path)
    return report


def write_dynamic_analysis_bundle(
    report: DynamicAnalyzerReport,
    report_dir: str | Path,
    *,
    namespace_root: str | Path | None = None,
    bundle_name: str = "dynamic_audit_latest",
    namespace: str = DYNAMIC_ANALYSIS_NAMESPACE,
) -> Dict[str, Path]:
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)

    dynamic_report_path = write_dynamic_report(report, report_path / "dynamic_report.json")
    dynamic_evidence_path = report_path / "dynamic_evidence.json"
    semantic_inputs_path = report_path / "semantic_inputs.json"
    summary_path = report_path / "summary.json"
    manifest_path = report_path / "manifest.json"

    dynamic_evidence_path.write_text(
        json.dumps(list(report.evidence_objects), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    semantic_inputs_path.write_text(
        json.dumps(dict(report.semantic_inputs), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    witness_scores = {
        witness["witness_id"]: float(witness["score"])
        for witness in report.witnesses
    }
    summary_payload = {
        "report_type": report.report_type,
        "spec_version": report.spec_version,
        "primary_run_ids": list(report.primary_run_ids),
        "comparison_run_ids": list(report.comparison_run_ids),
        "passed": bool(report.passed),
        "max_severity": str(report.max_severity),
        "num_findings": int(report.num_findings),
        "witness_scores": witness_scores,
    }
    summary_path.write_text(
        json.dumps(summary_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    manifest_payload = {
        "bundle_type": "dynamic_analysis_bundle.v1",
        "namespace": namespace,
        "report_type": report.report_type,
        "spec_version": report.spec_version,
        "primary_run_ids": list(report.primary_run_ids),
        "comparison_run_ids": list(report.comparison_run_ids),
        "report_path": dynamic_report_path.name,
        "summary_path": summary_path.name,
        "passed": bool(report.passed),
        "max_severity": str(report.max_severity),
        "num_findings": int(report.num_findings),
        "dynamic_evidence_path": dynamic_evidence_path.name,
        "semantic_inputs_path": semantic_inputs_path.name,
        "metadata": dict(report.metadata),
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True), encoding="utf-8")

    bundle_paths: Dict[str, Path] = {
        "report_dir": report_path,
        "dynamic_report_path": dynamic_report_path,
        "dynamic_evidence_path": dynamic_evidence_path,
        "semantic_inputs_path": semantic_inputs_path,
        "summary_path": summary_path,
        "manifest_path": manifest_path,
    }
    if namespace_root is not None:
        bundle_paths["namespace_manifest_path"] = write_namespace_manifest(
            namespace_root,
            bundle_name=bundle_name,
            report_mode=DYNAMIC_ANALYSIS_MODE,
            namespace=namespace,
            bundle_paths=bundle_paths,
            report_summary={
                "passed": bool(report.passed),
                "max_severity": str(report.max_severity),
                "num_findings": int(report.num_findings),
            },
        )
    return bundle_paths


def run_dynamic_analysis_bundle(
    *,
    run_dirs: Sequence[str | Path] | None = None,
    compare_run_dirs: Sequence[str | Path] | None = None,
    logs_root: str | Path | None = None,
    sources: Sequence[str] | None = None,
    compare_sources: Sequence[str] | None = None,
    scenario_types: Sequence[str] | None = None,
    compare_scenario_types: Sequence[str] | None = None,
    scene_cfg_names: Sequence[str] | None = None,
    compare_scene_cfg_names: Sequence[str] | None = None,
    spec_ir: Optional[SpecIR] = None,
    spec_cfg_dir=None,
    env_cfg_dir=None,
    detector_cfg_dir=None,
    scene_families: Sequence[str] | None = None,
    reports_root: str | Path | None = None,
    bundle_name: str = "dynamic_audit_latest",
    report_dir: str | Path | None = None,
    output_path: str | Path | None = None,
    static_bundle_dir: str | Path | None = None,
    static_bundle_name: str | None = None,
) -> tuple[DynamicAnalyzerReport, Dict[str, Path]]:
    effective_spec_ir = spec_ir or load_spec_ir(
        spec_cfg_dir=spec_cfg_dir,
        env_cfg_dir=env_cfg_dir,
        detector_cfg_dir=detector_cfg_dir,
        scene_families=scene_families or ("nominal", "boundary_critical", "shifted"),
    )
    report = run_dynamic_analysis(
        run_dirs=run_dirs,
        compare_run_dirs=compare_run_dirs,
        logs_root=logs_root,
        sources=sources,
        compare_sources=compare_sources,
        scenario_types=scenario_types,
        compare_scenario_types=compare_scenario_types,
        scene_cfg_names=scene_cfg_names,
        compare_scene_cfg_names=compare_scene_cfg_names,
        spec_ir=effective_spec_ir,
        output_path=output_path,
        static_bundle_dir=static_bundle_dir,
        static_bundle_name=static_bundle_name,
        reports_root=reports_root,
    )

    namespace = str(report.metadata.get("report_namespace", DYNAMIC_ANALYSIS_NAMESPACE))
    namespace_root = None
    if report_dir is None:
        if reports_root is None:
            reports_root = Path(__file__).resolve().parents[1] / "reports"
        namespace_root = resolve_report_namespace_root(
            reports_root,
            DYNAMIC_ANALYSIS_MODE,
            namespaces=effective_spec_ir.runtime_schema.report_namespaces,
        )
        report_dir = namespace_root / str(bundle_name)

    bundle_paths = write_dynamic_analysis_bundle(
        report,
        report_dir,
        namespace_root=namespace_root,
        bundle_name=str(bundle_name),
        namespace=namespace,
    )
    if reports_root is not None:
        bundle_paths["namespace_contract_path"] = write_report_namespace_contract(
            reports_root,
            namespaces=effective_spec_ir.runtime_schema.report_namespaces,
            report_mode_artifacts=effective_spec_ir.runtime_schema.report_mode_artifacts,
        )
    return report, bundle_paths


__all__ = [
    "DYNAMIC_ANALYSIS_NAMESPACE",
    "DynamicAnalyzerReport",
    "DynamicFindingRecord",
    "build_failure_summaries",
    "build_group_summaries",
    "build_dynamic_report",
    "load_static_bundle_context",
    "run_dynamic_analysis",
    "run_dynamic_analysis_bundle",
    "summarize_run_group",
    "write_dynamic_analysis_bundle",
    "write_dynamic_report",
]
