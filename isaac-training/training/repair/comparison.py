"""Phase 9 original-vs-repaired metric comparison helpers."""

from __future__ import annotations

from statistics import mean
from typing import Any, Dict, Iterable, List, Mapping, Sequence


METRIC_DIRECTIONS = {
    "W_CR": "lower_better",
    "W_EC": "lower_better",
    "W_ER": "lower_better",
    "boundary_critical_success_rate": "higher_better",
    "boundary_critical_collision_rate": "lower_better",
    "boundary_critical_near_violation_ratio": "lower_better",
    "boundary_critical_vs_nominal_success_gap": "lower_better",
    "boundary_critical_vs_nominal_min_distance_gap": "lower_better",
    "collision_rate": "lower_better",
    "critical_family_min_distance": "higher_better",
    "near_violation_ratio": "lower_better",
    "min_distance": "higher_better",
    "nominal_vs_shifted_collision_gap": "lower_better",
    "nominal_vs_shifted_min_distance_gap": "lower_better",
    "nominal_vs_shifted_near_violation_gap": "lower_better",
    "nominal_vs_shifted_return_gap": "lower_better",
    "nominal_vs_shifted_success_gap": "lower_better",
    "average_return": "higher_better",
    "shifted_min_distance": "higher_better",
    "success_rate": "higher_better",
}

CLAIM_TO_CONSISTENCY_METRICS = {
    "C-R": ("W_CR",),
    "E-C": ("W_EC",),
    "E-R": ("W_ER",),
}

SAFETY_METRICS = ("collision_rate", "near_violation_ratio", "min_distance")
PERFORMANCE_METRICS = ("average_return", "success_rate")

TARGET_METRIC_ALIASES = {
    "boundary_critical_success_rate": "success_rate",
    "boundary_critical_collision_rate": "collision_rate",
    "boundary_critical_near_violation_ratio": "near_violation_ratio",
    "critical_family_min_distance": "min_distance",
    "shifted_min_distance": "min_distance",
}

HIGHER_ORDER_METRICS_BY_CLAIM = {
    "C-R": (),
    "E-C": (
        "boundary_critical_success_rate",
        "boundary_critical_collision_rate",
        "boundary_critical_near_violation_ratio",
        "boundary_critical_vs_nominal_success_gap",
        "boundary_critical_vs_nominal_min_distance_gap",
        "critical_family_min_distance",
    ),
    "E-R": (
        "shifted_min_distance",
        "nominal_vs_shifted_success_gap",
        "nominal_vs_shifted_min_distance_gap",
        "nominal_vs_shifted_collision_gap",
        "nominal_vs_shifted_near_violation_gap",
        "nominal_vs_shifted_return_gap",
    ),
}


def _mean_numeric(values: Iterable[Any]) -> float | None:
    numeric: List[float] = []
    for value in values:
        if value is None:
            continue
        try:
            numeric.append(float(value))
        except Exception:
            continue
    if not numeric:
        return None
    return float(mean(numeric))


def _aggregate_run_summaries(run_payloads: Sequence[Mapping[str, Any]]) -> Dict[str, float]:
    metrics = sorted(
        {
            key
            for payload in run_payloads
            for key, value in dict(payload.get("summary") or {}).items()
            if isinstance(value, (int, float))
        }
    )
    aggregated: Dict[str, float] = {}
    for metric in metrics:
        value = _mean_numeric((dict(payload.get("summary") or {}).get(metric) for payload in run_payloads))
        if value is not None:
            aggregated[metric] = value
    return aggregated


def _extract_run_scenario_type(run_payload: Mapping[str, Any]) -> str:
    episodes = list(run_payload.get("episodes") or [])
    for episode in episodes:
        scenario_type = str(episode.get("scenario_type", "") or "")
        if scenario_type:
            return scenario_type
    summary = dict(run_payload.get("summary") or {})
    scenario_type = str(summary.get("scenario_type", "") or "")
    if scenario_type:
        return scenario_type
    return ""


