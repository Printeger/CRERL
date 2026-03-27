"""Structured Phase 8 repair bundle writer and Phase 9 preview helpers."""

from __future__ import annotations

import json
from copy import deepcopy
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

try:
    import yaml
except Exception:  # pragma: no cover - environment fallback
    class _YamlCompat:
        @staticmethod
        def _strip_comment(line: str) -> str:
            in_quote = False
            quote_char = ""
            result = []
            for ch in line:
                if ch in {'"', "'"}:
                    if not in_quote:
                        in_quote = True
                        quote_char = ch
                    elif quote_char == ch:
                        in_quote = False
                if ch == "#" and not in_quote:
                    break
                result.append(ch)
            return "".join(result).rstrip()

        @staticmethod
        def _parse_scalar(value: str):
            if value.startswith(("'", '"')) and value.endswith(("'", '"')):
                return value[1:-1]
            lower = value.lower()
            if lower == "true":
                return True
            if lower == "false":
                return False
            if lower in {"null", "none"}:
                return None
            try:
                if "." in value:
                    return float(value)
                return int(value)
            except ValueError:
                return value

        @classmethod
        def _parse_block(cls, lines, start_idx, indent):
            if start_idx >= len(lines):
                return {}, start_idx

            if lines[start_idx][1].startswith("- "):
                items = []
                idx = start_idx
                while idx < len(lines):
                    current_indent, current = lines[idx]
                    if current_indent < indent or current_indent != indent or not current.startswith("- "):
                        break
                    value = current[2:].strip()
                    idx += 1
                    if value == "":
                        child, idx = cls._parse_block(lines, idx, indent + 2)
                        items.append(child)
                    else:
                        items.append(cls._parse_scalar(value))
                return items, idx

            mapping = {}
            idx = start_idx
            while idx < len(lines):
                current_indent, current = lines[idx]
                if current_indent < indent or current_indent != indent:
                    break
                key, sep, raw_value = current.partition(":")
                if not sep:
                    raise ValueError(f"Invalid YAML line: {current}")
                key = key.strip()
                value = raw_value.strip()
                idx += 1
                if value == "":
                    if idx < len(lines) and lines[idx][0] > current_indent:
                        child, idx = cls._parse_block(lines, idx, current_indent + 2)
                        mapping[key] = child
                    else:
                        mapping[key] = {}
                else:
                    mapping[key] = cls._parse_scalar(value)
            return mapping, idx

        @classmethod
        def safe_load(cls, text):
            lines = []
            for raw_line in text.splitlines():
                stripped = cls._strip_comment(raw_line)
                if not stripped.strip():
                    continue
                indent = len(stripped) - len(stripped.lstrip(" "))
                lines.append((indent, stripped.lstrip(" ")))
            if not lines:
                return {}
            parsed, _ = cls._parse_block(lines, 0, lines[0][0])
            return parsed

    yaml = _YamlCompat()


REPAIR_NAMESPACE = DEFAULT_REPORT_NAMESPACES[REPAIR_GENERATION_MODE]
REPO_ROOT = Path(__file__).resolve().parents[3]


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


def _build_patch_preview_payload(plan: RepairPlan) -> Dict[str, Any]:
    selected_patch = plan.selected_patch.to_dict() if plan.selected_patch is not None else {}
    operations = list(selected_patch.get("operations", []) or [])
    files_touched = sorted({str(item.get("target_file", "")) for item in operations if item.get("target_file")})
    return {
        "preview_type": "phase8_spec_patch_preview.v1",
        "preview_mode": "non_destructive",
        "source_mutation_performed": False,
        "selected_candidate_id": plan.selected_candidate_id,
        "primary_claim_type": plan.primary_claim_type,
        "patch_id": str(selected_patch.get("patch_id", "")),
        "patch_type": str(selected_patch.get("patch_type", "")),
        "target_component": str(selected_patch.get("target_component", "")),
        "target_file": str(selected_patch.get("target_file", "")),
        "files_touched": files_touched,
        "operation_count": len(operations),
        "operations": [
            {
                **dict(item),
                "would_change": item.get("before") != item.get("after"),
            }
            for item in operations
        ],
    }


