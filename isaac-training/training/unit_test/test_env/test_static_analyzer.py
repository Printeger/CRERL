import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analyzers.detector_runner import run_static_analysis
from analyzers.spec_ir import _load_yaml_file, load_spec_ir
from analyzers.static_checks import (
    check_constraint_runtime_binding,
    check_execution_mode_alignment,
    check_required_runtime_fields,
    check_reward_constraint_conflicts,
    check_reward_proxy_suspicion,
    check_scene_family_coverage,
    check_scene_family_structure,
)

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "static_specs"
DEFAULT_SPEC_CFG_DIR = ROOT / "cfg" / "spec_cfg"
DEFAULT_ENV_CFG_DIR = ROOT / "cfg" / "env_cfg"
DEFAULT_DETECTOR_CFG_DIR = ROOT / "cfg" / "detector_cfg"


def _deep_merge(base, patch):
    merged = copy.deepcopy(base)
    for key, value in patch.items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _materialize_fixture_bundle(tmp_path: Path, fixture_name: str):
    spec_cfg_dir = tmp_path / "spec_cfg"
    env_cfg_dir = tmp_path / "env_cfg"
    detector_cfg_dir = tmp_path / "detector_cfg"
    shutil.copytree(DEFAULT_SPEC_CFG_DIR, spec_cfg_dir)
    shutil.copytree(DEFAULT_ENV_CFG_DIR, env_cfg_dir)
    shutil.copytree(DEFAULT_DETECTOR_CFG_DIR, detector_cfg_dir)

    patch_bundle = _load_yaml_file(FIXTURE_ROOT / fixture_name)
    root_map = {
        "spec_cfg": spec_cfg_dir,
        "env_cfg": env_cfg_dir,
        "detector_cfg": detector_cfg_dir,
    }
    for root_name, file_patches in patch_bundle.items():
        target_root = root_map[root_name]
        for filename, patch in file_patches.items():
            target_path = target_root / filename
            base_data = _load_yaml_file(target_path)
            merged_data = _deep_merge(base_data, patch)
            target_path.write_text(
                json.dumps(merged_data, indent=2, sort_keys=True),
                encoding="utf-8",
            )
    return spec_cfg_dir, env_cfg_dir, detector_cfg_dir


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
    assert payload["num_findings"] == 7


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


def test_scene_family_coverage_detects_undercovered_scene_requirement(tmp_path):
    spec_cfg_dir, env_cfg_dir, detector_cfg_dir = _materialize_fixture_bundle(
        tmp_path,
        "scene_family_undercoverage.yaml",
    )
    broken = load_spec_ir(
        spec_cfg_dir=spec_cfg_dir,
        env_cfg_dir=env_cfg_dir,
        detector_cfg_dir=detector_cfg_dir,
    )

    result = check_scene_family_coverage(broken)

    assert result.passed is False
    assert result.severity == "high"
    uncovered = result.details["uncovered_requirements"]
    assert uncovered[0]["constraint_id"] == "safety_margin"
    assert uncovered[0]["requirement"] == "dynamic_obstacles"


def test_required_runtime_fields_detects_missing_reward_binding(tmp_path):
    spec_cfg_dir, env_cfg_dir, detector_cfg_dir = _materialize_fixture_bundle(
        tmp_path,
        "missing_runtime_field.yaml",
    )
    broken = load_spec_ir(
        spec_cfg_dir=spec_cfg_dir,
        env_cfg_dir=env_cfg_dir,
        detector_cfg_dir=detector_cfg_dir,
    )

    result = check_required_runtime_fields(broken)

    assert result.passed is False
    assert result.severity == "high"
    missing = {
        item["component_key"]: item["expected_logged_key"]
        for item in result.details["missing_reward_logged_keys"]
    }
    assert missing["reward_progress"] == "missing_reward_progress"


def test_bad_reward_conflict_fixture_blocks_static_report(tmp_path):
    spec_cfg_dir, env_cfg_dir, detector_cfg_dir = _materialize_fixture_bundle(
        tmp_path,
        "reward_constraint_conflict.yaml",
    )
    output_path = tmp_path / "static_report.json"
    report = run_static_analysis(
        spec_cfg_dir=spec_cfg_dir,
        env_cfg_dir=env_cfg_dir,
        detector_cfg_dir=detector_cfg_dir,
        output_path=output_path,
    )

    assert report.passed is False
    assert report.max_severity == "high"
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    failing_checks = {
        finding["check_id"]
        for finding in payload["findings"]
        if not finding["passed"]
    }
    assert "reward_constraint_conflicts" in failing_checks


def test_scene_family_structure_detects_invalid_template_range(tmp_path):
    spec_cfg_dir, env_cfg_dir, detector_cfg_dir = _materialize_fixture_bundle(
        tmp_path,
        "scene_family_structure_invalid.yaml",
    )
    broken = load_spec_ir(
        spec_cfg_dir=spec_cfg_dir,
        env_cfg_dir=env_cfg_dir,
        detector_cfg_dir=detector_cfg_dir,
    )

    result = check_scene_family_structure(broken)

    assert result.passed is False
    assert result.severity == "high"
    issue_kinds = {issue["kind"] for issue in result.details["issues"]}
    assert "invalid_template_count_range" in issue_kinds


def test_execution_mode_alignment_detects_rollout_gap(tmp_path):
    spec_cfg_dir, env_cfg_dir, detector_cfg_dir = _materialize_fixture_bundle(
        tmp_path,
        "execution_mode_misalignment.yaml",
    )
    broken = load_spec_ir(
        spec_cfg_dir=spec_cfg_dir,
        env_cfg_dir=env_cfg_dir,
        detector_cfg_dir=detector_cfg_dir,
    )

    result = check_execution_mode_alignment(broken)

    assert result.passed is False
    assert result.severity == "high"
    issue_kinds = {issue["kind"] for issue in result.details["issues"]}
    assert "rollout_mode_gap" in issue_kinds


def test_run_static_audit_cli_writes_machine_readable_report(tmp_path):
    report_dir = tmp_path / "cli_bundle"
    output_path = tmp_path / "cli_static_report.json"
    command = [
        sys.executable,
        str(ROOT / "scripts" / "run_static_audit.py"),
        "--report-dir",
        str(report_dir),
        "--output",
        str(output_path),
    ]
    result = subprocess.run(
        command,
        cwd=ROOT.parent,
        capture_output=True,
        text=True,
        check=True,
    )

    assert output_path.exists()
    assert (report_dir / "static_report.json").exists()
    assert (report_dir / "summary.json").exists()
    assert (report_dir / "manifest.json").exists()
    stdout_payload = json.loads(result.stdout)
    file_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert stdout_payload["passed"] is True
    assert stdout_payload["num_findings"] == 7
    assert stdout_payload["report_dir"] == str(report_dir)
    assert file_payload["report_type"] == "static_analyzer_report.v1"
