"""Phase 10 integration audit bundle builder."""

from __future__ import annotations

import ast
import copy
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from analyzers.report_contract import (
    DEFAULT_REPORT_NAMESPACES,
    INTEGRATION_AUDIT_MODE,
    resolve_report_namespace_root,
    write_namespace_manifest,
    write_report_namespace_contract,
)
from analyzers.spec_ir import load_policy_spec
from envs.runtime.scene_family_bridge import build_scene_family_runtime_profile

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal envs
    class _YamlCompat:
        @staticmethod
        def _strip_comment(line: str) -> str:
            return line.split("#", 1)[0].rstrip()

        @staticmethod
        def _parse_scalar(value: str):
            lowered = value.lower()
            if lowered in {"true", "false"}:
                return lowered == "true"
            if lowered in {"null", "none", "~"}:
                return None
            if value.startswith(("'", '"')) and value.endswith(("'", '"')):
                return value[1:-1]
            if value.startswith(("[", "{", "(", "-")) or value[:1].isdigit():
                try:
                    normalized = (
                        value.replace("true", "True")
                        .replace("false", "False")
                        .replace("null", "None")
                    )
                    return ast.literal_eval(normalized)
                except Exception:
                    pass
            try:
                if "." in value or "e" in lowered:
                    return float(value)
                return int(value)
            except Exception:
                return value

        @classmethod
        def _parse_block(cls, lines, start_idx: int, indent: int):
            if start_idx >= len(lines):
                return {}, start_idx

            _, content = lines[start_idx]
            if content.startswith("- "):
                items = []
                idx = start_idx
                while idx < len(lines):
                    current_indent, current = lines[idx]
                    if current_indent < indent or not current.startswith("- ") or current_indent != indent:
                        break
                    payload = current[2:].strip()
                    idx += 1
                    if payload == "":
                        child, idx = cls._parse_block(lines, idx, indent + 2)
                        items.append(child)
                    else:
                        items.append(cls._parse_scalar(payload))
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


TRAINING_ROOT = Path(__file__).resolve().parents[1]
CFG_ROOT = TRAINING_ROOT / "cfg"
DEFAULT_MODE_CONFIGS = {
    "baseline": CFG_ROOT / "baseline.yaml",
    "eval": CFG_ROOT / "eval.yaml",
    "train": CFG_ROOT / "train.yaml",
}
INTEGRATION_NAMESPACE = DEFAULT_REPORT_NAMESPACES[INTEGRATION_AUDIT_MODE]


