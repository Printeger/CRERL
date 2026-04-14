"""Phase 1 M1 module with canonical LLM-alpha placeholder and YAML compatibility.

This module intentionally provides only interface placeholders. The actual
algorithm must be implemented only after the PDF section, contract tests, and
traceability requirements are satisfied.
"""

from __future__ import annotations

from numbers import Real
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import yaml

from .cfg import CFG, CFGSchema
from .diag_report import (
    AmbiguityFlag,
    Constraint,
    Environment,
    NLInput,
    PolicyClass,
    RewardDAG,
    RewardTerm,
    SpecS,
    TrainingEnvDistribution,
)
from .errors import CREError, CREErrorCode, ERROR_CLASS_REGISTRY
from .llm_gateway import LLMGateway

__all__ = [
    "detect_and_escalate_ambiguities",
    "parse_nl_input",
    "parse_yaml_input",
    "run_symbolic_precheck",
]


def parse_nl_input(
    nl_input: NLInput,
    cfg: CFGSchema = CFG,
    llm_client: LLMGateway | None = None,
) -> tuple[SpecS, list[AmbiguityFlag]]:
    """Canonical Stage I parser placeholder.

    # CRE_v4 Eq.(N/A) Part II §2.1.1 p.25
    """

    raise NotImplementedError(
        "parse_nl_input() is the canonical LLM-alpha path and remains to be "
        "implemented; parse_yaml_input() is compatibility-only"
    )


def _raise_cre_error(error_code: str, message: str) -> None:
    error_cls = ERROR_CLASS_REGISTRY[error_code]
    raise error_cls(message)


def _load_yaml_mapping(spec_path: str, expected_spec_type: str) -> dict[str, Any]:
    path = Path(spec_path)
    if not path.exists():
        _raise_cre_error(
            CREErrorCode.SPEC_PARSE_FAILURE,
            f"{spec_path}: file does not exist",
        )

    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        _raise_cre_error(
            CREErrorCode.SPEC_PARSE_FAILURE,
            f"{spec_path}: failed to parse YAML: {exc}",
        )
    except OSError as exc:
        _raise_cre_error(
            CREErrorCode.SPEC_PARSE_FAILURE,
            f"{spec_path}: failed to read file: {exc}",
        )

    if not isinstance(payload, dict):
        _raise_cre_error(
            CREErrorCode.SPEC_PARSE_FAILURE,
            f"{spec_path}: top-level YAML object must be a mapping",
        )

    spec_type = payload.get("spec_type")
    if spec_type != expected_spec_type:
        _raise_cre_error(
            CREErrorCode.SPEC_PARSE_FAILURE,
            (
                f"{spec_path}.spec_type: expected {expected_spec_type!r}, "
                f"got {spec_type!r}"
            ),
        )
    return payload


