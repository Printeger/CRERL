"""Repair-layer package for CRE patch generation and validation."""

from repair.acceptance import SUPPORTED_OPERATOR_TYPES, accept_repair
from repair.patch_executor import REPAIR_NAMESPACE, run_repair_bundle_write, write_repair_bundle
from repair.proposal_schema import (
    RepairBundleSummary,
    RepairCandidate,
    RepairPlan,
    SpecPatch,
    SpecPatchOperation,
)
from repair.repair_validator import build_phase9_validation_request, validate_repair
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
    "REPAIR_NAMESPACE",
    "SUPPORTED_OPERATOR_TYPES",
    "accept_repair",
    "build_phase9_validation_request",
    "build_repair_candidates",
    "load_phase7_repair_inputs",
    "propose_rule_based_repairs",
    "run_repair_bundle_write",
    "validate_repair",
    "write_repair_bundle",
]
