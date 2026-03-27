"""Repair-plan validation and Phase 9 handoff construction for Phase 8."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


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


def _append_check(
    checks: List[Dict[str, Any]],
    *,
    check_id: str,
    passed: bool,
    severity: str,
    summary: str,
    details: Mapping[str, Any] | None = None,
) -> None:
    checks.append(
        {
            "check_id": check_id,
            "passed": bool(passed),
            "severity": severity,
            "summary": summary,
            "details": dict(details or {}),
        }
    )


def _stable_unique(values: Sequence[Any]) -> List[str]:
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


def _infer_execution_modes(source_report_bundle: str) -> List[str]:
    lowered = str(source_report_bundle).lower()
    if "baseline" in lowered:
        return ["baseline"]
    if "eval" in lowered:
        return ["eval"]
    if "train" in lowered:
        return ["train"]
    return ["baseline", "eval"]


def _infer_scene_family_scope(primary_claim_type: str) -> List[str]:
    if primary_claim_type == "C-R":
        return ["nominal", "boundary_critical"]
    if primary_claim_type == "E-C":
        return ["boundary_critical"]
    if primary_claim_type == "E-R":
        return ["nominal", "shifted"]
    return ["nominal"]


def validate_repair(
    plan: Mapping[str, Any],
    *,
    acceptance: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Validate that a generated repair plan is internally coherent and Phase-9 ready."""

    checks: List[Dict[str, Any]] = []
    candidates = list(plan.get("candidates", []) or [])
    selected_candidate_id = str(plan.get("selected_candidate_id", ""))
    selected_patch = dict(plan.get("selected_patch") or {})
    validation_targets = list(plan.get("validation_targets", []) or [])
    primary_claim_type = str(plan.get("primary_claim_type", ""))
    acceptance_passed = bool((acceptance or {}).get("passed", False))

    selected_candidate = next(
        (item for item in candidates if str(item.get("candidate_id", "")) == selected_candidate_id),
        None,
    )
    patch_operations = list(selected_patch.get("operations", []) or [])
    selected_patch_id = str(selected_patch.get("patch_id", ""))

    _append_check(
        checks,
        check_id="selected_candidate_exists",
        passed=selected_candidate is not None,
        severity="high",
        summary="Selected candidate id resolves to a candidate in the repair plan.",
    )
    _append_check(
        checks,
        check_id="selected_patch_exists",
        passed=bool(selected_patch_id),
        severity="high",
        summary="Repair plan includes a selected structured patch.",
    )

    if selected_candidate is not None:
        candidate_patch = dict(selected_candidate.get("patch") or {})
        _append_check(
            checks,
            check_id="selected_patch_matches_candidate_patch",
            passed=str(candidate_patch.get("patch_id", "")) == selected_patch_id,
            severity="high",
            summary="Selected patch preview matches the patch attached to the selected candidate.",
            details={
                "candidate_patch_id": str(candidate_patch.get("patch_id", "")),
                "selected_patch_id": selected_patch_id,
            },
        )
        _append_check(
            checks,
            check_id="operator_within_supported_library",
            passed=str(selected_candidate.get("operator_type", "")) in SUPPORTED_OPERATOR_TYPES,
            severity="high",
            summary="Selected repair operator remains inside the supported Phase 8 repair library.",
            details={"operator_type": str(selected_candidate.get("operator_type", ""))},
        )
        _append_check(
            checks,
            check_id="primary_claim_alignment",
            passed=str(selected_candidate.get("claim_type", "")) == primary_claim_type,
            severity="medium",
            summary="Selected candidate remains aligned with the primary Phase 7 claim type.",
            details={
                "candidate_claim_type": str(selected_candidate.get("claim_type", "")),
                "primary_claim_type": primary_claim_type,
            },
        )
        _append_check(
            checks,
            check_id="expected_metric_direction_declared",
            passed=bool(list(selected_candidate.get("expected_metric_direction", []) or [])),
            severity="medium",
            summary="Selected candidate declares the metric directions that Phase 9 should check.",
        )

    operation_targets = _stable_unique(item.get("target_path", "") for item in patch_operations)
    operation_files = _stable_unique(item.get("target_file", "") for item in patch_operations)
    operation_changes = [item for item in patch_operations if item.get("before") != item.get("after")]
    _append_check(
        checks,
        check_id="patch_has_operations",
        passed=bool(patch_operations),
        severity="high",
        summary="Selected patch contains explicit operations.",
    )
    _append_check(
        checks,
        check_id="patch_operations_are_effective",
        passed=bool(operation_changes),
        severity="medium",
        summary="Selected patch preview changes at least one concrete value.",
        details={"effective_operations": len(operation_changes)},
    )
    _append_check(
        checks,
        check_id="patch_targets_declared",
        passed=bool(operation_targets and operation_files),
        severity="medium",
        summary="Selected patch preview exposes concrete target files and target paths.",
        details={
            "target_files": operation_files,
            "target_paths": operation_targets,
        },
    )
    _append_check(
        checks,
        check_id="phase9_validation_targets_declared",
        passed=bool(validation_targets),
        severity="high",
        summary="Repair plan declares explicit Phase 9 validation targets.",
        details={"validation_targets": validation_targets},
    )
    _append_check(
        checks,
        check_id="acceptance_preflight_passed",
        passed=acceptance_passed,
        severity="medium",
        summary="Repair plan passed the Phase 8 preflight acceptance gate before Phase 9 handoff.",
    )

    failing_checks = [item for item in checks if not item["passed"]]
    max_severity = "info"
    if failing_checks:
        max_severity = max(failing_checks, key=lambda item: _severity_rank(item["severity"]))["severity"]
    passed = not any(_severity_rank(item["severity"]) >= _severity_rank("high") for item in failing_checks)
    return {
        "validation_type": "phase8_repair_validator.v1",
        "passed": passed,
        "phase9_ready": passed and acceptance_passed,
        "max_severity": max_severity,
        "num_checks": len(checks),
        "failed_check_count": len(failing_checks),
        "checks": checks,
        "primary_claim_type": primary_claim_type,
        "selected_candidate_id": selected_candidate_id,
        "target_files": operation_files,
        "target_paths": operation_targets,
        "validation_targets": list(validation_targets),
    }


