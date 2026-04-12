import copy
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analyzers.spec_validator import validate_spec_file, validate_spec_set


SPEC_DIR = ROOT / "cfg" / "spec_cfg"


@pytest.fixture
def real_spec_paths():
    return {
        "reward": SPEC_DIR / "reward_spec_v1.yaml",
        "constraint": SPEC_DIR / "constraint_spec_v1.yaml",
        "policy": SPEC_DIR / "policy_spec_v1.yaml",
        "environment": SPEC_DIR / "env_spec_v1.yaml",
    }


def _load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _write_yaml(path: Path, payload) -> None:
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=False)


def _materialize_bundle(tmp_path: Path, real_spec_paths, overrides=None):
    overrides = overrides or {}
    bundle_paths = {}
    bundle_data = {}
    filename_map = {
        "reward": "reward_spec_v1.yaml",
        "constraint": "constraint_spec_v1.yaml",
        "policy": "policy_spec_v1.yaml",
        "environment": "env_spec_v1.yaml",
    }
    for spec_name, source_path in real_spec_paths.items():
        data = copy.deepcopy(_load_yaml(source_path))
        if spec_name in overrides:
            overrides[spec_name](data)
        target_path = tmp_path / filename_map[spec_name]
        _write_yaml(target_path, data)
        bundle_paths[spec_name] = target_path
        bundle_data[spec_name] = data
    return bundle_paths, bundle_data


def _validate_bundle(bundle_paths):
    return validate_spec_set(
        str(bundle_paths["reward"]),
        str(bundle_paths["constraint"]),
        str(bundle_paths["policy"]),
        str(bundle_paths["environment"]),
    )


def test_valid_spec_set(real_spec_paths):
    result = validate_spec_set(
        str(real_spec_paths["reward"]),
        str(real_spec_paths["constraint"]),
        str(real_spec_paths["policy"]),
        str(real_spec_paths["environment"]),
    )

    assert result.valid is True
    assert result.errors == []


def test_reward_missing_field(tmp_path, real_spec_paths):
    reward_data = _load_yaml(real_spec_paths["reward"])
    reward_data.pop("reward_terms")
    reward_path = tmp_path / "reward_spec_v1.yaml"
    _write_yaml(reward_path, reward_data)

    result = validate_spec_file(str(reward_path))

    assert result.valid is False
    assert result.errors


def test_reward_clip_bounds_inverted(tmp_path, real_spec_paths):
    reward_data = _load_yaml(real_spec_paths["reward"])
    reward_data["reward_terms"][0]["clip_bounds"]["min"] = 2.0
    reward_data["reward_terms"][0]["clip_bounds"]["max"] = 1.0
    reward_path = tmp_path / "reward_spec_v1.yaml"
    _write_yaml(reward_path, reward_data)

    result = validate_spec_file(str(reward_path))

    assert result.valid is False
    assert result.errors


def test_constraint_bad_severity(tmp_path, real_spec_paths):
    constraint_data = _load_yaml(real_spec_paths["constraint"])
    constraint_data["constraints"][0]["severity"] = "critical"
    constraint_path = tmp_path / "constraint_spec_v1.yaml"
    _write_yaml(constraint_path, constraint_data)

    result = validate_spec_file(str(constraint_path))

    assert result.valid is False
    assert result.errors


def test_constraint_soft_null_tolerance(tmp_path, real_spec_paths):
    constraint_data = _load_yaml(real_spec_paths["constraint"])
    constraint_data["constraints"][1]["tolerance"] = None
    constraint_path = tmp_path / "constraint_spec_v1.yaml"
    _write_yaml(constraint_path, constraint_data)

    result = validate_spec_file(str(constraint_path))

    assert result.valid is False
    assert result.errors


def test_constraint_hard_nonnull_tolerance(tmp_path, real_spec_paths):
    constraint_data = _load_yaml(real_spec_paths["constraint"])
    constraint_data["constraints"][0]["tolerance"] = 0.5
    constraint_path = tmp_path / "constraint_spec_v1.yaml"
    _write_yaml(constraint_path, constraint_data)

    result = validate_spec_file(str(constraint_path))

    assert result.valid is False
    assert result.errors


def test_version_mismatch(tmp_path, real_spec_paths):
    bundle_paths, _ = _materialize_bundle(
        tmp_path,
        real_spec_paths,
        overrides={"reward": lambda data: data.__setitem__("spec_version", "2.0")},
    )

    result = _validate_bundle(bundle_paths)

    assert result.valid is False
    assert any("spec_version mismatch" in error for error in result.errors)


def test_dag_dangling_edge(tmp_path, real_spec_paths):
    def patch_reward(data):
        data["dag_edges"][0]["from"] = "undefined_reward_term"

    bundle_paths, _ = _materialize_bundle(
        tmp_path,
        real_spec_paths,
        overrides={"reward": patch_reward},
    )

    result = _validate_bundle(bundle_paths)

    assert result.valid is False
    assert any("undefined term_id" in error for error in result.errors)


def test_dag_cycle(tmp_path, real_spec_paths):
    def patch_reward(data):
        data["dag_edges"] = [
            {"from": "reward_progress", "to": "reward_safety_static"},
            {"from": "reward_safety_static", "to": "reward_progress"},
        ]

    bundle_paths, _ = _materialize_bundle(
        tmp_path,
        real_spec_paths,
        overrides={"reward": patch_reward},
    )

    result = _validate_bundle(bundle_paths)

    assert result.valid is False
    assert any("cycle" in error for error in result.errors)


def test_env_undefined_shift(tmp_path, real_spec_paths):
    def patch_environment(data):
        data["E_dep"]["deployment_envs"][0]["applied_shift_operators"] = ["missing_shift_id"]

    bundle_paths, _ = _materialize_bundle(
        tmp_path,
        real_spec_paths,
        overrides={"environment": patch_environment},
    )

    result = _validate_bundle(bundle_paths)

    assert result.valid is False
    assert result.errors


def test_shaping_flag_no_edge_warning(tmp_path, real_spec_paths):
    def patch_reward(data):
        data["reward_terms"][-1]["shaping_flag"] = True

    bundle_paths, _ = _materialize_bundle(
        tmp_path,
        real_spec_paths,
        overrides={"reward": patch_reward},
    )

    result = _validate_bundle(bundle_paths)

    assert result.valid is True
    assert result.errors == []
    assert result.warnings
