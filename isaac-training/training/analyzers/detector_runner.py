"""Detector orchestration for Phase 4 static analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from .aggregation import FindingRecord, StaticAnalyzerReport, build_static_report, write_static_report
from .report_contract import (
    DEFAULT_REPORT_NAMESPACES,
    STATIC_AUDIT_MODE,
    resolve_report_namespace_root,
    write_namespace_manifest,
    write_report_namespace_contract,
)
from .spec_ir import (
    SpecIR,
    load_spec_ir,
)
from .static_checks import StaticCheckResult, run_static_checks

STATIC_AUDIT_NAMESPACE = DEFAULT_REPORT_NAMESPACES[STATIC_AUDIT_MODE]


def _finding_from_check(result: StaticCheckResult, index: int) -> FindingRecord:
    return FindingRecord(
        finding_id=f"{result.check_id}:{index}",
        check_id=result.check_id,
        passed=result.passed,
        severity=result.severity,
        summary=result.summary,
        details=dict(result.details),
        affected_paths=list(result.affected_paths),
        recommended_action=result.recommended_action,
    )


def run_static_analysis(
    spec_ir: Optional[SpecIR] = None,
    *,
    spec_cfg_dir=None,
    env_cfg_dir=None,
    detector_cfg_dir=None,
    scene_families: Sequence[str] | None = None,
    check_ids: Sequence[str] | None = None,
    output_path: str | Path | None = None,
) -> StaticAnalyzerReport:
    effective_spec_ir = spec_ir or load_spec_ir(
        spec_cfg_dir=spec_cfg_dir,
        env_cfg_dir=env_cfg_dir,
        detector_cfg_dir=detector_cfg_dir,
        scene_families=scene_families or ("nominal", "boundary_critical", "shifted"),
    )
    check_results = run_static_checks(effective_spec_ir, check_ids=check_ids)
    findings = [
        _finding_from_check(result, idx)
        for idx, result in enumerate(check_results, start=1)
    ]
    report = build_static_report(
        spec_version=effective_spec_ir.spec_version,
        scene_family_set=effective_spec_ir.environment_families.keys(),
        findings=findings,
        metadata={
            "detector_type": "static",
            "source_paths": dict(effective_spec_ir.source_paths),
            "check_ids": [result.check_id for result in check_results],
            "report_namespace": effective_spec_ir.runtime_schema.report_namespaces.get(
                STATIC_AUDIT_MODE,
                STATIC_AUDIT_NAMESPACE,
            ),
            "report_artifacts": list(
                effective_spec_ir.runtime_schema.report_mode_artifacts.get(STATIC_AUDIT_MODE, ())
            ),
        },
    )
    if output_path is not None:
        write_static_report(report, output_path)
    return report


def write_static_audit_bundle(
    report: StaticAnalyzerReport,
    report_dir: str | Path,
    *,
    namespace_root: str | Path | None = None,
    bundle_name: str = "static_audit_latest",
    namespace: str = STATIC_AUDIT_NAMESPACE,
) -> Dict[str, Path]:
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)

    static_report_path = write_static_report(report, report_path / "static_report.json")
    summary_path = report_path / "summary.json"
    manifest_path = report_path / "manifest.json"

    summary_payload = {
        "report_type": report.report_type,
        "spec_version": report.spec_version,
        "scene_family_set": list(report.scene_family_set),
        "passed": bool(report.passed),
        "max_severity": str(report.max_severity),
        "num_findings": int(report.num_findings),
    }
    summary_path.write_text(
        json.dumps(summary_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    manifest_payload = {
        "bundle_type": "static_audit_bundle.v3",
        "namespace": namespace,
        "report_type": report.report_type,
        "spec_version": report.spec_version,
        "scene_family_set": list(report.scene_family_set),
        "report_path": static_report_path.name,
        "summary_path": summary_path.name,
        "passed": bool(report.passed),
        "max_severity": str(report.max_severity),
        "num_findings": int(report.num_findings),
        "metadata": dict(report.metadata),
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True), encoding="utf-8")

    bundle_paths = {
        "report_dir": report_path,
        "static_report_path": static_report_path,
        "summary_path": summary_path,
        "manifest_path": manifest_path,
    }
    if namespace_root is not None:
        bundle_paths["namespace_manifest_path"] = write_namespace_manifest(
            namespace_root,
            bundle_name=bundle_name,
            report_mode=STATIC_AUDIT_MODE,
            namespace=namespace,
            bundle_paths=bundle_paths,
            report_summary={
                "passed": bool(report.passed),
                "max_severity": str(report.max_severity),
                "num_findings": int(report.num_findings),
            },
        )
    return bundle_paths


def run_static_analysis_bundle(
    spec_ir: Optional[SpecIR] = None,
    *,
    spec_cfg_dir=None,
    env_cfg_dir=None,
    detector_cfg_dir=None,
    scene_families: Sequence[str] | None = None,
    check_ids: Sequence[str] | None = None,
    reports_root: str | Path | None = None,
    bundle_name: str = "static_audit_latest",
    report_dir: str | Path | None = None,
    output_path: str | Path | None = None,
) -> tuple[StaticAnalyzerReport, Dict[str, Path]]:
    effective_spec_ir = spec_ir or load_spec_ir(
        spec_cfg_dir=spec_cfg_dir,
        env_cfg_dir=env_cfg_dir,
        detector_cfg_dir=detector_cfg_dir,
        scene_families=scene_families or ("nominal", "boundary_critical", "shifted"),
    )
    report = run_static_analysis(
        spec_ir=effective_spec_ir,
        check_ids=check_ids,
        output_path=output_path,
    )

    namespace = str(report.metadata.get("report_namespace", STATIC_AUDIT_NAMESPACE))
    namespace_root = None
    if report_dir is None:
        if reports_root is None:
            reports_root = Path(__file__).resolve().parents[1] / "reports"
        namespace_root = resolve_report_namespace_root(
            reports_root,
            STATIC_AUDIT_MODE,
            namespaces=effective_spec_ir.runtime_schema.report_namespaces,
        )
        report_dir = namespace_root / str(bundle_name)

    bundle_paths = write_static_audit_bundle(
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


def run_detectors(*args, **kwargs) -> StaticAnalyzerReport:
    """Backward-compatible entrypoint for the current static-only analyzer stage."""

    return run_static_analysis(*args, **kwargs)
