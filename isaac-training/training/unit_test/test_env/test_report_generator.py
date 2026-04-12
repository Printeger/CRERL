import json
import sys
from pathlib import Path

ISAAC_TRAINING_ROOT = Path(__file__).resolve().parents[3]
TRAINING_ROOT = ISAAC_TRAINING_ROOT / "training"
if str(TRAINING_ROOT) not in sys.path:
    sys.path.insert(0, str(TRAINING_ROOT))

from analyzers.dynamic_analyzer import DynamicReport
from analyzers.report_generator import generate_report
from analyzers.semantic_analyzer import SemanticIssue, SemanticReport
from analyzers.static_analyzer import StaticIssue, StaticReport


def _static_issue(issue_id: str, severity: str = "warning") -> StaticIssue:
    return StaticIssue(
        issue_id=issue_id,
        issue_type="C-R",
        severity=severity,
        rule_id="rule",
        description="static issue",
        traceable_fields=[],
        evidence={},
    )


def _semantic_issue(issue_id: str, severity: str = "warning") -> SemanticIssue:
    return SemanticIssue(
        issue_id=issue_id,
        issue_type="composite",
        severity=severity,
        rule_id="rule",
        description="semantic issue",
        traceable_fields=[],
        evidence={},
    )


def _static_report(*issues: StaticIssue, spec_versions: dict[str, str] | None = None) -> StaticReport:
    return StaticReport(
        spec_versions=spec_versions or {"reward": "static", "constraint": "static"},
        issues=list(issues),
        summary={},
        output_path=None,
    )


def _dynamic_report(*issues: StaticIssue, spec_versions: dict[str, str] | None = None) -> DynamicReport:
    return DynamicReport(
        spec_versions=spec_versions or {"constraint": "dynamic", "policy": "dynamic"},
        episode_count=1,
        issues=list(issues),
        summary={},
        output_path=None,
    )


def _semantic_report(
    *issues: SemanticIssue,
    spec_versions: dict[str, str] | None = None,
    psi_cre: float = 0.82,
    alarm: bool = False,
) -> SemanticReport:
    return SemanticReport(
        spec_versions=spec_versions or {"policy": "semantic", "environment": "semantic"},
        psi_cre=psi_cre,
        phi_cr=0.0,
        phi_ec=1.0,
        phi_er=None,
        issues=list(issues),
        summary={"alarm": alarm, "psi_cre": psi_cre},
        output_path=None,
    )


def test_report_id_format():
    report = generate_report(_static_report(), _dynamic_report(), _semantic_report())

    assert report.report_id.startswith("CRE-")


def test_spec_versions_merged():
    report = generate_report(
        _static_report(spec_versions={"reward": "static", "constraint": "static"}),
        _dynamic_report(spec_versions={"constraint": "dynamic", "policy": "dynamic"}),
        _semantic_report(spec_versions={"policy": "semantic", "environment": "semantic"}),
    )

    assert report.spec_versions == {
        "reward": "static",
        "constraint": "dynamic",
        "policy": "semantic",
        "environment": "semantic",
    }


def test_psi_cre_and_alarm_passthrough():
    semantic_report = _semantic_report(psi_cre=0.33, alarm=True)

    report = generate_report(_static_report(), _dynamic_report(), semantic_report)

    assert report.psi_cre == 0.33
    assert report.alarm is True


def test_summary_counts():
    report = generate_report(
        _static_report(_static_issue("CR-001", "error"), _static_issue("CR-002", "warning")),
        _dynamic_report(_static_issue("CR-101", "info")),
        _semantic_report(_semantic_issue("SA-001", "warning"), _semantic_issue("SA-002", "info")),
    )

    assert report.summary["total"] == 5
    assert report.summary["by_phase"] == {"static": 2, "dynamic": 1, "semantic": 2}
    assert report.summary["by_severity"] == {"error": 1, "warning": 2, "info": 2}


def test_output_dir_writes_json(tmp_path):
    report = generate_report(_static_report(), _dynamic_report(), _semantic_report(), output_dir=str(tmp_path))
    output_path = tmp_path / "report.json"

    assert report.output_path == str(output_path)
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "report_id" in payload


def test_empty_issues():
    report = generate_report(_static_report(), _dynamic_report(), _semantic_report())

    assert report.summary["total"] == 0
    assert report.alarm is False
