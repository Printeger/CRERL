from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Any

import yaml

from analyzers.dynamic_analyzer import DynamicReport
from analyzers.static_analyzer import StaticIssue, StaticReport


SEVERITIES = ("error", "warning", "info")
ISSUE_TYPES = ("C-R", "E-C", "E-R", "composite")


@dataclass
class SemanticIssue:
    issue_id: str
    issue_type: str
    severity: str
    rule_id: str
    description: str
    traceable_fields: list[str]
    evidence: dict[str, Any]


@dataclass
class SemanticReport:
    spec_versions: dict[str, str]
    psi_cre: float
    phi_cr: float
    phi_ec: float
    phi_er: float | None
    issues: list[SemanticIssue]
    summary: dict[str, Any]
    output_path: str | None


def _load_yaml_file(path: str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a top-level mapping")
    return payload


def _clamp01(value: float) -> float:
    return max(0.0, min(float(value), 1.0))


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))


def _f(x: float, k: float = 8.0, x0: float = 0.5) -> float:
    numerator = _sigmoid(k * (x - x0)) - _sigmoid(-k * x0)
    denominator = _sigmoid(k * (1.0 - x0)) - _sigmoid(-k * x0)
    return numerator / denominator


def _make_issue_factory():
    counter = 0

    def create_issue(
        issue_type: str,
        severity: str,
        rule_id: str,
        description: str,
        traceable_fields: list[str],
        evidence: dict[str, Any] | None = None,
    ) -> SemanticIssue:
        nonlocal counter
        counter += 1
        return SemanticIssue(
            issue_id=f"SA-{counter:03d}",
            issue_type=issue_type,
            severity=severity,
            rule_id=rule_id,
            description=description,
            traceable_fields=traceable_fields,
            evidence=evidence or {},
        )

    return create_issue


def _constraint_count(constraint_spec: dict[str, Any]) -> int:
    constraints = constraint_spec.get("constraints", [])
    if not isinstance(constraints, list):
        return 0
    return len([constraint for constraint in constraints if isinstance(constraint, dict)])


def _reward_term_count(reward_spec: dict[str, Any]) -> int:
    reward_terms = reward_spec.get("reward_terms", [])
    if not isinstance(reward_terms, list):
        return 0
    return len([reward_term for reward_term in reward_terms if isinstance(reward_term, dict)])


def _collect_issue_ids(issues: list[StaticIssue], issue_type: str | None = None) -> list[str]:
    collected: list[str] = []
    for issue in issues:
        if issue_type is not None and issue.issue_type != issue_type:
            continue
        collected.append(issue.issue_id)
    return collected


def _build_summary(issues: list[SemanticIssue], alarm: bool, psi_cre: float) -> dict[str, Any]:
    by_type = {issue_type: 0 for issue_type in ISSUE_TYPES}
    by_severity = {severity: 0 for severity in SEVERITIES}
    for issue in issues:
        by_type[issue.issue_type] = by_type.get(issue.issue_type, 0) + 1
        by_severity[issue.severity] = by_severity.get(issue.severity, 0) + 1
    return {
        "alarm": alarm,
        "psi_cre": psi_cre,
        "total": len(issues),
        "by_type": by_type,
        "by_severity": by_severity,
    }


def _write_report(report: SemanticReport, output_dir: str | None) -> SemanticReport:
    if output_dir is None:
        return report
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / "semantic_report.json"
    report.output_path = str(output_path)
    output_path.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
    return report


