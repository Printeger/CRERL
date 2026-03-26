"""Deterministic dynamic witness kernels for rollout-based CRE analysis."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return float(default)
    return float(value)


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _weighted_average(weighted_values: Sequence[tuple[float, float]]) -> float:
    total_weight = 0.0
    weighted_sum = 0.0
    for weight, value in weighted_values:
        if weight <= 0.0:
            continue
        total_weight += float(weight)
        weighted_sum += float(weight) * float(value)
    if total_weight <= 0.0:
        return 0.0
    return _clamp01(weighted_sum / total_weight)


def _score_from_threshold(value: float, low: float, high: float) -> float:
    if high <= low:
        return _clamp01(float(value))
    return _clamp01((float(value) - float(low)) / (float(high) - float(low)))


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0
    x_mean = _mean(xs)
    y_mean = _mean(ys)
    num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - x_mean) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - y_mean) ** 2 for y in ys))
    if den_x <= 1e-9 or den_y <= 1e-9:
        return 0.0
    return float(num / (den_x * den_y))


def _run_ids(run_payloads: Sequence[Mapping[str, Any]]) -> List[str]:
    return [str(item.get("run_id") or item.get("run_dir", "")) for item in run_payloads]


def _flatten_steps(run_payloads: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    steps: List[Mapping[str, Any]] = []
    for payload in run_payloads:
        steps.extend(payload.get("steps", []) or [])
    return steps


def _flatten_episodes(run_payloads: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    episodes: List[Mapping[str, Any]] = []
    for payload in run_payloads:
        episodes.extend(payload.get("episodes", []) or [])
    return episodes


def _collect_summary_metric(run_payloads: Sequence[Mapping[str, Any]], key: str) -> float:
    values: List[float] = []
    for payload in run_payloads:
        summary = payload.get("summary") or {}
        value = summary.get(key)
        if value is not None:
            values.append(float(value))
    return _mean(values)


def _collect_scene_families(run_payloads: Sequence[Mapping[str, Any]]) -> List[str]:
    families: List[str] = []
    for episode in _flatten_episodes(run_payloads):
        scenario_type = episode.get("scenario_type")
        if scenario_type not in (None, ""):
            families.append(str(scenario_type))
    return sorted(set(families))


def _group_episodes_by_family(run_payloads: Sequence[Mapping[str, Any]]) -> Dict[str, List[Mapping[str, Any]]]:
    grouped: Dict[str, List[Mapping[str, Any]]] = {}
    for episode in _flatten_episodes(run_payloads):
        family = str(episode.get("scenario_type", "unknown"))
        grouped.setdefault(family, []).append(episode)
    return grouped


def _family_summary(episodes: Sequence[Mapping[str, Any]]) -> Dict[str, float]:
    if not episodes:
        return {
            "episode_count": 0.0,
            "success_rate": 0.0,
            "collision_rate": 0.0,
            "near_violation_ratio": 0.0,
            "min_distance": 0.0,
            "average_return": 0.0,
        }
    min_distances = [
        float(item["min_obstacle_distance"])
        for item in episodes
        if item.get("min_obstacle_distance") is not None
    ]
    return {
        "episode_count": float(len(episodes)),
        "success_rate": sum(bool(item.get("success_flag")) for item in episodes) / len(episodes),
        "collision_rate": sum(bool(item.get("collision_flag")) for item in episodes) / len(episodes),
        "near_violation_ratio": _mean([
            float(item.get("near_violation_ratio", 0.0) or 0.0)
            for item in episodes
        ]),
        "min_distance": min(min_distances) if min_distances else 0.0,
        "average_return": _mean([
            float(item.get("return_total", 0.0) or 0.0)
            for item in episodes
        ]),
    }


def _resolve_expected_scene_families(spec_ir: Any) -> List[str]:
    if spec_ir is None:
        return []
    return sorted(str(key) for key in getattr(spec_ir, "environment_families", {}).keys())


def _resolve_expected_dynamic_families(spec_ir: Any) -> List[str]:
    if spec_ir is None:
        return []
    dynamic_families: List[str] = []
    for family_name, family_spec in getattr(spec_ir, "environment_families", {}).items():
        dynamic_cfg = getattr(family_spec, "dynamic_obstacles", {}) or {}
        if bool(dynamic_cfg.get("enabled", False)):
            dynamic_families.append(str(family_name))
    return sorted(dynamic_families)


def _infer_dynamic_episode(episode: Mapping[str, Any]) -> bool:
    tags = episode.get("scene_tags") or {}
    for key in ("dynamic_obstacles_enabled", "has_dynamic_obstacles"):
        if bool(tags.get(key)):
            return True
    if _safe_float(tags.get("dynamic_obstacle_count"), 0.0) > 0.0:
        return True
    return False


def _severity_from_score(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.50:
        return "medium"
    if score >= 0.25:
        return "warning"
    return "info"


@dataclass
class DynamicMetricResult:
    """Structured result for one dynamic metric."""

    metric_id: str
    value: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DynamicWitnessResult:
    """Structured result for one witness family."""

    witness_id: str
    score: float
    severity: str
    summary: str
    metrics: List[DynamicMetricResult] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "witness_id": self.witness_id,
            "score": float(self.score),
            "severity": str(self.severity),
            "summary": str(self.summary),
            "metrics": [
                {
                    "metric_id": item.metric_id,
                    "value": float(item.value),
                    "details": dict(item.details),
                }
                for item in self.metrics
            ],
            "details": dict(self.details),
        }


def compute_reward_violation_coupling(
    run_payloads: Sequence[Mapping[str, Any]],
    *,
    detector_thresholds: Optional[Mapping[str, Any]] = None,
    witness_weights: Optional[Mapping[str, Any]] = None,
) -> DynamicWitnessResult:
    thresholds = dict(detector_thresholds or {})
    weights = dict(witness_weights or {})
    near_violation_distance = float(thresholds.get("near_violation_distance", 0.6))

    steps = _flatten_steps(run_payloads)
    episodes = _flatten_episodes(run_payloads)

    near_steps = [
        step for step in steps
        if bool(step.get("near_violation_flag"))
        or (
            step.get("min_obstacle_distance") is not None
            and float(step["min_obstacle_distance"]) < near_violation_distance
        )
    ]
    positive_steps = [
        step for step in steps
        if float(step.get("reward_total", 0.0) or 0.0) > 0.0
    ]
    positive_near_steps = [
        step for step in near_steps
        if float(step.get("reward_total", 0.0) or 0.0) > 0.0
    ]

    positive_reward_total = sum(max(0.0, float(step.get("reward_total", 0.0) or 0.0)) for step in steps)
    near_positive_reward_total = sum(
        max(0.0, float(step.get("reward_total", 0.0) or 0.0)) for step in near_steps
    )

    clearance_samples = [
        float(step["min_obstacle_distance"])
        for step in steps
        if step.get("min_obstacle_distance") is not None
    ]
    reward_samples = [
        float(step.get("reward_total", 0.0) or 0.0)
        for step in steps
        if step.get("min_obstacle_distance") is not None
    ]
    clearance_reward_corr = _pearson(clearance_samples, reward_samples)
    negative_clearance_reward_corr = _clamp01(max(0.0, -clearance_reward_corr))

    hazardous_episodes = [
        episode for episode in episodes
        if bool(episode.get("collision_flag")) or bool(episode.get("out_of_bounds_flag"))
    ]
    overall_mean_return = _mean([
        float(episode.get("return_total", 0.0) or 0.0)
        for episode in episodes
    ])
    hazardous_mean_return = _mean([
        float(episode.get("return_total", 0.0) or 0.0)
        for episode in hazardous_episodes
    ])
    hazardous_terminal_return_ratio = _clamp01(
        hazardous_mean_return / max(abs(overall_mean_return), 1.0)
    ) if hazardous_episodes else 0.0

    near_violation_step_ratio = _clamp01(len(near_steps) / max(len(steps), 1))
    positive_reward_near_ratio = _clamp01(len(positive_near_steps) / max(len(positive_steps), 1))
    reward_concentration_ratio = _clamp01(
        near_positive_reward_total / max(positive_reward_total, 1e-6)
    )
    mean_reward = _mean([
        float(step.get("reward_total", 0.0) or 0.0) for step in steps
    ])
    proximity_pressure = _mean([
        _clamp01(
            max(0.0, near_violation_distance - float(step["min_obstacle_distance"]))
            / max(near_violation_distance, 1e-6)
        )
        for step in steps
        if step.get("min_obstacle_distance") is not None
    ])
    proximity_reward_alignment = _mean([
        _clamp01(
            max(0.0, float(step.get("reward_total", 0.0) or 0.0))
            / max(abs(mean_reward), 1.0)
        ) * _clamp01(
            max(0.0, near_violation_distance - float(step["min_obstacle_distance"]))
            / max(near_violation_distance, 1e-6)
        )
        for step in steps
        if step.get("min_obstacle_distance") is not None
    ])
    high_return_hazard_ratio = _clamp01(
        sum(
            1
            for episode in hazardous_episodes
            if float(episode.get("return_total", 0.0) or 0.0) >= overall_mean_return
        ) / max(len(hazardous_episodes), 1)
    ) if hazardous_episodes else 0.0

    score = _weighted_average(
        (
            (float(weights.get("constraint_reward", 1.0)), reward_concentration_ratio),
            (float(weights.get("near_violation", 0.5)), positive_reward_near_ratio),
            (float(weights.get("constraint_reward", 1.0)), negative_clearance_reward_corr),
            (float(weights.get("near_violation", 0.5)), near_violation_step_ratio),
            (float(weights.get("collision", 2.0)), hazardous_terminal_return_ratio),
            (float(weights.get("constraint_reward", 1.0)), proximity_reward_alignment),
            (float(weights.get("collision", 2.0)), high_return_hazard_ratio),
        )
    )
    severity = _severity_from_score(score)

    return DynamicWitnessResult(
        witness_id="W_CR",
        score=score,
        severity=severity,
        summary=(
            "Reward-boundary coupling is elevated."
            if score >= 0.50
            else "Reward-boundary coupling is limited."
        ),
        metrics=[
            DynamicMetricResult("near_violation_step_ratio", near_violation_step_ratio),
            DynamicMetricResult("positive_reward_near_ratio", positive_reward_near_ratio),
            DynamicMetricResult("reward_concentration_ratio", reward_concentration_ratio),
            DynamicMetricResult(
                "negative_clearance_reward_corr",
                negative_clearance_reward_corr,
                details={"raw_corr": clearance_reward_corr},
            ),
            DynamicMetricResult(
                "hazardous_terminal_return_ratio",
                hazardous_terminal_return_ratio,
                details={
                    "hazardous_episode_count": len(hazardous_episodes),
                    "hazardous_mean_return": hazardous_mean_return,
                    "overall_mean_return": overall_mean_return,
                },
            ),
            DynamicMetricResult("proximity_pressure", proximity_pressure),
            DynamicMetricResult("proximity_reward_alignment", proximity_reward_alignment),
            DynamicMetricResult("high_return_hazard_ratio", high_return_hazard_ratio),
        ],
        details={
            "primary_run_ids": _run_ids(run_payloads),
            "step_count": len(steps),
            "episode_count": len(episodes),
            "near_violation_distance": near_violation_distance,
            "mean_reward": mean_reward,
        },
    )


def compute_critical_state_coverage(
    run_payloads: Sequence[Mapping[str, Any]],
    *,
    spec_ir: Any = None,
    detector_thresholds: Optional[Mapping[str, Any]] = None,
    witness_weights: Optional[Mapping[str, Any]] = None,
) -> DynamicWitnessResult:
    del witness_weights  # reserved for future tuning
    thresholds = dict(detector_thresholds or {})
    collision_distance = float(thresholds.get("collision_distance", 0.3))
    near_violation_distance = float(thresholds.get("near_violation_distance", 0.6))

    steps = _flatten_steps(run_payloads)
    episodes = _flatten_episodes(run_payloads)
    expected_families = _resolve_expected_scene_families(spec_ir)
    observed_families = _collect_scene_families(run_payloads)
    expected_dynamic_families = _resolve_expected_dynamic_families(spec_ir)

    family_coverage_ratio = _clamp01(
        len(set(observed_families) & set(expected_families)) / max(len(expected_families), 1)
    ) if expected_families else 1.0

    distances = [
        float(step["min_obstacle_distance"])
        for step in steps
        if step.get("min_obstacle_distance") is not None
    ]
    visited_bands = {
        "collision_band": any(distance <= collision_distance for distance in distances),
        "near_violation_band": any(
            collision_distance < distance <= near_violation_distance for distance in distances
        ),
        "caution_band": any(
            near_violation_distance < distance <= (2.0 * near_violation_distance)
            for distance in distances
        ),
    }
    critical_band_coverage_ratio = _clamp01(
        sum(int(value) for value in visited_bands.values()) / len(visited_bands)
    )

    near_violation_steps = [
        step for step in steps
        if bool(step.get("near_violation_flag"))
        or (
            step.get("min_obstacle_distance") is not None
            and float(step["min_obstacle_distance"]) < near_violation_distance
        )
    ]
    near_violation_step_ratio = _clamp01(len(near_violation_steps) / max(len(steps), 1))
    critical_exposure_ratio = _clamp01(near_violation_step_ratio / 0.05)
    family_episodes = _group_episodes_by_family(run_payloads)
    family_failure_summary = {
        family_name: _family_summary(family_eps)
        for family_name, family_eps in sorted(family_episodes.items())
    }
    family_failure_pressure = _mean([
        _clamp01(summary["collision_rate"] + summary["near_violation_ratio"])
        for summary in family_failure_summary.values()
    ])

    observed_dynamic_families = sorted({
        str(episode.get("scenario_type"))
        for episode in episodes
        if _infer_dynamic_episode(episode)
    })
    if expected_dynamic_families:
        dynamic_hazard_coverage_ratio = _clamp01(
            len(set(observed_dynamic_families) & set(expected_dynamic_families))
            / max(len(expected_dynamic_families), 1)
        )
    else:
        dynamic_hazard_coverage_ratio = 1.0

    coverage_quality = _weighted_average(
        (
            (1.0, family_coverage_ratio),
            (1.0, critical_band_coverage_ratio),
            (1.0, critical_exposure_ratio),
            (1.0, dynamic_hazard_coverage_ratio),
        )
    )
    score = _clamp01((1.0 - coverage_quality) * 0.8 + family_failure_pressure * 0.2)
    severity = _severity_from_score(score)

    return DynamicWitnessResult(
        witness_id="W_EC",
        score=score,
        severity=severity,
        summary=(
            "Critical-state coverage appears weak."
            if score >= 0.50
            else "Critical-state coverage appears acceptable."
        ),
        metrics=[
            DynamicMetricResult("family_coverage_ratio", family_coverage_ratio),
            DynamicMetricResult("critical_band_coverage_ratio", critical_band_coverage_ratio),
            DynamicMetricResult("critical_exposure_ratio", critical_exposure_ratio),
            DynamicMetricResult("dynamic_hazard_coverage_ratio", dynamic_hazard_coverage_ratio),
            DynamicMetricResult("family_failure_pressure", family_failure_pressure),
        ],
        details={
            "primary_run_ids": _run_ids(run_payloads),
            "expected_families": expected_families,
            "observed_families": observed_families,
            "expected_dynamic_families": expected_dynamic_families,
            "observed_dynamic_families": observed_dynamic_families,
            "visited_bands": visited_bands,
            "step_count": len(steps),
            "episode_count": len(episodes),
            "family_failure_summary": family_failure_summary,
        },
    )


def _infer_transfer_groups(
    run_payloads: Sequence[Mapping[str, Any]],
) -> tuple[List[Mapping[str, Any]], List[Mapping[str, Any]]]:
    primary: List[Mapping[str, Any]] = []
    shifted: List[Mapping[str, Any]] = []
    for payload in run_payloads:
        scenarios = set(_collect_scene_families([payload]))
        if "shifted" in scenarios:
            shifted.append(payload)
        elif "nominal" in scenarios:
            primary.append(payload)
    return primary, shifted


def compute_transfer_fragility(
    run_payloads: Sequence[Mapping[str, Any]],
    *,
    comparison_run_payloads: Optional[Sequence[Mapping[str, Any]]] = None,
    detector_thresholds: Optional[Mapping[str, Any]] = None,
    witness_weights: Optional[Mapping[str, Any]] = None,
) -> DynamicWitnessResult:
    thresholds = dict(detector_thresholds or {})
    weights = dict(witness_weights or {})
    near_violation_distance = float(thresholds.get("near_violation_distance", 0.6))

    baseline_runs = list(run_payloads)
    compare_runs = list(comparison_run_payloads or [])
    auto_inferred = False
    if not compare_runs:
        baseline_runs, compare_runs = _infer_transfer_groups(run_payloads)
        auto_inferred = bool(compare_runs)
    if not baseline_runs:
        baseline_runs = list(run_payloads)

    baseline_success = _collect_summary_metric(baseline_runs, "success_rate")
    shifted_success = _collect_summary_metric(compare_runs, "success_rate")
    baseline_collision = _collect_summary_metric(baseline_runs, "collision_rate")
    shifted_collision = _collect_summary_metric(compare_runs, "collision_rate")
    baseline_near = _collect_summary_metric(baseline_runs, "near_violation_ratio")
    shifted_near = _collect_summary_metric(compare_runs, "near_violation_ratio")
    baseline_return = _collect_summary_metric(baseline_runs, "average_return")
    shifted_return = _collect_summary_metric(compare_runs, "average_return")
    baseline_min_distance = _collect_summary_metric(baseline_runs, "min_distance")
    shifted_min_distance = _collect_summary_metric(compare_runs, "min_distance")

    if compare_runs:
        success_gap = _clamp01(max(0.0, baseline_success - shifted_success))
        collision_gap = _clamp01(max(0.0, shifted_collision - baseline_collision))
        near_violation_gap = _clamp01(max(0.0, shifted_near - baseline_near))
        min_distance_gap = _clamp01(
            max(0.0, baseline_min_distance - shifted_min_distance)
            / max(baseline_min_distance, near_violation_distance, 1e-6)
        )
        average_return_gap = _clamp01(
            max(0.0, baseline_return - shifted_return)
            / max(abs(baseline_return), 1.0)
        )
    else:
        success_gap = 0.0
        collision_gap = 0.0
        near_violation_gap = 0.0
        min_distance_gap = 0.0
        average_return_gap = 0.0

    baseline_family_summary = {
        family_name: _family_summary(family_eps)
        for family_name, family_eps in sorted(_group_episodes_by_family(baseline_runs).items())
    }
    comparison_family_summary = {
        family_name: _family_summary(family_eps)
        for family_name, family_eps in sorted(_group_episodes_by_family(compare_runs).items())
    }
    baseline_families = set(baseline_family_summary.keys())
    comparison_families = set(comparison_family_summary.keys())
    family_shift_gap = _clamp01(1.0 if compare_runs and baseline_families != comparison_families else 0.0)

    source_pair_shift = _clamp01(
        max(0.0, collision_gap + near_violation_gap + min_distance_gap + average_return_gap) / 4.0
    ) if compare_runs else 0.0

    score = _weighted_average(
        (
            (float(weights.get("environment_reward", 1.0)), success_gap),
            (float(weights.get("environment_constraint", 1.0)), collision_gap),
            (float(weights.get("environment_constraint", 1.0)), near_violation_gap),
            (float(weights.get("environment_constraint", 1.0)), min_distance_gap),
            (float(weights.get("environment_reward", 1.0)), average_return_gap),
            (float(weights.get("environment_reward", 1.0)), source_pair_shift),
            (float(weights.get("environment_reward", 1.0)), family_shift_gap),
        )
    )
    severity = _severity_from_score(score)
    if compare_runs:
        summary = (
            "Transfer fragility under environment shift is elevated."
            if score >= 0.50
            else "Transfer fragility under environment shift is limited."
        )
    else:
        summary = "No comparison run group was available for transfer-fragility analysis."

    return DynamicWitnessResult(
        witness_id="W_ER",
        score=score,
        severity=severity,
        summary=summary,
        metrics=[
            DynamicMetricResult("success_rate_gap", success_gap),
            DynamicMetricResult("collision_rate_gap", collision_gap),
            DynamicMetricResult("near_violation_ratio_gap", near_violation_gap),
            DynamicMetricResult("min_distance_gap", min_distance_gap),
            DynamicMetricResult("average_return_gap", average_return_gap),
            DynamicMetricResult("source_pair_shift", source_pair_shift),
            DynamicMetricResult("family_shift_gap", family_shift_gap),
        ],
        details={
            "primary_run_ids": _run_ids(baseline_runs),
            "comparison_run_ids": _run_ids(compare_runs),
            "auto_inferred_comparison": auto_inferred,
            "baseline_summary": {
                "success_rate": baseline_success,
                "collision_rate": baseline_collision,
                "near_violation_ratio": baseline_near,
                "average_return": baseline_return,
                "min_distance": baseline_min_distance,
            },
            "comparison_summary": {
                "success_rate": shifted_success,
                "collision_rate": shifted_collision,
                "near_violation_ratio": shifted_near,
                "average_return": shifted_return,
                "min_distance": shifted_min_distance,
            },
            "baseline_families": sorted(baseline_families),
            "comparison_families": sorted(comparison_families),
            "baseline_family_summary": baseline_family_summary,
            "comparison_family_summary": comparison_family_summary,
        },
    )


def compute_dynamic_metrics(
    run_payloads: Sequence[Mapping[str, Any]],
    *,
    comparison_run_payloads: Optional[Sequence[Mapping[str, Any]]] = None,
    spec_ir: Any = None,
    detector_thresholds: Optional[Mapping[str, Any]] = None,
    witness_weights: Optional[Mapping[str, Any]] = None,
) -> List[DynamicWitnessResult]:
    thresholds = dict(detector_thresholds or {})
    weights = dict(witness_weights or {})
    return [
        compute_reward_violation_coupling(
            run_payloads,
            detector_thresholds=thresholds,
            witness_weights=weights,
        ),
        compute_critical_state_coverage(
            run_payloads,
            spec_ir=spec_ir,
            detector_thresholds=thresholds,
            witness_weights=weights,
        ),
        compute_transfer_fragility(
            run_payloads,
            comparison_run_payloads=comparison_run_payloads,
            detector_thresholds=thresholds,
            witness_weights=weights,
        ),
    ]


__all__ = [
    "DynamicMetricResult",
    "DynamicWitnessResult",
    "compute_critical_state_coverage",
    "compute_dynamic_metrics",
    "compute_reward_violation_coupling",
    "compute_transfer_fragility",
]
