"""Machine-readable CRE specification IR for static analysis."""

from __future__ import annotations

import ast
import copy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from envs.cre_logging import SCHEMA_VERSION as RUNTIME_LOG_SCHEMA_VERSION
from envs.cre_logging import STANDARD_REWARD_COMPONENT_KEYS
from runtime_logging.acceptance import (
    CANONICAL_DONE_TYPES,
    REQUIRED_EPISODE_FIELDS,
    REQUIRED_RUN_ARTIFACTS,
    REQUIRED_STEP_FIELDS,
)

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal envs
    class _YamlCompat:
        @staticmethod
        def _strip_comment(line: str) -> str:
            return line.split("#", 1)[0].rstrip()

        @staticmethod
        def _parse_scalar(value: str):
            lowered = value.lower()
            if lowered in {"true", "false"}:
                return lowered == "true"
            if lowered in {"null", "none", "~"}:
                return None
            if value.startswith(("'", '"')) and value.endswith(("'", '"')):
                return value[1:-1]
            if value.startswith(("[", "{", "(", "-")) or value[:1].isdigit():
                try:
                    normalized = (
                        value.replace("true", "True")
                        .replace("false", "False")
                        .replace("null", "None")
                    )
                    return ast.literal_eval(normalized)
                except Exception:
                    pass
            try:
                if "." in value or "e" in lowered:
                    return float(value)
                return int(value)
            except Exception:
                return value

        @classmethod
        def _parse_block(cls, lines, start_idx: int, indent: int):
            if start_idx >= len(lines):
                return {}, start_idx

            line_indent, content = lines[start_idx]
            if content.startswith("- "):
                items = []
                idx = start_idx
                while idx < len(lines):
                    current_indent, current = lines[idx]
                    if current_indent < indent or not current.startswith("- "):
                        break
                    if current_indent != indent:
                        break
                    payload = current[2:].strip()
                    idx += 1
                    if payload == "":
                        child, idx = cls._parse_block(lines, idx, indent + 2)
                        items.append(child)
                    else:
                        items.append(cls._parse_scalar(payload))
                return items, idx

            mapping = {}
            idx = start_idx
            while idx < len(lines):
                current_indent, current = lines[idx]
                if current_indent < indent or current_indent != indent:
                    break
                key, sep, raw_value = current.partition(":")
                if not sep:
                    raise ValueError(f"Invalid YAML line: {current}")
                key = key.strip()
                value = raw_value.strip()
                idx += 1
                if value == "":
                    if idx < len(lines) and lines[idx][0] > current_indent:
                        child, idx = cls._parse_block(lines, idx, current_indent + 2)
                        mapping[key] = child
                    else:
                        mapping[key] = {}
                else:
                    mapping[key] = cls._parse_scalar(value)
            return mapping, idx

        @classmethod
        def safe_load(cls, text):
            lines = []
            for raw_line in text.splitlines():
                stripped = cls._strip_comment(raw_line)
                if not stripped.strip():
                    continue
                indent = len(stripped) - len(stripped.lstrip(" "))
                lines.append((indent, stripped.lstrip(" ")))
            if not lines:
                return {}
            parsed, _ = cls._parse_block(lines, 0, lines[0][0])
            return parsed

    yaml = _YamlCompat()


TRAINING_ROOT = Path(__file__).resolve().parents[1]
CFG_ROOT = TRAINING_ROOT / "cfg"
SPEC_CFG_DIR = CFG_ROOT / "spec_cfg"
ENV_CFG_DIR = CFG_ROOT / "env_cfg"
DETECTOR_CFG_DIR = CFG_ROOT / "detector_cfg"

SCENE_CFG_BASE = "scene_cfg_base.yaml"
SCENE_CFG_BY_FAMILY = {
    "nominal": "scene_cfg_nominal.yaml",
    "boundary_critical": "scene_cfg_boundary_critical.yaml",
    "shifted": "scene_cfg_shifted.yaml",
}

