"""Phase 9 original-vs-repaired metric comparison helpers."""

from __future__ import annotations

from statistics import mean
from typing import Any, Dict, Iterable, List, Mapping, Sequence


METRIC_DIRECTIONS = {
    "W_CR": "lower_better",
    "W_EC": "lower_better",
    "W_ER": "lower_better",
    "collision_rate": "lower_better",
    "near_violation_ratio": "lower_better",
    "min_distance": "higher_better",
    "average_return": "higher_better",
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
    "critical_family_min_distance": "min_distance",
    "shifted_min_distance": "min_distance",
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
    candidate_metrics = sorted(
        set(validation_targets)
        | set(SAFETY_METRICS)
        | set(PERFORMANCE_METRICS)
        | set(original_summary.keys())
        | set(repaired_summary.keys())
    )

    metric_deltas: Dict[str, Dict[str, Any]] = {}
    missing_metrics: List[str] = []
    for metric_name in candidate_metrics:
        source_metric_name = TARGET_METRIC_ALIASES.get(metric_name, metric_name)
        if source_metric_name not in original_summary or source_metric_name not in repaired_summary:
            if metric_name in validation_targets:
                missing_metrics.append(metric_name)
            continue
        original_value = float(original_summary[source_metric_name])
        repaired_value = float(repaired_summary[source_metric_name])
        direction, improvement = _metric_improvement(source_metric_name, original_value, repaired_value)
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
        "metric_deltas": metric_deltas,
        "missing_metrics": sorted(set(missing_metrics)),
        "blocked_by": blocked_by,
    }


__all__ = [
    "CLAIM_TO_CONSISTENCY_METRICS",
    "METRIC_DIRECTIONS",
    "PERFORMANCE_METRICS",
    "SAFETY_METRICS",
    "TARGET_METRIC_ALIASES",
    "compare_validation_runs",
]
