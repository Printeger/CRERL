import json
import sys
from pathlib import Path

ISAAC_TRAINING_ROOT = Path(__file__).resolve().parents[3]
TRAINING_ROOT = ISAAC_TRAINING_ROOT / "training"
if str(TRAINING_ROOT) not in sys.path:
    sys.path.insert(0, str(TRAINING_ROOT))

# Historical / legacy pipeline imports.
from analyzers.legacy.report_generator import CREReport
from analyzers.legacy.semantic_analyzer import SemanticIssue
from analyzers.legacy.static_analyzer import StaticIssue
from repair.legacy.repair_generator import generate_repair


def _static_issue(issue_id: str, rule_id: str, *, old_value=None) -> StaticIssue:
    return StaticIssue(
        issue_id=issue_id,
        issue_type="C-R",
        severity="warning",
        rule_id=rule_id,
        description="static issue",
        traceable_fields=[],
        evidence={"old_value": old_value} if old_value is not None else {},
    )


def _semantic_issue(issue_id: str, rule_id: str, *, old_value=None) -> SemanticIssue:
    return SemanticIssue(
        issue_id=issue_id,
        issue_type="composite",
        severity="warning",
        rule_id=rule_id,
        description="semantic issue",
        traceable_fields=[],
        evidence={"old_value": old_value} if old_value is not None else {},
    )


def _cre_report(
    *,
    static_issues=None,
    dynamic_issues=None,
    semantic_issues=None,
    report_id: str = "CRE-20260412-153045",
) -> CREReport:
    return CREReport(
        report_id=report_id,
        spec_versions={"reward": "1.0"},
        static_issues=list(static_issues or []),
        dynamic_issues=list(dynamic_issues or []),
        semantic_issues=list(semantic_issues or []),
        psi_cre=0.82,
        alarm=False,
        summary={},
        output_path=None,
    )


def test_patch_id_format():
    result = generate_repair(_cre_report(static_issues=[_static_issue("CR-001", "type_compatibility")]))

    assert result.patches[0].patch_id == "PATCH-001"


def test_known_rule_generates_patch():
    result = generate_repair(_cre_report(static_issues=[_static_issue("CR-001", "type_compatibility")]))

    assert len(result.patches) == 1
    assert result.patches[0].target_spec == "reward"


def test_unknown_rule_skipped():
    result = generate_repair(_cre_report(static_issues=[_static_issue("CR-001", "unknown_rule")]))

    assert result.patches == []


def test_summary_counts():
    result = generate_repair(
        _cre_report(
            static_issues=[
                _static_issue("CR-001", "type_compatibility"),
                _static_issue("EC-001", "coverage_prebound"),
            ],
            dynamic_issues=[_static_issue("CR-101", "soft_constraint_penalty_alignment")],
            semantic_issues=[_semantic_issue("SA-001", "SEM-ALARM")],
        )
    )

    assert result.summary["total_patches"] == 4
    assert result.summary["by_target_spec"] == {"reward": 2, "constraint": 1, "env": 1}
    assert result.summary["source_issue_count"] == 4


def test_output_dir_writes_json(tmp_path):
    result = generate_repair(
        _cre_report(static_issues=[_static_issue("CR-001", "type_compatibility")]),
        output_dir=str(tmp_path),
    )
    output_path = tmp_path / "repair_result.json"

    assert result.output_path == str(output_path)
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "report_id" in payload


def test_empty_report_no_patches():
    result = generate_repair(_cre_report())

    assert result.patches == []
    assert result.summary["total_patches"] == 0


def test_report_id_passthrough():
    result = generate_repair(_cre_report(report_id="CRE-20260412-220000"))

    assert result.report_id == "CRE-20260412-220000"