def _require_mapping(value: object, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _raise_cre_error(
            CREErrorCode.SPEC_PARSE_FAILURE,
            f"{path}: expected dict, got {type(value).__name__}",
        )
    return value


def _require_list(value: object, path: str) -> list[Any]:
    if not isinstance(value, list):
        _raise_cre_error(
            CREErrorCode.SPEC_PARSE_FAILURE,
            f"{path}: expected list, got {type(value).__name__}",
        )
    return value


def _require_str(value: object, path: str, *, non_empty: bool = True) -> str:
    if not isinstance(value, str):
        _raise_cre_error(
            CREErrorCode.SPEC_PARSE_FAILURE,
            f"{path}: expected str, got {type(value).__name__}",
        )
    if non_empty and not value.strip():
        _raise_cre_error(
            CREErrorCode.SPEC_PARSE_FAILURE,
            f"{path}: must be a non-empty string",
        )
    return value


def _require_bool(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        _raise_cre_error(
            CREErrorCode.SPEC_PARSE_FAILURE,
            f"{path}: expected bool, got {type(value).__name__}",
        )
    return value


def _require_real(
    value: object,
    path: str,
    *,
    allow_none: bool = False,
) -> float | None:
    if value is None:
        if allow_none:
            return None
        _raise_cre_error(
            CREErrorCode.SPEC_PARSE_FAILURE,
            f"{path}: expected float, got null",
        )
    if isinstance(value, bool) or not isinstance(value, Real):
        _raise_cre_error(
            CREErrorCode.SPEC_PARSE_FAILURE,
            f"{path}: expected float, got {type(value).__name__}",
        )
    return float(value)


def _require_list_of_str_or_str(value: object, path: str) -> str | list[str]:
    if isinstance(value, str):
        if not value.strip():
            _raise_cre_error(
                CREErrorCode.SPEC_PARSE_FAILURE,
                f"{path}: string value must be non-empty",
            )
        return value

    items = _require_list(value, path)
    normalized: list[str] = []
    for index, item in enumerate(items):
        normalized.append(_require_str(item, f"{path}[{index}]"))
    return normalized


def _require_string_or_mapping(value: object, path: str) -> str | dict[str, Any]:
    if isinstance(value, str):
        return _require_str(value, path)
    if isinstance(value, dict):
        return value
    _raise_cre_error(
        CREErrorCode.SPEC_PARSE_FAILURE,
        f"{path}: expected str | dict, got {type(value).__name__}",
    )


def _build_indicator_predicate(source: str | dict[str, Any]) -> Callable[[Any, Any], int]:
    def _predicate(_state: Any, _action: Any) -> int:
        # CRE_v4 Eq.(N/A) Part II §2.1.1 p.25: the deterministic YAML adapter
        # preserves a callable slot for O_j while deferring symbolic execution.
        return 0

    _predicate.__name__ = "indicator_predicate"
    _predicate.__doc__ = str(source)
    return _predicate


def _parse_reward_spec(payload: dict[str, Any]) -> RewardDAG:
    _require_str(payload.get("spec_version"), "reward.spec_version")

    reward_terms = _require_list(payload.get("reward_terms"), "reward.reward_terms")
    if not reward_terms:
        _raise_cre_error(
            CREErrorCode.NULL_REWARD,
            "reward.reward_terms must contain at least one reward term",
        )

    reward_term_ids: set[str] = set()
    nodes: list[RewardTerm] = []
    for index, reward_term in enumerate(reward_terms):
        reward_term_path = f"reward.reward_terms[{index}]"
        reward_term_mapping = _require_mapping(reward_term, reward_term_path)
        term_id = _require_str(
            reward_term_mapping.get("term_id"),
            f"{reward_term_path}.term_id",
        )
        if term_id in reward_term_ids:
            _raise_cre_error(
                CREErrorCode.SPEC_PARSE_FAILURE,
                f"{reward_term_path}.term_id: duplicate term_id {term_id!r}",
            )
        reward_term_ids.add(term_id)
        _require_string_or_mapping(
            reward_term_mapping.get("term_expr"),
            f"{reward_term_path}.term_expr",
        )
        _require_real(
            reward_term_mapping.get("weight"),
            f"{reward_term_path}.weight",
        )
        _require_str(reward_term_mapping.get("unit"), f"{reward_term_path}.unit")
        clip_bounds = _require_mapping(
            reward_term_mapping.get("clip_bounds"),
            f"{reward_term_path}.clip_bounds",
        )
        clip_min = _require_real(
            clip_bounds.get("min"),
            f"{reward_term_path}.clip_bounds.min",
            allow_none=True,
        )
        clip_max = _require_real(
            clip_bounds.get("max"),
            f"{reward_term_path}.clip_bounds.max",
            allow_none=True,
        )
        if clip_min is not None and clip_max is not None and clip_min > clip_max:
            _raise_cre_error(
                CREErrorCode.SPEC_PARSE_FAILURE,
                f"{reward_term_path}.clip_bounds: min cannot be greater than max",
            )
        _require_bool(
            reward_term_mapping.get("shaping_flag"),
            f"{reward_term_path}.shaping_flag",
        )
        nodes.append(RewardTerm())

    dag_edges = _require_list(payload.get("dag_edges"), "reward.dag_edges")
    edges: list[tuple[str, str]] = []
    for index, edge in enumerate(dag_edges):
        edge_path = f"reward.dag_edges[{index}]"
        edge_mapping = _require_mapping(edge, edge_path)
        source = _require_str(edge_mapping.get("from"), f"{edge_path}.from")
        target = _require_str(edge_mapping.get("to"), f"{edge_path}.to")
        if source not in reward_term_ids:
            _raise_cre_error(
                CREErrorCode.SPEC_PARSE_FAILURE,
                f"{edge_path}.from: unknown reward term {source!r}",
            )
        if target not in reward_term_ids:
            _raise_cre_error(
                CREErrorCode.SPEC_PARSE_FAILURE,
                f"{edge_path}.to: unknown reward term {target!r}",
            )
        edges.append((source, target))

    return RewardDAG(nodes=nodes, edges=edges)


def _parse_constraint_spec(payload: dict[str, Any]) -> list[Constraint]:
    _require_str(payload.get("spec_version"), "constraint.spec_version")
    constraints_payload = _require_list(
        payload.get("constraints"),
        "constraint.constraints",
    )

    constraints: list[Constraint] = []
    constraint_ids: set[str] = set()
    for index, constraint_payload in enumerate(constraints_payload):
        constraint_path = f"constraint.constraints[{index}]"
        constraint_mapping = _require_mapping(constraint_payload, constraint_path)
        constraint_id = _require_str(
            constraint_mapping.get("constraint_id"),
            f"{constraint_path}.constraint_id",
        )
        if constraint_id in constraint_ids:
            _raise_cre_error(
                CREErrorCode.SPEC_PARSE_FAILURE,
                f"{constraint_path}.constraint_id: duplicate constraint_id {constraint_id!r}",
            )
        constraint_ids.add(constraint_id)
        predicate_source = _require_string_or_mapping(
            constraint_mapping.get("indicator_predicate"),
            f"{constraint_path}.indicator_predicate",
        )
        severity = _require_str(
            constraint_mapping.get("severity"),
            f"{constraint_path}.severity",
        )
        if severity not in {"hard", "soft", "info"}:
            _raise_cre_error(
                CREErrorCode.SPEC_PARSE_FAILURE,
                (
                    f"{constraint_path}.severity: expected one of "
                    "['hard', 'info', 'soft']"
                ),
            )
        temporal_scope = _require_str(
            constraint_mapping.get("temporal_scope"),
            f"{constraint_path}.temporal_scope",
        )
        if temporal_scope not in {"instantaneous", "episodic", "cumulative"}:
            _raise_cre_error(
                CREErrorCode.SPEC_PARSE_FAILURE,
                (
                    f"{constraint_path}.temporal_scope: expected one of "
                    "['cumulative', 'episodic', 'instantaneous']"
                ),
            )
        delta = _require_real(
            constraint_mapping.get("coverage_threshold_delta"),
            f"{constraint_path}.coverage_threshold_delta",
        )
        if delta is None or delta <= 0.0:
            _raise_cre_error(
                CREErrorCode.SPEC_PARSE_FAILURE,
                f"{constraint_path}.coverage_threshold_delta: must be > 0",
            )

        tolerance = _require_real(
            constraint_mapping.get("tolerance"),
            f"{constraint_path}.tolerance",
            allow_none=True,
        )
        penalty_weight = _require_real(
            constraint_mapping.get("penalty_weight"),
            f"{constraint_path}.penalty_weight",
            allow_none=True,
        )
        if severity == "soft":
            if tolerance is None:
                _raise_cre_error(
                    CREErrorCode.SPEC_PARSE_FAILURE,
                    f"{constraint_path}.tolerance: soft constraint requires a non-null value",
                )
            if penalty_weight is None:
                _raise_cre_error(
                    CREErrorCode.SPEC_PARSE_FAILURE,
                    f"{constraint_path}.penalty_weight: soft constraint requires a non-null value",
                )
        else:
            if tolerance is not None:
                _raise_cre_error(
                    CREErrorCode.SPEC_PARSE_FAILURE,
                    f"{constraint_path}.tolerance: hard/info constraints must set tolerance to null",
                )
            if penalty_weight is not None:
                _raise_cre_error(
                    CREErrorCode.SPEC_PARSE_FAILURE,
                    f"{constraint_path}.penalty_weight: hard/info constraints must set penalty_weight to null",
                )

        try:
            constraints.append(
                Constraint(
                    k_id=constraint_id,
                    predicate=_build_indicator_predicate(predicate_source),
                    sigma=severity,
                    scope=temporal_scope,
                    zeta=tolerance,
                    lam=penalty_weight,
                    delta=delta,
                )
            )
        except (TypeError, ValueError) as exc:
            _raise_cre_error(
                CREErrorCode.SPEC_PARSE_FAILURE,
                f"{constraint_path}: {exc}",
            )

    return constraints


def _parse_policy_spec(payload: dict[str, Any]) -> PolicyClass:
    _require_str(payload.get("spec_version"), "policy.spec_version")
    action_space = _require_mapping(payload.get("action_space"), "policy.action_space")
    _require_list_of_str_or_str(
        action_space.get("tensor_key"),
        "policy.action_space.tensor_key",
    )
    action_shape = _require_list(action_space.get("shape"), "policy.action_space.shape")
    if not action_shape:
        _raise_cre_error(
            CREErrorCode.SPEC_PARSE_FAILURE,
            "policy.action_space.shape: must contain at least one dimension",
        )
    for index, dimension in enumerate(action_shape):
        if not isinstance(dimension, (int, str)) or isinstance(dimension, bool):
            _raise_cre_error(
                CREErrorCode.SPEC_PARSE_FAILURE,
                (
                    f"policy.action_space.shape[{index}]: expected int | str, "
                    f"got {type(dimension).__name__}"
                ),
            )
    _require_str(action_space.get("dtype"), "policy.action_space.dtype")
    bounds = _require_mapping(action_space.get("bounds"), "policy.action_space.bounds")
    bound_min = _require_list(bounds.get("min"), "policy.action_space.bounds.min")
    bound_max = _require_list(bounds.get("max"), "policy.action_space.bounds.max")
    if len(bound_min) != len(bound_max):
        _raise_cre_error(
            CREErrorCode.SPEC_PARSE_FAILURE,
            "policy.action_space.bounds: min and max must have the same number of entries",
        )
    for index, value in enumerate(bound_min):
        _require_real(value, f"policy.action_space.bounds.min[{index}]")
    for index, value in enumerate(bound_max):
        _require_real(value, f"policy.action_space.bounds.max[{index}]")
    if len(action_shape) == 1 and isinstance(action_shape[0], int):
        if len(bound_min) != action_shape[0]:
            _raise_cre_error(
                CREErrorCode.SPEC_PARSE_FAILURE,
                (
                    "policy.action_space.bounds: bound length must match "
                    "action_space.shape[0]"
                ),
            )
    _require_str(action_space.get("unit"), "policy.action_space.unit")

    observation_space = _require_list(
        payload.get("observation_space"),
        "policy.observation_space",
    )
    if not observation_space:
        _raise_cre_error(
            CREErrorCode.SPEC_PARSE_FAILURE,
            "policy.observation_space: must contain at least one observation entry",
        )
    for index, observation_payload in enumerate(observation_space):
        observation_path = f"policy.observation_space[{index}]"
        observation_mapping = _require_mapping(observation_payload, observation_path)
        _require_list_of_str_or_str(observation_mapping.get("key"), f"{observation_path}.key")
        observation_shape = _require_list(
            observation_mapping.get("shape"),
            f"{observation_path}.shape",
        )
        if not observation_shape:
            _raise_cre_error(
                CREErrorCode.SPEC_PARSE_FAILURE,
                f"{observation_path}.shape: must contain at least one dimension",
            )
        for shape_index, dimension in enumerate(observation_shape):
            if not isinstance(dimension, (int, str)) or isinstance(dimension, bool):
                _raise_cre_error(
                    CREErrorCode.SPEC_PARSE_FAILURE,
                    (
                        f"{observation_path}.shape[{shape_index}]: expected int | str, "
                        f"got {type(dimension).__name__}"
                    ),
                )
        _require_str(observation_mapping.get("dtype"), f"{observation_path}.dtype")
        _require_str(observation_mapping.get("unit"), f"{observation_path}.unit")

    execution_frequency_hz = _require_real(
        payload.get("execution_frequency_hz"),
        "policy.execution_frequency_hz",
    )
    if execution_frequency_hz is None or execution_frequency_hz <= 0.0:
        _raise_cre_error(
            CREErrorCode.SPEC_PARSE_FAILURE,
            "policy.execution_frequency_hz: must be > 0",
        )

    return PolicyClass()


def _parse_environment_spec(
    payload: dict[str, Any],
) -> tuple[TrainingEnvDistribution, list[Environment]]:
    _require_str(payload.get("spec_version"), "environment.spec_version")

    e_tr = _require_mapping(payload.get("E_tr"), "environment.E_tr")
    _require_str(e_tr.get("distribution_id"), "environment.E_tr.distribution_id")
    _require_str(e_tr.get("description"), "environment.E_tr.description")
    nominal_family = _require_str(
        e_tr.get("nominal_family"),
        "environment.E_tr.nominal_family",
    )
    training_scene_families = _require_list(
        e_tr.get("scene_families"),
        "environment.E_tr.scene_families",
    )
    if nominal_family not in {
        _require_str(family, f"environment.E_tr.scene_families[{index}]")
        for index, family in enumerate(training_scene_families)
    }:
        _raise_cre_error(
            CREErrorCode.SPEC_PARSE_FAILURE,
            "environment.E_tr.nominal_family: must be included in E_tr.scene_families",
        )
    for index, operator in enumerate(
        _require_list(e_tr.get("shift_operators"), "environment.E_tr.shift_operators")
    ):
        _require_str(operator, f"environment.E_tr.shift_operators[{index}]")
    for index, seed in enumerate(
        _require_list(e_tr.get("generator_seeds"), "environment.E_tr.generator_seeds")
    ):
        if not isinstance(seed, int) or isinstance(seed, bool):
            _raise_cre_error(
                CREErrorCode.SPEC_PARSE_FAILURE,
                f"environment.E_tr.generator_seeds[{index}]: expected int, got {type(seed).__name__}",
            )
    for index, ref in enumerate(
        _require_list(e_tr.get("env_cfg_refs"), "environment.E_tr.env_cfg_refs")
    ):
        _require_str(ref, f"environment.E_tr.env_cfg_refs[{index}]")

    e_dep = _require_mapping(payload.get("E_dep"), "environment.E_dep")
    nominal_env = _require_str(e_dep.get("nominal_env"), "environment.E_dep.nominal_env")
    deployment_envs_payload = _require_list(
        e_dep.get("deployment_envs"),
        "environment.E_dep.deployment_envs",
    )
    if not deployment_envs_payload:
        _raise_cre_error(
            CREErrorCode.EMPTY_ENV_SET,
            "environment.E_dep.deployment_envs must contain at least one deployment environment",
        )
    deployment_envs: list[Environment] = []
    env_ids: set[str] = set()
    scene_families: set[str] = set()
    for index, environment_payload in enumerate(deployment_envs_payload):
        environment_path = f"environment.E_dep.deployment_envs[{index}]"
        environment_mapping = _require_mapping(environment_payload, environment_path)
        env_id = _require_str(environment_mapping.get("env_id"), f"{environment_path}.env_id")
        env_ids.add(env_id)
        scene_family = _require_str(
            environment_mapping.get("scene_family"),
            f"{environment_path}.scene_family",
        )
        scene_families.add(scene_family)
        seed = environment_mapping.get("generator_seed")
        if not isinstance(seed, int) or isinstance(seed, bool):
            _raise_cre_error(
                CREErrorCode.SPEC_PARSE_FAILURE,
                (
                    f"{environment_path}.generator_seed: expected int, got "
                    f"{type(seed).__name__}"
                ),
            )
        _require_str(environment_mapping.get("env_cfg_ref"), f"{environment_path}.env_cfg_ref")
        applied_shift_operators = _require_list(
            environment_mapping.get("applied_shift_operators"),
            f"{environment_path}.applied_shift_operators",
        )
        for operator_index, operator in enumerate(applied_shift_operators):
            _require_str(
                operator,
                f"{environment_path}.applied_shift_operators[{operator_index}]",
            )
        deployment_envs.append(Environment())

    if nominal_env not in env_ids and nominal_env not in scene_families:
        _raise_cre_error(
            CREErrorCode.SPEC_PARSE_FAILURE,
            (
                "environment.E_dep.nominal_env: must match a deployment env_id "
                "or scene_family"
            ),
        )

    for index, family in enumerate(
        _require_list(payload.get("scene_families"), "environment.scene_families")
    ):
        _require_str(family, f"environment.scene_families[{index}]")

    shift_operators = _require_list(
        payload.get("shift_operators"),
        "environment.shift_operators",
    )
    for index, operator_payload in enumerate(shift_operators):
        operator_path = f"environment.shift_operators[{index}]"
        operator_mapping = _require_mapping(operator_payload, operator_path)
        _require_str(operator_mapping.get("shift_id"), f"{operator_path}.shift_id")
        _require_str(operator_mapping.get("description"), f"{operator_path}.description")
        inferred_from = _require_list(
            operator_mapping.get("inferred_from"),
            f"{operator_path}.inferred_from",
        )
        for ref_index, ref in enumerate(inferred_from):
            _require_str(ref, f"{operator_path}.inferred_from[{ref_index}]")

    generator_seed_rows = _require_list(
        payload.get("generator_seeds"),
        "environment.generator_seeds",
    )
    for index, generator_seed_payload in enumerate(generator_seed_rows):
        seed_path = f"environment.generator_seeds[{index}]"
        generator_seed_mapping = _require_mapping(generator_seed_payload, seed_path)
        _require_str(generator_seed_mapping.get("cfg_name"), f"{seed_path}.cfg_name")
        seed_value = generator_seed_mapping.get("seed")
        if not isinstance(seed_value, int) or isinstance(seed_value, bool):
            _raise_cre_error(
                CREErrorCode.SPEC_PARSE_FAILURE,
                f"{seed_path}.seed: expected int, got {type(seed_value).__name__}",
            )

    for index, ref in enumerate(
        _require_list(payload.get("env_cfg_refs"), "environment.env_cfg_refs")
    ):
        _require_str(ref, f"environment.env_cfg_refs[{index}]")

    return TrainingEnvDistribution(), deployment_envs


def parse_yaml_input(
    reward_spec_path: str,
    constraint_spec_path: str,
    policy_spec_path: str,
    env_spec_path: str,
) -> tuple[SpecS, list[AmbiguityFlag]]:
    """Parse four structured YAML spec files into the canonical SpecS object.

    # CRE_v4 Eq.(N/A) Part II §2.1.1 p.25
    # D-I20: this is a deterministic YAML compatibility adapter and cannot
    # stand in for the canonical `parse_nl_input()` / LLM-alpha runtime chain.
    """
    reward_payload = _load_yaml_mapping(reward_spec_path, "reward")
    constraint_payload = _load_yaml_mapping(constraint_spec_path, "constraint")
    policy_payload = _load_yaml_mapping(policy_spec_path, "policy")
    environment_payload = _load_yaml_mapping(env_spec_path, "environment")

    reward_dag = _parse_reward_spec(reward_payload)
    constraints = _parse_constraint_spec(constraint_payload)
    policy = _parse_policy_spec(policy_payload)
    training_env_distribution, deployment_envs = _parse_environment_spec(
        environment_payload
    )

    try:
        spec = SpecS(
            spec_id=str(uuid4()),
            E_tr=training_env_distribution,
            E_dep=deployment_envs,
            R=reward_dag,
            C=constraints,
            Pi=policy,
            version=0,
        )
    except (TypeError, ValueError) as exc:
        if isinstance(exc, CREError):
            raise
        _raise_cre_error(
            CREErrorCode.SPEC_PARSE_FAILURE,
            f"SpecS construction failed: {exc}",
        )

    return spec, []


def detect_and_escalate_ambiguities(
    spec: SpecS,
    ambiguity_flags: list[AmbiguityFlag],
    cfg: CFGSchema = CFG,
    llm_client: LLMGateway | None = None,
) -> list[AmbiguityFlag]:
    """Detect canonical ambiguity flags from an already constructed SpecS.

    # CRE_v4 Eq.(N/A) Part II §2.1.2 p.26
    """

    raise NotImplementedError(
        "detect_and_escalate_ambiguities() contract scaffold only"
    )


def run_symbolic_precheck(spec: SpecS) -> list[str]:
    """Run the symbolic pre-check over a canonical SpecS instance.

    # CRE_v4 Eq.(N/A) Part II §2.1.3 pp.26-27
    """

    raise NotImplementedError("run_symbolic_precheck() contract scaffold only")
