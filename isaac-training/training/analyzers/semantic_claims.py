"""Structured semantic claim schema for Phase 6 diagnosis."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Sequence


CANONICAL_CLAIM_TYPES = ("C-R", "E-C", "E-R", "unknown")
CANONICAL_CLAIM_STATUSES = ("supported", "weak", "rejected")
CANONICAL_SEVERITIES = ("info", "warning", "medium", "high", "critical")


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


def normalize_claim_type(value: Any) -> str:
    claim_type = str(value or "unknown").strip().upper()
    if claim_type in {"CR", "C_R"}:
        claim_type = "C-R"
    elif claim_type in {"EC", "E_C"}:
        claim_type = "E-C"
    elif claim_type in {"ER", "E_R"}:
        claim_type = "E-R"
    return claim_type if claim_type in CANONICAL_CLAIM_TYPES else "unknown"


def normalize_claim_status(value: Any) -> str:
    status = str(value or "weak").strip().lower()
    return status if status in CANONICAL_CLAIM_STATUSES else "weak"


def normalize_severity(value: Any) -> str:
    severity = str(value or "warning").strip().lower()
    return severity if severity in CANONICAL_SEVERITIES else "warning"


def normalize_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        confidence = 0.0
    return max(0.0, min(1.0, confidence))


@dataclass
class SemanticClaim:
    """A machine-readable semantic inconsistency claim."""

    claim_id: str
    claim_type: str
    confidence: float
    severity: str
    summary: str
    rationale: str = ""
    status: str = "weak"
    supporting_evidence_ids: List[str] = field(default_factory=list)
    supporting_witness_ids: List[str] = field(default_factory=list)
    supporting_finding_ids: List[str] = field(default_factory=list)
    affected_families: List[str] = field(default_factory=list)
    affected_sources: List[str] = field(default_factory=list)
    affected_scene_cfg_names: List[str] = field(default_factory=list)
    repair_direction_hint: str = ""
    provider_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.claim_type = normalize_claim_type(self.claim_type)
        self.status = normalize_claim_status(self.status)
        self.severity = normalize_severity(self.severity)
        self.confidence = normalize_confidence(self.confidence)
        self.supporting_evidence_ids = _dedupe_strings(self.supporting_evidence_ids)
        self.supporting_witness_ids = _dedupe_strings(self.supporting_witness_ids)
        self.supporting_finding_ids = _dedupe_strings(self.supporting_finding_ids)
        self.affected_families = _dedupe_strings(self.affected_families)
        self.affected_sources = _dedupe_strings(self.affected_sources)
        self.affected_scene_cfg_names = _dedupe_strings(self.affected_scene_cfg_names)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SemanticClaim":
        return cls(
            claim_id=str(payload.get("claim_id", "")),
            claim_type=payload.get("claim_type", "unknown"),
            confidence=payload.get("confidence", 0.0),
            severity=payload.get("severity", "warning"),
            summary=str(payload.get("summary", "")),
            rationale=str(payload.get("rationale", "")),
            status=payload.get("status", "weak"),
            supporting_evidence_ids=list(payload.get("supporting_evidence_ids", []) or []),
            supporting_witness_ids=list(payload.get("supporting_witness_ids", []) or []),
            supporting_finding_ids=list(payload.get("supporting_finding_ids", []) or []),
            affected_families=list(payload.get("affected_families", []) or []),
            affected_sources=list(payload.get("affected_sources", []) or []),
            affected_scene_cfg_names=list(payload.get("affected_scene_cfg_names", []) or []),
            repair_direction_hint=str(payload.get("repair_direction_hint", "")),
            provider_metadata=dict(payload.get("provider_metadata", {}) or {}),
        )


@dataclass
class SemanticCrossCheckResult:
    """Minimal cross-check status for a semantic claim."""

    claim_id: str
    passed: bool
    support_status: str
    messages: List[str] = field(default_factory=list)
    matched_evidence_ids: List[str] = field(default_factory=list)
    matched_witness_ids: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.support_status = normalize_claim_status(self.support_status)
        self.messages = _dedupe_strings(self.messages)
        self.matched_evidence_ids = _dedupe_strings(self.matched_evidence_ids)
        self.matched_witness_ids = _dedupe_strings(self.matched_witness_ids)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SemanticClaimSet:
    """Collection of semantic claims grouped by support status."""

    claim_set_type: str = "semantic_claim_set.v1"
    supported_claims: List[SemanticClaim] = field(default_factory=list)
    weak_claims: List[SemanticClaim] = field(default_factory=list)
    rejected_claims: List[SemanticClaim] = field(default_factory=list)
    cross_checks: List[SemanticCrossCheckResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_set_type": self.claim_set_type,
            "supported_claims": [item.to_dict() for item in self.supported_claims],
            "weak_claims": [item.to_dict() for item in self.weak_claims],
            "rejected_claims": [item.to_dict() for item in self.rejected_claims],
            "cross_checks": [item.to_dict() for item in self.cross_checks],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SemanticClaimSet":
        return cls(
            claim_set_type=str(payload.get("claim_set_type", "semantic_claim_set.v1")),
            supported_claims=[
                SemanticClaim.from_dict(item)
                for item in (payload.get("supported_claims") or [])
            ],
            weak_claims=[
                SemanticClaim.from_dict(item)
                for item in (payload.get("weak_claims") or [])
            ],
            rejected_claims=[
                SemanticClaim.from_dict(item)
                for item in (payload.get("rejected_claims") or [])
            ],
            cross_checks=[
                SemanticCrossCheckResult(**dict(item))
                for item in (payload.get("cross_checks") or [])
            ],
            metadata=dict(payload.get("metadata", {}) or {}),
        )


__all__ = [
    "CANONICAL_CLAIM_STATUSES",
    "CANONICAL_CLAIM_TYPES",
    "CANONICAL_SEVERITIES",
    "SemanticClaim",
    "SemanticClaimSet",
    "SemanticCrossCheckResult",
    "normalize_claim_status",
    "normalize_claim_type",
    "normalize_confidence",
    "normalize_severity",
]