def run_semantic_analysis(
    static_report: StaticReport,
    dynamic_report: DynamicReport,
    reward_spec_path: str,
    constraint_spec_path: str,
    output_dir: str | None = None,
) -> SemanticReport:
    reward_spec = _load_yaml_file(reward_spec_path)
    constraint_spec = _load_yaml_file(constraint_spec_path)

    dynamic_cr_issues = [issue for issue in dynamic_report.issues if issue.issue_type == "C-R"]
    static_cr_issues = [issue for issue in static_report.issues if issue.issue_type == "C-R"]
    static_ec_issues = [issue for issue in static_report.issues if issue.issue_type == "E-C"]
    dynamic_ec_issues = [issue for issue in dynamic_report.issues if issue.issue_type == "E-C"]
    static_er_issues = [issue for issue in static_report.issues if issue.issue_type == "E-R"]
    dynamic_er_issues = [issue for issue in dynamic_report.issues if issue.issue_type == "E-R"]

    cr_issues = [
        issue
        for issue in [*static_report.issues, *list(dynamic_report.issues)]
        if issue.issue_type == "C-R"
    ]
    total_terms = max(_reward_term_count(reward_spec), 1)
    phi_cr = _clamp01(min(len(cr_issues) / total_terms, 1.0))
    total_constraints = _constraint_count(constraint_spec)
    ec_issues = [
        issue
        for issue in [*static_report.issues, *list(dynamic_report.issues)]
        if issue.issue_type == "E-C"
    ]
    phi_ec = _clamp01(1.0 - min(len(ec_issues) / max(total_constraints, 1), 1.0))
    phi_er = None

    w_cr = 0.5
    w_ec = 0.5
    psi_cre = _clamp01(1.0 - (w_cr * _f(phi_cr) + w_ec * _f(1.0 - phi_ec)))
    alarm = psi_cre < 0.75

    create_issue = _make_issue_factory()
    issues: list[SemanticIssue] = []

    if phi_cr > 0.1 and static_cr_issues:
        issues.append(
            create_issue(
                issue_type="composite",
                severity="warning",
                rule_id="SEM-CR-COMPOSITE",
                description="静态/动态分析中检测到边界趋近相关 C-R 风险，形成复合冲突信号",
                traceable_fields=[
                    "static_report.issues[*].issue_type",
                    "dynamic_report.issues[*].issue_type",
                    "reward.reward_terms[*].term_id",
                ],
                evidence={
                    "phi_cr": phi_cr,
                    "threshold": 0.1,
                    "source_issue_ids": _collect_issue_ids(static_cr_issues) + _collect_issue_ids(dynamic_cr_issues),
                },
            )
        )

    if phi_ec < 0.5:
        issues.append(
            create_issue(
                issue_type="E-C",
                severity="warning",
                rule_id="SEM-EC-COVERAGE",
                description="训练环境对约束关键区域覆盖不足（φ̄¹_EC < 0.5）",
                traceable_fields=[
                    "constraint.constraints[*].constraint_id",
                    "static_report.issues[*].issue_type",
                    "dynamic_report.issues[*].issue_type",
                ],
                evidence={
                    "phi_ec": phi_ec,
                    "threshold": 0.5,
                    "total_constraints": total_constraints,
                    "source_issue_ids": _collect_issue_ids(static_ec_issues) + _collect_issue_ids(dynamic_ec_issues),
                },
            )
        )

    if static_er_issues or dynamic_er_issues:
        issues.append(
            create_issue(
                issue_type="E-R",
                severity="warning",
                rule_id="SEM-ER-DETECTION",
                description="部署 shift 风险已在静态/动态分析中检出，需确认训练分布显式覆盖",
                traceable_fields=[
                    "static_report.issues[*].issue_type",
                    "dynamic_report.issues[*].issue_type",
                ],
                evidence={
                    "phi_er": phi_er,
                    "source_issue_ids": _collect_issue_ids(static_er_issues) + _collect_issue_ids(dynamic_er_issues),
                },
            )
        )

    if alarm:
        issues.append(
            create_issue(
                issue_type="composite",
                severity="error",
                rule_id="SEM-ALARM",
                description=f"Ψ_CRE={psi_cre:.3f} 低于告警阈值 0.75，建议修复 spec",
                traceable_fields=[
                    "semantic.phi_cr",
                    "semantic.phi_ec",
                    "semantic.psi_cre",
                ],
                evidence={
                    "psi_cre": psi_cre,
                    "threshold": 0.75,
                    "phi_cr": phi_cr,
                    "phi_ec": phi_ec,
                    "phi_er": phi_er,
                    "source_issue_ids": (
                        _collect_issue_ids(static_report.issues)
                        + _collect_issue_ids(dynamic_report.issues)
                    ),
                },
            )
        )

    spec_versions = dict(static_report.spec_versions)
    spec_versions.update(dynamic_report.spec_versions)
    spec_versions.update(
        {
            "reward": str(reward_spec.get("spec_version", "")),
            "constraint": str(constraint_spec.get("spec_version", "")),
        }
    )
    report = SemanticReport(
        spec_versions=spec_versions,
        psi_cre=psi_cre,
        phi_cr=phi_cr,
        phi_ec=phi_ec,
        phi_er=phi_er,
        issues=issues,
        summary=_build_summary(issues, alarm=alarm, psi_cre=psi_cre),
        output_path=None,
    )
    return _write_report(report, output_dir)
