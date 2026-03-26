"""Detector orchestration for Phase 4 static analysis."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from .aggregation import FindingRecord, StaticAnalyzerReport, build_static_report, write_static_report
from .spec_ir import SpecIR, load_spec_ir
from .static_checks import StaticCheckResult, run_static_checks


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
        },
    )
    if output_path is not None:
        write_static_report(report, output_path)
    return report


def write_static_audit_bundle(
    report: StaticAnalyzerReport,
    report_dir: str | Path,
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
        "bundle_type": "static_audit_bundle.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
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
    manifest_path.write_text(
        json.dumps(manifest_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "report_dir": report_path,
        "static_report_path": static_report_path,
        "summary_path": summary_path,
        "manifest_path": manifest_path,
    }


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
    report = run_static_analysis(
        spec_ir=spec_ir,
        spec_cfg_dir=spec_cfg_dir,
        env_cfg_dir=env_cfg_dir,
        detector_cfg_dir=detector_cfg_dir,
        scene_families=scene_families,
        check_ids=check_ids,
        output_path=output_path,
    )

    if report_dir is None:
        if reports_root is None:
            reports_root = Path(__file__).resolve().parents[1] / "reports"
        report_dir = Path(reports_root) / "static_audits" / str(bundle_name)

    bundle_paths = write_static_audit_bundle(report, report_dir)
    return report, bundle_paths


def run_detectors(*args, **kwargs) -> StaticAnalyzerReport:
    """Backward-compatible entrypoint for the current static-only analyzer stage."""

    return run_static_analysis(*args, **kwargs)
