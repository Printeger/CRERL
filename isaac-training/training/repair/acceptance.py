"""Repair proposal preflight acceptance checks for Phase 8."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping


SEVERITY_ORDER = {
    "info": 0,
    "warning": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

SUPPORTED_OPERATOR_TYPES = {
    "reduce_progress_proxy_weight",
    "strengthen_safety_reward",
    "strengthen_height_penalty",
    "increase_critical_route_bias",
    "increase_critical_template_floor",
    "increase_shifted_boundary_bias",
    "enable_shifted_dynamic_hazards",
}


def _severity_rank(value: str) -> int:
    return SEVERITY_ORDER.get(str(value).lower(), 0)


def _append_check(checks: List[Dict[str, Any]], *, check_id: str, passed: bool, severity: str, summary: str, details=None):
    checks.append(
        {
            "check_id": check_id,
            "passed": bool(passed),
            "severity": severity,
            "summary": summary,
            "details": dict(details or {}),
        }
    )


def accept_repair(plan: Mapping[str, Any]) -> Dict[str, Any]:
    """Run lightweight Phase 8 preflight checks over a repair plan."""

    checks: List[Dict[str, Any]] = []
    candidates = list(plan.get("candidates", []) or [])
    selected_candidate_id = str(plan.get("selected_candidate_id", ""))
    selected_patch = dict(plan.get("selected_patch") or {})
    primary_claim_type = str(plan.get("primary_claim_type", ""))

    _append_check(
        checks,
        check_id="selected_candidate_present",
        passed=bool(selected_candidate_id),
        severity="high",
        summary="Repair plan selects a primary candidate.",
    )
    _append_check(
        checks,
        check_id="selected_patch_present",
        passed=bool(selected_patch),
        severity="high",
        summary="Repair plan includes a selected patch preview.",
    )

    selected_candidate = next(
        (item for item in candidates if str(item.get("candidate_id", "")) == selected_candidate_id),
        None,
    )
    _append_check(
        checks,
        check_id="selected_candidate_resolves",
        passed=selected_candidate is not None,
        severity="high",
        summary="Selected candidate id resolves inside the candidate set.",
    )

    if selected_candidate is not None:
        _append_check(
            checks,
            check_id="primary_claim_alignment",
            passed=str(selected_candidate.get("claim_type", "")) == primary_claim_type,
            severity="medium",
            summary="Selected candidate is aligned with the primary Phase 7 claim type.",
            details={
                "candidate_claim_type": str(selected_candidate.get("claim_type", "")),
                "primary_claim_type": primary_claim_type,
            },
        )
        _append_check(
            checks,
            check_id="supported_operator_type",
            passed=str(selected_candidate.get("operator_type", "")) in SUPPORTED_OPERATOR_TYPES,
            severity="high",
            summary="Selected candidate operator belongs to the supported Phase 8 repair library.",
            details={"operator_type": str(selected_candidate.get("operator_type", ""))},
        )
        _append_check(
            checks,
            check_id="validation_targets_declared",
            passed=bool(list(plan.get("validation_targets", []) or [])),
            severity="medium",
            summary="Repair plan declares the Phase 9 metrics it expects to improve.",
        )

    patch_operations = list(selected_patch.get("operations", []) or [])
    _append_check(
        checks,
        check_id="patch_has_operations",
        passed=bool(patch_operations),
        severity="high",
        summary="Selected patch contains at least one explicit operation.",
    )
    _append_check(
        checks,
        check_id="patch_is_minimal_preview",
        passed=len(patch_operations) <= 4,
        severity="medium",
        summary="Selected patch remains a small structured preview rather than a broad uncontrolled mutation.",
        details={"operation_count": len(patch_operations)},
    )

    missing_files: List[str] = []
    for entry in patch_operations:
        target_file = entry.get("target_file")
        if not target_file:
            missing_files.append("")
            continue
        if not Path(target_file).is_absolute():
            target_file = str((Path(__file__).resolve().parents[3] / str(target_file)).resolve())
        if not Path(str(target_file)).exists():
            missing_files.append(str(entry.get("target_file", "")))
    _append_check(
        checks,
        check_id="patch_target_files_exist",
        passed=not missing_files,
        severity="high",
        summary="All patch target files exist in the repo.",
        details={"missing_files": missing_files},
    )

    non_empty_paths = all(bool(str(entry.get("target_path", "")).strip()) for entry in patch_operations)
    _append_check(
        checks,
        check_id="patch_target_paths_declared",
        passed=non_empty_paths if patch_operations else False,
        severity="medium",
        summary="All patch operations specify a concrete target path.",
    )

    failing_checks = [item for item in checks if not item["passed"]]
    max_severity = "info"
    if failing_checks:
        max_severity = max(failing_checks, key=lambda item: _severity_rank(item["severity"]))["severity"]
    passed = not any(_severity_rank(item["severity"]) >= _severity_rank("high") for item in failing_checks)
    return {
        "acceptance_type": "phase8_repair_acceptance.v1",
        "passed": passed,
        "max_severity": max_severity,
        "num_checks": len(checks),
        "failed_check_count": len(failing_checks),
        "checks": checks,
        "selected_candidate_id": selected_candidate_id,
        "primary_claim_type": primary_claim_type,
    }


__all__ = ["accept_repair", "SUPPORTED_OPERATOR_TYPES"]