def _aggregate_by_scenario(run_payloads: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, float]]:
    grouped: Dict[str, List[Mapping[str, Any]]] = {}
    for payload in run_payloads:
        scenario_type = _extract_run_scenario_type(payload)
        if not scenario_type:
            continue
        grouped.setdefault(scenario_type, []).append(payload)
    return {
        scenario_type: _aggregate_run_summaries(group_payloads)
        for scenario_type, group_payloads in grouped.items()
    }


def _aggregate_by_source(run_payloads: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, float]]:
    grouped: Dict[str, List[Mapping[str, Any]]] = {}
    for payload in run_payloads:
        manifest = dict(payload.get("manifest") or {})
        source = str(manifest.get("source", "") or "")
        if not source:
            episodes = list(payload.get("episodes") or [])
            source = next((str(item.get("source", "") or "") for item in episodes if item.get("source")), "")
        if not source:
            continue
        grouped.setdefault(source, []).append(payload)
    return {
        source: _aggregate_run_summaries(group_payloads)
        for source, group_payloads in grouped.items()
    }


def _mean_metric_from_scenarios(
    scenario_summaries: Mapping[str, Mapping[str, Any]],
    *,
    scenario_names: Sequence[str],
    metric_name: str,
) -> float | None:
    values = []
    for scenario_name in scenario_names:
        scenario_summary = dict(scenario_summaries.get(scenario_name) or {})
        if metric_name in scenario_summary:
            values.append(scenario_summary[metric_name])
    return _mean_numeric(values)


