"""Rollout-based dynamic analyzer for Phase 5 CRE witness metrics."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from analyzers.dynamic_metrics import DynamicWitnessResult, compute_dynamic_metrics
from analyzers.report_contract import (
    DEFAULT_REPORT_NAMESPACES,
    DYNAMIC_ANALYSIS_MODE,
    resolve_report_namespace_root,
    write_namespace_manifest,
    write_report_namespace_contract,
)
from analyzers.spec_ir import SpecIR, load_spec_ir
from runtime_logging.episode_writer import load_run_directories


DYNAMIC_ANALYSIS_NAMESPACE = DEFAULT_REPORT_NAMESPACES[DYNAMIC_ANALYSIS_MODE]


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
        metadata=dict(metadata or {}),
    )


def write_dynamic_report(report: DynamicAnalyzerReport, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return path


def run_dynamic_analysis(
    *,
    run_dirs: Sequence[str | Path],
    compare_run_dirs: Sequence[str | Path] | None = None,
    spec_ir: Optional[SpecIR] = None,
    spec_cfg_dir=None,
    env_cfg_dir=None,
    detector_cfg_dir=None,
    scene_families: Sequence[str] | None = None,
    output_path: str | Path | None = None,
    static_bundle_dir: str | Path | None = None,
) -> DynamicAnalyzerReport:
    effective_spec_ir = spec_ir or load_spec_ir(
        spec_cfg_dir=spec_cfg_dir,
        env_cfg_dir=env_cfg_dir,
        detector_cfg_dir=detector_cfg_dir,
        scene_families=scene_families or ("nominal", "boundary_critical", "shifted"),
    )
    primary_runs = load_run_directories(run_dirs, require_passed=True)
    comparison_runs = load_run_directories(compare_run_dirs or (), require_passed=True)

    witness_results = compute_dynamic_metrics(
        primary_runs,
        comparison_run_payloads=comparison_runs or None,
        spec_ir=effective_spec_ir,
        detector_thresholds=effective_spec_ir.detector_thresholds,
        witness_weights=effective_spec_ir.witness_weights,
    )
    report = build_dynamic_report(
        spec_version=effective_spec_ir.spec_version,
        primary_run_ids=[item["run_id"] for item in primary_runs],
        comparison_run_ids=[item["run_id"] for item in comparison_runs],
        witness_results=witness_results,
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
            "static_bundle_dir": str(static_bundle_dir) if static_bundle_dir else "",
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
    summary_path = report_path / "summary.json"
    manifest_path = report_path / "manifest.json"

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
        "metadata": dict(report.metadata),
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True), encoding="utf-8")

    bundle_paths: Dict[str, Path] = {
        "report_dir": report_path,
        "dynamic_report_path": dynamic_report_path,
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
    run_dirs: Sequence[str | Path],
    compare_run_dirs: Sequence[str | Path] | None = None,
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
        spec_ir=effective_spec_ir,
        output_path=output_path,
        static_bundle_dir=static_bundle_dir,
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
    "build_dynamic_report",
    "run_dynamic_analysis",
    "run_dynamic_analysis_bundle",
    "write_dynamic_analysis_bundle",
    "write_dynamic_report",
]
