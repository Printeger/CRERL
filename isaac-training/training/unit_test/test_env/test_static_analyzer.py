import copy
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Historical / legacy pipeline imports.
from analyzers.legacy.static_analyzer import StaticReport, run_static_analysis


SPEC_DIR = ROOT / "cfg" / "spec_cfg"


def _load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _write_yaml(path: Path, payload) -> None:
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=False)


def _materialize_bundle(tmp_path: Path, overrides=None):
    overrides = overrides or {}
    bundle_paths = {}
    filename_map = {
        "reward": "reward_spec_v1.yaml",
        "constraint": "constraint_spec_v1.yaml",
        "policy": "policy_spec_v1.yaml",
        "environment": "env_spec_v1.yaml",
    }
    for spec_name, filename in filename_map.items():
        data = copy.deepcopy(_load_yaml(SPEC_DIR / filename))
        if spec_name in overrides:
            overrides[spec_name](data)
        target_path = tmp_path / filename
        _write_yaml(target_path, data)
        bundle_paths[spec_name] = target_path
    return bundle_paths


def _run_bundle(bundle_paths, output_dir=None):
    return run_static_analysis(
        str(bundle_paths["reward"]),
        str(bundle_paths["constraint"]),
        str(bundle_paths["policy"]),
        str(bundle_paths["environment"]),
        output_dir=str(output_dir) if output_dir is not None else None,
    )


def test_valid_spec_no_errors(tmp_path):
    bundle_paths = _materialize_bundle(tmp_path)

    report = _run_bundle(bundle_paths)

    assert isinstance(report, StaticReport)
    assert not hasattr(report, "valid")
    assert isinstance(report.issues, list)
    assert all(issue.severity != "error" for issue in report.issues)


def test_cr_type_compatibility_fires(tmp_path):
    def patch_reward(data):
        data["reward_terms"][0]["term_expr"] = "min_obstacle_distance_m - goal_distance_t"
        data["reward_terms"][0]["weight"] = 1.0

    bundle_paths = _materialize_bundle(tmp_path, overrides={"reward": patch_reward})

    report = _run_bundle(bundle_paths)

    assert any(
        issue.issue_type == "C-R" and issue.rule_id == "type_compatibility"
        for issue in report.issues
    )


def test_ec_coverage_prebound_fires(tmp_path):
    def patch_constraint(data):
        data["constraints"][0]["constraint_id"] = "xyz_constraint"
        data["constraints"][0]["severity"] = "hard"

    def patch_environment(data):
        data["E_tr"]["scene_families"] = ["nominal"]

    bundle_paths = _materialize_bundle(
        tmp_path,
        overrides={
            "constraint": patch_constraint,
            "environment": patch_environment,
        },
    )

    report = _run_bundle(bundle_paths)

    matching_issues = [
        issue
        for issue in report.issues
        if issue.issue_type == "E-C" and issue.rule_id == "coverage_prebound"
    ]
    assert matching_issues
    assert matching_issues[0].evidence["e_tr_family_count"] == 1


def test_er_deployment_shift_fires(tmp_path):
    def patch_environment(data):
        data["E_tr"]["shift_operators"] = []
        data["E_dep"]["deployment_envs"][0]["applied_shift_operators"] = ["workspace_scale_shift"]

    bundle_paths = _materialize_bundle(tmp_path, overrides={"environment": patch_environment})

    report = _run_bundle(bundle_paths)

    assert any(
        issue.issue_type == "E-R" and issue.rule_id == "deployment_shift_coverage"
        for issue in report.issues
    )


def test_invalid_spec_returns_empty_report():
    report = run_static_analysis(
        "missing_reward.yaml",
        "missing_constraint.yaml",
        "missing_policy.yaml",
        "missing_env.yaml",
    )

    assert isinstance(report, StaticReport)
    assert report.issues == []
    assert report.summary["validation_failed"] is True
