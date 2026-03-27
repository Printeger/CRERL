"""Structured repair proposal schema for Phase 8."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class SpecPatchOperation:
    """One explicit config/spec delta in a repair patch."""

    operation_id: str
    target_file: str
    target_path: str
    operation: str
    before: Any = None
    after: Any = None
    rationale: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SpecPatch:
    """Structured preview patch for a candidate repair."""

    patch_id: str
    patch_type: str
    target_component: str
    target_file: str
    operations: List[SpecPatchOperation] = field(default_factory=list)
    rationale: str = ""
    expected_metric_direction: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["operations"] = [item.to_dict() for item in self.operations]
        return payload


@dataclass
class RepairCandidate:
    """A repair candidate derived from one ranked repair-ready claim."""

    candidate_id: str
    origin_claim_id: str
    claim_type: str
    target_component: str
    operator_type: str
    priority: int
    selection_score: float
    estimated_edit_cost: float
    expected_metric_direction: List[str] = field(default_factory=list)
    rationale: str = ""
    target_file: str = ""
    target_paths: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    source_record_ids: List[str] = field(default_factory=list)
    patch: SpecPatch | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["patch"] = self.patch.to_dict() if self.patch is not None else None
        return payload


@dataclass
class RepairPlan:
    """Canonical Phase 8 repair plan bundle payload."""

    plan_type: str
    source_report_bundle: str
    primary_claim_type: str
    primary_repair_direction: str
    selected_candidate_id: str
    selected_claim_ids: List[str] = field(default_factory=list)
    candidates: List[RepairCandidate] = field(default_factory=list)
    selected_patch: SpecPatch | None = None
    rationale: str = ""
    validation_targets: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["candidates"] = [item.to_dict() for item in self.candidates]
        payload["selected_patch"] = self.selected_patch.to_dict() if self.selected_patch is not None else None
        return payload


@dataclass
class RepairBundleSummary:
    """Compact summary written alongside a repair plan bundle."""

    bundle_type: str
    plan_type: str
    primary_claim_type: str
    selected_candidate_id: str
    candidate_count: int
    validation_targets: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


__all__ = [
    "RepairBundleSummary",
    "RepairCandidate",
    "RepairPlan",
    "SpecPatch",
    "SpecPatchOperation",
]