def _derive_metric_value(
    metric_name: str,
    *,
    overall_summary: Mapping[str, Any],
    scenario_summaries: Mapping[str, Mapping[str, Any]],
) -> tuple[float | None, str]:
    if metric_name in overall_summary:
        return float(overall_summary[metric_name]), metric_name

    alias_name = TARGET_METRIC_ALIASES.get(metric_name)
    if metric_name == "boundary_critical_success_rate":
        value = _mean_metric_from_scenarios(
            scenario_summaries,
            scenario_names=("boundary_critical",),
            metric_name="success_rate",
        )
        return (float(value), "boundary_critical.success_rate") if value is not None else (None, "")

    if metric_name == "boundary_critical_collision_rate":
        value = _mean_metric_from_scenarios(
            scenario_summaries,
            scenario_names=("boundary_critical",),
            metric_name="collision_rate",
        )
        return (float(value), "boundary_critical.collision_rate") if value is not None else (None, "")

    if metric_name == "boundary_critical_near_violation_ratio":
        value = _mean_metric_from_scenarios(
            scenario_summaries,
            scenario_names=("boundary_critical",),
            metric_name="near_violation_ratio",
        )
        return (
            (float(value), "boundary_critical.near_violation_ratio") if value is not None else (None, "")
        )

    if metric_name == "critical_family_min_distance":
        critical_scenarios = tuple(
            sorted(name for name in scenario_summaries.keys() if name and name != "nominal")
        )
        value = _mean_metric_from_scenarios(
            scenario_summaries,
            scenario_names=critical_scenarios,
            metric_name="min_distance",
        )
        if value is None and alias_name and alias_name in overall_summary:
            return float(overall_summary[alias_name]), alias_name
        source_name = ",".join(f"{name}.min_distance" for name in critical_scenarios) or alias_name or ""
        return (float(value), source_name) if value is not None else (None, "")

    if metric_name == "shifted_min_distance":
        value = _mean_metric_from_scenarios(
            scenario_summaries,
            scenario_names=("shifted",),
            metric_name="min_distance",
        )
        if value is None and alias_name and alias_name in overall_summary:
            return float(overall_summary[alias_name]), alias_name
        return (float(value), "shifted.min_distance") if value is not None else (None, "")

    if metric_name == "nominal_vs_shifted_success_gap":
        nominal = _mean_metric_from_scenarios(
            scenario_summaries,
            scenario_names=("nominal",),
            metric_name="success_rate",
        )
        shifted = _mean_metric_from_scenarios(
            scenario_summaries,
            scenario_names=("shifted",),
            metric_name="success_rate",
        )
        if nominal is None or shifted is None:
            return None, ""
        return abs(float(nominal) - float(shifted)), "abs(nominal.success_rate-shifted.success_rate)"

    if metric_name == "nominal_vs_shifted_min_distance_gap":
        nominal = _mean_metric_from_scenarios(
            scenario_summaries,
            scenario_names=("nominal",),
            metric_name="min_distance",
        )
        shifted = _mean_metric_from_scenarios(
            scenario_summaries,
            scenario_names=("shifted",),
            metric_name="min_distance",
        )
        if nominal is None or shifted is None:
            return None, ""
        return abs(float(nominal) - float(shifted)), "abs(nominal.min_distance-shifted.min_distance)"

    if metric_name == "nominal_vs_shifted_collision_gap":
        nominal = _mean_metric_from_scenarios(
            scenario_summaries,
            scenario_names=("nominal",),
            metric_name="collision_rate",
        )
        shifted = _mean_metric_from_scenarios(
            scenario_summaries,
            scenario_names=("shifted",),
            metric_name="collision_rate",
        )
        if nominal is None or shifted is None:
            return None, ""
        return abs(float(nominal) - float(shifted)), "abs(nominal.collision_rate-shifted.collision_rate)"

    if metric_name == "nominal_vs_shifted_near_violation_gap":
        nominal = _mean_metric_from_scenarios(
            scenario_summaries,
            scenario_names=("nominal",),
            metric_name="near_violation_ratio",
        )
        shifted = _mean_metric_from_scenarios(
            scenario_summaries,
            scenario_names=("shifted",),
            metric_name="near_violation_ratio",
        )
        if nominal is None or shifted is None:
            return None, ""
        return (
            abs(float(nominal) - float(shifted)),
            "abs(nominal.near_violation_ratio-shifted.near_violation_ratio)",
        )

    if metric_name == "nominal_vs_shifted_return_gap":
        nominal = _mean_metric_from_scenarios(
            scenario_summaries,
            scenario_names=("nominal",),
            metric_name="average_return",
        )
        shifted = _mean_metric_from_scenarios(
            scenario_summaries,
            scenario_names=("shifted",),
            metric_name="average_return",
        )
        if nominal is None or shifted is None:
            return None, ""
        return abs(float(nominal) - float(shifted)), "abs(nominal.average_return-shifted.average_return)"

    if metric_name == "boundary_critical_vs_nominal_success_gap":
        nominal = _mean_metric_from_scenarios(
            scenario_summaries,
            scenario_names=("nominal",),
            metric_name="success_rate",
        )
        boundary = _mean_metric_from_scenarios(
            scenario_summaries,
            scenario_names=("boundary_critical",),
            metric_name="success_rate",
        )
        if nominal is None or boundary is None:
            return None, ""
        return abs(float(boundary) - float(nominal)), "abs(boundary_critical.success_rate-nominal.success_rate)"

    if metric_name == "boundary_critical_vs_nominal_min_distance_gap":
        nominal = _mean_metric_from_scenarios(
            scenario_summaries,
            scenario_names=("nominal",),
            metric_name="min_distance",
        )
        boundary = _mean_metric_from_scenarios(
            scenario_summaries,
            scenario_names=("boundary_critical",),
            metric_name="min_distance",
        )
        if nominal is None or boundary is None:
            return None, ""
        return abs(float(boundary) - float(nominal)), "abs(boundary_critical.min_distance-nominal.min_distance)"

    if alias_name and alias_name in overall_summary:
        return float(overall_summary[alias_name]), alias_name
    return None, ""


