"""Phase 9 repair-validation decision rules."""

from __future__ import annotations

from statistics import mean
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from repair.comparison import (
    CLAIM_TO_CONSISTENCY_METRICS,
    HIGHER_ORDER_METRICS_BY_CLAIM,
    PERFORMANCE_METRICS,
    SAFETY_METRICS,
)


def _mean_improvements(metric_deltas: Mapping[str, Mapping[str, Any]], metric_names: Sequence[str]) -> float | None:
    values: List[float] = []
    for name in metric_names:
        payload = metric_deltas.get(name)
        if not payload:
            continue
        try:
            values.append(float(payload.get("improvement", 0.0)))
        except Exception:
            continue
    if not values:
        return None
    return float(mean(values))


def _min_improvement(metric_deltas: Mapping[str, Mapping[str, Any]], metric_names: Iterable[str]) -> float | None:
    values: List[float] = []
    for name in metric_names:
        payload = metric_deltas.get(name)
        if not payload:
            continue
        try:
            values.append(float(payload.get("improvement", 0.0)))
        except Exception:
            continue
    if not values:
        return None
    return min(values)


def decide_validation(
    comparison: Mapping[str, Any],
    *,
    performance_regression_epsilon: float = 0.05,
) -> Dict[str, Any]:
    """Apply the first Phase 9 evidence-based repair decision rule."""

    primary_claim_type = str(comparison.get("primary_claim_type", ""))
    metric_deltas = dict(comparison.get("metric_deltas") or {})
    blocked_by = list(comparison.get("blocked_by", []) or [])
    consistency_metrics = CLAIM_TO_CONSISTENCY_METRICS.get(primary_claim_type, ())
    claim_specific_metrics = tuple(HIGHER_ORDER_METRICS_BY_CLAIM.get(primary_claim_type, ()))

    consistency_improvement = _mean_improvements(metric_deltas, consistency_metrics)
    safety_improvement = _mean_improvements(metric_deltas, SAFETY_METRICS)
    performance_floor = _min_improvement(metric_deltas, PERFORMANCE_METRICS)
    claim_specific_improvement = _mean_improvements(metric_deltas, claim_specific_metrics)
    claim_specific_floor = _min_improvement(metric_deltas, claim_specific_metrics)

    if not consistency_metrics:
        blocked_by.append("missing_consistency_metric_mapping")
    if consistency_improvement is None:
        blocked_by.append("missing_consistency_evidence")
    if safety_improvement is None:
        blocked_by.append("missing_safety_evidence")
    if performance_floor is None:
        blocked_by.append("missing_performance_evidence")
    if claim_specific_metrics and claim_specific_improvement is None:
        blocked_by.append("missing_claim_specific_evidence")

    consistency_ok = consistency_improvement is not None and consistency_improvement > 0.0
    safety_ok = safety_improvement is not None and safety_improvement > 0.0
    performance_ok = performance_floor is not None and performance_floor >= -float(performance_regression_epsilon)
    claim_specific_ok = (
        not claim_specific_metrics
        or (
            claim_specific_improvement is not None
            and claim_specific_improvement > 0.0
            and (claim_specific_floor is None or claim_specific_floor >= 0.0)
        )
    )

    if blocked_by:
        status = "inconclusive"
        accepted = False
        rationale = "Validation decision is inconclusive because required repaired/original evidence is missing."
    elif consistency_ok and safety_ok and performance_ok and claim_specific_ok:
        status = "accepted"
        accepted = True
        rationale = (
            "Repair improves consistency and safety, satisfies claim-specific family-gap checks, "
            "and stays within the allowed performance regression bound."
        )
    else:
        status = "rejected"
        accepted = False
        rationale = (
            "Repair failed the Phase 9 decision rule on consistency, safety, claim-specific family-gap checks, "
            "or performance."
        )

    metric_deltas_summary = {
        "consistency_improvement": consistency_improvement,
        "safety_improvement": safety_improvement,
        "performance_floor": performance_floor,
        "claim_specific_improvement": claim_specific_improvement,
        "claim_specific_floor": claim_specific_floor,
    }
    return {
        "decision_type": "phase9_validation_decision.v1",
        "decision_status": status,
        "accepted": accepted,
        "acceptance_rule": {
            "consistency": "delta > 0",
            "safety": "delta > 0",
            "claim_specific": (
                "mean(delta) > 0 and min(delta) >= 0"
                if claim_specific_metrics
                else "not_required"
            ),
            "performance": f"delta >= -{float(performance_regression_epsilon)}",
        },
        "decision_rationale": rationale,
        "metric_deltas": metric_deltas_summary,
        "claim_specific_metrics": list(claim_specific_metrics),
        "blocked_by": sorted(set(blocked_by)),
        "next_action": (
            "promote_repair_candidate"
            if accepted
            else "collect_more_evidence_or_try_next_candidate"
            if status == "inconclusive"
            else "reject_or_revise_repair_candidate"
        ),
    }


__all__ = ["decide_validation"]
