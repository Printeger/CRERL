"""Repair-layer package for CRE patch generation and validation."""

from repair.proposal_schema import (
    RepairBundleSummary,
    RepairCandidate,
    RepairPlan,
    SpecPatch,
    SpecPatchOperation,
)
from repair.rule_based_repair import (
    build_repair_candidates,
    load_phase7_repair_inputs,
    propose_rule_based_repairs,
)

__all__ = [
    "RepairBundleSummary",
    "RepairCandidate",
    "RepairPlan",
    "SpecPatch",
    "SpecPatchOperation",
    "build_repair_candidates",
    "load_phase7_repair_inputs",
    "propose_rule_based_repairs",
]
