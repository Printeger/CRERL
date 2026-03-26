"""Stable dynamic evidence objects for Phase 5 -> Phase 6 handoff."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence


@dataclass
class DynamicEvidenceObject:
    """A stable, machine-readable runtime evidence object."""

    evidence_id: str
    evidence_type: str
    scope: str
    title: str
    summary: str
    severity: str
    score: float
    witness_id: str = ""
    grouping_key: str = ""
    group_name: str = ""
    sources: List[str] = field(default_factory=list)
    scenario_types: List[str] = field(default_factory=list)
    scene_cfg_names: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    semantic_tags: List[str] = field(default_factory=list)
    attribution_hints: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _as_list(values: Any) -> List[str]:
    if values is None:
        return []
    if isinstance(values, (list, tuple, set)):
        return [str(item) for item in values if item not in (None, "")]
    if values in ("", None):
        return []
    return [str(values)]


def _witness_metric_map(witness_payload: Mapping[str, Any]) -> Dict[str, float]:
    metric_map: Dict[str, float] = {}
    for metric in witness_payload.get("metrics", []) or []:
        metric_id = str(metric.get("metric_id", ""))
        if not metric_id:
            continue
        metric_map[metric_id] = float(metric.get("value", 0.0) or 0.0)
    return metric_map


def _derive_attribution_hints(
    *,
    witness_id: str = "",
    grouping_key: str = "",
    scenario_types: Sequence[str] = (),
    sources: Sequence[str] = (),
) -> List[str]:
    hints: List[str] = []
    witness_id = str(witness_id)
    if witness_id == "W_CR":
        hints.extend(["C-R", "reward-constraint-coupling"])
    elif witness_id == "W_EC":
        hints.extend(["E-C", "critical-state-undercoverage"])
    elif witness_id == "W_ER":
        hints.extend(["E-R", "shift-fragility"])
    if grouping_key == "scenario_type" and "shifted" in {str(item) for item in scenario_types}:
        hints.append("shifted-family-hotspot")
    if grouping_key == "source" and any(str(item).startswith("baseline_") for item in sources):
        hints.append("baseline-conditioned")
    return sorted(set(hints))


def _build_witness_evidence_objects(report_payload: Mapping[str, Any]) -> List[DynamicEvidenceObject]:
    evidence: List[DynamicEvidenceObject] = []
    for witness in report_payload.get("witnesses", []) or []:
        witness_id = str(witness.get("witness_id", "unknown"))
        details = dict(witness.get("details") or {})
        evidence.append(
            DynamicEvidenceObject(
                evidence_id=f"witness:{witness_id}",
                evidence_type="witness_summary",
                scope="report",
                title=f"{witness_id} witness summary",
                summary=str(witness.get("summary", "")),
                severity=str(witness.get("severity", "info")),
                score=float(witness.get("score", 0.0) or 0.0),
                witness_id=witness_id,
                sources=[],
                scenario_types=[],
                scene_cfg_names=[],
                evidence_refs=[
                    str(item)
                    for item in (
                        list(details.get("primary_run_ids", []) or [])
                        + list(details.get("comparison_run_ids", []) or [])
                    )
                    if item not in (None, "")
                ],
                semantic_tags=[witness_id.lower(), "dynamic_witness"],
                attribution_hints=_derive_attribution_hints(witness_id=witness_id),
                metrics=_witness_metric_map(witness),
                payload=details,
            )
        )
    return evidence


def _collect_failure_entries(
    failure_summaries: Mapping[str, Any],
    *,
    scope: str,
) -> List[DynamicEvidenceObject]:
    evidence: List[DynamicEvidenceObject] = []
    for grouping_name, grouped in (failure_summaries or {}).items():
        if grouping_name == "grouping_keys":
            continue
        grouping_key = str(grouping_name).replace("by_", "", 1)
        for group_name, summary in (grouped or {}).items():
            failure_pressure = float(summary.get("failure_pressure", 0.0) or 0.0)
            if failure_pressure <= 0.0:
                continue
            evidence.append(
                DynamicEvidenceObject(
                    evidence_id=f"failure:{scope}:{grouping_key}:{group_name}",
                    evidence_type="failure_hotspot",
                    scope=scope,
                    title=f"{scope} failure hotspot for {grouping_key}={group_name}",
                    summary=(
                        f"{scope} group '{group_name}' under '{grouping_key}' has "
                        f"failure pressure {failure_pressure:.3f}"
                    ),
                    severity=(
                        "high" if failure_pressure >= 0.75
                        else "medium" if failure_pressure >= 0.50
                        else "warning"
                    ),
                    score=failure_pressure,
                    grouping_key=grouping_key,
                    group_name=str(group_name),
                    sources=_as_list(summary.get("sources")),
                    scenario_types=_as_list(summary.get("scenario_types")),
                    scene_cfg_names=_as_list(summary.get("scene_cfg_names")),
                    evidence_refs=_as_list(summary.get("run_ids")),
                    semantic_tags=[
                        "failure_hotspot",
                        scope,
                        grouping_key,
                        str(group_name),
                    ],
                    attribution_hints=_derive_attribution_hints(
                        grouping_key=grouping_key,
                        scenario_types=_as_list(summary.get("scenario_types")),
                        sources=_as_list(summary.get("sources")),
                    ),
                    metrics={
                        "failure_pressure": failure_pressure,
                        "success_rate": float(summary.get("success_rate", 0.0) or 0.0),
                        "collision_rate": float(summary.get("collision_rate", 0.0) or 0.0),
                        "near_violation_ratio": float(summary.get("near_violation_ratio", 0.0) or 0.0),
                        "min_distance": summary.get("min_distance"),
                        "average_return": float(summary.get("average_return", 0.0) or 0.0),
                    },
                    payload=dict(summary),
                )
            )
    evidence.sort(key=lambda item: (-item.score, item.evidence_id))
    return evidence


def build_dynamic_evidence_objects(report_payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    evidence_objects: List[DynamicEvidenceObject] = []
    evidence_objects.extend(_build_witness_evidence_objects(report_payload))

    failure_summaries = report_payload.get("failure_summaries") or {}
    evidence_objects.extend(
        _collect_failure_entries(
            (failure_summaries.get("primary") or {}),
            scope="primary",
        )
    )
    evidence_objects.extend(
        _collect_failure_entries(
            (failure_summaries.get("comparison") or {}),
            scope="comparison",
        )
    )
    return [item.to_dict() for item in evidence_objects]


def build_semantic_diagnosis_inputs(
    report_payload: Mapping[str, Any],
    *,
    spec_ir: Optional[Any] = None,
    max_failure_objects: int = 8,
) -> Dict[str, Any]:
    evidence_objects = build_dynamic_evidence_objects(report_payload)
    witness_objects = [
        item for item in evidence_objects if item["evidence_type"] == "witness_summary"
    ]
    failure_objects = [
        item for item in evidence_objects if item["evidence_type"] == "failure_hotspot"
    ]

    constraint_ids = []
    reward_components = []
    declared_families = []
    if spec_ir is not None:
        constraint_ids = sorted(str(key) for key in getattr(spec_ir, "constraints", {}).keys())
        reward_components = sorted(
            str(key) for key in getattr(getattr(spec_ir, "reward_spec", None), "components", {}).keys()
        )
        declared_families = sorted(
            str(key) for key in getattr(spec_ir, "environment_families", {}).keys()
        )

    return {
        "semantic_input_type": "dynamic_semantic_input.v1",
        "semantic_contract_type": "phase6_dynamic_semantic_contract.v1",
        "spec_version": str(report_payload.get("spec_version", "")),
        "primary_run_ids": list(report_payload.get("primary_run_ids", []) or []),
        "comparison_run_ids": list(report_payload.get("comparison_run_ids", []) or []),
        "report_summary": {
            "passed": bool(report_payload.get("passed", False)),
            "max_severity": str(report_payload.get("max_severity", "info")),
            "num_findings": int(report_payload.get("num_findings", 0) or 0),
        },
        "declared_families": declared_families,
        "constraint_ids": constraint_ids,
        "reward_components": reward_components,
        "witness_overview": [
            {
                "witness_id": item.get("witness_id", ""),
                "severity": item.get("severity", "info"),
                "score": float(item.get("score", 0.0) or 0.0),
                "summary": item.get("summary", ""),
                "metrics": dict(item.get("metrics", {})),
                "evidence_refs": list(item.get("evidence_refs", []) or []),
                "attribution_hints": list(item.get("attribution_hints", []) or []),
            }
            for item in witness_objects
        ],
        "attribution_candidates": [
            {
                "candidate_id": item.get("evidence_id", ""),
                "evidence_type": item.get("evidence_type", ""),
                "scope": item.get("scope", ""),
                "severity": item.get("severity", "info"),
                "score": float(item.get("score", 0.0) or 0.0),
                "summary": item.get("summary", ""),
                "attribution_hints": list(item.get("attribution_hints", []) or []),
                "evidence_refs": list(item.get("evidence_refs", []) or []),
            }
            for item in sorted(
                evidence_objects,
                key=lambda item: float(item.get("score", 0.0) or 0.0),
                reverse=True,
            )[:max_failure_objects]
        ],
        "failure_hotspots": failure_objects[:max_failure_objects],
        "static_context": dict(report_payload.get("static_context") or {}),
        "prompt_sections": {
            "spec_context": {
                "declared_families": declared_families,
                "constraint_ids": constraint_ids,
                "reward_components": reward_components,
            },
            "runtime_summary": {
                "report_summary": {
                    "passed": bool(report_payload.get("passed", False)),
                    "max_severity": str(report_payload.get("max_severity", "info")),
                    "num_findings": int(report_payload.get("num_findings", 0) or 0),
                },
                "primary_run_ids": list(report_payload.get("primary_run_ids", []) or []),
                "comparison_run_ids": list(report_payload.get("comparison_run_ids", []) or []),
            },
            "witness_summary": [
                {
                    "witness_id": item.get("witness_id", ""),
                    "severity": item.get("severity", "info"),
                    "score": float(item.get("score", 0.0) or 0.0),
                    "summary": item.get("summary", ""),
                }
                for item in witness_objects
            ],
            "failure_hotspots": failure_objects[:max_failure_objects],
        },
        "cross_validation_contract": {
            "contract_type": "phase6_cross_validation_contract.v1",
            "required_supported_claim_types": [
                "C-R",
                "E-C",
                "E-R",
            ],
            "required_evidence_fields": [
                "evidence_refs",
                "severity",
                "score",
                "summary",
                "attribution_hints",
            ],
            "claim_to_witness_map": {
                "C-R": ["W_CR"],
                "E-C": ["W_EC"],
                "E-R": ["W_ER"],
            },
            "validation_rules": [
                "Every semantic claim must cite at least one witness or failure-hotspot evidence object.",
                "Semantic attribution must be rejected when no supporting evidence_refs are present.",
                "Claims about shifted degradation should prefer evidence carrying shifted-family-hotspot or W_ER hints.",
            ],
        },
        "prompt_seeds": [
            "Which dynamic witness provides the strongest evidence of inconsistency, and why?",
            "Which source-conditioned or family-conditioned hotspot should be explained first?",
            "Does the dynamic evidence suggest a C-R, E-C, or E-R inconsistency pattern?",
            "What runtime evidence best explains degradation between nominal and shifted conditions?",
        ],
    }


__all__ = [
    "DynamicEvidenceObject",
    "build_dynamic_evidence_objects",
    "build_semantic_diagnosis_inputs",
]