DEFAULT_SCENE_FAMILIES = ("nominal", "boundary_critical", "shifted")
DEFAULT_DONE_TYPE_CODE_LABELS = {
    0: "running",
    1: "success",
    2: "collision",
    3: "out_of_bounds",
    4: "truncated",
}
DEFAULT_RUNTIME_INFO_FIELDS = (
    "drone_state",
    "goal_distance",
    "min_obstacle_distance",
    "near_violation_flag",
    "out_of_bounds_flag",
    "collision_flag",
    "yaw_rate",
    "speed_norm",
    "done_type",
    "reward_total",
    "reward_progress",
    "reward_safety_static",
    "reward_safety_dynamic",
    "penalty_smooth",
    "penalty_height",
)
DEFAULT_RUNTIME_STATS_FIELDS = (
    "return",
    "episode_len",
    "reach_goal",
    "collision",
    "truncated",
    "goal_distance",
    "min_obstacle_distance",
    "near_violation_steps",
    "near_violation_ratio",
    "out_of_bounds",
    "done_type",
    "reward_progress_total",
    "reward_safety_static_total",
    "reward_safety_dynamic_total",
    "penalty_smooth_total",
    "penalty_height_total",
)
DEFAULT_EXECUTION_MODE_ARTIFACTS = {
    mode: tuple(REQUIRED_RUN_ARTIFACTS)
    for mode in ("manual", "train", "eval", "baseline")
}
DEFAULT_REPORT_MODE_ARTIFACTS = {
    "static_audit": (
        "static_report.json",
        "summary.json",
        "manifest.json",
        "namespace_manifest.json",
    )
}
DEFAULT_REPORT_NAMESPACES = {
    "static_audit": "analysis/static",
}


def _load_yaml_file(path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML file at {path} must load to a dict.")
    return data


def _deep_merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, Mapping)
        ):
            merged[key] = _deep_merge_dicts(merged[key], dict(value))
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _as_tuple(value: Any) -> Tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    return (value,)


def _as_str_tuple(value: Any) -> Tuple[str, ...]:
    return tuple(str(item) for item in _as_tuple(value))


def _to_path_dict(mapping: Mapping[str, Any]) -> Dict[str, str]:
    return {str(key): str(value) for key, value in mapping.items()}


@dataclass
class ConstraintSpec:
    constraint_id: str
    meaning: str = ""
    kind: str = "hard_boolean"
    severity: str = "info"
    logged_variable: str = ""
    threshold: Any = None
    threshold_ref: Optional[str] = None
    violation_condition: str = ""
    binding_required: bool = True
    active_scene_requirements: Tuple[str, ...] = ()
    notes: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RewardComponentSpec:
    component_key: str
    sign: str = "neutral"
    weight: Optional[float] = None
    expected_logged_key: Optional[str] = None
    expected_total_field: Optional[str] = None
    enabled: bool = True
    intended_effect: str = ""
    execution_modes: Tuple[str, ...] = ()
    notes: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RewardSpec:
    spec_version: str = "v0"
    reward_total_field: str = "reward_total"
    components: Dict[str, RewardComponentSpec] = field(default_factory=dict)
    assumptions: Dict[str, Any] = field(default_factory=dict)
    standard_component_keys: Tuple[str, ...] = field(default_factory=tuple)
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EnvironmentFamilySpec:
    family: str
    scene_cfg_name: str
    scene_id: str
    seed: Optional[int] = None
    workspace: Dict[str, Any] = field(default_factory=dict)
    primitive_budget: Dict[str, Any] = field(default_factory=dict)
    primitive_type_ratio: Dict[str, Any] = field(default_factory=dict)
    distribution_modes: Dict[str, Any] = field(default_factory=dict)
    background_placement: Dict[str, Any] = field(default_factory=dict)
    templates: Dict[str, Any] = field(default_factory=dict)
    template_params: Dict[str, Any] = field(default_factory=dict)
    dynamic_obstacles: Dict[str, Any] = field(default_factory=dict)
    start_goal: Dict[str, Any] = field(default_factory=dict)
    validation: Dict[str, Any] = field(default_factory=dict)
    logging: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicySpec:
    spec_version: str = "v0"
    policy_type: str = "velocity_command_uav"
    action_type: str = "continuous"
    action_dimensions: int = 3
    action_bounds: Tuple[float, float] = (-2.0, 2.0)
    command_frame: str = "goal_aligned_velocity"
    yaw_control: bool = False
    observations: Dict[str, Any] = field(default_factory=dict)
    control: Dict[str, Any] = field(default_factory=dict)
    runtime_expectations: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuntimeSchemaSpec:
    schema_version: str
    step_required_fields: Tuple[str, ...]
    episode_required_fields: Tuple[str, ...]
    canonical_done_types: Tuple[str, ...]
    done_type_code_labels: Dict[int, str]
    reward_component_keys: Tuple[str, ...]
    runtime_info_fields: Tuple[str, ...]
    runtime_stats_fields: Tuple[str, ...]
    execution_mode_artifacts: Dict[str, Tuple[str, ...]]
    report_mode_artifacts: Dict[str, Tuple[str, ...]]
    report_namespaces: Dict[str, str]


