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

SUPPORT_PRIORITY = {
    "machine_direct": 1.0,
    "machine_derived": 0.85,
    "semantic_supported": 0.75,
    "semantic_weak": 0.35,
    "semantic_rejected": 0.05,
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
    selected_from_rank: int
    severity: str
    confidence: float
    support_status: str
    summary: str
    impacted_components: List[str] = field(default_factory=list)
    suggested_repair_direction: str = ""
    required_evidence_refs: List[str] = field(default_factory=list)
    source_record_ids: List[str] = field(default_factory=list)
    selection_basis: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RepairHandoffBundle:
    """Stable Phase 8-facing repair handoff bundle."""

    handoff_type: str
    primary_claim_type: str
    primary_repair_direction: str
    claim_record_schema: str
    selection_policy: str
    impacted_components_union: List[str] = field(default_factory=list)
    selected_claims: List[RepairReadyRecord] = field(default_factory=list)
    repair_order: List[Dict[str, Any]] = field(default_factory=list)
    required_evidence_contract: Dict[str, Any] = field(default_factory=dict)
    selection_summary: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["selected_claims"] = [item.to_dict() for item in self.selected_claims]
        return payload


def _rank_score(
    *,
    severity: str,
    confidence: float,
    source_key: str,
    support_status: str,
    evidence_count: int,
) -> float:
    return round(
        0.40 * _severity_score(severity)
        + 0.20 * SOURCE_PRIORITY.get(source_key, 0.2)
        + 0.20 * SUPPORT_PRIORITY.get(support_status, 0.2)
        + 0.15 * _normalize_confidence(confidence)
        + 0.05 * min(max(int(evidence_count), 0), 4) / 4.0,
        6,
    )


def _pairwise_top_conflicts(top_by_namespace: Mapping[str, Mapping[str, Any]]) -> List[Dict[str, Any]]:
    conflicts: List[Dict[str, Any]] = []
    namespace_pairs = (
        ("analysis/static", "analysis/dynamic", "static_dynamic_claim_type_conflict"),
        ("analysis/static", "analysis/semantic", "static_semantic_claim_type_conflict"),
        ("analysis/dynamic", "analysis/semantic", "dynamic_semantic_claim_type_conflict"),
    )
    for left_namespace, right_namespace, kind in namespace_pairs:
        left = top_by_namespace.get(left_namespace)
        right = top_by_namespace.get(right_namespace)
        if not left or not right:
            continue
        if left.get("claim_type") == right.get("claim_type"):
            continue
        conflicts.append(
            {
                "kind": kind,
                "left_namespace": left_namespace,
                "right_namespace": right_namespace,
                "left_claim_type": left.get("claim_type", ""),
                "right_claim_type": right.get("claim_type", ""),
                "left_support_status": left.get("support_status", ""),
                "right_support_status": right.get("support_status", ""),
            }
        )
    return conflicts


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
                    support_status="machine_direct",
                    evidence_count=len(_stable_unique(entry.get("affected_paths", []) or [])),
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
                    support_status="machine_derived",
                    evidence_count=len(_stable_unique(entry.get("evidence_refs", []) or [])),
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
                        support_status=support_status,
                        evidence_count=len(_stable_unique(entry.get("supporting_evidence_ids", []) or [])),
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
    claim_type_scores: Dict[str, float] = {}
    top_by_namespace: Dict[str, Dict[str, Any]] = {}
    for finding in ranked_findings:
        claim_type_breakdown[finding.claim_type] = int(claim_type_breakdown.get(finding.claim_type, 0)) + 1
        source_breakdown[finding.source_namespace] = int(source_breakdown.get(finding.source_namespace, 0)) + 1
        claim_type_scores[finding.claim_type] = round(
            float(claim_type_scores.get(finding.claim_type, 0.0))
            + float(finding.rank_score) * float(SUPPORT_PRIORITY.get(finding.support_status, 0.2)),
            6,
        )
        if finding.source_namespace not in top_by_namespace:
            top_by_namespace[finding.source_namespace] = {
                "claim_type": finding.claim_type,
                "summary": finding.summary,
                "severity": finding.severity,
                "support_status": finding.support_status,
                "rank_score": finding.rank_score,
            }

    top_finding = ranked_findings[0] if ranked_findings else None
    blocking_static = [
        finding
        for finding in ranked_findings
        if finding.source_namespace == "analysis/static"
        and finding.support_status == "machine_direct"
        and _severity_rank(finding.severity) >= _severity_rank("high")
    ]

    selection_mode = "aggregate_claim_score"
    if blocking_static:
        primary_finding = blocking_static[0]
        primary_claim_type = primary_finding.claim_type
        selection_mode = "static_blocker_override"
    else:
        primary_claim_type = ""
        if claim_type_scores:
            primary_claim_type = max(
                sorted(claim_type_scores),
                key=lambda key: (claim_type_scores[key], claim_type_breakdown.get(key, 0), key),
            )
        if not primary_claim_type and top_finding is not None:
            primary_claim_type = top_finding.claim_type

        primary_finding = next(
            (finding for finding in ranked_findings if finding.claim_type == primary_claim_type),
            top_finding,
        )

    claim_type_ordering = [
        {
            "claim_type": claim_type,
            "aggregate_score": claim_type_scores[claim_type],
            "finding_count": claim_type_breakdown.get(claim_type, 0),
        }
        for claim_type in sorted(
            claim_type_scores,
            key=lambda key: (claim_type_scores[key], claim_type_breakdown.get(key, 0), key),
            reverse=True,
        )
    ]

    conflicts = _pairwise_top_conflicts(top_by_namespace)

    selection_reason = ""
    if primary_finding is not None:
        if selection_mode == "static_blocker_override":
            selection_reason = (
                f"Selected `{primary_claim_type}` because a high-severity static blocker "
                f"takes precedence over weaker cross-namespace alternatives."
            )
        else:
            selection_reason = (
                f"Selected `{primary_claim_type}` from aggregated cross-namespace score "
                f"with strongest supporting finding in `{primary_finding.source_namespace}`."
            )
    return {
        "primary_claim_type": primary_claim_type,
        "primary_summary": primary_finding.summary if primary_finding else "",
        "primary_support_status": primary_finding.support_status if primary_finding else "",
        "claim_type_breakdown": dict(sorted(claim_type_breakdown.items())),
        "source_breakdown": dict(sorted(source_breakdown.items())),
        "claim_type_scores": dict(sorted(claim_type_scores.items())),
        "claim_type_ordering": claim_type_ordering,
        "top_by_namespace": top_by_namespace,
        "conflicts": conflicts,
        "selection_mode": selection_mode,
        "selection_reason": selection_reason,
    }


def build_repair_handoff(
    ranked_findings: Sequence[RankedFinding],
    claim_consumer: Mapping[str, Any],
    *,
    primary_claim_type_override: str = "",
) -> RepairHandoffBundle:
    selected_claims: List[RepairReadyRecord] = []
    seen_source_records = set()
    impacted_components_union = set()
    primary_claim_type = str(primary_claim_type_override or claim_consumer.get("primary_claim_type", "")) or (
        ranked_findings[0].claim_type if ranked_findings else ""
    )
    primary_repair_direction = CLAIM_TYPE_TO_REPAIR_DIRECTION.get(primary_claim_type, "")
    selected_by_claim_type: Dict[str, List[RepairReadyRecord]] = {}

    def _register(record: RepairReadyRecord) -> None:
        selected_claims.append(record)
        selected_by_claim_type.setdefault(record.claim_type, []).append(record)

    def _has_overlapping_selected(
        claim_type: str,
        evidence_refs: Sequence[str],
        *,
        stronger_only: bool = True,
    ) -> bool:
        existing = selected_by_claim_type.get(claim_type, [])
        if not existing:
            return False
        evidence_set = set(_stable_unique(evidence_refs))
        for record in existing:
            if stronger_only and SUPPORT_PRIORITY.get(record.support_status, 0.0) < SUPPORT_PRIORITY.get("semantic_supported", 0.75):
                continue
            if evidence_set and evidence_set.intersection(record.required_evidence_refs):
                return True
        return False

    for entry in claim_consumer.get("repair_ready_claims", []) or []:
        source_record_id = str(entry.get("claim_id", ""))
        if source_record_id in seen_source_records:
            continue
        seen_source_records.add(source_record_id)
        claim_type = str(entry.get("claim_type", "unknown"))
        impacted_components = list(entry.get("impacted_components", []) or CLAIM_TYPE_TO_COMPONENTS.get(claim_type, ()))
        impacted_components_union.update(impacted_components)
        _register(
            RepairReadyRecord(
                handoff_id=f"repair_handoff:{source_record_id}",
                claim_type=claim_type,
                selected_from="analysis/semantic",
                selected_from_rank=next(
                    (
                        index
                        for index, finding in enumerate(ranked_findings, start=1)
                        if finding.source_record_id == source_record_id
                    ),
                    -1,
                ),
                severity=str(entry.get("severity", "warning")),
                confidence=_normalize_confidence(entry.get("confidence", 0.0), fallback=0.5),
                support_status=str(entry.get("crosscheck_support_status", "semantic_supported")),
                summary=str(entry.get("summary", "")),
                impacted_components=impacted_components,
                suggested_repair_direction=CLAIM_TYPE_TO_REPAIR_DIRECTION.get(claim_type, ""),
                required_evidence_refs=_stable_unique(entry.get("supporting_evidence_ids", []) or []),
                source_record_ids=_stable_unique([source_record_id]),
                selection_basis="semantic_supported_claim_consumer",
            )
        )

    for rank, finding in enumerate(ranked_findings, start=1):
        if finding.source_record_id in seen_source_records:
            continue
        if finding.support_status == "semantic_rejected":
            continue
        if finding.claim_type == "unknown":
            continue
        if finding.support_status == "semantic_weak" and (
            selected_by_claim_type.get(finding.claim_type)
            or _has_overlapping_selected(finding.claim_type, finding.evidence_refs, stronger_only=False)
        ):
            continue
        if _has_overlapping_selected(finding.claim_type, finding.evidence_refs):
            continue
        impacted_components_union.update(finding.impacted_components)
        _register(
            RepairReadyRecord(
                handoff_id=f"repair_handoff:{finding.source_record_id}",
                claim_type=finding.claim_type,
                selected_from=finding.source_namespace,
                selected_from_rank=rank,
                severity=finding.severity,
                confidence=finding.confidence,
                support_status=finding.support_status,
                summary=finding.summary,
                impacted_components=list(finding.impacted_components),
                suggested_repair_direction=finding.repair_direction,
                required_evidence_refs=list(finding.evidence_refs),
                source_record_ids=[finding.source_record_id],
                selection_basis="ranked_finding_backfill",
            )
        )
        seen_source_records.add(finding.source_record_id)
    selected_claims = sorted(
        selected_claims,
        key=lambda item: (
            1 if item.claim_type == primary_claim_type else 0,
            SUPPORT_PRIORITY.get(item.support_status, 0.0),
            _severity_rank(item.severity),
            item.confidence,
            -item.selected_from_rank if item.selected_from_rank > 0 else -9999,
            item.handoff_id,
        ),
        reverse=True,
    )[:6]
    selection_focus_order = _stable_unique(
        [primary_claim_type, *[item.claim_type for item in selected_claims if item.claim_type != primary_claim_type]]
    )
    repair_order = [
        {
            "order": index,
            "handoff_id": item.handoff_id,
            "claim_type": item.claim_type,
            "selected_from": item.selected_from,
            "suggested_repair_direction": item.suggested_repair_direction,
            "selection_basis": item.selection_basis,
        }
        for index, item in enumerate(selected_claims, start=1)
    ]
    return RepairHandoffBundle(
        handoff_type="phase8_repair_handoff.v1",
        primary_claim_type=primary_claim_type,
        primary_repair_direction=primary_repair_direction,
        claim_record_schema="phase7_repair_ready_claim.v1",
        selection_policy="phase7_ranked_claim_selection.v3",
        impacted_components_union=sorted(impacted_components_union),
        selected_claims=selected_claims,
        repair_order=repair_order,
        required_evidence_contract={
            "required_claim_fields": [
                "claim_type",
                "support_status",
                "impacted_components",
                "suggested_repair_direction",
                "required_evidence_refs",
            ],
            "required_support_statuses": [
                "machine_direct",
                "machine_derived",
                "semantic_supported",
                "semantic_weak",
            ],
        },
        selection_summary={
            "primary_claim_type": primary_claim_type,
            "selection_focus_order": selection_focus_order,
            "selected_claim_count": len(selected_claims),
        },
        metadata={
            "phase8_ready": True,
            "max_selected_claims": 6,
        },
    )


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
    "RepairHandoffBundle",
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
