import json
import sys
from pathlib import Path

import pytest

ISAAC_TRAINING_ROOT = Path(__file__).resolve().parents[3]
TRAINING_ROOT = ISAAC_TRAINING_ROOT / "training"
if str(TRAINING_ROOT) not in sys.path:
    sys.path.insert(0, str(TRAINING_ROOT))

# Historical / legacy pipeline imports.
from analyzers.legacy.dynamic_analyzer import DynamicReport
from analyzers.legacy.semantic_analyzer import run_semantic_analysis
from analyzers.legacy.static_analyzer import StaticIssue, StaticReport


SPEC_DIR = TRAINING_ROOT / "cfg" / "spec_cfg"
SPEC_VERSIONS = {
    "reward": "1.0",
    "constraint": "1.0",
    "policy": "1.0",
    "environment": "1.0",
}


def _issue(issue_id: str, issue_type: str, severity: str = "warning", rule_id: str = "rule") -> StaticIssue:
    return StaticIssue(
        issue_id=issue_id,
        issue_type=issue_type,
        severity=severity,
        rule_id=rule_id,
        description=f"{issue_type} issue",
        traceable_fields=[],
        evidence={},
    )


def _static_report(*issues: StaticIssue) -> StaticReport:
    return StaticReport(
        spec_versions=dict(SPEC_VERSIONS),
        issues=list(issues),
        summary={},
        output_path=None,
    )


def _dynamic_report(*issues: StaticIssue, episode_count: int = 10) -> DynamicReport:
    return DynamicReport(
        spec_versions={"reward": "1.0", "constraint": "1.0"},
        episode_count=episode_count,
        issues=list(issues),
        summary={},
        output_path=None,
    )


def _run(static_report: StaticReport, dynamic_report: DynamicReport, output_dir: Path | None = None):
    return run_semantic_analysis(
        static_report,
        dynamic_report,
        str(SPEC_DIR / "reward_spec_v1.yaml"),
        str(SPEC_DIR / "constraint_spec_v1.yaml"),
        output_dir=str(output_dir) if output_dir is not None else None,
    )


def test_phi_cr_zero_no_cr_issues():
    report = _run(_static_report(), _dynamic_report())

    assert report.phi_cr == 0.0
    assert report.psi_cre == pytest.approx(1.0, abs=1e-9)


def test_phi_cr_nonzero_with_cr_issues():
    report = _run(
        _static_report(_issue("CR-001", "C-R")),
        _dynamic_report(_issue("CR-101", "C-R"), episode_count=4),
    )

    assert report.phi_cr > 0.0
    assert any(issue.rule_id == "SEM-CR-COMPOSITE" for issue in report.issues)


def test_phi_ec_low_triggers_coverage_warning():
    report = _run(
        _static_report(
            _issue("EC-001", "E-C"),
            _issue("EC-002", "E-C"),
            _issue("EC-003", "E-C"),
        ),
        _dynamic_report(),
    )

    assert report.phi_ec < 0.5
    assert any(issue.rule_id == "SEM-EC-COVERAGE" for issue in report.issues)


def test_alarm_triggered_when_psi_below_threshold():
    report = _run(
        _static_report(
            _issue("CR-001", "C-R"),
            _issue("CR-002", "C-R"),
            _issue("CR-003", "C-R"),
            _issue("CR-004", "C-R"),
        ),
        _dynamic_report(),
    )

    assert report.summary["alarm"] is True
    assert any(issue.rule_id == "SEM-ALARM" and issue.severity == "error" for issue in report.issues)


def test_no_alarm_clean_input():
    report = _run(_static_report(), _dynamic_report())

    assert report.summary["alarm"] is False
    assert report.issues == []


def test_phi_er_always_none():
    report = _run(_static_report(_issue("EC-001", "E-C")), _dynamic_report(_issue("CR-001", "C-R")))

    assert report.phi_er is None


def test_output_dir_writes_json(tmp_path):
    report = _run(_static_report(), _dynamic_report(), output_dir=tmp_path)
    output_path = tmp_path / "semantic_report.json"

    assert report.output_path == str(output_path)
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "psi_cre" in payload


def test_psi_cre_in_range():
    report = _run(
        _static_report(_issue("EC-001", "E-C"), _issue("CR-001", "C-R")),
        _dynamic_report(_issue("CR-101", "C-R"), _issue("EC-101", "E-C"), episode_count=3),
    )

    assert 0.0 <= report.psi_cre <= 1.0
