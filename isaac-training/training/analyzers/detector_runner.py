"""Detector orchestration for Phase 4 static analysis."""

from __future__ import annotations

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


def run_detectors(*args, **kwargs) -> StaticAnalyzerReport:
    """Backward-compatible entrypoint for the current static-only analyzer stage."""

    return run_static_analysis(*args, **kwargs)
