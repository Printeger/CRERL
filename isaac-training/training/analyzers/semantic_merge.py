"""Higher-level semantic merge and Phase-7 claim consumer interfaces."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


def _claim_type_breakdown(claims: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    breakdown: Dict[str, int] = {}
    for claim in claims:
        claim_type = str(claim.get("claim_type", "unknown"))
        breakdown[claim_type] = int(breakdown.get(claim_type, 0)) + 1
    return dict(sorted(breakdown.items()))


def _dedupe_strings(values: Sequence[Any] | None) -> List[str]:
    if not values:
        return []
    seen = set()
    result: List[str] = []
    for item in values:
        if item in (None, ""):
            continue
        value = str(item)
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


@dataclass
class Phase7ClaimRecord:
    """Consumer-facing semantic claim record for Phase 7 and Phase 8."""

    claim_id: str
    claim_type: str
    status: str
    severity: str
    confidence: float
    summary: str
    rationale: str = ""
    supporting_evidence_ids: List[str] = field(default_factory=list)
    supporting_witness_ids: List[str] = field(default_factory=list)
    supporting_finding_ids: List[str] = field(default_factory=list)
    affected_families: List[str] = field(default_factory=list)
    affected_sources: List[str] = field(default_factory=list)
    affected_scene_cfg_names: List[str] = field(default_factory=list)
    repair_direction_hint: str = ""
    crosscheck_support_status: str = "weak"
    claim_priority: str = "secondary"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Phase7ClaimConsumerBundle:
    """Stable semantic claim substrate for downstream report/repair logic."""

    consumer_type: str
    semantic_bundle_name: str
    static_bundle_name: str
    dynamic_bundle_name: str
    primary_claim_type: str
    repair_ready_claims: List[Phase7ClaimRecord] = field(default_factory=list)
    review_claims: List[Phase7ClaimRecord] = field(default_factory=list)
    rejected_claims: List[Phase7ClaimRecord] = field(default_factory=list)
    crosscheck_summary: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "consumer_type": self.consumer_type,
            "semantic_bundle_name": self.semantic_bundle_name,
            "static_bundle_name": self.static_bundle_name,
            "dynamic_bundle_name": self.dynamic_bundle_name,
            "primary_claim_type": self.primary_claim_type,
            "repair_ready_claims": [item.to_dict() for item in self.repair_ready_claims],
            "review_claims": [item.to_dict() for item in self.review_claims],
            "rejected_claims": [item.to_dict() for item in self.rejected_claims],
            "crosscheck_summary": dict(self.crosscheck_summary),
            "metadata": dict(self.metadata),
        }


@dataclass
class SemanticReportMergeInput:
    """Higher-level semantic summary payload for Phase 7 merged reporting."""

    merge_input_type: str
    semantic_bundle_name: str
    static_bundle_name: str
    dynamic_bundle_name: str
    spec_version: str
    passed: bool
    max_severity: str
    top_claim: Dict[str, Any] = field(default_factory=dict)
    claim_overview: Dict[str, Any] = field(default_factory=dict)
    evidence_overview: Dict[str, Any] = field(default_factory=dict)
    human_summary: Dict[str, Any] = field(default_factory=dict)
    consumer_contract: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _claim_from_payload(
    claim: Mapping[str, Any],
    *,
    claim_priority: str,
    crosscheck_support_status: str,
) -> Phase7ClaimRecord:
    return Phase7ClaimRecord(
        claim_id=str(claim.get("claim_id", "")),
        claim_type=str(claim.get("claim_type", "unknown")),
        status=str(claim.get("status", "weak")),
        severity=str(claim.get("severity", "warning")),
        confidence=float(claim.get("confidence", 0.0) or 0.0),
        summary=str(claim.get("summary", "")),
        rationale=str(claim.get("rationale", "")),
        supporting_evidence_ids=_dedupe_strings(claim.get("supporting_evidence_ids", []) or []),
        supporting_witness_ids=_dedupe_strings(claim.get("supporting_witness_ids", []) or []),
        supporting_finding_ids=_dedupe_strings(claim.get("supporting_finding_ids", []) or []),
        affected_families=_dedupe_strings(claim.get("affected_families", []) or []),
        affected_sources=_dedupe_strings(claim.get("affected_sources", []) or []),
        affected_scene_cfg_names=_dedupe_strings(claim.get("affected_scene_cfg_names", []) or []),
        repair_direction_hint=str(claim.get("repair_direction_hint", "")),
        crosscheck_support_status=str(crosscheck_support_status),
        claim_priority=str(claim_priority),
    )


def build_phase7_claim_consumer(
    report: Mapping[str, Any],
    *,
    semantic_bundle_name: str,
) -> Phase7ClaimConsumerBundle:
    supported_claims = list(report.get("supported_claims", []) or [])
    weak_claims = list(report.get("weak_claims", []) or [])
    rejected_claims = list(report.get("rejected_claims", []) or [])
    cross_checks = list(report.get("cross_checks", []) or [])
    human_summary = dict(report.get("human_summary", {}) or {})

    primary_claim_type = str(human_summary.get("most_likely_claim_type", ""))
    repair_ready_claims = [
        _claim_from_payload(
            claim,
            claim_priority="primary" if str(claim.get("claim_type", "")) == primary_claim_type else "secondary",
            crosscheck_support_status="supported",
        )
        for claim in supported_claims
    ]
    review_claims = [
        _claim_from_payload(
            claim,
            claim_priority="review",
            crosscheck_support_status="weak",
        )
        for claim in weak_claims
    ]
    rejected_claim_records = [
        _claim_from_payload(
            claim,
            claim_priority="discarded",
            crosscheck_support_status="rejected",
        )
        for claim in rejected_claims
    ]

    crosscheck_summary = {
        "supported_count": len(supported_claims),
        "weak_count": len(weak_claims),
        "rejected_count": len(rejected_claims),
        "total_cross_checks": len(cross_checks),
        "claim_type_breakdown": _claim_type_breakdown([*supported_claims, *weak_claims, *rejected_claims]),
    }
    return Phase7ClaimConsumerBundle(
        consumer_type="phase7_claim_consumer.v1",
        semantic_bundle_name=str(semantic_bundle_name),
        static_bundle_name=str(report.get("static_bundle_name", "")),
        dynamic_bundle_name=str(report.get("dynamic_bundle_name", "")),
        primary_claim_type=primary_claim_type,
        repair_ready_claims=repair_ready_claims,
        review_claims=review_claims,
        rejected_claims=rejected_claim_records,
        crosscheck_summary=crosscheck_summary,
        metadata={
            "consumer_contract_type": "phase7_claim_consumer_contract.v1",
            "expected_consumers": ["phase7_report_generator", "phase8_repair_engine"],
        },
    )


def build_semantic_report_merge_input(
    report: Mapping[str, Any],
    *,
    semantic_bundle_name: str,
    claim_consumer_bundle: Mapping[str, Any],
) -> SemanticReportMergeInput:
    supported_claims = list(report.get("supported_claims", []) or [])
    weak_claims = list(report.get("weak_claims", []) or [])
    rejected_claims = list(report.get("rejected_claims", []) or [])
    semantic_input = dict(report.get("semantic_input", {}) or {})
    evidence_context = dict(semantic_input.get("evidence_context", {}) or {})

    top_claim = dict()
    if supported_claims:
        top_claim = dict(supported_claims[0])
    elif weak_claims:
        top_claim = dict(weak_claims[0])

    return SemanticReportMergeInput(
        merge_input_type="phase7_semantic_report_merge_input.v1",
        semantic_bundle_name=str(semantic_bundle_name),
        static_bundle_name=str(report.get("static_bundle_name", "")),
        dynamic_bundle_name=str(report.get("dynamic_bundle_name", "")),
        spec_version=str(report.get("spec_version", "")),
        passed=bool(report.get("passed", False)),
        max_severity=str(report.get("max_severity", "info")),
        top_claim=top_claim,
        claim_overview={
            "supported_count": len(supported_claims),
            "weak_count": len(weak_claims),
            "rejected_count": len(rejected_claims),
            "claim_type_breakdown": _claim_type_breakdown([*supported_claims, *weak_claims, *rejected_claims]),
        },
        evidence_overview={
            "static_finding_count": int((evidence_context.get("static_findings") or {}).get("count", 0) or 0),
            "dynamic_finding_count": int((evidence_context.get("dynamic_findings") or {}).get("count", 0) or 0),
            "witness_count": len(list(evidence_context.get("witness_summaries", []) or [])),
            "evidence_object_count": len(list(evidence_context.get("evidence_objects", []) or [])),
            "failure_hotspot_count": len(list(evidence_context.get("failure_hotspots", []) or [])),
        },
        human_summary=dict(report.get("human_summary", {}) or {}),
        consumer_contract={
            "claim_consumer_type": str(claim_consumer_bundle.get("consumer_type", "")),
            "consumer_contract_type": str(
                (claim_consumer_bundle.get("metadata", {}) or {}).get("consumer_contract_type", "")
            ),
            "repair_ready_claim_schema": "phase7_claim_record.v1",
        },
        metadata={
            "merge_target": "phase7_unified_report_generation",
            "repair_target": "phase8_repair_engine",
        },
    )


def write_phase7_claim_consumer(bundle: Mapping[str, Any], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(bundle), indent=2, sort_keys=True), encoding="utf-8")
    return path


def write_semantic_report_merge_input(payload: Mapping[str, Any], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True), encoding="utf-8")
    return path


__all__ = [
    "Phase7ClaimConsumerBundle",
    "Phase7ClaimRecord",
    "SemanticReportMergeInput",
    "build_phase7_claim_consumer",
    "build_semantic_report_merge_input",
    "write_phase7_claim_consumer",
    "write_semantic_report_merge_input",
]