def build_phase9_validation_request(
    plan: Mapping[str, Any],
    *,
    repair_validation: Mapping[str, Any],
    acceptance: Mapping[str, Any] | None = None,
    bundle_name: str = "repair_latest",
    repair_namespace: str = "analysis/repair",
) -> Dict[str, Any]:
    """Build a deterministic Phase 9 handoff artifact from a Phase 8 repair plan."""

    candidates = list(plan.get("candidates", []) or [])
    selected_candidate_id = str(plan.get("selected_candidate_id", ""))
    selected_candidate = next(
        (item for item in candidates if str(item.get("candidate_id", "")) == selected_candidate_id),
        None,
    )
    selected_patch = dict(plan.get("selected_patch") or {})
    patch_operations = list(selected_patch.get("operations", []) or [])
    target_files = _stable_unique(item.get("target_file", "") for item in patch_operations)
    target_paths = _stable_unique(item.get("target_path", "") for item in patch_operations)

    return {
        "request_type": "phase9_validation_request.v1",
        "phase9_entrypoint": "repair_validation_loop.v1",
        "repair_bundle_name": bundle_name,
        "repair_namespace": repair_namespace,
        "phase9_ready": bool(repair_validation.get("phase9_ready", False)),
        "source_report_bundle": str(plan.get("source_report_bundle", "")),
        "primary_claim_type": str(plan.get("primary_claim_type", "")),
        "primary_repair_direction": str(plan.get("primary_repair_direction", "")),
        "selected_candidate_id": selected_candidate_id,
        "selected_operator_type": str((selected_candidate or {}).get("operator_type", "")),
        "selected_target_component": str((selected_candidate or {}).get("target_component", "")),
        "selected_target_files": target_files,
        "selected_target_paths": target_paths,
        "preferred_execution_modes": _infer_execution_modes(str(plan.get("source_report_bundle", ""))),
        "scene_family_scope": _infer_scene_family_scope(str(plan.get("primary_claim_type", ""))),
        "comparison_mode": "pre_post_targeted_rerun.v1",
        "validation_targets": list(plan.get("validation_targets", []) or []),
        "expected_metric_direction": list((selected_candidate or {}).get("expected_metric_direction", []) or []),
        "evidence_refs": list((selected_candidate or {}).get("evidence_refs", []) or []),
        "required_upstream_artifacts": [
            "analysis/report/<bundle>/repair_handoff.json",
            "analysis/report/<bundle>/report.json",
            "analysis/repair/<bundle>/repair_plan.json",
            "analysis/repair/<bundle>/spec_patch.json",
            "analysis/repair/<bundle>/repair_validation.json",
        ],
        "cross_phase_contract": {
            "phase7_input": "repair_handoff.json",
            "phase8_bundle": "repair_plan.json",
            "phase9_request": "validation_request.json",
        },
        "acceptance_passed": bool((acceptance or {}).get("passed", False)),
        "repair_validation_passed": bool(repair_validation.get("passed", False)),
    }


__all__ = [
    "SUPPORTED_OPERATOR_TYPES",
    "build_phase9_validation_request",
    "validate_repair",
]
