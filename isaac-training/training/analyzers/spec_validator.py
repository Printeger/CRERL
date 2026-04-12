from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


SPEC_TYPES = {"reward", "constraint", "policy", "environment"}
CONSTRAINT_SEVERITIES = {"hard", "soft", "info"}
TEMPORAL_SCOPES = {"instantaneous", "episodic", "cumulative"}


def _scalar_schema(*types: str, enum: list[str] | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {"kind": "scalar", "types": list(types)}
    if enum is not None:
        schema["enum"] = enum
    return schema


STRING_OR_DICT_SCHEMA = {
    "any_of": [
        {"kind": "scalar", "types": ["str"]},
        {"kind": "dict"},
    ]
}

STRING_OR_PATH_SCHEMA = {
    "any_of": [
        {"kind": "scalar", "types": ["str"]},
        {
            "kind": "list",
            "item": {"kind": "scalar", "types": ["str"]},
        },
    ]
}

SHAPE_ITEM_SCHEMA = {
    "any_of": [
        {"kind": "scalar", "types": ["int"]},
        {"kind": "scalar", "types": ["str"]},
    ]
}

NUMERIC_OR_NULL_SCHEMA = _scalar_schema("float", "null")

REWARD_SPEC_SCHEMA = {
    "kind": "dict",
    "required": {
        "spec_type": {"kind": "literal", "value": "reward"},
        "spec_version": _scalar_schema("str"),
        "reward_terms": {
            "kind": "list",
            "item": {
                "kind": "dict",
                "required": {
                    "term_id": _scalar_schema("str"),
                    "term_expr": STRING_OR_DICT_SCHEMA,
                    "weight": _scalar_schema("float"),
                    "unit": _scalar_schema("str"),
                    "clip_bounds": {
                        "kind": "dict",
                        "required": {
                            "min": NUMERIC_OR_NULL_SCHEMA,
                            "max": NUMERIC_OR_NULL_SCHEMA,
                        },
                    },
                    "shaping_flag": _scalar_schema("bool"),
                },
            },
        },
        "dag_edges": {
            "kind": "list",
            "item": {
                "kind": "dict",
                "required": {
                    "from": _scalar_schema("str"),
                    "to": _scalar_schema("str"),
                },
            },
        },
    },
}

CONSTRAINT_SPEC_SCHEMA = {
    "kind": "dict",
    "required": {
        "spec_type": {"kind": "literal", "value": "constraint"},
        "spec_version": _scalar_schema("str"),
        "constraints": {
            "kind": "list",
            "item": {
                "kind": "dict",
                "required": {
                    "constraint_id": _scalar_schema("str"),
                    "indicator_predicate": STRING_OR_DICT_SCHEMA,
                    "severity": _scalar_schema(
                        "str",
                        enum=sorted(CONSTRAINT_SEVERITIES),
                    ),
                    "temporal_scope": _scalar_schema(
                        "str",
                        enum=sorted(TEMPORAL_SCOPES),
                    ),
                    "coverage_threshold_delta": _scalar_schema("float"),
                    "tolerance": NUMERIC_OR_NULL_SCHEMA,
                    "penalty_weight": NUMERIC_OR_NULL_SCHEMA,
                },
            },
        },
    },
}

POLICY_SPEC_SCHEMA = {
    "kind": "dict",
    "required": {
        "spec_type": {"kind": "literal", "value": "policy"},
        "spec_version": _scalar_schema("str"),
        "action_space": {
            "kind": "dict",
            "required": {
                "tensor_key": STRING_OR_PATH_SCHEMA,
                "shape": {
                    "kind": "list",
                    "item": SHAPE_ITEM_SCHEMA,
                },
                "dtype": _scalar_schema("str"),
                "bounds": {
                    "kind": "dict",
                    "required": {
                        "min": {
                            "kind": "list",
                            "item": _scalar_schema("float"),
                        },
                        "max": {
                            "kind": "list",
                            "item": _scalar_schema("float"),
                        },
                    },
                },
                "unit": _scalar_schema("str"),
            },
        },
        "observation_space": {
            "kind": "list",
            "item": {
                "kind": "dict",
                "required": {
                    "key": STRING_OR_PATH_SCHEMA,
                    "shape": {
                        "kind": "list",
                        "item": SHAPE_ITEM_SCHEMA,
                    },
                    "dtype": _scalar_schema("str"),
                    "unit": _scalar_schema("str"),
                },
            },
        },
        "execution_frequency_hz": _scalar_schema("float"),
    },
}

ENVIRONMENT_SPEC_SCHEMA = {
    "kind": "dict",
    "required": {
        "spec_type": {"kind": "literal", "value": "environment"},
        "spec_version": _scalar_schema("str"),
        "E_tr": {
            "kind": "dict",
            "required": {
                "distribution_id": _scalar_schema("str"),
                "description": _scalar_schema("str"),
                "nominal_family": _scalar_schema("str"),
                "scene_families": {
                    "kind": "list",
                    "item": _scalar_schema("str"),
                },
                "shift_operators": {
                    "kind": "list",
                    "item": _scalar_schema("str"),
                },
                "generator_seeds": {
                    "kind": "list",
                    "item": _scalar_schema("int"),
                },
                "env_cfg_refs": {
                    "kind": "list",
                    "item": _scalar_schema("str"),
                },
            },
        },
        "E_dep": {
            "kind": "dict",
            "required": {
                "nominal_env": _scalar_schema("str"),
                "deployment_envs": {
                    "kind": "list",
                    "item": {
                        "kind": "dict",
                        "required": {
                            "env_id": _scalar_schema("str"),
                            "scene_family": _scalar_schema("str"),
                            "generator_seed": _scalar_schema("int"),
                            "env_cfg_ref": _scalar_schema("str"),
                            "applied_shift_operators": {
                                "kind": "list",
                                "item": _scalar_schema("str"),
                            },
                        },
                    },
                },
            },
        },
        "scene_families": {
            "kind": "list",
            "item": _scalar_schema("str"),
        },
        "shift_operators": {
            "kind": "list",
            "item": {
                "kind": "dict",
                "required": {
                    "shift_id": _scalar_schema("str"),
                    "description": _scalar_schema("str"),
                    "inferred_from": {
                        "kind": "list",
                        "item": _scalar_schema("str"),
                    },
                },
            },
        },
        "generator_seeds": {
            "kind": "list",
            "item": {
                "kind": "dict",
                "required": {
                    "cfg_name": _scalar_schema("str"),
                    "seed": _scalar_schema("int"),
                },
            },
        },
        "env_cfg_refs": {
            "kind": "list",
            "item": _scalar_schema("str"),
        },
    },
}

SPEC_SCHEMAS = {
    "reward": REWARD_SPEC_SCHEMA,
    "constraint": CONSTRAINT_SPEC_SCHEMA,
    "policy": POLICY_SPEC_SCHEMA,
    "environment": ENVIRONMENT_SPEC_SCHEMA,
}


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _merge_results(*results: ValidationResult) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    for result in results:
        errors.extend(result.errors)
        warnings.extend(result.warnings)
    return ValidationResult(valid=not errors, errors=errors, warnings=warnings)


def _matches_type(value: Any, expected_type: str) -> bool:
    if expected_type == "str":
        return isinstance(value, str)
    if expected_type == "bool":
        return isinstance(value, bool)
    if expected_type == "dict":
        return isinstance(value, dict)
    if expected_type == "list":
        return isinstance(value, list)
    if expected_type == "null":
        return value is None
    if expected_type == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "float":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    raise ValueError(f"Unsupported schema type: {expected_type}")


def _format_type_names(type_names: list[str]) -> str:
    return " | ".join(type_names)


def _validate_schema(
    value: Any,
    schema: dict[str, Any],
    path: str,
    errors: list[str],
) -> None:
    if "any_of" in schema:
        option_errors: list[list[str]] = []
        for candidate in schema["any_of"]:
            candidate_errors: list[str] = []
            _validate_schema(value, candidate, path, candidate_errors)
            if not candidate_errors:
                return
            option_errors.append(candidate_errors)
        expected = []
        for candidate in schema["any_of"]:
            kind = candidate.get("kind")
            if kind == "scalar":
                expected.append(_format_type_names(candidate["types"]))
            elif kind == "dict":
                expected.append("dict")
            elif kind == "list":
                expected.append("list")
            else:
                expected.append(kind or "unknown")
        errors.append(f"{path}: expected one of {', '.join(expected)}")
        return

    kind = schema["kind"]
    if kind == "literal":
        if value != schema["value"]:
            errors.append(f"{path}: expected literal {schema['value']!r}, got {value!r}")
        return

    if kind == "dict":
        if not isinstance(value, dict):
            errors.append(f"{path}: expected dict, got {type(value).__name__}")
            return
        required = schema.get("required", {})
        optional = schema.get("optional", {})
        for field_name, field_schema in required.items():
            if field_name not in value:
                errors.append(f"{path}: missing required field '{field_name}'")
                continue
            _validate_schema(value[field_name], field_schema, f"{path}.{field_name}", errors)
        for field_name, field_schema in optional.items():
            if field_name in value:
                _validate_schema(value[field_name], field_schema, f"{path}.{field_name}", errors)
        return

    if kind == "list":
        if not isinstance(value, list):
            errors.append(f"{path}: expected list, got {type(value).__name__}")
            return
        item_schema = schema.get("item")
        if item_schema is None:
            return
        for index, item in enumerate(value):
            _validate_schema(item, item_schema, f"{path}[{index}]", errors)
        return

    if kind == "scalar":
        expected_types = schema["types"]
        if not any(_matches_type(value, expected_type) for expected_type in expected_types):
            errors.append(
                f"{path}: expected {_format_type_names(expected_types)}, got {type(value).__name__}"
            )
            return
        allowed_values = schema.get("enum")
        if allowed_values is not None and value not in allowed_values:
            errors.append(f"{path}: expected one of {allowed_values}, got {value!r}")
        return

    errors.append(f"{path}: unknown schema kind {kind!r}")


def _load_yaml(spec_path: str) -> tuple[Any | None, list[str]]:
    path = Path(spec_path)
    if not path.exists():
        return None, [f"{spec_path}: file does not exist"]
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        return None, [f"{spec_path}: failed to parse YAML: {exc}"]
    except OSError as exc:
        return None, [f"{spec_path}: failed to read file: {exc}"]
    return data, []


def _validate_reward_file(data: dict[str, Any], errors: list[str]) -> None:
    reward_terms = data.get("reward_terms", [])
    if not isinstance(reward_terms, list):
        return
    for index, term in enumerate(reward_terms):
        if not isinstance(term, dict):
            continue
        clip_bounds = term.get("clip_bounds")
        if not isinstance(clip_bounds, dict):
            continue
        minimum = clip_bounds.get("min")
        maximum = clip_bounds.get("max")
        if (
            isinstance(minimum, (int, float))
            and not isinstance(minimum, bool)
            and isinstance(maximum, (int, float))
            and not isinstance(maximum, bool)
            and minimum > maximum
        ):
            errors.append(
                f"spec.reward_terms[{index}].clip_bounds: min cannot be greater than max"
            )


def _validate_constraint_file(data: dict[str, Any], errors: list[str]) -> None:
    constraints = data.get("constraints", [])
    if not isinstance(constraints, list):
        return
    for index, constraint in enumerate(constraints):
        if not isinstance(constraint, dict):
            continue
        path = f"spec.constraints[{index}]"
        delta = constraint.get("coverage_threshold_delta")
        if isinstance(delta, (int, float)) and not isinstance(delta, bool):
            if delta <= 0:
                errors.append(f"{path}.coverage_threshold_delta: must be > 0")
        severity = constraint.get("severity")
        tolerance = constraint.get("tolerance")
        penalty_weight = constraint.get("penalty_weight")
        if severity == "soft":
            if tolerance is None:
                errors.append(f"{path}.tolerance: soft constraint requires a non-null value")
            if penalty_weight is None:
                errors.append(
                    f"{path}.penalty_weight: soft constraint requires a non-null value"
                )
        elif severity in {"hard", "info"}:
            if tolerance is not None:
                errors.append(
                    f"{path}.tolerance: hard/info constraints must set tolerance to null"
                )
            if penalty_weight is not None:
                errors.append(
                    f"{path}.penalty_weight: hard/info constraints must set penalty_weight to null"
                )


def _validate_policy_file(data: dict[str, Any], errors: list[str]) -> None:
    action_space = data.get("action_space")
    if not isinstance(action_space, dict):
        return
    bounds = action_space.get("bounds")
    shape = action_space.get("shape")
    if isinstance(bounds, dict):
        bound_min = bounds.get("min")
        bound_max = bounds.get("max")
        if isinstance(bound_min, list) and isinstance(bound_max, list):
            if len(bound_min) != len(bound_max):
                errors.append(
                    "spec.action_space.bounds: min and max must have the same number of entries"
                )
            if isinstance(shape, list) and len(shape) == 1 and isinstance(shape[0], int):
                if len(bound_min) != shape[0] or len(bound_max) != shape[0]:
                    errors.append(
                        "spec.action_space.bounds: bound length must match action_space.shape[0]"
                    )


def _validate_environment_file(data: dict[str, Any], errors: list[str]) -> None:
    e_tr = data.get("E_tr")
    if isinstance(e_tr, dict):
        nominal_family = e_tr.get("nominal_family")
        scene_families = e_tr.get("scene_families")
        if isinstance(scene_families, list) and nominal_family not in scene_families:
            errors.append("spec.E_tr.nominal_family: must be included in E_tr.scene_families")

    e_dep = data.get("E_dep")
    if isinstance(e_dep, dict):
        nominal_env = e_dep.get("nominal_env")
        deployment_envs = e_dep.get("deployment_envs")
        if isinstance(deployment_envs, list) and nominal_env is not None:
            env_ids = {
                env.get("env_id")
                for env in deployment_envs
                if isinstance(env, dict) and isinstance(env.get("env_id"), str)
            }
            if nominal_env not in env_ids and nominal_env not in {
                env.get("scene_family")
                for env in deployment_envs
                if isinstance(env, dict)
            }:
                errors.append(
                    "spec.E_dep.nominal_env: must match a deployment env_id or scene_family"
                )


def _run_file_specific_checks(spec_type: str, data: dict[str, Any], errors: list[str]) -> None:
    if spec_type == "reward":
        _validate_reward_file(data, errors)
    elif spec_type == "constraint":
        _validate_constraint_file(data, errors)
    elif spec_type == "policy":
        _validate_policy_file(data, errors)
    elif spec_type == "environment":
        _validate_environment_file(data, errors)


def validate_spec_file(spec_path: str) -> ValidationResult:
    data, load_errors = _load_yaml(spec_path)
    if load_errors:
        return ValidationResult(valid=False, errors=load_errors, warnings=[])
    if not isinstance(data, dict):
        return ValidationResult(
            valid=False,
            errors=[f"{spec_path}: top-level YAML object must be a mapping"],
            warnings=[],
        )

    spec_type = data.get("spec_type")
    if spec_type not in SPEC_TYPES:
        return ValidationResult(
            valid=False,
            errors=[
                f"{spec_path}: spec_type must be one of {sorted(SPEC_TYPES)}, got {spec_type!r}"
            ],
            warnings=[],
        )

    errors: list[str] = []
    warnings: list[str] = []
    _validate_schema(data, SPEC_SCHEMAS[spec_type], "spec", errors)
    _run_file_specific_checks(spec_type, data, errors)
    return ValidationResult(valid=not errors, errors=errors, warnings=warnings)


def _build_reward_adjacency(
    term_ids: set[str],
    dag_edges: list[dict[str, Any]],
) -> dict[str, list[str]]:
    adjacency = {term_id: [] for term_id in term_ids}
    for edge in dag_edges:
        if not isinstance(edge, dict):
            continue
        source = edge.get("from")
        target = edge.get("to")
        if source in term_ids and target in term_ids:
            adjacency[source].append(target)
    return adjacency


def _find_cycle(adjacency: dict[str, list[str]]) -> list[str] | None:
    visited: set[str] = set()
    visiting: set[str] = set()
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        visited.add(node)
        visiting.add(node)
        stack.append(node)
        for neighbor in adjacency.get(node, []):
            if neighbor not in visited:
                cycle = visit(neighbor)
                if cycle is not None:
                    return cycle
            elif neighbor in visiting:
                start_index = stack.index(neighbor)
                return stack[start_index:] + [neighbor]
        visiting.remove(node)
        stack.pop()
        return None

    for node in adjacency:
        if node not in visited:
            cycle = visit(node)
            if cycle is not None:
                return cycle
    return None


def validate_spec_set(
    reward_spec_path: str,
    constraint_spec_path: str,
    policy_spec_path: str,
    env_spec_path: str,
) -> ValidationResult:
    file_results = {
        "reward": validate_spec_file(reward_spec_path),
        "constraint": validate_spec_file(constraint_spec_path),
        "policy": validate_spec_file(policy_spec_path),
        "environment": validate_spec_file(env_spec_path),
    }
    merged = _merge_results(*file_results.values())

    loaded_specs: dict[str, dict[str, Any]] = {}
    for spec_name, spec_path in {
        "reward": reward_spec_path,
        "constraint": constraint_spec_path,
        "policy": policy_spec_path,
        "environment": env_spec_path,
    }.items():
        data, load_errors = _load_yaml(spec_path)
        if load_errors or not isinstance(data, dict):
            continue
        loaded_specs[spec_name] = data

    cross_errors: list[str] = []
    cross_warnings: list[str] = []

    version_map = {
        spec_name: data.get("spec_version")
        for spec_name, data in loaded_specs.items()
        if isinstance(data.get("spec_version"), str)
    }
    if len(version_map) == 4 and len(set(version_map.values())) != 1:
        detail = ", ".join(
            f"{spec_name}={version!r}" for spec_name, version in sorted(version_map.items())
        )
        cross_errors.append(f"spec_version mismatch across spec set: {detail}")

    reward_data = loaded_specs.get("reward")
    if isinstance(reward_data, dict):
        reward_terms = reward_data.get("reward_terms")
        dag_edges = reward_data.get("dag_edges")
        if isinstance(reward_terms, list) and isinstance(dag_edges, list):
            term_ids = {
                term.get("term_id")
                for term in reward_terms
                if isinstance(term, dict) and isinstance(term.get("term_id"), str)
            }
            edge_membership: dict[str, int] = {term_id: 0 for term_id in term_ids}
            for index, edge in enumerate(dag_edges):
                if not isinstance(edge, dict):
                    continue
                source = edge.get("from")
                target = edge.get("to")
                if source not in term_ids:
                    cross_errors.append(
                        f"reward.dag_edges[{index}].from references undefined term_id {source!r}"
                    )
                else:
                    edge_membership[source] += 1
                if target not in term_ids:
                    cross_errors.append(
                        f"reward.dag_edges[{index}].to references undefined term_id {target!r}"
                    )
                else:
                    edge_membership[target] += 1

            adjacency = _build_reward_adjacency(term_ids, dag_edges)
            cycle = _find_cycle(adjacency)
            if cycle is not None:
                cycle_repr = " -> ".join(cycle)
                cross_errors.append(f"reward.dag_edges contains a cycle: {cycle_repr}")

            for term in reward_terms:
                if not isinstance(term, dict):
                    continue
                term_id = term.get("term_id")
                shaping_flag = term.get("shaping_flag")
                if (
                    isinstance(term_id, str)
                    and shaping_flag is True
                    and edge_membership.get(term_id, 0) == 0
                ):
                    cross_warnings.append(
                        f"term {term_id} has shaping_flag=true but no DAG edge"
                    )

    env_data = loaded_specs.get("environment")
    if isinstance(env_data, dict):
        shift_operators = env_data.get("shift_operators")
        scene_families = env_data.get("scene_families")
        e_dep = env_data.get("E_dep")
        defined_shift_ids = {
            item.get("shift_id")
            for item in shift_operators
            if isinstance(item, dict) and isinstance(item.get("shift_id"), str)
        } if isinstance(shift_operators, list) else set()
        defined_scene_families = {
            family for family in scene_families if isinstance(family, str)
        } if isinstance(scene_families, list) else set()

        if isinstance(e_dep, dict):
            deployment_envs = e_dep.get("deployment_envs")
            if isinstance(deployment_envs, list):
                for index, deployment_env in enumerate(deployment_envs):
                    if not isinstance(deployment_env, dict):
                        continue
                    scene_family = deployment_env.get("scene_family")
                    if scene_family not in defined_scene_families:
                        cross_errors.append(
                            "environment.E_dep.deployment_envs"
                            f"[{index}].scene_family references undefined scene family"
                            f" {scene_family!r}"
                        )
                    applied_shift_operators = deployment_env.get("applied_shift_operators")
                    if isinstance(applied_shift_operators, list):
                        for shift_index, shift_id in enumerate(applied_shift_operators):
                            if shift_id not in defined_shift_ids:
                                cross_errors.append(
                                    "environment.E_dep.deployment_envs"
                                    f"[{index}].applied_shift_operators[{shift_index}]"
                                    f" references undefined shift_id {shift_id!r}"
                                )

    merged.errors.extend(cross_errors)
    merged.warnings.extend(cross_warnings)
    merged.valid = not merged.errors
    return merged
