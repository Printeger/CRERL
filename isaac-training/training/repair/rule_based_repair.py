"""Rule-based Phase 8 repair candidate generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from repair.proposal_schema import (
    RepairCandidate,
    RepairPlan,
    SpecPatch,
    SpecPatchOperation,
)

try:
    import yaml
except Exception:  # pragma: no cover - environment fallback
    yaml = None


REPO_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_TARGET_FILES = {
    "C-R": REPO_ROOT / "isaac-training" / "training" / "cfg" / "spec_cfg" / "reward_spec_v0.yaml",
    "E-C": REPO_ROOT / "isaac-training" / "training" / "cfg" / "env_cfg" / "scene_cfg_boundary_critical.yaml",
    "E-R": REPO_ROOT / "isaac-training" / "training" / "cfg" / "env_cfg" / "scene_cfg_shifted.yaml",
}

DEFAULT_VALIDATION_TARGETS = {
    "C-R": ["W_CR", "min_distance", "near_violation_ratio"],
    "E-C": ["W_EC", "boundary_critical_success_rate", "critical_family_min_distance"],
    "E-R": ["W_ER", "nominal_vs_shifted_success_gap", "shifted_min_distance"],
}

CLAIM_TYPE_TO_COMPONENT = {
    "C-R": "R",
    "E-C": "E",
    "E-R": "E",
}

SUPPORT_SCORE = {
    "machine_direct": 1.0,
    "machine_derived": 0.85,
    "semantic_supported": 0.75,
    "semantic_weak": 0.35,
    "semantic_rejected": 0.05,
}

SEVERITY_SCORE = {
    "info": 0.2,
    "warning": 0.4,
    "medium": 0.6,
    "high": 0.8,
    "critical": 1.0,
}


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except Exception:
        return str(path)


def _json_load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _yaml_load(path: Path) -> Any:
    if yaml is None or not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _get_path_value(payload: Any, dotted_path: str) -> Any:
    current = payload
    for part in dotted_path.split("."):
        if isinstance(current, Mapping):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            if index >= len(current):
                return None
            current = current[index]
        else:
            return None
    return current


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


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def load_phase7_repair_inputs(report_bundle_dir: str | Path) -> Dict[str, Any]:
    bundle_dir = Path(report_bundle_dir)
    manifest = _json_load(bundle_dir / "manifest.json")
    summary = _json_load(bundle_dir / "summary.json")
    report = _json_load(bundle_dir / "report.json")
    repair_handoff = _json_load(bundle_dir / "repair_handoff.json")
    return {
        "bundle_dir": bundle_dir,
        "bundle_name": str(manifest.get("metadata", {}).get("bundle_name", bundle_dir.name)),
        "manifest": manifest,
        "summary": summary,
        "report": report,
        "repair_handoff": repair_handoff,
    }


def _choose_target_file(claim_type: str, claim: Mapping[str, Any]) -> Path:
    for ref in claim.get("required_evidence_refs", []) or []:
        try:
            candidate = Path(str(ref))
        except Exception:
            continue
        if candidate.suffix in {".yaml", ".yml"} and candidate.exists():
            return candidate
    return DEFAULT_TARGET_FILES[claim_type]


def _make_operation(
    *,
    candidate_id: str,
    target_file: Path,
    target_path: str,
    after: Any,
    rationale: str,
) -> SpecPatchOperation:
    payload = _yaml_load(target_file)
    before = _get_path_value(payload, target_path) if payload is not None else None
    return SpecPatchOperation(
        operation_id=f"{candidate_id}:{target_path}",
        target_file=_repo_relative(target_file),
        target_path=target_path,
        operation="set",
        before=before,
        after=after,
        rationale=rationale,
    )


def _build_cr_candidates(claim: Mapping[str, Any], *, primary_claim_type: str) -> List[Dict[str, Any]]:
    summary = str(claim.get("summary", "")).lower()
    evidence_refs = [str(item).lower() for item in claim.get("required_evidence_refs", []) or []]
    items: List[Dict[str, Any]] = []
    if "proxy" in summary or any("reward_progress" in item for item in evidence_refs):
        items.append(
            {
                "operator_type": "reduce_progress_proxy_weight",
                "target_file": DEFAULT_TARGET_FILES["C-R"],
                "operations": [
                    {
                        "target_path": "components.reward_progress.weight",
                        "transform": lambda old: round(max(0.2, _as_float(old, 1.0) * 0.8), 4),
                        "rationale": "Reduce progress dominance so safety-oriented terms can influence policy behavior more strongly.",
                    }
                ],
                "expected_metric_direction": ["decrease_W_CR", "reduce_boundary_seeking"],
                "estimated_edit_cost": 1.0,
            }
        )
    items.append(
        {
            "operator_type": "strengthen_safety_reward",
            "target_file": DEFAULT_TARGET_FILES["C-R"],
            "operations": [
                {
                    "target_path": "components.reward_safety_static.weight",
                    "transform": lambda old: round(_as_float(old, 1.0) + 0.5, 4),
                    "rationale": "Increase static-obstacle safety shaping to better support the declared clearance constraint.",
                }
            ],
            "expected_metric_direction": ["decrease_W_CR", "increase_min_distance"],
            "estimated_edit_cost": 1.0,
        }
    )
    items.append(
        {
            "operator_type": "strengthen_height_penalty",
            "target_file": DEFAULT_TARGET_FILES["C-R"],
            "operations": [
                {
                    "target_path": "components.penalty_height.weight",
                    "transform": lambda old: round(_as_float(old, -8.0) * 1.1, 4),
                    "rationale": "Increase boundary-aware height penalty magnitude in a minimal way.",
                }
            ],
            "expected_metric_direction": ["decrease_W_CR", "decrease_out_of_bounds_rate"],
            "estimated_edit_cost": 1.2,
        }
    )
    return items


def _build_ec_candidates(claim: Mapping[str, Any], *, primary_claim_type: str) -> List[Dict[str, Any]]:
    target_file = DEFAULT_TARGET_FILES["E-C"]
    items: List[Dict[str, Any]] = [
        {
            "operator_type": "increase_critical_route_bias",
            "target_file": target_file,
            "operations": [
                {
                    "target_path": "distribution_modes.route_adjacent_bias",
                    "transform": lambda old: round(_clamp(_as_float(old, 0.55) + 0.1, 0.0, 0.9), 4),
                    "rationale": "Bias obstacle structure closer to routes to inject more critical scenarios.",
                }
            ],
            "expected_metric_direction": ["decrease_W_EC", "increase_critical_family_coverage"],
            "estimated_edit_cost": 1.0,
        },
        {
            "operator_type": "increase_critical_template_floor",
            "target_file": target_file,
            "operations": [
                {
                    "target_path": "templates.min_templates_per_scene",
                    "transform": lambda old: int(_as_float(old, 1.0) + 1),
                    "rationale": "Require at least one more structured template to make critical-family scenes denser and more diagnostic.",
                }
            ],
            "expected_metric_direction": ["decrease_W_EC", "increase_critical_family_coverage"],
            "estimated_edit_cost": 1.1,
        },
    ]
    return items


def _build_er_candidates(claim: Mapping[str, Any], *, primary_claim_type: str) -> List[Dict[str, Any]]:
    target_file = DEFAULT_TARGET_FILES["E-R"]
    items: List[Dict[str, Any]] = [
        {
            "operator_type": "increase_shifted_boundary_bias",
            "target_file": target_file,
            "operations": [
                {
                    "target_path": "distribution_modes.boundary_adjacent_bias",
                    "transform": lambda old: round(_clamp(_as_float(old, 0.05) + 0.1, 0.0, 0.5), 4),
                    "rationale": "Make shifted scenes place more structure near boundary regions to better represent robustness stress.",
                }
            ],
            "expected_metric_direction": ["decrease_W_ER", "reduce_shifted_gap"],
            "estimated_edit_cost": 1.0,
        },
        {
            "operator_type": "enable_shifted_dynamic_hazards",
            "target_file": target_file,
            "operations": [
                {
                    "target_path": "dynamic_obstacles.enabled",
                    "transform": lambda old: True,
                    "rationale": "Enable dynamic hazards in the shifted family to make robustness stress explicit.",
                },
                {
                    "target_path": "dynamic_obstacles.max_dynamic_count",
                    "transform": lambda old: max(int(_as_float(old, 0.0)), 2),
                    "rationale": "Ensure the shifted family includes a small but non-zero dynamic obstacle budget.",
                },
            ],
            "expected_metric_direction": ["decrease_W_ER", "reduce_shifted_gap"],
            "estimated_edit_cost": 1.4,
        },
    ]
    return items


def _operator_specs_for_claim(claim: Mapping[str, Any], *, primary_claim_type: str) -> List[Dict[str, Any]]:
    claim_type = str(claim.get("claim_type", ""))
    if claim_type == "C-R":
        return _build_cr_candidates(claim, primary_claim_type=primary_claim_type)
    if claim_type == "E-C":
        return _build_ec_candidates(claim, primary_claim_type=primary_claim_type)
    if claim_type == "E-R":
        return _build_er_candidates(claim, primary_claim_type=primary_claim_type)
    return []


def _candidate_score(
    claim: Mapping[str, Any],
    spec: Mapping[str, Any],
    *,
    primary_claim_type: str,
) -> float:
    claim_type = str(claim.get("claim_type", ""))
    severity = str(claim.get("severity", "warning")).lower()
    confidence = _as_float(claim.get("confidence", 0.5), 0.5)
    support_status = str(claim.get("support_status", "machine_direct"))
    rank = int(claim.get("selected_from_rank", 99) or 99)
    edit_cost = float(spec.get("estimated_edit_cost", 1.0))
    operator_preference = float(spec.get("operator_preference", 0.0))
    return round(
        (1.0 if claim_type == primary_claim_type else 0.0) * 50.0
        + SUPPORT_SCORE.get(support_status, 0.2) * 20.0
        + SEVERITY_SCORE.get(severity, 0.4) * 15.0
        + confidence * 10.0
        + max(0.0, 10.0 - min(rank, 10))
        + operator_preference
        - edit_cost * 5.0,
        6,
    )


def _build_candidate(
    claim: Mapping[str, Any],
    spec: Mapping[str, Any],
    *,
    candidate_index: int,
    primary_claim_type: str,
) -> RepairCandidate:
    claim_type = str(claim.get("claim_type", ""))
    claim_id = str(claim.get("handoff_id") or claim.get("claim_id") or f"claim:{candidate_index}")
    target_file = Path(spec["target_file"])
    operations: List[SpecPatchOperation] = []
    for op_index, op_spec in enumerate(spec.get("operations", []) or [], start=1):
        payload = _yaml_load(target_file)
        before = _get_path_value(payload, op_spec["target_path"]) if payload is not None else None
        after = op_spec["transform"](before)
        operations.append(
            SpecPatchOperation(
                operation_id=f"{claim_id}:{spec['operator_type']}:{op_index}",
                target_file=_repo_relative(target_file),
                target_path=str(op_spec["target_path"]),
                operation="set",
                before=before,
                after=after,
                rationale=str(op_spec["rationale"]),
            )
        )
    patch = SpecPatch(
        patch_id=f"patch:{claim_id}:{spec['operator_type']}",
        patch_type="phase8_spec_patch.v1",
        target_component=CLAIM_TYPE_TO_COMPONENT.get(claim_type, "unknown"),
        target_file=_repo_relative(target_file),
        operations=operations,
        rationale=" ".join(item.rationale for item in operations),
        expected_metric_direction=list(spec.get("expected_metric_direction", []) or []),
        metadata={
            "preview_only": True,
            "origin_claim_type": claim_type,
            "operator_type": str(spec["operator_type"]),
        },
    )
    score = _candidate_score(claim, spec, primary_claim_type=primary_claim_type)
    return RepairCandidate(
        candidate_id=f"candidate:{claim_id}:{spec['operator_type']}",
        origin_claim_id=claim_id,
        claim_type=claim_type,
        target_component=CLAIM_TYPE_TO_COMPONENT.get(claim_type, "unknown"),
        operator_type=str(spec["operator_type"]),
        priority=-1,
        selection_score=score,
        estimated_edit_cost=float(spec.get("estimated_edit_cost", 1.0)),
        expected_metric_direction=list(spec.get("expected_metric_direction", []) or []),
        rationale=" ".join(item.rationale for item in operations),
        target_file=_repo_relative(target_file),
        target_paths=[item.target_path for item in operations],
        evidence_refs=_stable_unique(claim.get("required_evidence_refs", []) or []),
        source_record_ids=_stable_unique(claim.get("source_record_ids", []) or [claim_id]),
        patch=patch,
        metadata={
            "selected_from": str(claim.get("selected_from", "")),
            "selected_from_rank": int(claim.get("selected_from_rank", -1) or -1),
            "support_status": str(claim.get("support_status", "")),
            "selection_basis": str(claim.get("selection_basis", "")),
        },
    )


def build_repair_candidates(repair_handoff: Mapping[str, Any]) -> List[RepairCandidate]:
    primary_claim_type = str(repair_handoff.get("primary_claim_type", ""))
    selected_claims = list(repair_handoff.get("selected_claims", []) or [])
    candidates: List[RepairCandidate] = []
    seen = set()
    for claim_index, claim in enumerate(selected_claims, start=1):
        for operator_rank, spec in enumerate(
            _operator_specs_for_claim(claim, primary_claim_type=primary_claim_type),
            start=1,
        ):
            spec = dict(spec)
            spec["operator_preference"] = max(0.0, 1.0 - 0.05 * float(operator_rank - 1))
            key = (
                str(claim.get("handoff_id", "")),
                str(spec["operator_type"]),
                _repo_relative(Path(spec["target_file"])),
                tuple(op["target_path"] for op in spec.get("operations", []) or []),
            )
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                _build_candidate(
                    claim,
                    spec,
                    candidate_index=claim_index,
                    primary_claim_type=primary_claim_type,
                )
            )
    ordered = sorted(
        candidates,
        key=lambda item: (
            item.selection_score,
            -item.estimated_edit_cost,
            item.candidate_id,
        ),
        reverse=True,
    )
    for priority, item in enumerate(ordered, start=1):
        item.priority = priority
    return ordered


def propose_rule_based_repairs(
    *,
    report_bundle_dir: str | Path | None = None,
    report: Mapping[str, Any] | None = None,
    repair_handoff: Mapping[str, Any] | None = None,
    primary_claim_type_override: str = "",
) -> RepairPlan:
    if report_bundle_dir is not None:
        bundle_inputs = load_phase7_repair_inputs(report_bundle_dir)
        effective_report = dict(bundle_inputs["report"])
        effective_handoff = dict(bundle_inputs["repair_handoff"])
        source_report_bundle = str(bundle_inputs["manifest"].get("metadata", {}).get("bundle_name", bundle_inputs["bundle_dir"].name))
    else:
        effective_report = dict(report or {})
        effective_handoff = dict(repair_handoff or {})
        source_report_bundle = str(effective_report.get("bundle_name", "report_inline"))

    if primary_claim_type_override:
        effective_handoff["primary_claim_type"] = str(primary_claim_type_override)

    candidates = build_repair_candidates(effective_handoff)
    selected_candidate = candidates[0] if candidates else None
    primary_claim_type = str(effective_handoff.get("primary_claim_type", ""))
    primary_repair_direction = str(effective_handoff.get("primary_repair_direction", ""))
    selected_claim_ids = [
        str(item.get("handoff_id", ""))
        for item in list(effective_handoff.get("selected_claims", []) or [])
    ]
    if selected_candidate is not None:
        rationale = (
            f"Selected `{selected_candidate.operator_type}` as the first repair operator for "
            f"`{primary_claim_type}` based on Phase 7 handoff ordering and minimal edit cost."
        )
        if primary_claim_type_override:
            rationale += f" The primary claim type was overridden to `{primary_claim_type_override}` for this repair pass."
    else:
        rationale = "No repair candidates were generated from the provided handoff."
    return RepairPlan(
        plan_type="phase8_repair_plan.v1",
        source_report_bundle=source_report_bundle,
        primary_claim_type=primary_claim_type,
        primary_repair_direction=primary_repair_direction,
        selected_candidate_id=selected_candidate.candidate_id if selected_candidate is not None else "",
        selected_claim_ids=selected_claim_ids,
        candidates=candidates,
        selected_patch=selected_candidate.patch if selected_candidate is not None else None,
        rationale=rationale,
        validation_targets=list(DEFAULT_VALIDATION_TARGETS.get(primary_claim_type, [])),
        metadata={
            "selection_policy": str(effective_handoff.get("selection_policy", "")),
            "selection_focus_order": list(effective_handoff.get("selection_summary", {}).get("selection_focus_order", []) or []),
            "upstream_report_type": str(effective_report.get("report_type", "")),
            "patch_preview_only": True,
            "primary_claim_type_override": str(primary_claim_type_override or ""),
        },
    )


__all__ = [
    "build_repair_candidates",
    "load_phase7_repair_inputs",
    "propose_rule_based_repairs",
]
