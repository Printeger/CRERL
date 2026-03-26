import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analyzers.detector_runner import run_static_analysis
from analyzers.spec_ir import load_spec_ir
from analyzers.static_checks import (
    check_constraint_runtime_binding,
    check_reward_constraint_conflicts,
    check_reward_proxy_suspicion,
)


def test_run_static_analysis_generates_machine_readable_report(tmp_path):
    output_path = tmp_path / "static_report.json"
    report = run_static_analysis(output_path=output_path)

    assert report.report_type == "static_analyzer_report.v1"
    assert report.spec_version == "v0"
    assert sorted(report.scene_family_set) == ["boundary_critical", "nominal", "shifted"]
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["spec_version"] == "v0"
    assert payload["report_type"] == "static_analyzer_report.v1"
    assert payload["passed"] is True
    assert payload["num_findings"] == 3


def test_constraint_runtime_binding_detects_missing_logged_variable():
    spec_ir = load_spec_ir()
    broken = copy.deepcopy(spec_ir)
    broken.constraints["collision_avoidance"].logged_variable = "missing_collision_field"

    result = check_constraint_runtime_binding(broken)

    assert result.passed is False
    assert result.severity == "high"
    assert result.details["missing_logged_variables"][0]["constraint_id"] == "collision_avoidance"


def test_reward_constraint_conflict_detects_missing_safety_reward_support():
    spec_ir = load_spec_ir()
    broken = copy.deepcopy(spec_ir)
    broken.reward_spec.components["reward_safety_static"].enabled = False
    broken.reward_spec.components["reward_safety_dynamic"].enabled = False

    result = check_reward_constraint_conflicts(broken)

    assert result.passed is False
    assert result.severity == "high"
    issue_kinds = {issue["kind"] for issue in result.details["issues"]}
    assert "missing_static_safety_support" in issue_kinds
    assert "missing_collision_support" in issue_kinds


def test_reward_proxy_suspicion_returns_warning_for_current_v0_assumptions():
    spec_ir = load_spec_ir()

    result = check_reward_proxy_suspicion(spec_ir)

    assert result.passed is False
    assert result.severity == "warning"
    warning_kinds = {warning["kind"] for warning in result.details["warnings"]}
    assert "constant_step_bias" in warning_kinds
    assert "progress_without_success_bonus" in warning_kinds
