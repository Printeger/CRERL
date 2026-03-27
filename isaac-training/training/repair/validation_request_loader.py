"""Phase 9 validation-request loader for Phase 8 repair bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping


REQUIRED_REPAIR_BUNDLE_ARTIFACTS = (
    "repair_plan.json",
    "spec_patch.json",
    "spec_patch_preview.json",
    "validation_context_preview.json",
    "repair_validation.json",
    "validation_request.json",
    "manifest.json",
)


def _json_load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _stable_unique(values: Iterable[Any]) -> List[str]:
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


def load_validation_request_bundle(
    repair_bundle_dir: str | Path,
    *,
    require_phase9_ready: bool = False,
) -> Dict[str, Any]:
    """Load a Phase 8 repair bundle into a normalized Phase 9 validation input."""

    bundle_dir = Path(repair_bundle_dir)
    resolved_paths = {name: bundle_dir / name for name in REQUIRED_REPAIR_BUNDLE_ARTIFACTS}
    missing_artifacts = [name for name, path in resolved_paths.items() if not path.exists()]

    manifest = _json_load(resolved_paths["manifest.json"]) if "manifest.json" not in missing_artifacts else {}
    repair_plan = _json_load(resolved_paths["repair_plan.json"]) if "repair_plan.json" not in missing_artifacts else {}
    spec_patch = _json_load(resolved_paths["spec_patch.json"]) if "spec_patch.json" not in missing_artifacts else {}
    spec_patch_preview = (
        _json_load(resolved_paths["spec_patch_preview.json"])
        if "spec_patch_preview.json" not in missing_artifacts
        else {}
    )
    validation_context_preview = (
        _json_load(resolved_paths["validation_context_preview.json"])
        if "validation_context_preview.json" not in missing_artifacts
        else {}
    )
    repair_validation = (
        _json_load(resolved_paths["repair_validation.json"])
        if "repair_validation.json" not in missing_artifacts
        else {}
    )
    validation_request = (
        _json_load(resolved_paths["validation_request.json"])
        if "validation_request.json" not in missing_artifacts
        else {}
    )

    preferred_execution_modes = _stable_unique(validation_request.get("preferred_execution_modes", []) or [])
    scene_family_scope = _stable_unique(validation_request.get("scene_family_scope", []) or [])
    validation_targets = _stable_unique(validation_request.get("validation_targets", []) or [])

    bundle_name = str(validation_request.get("repair_bundle_name") or bundle_dir.name)
    phase9_ready = bool(validation_request.get("phase9_ready", False)) and bool(
        repair_validation.get("phase9_ready", False)
    )
    blockers: List[str] = []
    if missing_artifacts:
        blockers.append("missing_required_artifacts")
    if not bool(validation_request.get("request_type")):
        blockers.append("missing_validation_request_type")
    if not bool(repair_validation.get("validation_type")):
        blockers.append("missing_repair_validation_type")
    if require_phase9_ready and not phase9_ready:
        blockers.append("phase9_not_ready")

    return {
        "loader_type": "phase9_validation_request_loader.v1",
        "repair_bundle_dir": str(bundle_dir),
        "repair_bundle_name": bundle_name,
        "repair_namespace": str(validation_request.get("repair_namespace", "analysis/repair")),
        "phase9_entrypoint": str(validation_request.get("phase9_entrypoint", "")),
        "phase9_ready": phase9_ready,
        "request_valid": not blockers,
        "blockers": blockers,
        "missing_artifacts": missing_artifacts,
        "preferred_execution_modes": preferred_execution_modes,
        "scene_family_scope": scene_family_scope,
        "validation_targets": validation_targets,
        "primary_claim_type": str(validation_request.get("primary_claim_type", "")),
        "primary_repair_direction": str(validation_request.get("primary_repair_direction", "")),
        "selected_candidate_id": str(validation_request.get("selected_candidate_id", "")),
        "selected_target_component": str(validation_request.get("selected_target_component", "")),
        "selected_target_files": _stable_unique(validation_request.get("selected_target_files", []) or []),
        "selected_target_paths": _stable_unique(validation_request.get("selected_target_paths", []) or []),
        "expected_metric_direction": _stable_unique(validation_request.get("expected_metric_direction", []) or []),
        "manifest": manifest,
        "repair_plan": repair_plan,
        "spec_patch": spec_patch,
        "spec_patch_preview": spec_patch_preview,
        "validation_context_preview": validation_context_preview,
        "repair_validation": repair_validation,
        "validation_request": validation_request,
        "resolved_paths": {name: str(path) for name, path in resolved_paths.items()},
    }


__all__ = [
    "REQUIRED_REPAIR_BUNDLE_ARTIFACTS",
    "load_validation_request_bundle",
]
