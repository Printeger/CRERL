"""Repair-layer package for CRE patch generation and validation."""

from repair.acceptance import SUPPORTED_OPERATOR_TYPES, accept_repair
from repair.comparison import compare_validation_runs
from repair.decision import decide_validation
from repair.patch_executor import (
    REPAIR_NAMESPACE,
    build_validation_context_preview,
    run_repair_bundle_write,
    write_repair_bundle,
)
from repair.proposal_schema import (
    RepairBundleSummary,
    RepairCandidate,
    RepairPlan,
    SpecPatch,
    SpecPatchOperation,
)
from repair.repair_validator import build_phase9_validation_request, validate_repair
from repair.validation_request_loader import REQUIRED_REPAIR_BUNDLE_ARTIFACTS, load_validation_request_bundle
from repair.validation_runner import (
    VALIDATION_NAMESPACE,
    build_validation_rerun_tasks,
    prepare_validation_runs,
    preview_rerun_runner,
    run_validation_bundle_write,
    trigger_targeted_reruns,
    write_validation_bundle,
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
    "REQUIRED_REPAIR_BUNDLE_ARTIFACTS",
    "REPAIR_NAMESPACE",
    "VALIDATION_NAMESPACE",
    "SUPPORTED_OPERATOR_TYPES",
    "accept_repair",
    "build_phase9_validation_request",
    "build_validation_rerun_tasks",
    "build_validation_context_preview",
    "build_repair_candidates",
    "compare_validation_runs",
    "decide_validation",
    "load_phase7_repair_inputs",
    "load_validation_request_bundle",
    "prepare_validation_runs",
    "preview_rerun_runner",
    "propose_rule_based_repairs",
    "run_repair_bundle_write",
    "run_validation_bundle_write",
    "trigger_targeted_reruns",
    "validate_repair",
    "write_validation_bundle",
    "write_repair_bundle",
]
