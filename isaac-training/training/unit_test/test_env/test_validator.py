import json
import sys
from pathlib import Path

ISAAC_TRAINING_ROOT = Path(__file__).resolve().parents[3]
TRAINING_ROOT = ISAAC_TRAINING_ROOT / "training"
if str(TRAINING_ROOT) not in sys.path:
    sys.path.insert(0, str(TRAINING_ROOT))

from analyzers.static_analyzer import StaticReport, run_static_analysis
from repair.repair_generator import RepairPatch, RepairResult
from repair.validator import validate_repair


SPEC_DIR = TRAINING_ROOT / "cfg" / "spec_cfg"


def _real_static_report() -> StaticReport:
    return run_static_analysis(
        str(SPEC_DIR / "reward_spec_v1.yaml"),
        str(SPEC_DIR / "constraint_spec_v1.yaml"),
        str(SPEC_DIR / "policy_spec_v1.yaml"),
        str(SPEC_DIR / "env_spec_v1.yaml"),
    )


def _repair_result(*patches: RepairPatch, report_id: str = "CRE-20260412-153045") -> RepairResult:
    return RepairResult(
        report_id=report_id,
        patches=list(patches),
        summary={},
        output_path=None,
    )


def _patch(
    patch_id: str,
    *,
    target_spec: str,
    target_field: str,
    operation: str,
    new_value,
) -> RepairPatch:
    return RepairPatch(
        patch_id=patch_id,
        target_spec=target_spec,
        target_field=target_field,
        operation=operation,
        old_value=None,
        new_value=new_value,
        rationale="test patch",
        source_issue_ids=["TEST-001"],
    )


def test_passed_when_no_issues_introduced():
    static_report = _real_static_report()
    repair_result = _repair_result(
        _patch(
            "PATCH-001",
            target_spec="reward",
            target_field="reward_terms[*].weight",
            operation="set",
            new_value=0.0,
        )
    )

    result = validate_repair(
        repair_result,
        static_report,
        str(SPEC_DIR / "reward_spec_v1.yaml"),
        str(SPEC_DIR / "constraint_spec_v1.yaml"),
        str(SPEC_DIR / "policy_spec_v1.yaml"),
        str(SPEC_DIR / "env_spec_v1.yaml"),
    )

    assert result.passed is True


def test_failed_when_issues_introduced():
    static_report = StaticReport(spec_versions={}, issues=[], summary={}, output_path=None)
    result = validate_repair(
        _repair_result(),
        static_report,
        str(SPEC_DIR / "reward_spec_v1.yaml"),
        str(SPEC_DIR / "constraint_spec_v1.yaml"),
        str(SPEC_DIR / "policy_spec_v1.yaml"),
        str(SPEC_DIR / "env_spec_v1.yaml"),
    )

    assert result.passed is False


def test_issues_resolved_computed_correctly():
    static_report = _real_static_report()
    result = validate_repair(
        _repair_result(
            _patch(
                "PATCH-001",
                target_spec="reward",
                target_field="reward_terms[*].weight",
                operation="set",
                new_value=0.0,
            )
        ),
        static_report,
        str(SPEC_DIR / "reward_spec_v1.yaml"),
        str(SPEC_DIR / "constraint_spec_v1.yaml"),
        str(SPEC_DIR / "policy_spec_v1.yaml"),
        str(SPEC_DIR / "env_spec_v1.yaml"),
    )

    expected = [issue_id for issue_id in result.issues_before if issue_id not in result.issues_after]
    assert result.issues_resolved == expected


def test_issues_introduced_computed_correctly():
    result = validate_repair(
        _repair_result(),
        StaticReport(spec_versions={}, issues=[], summary={}, output_path=None),
        str(SPEC_DIR / "reward_spec_v1.yaml"),
        str(SPEC_DIR / "constraint_spec_v1.yaml"),
        str(SPEC_DIR / "policy_spec_v1.yaml"),
        str(SPEC_DIR / "env_spec_v1.yaml"),
    )

    assert result.issues_introduced == result.issues_after


def test_empty_repair_no_change():
    static_report = _real_static_report()
    result = validate_repair(
        _repair_result(),
        static_report,
        str(SPEC_DIR / "reward_spec_v1.yaml"),
        str(SPEC_DIR / "constraint_spec_v1.yaml"),
        str(SPEC_DIR / "policy_spec_v1.yaml"),
        str(SPEC_DIR / "env_spec_v1.yaml"),
    )

    assert result.issues_before == result.issues_after
    assert result.passed is False


def test_output_dir_writes_json(tmp_path):
    result = validate_repair(
        _repair_result(),
        _real_static_report(),
        str(SPEC_DIR / "reward_spec_v1.yaml"),
        str(SPEC_DIR / "constraint_spec_v1.yaml"),
        str(SPEC_DIR / "policy_spec_v1.yaml"),
        str(SPEC_DIR / "env_spec_v1.yaml"),
        output_dir=str(tmp_path),
    )
    output_path = tmp_path / "validation_result.json"

    assert result.output_path == str(output_path)
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "report_id" in payload


def test_report_id_passthrough():
    result = validate_repair(
        _repair_result(report_id="CRE-20260412-230000"),
        _real_static_report(),
        str(SPEC_DIR / "reward_spec_v1.yaml"),
        str(SPEC_DIR / "constraint_spec_v1.yaml"),
        str(SPEC_DIR / "policy_spec_v1.yaml"),
        str(SPEC_DIR / "env_spec_v1.yaml"),
    )

    assert result.report_id == "CRE-20260412-230000"
