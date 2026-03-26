"""Minimal report containers for Phase 4 static analysis."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


SEVERITY_ORDER = {
    "info": 0,
    "warning": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


@dataclass
class FindingRecord:
    """Machine-readable finding emitted by a detector stage."""

    finding_id: str
    check_id: str
    passed: bool
    severity: str
    summary: str
    details: Dict[str, Any] = field(default_factory=dict)
    affected_paths: List[str] = field(default_factory=list)
    recommended_action: str = ""


@dataclass
class StaticAnalyzerReport:
    """Phase 4 static analyzer report."""

    report_type: str
    spec_version: str
    scene_family_set: List[str]
    passed: bool
    max_severity: str
    num_findings: int
    findings: List[FindingRecord] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _severity_rank(value: str) -> int:
    return SEVERITY_ORDER.get(str(value).lower(), 0)


def _max_severity(findings: Sequence[FindingRecord]) -> str:
    if not findings:
        return "info"
    return max(findings, key=lambda item: _severity_rank(item.severity)).severity


def build_static_report(
    spec_version: str,
    scene_family_set: Iterable[str],
    findings: Sequence[FindingRecord],
    metadata: Dict[str, Any] | None = None,
) -> StaticAnalyzerReport:
    finding_list = list(findings)
    blocking = [
        finding
        for finding in finding_list
        if (not finding.passed) and _severity_rank(finding.severity) >= _severity_rank("high")
    ]
    return StaticAnalyzerReport(
        report_type="static_analyzer_report.v1",
        spec_version=str(spec_version),
        scene_family_set=sorted(str(item) for item in scene_family_set),
        passed=not blocking,
        max_severity=_max_severity(finding_list),
        num_findings=len(finding_list),
        findings=finding_list,
        metadata=dict(metadata or {}),
    )


def write_static_report(report: StaticAnalyzerReport, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return path