def _metric_category(metric_name: str, primary_claim_type: str) -> str:
    if metric_name in CLAIM_TO_CONSISTENCY_METRICS.get(primary_claim_type, ()):
        return "consistency"
    if metric_name in SAFETY_METRICS:
        return "safety"
    if metric_name in PERFORMANCE_METRICS:
        return "performance"
    return "auxiliary"


def _metric_improvement(metric_name: str, original: float, repaired: float) -> tuple[str, float]:
    direction = METRIC_DIRECTIONS.get(metric_name, "higher_better")
    delta_raw = float(repaired) - float(original)
    improvement = delta_raw if direction == "higher_better" else -delta_raw
    return direction, improvement


def compare_validation_runs(
    *,
    primary_claim_type: str,
    validation_targets: Sequence[str],
    original_runs: Sequence[Mapping[str, Any]],
    repaired_runs: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Compare aggregated original and repaired accepted-run evidence."""

    original_summary = _aggregate_run_summaries(original_runs)
    repaired_summary = _aggregate_run_summaries(repaired_runs)
    original_by_scenario = _aggregate_by_scenario(original_runs)
    repaired_by_scenario = _aggregate_by_scenario(repaired_runs)
    original_by_source = _aggregate_by_source(original_runs)
    repaired_by_source = _aggregate_by_source(repaired_runs)
    candidate_metrics = sorted(
        set(validation_targets)
        | set(HIGHER_ORDER_METRICS_BY_CLAIM.get(primary_claim_type, ()))
        | set(SAFETY_METRICS)
        | set(PERFORMANCE_METRICS)
        | set(original_summary.keys())
        | set(repaired_summary.keys())
    )

    metric_deltas: Dict[str, Dict[str, Any]] = {}
    missing_metrics: List[str] = []
    for metric_name in candidate_metrics:
        original_value, original_source_metric = _derive_metric_value(
            metric_name,
            overall_summary=original_summary,
            scenario_summaries=original_by_scenario,
        )
        repaired_value, repaired_source_metric = _derive_metric_value(
            metric_name,
            overall_summary=repaired_summary,
            scenario_summaries=repaired_by_scenario,
        )
        if original_value is None or repaired_value is None:
            if metric_name in validation_targets:
                missing_metrics.append(metric_name)
            continue
        source_metric_name = original_source_metric or repaired_source_metric or TARGET_METRIC_ALIASES.get(metric_name, metric_name)
        direction, improvement = _metric_improvement(metric_name, original_value, repaired_value)
        metric_deltas[metric_name] = {
            "metric_name": metric_name,
            "source_metric_name": source_metric_name,
            "category": _metric_category(metric_name, primary_claim_type),
            "direction": direction,
            "original": original_value,
            "repaired": repaired_value,
            "delta_raw": repaired_value - original_value,
            "improvement": improvement,
        }

    blocked_by: List[str] = []
    if not original_runs:
        blocked_by.append("missing_original_runs")
    if not repaired_runs:
        blocked_by.append("missing_repaired_runs")

    return {
        "comparison_type": "phase9_metric_comparison.v1",
        "primary_claim_type": primary_claim_type,
        "validation_targets": list(validation_targets),
        "original_run_count": len(original_runs),
        "repaired_run_count": len(repaired_runs),
        "original_summary": original_summary,
        "repaired_summary": repaired_summary,
        "original_by_scenario": original_by_scenario,
        "repaired_by_scenario": repaired_by_scenario,
        "original_by_source": original_by_source,
        "repaired_by_source": repaired_by_source,
        "metric_deltas": metric_deltas,
        "missing_metrics": sorted(set(missing_metrics)),
        "blocked_by": blocked_by,
    }


__all__ = [
    "CLAIM_TO_CONSISTENCY_METRICS",
    "HIGHER_ORDER_METRICS_BY_CLAIM",
    "METRIC_DIRECTIONS",
    "PERFORMANCE_METRICS",
    "SAFETY_METRICS",
    "TARGET_METRIC_ALIASES",
    "compare_validation_runs",
]
