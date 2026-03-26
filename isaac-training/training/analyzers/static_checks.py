"""Phase 4 deterministic static consistency checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Sequence

from .spec_ir import SpecIR


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


def _scene_cfg_paths(spec_ir: SpecIR) -> List[str]:
    return sorted(
        str(path)
        for key, path in spec_ir.source_paths.items()
        if str(key).startswith("scene_family:")
    )


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


def run_static_checks(
    spec_ir: SpecIR,
    check_ids: Sequence[str] | None = None,
) -> List[StaticCheckResult]:
    available = {
        "constraint_runtime_binding": check_constraint_runtime_binding,
        "reward_constraint_conflicts": check_reward_constraint_conflicts,
        "reward_proxy_suspicion": check_reward_proxy_suspicion,
    }
    selected = list(check_ids) if check_ids is not None else list(available.keys())
    results: List[StaticCheckResult] = []
    for check_id in selected:
        if check_id not in available:
            raise ValueError(f"Unknown static check '{check_id}'.")
        results.append(available[check_id](spec_ir))
    return results