def _resolve_target_file(target_file: str, *, repo_root: Path | None = None) -> Path:
    path = Path(target_file)
    if path.is_absolute():
        return path
    root = repo_root or REPO_ROOT
    return (root / path).resolve()


def _load_document(path: Path) -> tuple[Any, str]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8")), "json"
    if suffix in {".yaml", ".yml"} and yaml is not None:
        return yaml.safe_load(path.read_text(encoding="utf-8")), "yaml"
    return path.read_text(encoding="utf-8"), "text"


def _set_path_value(payload: Any, dotted_path: str, value: Any) -> Any:
    if not dotted_path:
        return payload
    parts = dotted_path.split(".")
    current = payload
    for index, part in enumerate(parts[:-1]):
        next_part = parts[index + 1]
        if isinstance(current, list):
            target_index = int(part)
            while len(current) <= target_index:
                current.append({} if not next_part.isdigit() else [])
            if current[target_index] is None:
                current[target_index] = {} if not next_part.isdigit() else []
            current = current[target_index]
            continue
        if not isinstance(current, dict):
            raise TypeError(f"Cannot set dotted path '{dotted_path}' on non-container value.")
        if part not in current or current[part] is None:
            current[part] = [] if next_part.isdigit() else {}
        current = current[part]

    leaf = parts[-1]
    if isinstance(current, list):
        target_index = int(leaf)
        while len(current) <= target_index:
            current.append(None)
        current[target_index] = value
    elif isinstance(current, dict):
        current[leaf] = value
    else:
        raise TypeError(f"Cannot set dotted path '{dotted_path}' on non-container value.")
    return payload


def build_validation_context_preview(
    plan: RepairPlan | Mapping[str, Any],
    *,
    validation_request: Mapping[str, Any] | None = None,
    repo_root: str | Path | None = None,
) -> Dict[str, Any]:
    plan_payload = plan.to_dict() if isinstance(plan, RepairPlan) else dict(plan)
    selected_patch = dict(plan_payload.get("selected_patch") or {})
    operations = list(selected_patch.get("operations", []) or [])
    grouped: Dict[str, list[Dict[str, Any]]] = {}
    for operation in operations:
        target_file = str(operation.get("target_file", ""))
        grouped.setdefault(target_file, []).append(dict(operation))

    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    file_previews = []
    for target_file, file_operations in grouped.items():
        resolved_path = _resolve_target_file(target_file, repo_root=root)
        original_document, document_type = _load_document(resolved_path)
        patched_document = deepcopy(original_document)
        preview_operations = []
        for item in file_operations:
            _set_path_value(patched_document, str(item.get("target_path", "")), item.get("after"))
            preview_operations.append(
                {
                    **dict(item),
                    "would_change": item.get("before") != item.get("after"),
                }
            )
        file_previews.append(
            {
                "target_file": target_file,
                "resolved_target_file": str(resolved_path),
                "document_type": document_type,
                "operation_count": len(preview_operations),
                "operations": preview_operations,
                "original_document": original_document,
                "patched_document": patched_document,
            }
        )

    request_payload = dict(validation_request or {})
    return {
        "preview_type": "phase9_validation_context_preview.v1",
        "preview_mode": "non_destructive_validation_context",
        "source_mutation_performed": False,
        "repair_bundle_name": str(request_payload.get("repair_bundle_name", "")),
        "phase9_entrypoint": str(request_payload.get("phase9_entrypoint", "")),
        "preferred_execution_modes": list(request_payload.get("preferred_execution_modes", []) or []),
        "scene_family_scope": list(request_payload.get("scene_family_scope", []) or []),
        "validation_targets": list(request_payload.get("validation_targets", []) or []),
        "target_file_count": len(file_previews),
        "file_previews": file_previews,
    }