@dataclass
class SpecIR:
    spec_version: str = "v0"
    constraints: Dict[str, ConstraintSpec] = field(default_factory=dict)
    reward_spec: RewardSpec = field(default_factory=RewardSpec)
    environment_families: Dict[str, EnvironmentFamilySpec] = field(default_factory=dict)
    policy_spec: PolicySpec = field(default_factory=PolicySpec)
    runtime_schema: RuntimeSchemaSpec = field(
        default_factory=lambda: build_runtime_schema_spec()
    )
    detector_thresholds: Dict[str, Any] = field(default_factory=dict)
    witness_weights: Dict[str, Any] = field(default_factory=dict)
    source_paths: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_scene_family_config(
    scene_family: str,
    env_cfg_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    env_cfg_dir = env_cfg_dir or ENV_CFG_DIR
    base_cfg = {}
    base_path = env_cfg_dir / SCENE_CFG_BASE
    if base_path.exists():
        base_cfg = _load_yaml_file(base_path)

    family_cfg_name = SCENE_CFG_BY_FAMILY.get(str(scene_family))
    if family_cfg_name is None:
        raise ValueError(f"Unsupported scene family '{scene_family}'.")

    family_path = env_cfg_dir / family_cfg_name
    if not family_path.exists():
        raise FileNotFoundError(f"Missing scene family config: {family_path}")

    family_cfg = _load_yaml_file(family_path)
    merged = _deep_merge_dicts(base_cfg, family_cfg)
    merged["scene_family"] = str(scene_family)
    merged["scene_cfg_name"] = family_cfg_name
    return merged


def load_constraint_spec(spec_cfg_dir: Optional[Path] = None) -> Dict[str, ConstraintSpec]:
    spec_cfg_dir = spec_cfg_dir or SPEC_CFG_DIR
    path = spec_cfg_dir / "constraint_spec_v0.yaml"
    raw = _load_yaml_file(path)
    constraints = raw.get("constraints", {})
    if not isinstance(constraints, Mapping):
        raise ValueError("constraint_spec_v0.yaml must contain a mapping named 'constraints'.")

    parsed: Dict[str, ConstraintSpec] = {}
    for constraint_id, payload in constraints.items():
        payload = dict(payload or {})
        parsed[str(constraint_id)] = ConstraintSpec(
            constraint_id=str(constraint_id),
            meaning=str(payload.get("meaning", "")),
            kind=str(payload.get("kind", "hard_boolean")),
            severity=str(payload.get("severity", "info")),
            logged_variable=str(payload.get("logged_variable", "")),
            threshold=payload.get("threshold"),
            threshold_ref=payload.get("threshold_ref"),
            violation_condition=str(payload.get("violation_condition", "")),
            binding_required=bool(payload.get("binding_required", True)),
            active_scene_requirements=_as_str_tuple(payload.get("active_scene_requirements")),
            notes=str(payload.get("notes", "")),
            raw=payload,
        )
    return parsed


def load_reward_spec(spec_cfg_dir: Optional[Path] = None) -> RewardSpec:
    spec_cfg_dir = spec_cfg_dir or SPEC_CFG_DIR
    path = spec_cfg_dir / "reward_spec_v0.yaml"
    raw = _load_yaml_file(path)
    components = raw.get("components", {})
    if not isinstance(components, Mapping):
        raise ValueError("reward_spec_v0.yaml must contain a mapping named 'components'.")

    parsed_components: Dict[str, RewardComponentSpec] = {}
    for component_key, payload in components.items():
        payload = dict(payload or {})
        parsed_components[str(component_key)] = RewardComponentSpec(
            component_key=str(component_key),
            sign=str(payload.get("sign", "neutral")),
            weight=payload.get("weight"),
            expected_logged_key=payload.get("expected_logged_key"),
            expected_total_field=payload.get("expected_total_field"),
            enabled=bool(payload.get("enabled", True)),
            intended_effect=str(payload.get("intended_effect", "")),
            execution_modes=_as_str_tuple(payload.get("execution_modes")),
            notes=str(payload.get("notes", "")),
            raw=payload,
        )

    return RewardSpec(
        spec_version=str(raw.get("spec_version", "v0")),
        reward_total_field=str(raw.get("reward_total_field", "reward_total")),
        components=parsed_components,
        assumptions=dict(raw.get("assumptions", {})),
        standard_component_keys=_as_str_tuple(
            raw.get("standard_component_keys", STANDARD_REWARD_COMPONENT_KEYS)
        ),
        raw=raw,
    )


def load_policy_spec(spec_cfg_dir: Optional[Path] = None) -> PolicySpec:
    spec_cfg_dir = spec_cfg_dir or SPEC_CFG_DIR
    path = spec_cfg_dir / "policy_spec_v0.yaml"
    raw = _load_yaml_file(path)
    bounds = raw.get("action_bounds", [-2.0, 2.0])
    if isinstance(bounds, Sequence) and len(bounds) == 2:
        action_bounds = (float(bounds[0]), float(bounds[1]))
    else:
        action_bounds = (-2.0, 2.0)

    return PolicySpec(
        spec_version=str(raw.get("spec_version", "v0")),
        policy_type=str(raw.get("policy_type", "velocity_command_uav")),
        action_type=str(raw.get("action_type", "continuous")),
        action_dimensions=int(raw.get("action_dimensions", 3)),
        action_bounds=action_bounds,
        command_frame=str(raw.get("command_frame", "goal_aligned_velocity")),
        yaw_control=bool(raw.get("yaw_control", False)),
        observations=dict(raw.get("observations", {})),
        control=dict(raw.get("control", {})),
        runtime_expectations=dict(raw.get("runtime_expectations", {})),
        raw=raw,
    )


def load_environment_spec(
    scene_families: Sequence[str] = DEFAULT_SCENE_FAMILIES,
    env_cfg_dir: Optional[Path] = None,
) -> Dict[str, EnvironmentFamilySpec]:
    env_cfg_dir = env_cfg_dir or ENV_CFG_DIR
    parsed: Dict[str, EnvironmentFamilySpec] = {}
    for family in scene_families:
        cfg = load_scene_family_config(str(family), env_cfg_dir=env_cfg_dir)
        family_name = str(cfg.get("scene_family", family))
        parsed[family_name] = EnvironmentFamilySpec(
            family=family_name,
            scene_cfg_name=str(cfg.get("scene_cfg_name", SCENE_CFG_BY_FAMILY.get(family_name, ""))),
            scene_id=str(cfg.get("scene_id", "")),
            seed=cfg.get("seed"),
            workspace=dict(cfg.get("workspace", {})),
            primitive_budget=dict(cfg.get("primitive_budget", {})),
            primitive_type_ratio=dict(cfg.get("primitive_type_ratio", {})),
            distribution_modes=dict(cfg.get("distribution_modes", {})),
            background_placement=dict(cfg.get("background_placement", {})),
            templates=dict(cfg.get("templates", {})),
            template_params=dict(cfg.get("template_params", {})),
            dynamic_obstacles=dict(cfg.get("dynamic_obstacles", {})),
            start_goal=dict(cfg.get("start_goal", {})),
            validation=dict(cfg.get("validation", {})),
            logging=dict(cfg.get("logging", {})),
            raw=cfg,
        )
    return parsed


def load_detector_thresholds(detector_cfg_dir: Optional[Path] = None) -> Dict[str, Any]:
    detector_cfg_dir = detector_cfg_dir or DETECTOR_CFG_DIR
    return _load_yaml_file(detector_cfg_dir / "detector_thresholds.yaml")


def load_witness_weights(detector_cfg_dir: Optional[Path] = None) -> Dict[str, Any]:
    detector_cfg_dir = detector_cfg_dir or DETECTOR_CFG_DIR
    return _load_yaml_file(detector_cfg_dir / "witness_weights.yaml")


def build_runtime_schema_spec() -> RuntimeSchemaSpec:
    return RuntimeSchemaSpec(
        schema_version=RUNTIME_LOG_SCHEMA_VERSION,
        step_required_fields=tuple(sorted(REQUIRED_STEP_FIELDS)),
        episode_required_fields=tuple(sorted(REQUIRED_EPISODE_FIELDS)),
        canonical_done_types=tuple(sorted(CANONICAL_DONE_TYPES)),
        done_type_code_labels=dict(DEFAULT_DONE_TYPE_CODE_LABELS),
        reward_component_keys=tuple(STANDARD_REWARD_COMPONENT_KEYS),
        runtime_info_fields=tuple(DEFAULT_RUNTIME_INFO_FIELDS),
        runtime_stats_fields=tuple(DEFAULT_RUNTIME_STATS_FIELDS),
        execution_mode_artifacts=dict(DEFAULT_EXECUTION_MODE_ARTIFACTS),
        report_mode_artifacts=dict(DEFAULT_REPORT_MODE_ARTIFACTS),
        report_namespaces=dict(DEFAULT_REPORT_NAMESPACES),
    )


def load_spec_ir(
    spec_cfg_dir: Optional[Path] = None,
    env_cfg_dir: Optional[Path] = None,
    detector_cfg_dir: Optional[Path] = None,
    scene_families: Sequence[str] = DEFAULT_SCENE_FAMILIES,
) -> SpecIR:
    spec_cfg_dir = spec_cfg_dir or SPEC_CFG_DIR
    env_cfg_dir = env_cfg_dir or ENV_CFG_DIR
    detector_cfg_dir = detector_cfg_dir or DETECTOR_CFG_DIR

    constraints = load_constraint_spec(spec_cfg_dir)
    reward_spec = load_reward_spec(spec_cfg_dir)
    policy_spec = load_policy_spec(spec_cfg_dir)
    environment_families = load_environment_spec(scene_families, env_cfg_dir)
    runtime_schema = build_runtime_schema_spec()
    detector_thresholds = load_detector_thresholds(detector_cfg_dir)
    witness_weights = load_witness_weights(detector_cfg_dir)

    spec_version = next(
        value
        for value in (
            reward_spec.spec_version,
            policy_spec.spec_version,
            detector_thresholds.get("spec_version"),
            "v0",
        )
        if value
    )

    source_paths = _to_path_dict({
        "constraint_spec": spec_cfg_dir / "constraint_spec_v0.yaml",
        "reward_spec": spec_cfg_dir / "reward_spec_v0.yaml",
        "policy_spec": spec_cfg_dir / "policy_spec_v0.yaml",
        "detector_thresholds": detector_cfg_dir / "detector_thresholds.yaml",
        "witness_weights": detector_cfg_dir / "witness_weights.yaml",
        "scene_cfg_base": env_cfg_dir / SCENE_CFG_BASE,
        **{
            f"scene_family:{family}": env_cfg_dir / SCENE_CFG_BY_FAMILY[str(family)]
            for family in scene_families
            if str(family) in SCENE_CFG_BY_FAMILY
        },
    })

    return SpecIR(
        spec_version=str(spec_version),
        constraints=constraints,
        reward_spec=reward_spec,
        environment_families=environment_families,
        policy_spec=policy_spec,
        runtime_schema=runtime_schema,
        detector_thresholds=detector_thresholds,
        witness_weights=witness_weights,
        source_paths=source_paths,
    )
