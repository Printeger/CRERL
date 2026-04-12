from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from statistics import median
from typing import Any

import yaml

from analyzers.static_analyzer import ISSUE_TYPE_PREFIX, SEVERITIES, ISSUE_TYPES, StaticIssue, StaticReport


@dataclass
class DynamicReport:
    spec_versions: dict[str, str]
    episode_count: int
    issues: list[StaticIssue]
    summary: dict[str, Any]
    output_path: str | None


def _load_yaml_file(path: str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a top-level mapping")
    return payload


def _load_log_dir(log_dir: str) -> list[dict[str, Any]]:
    log_path = Path(log_dir)
    episodes_dir = log_path / "episodes"
    episodes: list[dict[str, Any]] = []

    if episodes_dir.exists():
        for episode_path in sorted(episodes_dir.glob("episode_*.json")):
            payload = json.loads(episode_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                continue
            summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
            steps = payload.get("steps") if isinstance(payload.get("steps"), list) else []
            episodes.append({"summary": summary, "steps": steps})
        if episodes:
            return episodes

    episodes_jsonl_path = log_path / "episodes.jsonl"
    if episodes_jsonl_path.exists():
        for line in episodes_jsonl_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            summary = json.loads(line)
            if not isinstance(summary, dict):
                continue
            episodes.append({"summary": summary, "steps": []})
    return episodes


def _normalize_done_type(raw: str | int) -> int:
    if isinstance(raw, bool):
        return 4
    if isinstance(raw, int):
        return raw if raw in {0, 1, 2, 3, 4} else 4
    mapping = {
        "running": 0,
        "success": 1,
        "collision": 2,
        "out_of_bounds": 3,
        "truncated": 4,
        "manual_exit": 4,
        "manual_regen": 4,
        "unknown": 4,
    }
    return mapping.get(str(raw).strip().lower(), 4)


def _get_min_obstacle_distance(step: dict[str, Any]) -> float | None:
    value = step.get("min_obstacle_distance")
    if value is None:
        return None
    return float(value)


def _get_velocity_norm(step: dict[str, Any]) -> float | None:
    velocity = step.get("velocity")
    if not isinstance(velocity, (list, tuple)) or len(velocity) < 3:
        return None
    try:
        vx, vy, vz = (float(velocity[0]), float(velocity[1]), float(velocity[2]))
    except (TypeError, ValueError):
        return None
    return (vx ** 2 + vy ** 2 + vz ** 2) ** 0.5


def _get_yaw_rate(step: dict[str, Any]) -> float | None:
    value = step.get("yaw_rate")
    if value is None:
        return None
    return float(value)


def _get_position(step: dict[str, Any]) -> tuple[float, float, float] | None:
    position = step.get("position")
    if not isinstance(position, (list, tuple)) or len(position) < 3:
        return None
    try:
        return (float(position[0]), float(position[1]), float(position[2]))
    except (TypeError, ValueError):
        return None


def _make_issue_factory():
    counters: dict[str, int] = defaultdict(int)

    def create_issue(
        issue_type: str,
        severity: str,
        rule_id: str,
        description: str,
        traceable_fields: list[str],
        evidence: dict[str, Any] | None = None,
    ) -> StaticIssue:
        prefix = ISSUE_TYPE_PREFIX[issue_type]
        counters[prefix] += 1
        return StaticIssue(
            issue_id=f"{prefix}-{counters[prefix]:03d}",
            issue_type=issue_type,
            severity=severity,
            rule_id=rule_id,
            description=description,
            traceable_fields=traceable_fields,
            evidence=evidence or {},
        )

    return create_issue


def _all_steps(episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for episode in episodes:
        payload = episode.get("steps", [])
        if isinstance(payload, list):
            steps.extend(step for step in payload if isinstance(step, dict))
    return steps


def _iter_constraints_by_severity(
    constraint_spec: dict[str, Any],
    severity: str,
) -> list[tuple[int, dict[str, Any]]]:
    constraints = constraint_spec.get("constraints", [])
    if not isinstance(constraints, list):
        return []
    return [
        (index, constraint)
        for index, constraint in enumerate(constraints)
        if isinstance(constraint, dict) and constraint.get("severity") == severity
    ]


def _extract_episode_reward(episode: dict[str, Any]) -> float:
    summary = episode.get("summary", {})
    if isinstance(summary, dict) and summary.get("return_total") is not None:
        return float(summary["return_total"])
    reward_total = 0.0
    for step in episode.get("steps", []):
        if isinstance(step, dict):
            reward_total += float(step.get("reward_total", 0.0) or 0.0)
    return reward_total


def _episode_has_violation(episode: dict[str, Any]) -> bool:
    summary = episode.get("summary", {})
    if isinstance(summary, dict):
        if bool(summary.get("collision_flag")) or bool(summary.get("out_of_bounds_flag")):
            return True
        if _normalize_done_type(summary.get("done_type", "unknown")) in {2, 3}:
            return True
    for step in episode.get("steps", []):
        if not isinstance(step, dict):
            continue
        if bool(step.get("collision_flag")) or bool(step.get("out_of_bounds_flag")):
            return True
        if _normalize_done_type(step.get("done_type", "unknown")) in {2, 3}:
            return True
    return False


def _rule_d1_hard_constraint_violation_rate(
    constraint_spec: dict[str, Any],
    steps: list[dict[str, Any]],
    create_issue,
) -> list[StaticIssue]:
    issues: list[StaticIssue] = []
    for constraint_index, constraint in _iter_constraints_by_severity(constraint_spec, "hard"):
        constraint_id = str(constraint.get("constraint_id", f"hard_constraint_{constraint_index}"))
        if constraint_id == "collision_avoidance":
            violation_steps = 0
            observed_steps = 0
            for step in steps:
                if "collision_flag" not in step and "done_type" not in step:
                    continue
                observed_steps += 1
                if bool(step.get("collision_flag")) or _normalize_done_type(step.get("done_type", "unknown")) == 2:
                    violation_steps += 1
            if observed_steps == 0:
                issues.append(
                    create_issue(
                        "C-R",
                        "info",
                        "hard_constraint_violation_rate",
                        f"Constraint '{constraint_id}' could not be evaluated because collision fields are missing from step logs.",
                        [
                            f"constraint.constraints[{constraint_index}].indicator_predicate",
                            "log.steps[*].collision_flag",
                            "log.steps[*].done_type",
                        ],
                        {
                            "constraint_id": constraint_id,
                            "missing_fields": ["collision_flag", "done_type"],
                        },
                    )
                )
                continue
            violation_rate = violation_steps / observed_steps
            if violation_rate > 0:
                issues.append(
                    create_issue(
                        "C-R",
                        "warning",
                        "hard_constraint_violation_rate",
                        f"Hard constraint '{constraint_id}' is violated in a non-zero fraction of logged steps.",
                        [
                            f"constraint.constraints[{constraint_index}].indicator_predicate",
                            "log.steps[*].collision_flag",
                            "log.steps[*].done_type",
                        ],
                        {
                            "constraint_id": constraint_id,
                            "violation_rate": violation_rate,
                            "total_steps": observed_steps,
                            "violation_steps": violation_steps,
                        },
                    )
                )
        elif constraint_id == "workspace_boundary":
            violation_steps = 0
            observed_steps = 0
            for step in steps:
                if "out_of_bounds_flag" not in step and "done_type" not in step:
                    continue
                observed_steps += 1
                if bool(step.get("out_of_bounds_flag")) or _normalize_done_type(step.get("done_type", "unknown")) == 3:
                    violation_steps += 1
            if observed_steps == 0:
                issues.append(
                    create_issue(
                        "C-R",
                        "info",
                        "hard_constraint_violation_rate",
                        f"Constraint '{constraint_id}' could not be evaluated because boundary fields are missing from step logs.",
                        [
                            f"constraint.constraints[{constraint_index}].indicator_predicate",
                            "log.steps[*].out_of_bounds_flag",
                            "log.steps[*].done_type",
                        ],
                        {
                            "constraint_id": constraint_id,
                            "missing_fields": ["out_of_bounds_flag", "done_type"],
                        },
                    )
                )
                continue
            violation_rate = violation_steps / observed_steps
            if violation_rate > 0:
                issues.append(
                    create_issue(
                        "C-R",
                        "warning",
                        "hard_constraint_violation_rate",
                        f"Hard constraint '{constraint_id}' is violated in a non-zero fraction of logged steps.",
                        [
                            f"constraint.constraints[{constraint_index}].indicator_predicate",
                            "log.steps[*].out_of_bounds_flag",
                            "log.steps[*].done_type",
                        ],
                        {
                            "constraint_id": constraint_id,
                            "violation_rate": violation_rate,
                            "total_steps": observed_steps,
                            "violation_steps": violation_steps,
                        },
                    )
                )
    return issues


def _rule_d2_soft_constraint_exceedance_rate(
    constraint_spec: dict[str, Any],
    steps: list[dict[str, Any]],
    create_issue,
) -> list[StaticIssue]:
    issues: list[StaticIssue] = []
    for constraint_index, constraint in _iter_constraints_by_severity(constraint_spec, "soft"):
        constraint_id = str(constraint.get("constraint_id", f"soft_constraint_{constraint_index}"))
        threshold = None
        exceedance_steps = 0
        observed_steps = 0
        evidence: dict[str, Any] = {"constraint_id": constraint_id}

        if constraint_id == "safety_margin":
            threshold = 0.50
            for step in steps:
                distance = _get_min_obstacle_distance(step)
                if distance is None:
                    continue
                observed_steps += 1
                if distance < threshold:
                    exceedance_steps += 1
        elif constraint_id == "speed_bound":
            threshold = 2.00
            for step in steps:
                speed = _get_velocity_norm(step)
                if speed is None:
                    continue
                observed_steps += 1
                if speed > threshold:
                    exceedance_steps += 1
        elif constraint_id == "attitude_turn_rate":
            threshold = 1.20
            evidence["partial_coverage"] = True
            for step in steps:
                yaw_rate = _get_yaw_rate(step)
                if yaw_rate is None:
                    continue
                observed_steps += 1
                if abs(yaw_rate) > threshold:
                    exceedance_steps += 1
        else:
            continue

        if observed_steps == 0:
            continue
        exceedance_rate = exceedance_steps / observed_steps
        if exceedance_rate > 0:
            evidence.update(
                {
                    "exceedance_rate": exceedance_rate,
                    "threshold": threshold,
                    "total_steps": observed_steps,
                }
            )
            issues.append(
                create_issue(
                    "C-R",
                    "info",
                    "soft_constraint_exceedance_rate",
                    f"Soft constraint '{constraint_id}' exceeds its dynamic threshold in logged steps.",
                    [
                        f"constraint.constraints[{constraint_index}].indicator_predicate",
                        f"constraint.constraints[{constraint_index}].penalty_weight",
                    ],
                    evidence,
                )
            )
    return issues


def _rule_d3_critical_region_proximity(
    constraint_spec: dict[str, Any],
    steps: list[dict[str, Any]],
    create_issue,
) -> list[StaticIssue]:
    issues: list[StaticIssue] = []
    for constraint_index, constraint in _iter_constraints_by_severity(constraint_spec, "hard"):
        constraint_id = str(constraint.get("constraint_id", f"hard_constraint_{constraint_index}"))
        coverage_threshold_delta = float(constraint.get("coverage_threshold_delta", 0.0) or 0.0)

        if constraint_id == "collision_avoidance":
            observed_steps = 0
            proximity_steps = 0
            for step in steps:
                distance = _get_min_obstacle_distance(step)
                if distance is None:
                    continue
                observed_steps += 1
                if distance < 1.0:
                    proximity_steps += 1
            if observed_steps == 0:
                continue
            proximity_rate = proximity_steps / observed_steps
            if proximity_rate < coverage_threshold_delta:
                issues.append(
                    create_issue(
                        "E-C",
                        "warning",
                        "critical_region_proximity",
                        f"Hard constraint '{constraint_id}' has low critical-region proximity coverage in logged steps.",
                        [
                            f"constraint.constraints[{constraint_index}].coverage_threshold_delta",
                            "log.steps[*].min_obstacle_distance",
                        ],
                        {
                            "constraint_id": constraint_id,
                            "proximity_rate": proximity_rate,
                            "coverage_threshold_delta": coverage_threshold_delta,
                            "total_steps": observed_steps,
                        },
                    )
                )
        elif constraint_id == "workspace_boundary":
            observed_steps = 0
            proximity_steps = 0
            for step in steps:
                if "out_of_bounds_flag" not in step and "done_type" not in step:
                    continue
                observed_steps += 1
                if bool(step.get("out_of_bounds_flag")) or _normalize_done_type(step.get("done_type", "unknown")) == 3:
                    proximity_steps += 1
            if observed_steps == 0:
                continue
            proximity_rate = proximity_steps / observed_steps
            if proximity_rate < coverage_threshold_delta:
                issues.append(
                    create_issue(
                        "E-C",
                        "warning",
                        "critical_region_proximity",
                        f"Hard constraint '{constraint_id}' has low boundary-region coverage in logged steps.",
                        [
                            f"constraint.constraints[{constraint_index}].coverage_threshold_delta",
                            "log.steps[*].out_of_bounds_flag",
                            "log.steps[*].done_type",
                        ],
                        {
                            "constraint_id": constraint_id,
                            "proximity_rate": proximity_rate,
                            "coverage_threshold_delta": coverage_threshold_delta,
                            "total_steps": observed_steps,
                        },
                    )
                )
    return issues


def _rule_d4_reward_violation_correlation(
    episodes: list[dict[str, Any]],
    create_issue,
) -> list[StaticIssue]:
    issues: list[StaticIssue] = []
    total_episodes = len(episodes)
    if total_episodes < 5:
        issues.append(
            create_issue(
                "C-R",
                "info",
                "reward_violation_correlation",
                "Reward-violation correlation was skipped because fewer than 5 episodes are available.",
                ["log.episodes[*].summary.return_total", "log.episodes[*].summary.done_type"],
                {"total_episodes": total_episodes, "sample_insufficient": True},
            )
        )
        return issues

    rewards = [_extract_episode_reward(episode) for episode in episodes]
    median_reward = float(median(rewards))
    correlated_episodes = []
    for episode_index, episode in enumerate(episodes):
        reward_total = _extract_episode_reward(episode)
        if reward_total > median_reward and _episode_has_violation(episode):
            correlated_episodes.append(episode_index)

    if correlated_episodes:
        issues.append(
            create_issue(
                "C-R",
                "warning",
                "reward_violation_correlation",
                "High-reward episodes also exhibit constraint violations, indicating reward-violation coupling.",
                ["log.episodes[*].summary.return_total", "log.episodes[*].summary.collision_flag"],
                {
                    "correlated_episode_count": len(correlated_episodes),
                    "total_episodes": total_episodes,
                    "median_reward": median_reward,
                    "correlated_episode_indices": correlated_episodes,
                },
            )
        )
    return issues


def _rule_d5_missing_field_coverage(create_issue) -> list[StaticIssue]:
    missing_specs = [
        {
            "issue_type": "C-R",
            "description": "Dynamic reward term 'reward_safety_dynamic' cannot be fully recomputed because min_dynamic_obstacle_distance_m is absent from logs.",
            "traceable_fields": ["reward.reward_terms[2].term_expr"],
            "evidence": {
                "missing_field": "min_dynamic_obstacle_distance_m",
                "affected_spec": "reward.reward_terms[2]",
                "handling": "skip reward_safety_dynamic recomputation",
            },
        },
        {
            "issue_type": "C-R",
            "description": "Dynamic reward term 'penalty_smooth' cannot be recomputed from raw actions because action command history is absent from logs.",
            "traceable_fields": ["reward.reward_terms[3].term_expr"],
            "evidence": {
                "missing_field": "action_cmd_world_mps_t / action_cmd_world_mps_t_minus_1",
                "affected_spec": "reward.reward_terms[3]",
                "handling": "use logged reward_components.penalty_smooth proxy only",
            },
        },
        {
            "issue_type": "C-R",
            "description": "Dynamic reward term 'manual_control' cannot be recomputed because manual_override_active is absent from logs.",
            "traceable_fields": ["reward.reward_terms[5].term_expr"],
            "evidence": {
                "missing_field": "manual_override_active",
                "affected_spec": "reward.reward_terms[5]",
                "handling": "use logged reward_components.manual_control proxy only",
            },
        },
        {
            "issue_type": "C-R",
            "description": "Constraint 'workspace_boundary' cannot be fully reconstructed geometrically because workspace_size_x_m and workspace_size_y_m are absent from logs.",
            "traceable_fields": ["constraint.constraints[2].indicator_predicate"],
            "evidence": {
                "missing_field": "workspace_size_x_m / workspace_size_y_m",
                "affected_spec": "constraint.constraints[2]",
                "handling": "use out_of_bounds_flag or done_type proxy",
            },
        },
        {
            "issue_type": "C-R",
            "description": "Constraint 'attitude_turn_rate' has only partial dynamic coverage because body_roll_rad and body_pitch_rad are absent from logs.",
            "traceable_fields": ["constraint.constraints[4].indicator_predicate"],
            "evidence": {
                "missing_field": "body_roll_rad / body_pitch_rad",
                "affected_spec": "constraint.constraints[4]",
                "handling": "detect yaw-rate branch only",
                "partial_coverage": True,
            },
        },
    ]
    return [
        create_issue(
            spec["issue_type"],
            "info",
            "missing_field_coverage",
            spec["description"],
            spec["traceable_fields"],
            spec["evidence"],
        )
        for spec in missing_specs
    ]


def _build_summary(
    issues: list[StaticIssue],
    *,
    episode_count: int,
    total_steps: int,
    no_episodes: bool,
) -> dict[str, Any]:
    by_type = {issue_type: 0 for issue_type in ISSUE_TYPES}
    by_severity = {severity: 0 for severity in SEVERITIES}
    for issue in issues:
        by_type[issue.issue_type] = by_type.get(issue.issue_type, 0) + 1
        by_severity[issue.severity] = by_severity.get(issue.severity, 0) + 1
    return {
        "total": len(issues),
        "by_type": by_type,
        "by_severity": by_severity,
        "episode_count": episode_count,
        "total_steps": total_steps,
        "no_episodes": no_episodes,
    }


def _write_report(report: DynamicReport, output_dir: str | None) -> DynamicReport:
    if output_dir is None:
        return report
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / "dynamic_report.json"
    report.output_path = str(output_path)
    output_path.write_text(json.dumps(asdict(report), indent=2, sort_keys=True), encoding="utf-8")
    return report


def run_dynamic_analysis(
    static_report: StaticReport,
    log_dir: str,
    reward_spec_path: str,
    constraint_spec_path: str,
    output_dir: str | None = None,
) -> DynamicReport:
    episodes = _load_log_dir(log_dir)
    if not episodes:
        report = DynamicReport(
            spec_versions=dict(static_report.spec_versions),
            episode_count=0,
            issues=[],
            summary=_build_summary([], episode_count=0, total_steps=0, no_episodes=True),
            output_path=None,
        )
        return _write_report(report, output_dir)

    reward_spec = _load_yaml_file(reward_spec_path)
    constraint_spec = _load_yaml_file(constraint_spec_path)
    steps = _all_steps(episodes)
    create_issue = _make_issue_factory()

    issues: list[StaticIssue] = []
    issues.extend(_rule_d1_hard_constraint_violation_rate(constraint_spec, steps, create_issue))
    issues.extend(_rule_d2_soft_constraint_exceedance_rate(constraint_spec, steps, create_issue))
    issues.extend(_rule_d3_critical_region_proximity(constraint_spec, steps, create_issue))
    issues.extend(_rule_d4_reward_violation_correlation(episodes, create_issue))
    issues.extend(_rule_d5_missing_field_coverage(create_issue))

    spec_versions = dict(static_report.spec_versions)
    spec_versions.update(
        {
            "reward": str(reward_spec.get("spec_version", "")),
            "constraint": str(constraint_spec.get("spec_version", "")),
        }
    )
    report = DynamicReport(
        spec_versions=spec_versions,
        episode_count=len(episodes),
        issues=issues,
        summary=_build_summary(
            issues,
            episode_count=len(episodes),
            total_steps=len(steps),
            no_episodes=False,
        ),
        output_path=None,
    )
    return _write_report(report, output_dir)
