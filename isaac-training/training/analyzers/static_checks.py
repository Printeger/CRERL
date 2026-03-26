"""Phase 4 deterministic static consistency checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Sequence

from envs.env_gen import SUPPORTED_RULE_TEMPLATE_TYPES, SUPPORTED_SCENE_FAMILY_BACKEND
from .spec_ir import SpecIR

SUPPORTED_EXECUTION_MODES = {"manual", "train", "eval", "baseline"}
ROLLOUT_EXECUTION_MODES = {"train", "eval", "baseline"}


@dataclass
class StaticCheckResult:
    """Structured result for a static consistency check."""

    check_id: str
    passed: bool
    severity: str = "info"
    summary: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    affected_paths: List[str] = field(default_factory=list)
    recommended_action: str = ""


def _source_path(spec_ir: SpecIR, key: str) -> str:
    return str(spec_ir.source_paths.get(key, key))


def _constraint_spec_path(spec_ir: SpecIR) -> str:
    return _source_path(spec_ir, "constraint_spec")


def _reward_spec_path(spec_ir: SpecIR) -> str:
    return _source_path(spec_ir, "reward_spec")


def _policy_spec_path(spec_ir: SpecIR) -> str:
    return _source_path(spec_ir, "policy_spec")


def _scene_backend_path() -> str:
    return str(Path(__file__).resolve().parents[1] / "envs" / "env_gen.py")


def _scene_cfg_paths(spec_ir: SpecIR) -> List[str]:
    return sorted(
        str(path)
        for key, path in spec_ir.source_paths.items()
        if str(key).startswith("scene_family:")
    )


def _runtime_fields(spec_ir: SpecIR) -> set[str]:
    return (
        set(spec_ir.runtime_schema.step_required_fields)
        | set(spec_ir.runtime_schema.episode_required_fields)
        | set(spec_ir.runtime_schema.runtime_info_fields)
        | set(spec_ir.runtime_schema.runtime_stats_fields)
    )


def _family_capabilities(spec_ir: SpecIR) -> Dict[str, Dict[str, bool]]:
    capabilities: Dict[str, Dict[str, bool]] = {}
    for family_name, family in spec_ir.environment_families.items():
        primitive_budget = family.primitive_budget
        templates = family.templates
        dynamic_cfg = family.dynamic_obstacles
        candidate_types = set(templates.get("candidate_types", []))
        capabilities[family_name] = {
            "all_families": True,
            "workspace_limits": bool(family.workspace),
            "static_obstacles": any(
                int((primitive_budget.get(key) or [0, 0])[1]) > 0
                for key in ("box", "cylinder", "slab", "perforated_slab")
            ) or bool(templates.get("enabled", False)),
            "dynamic_obstacles": bool(dynamic_cfg.get("enabled"))
            and int(dynamic_cfg.get("max_dynamic_count", 0) or 0) > 0,
            "route_adjacent_structure": bool(templates.get("enabled", False))
            and float(family.distribution_modes.get("route_adjacent_bias", 0.0) or 0.0) > 0.0,
            "perforated_templates": "perforated_barrier" in candidate_types
            or int((primitive_budget.get("perforated_slab") or [0, 0])[1]) > 0,
            "shifted_distribution": family_name == "shifted",
        }
    return capabilities


def _coerce_range_pair(value: Any) -> tuple[float, float] | None:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            return float(value[0]), float(value[1])
        except (TypeError, ValueError):
            return None
    return None


def check_constraint_runtime_binding(spec_ir: SpecIR) -> StaticCheckResult:
    runtime_fields = (
        set(spec_ir.runtime_schema.step_required_fields)
        | set(spec_ir.runtime_schema.runtime_info_fields)
        | set(spec_ir.runtime_schema.runtime_stats_fields)
    )

    missing_logged_variables: List[Dict[str, Any]] = []
    missing_threshold_refs: List[Dict[str, Any]] = []
    for constraint_id, constraint in spec_ir.constraints.items():
        if constraint.binding_required and constraint.logged_variable:
            if constraint.logged_variable not in runtime_fields:
                missing_logged_variables.append(
                    {
                        "constraint_id": constraint_id,
                        "logged_variable": constraint.logged_variable,
                    }
                )
        if constraint.threshold_ref:
            if constraint.threshold_ref not in spec_ir.detector_thresholds:
                missing_threshold_refs.append(
                    {
                        "constraint_id": constraint_id,
                        "threshold_ref": constraint.threshold_ref,
                    }
                )

    issues = missing_logged_variables + missing_threshold_refs
    passed = not issues
    if passed:
        summary = "All required constraints map to runtime fields and threshold references."
        severity = "info"
    else:
        summary = "Some declared constraints do not bind cleanly to runtime fields or thresholds."
        severity = "high"

    return StaticCheckResult(
        check_id="constraint_runtime_binding",
        passed=passed,
        severity=severity,
        summary=summary,
        details={
            "missing_logged_variables": missing_logged_variables,
            "missing_threshold_refs": missing_threshold_refs,
            "runtime_fields_checked": sorted(runtime_fields),
        },
        affected_paths=[_constraint_spec_path(spec_ir)],
        recommended_action=(
            "Update the constraint spec or runtime schema so every required "
            "constraint has a valid logged_variable and threshold_ref."
        ),
    )


def check_reward_constraint_conflicts(spec_ir: SpecIR) -> StaticCheckResult:
    issues: List[Dict[str, Any]] = []
    reward_components = spec_ir.reward_spec.components

    def enabled(name: str) -> bool:
        component = reward_components.get(name)
        return bool(component and component.enabled)

    constraints = spec_ir.constraints
    dynamic_enabled = any(
        bool(family.dynamic_obstacles.get("enabled"))
        or int(family.dynamic_obstacles.get("max_dynamic_count", 0) or 0) > 0
        for family in spec_ir.environment_families.values()
    )

    if "safety_margin" in constraints and not enabled("reward_safety_static"):
        issues.append(
            {
                "kind": "missing_static_safety_support",
                "constraint": "safety_margin",
                "reward_component": "reward_safety_static",
                "reason": "Safety margin is declared but no static safety shaping is enabled.",
            }
        )

    if "collision_avoidance" in constraints:
        if not enabled("reward_safety_static") and not enabled("reward_safety_dynamic"):
            issues.append(
                {
                    "kind": "missing_collision_support",
                    "constraint": "collision_avoidance",
                    "reward_component": None,
                    "reason": "Collision avoidance exists but no safety-related reward component is enabled.",
                }
            )

    if dynamic_enabled and "safety_margin" in constraints and not enabled("reward_safety_dynamic"):
        issues.append(
            {
                "kind": "missing_dynamic_safety_support",
                "constraint": "safety_margin",
                "reward_component": "reward_safety_dynamic",
                "reason": "Dynamic hazards are enabled in the environment spec but dynamic safety shaping is disabled.",
            }
        )

    if "speed_bound" in constraints and enabled("reward_progress") and not enabled("penalty_smooth"):
        issues.append(
            {
                "kind": "speed_progress_tension",
                "constraint": "speed_bound",
                "reward_component": "reward_progress",
                "reason": "Progress reward is enabled while speed is bounded and no smoothness penalty is active.",
            }
        )

    if "workspace_boundary" in constraints and not enabled("penalty_height"):
        issues.append(
            {
                "kind": "missing_workspace_penalty",
                "constraint": "workspace_boundary",
                "reward_component": "penalty_height",
                "reason": "Workspace boundary exists but no height penalty is enabled.",
            }
        )

    passed = not issues
    return StaticCheckResult(
        check_id="reward_constraint_conflicts",
        passed=passed,
        severity="high" if not passed else "info",
        summary=(
            "No obvious reward/constraint direct conflicts were detected."
            if passed
            else "Potential reward/constraint conflicts were detected in the v0 spec."
        ),
        details={
            "issues": issues,
            "enabled_reward_components": sorted(
                key for key, component in reward_components.items() if component.enabled
            ),
        },
        affected_paths=[_reward_spec_path(spec_ir), _constraint_spec_path(spec_ir)],
        recommended_action=(
            "Rebalance reward components or constraint support terms so each "
            "declared safety requirement has an explicit behavioral counterweight."
        ),
    )


def check_reward_proxy_suspicion(spec_ir: SpecIR) -> StaticCheckResult:
    assumptions = spec_ir.reward_spec.assumptions
    reward_components = spec_ir.reward_spec.components
    warnings: List[Dict[str, Any]] = []

    if assumptions.get("constant_step_bias_present", False):
        warnings.append(
            {
                "kind": "constant_step_bias",
                "reason": "A constant per-step reward bias is present and may reward lingering or overlong trajectories.",
            }
        )

    if (
        assumptions.get("success_bonus_present", False) is False
        and reward_components.get("reward_progress")
        and reward_components["reward_progress"].enabled
    ):
        warnings.append(
            {
                "kind": "progress_without_success_bonus",
                "reason": "Progress shaping is active while no explicit success bonus is declared.",
            }
        )

    if (
        assumptions.get("collision_penalty_present", False) is False
        and "collision_avoidance" in spec_ir.constraints
    ):
        warnings.append(
            {
                "kind": "no_collision_penalty",
                "reason": "Collision avoidance is declared but no explicit collision penalty is present in the reward assumptions.",
            }
        )

    passed = not warnings
    return StaticCheckResult(
        check_id="reward_proxy_suspicion",
        passed=passed,
        severity="warning" if warnings else "info",
        summary=(
            "No suspicious reward proxy patterns were detected."
            if passed
            else "The reward specification contains proxy patterns that may deserve review."
        ),
        details={
            "warnings": warnings,
            "assumptions": dict(assumptions),
        },
        affected_paths=[_reward_spec_path(spec_ir), _policy_spec_path(spec_ir)],
        recommended_action=(
            "Review whether progress shaping, step bias, and success/collision "
            "signals reflect the intended task objective instead of only an easy proxy."
        ),
    )


def check_scene_family_coverage(spec_ir: SpecIR) -> StaticCheckResult:
    capabilities = _family_capabilities(spec_ir)
    uncovered_requirements: List[Dict[str, Any]] = []

    for constraint_id, constraint in spec_ir.constraints.items():
        for requirement in constraint.active_scene_requirements:
            if requirement in ("", "all_families"):
                continue
            covered_by = sorted(
                family_name
                for family_name, family_caps in capabilities.items()
                if family_caps.get(requirement, False)
            )
            if not covered_by:
                uncovered_requirements.append(
                    {
                        "constraint_id": constraint_id,
                        "requirement": requirement,
                        "covered_by": covered_by,
                    }
                )

    passed = not uncovered_requirements
    return StaticCheckResult(
        check_id="scene_family_coverage",
        passed=passed,
        severity="high" if not passed else "info",
        summary=(
            "Scene families cover the current constraint activation requirements."
            if passed
            else "Some declared constraint activation requirements are not covered by any scene family."
        ),
        details={
            "uncovered_requirements": uncovered_requirements,
            "family_capabilities": capabilities,
        },
        affected_paths=_scene_cfg_paths(spec_ir) + [_constraint_spec_path(spec_ir)],
        recommended_action=(
            "Add or adjust scene-family capabilities so every declared constraint "
            "activation requirement is covered by at least one family."
        ),
    )


def check_required_runtime_fields(spec_ir: SpecIR) -> StaticCheckResult:
    runtime_fields = _runtime_fields(spec_ir)
    missing_reward_logged_keys: List[Dict[str, Any]] = []
    missing_reward_total_fields: List[Dict[str, Any]] = []
    required_core_fields = {
        "scene_id",
        "scenario_type",
        "scene_cfg_name",
        "reward_total",
        "done_type",
        "source",
    }
    missing_core_fields = sorted(required_core_fields - set(spec_ir.runtime_schema.step_required_fields))

    for component_key, component in spec_ir.reward_spec.components.items():
        if not component.enabled:
            continue
        execution_modes = set(component.execution_modes)
        if execution_modes and execution_modes <= {"manual"}:
            continue
        if component.expected_logged_key and component.expected_logged_key not in runtime_fields:
            missing_reward_logged_keys.append(
                {
                    "component_key": component_key,
                    "expected_logged_key": component.expected_logged_key,
                }
            )
        if component.expected_total_field and component.expected_total_field not in runtime_fields:
            missing_reward_total_fields.append(
                {
                    "component_key": component_key,
                    "expected_total_field": component.expected_total_field,
                }
            )

    missing_done_type_labels = []
    if spec_ir.policy_spec.runtime_expectations.get("done_type_labels_required", False):
        for code in (0, 1, 2, 3, 4):
            if code not in spec_ir.runtime_schema.done_type_code_labels:
                missing_done_type_labels.append(code)

    passed = not (missing_core_fields or missing_reward_logged_keys or missing_reward_total_fields or missing_done_type_labels)
    return StaticCheckResult(
        check_id="required_runtime_fields",
        passed=passed,
        severity="high" if not passed else "info",
        summary=(
            "The runtime schema provides the required core fields and reward bindings."
            if passed
            else "The runtime schema is missing one or more required fields or reward bindings."
        ),
        details={
            "missing_core_fields": missing_core_fields,
            "missing_reward_logged_keys": missing_reward_logged_keys,
            "missing_reward_total_fields": missing_reward_total_fields,
            "missing_done_type_labels": missing_done_type_labels,
            "runtime_fields_checked": sorted(runtime_fields),
        },
        affected_paths=[_reward_spec_path(spec_ir), _policy_spec_path(spec_ir)],
        recommended_action=(
            "Align the runtime schema with the declared reward and policy "
            "expectations so all required fields are emitted and named consistently."
        ),
    )


def check_scene_family_structure(spec_ir: SpecIR) -> StaticCheckResult:
    issues: List[Dict[str, Any]] = []

    for family_name, family in spec_ir.environment_families.items():
        workspace = family.workspace
        if float(workspace.get("size_x", 0.0) or 0.0) <= 0.0:
            issues.append(
                {
                    "family": family_name,
                    "kind": "invalid_workspace_size_x",
                    "value": workspace.get("size_x"),
                }
            )
        if float(workspace.get("size_y", 0.0) or 0.0) <= 0.0:
            issues.append(
                {
                    "family": family_name,
                    "kind": "invalid_workspace_size_y",
                    "value": workspace.get("size_y"),
                }
            )
        size_z = float(workspace.get("size_z", 0.0) or 0.0)
        height_min = float(workspace.get("flight_height_min", 0.0) or 0.0)
        height_max = float(workspace.get("flight_height_max", 0.0) or 0.0)
        if size_z <= 0.0:
            issues.append(
                {"family": family_name, "kind": "invalid_workspace_size_z", "value": size_z}
            )
        if not (0.0 <= height_min < height_max <= size_z):
            issues.append(
                {
                    "family": family_name,
                    "kind": "invalid_flight_height_band",
                    "flight_height_min": height_min,
                    "flight_height_max": height_max,
                    "size_z": size_z,
                }
            )

        background = family.background_placement
        free_space_min = float(background.get("free_space_fraction_min", 0.0) or 0.0)
        free_space_max = float(background.get("free_space_fraction_max", 0.0) or 0.0)
        if not (0.0 <= free_space_min <= free_space_max <= 1.0):
            issues.append(
                {
                    "family": family_name,
                    "kind": "invalid_free_space_fraction_range",
                    "free_space_fraction_min": free_space_min,
                    "free_space_fraction_max": free_space_max,
                }
            )
        if float(background.get("obstacle_obstacle_min_dist", 0.0) or 0.0) < 0.0:
            issues.append(
                {
                    "family": family_name,
                    "kind": "negative_obstacle_obstacle_min_dist",
                    "value": background.get("obstacle_obstacle_min_dist"),
                }
            )

        start_goal = family.start_goal
        start_goal_range = (
            float(start_goal.get("start_goal_distance_min", 0.0) or 0.0),
            float(start_goal.get("start_goal_distance_max", 0.0) or 0.0),
        )
        if start_goal_range[0] <= 0.0 or start_goal_range[0] > start_goal_range[1]:
            issues.append(
                {
                    "family": family_name,
                    "kind": "invalid_start_goal_distance_range",
                    "start_goal_distance_min": start_goal_range[0],
                    "start_goal_distance_max": start_goal_range[1],
                }
            )
        for clearance_key in (
            "start_clearance_min",
            "goal_clearance_min",
            "goal_boundary_clearance_min",
        ):
            if float(start_goal.get(clearance_key, 0.0) or 0.0) < 0.0:
                issues.append(
                    {
                        "family": family_name,
                        "kind": "negative_clearance_requirement",
                        "field": clearance_key,
                        "value": start_goal.get(clearance_key),
                    }
                )

        templates = family.templates
        validation = family.validation
        template_params = family.template_params
        candidate_types = list(templates.get("candidate_types", []))
        min_templates = int(templates.get("min_templates_per_scene", 0) or 0)
        max_templates = int(templates.get("max_templates_per_scene", 0) or 0)
        if bool(templates.get("enabled", False)):
            if not candidate_types:
                issues.append(
                    {
                        "family": family_name,
                        "kind": "missing_template_candidates",
                    }
                )
            if min_templates > max_templates:
                issues.append(
                    {
                        "family": family_name,
                        "kind": "invalid_template_count_range",
                        "min_templates_per_scene": min_templates,
                        "max_templates_per_scene": max_templates,
                    }
                )
            if bool(validation.get("require_template_presence", False)) and max_templates < 1:
                issues.append(
                    {
                        "family": family_name,
                        "kind": "template_presence_impossible",
                        "max_templates_per_scene": max_templates,
                    }
                )
            for template_name in candidate_types:
                template_cfg = template_params.get(template_name)
                if not isinstance(template_cfg, dict):
                    issues.append(
                        {
                            "family": family_name,
                            "kind": "missing_template_params",
                            "template": template_name,
                        }
                    )
                    continue
                if not bool(template_cfg.get("enabled", False)):
                    issues.append(
                        {
                            "family": family_name,
                            "kind": "disabled_candidate_template",
                            "template": template_name,
                        }
                    )
                count_range = _coerce_range_pair(template_cfg.get("count"))
                if count_range is None or count_range[0] > count_range[1]:
                    issues.append(
                        {
                            "family": family_name,
                            "kind": "invalid_template_count_param",
                            "template": template_name,
                            "count": template_cfg.get("count"),
                        }
                    )
                if template_name == "perforated_barrier" and bool(
                    validation.get("require_traversable_perforation", False)
                ):
                    hole_range = _coerce_range_pair(template_cfg.get("hole_count_range"))
                    if hole_range is None or hole_range[1] < 1.0:
                        issues.append(
                            {
                                "family": family_name,
                                "kind": "invalid_perforated_hole_count",
                                "template": template_name,
                                "hole_count_range": template_cfg.get("hole_count_range"),
                            }
                        )
        elif str(family.distribution_modes.get("structure", "")) == "template_driven":
            issues.append(
                {
                    "family": family_name,
                    "kind": "template_driven_without_templates",
                }
            )

    passed = not issues
    return StaticCheckResult(
        check_id="scene_family_structure",
        passed=passed,
        severity="high" if not passed else "info",
        summary=(
            "Scene family configs satisfy the current structural validation rules."
            if passed
            else "Some scene family configs violate required structural validation rules."
        ),
        details={"issues": issues},
        affected_paths=_scene_cfg_paths(spec_ir),
        recommended_action=(
            "Repair scene-family config structure so workspace, start-goal, "
            "template, and validation settings remain internally consistent."
        ),
    )


def check_execution_mode_alignment(spec_ir: SpecIR) -> StaticCheckResult:
    issues: List[Dict[str, Any]] = []
    runtime_expectations = spec_ir.policy_spec.runtime_expectations
    supported_execution_modes = set(
        runtime_expectations.get("supported_execution_modes", sorted(SUPPORTED_EXECUTION_MODES))
    )
    rollout_required_artifacts = set(
        runtime_expectations.get("rollout_required_artifacts", ())
    )
    static_audit_namespace = str(
        runtime_expectations.get(
            "static_audit_namespace",
            spec_ir.runtime_schema.report_namespaces.get("static_audit", "analysis/static"),
        )
    )
    static_audit_required_artifacts = set(
        runtime_expectations.get("static_audit_required_artifacts", ())
    )

    unknown_supported_modes = sorted(supported_execution_modes - SUPPORTED_EXECUTION_MODES)
    if unknown_supported_modes:
        issues.append(
            {
                "kind": "unknown_supported_execution_modes",
                "unknown_modes": unknown_supported_modes,
            }
        )

    for mode in sorted(supported_execution_modes & SUPPORTED_EXECUTION_MODES):
        artifacts = set(spec_ir.runtime_schema.execution_mode_artifacts.get(mode, ()))
        missing_artifacts = sorted(rollout_required_artifacts - artifacts)
        if missing_artifacts:
            issues.append(
                {
                    "kind": "missing_execution_mode_artifacts",
                    "mode": mode,
                    "missing_artifacts": missing_artifacts,
                }
            )

    actual_static_namespace = spec_ir.runtime_schema.report_namespaces.get("static_audit", "")
    if static_audit_namespace != actual_static_namespace:
        issues.append(
            {
                "kind": "static_audit_namespace_mismatch",
                "expected_namespace": static_audit_namespace,
                "actual_namespace": actual_static_namespace,
            }
        )

    actual_static_artifacts = set(spec_ir.runtime_schema.report_mode_artifacts.get("static_audit", ()))
    missing_static_artifacts = sorted(static_audit_required_artifacts - actual_static_artifacts)
    if missing_static_artifacts:
        issues.append(
            {
                "kind": "missing_static_audit_report_artifacts",
                "missing_artifacts": missing_static_artifacts,
            }
        )

    for component_key, component in spec_ir.reward_spec.components.items():
        if not component.enabled:
            continue
        modes = set(component.execution_modes)
        if not modes:
            issues.append(
                {
                    "component_key": component_key,
                    "kind": "missing_execution_modes",
                }
            )
            continue
        unknown_modes = sorted(modes - supported_execution_modes)
        if unknown_modes:
            issues.append(
                {
                    "component_key": component_key,
                    "kind": "unknown_execution_modes",
                    "unknown_modes": unknown_modes,
                }
            )
        if component_key == "manual_control":
            if modes != {"manual"}:
                issues.append(
                    {
                        "component_key": component_key,
                        "kind": "manual_component_mode_mismatch",
                        "execution_modes": sorted(modes),
                    }
                )
            continue

        missing_rollout_modes = sorted((ROLLOUT_EXECUTION_MODES & supported_execution_modes) - modes)
        if missing_rollout_modes:
            issues.append(
                {
                    "component_key": component_key,
                    "kind": "rollout_mode_gap",
                    "missing_modes": missing_rollout_modes,
                    "execution_modes": sorted(modes),
                }
            )
        if "manual" in modes:
            issues.append(
                {
                    "component_key": component_key,
                    "kind": "manual_mode_mixed_into_rollout_component",
                    "execution_modes": sorted(modes),
                }
            )

    passed = not issues
    return StaticCheckResult(
        check_id="execution_mode_alignment",
        passed=passed,
        severity="high" if not passed else "info",
        summary=(
            "Reward component execution modes align with the supported execution paths."
            if passed
            else "Some reward components do not align with the supported execution paths."
        ),
        details={
            "issues": issues,
            "supported_execution_modes": sorted(SUPPORTED_EXECUTION_MODES),
            "required_rollout_modes": sorted(ROLLOUT_EXECUTION_MODES),
        },
        affected_paths=[_reward_spec_path(spec_ir), _policy_spec_path(spec_ir)],
        recommended_action=(
            "Align reward component execution_modes with the supported manual, "
            "train, eval, and baseline execution paths."
        ),
    )


def check_scene_backend_capability(spec_ir: SpecIR) -> StaticCheckResult:
    issues: List[Dict[str, Any]] = []

    for family_name, family in spec_ir.environment_families.items():
        if family_name not in SUPPORTED_SCENE_FAMILY_BACKEND:
            issues.append(
                {
                    "family": family_name,
                    "kind": "unsupported_scene_family_backend",
                }
            )

        candidate_types = list(family.templates.get("candidate_types", []))
        unsupported_candidates = sorted(
            template_name
            for template_name in candidate_types
            if template_name not in SUPPORTED_RULE_TEMPLATE_TYPES
        )
        if unsupported_candidates:
            issues.append(
                {
                    "family": family_name,
                    "kind": "unsupported_template_candidates",
                    "template_types": unsupported_candidates,
                }
            )

        dynamic_cfg = family.dynamic_obstacles
        dynamic_enabled = bool(dynamic_cfg.get("enabled")) and int(dynamic_cfg.get("max_dynamic_count", 0) or 0) > 0
        if dynamic_enabled:
            dynamic_budget = family.primitive_budget
            has_dynamic_budget = any(
                int((dynamic_budget.get(key) or [0, 0])[1]) > 0
                for key in ("sphere", "capsule")
            )
            has_dynamic_template = "moving_crossing" in candidate_types
            if not (has_dynamic_budget or has_dynamic_template):
                issues.append(
                    {
                        "family": family_name,
                        "kind": "dynamic_backend_not_expressible",
                        "max_dynamic_count": dynamic_cfg.get("max_dynamic_count"),
                    }
                )

        if family.validation.get("require_traversable_perforation", False):
            supports_perforation = (
                "perforated_barrier" in candidate_types
                or int((family.primitive_budget.get("perforated_slab") or [0, 0])[1]) > 0
            )
            if not supports_perforation:
                issues.append(
                    {
                        "family": family_name,
                        "kind": "perforation_requirement_not_expressible",
                    }
                )

    passed = not issues
    return StaticCheckResult(
        check_id="scene_backend_capability",
        passed=passed,
        severity="high" if not passed else "info",
        summary=(
            "Scene backend capability matches the declared family requirements."
            if passed
            else "Some scene family requirements are not expressible by the current scene backend."
        ),
        details={
            "issues": issues,
            "supported_scene_families": sorted(SUPPORTED_SCENE_FAMILY_BACKEND),
            "supported_rule_templates": sorted(SUPPORTED_RULE_TEMPLATE_TYPES),
        },
        affected_paths=_scene_cfg_paths(spec_ir) + [_scene_backend_path()],
        recommended_action=(
            "Align scene-family declarations with the actual env_gen backend "
            "capabilities, or extend the backend to express the missing cases."
        ),
    )


def run_static_checks(
    spec_ir: SpecIR,
    check_ids: Sequence[str] | None = None,
) -> List[StaticCheckResult]:
    available = {
        "constraint_runtime_binding": check_constraint_runtime_binding,
        "reward_constraint_conflicts": check_reward_constraint_conflicts,
        "reward_proxy_suspicion": check_reward_proxy_suspicion,
        "scene_family_coverage": check_scene_family_coverage,
        "scene_family_structure": check_scene_family_structure,
        "scene_backend_capability": check_scene_backend_capability,
        "execution_mode_alignment": check_execution_mode_alignment,
        "required_runtime_fields": check_required_runtime_fields,
    }
    selected = list(check_ids) if check_ids is not None else list(available.keys())
    results: List[StaticCheckResult] = []
    for check_id in selected:
        if check_id not in available:
            raise ValueError(f"Unknown static check '{check_id}'.")
        results.append(available[check_id](spec_ir))
    return results
