"""Contract tests for the CRE_v4 Phase 1 M1 functions."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import sys
from uuid import UUID

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analyzers.diag_report import SpecS  # noqa: E402
from analyzers.errors import CREErrorCode, ERROR_CLASS_REGISTRY  # noqa: E402
from analyzers.m1 import (  # noqa: E402
    detect_and_escalate_ambiguities,
    parse_yaml_input,
    run_symbolic_precheck,
)


def _write_yaml(tmp_path: Path, filename: str, payload: dict) -> str:
    path = tmp_path / filename
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return str(path)


def _valid_reward_spec() -> dict:
    return {
        "spec_type": "reward",
        "spec_version": "1.0",
        "reward_terms": [
            {
                "term_id": "reward_progress",
                "term_expr": "goal_distance_t_minus_1 - goal_distance_t",
                "weight": 1.0,
                "unit": "m",
                "clip_bounds": {"min": -1.0, "max": 1.0},
                "shaping_flag": True,
            }
        ],
        "dag_edges": [],
    }


def _valid_constraint_spec() -> dict:
    return {
        "spec_type": "constraint",
        "spec_version": "1.0",
        "constraints": [
            {
                "constraint_id": "collision_avoidance",
                "indicator_predicate": "min_obstacle_distance_m <= 0.0 OR done_type == 2",
                "severity": "hard",
                "temporal_scope": "instantaneous",
                "coverage_threshold_delta": 0.9,
                "tolerance": None,
                "penalty_weight": None,
            }
        ],
    }


def _valid_policy_spec() -> dict:
    return {
        "spec_type": "policy",
        "spec_version": "1.0",
        "action_space": {
            "tensor_key": ["agents", "action"],
            "shape": [3],
            "dtype": "float32",
            "bounds": {
                "min": [-2.0, -2.0, -2.0],
                "max": [2.0, 2.0, 2.0],
            },
            "unit": "m/s",
        },
        "observation_space": [
            {
                "key": ["agents", "observation", "state"],
                "shape": ["state_dim"],
                "dtype": "float32",
                "unit": "mixed_state_vector",
            }
        ],
        "execution_frequency_hz": 62.5,
    }


def _valid_environment_spec() -> dict:
    return {
        "spec_type": "environment",
        "spec_version": "1.0",
        "E_tr": {
            "distribution_id": "train_distribution_v1",
            "description": "Training distribution",
            "nominal_family": "nominal",
            "scene_families": ["nominal"],
            "shift_operators": [],
            "generator_seeds": [1001],
            "env_cfg_refs": ["cfg/env_cfg/scene_cfg_nominal.yaml"],
        },
        "E_dep": {
            "nominal_env": "e0_nominal",
            "deployment_envs": [
                {
                    "env_id": "e0_nominal",
                    "scene_family": "nominal",
                    "generator_seed": 1001,
                    "env_cfg_ref": "cfg/env_cfg/scene_cfg_nominal.yaml",
                    "applied_shift_operators": [],
                },
                {
                    "env_id": "e1_shifted",
                    "scene_family": "shifted",
                    "generator_seed": 2001,
                    "env_cfg_ref": "cfg/env_cfg/scene_cfg_shifted.yaml",
                    "applied_shift_operators": ["workspace_scale_shift"],
                },
            ],
        },
        "scene_families": ["nominal", "shifted"],
        "shift_operators": [
            {
                "shift_id": "workspace_scale_shift",
                "description": "Scale workspace in deployment.",
                "inferred_from": ["cfg/env_cfg/scene_cfg_shifted.yaml"],
            }
        ],
        "generator_seeds": [
            {"cfg_name": "scene_cfg_nominal", "seed": 1001},
            {"cfg_name": "scene_cfg_shifted", "seed": 2001},
        ],
        "env_cfg_refs": [
            "cfg/env_cfg/scene_cfg_nominal.yaml",
            "cfg/env_cfg/scene_cfg_shifted.yaml",
        ],
    }


def _write_valid_spec_bundle(tmp_path: Path) -> tuple[str, str, str, str]:
    return (
        _write_yaml(tmp_path, "reward.yaml", _valid_reward_spec()),
        _write_yaml(tmp_path, "constraint.yaml", _valid_constraint_spec()),
        _write_yaml(tmp_path, "policy.yaml", _valid_policy_spec()),
        _write_yaml(tmp_path, "environment.yaml", _valid_environment_spec()),
    )


def test_parse_round_trip_valid_yaml_bundle(tmp_path: Path) -> None:
    """T1/T5/T6 equivalent for the deterministic YAML adapter."""

    reward_path, constraint_path, policy_path, env_path = _write_valid_spec_bundle(
        tmp_path
    )

    spec, flags = parse_yaml_input(
        reward_path,
        constraint_path,
        policy_path,
        env_path,
    )

    assert isinstance(spec, SpecS)
    assert len(spec.R.nodes) == 1
    assert len(spec.C) == 1
    assert spec.C[0].sigma == "hard"
    assert len(spec.E_dep) == 2
    assert flags == []
    assert spec.version == 0
    assert UUID(spec.spec_id)
    with pytest.raises(FrozenInstanceError):
        spec.version = 1


def test_parse_missing_required_reward_weight_raises_spec_parse_failure(
    tmp_path: Path,
) -> None:
    """Structured-YAML equivalent of an underspecified reward description."""

    reward_spec = _valid_reward_spec()
    del reward_spec["reward_terms"][0]["weight"]
    reward_path = _write_yaml(tmp_path, "reward.yaml", reward_spec)
    constraint_path = _write_yaml(tmp_path, "constraint.yaml", _valid_constraint_spec())
    policy_path = _write_yaml(tmp_path, "policy.yaml", _valid_policy_spec())
    env_path = _write_yaml(tmp_path, "environment.yaml", _valid_environment_spec())

    error_cls = ERROR_CLASS_REGISTRY[CREErrorCode.SPEC_PARSE_FAILURE]
    with pytest.raises(error_cls, match="reward_terms\\[0\\]\\.weight"):
        parse_yaml_input(
            reward_path,
            constraint_path,
            policy_path,
            env_path,
        )


def test_parse_empty_reward_terms_raises_null_reward(tmp_path: Path) -> None:
    """NULL_REWARD maps to an empty structured reward DAG."""

    reward_spec = _valid_reward_spec()
    reward_spec["reward_terms"] = []
    reward_path = _write_yaml(tmp_path, "reward.yaml", reward_spec)
    constraint_path = _write_yaml(tmp_path, "constraint.yaml", _valid_constraint_spec())
    policy_path = _write_yaml(tmp_path, "policy.yaml", _valid_policy_spec())
    env_path = _write_yaml(tmp_path, "environment.yaml", _valid_environment_spec())

    error_cls = ERROR_CLASS_REGISTRY[CREErrorCode.NULL_REWARD]
    with pytest.raises(error_cls, match="reward_terms"):
        parse_yaml_input(
            reward_path,
            constraint_path,
            policy_path,
            env_path,
        )


def test_parse_empty_deployment_envs_raises_empty_env_set(tmp_path: Path) -> None:
    """EMPTY_ENV_SET requires at least the nominal deployment environment e0."""

    env_spec = _valid_environment_spec()
    env_spec["E_dep"]["deployment_envs"] = []

    reward_path = _write_yaml(tmp_path, "reward.yaml", _valid_reward_spec())
    constraint_path = _write_yaml(tmp_path, "constraint.yaml", _valid_constraint_spec())
    policy_path = _write_yaml(tmp_path, "policy.yaml", _valid_policy_spec())
    env_path = _write_yaml(tmp_path, "environment.yaml", env_spec)

    error_cls = ERROR_CLASS_REGISTRY[CREErrorCode.EMPTY_ENV_SET]
    with pytest.raises(error_cls, match="deployment_envs"):
        parse_yaml_input(
            reward_path,
            constraint_path,
            policy_path,
            env_path,
        )


@pytest.mark.xfail(
    reason="M1.detect_and_escalate_ambiguities() is not part of the current task",
    strict=False,
)
def test_escalate_contract_placeholder() -> None:
    """Placeholder for TRACEABILITY.md Part B line 31."""

    assert callable(detect_and_escalate_ambiguities)
    pytest.fail(
        "TODO: transcribe CRE_v4 Part II §2.1.2 p.26 Test Standards into "
        "test_escalate_* contract assertions"
    )


@pytest.mark.xfail(
    reason="M1.run_symbolic_precheck() is not part of the current task",
    strict=False,
)
def test_precheck_contract_placeholder() -> None:
    """Placeholder for TRACEABILITY.md Part B line 32."""

    assert callable(run_symbolic_precheck)
    pytest.fail(
        "TODO: transcribe CRE_v4 Part II §2.1.3 pp.26-27 Test Standards into "
        "test_precheck_* contract assertions"
    )