def write_repair_bundle(
    plan: RepairPlan,
    acceptance: Mapping[str, Any],
    repair_dir: str | Path,
    *,
    repair_validation: Mapping[str, Any] | None = None,
    validation_request: Mapping[str, Any] | None = None,
    namespace_root: str | Path | None = None,
    bundle_name: str = "repair_latest",
    namespace: str = REPAIR_NAMESPACE,
) -> Dict[str, Path]:
    repair_path = Path(repair_dir)
    repair_path.mkdir(parents=True, exist_ok=True)

    repair_plan_path = repair_path / "repair_plan.json"
    repair_candidates_path = repair_path / "repair_candidates.json"
    spec_patch_path = repair_path / "spec_patch.json"
    spec_patch_preview_path = repair_path / "spec_patch_preview.json"
    validation_context_preview_path = repair_path / "validation_context_preview.json"
    repair_summary_path = repair_path / "repair_summary.json"
    repair_summary_md_path = repair_path / "repair_summary.md"
    acceptance_path = repair_path / "acceptance.json"
    repair_validation_path = repair_path / "repair_validation.json"
    validation_request_path = repair_path / "validation_request.json"
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
    spec_patch_preview_path.write_text(
        json.dumps(_build_patch_preview_payload(plan), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    validation_context_preview_path.write_text(
        json.dumps(
            build_validation_context_preview(plan, validation_request=validation_request),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    repair_summary_payload = _build_repair_summary_payload(plan, acceptance)
    repair_summary_path.write_text(json.dumps(repair_summary_payload, indent=2, sort_keys=True), encoding="utf-8")
    repair_summary_md_path.write_text(_build_human_summary_markdown(plan, acceptance), encoding="utf-8")
    acceptance_path.write_text(json.dumps(dict(acceptance), indent=2, sort_keys=True), encoding="utf-8")
    repair_validation_path.write_text(
        json.dumps(dict(repair_validation or {}), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    validation_request_path.write_text(
        json.dumps(dict(validation_request or {}), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    manifest_payload = {
        "bundle_type": "repair_generation_bundle.v1",
        "namespace": namespace,
        "plan_type": plan.plan_type,
        "source_report_bundle": plan.source_report_bundle,
        "repair_plan_path": repair_plan_path.name,
        "repair_candidates_path": repair_candidates_path.name,
        "spec_patch_path": spec_patch_path.name,
        "spec_patch_preview_path": spec_patch_preview_path.name,
        "validation_context_preview_path": validation_context_preview_path.name,
        "repair_summary_path": repair_summary_path.name,
        "repair_summary_md_path": repair_summary_md_path.name,
        "acceptance_path": acceptance_path.name,
        "repair_validation_path": repair_validation_path.name,
        "validation_request_path": validation_request_path.name,
        "selected_candidate_id": plan.selected_candidate_id,
        "primary_claim_type": plan.primary_claim_type,
        "passed": bool(acceptance.get("passed", False)),
        "max_severity": str(acceptance.get("max_severity", "info")),
        "phase9_ready": bool((repair_validation or {}).get("phase9_ready", False)),
        "metadata": dict(plan.metadata),
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True), encoding="utf-8")

    bundle_paths: Dict[str, Path] = {
        "report_dir": repair_path,
        "repair_dir": repair_path,
        "repair_plan_path": repair_plan_path,
        "repair_candidates_path": repair_candidates_path,
        "spec_patch_path": spec_patch_path,
        "spec_patch_preview_path": spec_patch_preview_path,
        "validation_context_preview_path": validation_context_preview_path,
        "repair_summary_path": repair_summary_path,
        "repair_summary_md_path": repair_summary_md_path,
        "acceptance_path": acceptance_path,
        "repair_validation_path": repair_validation_path,
        "validation_request_path": validation_request_path,
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
                "phase9_ready": bool((repair_validation or {}).get("phase9_ready", False)),
            },
        )
    return bundle_paths


def run_repair_bundle_write(
    plan: RepairPlan,
    acceptance: Mapping[str, Any],
    *,
    repair_validation: Mapping[str, Any] | None = None,
    validation_request: Mapping[str, Any] | None = None,
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
        repair_validation=repair_validation,
        validation_request=validation_request,
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
    "build_validation_context_preview",
    "run_repair_bundle_write",
    "write_repair_bundle",
]
