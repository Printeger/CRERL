from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from analyzers.legacy.dynamic_analyzer import DynamicReport
from analyzers.legacy.semantic_analyzer import SemanticIssue, SemanticReport
from analyzers.legacy.static_analyzer import StaticIssue, StaticReport


SEVERITIES = ("error", "warning", "info")


@dataclass
class CREReport:
    report_id: str
    spec_versions: dict[str, str]
    static_issues: list[StaticIssue]
    dynamic_issues: list[StaticIssue]
    semantic_issues: list[SemanticIssue]
    psi_cre: float
    alarm: bool
    summary: dict[str, Any]
    output_path: str | None


def _generate_report_id() -> str:
    return datetime.utcnow().strftime("CRE-%Y%m%d-%H%M%S")


def _build_summary(
    static_issues: list[StaticIssue],
    dynamic_issues: list[StaticIssue],
    semantic_issues: list[SemanticIssue],
    *,
    alarm: bool,
    psi_cre: float,
) -> dict[str, Any]:
    by_phase = {
        "static": len(static_issues),
        "dynamic": len(dynamic_issues),
        "semantic": len(semantic_issues),
    }
    by_severity = {severity: 0 for severity in SEVERITIES}
    for issue in [*static_issues, *dynamic_issues, *semantic_issues]:
        by_severity[issue.severity] = by_severity.get(issue.severity, 0) + 1
    return {
        "total": sum(by_phase.values()),
        "by_phase": by_phase,
        "by_severity": by_severity,
        "alarm": alarm,
        "psi_cre": psi_cre,
    }


def _write_report(report: CREReport, output_dir: str | None) -> CREReport:
    if output_dir is None:
        return report
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / "report.json"
    report.output_path = str(output_path)
    output_path.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
    return report


def generate_report(
    static_report: StaticReport,
    dynamic_report: DynamicReport,
    semantic_report: SemanticReport,
    output_dir: str | None = None,
) -> CREReport:
    spec_versions = dict(static_report.spec_versions)
    spec_versions.update(dynamic_report.spec_versions)
    spec_versions.update(semantic_report.spec_versions)

    static_issues = list(static_report.issues)
    dynamic_issues = list(dynamic_report.issues)
    semantic_issues = list(semantic_report.issues)
    psi_cre = semantic_report.psi_cre
    alarm = bool(semantic_report.summary.get("alarm", False))

    report = CREReport(
        report_id=_generate_report_id(),
        spec_versions=spec_versions,
        static_issues=static_issues,
        dynamic_issues=dynamic_issues,
        semantic_issues=semantic_issues,
        psi_cre=psi_cre,
        alarm=alarm,
        summary=_build_summary(
            static_issues,
            dynamic_issues,
            semantic_issues,
            alarm=alarm,
            psi_cre=psi_cre,
        ),
        output_path=None,
    )
    return _write_report(report, output_dir)