def _load_yaml_file(path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML file at {path} must load to a dict.")
    return data


def _ensure_mode_config(
    cfg: Mapping[str, Any],
    *,
    scene_family: str,
    repair_preview_path: str,
    mode: str,
) -> Dict[str, Any]:
    payload = copy.deepcopy(dict(cfg))
    scene_family_backend = dict(payload.get("scene_family_backend", {}))
    scene_family_backend["enabled"] = True
    scene_family_backend["family"] = str(scene_family)
    payload["scene_family_backend"] = scene_family_backend

    repair = dict(payload.get("repair", {}))
    repair.setdefault("validation_context_preview", "")
    if repair_preview_path:
        repair["validation_context_preview"] = str(repair_preview_path)
    payload["repair"] = repair

    scene_logging = dict(payload.get("scene_logging", {}))
    scene_logging.setdefault("scenario_type", str(scene_family))
    scene_logging.setdefault("scene_cfg_name", f"scene_cfg_{scene_family}.yaml")
    scene_logging.setdefault("scene_id_prefix", f"{mode}_{scene_family}_scene")
    payload["scene_logging"] = scene_logging
    return payload


def _build_execution_mode_entry(
    *,
    mode: str,
    config_path: Path,
    config_payload: Mapping[str, Any],
    scene_family: str,
    repair_preview_path: str,
    policy_runtime_expectations: Mapping[str, Any],
) -> Dict[str, Any]:
    profile = build_scene_family_runtime_profile(
        config_payload.get("scene_family_backend"),
        seed=int(config_payload.get("seed", 0)),
        repair_context=config_payload.get("repair"),
    )
    repair_preview_binding = dict(profile.get("repair_preview_binding", {}))
    effective_scene_binding = dict(profile.get("effective_scene_binding", {}))
    effective_spec_binding = dict(profile.get("effective_spec_binding", {}))
    repair_declared = "repair" in config_payload and "validation_context_preview" in dict(config_payload.get("repair", {}))
    preview_requested = bool(repair_preview_path)
    supported_modes = {
        str(item) for item in list(policy_runtime_expectations.get("supported_execution_modes", []) or [])
    }
    rollout_required_artifacts = [
        str(item) for item in list(policy_runtime_expectations.get("rollout_required_artifacts", []) or [])
    ]
    accepted_run_contract_ready = bool(rollout_required_artifacts)
    direct_runtime_metadata_binding = bool(effective_scene_binding) and bool(effective_spec_binding)
    comparison_ready_direct = (
        bool(profile.get("enabled"))
        and direct_runtime_metadata_binding
        and accepted_run_contract_ready
        and (bool(repair_preview_binding.get("preview_bound", False)) if preview_requested else True)
    )
    requires_validation_only_glue = not comparison_ready_direct

    return {
        "execution_mode": mode,
        "config_path": str(config_path),
        "scene_family_backend_direct": bool(profile.get("enabled", False)),
        "repair_preview_config_declared": bool(repair_declared),
        "repair_preview_requested": bool(preview_requested),
        "repair_preview_bound": bool(repair_preview_binding.get("preview_bound", False)),
        "direct_runtime_metadata_binding": bool(direct_runtime_metadata_binding),
        "accepted_cre_logs_direct": bool(accepted_run_contract_ready),
        "comparison_ready_direct": bool(comparison_ready_direct),
        "supported_execution_mode": mode in supported_modes,
        "requires_validation_only_glue": bool(requires_validation_only_glue),
        "effective_family": str(profile.get("family", scene_family)),
        "scene_cfg_name": str(profile.get("scene_cfg_name", "")),
        "scene_id_prefix": str(profile.get("scene_id_prefix", "")),
        "repair_preview_binding": repair_preview_binding,
        "effective_scene_binding": effective_scene_binding,
        "effective_spec_binding": effective_spec_binding,
    }


def _build_integration_acceptance(
    execution_matrix: Sequence[Mapping[str, Any]],
    *,
    repair_preview_path: str,
    policy_runtime_expectations: Mapping[str, Any],
) -> Dict[str, Any]:
    checks = []

    def _append(check_id: str, passed: bool, severity: str, summary: str, details=None):
        checks.append(
            {
                "check_id": check_id,
                "passed": bool(passed),
                "severity": severity,
                "summary": summary,
                "details": dict(details or {}),
            }
        )

    _append(
        "supported_execution_modes",
        all(bool(item.get("supported_execution_mode", False)) for item in execution_matrix),
        "high",
        "All targeted execution modes are declared in the CRE runtime contract.",
    )
    _append(
        "direct_scene_family_binding",
        all(bool(item.get("scene_family_backend_direct", False)) for item in execution_matrix)
        if bool(policy_runtime_expectations.get("integration_direct_scene_binding_required", True))
        else True,
        "high",
        "All targeted execution modes compile the family-based scene backend directly.",
    )
    _append(
        "direct_runtime_metadata_binding",
        all(bool(item.get("direct_runtime_metadata_binding", False)) for item in execution_matrix)
        if bool(policy_runtime_expectations.get("integration_direct_runtime_metadata_binding_required", True))
        else True,
        "high",
        "All targeted execution modes expose effective scene/spec runtime bindings directly.",
    )
    _append(
        "accepted_cre_logs_direct",
        all(bool(item.get("accepted_cre_logs_direct", False)) for item in execution_matrix),
        "medium",
        "All targeted execution modes already satisfy accepted CRE log artifact expectations.",
    )
    if repair_preview_path:
        _append(
            "direct_repaired_preview_binding",
            all(bool(item.get("repair_preview_bound", False)) for item in execution_matrix)
            if bool(policy_runtime_expectations.get("integration_direct_repair_preview_binding_required", True))
            else True,
            "high",
            "All targeted execution modes bind the repaired preview context without validation-only wrappers.",
            details={"repair_preview_path": repair_preview_path},
        )
    else:
        _append(
            "direct_repaired_preview_binding",
            all(bool(item.get("repair_preview_config_declared", False)) for item in execution_matrix),
            "medium",
            "Execution mode configs expose a native repaired-preview injection path.",
        )
    _append(
        "comparison_readiness",
        all(bool(item.get("comparison_ready_direct", False)) for item in execution_matrix),
        "high",
        "All targeted execution modes can participate in original-vs-repaired comparisons directly.",
    )

    failing_high = [item for item in checks if not item["passed"] and item["severity"] == "high"]
    failing_any = [item for item in checks if not item["passed"]]
    max_severity = "info"
    if failing_any:
        severity_order = {"info": 0, "medium": 1, "high": 2, "critical": 3}
        max_severity = max(failing_any, key=lambda item: severity_order.get(str(item["severity"]), 0))["severity"]

    return {
        "acceptance_type": "phase10_integration_acceptance.v1",
        "passed": not failing_high,
        "max_severity": max_severity,
        "num_checks": len(checks),
        "failed_check_count": len(failing_any),
        "checks": checks,
        "validation_only_glue_modes": [
            str(item.get("execution_mode", ""))
            for item in execution_matrix
            if bool(item.get("requires_validation_only_glue", False))
        ],
    }


def _build_summary_markdown(
    *,
    scene_family: str,
    repair_preview_path: str,
    execution_matrix: Sequence[Mapping[str, Any]],
    acceptance: Mapping[str, Any],
) -> str:
    lines = [
        "# Phase 10 Integration Summary",
        "",
        f"- Scene family: `{scene_family}`",
        f"- Repair preview path: `{repair_preview_path}`" if repair_preview_path else "- Repair preview path: `(none)`",
        f"- Passed: `{bool(acceptance.get('passed', False))}`",
        f"- Max severity: `{acceptance.get('max_severity', 'info')}`",
        "",
        "## Execution Matrix",
        "",
    ]
    for row in execution_matrix:
        lines.extend(
            [
                f"### `{row.get('execution_mode', '')}`",
                "",
                f"- Scene-family backend direct: `{row.get('scene_family_backend_direct', False)}`",
                f"- Runtime metadata direct: `{row.get('direct_runtime_metadata_binding', False)}`",
                f"- Repair preview bound: `{row.get('repair_preview_bound', False)}`",
                f"- Accepted CRE logs direct: `{row.get('accepted_cre_logs_direct', False)}`",
                f"- Comparison ready direct: `{row.get('comparison_ready_direct', False)}`",
                f"- Validation-only glue required: `{row.get('requires_validation_only_glue', False)}`",
                "",
            ]
        )
    lines.extend(["## Remaining Gaps", ""])
    glue_modes = list(acceptance.get("validation_only_glue_modes", []) or [])
    if glue_modes:
        for mode in glue_modes:
            lines.append(f"- `{mode}` still requires validation-only adapter glue.")
    else:
        lines.append("- No validation-only adapter glue is required for the current integration scope.")
    return "\n".join(lines).strip() + "\n"


@dataclass
class IntegrationAudit:
    integration_type: str
    scene_family: str
    repair_preview_path: str
    execution_modes: list[str] = field(default_factory=list)
    integration_plan: Dict[str, Any] = field(default_factory=dict)
    execution_matrix: Dict[str, Any] = field(default_factory=dict)
    run_binding: Dict[str, Any] = field(default_factory=dict)
    integration_acceptance: Dict[str, Any] = field(default_factory=dict)
    integration_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_integration_audit(
    *,
    scene_family: str,
    repair_preview_path: str = "",
    execution_modes: Sequence[str] = ("baseline", "eval", "train"),
    mode_configs: Optional[Mapping[str, Path]] = None,
    spec_cfg_dir: Optional[Path] = None,
) -> IntegrationAudit:
    policy_spec = load_policy_spec(spec_cfg_dir)
    runtime_expectations = dict(policy_spec.runtime_expectations or {})
    mode_config_paths = {**DEFAULT_MODE_CONFIGS, **dict(mode_configs or {})}

    matrix_rows = []
    bindings_by_mode = {}
    for mode in execution_modes:
        config_path = Path(mode_config_paths[mode])
        config_payload = _ensure_mode_config(
            _load_yaml_file(config_path),
            scene_family=scene_family,
            repair_preview_path=repair_preview_path,
            mode=mode,
        )
        entry = _build_execution_mode_entry(
            mode=mode,
            config_path=config_path,
            config_payload=config_payload,
            scene_family=scene_family,
            repair_preview_path=repair_preview_path,
            policy_runtime_expectations=runtime_expectations,
        )
        matrix_rows.append(entry)
        bindings_by_mode[mode] = {
            "config_path": str(config_path),
            "scene_logging": dict(config_payload.get("scene_logging", {})),
            "scene_family_backend": dict(config_payload.get("scene_family_backend", {})),
            "repair": dict(config_payload.get("repair", {})),
            "effective_scene_binding": dict(entry.get("effective_scene_binding", {})),
            "effective_spec_binding": dict(entry.get("effective_spec_binding", {})),
            "repair_preview_binding": dict(entry.get("repair_preview_binding", {})),
        }

    acceptance = _build_integration_acceptance(
        matrix_rows,
        repair_preview_path=repair_preview_path,
        policy_runtime_expectations=runtime_expectations,
    )
    integration_required_artifacts = [
        str(item)
        for item in list(runtime_expectations.get("integration_audit_required_artifacts", []) or [])
    ]
    plan = {
        "integration_type": "phase10_integration_plan.v1",
        "scene_family": str(scene_family),
        "repair_preview_path": str(repair_preview_path),
        "target_execution_modes": [str(item) for item in execution_modes],
        "expected_run_types": [f"{mode}_accepted_run" for mode in execution_modes],
        "expected_output_contracts": {
            "rollout_required_artifacts": list(runtime_expectations.get("rollout_required_artifacts", []) or []),
            "integration_required_artifacts": integration_required_artifacts,
        },
        "validation_linkage": {
            "validation_context_preview_contract": "phase9_validation_context_preview.v1",
            "post_repair_evidence_consumer_contract": str(
                runtime_expectations.get(
                    "validation_post_repair_evidence_consumer_contract",
                    "phase10_post_repair_evidence_consumer.v2",
                )
            ),
        },
    }
    execution_matrix_payload = {
        "matrix_type": "phase10_execution_matrix.v1",
        "scene_family": str(scene_family),
        "repair_preview_path": str(repair_preview_path),
        "execution_modes": matrix_rows,
    }
    run_binding = {
        "binding_type": "phase10_run_binding.v1",
        "scene_family": str(scene_family),
        "repair_preview_path": str(repair_preview_path),
        "bindings_by_mode": bindings_by_mode,
    }
    summary = {
        "integration_type": "phase10_integration_summary.v1",
        "passed": bool(acceptance.get("passed", False)),
        "max_severity": str(acceptance.get("max_severity", "info")),
        "scene_family": str(scene_family),
        "repair_preview_bound_modes": [
            str(item.get("execution_mode", ""))
            for item in matrix_rows
            if bool(item.get("repair_preview_bound", False))
        ],
        "comparison_ready_modes": [
            str(item.get("execution_mode", ""))
            for item in matrix_rows
            if bool(item.get("comparison_ready_direct", False))
        ],
        "validation_only_glue_modes": list(acceptance.get("validation_only_glue_modes", []) or []),
    }
    return IntegrationAudit(
        integration_type="phase10_integration_audit.v1",
        scene_family=str(scene_family),
        repair_preview_path=str(repair_preview_path),
        execution_modes=[str(item) for item in execution_modes],
        integration_plan=plan,
        execution_matrix=execution_matrix_payload,
        run_binding=run_binding,
        integration_acceptance=acceptance,
        integration_summary=summary,
    )


def write_integration_bundle(
    audit: IntegrationAudit,
    integration_dir: str | Path,
    *,
    namespace_root: str | Path | None = None,
    bundle_name: str = "integration_latest",
    namespace: str = INTEGRATION_NAMESPACE,
) -> Dict[str, Path]:
    integration_path = Path(integration_dir)
    integration_path.mkdir(parents=True, exist_ok=True)

    integration_plan_path = integration_path / "integration_plan.json"
    execution_matrix_path = integration_path / "execution_matrix.json"
    run_binding_path = integration_path / "run_binding.json"
    integration_acceptance_path = integration_path / "integration_acceptance.json"
    integration_summary_path = integration_path / "integration_summary.json"
    integration_summary_md_path = integration_path / "integration_summary.md"
    manifest_path = integration_path / "manifest.json"

    integration_plan_path.write_text(
        json.dumps(audit.integration_plan, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    execution_matrix_path.write_text(
        json.dumps(audit.execution_matrix, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    run_binding_path.write_text(
        json.dumps(audit.run_binding, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    integration_acceptance_path.write_text(
        json.dumps(audit.integration_acceptance, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    integration_summary_path.write_text(
        json.dumps(audit.integration_summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    integration_summary_md_path.write_text(
        _build_summary_markdown(
            scene_family=audit.scene_family,
            repair_preview_path=audit.repair_preview_path,
            execution_matrix=list(audit.execution_matrix.get("execution_modes", []) or []),
            acceptance=audit.integration_acceptance,
        ),
        encoding="utf-8",
    )
    manifest_payload = {
        "bundle_type": audit.integration_type,
        "namespace": namespace,
        "scene_family": audit.scene_family,
        "repair_preview_path": audit.repair_preview_path,
        "integration_plan_path": integration_plan_path.name,
        "execution_matrix_path": execution_matrix_path.name,
        "run_binding_path": run_binding_path.name,
        "integration_acceptance_path": integration_acceptance_path.name,
        "integration_summary_path": integration_summary_path.name,
        "integration_summary_md_path": integration_summary_md_path.name,
        "passed": bool(audit.integration_acceptance.get("passed", False)),
        "max_severity": str(audit.integration_acceptance.get("max_severity", "info")),
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True), encoding="utf-8")

    bundle_paths: Dict[str, Path] = {
        "report_dir": integration_path,
        "integration_dir": integration_path,
        "integration_plan_path": integration_plan_path,
        "execution_matrix_path": execution_matrix_path,
        "run_binding_path": run_binding_path,
        "integration_acceptance_path": integration_acceptance_path,
        "integration_summary_path": integration_summary_path,
        "integration_summary_md_path": integration_summary_md_path,
        "manifest_path": manifest_path,
        "summary_path": integration_summary_path,
    }
    if namespace_root is not None:
        bundle_paths["namespace_manifest_path"] = write_namespace_manifest(
            namespace_root,
            bundle_name=bundle_name,
            report_mode=INTEGRATION_AUDIT_MODE,
            namespace=namespace,
            bundle_paths=bundle_paths,
            report_summary={
                "passed": bool(audit.integration_acceptance.get("passed", False)),
                "max_severity": str(audit.integration_acceptance.get("max_severity", "info")),
                "scene_family": audit.scene_family,
            },
        )
    return bundle_paths


def run_integration_audit_bundle(
    *,
    scene_family: str,
    repair_preview_path: str = "",
    execution_modes: Sequence[str] = ("baseline", "eval", "train"),
    reports_root: str | Path | None = None,
    bundle_name: str = "integration_latest",
    integration_dir: str | Path | None = None,
    namespaces: Mapping[str, str] | None = None,
    report_mode_artifacts: Mapping[str, Any] | None = None,
    spec_cfg_dir: Optional[Path] = None,
) -> tuple[IntegrationAudit, Dict[str, Path]]:
    audit = build_integration_audit(
        scene_family=scene_family,
        repair_preview_path=repair_preview_path,
        execution_modes=execution_modes,
        spec_cfg_dir=spec_cfg_dir,
    )
    namespace = str((namespaces or DEFAULT_REPORT_NAMESPACES).get(INTEGRATION_AUDIT_MODE, INTEGRATION_NAMESPACE))
    namespace_root = None
    if integration_dir is None:
        if reports_root is None:
            reports_root = TRAINING_ROOT / "reports"
        namespace_root = resolve_report_namespace_root(reports_root, INTEGRATION_AUDIT_MODE, namespaces=namespaces)
        integration_dir = namespace_root / str(bundle_name)
    bundle_paths = write_integration_bundle(
        audit,
        integration_dir,
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
    return audit, bundle_paths


__all__ = [
    "INTEGRATION_NAMESPACE",
    "IntegrationAudit",
    "build_integration_audit",
    "run_integration_audit_bundle",
    "write_integration_bundle",
]
