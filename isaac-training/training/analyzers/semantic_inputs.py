"""Semantic analysis input builder for Phase 6."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from analyzers.spec_ir import SpecIR, load_spec_ir


def _json_load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (list, tuple, set)):
        return [str(item) for item in values if item not in (None, "")]
    if values in ("", None):
        return []
    return [str(values)]


def _bundle_name(bundle_dir: str | Path, manifest: Mapping[str, Any] | None) -> str:
    if manifest:
        value = manifest.get("bundle_name")
        if value not in (None, ""):
            return str(value)
    return Path(bundle_dir).name


@dataclass
class StaticBundleContext:
    bundle_dir: str
    report: Dict[str, Any] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)
    manifest: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DynamicBundleContext:
    bundle_dir: str
    report: Dict[str, Any] = field(default_factory=dict)
    evidence: Dict[str, Any] = field(default_factory=dict)
    semantic_inputs: Dict[str, Any] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)
    manifest: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SemanticAnalysisInput:
    input_type: str
    spec_version: str
    spec_summary: Dict[str, Any] = field(default_factory=dict)
    static_context: Dict[str, Any] = field(default_factory=dict)
    dynamic_context: Dict[str, Any] = field(default_factory=dict)
    evidence_context: Dict[str, Any] = field(default_factory=dict)
    prompt_sections: Dict[str, Any] = field(default_factory=dict)
    cross_validation_requirements: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_static_bundle(static_bundle_dir: str | Path) -> StaticBundleContext:
    bundle_dir = Path(static_bundle_dir)
    return StaticBundleContext(
        bundle_dir=str(bundle_dir),
        report=_json_load(bundle_dir / "static_report.json"),
        summary=_json_load(bundle_dir / "summary.json"),
        manifest=_json_load(bundle_dir / "manifest.json"),
    )


def load_dynamic_bundle(dynamic_bundle_dir: str | Path) -> DynamicBundleContext:
    bundle_dir = Path(dynamic_bundle_dir)
    evidence_path = bundle_dir / "dynamic_evidence.json"
    semantic_path = bundle_dir / "semantic_inputs.json"
    return DynamicBundleContext(
        bundle_dir=str(bundle_dir),
        report=_json_load(bundle_dir / "dynamic_report.json"),
        evidence=_json_load(evidence_path) if evidence_path.exists() else {},
        semantic_inputs=_json_load(semantic_path) if semantic_path.exists() else {},
        summary=_json_load(bundle_dir / "summary.json"),
        manifest=_json_load(bundle_dir / "manifest.json"),
    )


def build_spec_summary(spec_ir: SpecIR) -> Dict[str, Any]:
    return {
        "spec_version": str(spec_ir.spec_version),
        "constraint_ids": sorted(str(key) for key in spec_ir.constraints.keys()),
        "reward_components": sorted(str(key) for key in spec_ir.reward_spec.components.keys()),
        "environment_families": sorted(str(key) for key in spec_ir.environment_families.keys()),
        "report_namespaces": dict(spec_ir.runtime_schema.report_namespaces),
        "report_mode_artifacts": {
            str(key): list(value)
            for key, value in spec_ir.runtime_schema.report_mode_artifacts.items()
        },
    }


def collect_evidence_context(
    static_bundle: StaticBundleContext,
    dynamic_bundle: DynamicBundleContext,
) -> Dict[str, Any]:
    static_findings = list((static_bundle.report or {}).get("findings", []) or [])
    dynamic_findings = list((dynamic_bundle.report or {}).get("findings", []) or [])
    evidence_objects = list((dynamic_bundle.report or {}).get("evidence_objects", []) or [])
    inherited_semantic_inputs = dict(dynamic_bundle.semantic_inputs or {})
    return {
        "static_findings": {
            "count": len(static_findings),
            "max_severity": (static_bundle.report or {}).get("max_severity", "info"),
            "finding_ids": [
                str(item.get("finding_id", ""))
                for item in static_findings
                if item.get("finding_id")
            ],
        },
        "dynamic_findings": {
            "count": len(dynamic_findings),
            "max_severity": (dynamic_bundle.report or {}).get("max_severity", "info"),
            "finding_ids": [
                str(item.get("finding_id", ""))
                for item in dynamic_findings
                if item.get("finding_id")
            ],
        },
        "witness_summaries": list((dynamic_bundle.report or {}).get("witnesses", []) or []),
        "evidence_objects": evidence_objects,
        "failure_hotspots": list(inherited_semantic_inputs.get("failure_hotspots", []) or []),
        "attribution_candidates": list(inherited_semantic_inputs.get("attribution_candidates", []) or []),
        "static_bundle_refs": {
            "bundle_dir": static_bundle.bundle_dir,
            "bundle_name": _bundle_name(static_bundle.bundle_dir, static_bundle.manifest),
        },
        "dynamic_bundle_refs": {
            "bundle_dir": dynamic_bundle.bundle_dir,
            "bundle_name": _bundle_name(dynamic_bundle.bundle_dir, dynamic_bundle.manifest),
            "primary_run_ids": list((dynamic_bundle.report or {}).get("primary_run_ids", []) or []),
            "comparison_run_ids": list((dynamic_bundle.report or {}).get("comparison_run_ids", []) or []),
        },
    }


def build_prompt_sections(
    spec_ir: SpecIR,
    static_bundle: StaticBundleContext,
    dynamic_bundle: DynamicBundleContext,
    evidence_context: Mapping[str, Any],
) -> Dict[str, Any]:
    inherited = dict(dynamic_bundle.semantic_inputs or {})
    return {
        "spec_context": {
            "spec_version": str(spec_ir.spec_version),
            "constraint_ids": sorted(str(key) for key in spec_ir.constraints.keys()),
            "reward_components": sorted(str(key) for key in spec_ir.reward_spec.components.keys()),
            "declared_families": sorted(str(key) for key in spec_ir.environment_families.keys()),
        },
        "static_context": {
            "report_summary": {
                "passed": bool((static_bundle.report or {}).get("passed", False)),
                "max_severity": (static_bundle.report or {}).get("max_severity", "info"),
                "num_findings": int((static_bundle.report or {}).get("num_findings", 0) or 0),
            },
            "top_findings": list((static_bundle.report or {}).get("findings", []) or [])[:8],
        },
        "dynamic_context": {
            "report_summary": {
                "passed": bool((dynamic_bundle.report or {}).get("passed", False)),
                "max_severity": (dynamic_bundle.report or {}).get("max_severity", "info"),
                "num_findings": int((dynamic_bundle.report or {}).get("num_findings", 0) or 0),
            },
            "witnesses": list((dynamic_bundle.report or {}).get("witnesses", []) or []),
            "primary_run_ids": list((dynamic_bundle.report or {}).get("primary_run_ids", []) or []),
            "comparison_run_ids": list((dynamic_bundle.report or {}).get("comparison_run_ids", []) or []),
        },
        "evidence_hotspots": {
            "failure_hotspots": list(evidence_context.get("failure_hotspots", []) or [])[:8],
            "attribution_candidates": list(evidence_context.get("attribution_candidates", []) or [])[:8],
            "evidence_objects": list(evidence_context.get("evidence_objects", []) or [])[:8],
        },
        "semantic_handoff": {
            "semantic_input_type": inherited.get("semantic_input_type", ""),
            "semantic_contract_type": inherited.get("semantic_contract_type", ""),
            "prompt_seeds": list(inherited.get("prompt_seeds", []) or []),
        },
    }


def build_semantic_analysis_input(
    *,
    spec_ir: Optional[SpecIR] = None,
    static_bundle: Optional[StaticBundleContext] = None,
    dynamic_bundle: Optional[DynamicBundleContext] = None,
    static_bundle_dir: str | Path | None = None,
    dynamic_bundle_dir: str | Path | None = None,
) -> SemanticAnalysisInput:
    effective_spec_ir = spec_ir or load_spec_ir()
    if static_bundle is None and static_bundle_dir is None:
        raise ValueError("Either static_bundle or static_bundle_dir must be provided.")
    if dynamic_bundle is None and dynamic_bundle_dir is None:
        raise ValueError("Either dynamic_bundle or dynamic_bundle_dir must be provided.")

    effective_static_bundle = static_bundle or load_static_bundle(static_bundle_dir)  # type: ignore[arg-type]
    effective_dynamic_bundle = dynamic_bundle or load_dynamic_bundle(dynamic_bundle_dir)  # type: ignore[arg-type]

    evidence_context = collect_evidence_context(
        effective_static_bundle,
        effective_dynamic_bundle,
    )
    prompt_sections = build_prompt_sections(
        effective_spec_ir,
        effective_static_bundle,
        effective_dynamic_bundle,
        evidence_context,
    )
    inherited_semantic_inputs = dict(effective_dynamic_bundle.semantic_inputs or {})
    return SemanticAnalysisInput(
        input_type="semantic_analysis_input.v1",
        spec_version=str(effective_spec_ir.spec_version),
        spec_summary=build_spec_summary(effective_spec_ir),
        static_context={
            "bundle_dir": effective_static_bundle.bundle_dir,
            "bundle_name": _bundle_name(
                effective_static_bundle.bundle_dir,
                effective_static_bundle.manifest,
            ),
            "summary": dict(effective_static_bundle.summary or {}),
            "manifest": dict(effective_static_bundle.manifest or {}),
        },
        dynamic_context={
            "bundle_dir": effective_dynamic_bundle.bundle_dir,
            "bundle_name": _bundle_name(
                effective_dynamic_bundle.bundle_dir,
                effective_dynamic_bundle.manifest,
            ),
            "summary": dict(effective_dynamic_bundle.summary or {}),
            "manifest": dict(effective_dynamic_bundle.manifest or {}),
            "primary_run_ids": list((effective_dynamic_bundle.report or {}).get("primary_run_ids", []) or []),
            "comparison_run_ids": list((effective_dynamic_bundle.report or {}).get("comparison_run_ids", []) or []),
        },
        evidence_context=evidence_context,
        prompt_sections=prompt_sections,
        cross_validation_requirements={
            "semantic_contract_type": inherited_semantic_inputs.get("semantic_contract_type", ""),
            "cross_validation_contract": dict(
                inherited_semantic_inputs.get("cross_validation_contract", {}) or {}
            ),
            "required_claim_types": _as_list(
                (
                    inherited_semantic_inputs.get("cross_validation_contract", {}) or {}
                ).get("required_supported_claim_types")
            ),
        },
        metadata={
            "semantic_input_source": "phase6_semantic_builder",
            "reused_dynamic_semantic_input_type": inherited_semantic_inputs.get(
                "semantic_input_type",
                "",
            ),
        },
    )


__all__ = [
    "DynamicBundleContext",
    "SemanticAnalysisInput",
    "StaticBundleContext",
    "build_prompt_sections",
    "build_semantic_analysis_input",
    "build_spec_summary",
    "collect_evidence_context",
    "load_dynamic_bundle",
    "load_static_bundle",
]
