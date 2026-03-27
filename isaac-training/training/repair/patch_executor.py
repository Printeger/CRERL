"""Structured Phase 8 repair bundle writer and patch preview helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping

from analyzers.report_contract import (
    DEFAULT_REPORT_NAMESPACES,
    REPAIR_GENERATION_MODE,
    resolve_report_namespace_root,
    write_namespace_manifest,
    write_report_namespace_contract,
)
from repair.proposal_schema import RepairBundleSummary, RepairPlan


REPAIR_NAMESPACE = DEFAULT_REPORT_NAMESPACES[REPAIR_GENERATION_MODE]


def _build_repair_summary_payload(plan: RepairPlan, acceptance: Mapping[str, Any]) -> Dict[str, Any]:
    return RepairBundleSummary(
        bundle_type="repair_generation_bundle.v1",
        plan_type=plan.plan_type,
        primary_claim_type=plan.primary_claim_type,
        selected_candidate_id=plan.selected_candidate_id,
        candidate_count=len(plan.candidates),
        validation_targets=list(plan.validation_targets),
        metadata={
            "passed": bool(acceptance.get("passed", False)),
            "max_severity": str(acceptance.get("max_severity", "info")),
            "primary_repair_direction": str(plan.primary_repair_direction),
        },
    ).to_dict()


def _build_human_summary_markdown(plan: RepairPlan, acceptance: Mapping[str, Any]) -> str:
    selected_patch = plan.selected_patch.to_dict() if plan.selected_patch is not None else {}
    selected_candidate = next(
        (item for item in plan.candidates if item.candidate_id == plan.selected_candidate_id),
        None,
    )
    lines = [
        "# Repair Summary",
        "",
        f"- Plan type: `{plan.plan_type}`",
        f"- Source report bundle: `{plan.source_report_bundle}`",
        f"- Primary claim type: `{plan.primary_claim_type}`",
        f"- Primary repair direction: `{plan.primary_repair_direction}`",
        f"- Acceptance passed: `{bool(acceptance.get('passed', False))}`",
        f"- Acceptance max severity: `{acceptance.get('max_severity', 'info')}`",
        "",
        "## Selected Candidate",
        "",
        f"- Candidate id: `{plan.selected_candidate_id}`",
        f"- Operator type: `{(selected_candidate.operator_type if selected_candidate else '')}`",
        f"- Target component: `{(selected_candidate.target_component if selected_candidate else '')}`",
        f"- Target file: `{(selected_candidate.target_file if selected_candidate else '')}`",
        f"- Estimated edit cost: `{(selected_candidate.estimated_edit_cost if selected_candidate else 0.0)}`",
        "",
        "## Patch Preview",
        "",
        f"- Patch id: `{selected_patch.get('patch_id', '')}`",
        f"- Patch type: `{selected_patch.get('patch_type', '')}`",
        f"- Operations: `{len(selected_patch.get('operations', []) or [])}`",
        "",
        "## Phase 9 Validation Targets",
        "",
    ]
    if plan.validation_targets:
        for item in plan.validation_targets:
            lines.append(f"- `{item}`")
    else:
        lines.append("- No validation targets declared.")
    lines.extend(
        [
            "",
            "## Rationale",
            "",
            plan.rationale or "No rationale recorded.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def write_repair_bundle(
    plan: RepairPlan,
    acceptance: Mapping[str, Any],
    repair_dir: str | Path,
    *,
    namespace_root: str | Path | None = None,
    bundle_name: str = "repair_latest",
    namespace: str = REPAIR_NAMESPACE,
) -> Dict[str, Path]:
    repair_path = Path(repair_dir)
    repair_path.mkdir(parents=True, exist_ok=True)

    repair_plan_path = repair_path / "repair_plan.json"
    repair_candidates_path = repair_path / "repair_candidates.json"
    spec_patch_path = repair_path / "spec_patch.json"
    repair_summary_path = repair_path / "repair_summary.json"
    repair_summary_md_path = repair_path / "repair_summary.md"
    acceptance_path = repair_path / "acceptance.json"
    manifest_path = repair_path / "manifest.json"

    repair_plan_path.write_text(json.dumps(plan.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    repair_candidates_path.write_text(
        json.dumps([item.to_dict() for item in plan.candidates], indent=2, sort_keys=True),
        encoding="utf-8",
    )
    spec_patch_path.write_text(
        json.dumps(plan.selected_patch.to_dict() if plan.selected_patch is not None else {}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    repair_summary_payload = _build_repair_summary_payload(plan, acceptance)
    repair_summary_path.write_text(json.dumps(repair_summary_payload, indent=2, sort_keys=True), encoding="utf-8")
    repair_summary_md_path.write_text(_build_human_summary_markdown(plan, acceptance), encoding="utf-8")
    acceptance_path.write_text(json.dumps(dict(acceptance), indent=2, sort_keys=True), encoding="utf-8")

    manifest_payload = {
        "bundle_type": "repair_generation_bundle.v1",
        "namespace": namespace,
        "plan_type": plan.plan_type,
        "source_report_bundle": plan.source_report_bundle,
        "repair_plan_path": repair_plan_path.name,
        "repair_candidates_path": repair_candidates_path.name,
        "spec_patch_path": spec_patch_path.name,
        "repair_summary_path": repair_summary_path.name,
        "repair_summary_md_path": repair_summary_md_path.name,
        "acceptance_path": acceptance_path.name,
        "selected_candidate_id": plan.selected_candidate_id,
        "primary_claim_type": plan.primary_claim_type,
        "passed": bool(acceptance.get("passed", False)),
        "max_severity": str(acceptance.get("max_severity", "info")),
        "metadata": dict(plan.metadata),
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True), encoding="utf-8")

    bundle_paths: Dict[str, Path] = {
        "report_dir": repair_path,
        "repair_dir": repair_path,
        "repair_plan_path": repair_plan_path,
        "repair_candidates_path": repair_candidates_path,
        "spec_patch_path": spec_patch_path,
        "repair_summary_path": repair_summary_path,
        "repair_summary_md_path": repair_summary_md_path,
        "acceptance_path": acceptance_path,
        "manifest_path": manifest_path,
        "summary_path": repair_summary_path,
    }
    if namespace_root is not None:
        bundle_paths["namespace_manifest_path"] = write_namespace_manifest(
            namespace_root,
            bundle_name=bundle_name,
            report_mode=REPAIR_GENERATION_MODE,
            namespace=namespace,
            bundle_paths=bundle_paths,
            report_summary={
                "passed": bool(acceptance.get("passed", False)),
                "max_severity": str(acceptance.get("max_severity", "info")),
                "primary_claim_type": plan.primary_claim_type,
                "selected_candidate_id": plan.selected_candidate_id,
            },
        )
    return bundle_paths


def run_repair_bundle_write(
    plan: RepairPlan,
    acceptance: Mapping[str, Any],
    *,
    reports_root: str | Path | None = None,
    bundle_name: str = "repair_latest",
    repair_dir: str | Path | None = None,
    namespaces: Mapping[str, str] | None = None,
    report_mode_artifacts: Mapping[str, Any] | None = None,
) -> Dict[str, Path]:
    namespace = str((namespaces or DEFAULT_REPORT_NAMESPACES).get(REPAIR_GENERATION_MODE, REPAIR_NAMESPACE))
    namespace_root = None
    if repair_dir is None:
        if reports_root is None:
            reports_root = Path(__file__).resolve().parents[1] / "reports"
        namespace_root = resolve_report_namespace_root(
            reports_root,
            REPAIR_GENERATION_MODE,
            namespaces=namespaces,
        )
        repair_dir = namespace_root / str(bundle_name)
    bundle_paths = write_repair_bundle(
        plan,
        acceptance,
        repair_dir,
        namespace_root=namespace_root,
        bundle_name=str(bundle_name),
        namespace=namespace,
    )
    if reports_root is not None:
        bundle_paths["namespace_contract_path"] = write_report_namespace_contract(
            reports_root,
            namespaces=namespaces,
            report_mode_artifacts=report_mode_artifacts,
        )
    return bundle_paths


__all__ = [
    "REPAIR_NAMESPACE",
    "run_repair_bundle_write",
    "write_repair_bundle",
]
