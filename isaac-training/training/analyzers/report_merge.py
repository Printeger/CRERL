"""Normalization, ranking, and repair-handoff helpers for Phase 7 reporting."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Sequence


SEVERITY_ORDER = {
    "info": 0,
    "warning": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

SEVERITY_SCORE = {
    "info": 0.2,
    "warning": 0.4,
    "medium": 0.6,
    "high": 0.8,
    "critical": 1.0,
}

SOURCE_PRIORITY = {
    "static": 1.0,
    "dynamic": 0.8,
    "semantic_supported": 0.6,
    "semantic_weak": 0.4,
    "semantic_rejected": 0.1,
}

STATIC_CHECK_TO_CLAIM_TYPE = {
    "constraint_runtime_binding": "C-R",
    "reward_constraint_conflicts": "C-R",
    "reward_proxy_suspicion": "C-R",
    "required_runtime_fields": "C-R",
    "scene_family_coverage": "E-C",
    "scene_family_structure": "E-C",
    "scene_backend_capability": "E-R",
    "execution_mode_alignment": "E-R",
}

WITNESS_TO_CLAIM_TYPE = {
    "W_CR": "C-R",
    "W_EC": "E-C",
    "W_ER": "E-R",
}

CLAIM_TYPE_TO_COMPONENTS = {
    "C-R": ("C", "R"),
    "E-C": ("E", "C"),
    "E-R": ("E", "R"),
}

CLAIM_TYPE_TO_REPAIR_DIRECTION = {
    "C-R": "reward",
    "E-C": "environment",
    "E-R": "mixed",
}


def _severity_rank(value: str) -> int:
    return SEVERITY_ORDER.get(str(value).lower(), 0)


def _severity_score(value: str) -> float:
    return SEVERITY_SCORE.get(str(value).lower(), 0.2)


def _stable_unique(values: Iterable[Any]) -> List[str]:
    seen = set()
    items: List[str] = []
    for raw in values:
        if raw in (None, ""):
            continue
        value = str(raw)
        if value in seen:
            continue
        seen.add(value)
        items.append(value)
    return items


def _normalize_confidence(raw: Any, *, fallback: float = 0.5) -> float:
    try:
        value = float(raw)
    except Exception:
        value = float(fallback)
    return max(0.0, min(1.0, value))


def _static_confidence(finding: Mapping[str, Any]) -> float:
    if finding.get("passed", False):
        return 0.35
    return _severity_score(str(finding.get("severity", "warning")))


@dataclass
class RankedFinding:
    """Unified ranked finding record for Phase 7 merged reporting."""

    finding_id: str
    source_namespace: str
    source_record_id: str
    claim_type: str
    severity: str
    confidence: float
    support_status: str
    summary: str
    evidence_refs: List[str] = field(default_factory=list)
    impacted_components: List[str] = field(default_factory=list)
    repair_direction: str = ""
    rank_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RepairReadyRecord:
    """Minimal repair-ready claim handoff for Phase 8."""

    handoff_id: str
    claim_type: str
    selected_from: str
    severity: str
    confidence: float
    support_status: str
    summary: str
    impacted_components: List[str] = field(default_factory=list)
    suggested_repair_direction: str = ""
    evidence_refs: List[str] = field(default_factory=list)
    source_record_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _rank_score(
    *,
    severity: str,
    confidence: float,
    source_key: str,
) -> float:
    return round(
        0.55 * _severity_score(severity)
        + 0.30 * SOURCE_PRIORITY.get(source_key, 0.2)
        + 0.15 * _normalize_confidence(confidence),
        6,
    )


def normalize_static_findings(static_report: Mapping[str, Any]) -> List[RankedFinding]:
    findings: List[RankedFinding] = []
    for entry in static_report.get("findings", []) or []:
        check_id = str(entry.get("check_id", ""))
        severity = str(entry.get("severity", "warning"))
        claim_type = STATIC_CHECK_TO_CLAIM_TYPE.get(check_id, "unknown")
        confidence = _static_confidence(entry)
        findings.append(
            RankedFinding(
                finding_id=f"report:static:{entry.get('finding_id', check_id)}",
                source_namespace="analysis/static",
                source_record_id=str(entry.get("finding_id", check_id)),
                claim_type=claim_type,
                severity=severity,
                confidence=confidence,
                support_status="machine_direct",
                summary=str(entry.get("summary", "")),
                evidence_refs=_stable_unique(entry.get("affected_paths", []) or []),
                impacted_components=list(CLAIM_TYPE_TO_COMPONENTS.get(claim_type, ())),
                repair_direction=CLAIM_TYPE_TO_REPAIR_DIRECTION.get(claim_type, ""),
                rank_score=_rank_score(
                    severity=severity,
                    confidence=confidence,
                    source_key="static",
                ),
                metadata={
                    "check_id": check_id,
                    "passed": bool(entry.get("passed", False)),
                    "recommended_action": str(entry.get("recommended_action", "")),
                },
            )
        )
    return findings


def normalize_dynamic_findings(dynamic_report: Mapping[str, Any]) -> List[RankedFinding]:
    findings: List[RankedFinding] = []
    for entry in dynamic_report.get("findings", []) or []:
        witness_id = str(entry.get("witness_id", ""))
        claim_type = WITNESS_TO_CLAIM_TYPE.get(witness_id, "unknown")
        severity = str(entry.get("severity", "warning"))
        confidence = _normalize_confidence(entry.get("score", 0.0), fallback=0.5)
        findings.append(
            RankedFinding(
                finding_id=f"report:dynamic:{entry.get('finding_id', witness_id)}",
                source_namespace="analysis/dynamic",
                source_record_id=str(entry.get("finding_id", witness_id)),
                claim_type=claim_type,
                severity=severity,
                confidence=confidence,
                support_status="machine_derived",
                summary=str(entry.get("summary", "")),
                evidence_refs=_stable_unique(entry.get("evidence_refs", []) or []),
                impacted_components=list(CLAIM_TYPE_TO_COMPONENTS.get(claim_type, ())),
                repair_direction=CLAIM_TYPE_TO_REPAIR_DIRECTION.get(claim_type, ""),
                rank_score=_rank_score(
                    severity=severity,
                    confidence=confidence,
                    source_key="dynamic",
                ),
                metadata={
                    "witness_id": witness_id,
                    "score": confidence,
                },
            )
        )
    return findings


def normalize_semantic_claims(
    semantic_report: Mapping[str, Any],
    claim_consumer: Mapping[str, Any],
) -> List[RankedFinding]:
    findings: List[RankedFinding] = []

    def _append(
        claims: Sequence[Mapping[str, Any]],
        *,
        source_key: str,
        support_status: str,
    ) -> None:
        for entry in claims:
            claim_type = str(entry.get("claim_type", "unknown"))
            severity = str(entry.get("severity", "warning"))
            confidence = _normalize_confidence(entry.get("confidence", 0.0), fallback=0.5)
            findings.append(
                RankedFinding(
                    finding_id=f"report:semantic:{entry.get('claim_id', claim_type)}",
                    source_namespace="analysis/semantic",
                    source_record_id=str(entry.get("claim_id", claim_type)),
                    claim_type=claim_type,
                    severity=severity,
                    confidence=confidence,
                    support_status=support_status,
                    summary=str(entry.get("summary", "")),
                    evidence_refs=_stable_unique(entry.get("supporting_evidence_ids", []) or []),
                    impacted_components=list(CLAIM_TYPE_TO_COMPONENTS.get(claim_type, ())),
                    repair_direction=str(entry.get("repair_direction_hint", "")) or CLAIM_TYPE_TO_REPAIR_DIRECTION.get(
                        claim_type,
                        "",
                    ),
                    rank_score=_rank_score(
                        severity=severity,
                        confidence=confidence,
                        source_key=source_key,
                    ),
                    metadata={
                        "affected_families": list(entry.get("affected_families", []) or []),
                        "affected_sources": list(entry.get("affected_sources", []) or []),
                        "affected_scene_cfg_names": list(entry.get("affected_scene_cfg_names", []) or []),
                        "semantic_bundle_name": str(claim_consumer.get("semantic_bundle_name", "")),
                    },
                )
            )

    _append(semantic_report.get("supported_claims", []) or [], source_key="semantic_supported", support_status="semantic_supported")
    _append(semantic_report.get("weak_claims", []) or [], source_key="semantic_weak", support_status="semantic_weak")
    _append(semantic_report.get("rejected_claims", []) or [], source_key="semantic_rejected", support_status="semantic_rejected")
    return findings


def rank_findings(findings: Sequence[RankedFinding]) -> List[RankedFinding]:
    return sorted(
        findings,
        key=lambda item: (
            item.rank_score,
            _severity_rank(item.severity),
            item.confidence,
            item.finding_id,
        ),
        reverse=True,
    )


def build_root_cause_summary(ranked_findings: Sequence[RankedFinding]) -> Dict[str, Any]:
    claim_type_breakdown: Dict[str, int] = {}
    source_breakdown: Dict[str, int] = {}
    for finding in ranked_findings:
        claim_type_breakdown[finding.claim_type] = int(claim_type_breakdown.get(finding.claim_type, 0)) + 1
        source_breakdown[finding.source_namespace] = int(source_breakdown.get(finding.source_namespace, 0)) + 1

    top_finding = ranked_findings[0] if ranked_findings else None
    return {
        "primary_claim_type": top_finding.claim_type if top_finding else "",
        "primary_summary": top_finding.summary if top_finding else "",
        "primary_support_status": top_finding.support_status if top_finding else "",
        "claim_type_breakdown": dict(sorted(claim_type_breakdown.items())),
        "source_breakdown": dict(sorted(source_breakdown.items())),
    }


def build_repair_handoff(
    ranked_findings: Sequence[RankedFinding],
    claim_consumer: Mapping[str, Any],
) -> List[RepairReadyRecord]:
    handoff: List[RepairReadyRecord] = []
    seen_source_records = set()

    for entry in claim_consumer.get("repair_ready_claims", []) or []:
        source_record_id = str(entry.get("claim_id", ""))
        if source_record_id in seen_source_records:
            continue
        seen_source_records.add(source_record_id)
        claim_type = str(entry.get("claim_type", "unknown"))
        handoff.append(
            RepairReadyRecord(
                handoff_id=f"repair_handoff:{source_record_id}",
                claim_type=claim_type,
                selected_from="analysis/semantic",
                severity=str(entry.get("severity", "warning")),
                confidence=_normalize_confidence(entry.get("confidence", 0.0), fallback=0.5),
                support_status=str(entry.get("crosscheck_support_status", "semantic_supported")),
                summary=str(entry.get("summary", "")),
                impacted_components=list(entry.get("impacted_components", []) or CLAIM_TYPE_TO_COMPONENTS.get(claim_type, ())),
                suggested_repair_direction=CLAIM_TYPE_TO_REPAIR_DIRECTION.get(claim_type, ""),
                evidence_refs=_stable_unique(entry.get("supporting_evidence_ids", []) or []),
                source_record_ids=_stable_unique([source_record_id]),
            )
        )

    for finding in ranked_findings:
        if finding.source_record_id in seen_source_records:
            continue
        if finding.support_status == "semantic_rejected":
            continue
        if finding.claim_type == "unknown":
            continue
        handoff.append(
            RepairReadyRecord(
                handoff_id=f"repair_handoff:{finding.source_record_id}",
                claim_type=finding.claim_type,
                selected_from=finding.source_namespace,
                severity=finding.severity,
                confidence=finding.confidence,
                support_status=finding.support_status,
                summary=finding.summary,
                impacted_components=list(finding.impacted_components),
                suggested_repair_direction=finding.repair_direction,
                evidence_refs=list(finding.evidence_refs),
                source_record_ids=[finding.source_record_id],
            )
        )
        seen_source_records.add(finding.source_record_id)
        if len(handoff) >= 6:
            break
    return handoff


def build_semantic_claim_summary(semantic_report: Mapping[str, Any]) -> Dict[str, Any]:
    human_summary = dict(semantic_report.get("human_summary", {}) or {})
    return {
        "supported_claims": len(semantic_report.get("supported_claims", []) or []),
        "weak_claims": len(semantic_report.get("weak_claims", []) or []),
        "rejected_claims": len(semantic_report.get("rejected_claims", []) or []),
        "most_likely_claim_type": str(human_summary.get("most_likely_claim_type", "")),
        "most_likely_claim_summary": str(human_summary.get("most_likely_claim_summary", "")),
        "next_check_or_repair_direction": str(human_summary.get("next_check_or_repair_direction", "")),
    }


def build_witness_summary(dynamic_report: Mapping[str, Any]) -> Dict[str, Any]:
    witness_scores: Dict[str, float] = {}
    witness_severities: Dict[str, str] = {}
    for witness in dynamic_report.get("witnesses", []) or []:
        witness_id = str(witness.get("witness_id", ""))
        if not witness_id:
            continue
        witness_scores[witness_id] = _normalize_confidence(witness.get("score", 0.0), fallback=0.0)
        witness_severities[witness_id] = str(witness.get("severity", "info"))
    return {
        "witness_scores": dict(sorted(witness_scores.items())),
        "witness_severities": dict(sorted(witness_severities.items())),
        "group_summaries": dict(dynamic_report.get("group_summaries", {}) or {}),
        "failure_summaries": dict(dynamic_report.get("failure_summaries", {}) or {}),
    }


__all__ = [
    "CLAIM_TYPE_TO_COMPONENTS",
    "CLAIM_TYPE_TO_REPAIR_DIRECTION",
    "RankedFinding",
    "RepairReadyRecord",
    "build_repair_handoff",
    "build_root_cause_summary",
    "build_semantic_claim_summary",
    "build_witness_summary",
    "normalize_dynamic_findings",
    "normalize_semantic_claims",
    "normalize_static_findings",
    "rank_findings",
]
