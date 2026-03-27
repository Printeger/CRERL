"""Phase 9 validation runner and namespaced validation bundle writer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from analyzers.report_contract import (
    DEFAULT_REPORT_NAMESPACES,
    VALIDATION_GENERATION_MODE,
    resolve_report_namespace_root,
    write_namespace_manifest,
    write_report_namespace_contract,
)
from runtime_logging.episode_writer import (
    discover_accepted_run_directories,
    load_run_directories,
)

from repair.validation_request_loader import load_validation_request_bundle


VALIDATION_NAMESPACE = DEFAULT_REPORT_NAMESPACES[VALIDATION_GENERATION_MODE]


def _build_validation_plan(
    validation_input: Mapping[str, Any],
    *,
    logs_root: str | Path | None = None,
    original_run_dirs: Sequence[str | Path] = (),
    repaired_run_dirs: Sequence[str | Path] = (),
) -> Dict[str, Any]:
    return {
        "plan_type": "phase9_validation_plan.v1",
        "repair_bundle_name": str(validation_input.get("repair_bundle_name", "")),
        "repair_bundle_dir": str(validation_input.get("repair_bundle_dir", "")),
        "phase9_entrypoint": str(validation_input.get("phase9_entrypoint", "")),
        "primary_claim_type": str(validation_input.get("primary_claim_type", "")),
        "preferred_execution_modes": list(validation_input.get("preferred_execution_modes", []) or []),
        "scene_family_scope": list(validation_input.get("scene_family_scope", []) or []),
        "validation_targets": list(validation_input.get("validation_targets", []) or []),
        "comparison_mode": str(validation_input.get("validation_request", {}).get("comparison_mode", "")),
        "logs_root": str(logs_root) if logs_root is not None else "",
        "original_run_dirs": [str(item) for item in original_run_dirs],
        "repaired_run_dirs": [str(item) for item in repaired_run_dirs],
    }


def prepare_validation_runs(
    *,
    repair_bundle_dir: str | Path,
    logs_root: str | Path | None = None,
    original_run_dirs: Sequence[str | Path] = (),
    repaired_run_dirs: Sequence[str | Path] = (),
) -> Dict[str, Any]:
    """Prepare Phase 9 validation inputs and accepted-run references."""

    validation_input = load_validation_request_bundle(repair_bundle_dir, require_phase9_ready=False)
    resolved_original_dirs = [Path(item) for item in original_run_dirs]
    resolved_repaired_dirs = [Path(item) for item in repaired_run_dirs]

    discovery_used = False
    if not resolved_original_dirs and logs_root is not None:
        discovery_used = True
        resolved_original_dirs = discover_accepted_run_directories(
            logs_root,
            sources=validation_input.get("preferred_execution_modes", []),
            scenario_types=validation_input.get("scene_family_scope", []),
            require_passed=True,
        )

    original_runs = load_run_directories(resolved_original_dirs, require_passed=True) if resolved_original_dirs else []
    repaired_runs = load_run_directories(resolved_repaired_dirs, require_passed=True) if resolved_repaired_dirs else []

    validation_plan = _build_validation_plan(
        validation_input,
        logs_root=logs_root,
        original_run_dirs=resolved_original_dirs,
        repaired_run_dirs=resolved_repaired_dirs,
    )
    validation_runs = {
        "runs_type": "phase9_validation_runs.v1",
        "discovery_used": discovery_used,
        "original_runs": [
            {
                "run_dir": str(item.get("run_dir", "")),
                "run_id": str(item.get("run_id", "")),
                "source": str((item.get("manifest") or {}).get("source", "")),
                "summary": dict(item.get("summary") or {}),
                "acceptance": dict(item.get("acceptance") or {}),
            }
            for item in original_runs
        ],
        "repaired_runs": [
            {
                "run_dir": str(item.get("run_dir", "")),
                "run_id": str(item.get("run_id", "")),
                "source": str((item.get("manifest") or {}).get("source", "")),
                "summary": dict(item.get("summary") or {}),
                "acceptance": dict(item.get("acceptance") or {}),
            }
            for item in repaired_runs
        ],
    }
    return {
        "validation_input": validation_input,
        "validation_plan": validation_plan,
        "validation_runs": validation_runs,
        "original_runs": original_runs,
        "repaired_runs": repaired_runs,
    }


def _build_validation_summary_payload(
    *,
    validation_plan: Mapping[str, Any],
    comparison: Mapping[str, Any],
    decision: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "bundle_type": "validation_bundle.v1",
        "validation_plan_type": str(validation_plan.get("plan_type", "")),
        "primary_claim_type": str(validation_plan.get("primary_claim_type", "")),
        "decision_status": str(decision.get("decision_status", "")),
        "accepted": bool(decision.get("accepted", False)),
        "original_run_count": int(comparison.get("original_run_count", 0) or 0),
        "repaired_run_count": int(comparison.get("repaired_run_count", 0) or 0),
        "blocked_by": list(decision.get("blocked_by", []) or []),
    }


def _build_validation_summary_markdown(
    *,
    validation_plan: Mapping[str, Any],
    comparison: Mapping[str, Any],
    decision: Mapping[str, Any],
) -> str:
    lines = [
        "# Validation Summary",
        "",
        f"- Repair bundle: `{validation_plan.get('repair_bundle_name', '')}`",
        f"- Primary claim type: `{validation_plan.get('primary_claim_type', '')}`",
        f"- Decision: `{decision.get('decision_status', '')}`",
        f"- Accepted: `{bool(decision.get('accepted', False))}`",
        f"- Original runs: `{comparison.get('original_run_count', 0)}`",
        f"- Repaired runs: `{comparison.get('repaired_run_count', 0)}`",
        "",
        "## Metric Deltas",
        "",
    ]
    metric_deltas = dict(comparison.get("metric_deltas") or {})
    if metric_deltas:
        for metric_name, payload in metric_deltas.items():
            lines.append(
                f"- `{metric_name}`:"
                f" original=`{payload.get('original', '')}`"
                f" repaired=`{payload.get('repaired', '')}`"
                f" improvement=`{payload.get('improvement', '')}`"
            )
    else:
        lines.append("- No metric deltas available.")
    lines.extend(
        [
            "",
            "## Decision Rationale",
            "",
            str(decision.get("decision_rationale", "")) or "No rationale recorded.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def write_validation_bundle(
    *,
    validation_plan: Mapping[str, Any],
    validation_runs: Mapping[str, Any],
    comparison: Mapping[str, Any],
    decision: Mapping[str, Any],
    validation_dir: str | Path,
    namespace_root: str | Path | None = None,
    bundle_name: str = "validation_latest",
    namespace: str = VALIDATION_NAMESPACE,
) -> Dict[str, Path]:
    validation_path = Path(validation_dir)
    validation_path.mkdir(parents=True, exist_ok=True)

    validation_plan_path = validation_path / "validation_plan.json"
    validation_runs_path = validation_path / "validation_runs.json"
    comparison_path = validation_path / "comparison.json"
    validation_decision_path = validation_path / "validation_decision.json"
    validation_summary_path = validation_path / "validation_summary.json"
    validation_summary_md_path = validation_path / "validation_summary.md"
    manifest_path = validation_path / "manifest.json"

    validation_plan_path.write_text(json.dumps(dict(validation_plan), indent=2, sort_keys=True), encoding="utf-8")
    validation_runs_path.write_text(json.dumps(dict(validation_runs), indent=2, sort_keys=True), encoding="utf-8")
    comparison_path.write_text(json.dumps(dict(comparison), indent=2, sort_keys=True), encoding="utf-8")
    validation_decision_path.write_text(json.dumps(dict(decision), indent=2, sort_keys=True), encoding="utf-8")
    summary_payload = _build_validation_summary_payload(
        validation_plan=validation_plan,
        comparison=comparison,
        decision=decision,
    )
    validation_summary_path.write_text(json.dumps(summary_payload, indent=2, sort_keys=True), encoding="utf-8")
    validation_summary_md_path.write_text(
        _build_validation_summary_markdown(
            validation_plan=validation_plan,
            comparison=comparison,
            decision=decision,
        ),
        encoding="utf-8",
    )
    manifest_payload = {
        "bundle_type": "validation_bundle.v1",
        "namespace": namespace,
        "repair_bundle_name": str(validation_plan.get("repair_bundle_name", "")),
        "validation_plan_path": validation_plan_path.name,
        "validation_runs_path": validation_runs_path.name,
        "comparison_path": comparison_path.name,
        "validation_decision_path": validation_decision_path.name,
        "validation_summary_path": validation_summary_path.name,
        "validation_summary_md_path": validation_summary_md_path.name,
        "accepted": bool(decision.get("accepted", False)),
        "decision_status": str(decision.get("decision_status", "")),
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True), encoding="utf-8")

    bundle_paths: Dict[str, Path] = {
        "report_dir": validation_path,
        "validation_dir": validation_path,
        "validation_plan_path": validation_plan_path,
        "validation_runs_path": validation_runs_path,
        "comparison_path": comparison_path,
        "validation_decision_path": validation_decision_path,
        "validation_summary_path": validation_summary_path,
        "validation_summary_md_path": validation_summary_md_path,
        "manifest_path": manifest_path,
        "summary_path": validation_summary_path,
    }
    if namespace_root is not None:
        bundle_paths["namespace_manifest_path"] = write_namespace_manifest(
            namespace_root,
            bundle_name=bundle_name,
            report_mode=VALIDATION_GENERATION_MODE,
            namespace=namespace,
            bundle_paths=bundle_paths,
            report_summary={
                "accepted": bool(decision.get("accepted", False)),
                "decision_status": str(decision.get("decision_status", "")),
                "primary_claim_type": str(validation_plan.get("primary_claim_type", "")),
            },
        )
    return bundle_paths


def run_validation_bundle_write(
    *,
    validation_plan: Mapping[str, Any],
    validation_runs: Mapping[str, Any],
    comparison: Mapping[str, Any],
    decision: Mapping[str, Any],
    reports_root: str | Path | None = None,
    bundle_name: str = "validation_latest",
    validation_dir: str | Path | None = None,
    namespaces: Mapping[str, str] | None = None,
    report_mode_artifacts: Mapping[str, Any] | None = None,
) -> Dict[str, Path]:
    namespace = str((namespaces or DEFAULT_REPORT_NAMESPACES).get(VALIDATION_GENERATION_MODE, VALIDATION_NAMESPACE))
    namespace_root = None
    if validation_dir is None:
        if reports_root is None:
            reports_root = Path(__file__).resolve().parents[1] / "reports"
        namespace_root = resolve_report_namespace_root(reports_root, VALIDATION_GENERATION_MODE, namespaces=namespaces)
        validation_dir = namespace_root / str(bundle_name)
    bundle_paths = write_validation_bundle(
        validation_plan=validation_plan,
        validation_runs=validation_runs,
        comparison=comparison,
        decision=decision,
        validation_dir=validation_dir,
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
    "VALIDATION_NAMESPACE",
    "prepare_validation_runs",
    "run_validation_bundle_write",
    "write_validation_bundle",
]
