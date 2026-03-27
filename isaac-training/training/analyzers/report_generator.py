"""Phase 7 unified report generator and namespaced report bundle writer."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from analyzers.report_contract import (
    DEFAULT_REPORT_NAMESPACES,
    REPORT_GENERATION_MODE,
    resolve_report_namespace_root,
    write_namespace_manifest,
    write_report_namespace_contract,
)
from analyzers.report_merge import (
    RankedFinding,
    RepairHandoffBundle,
    build_repair_handoff,
    build_root_cause_summary,
    build_semantic_claim_summary,
    build_witness_summary,
    normalize_dynamic_findings,
    normalize_semantic_claims,
    normalize_static_findings,
    rank_findings,
)
from analyzers.spec_ir import SpecIR, load_spec_ir


REPORT_NAMESPACE = DEFAULT_REPORT_NAMESPACES[REPORT_GENERATION_MODE]
SEVERITY_ORDER = {
    "info": 0,
    "warning": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def _severity_rank(value: str) -> int:
    return SEVERITY_ORDER.get(str(value).lower(), 0)


def _json_load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _bundle_name(bundle_dir: Path, manifest: Mapping[str, Any]) -> str:
    return str(
        manifest.get("bundle_name")
        or manifest.get("latest_bundle")
        or bundle_dir.name
    )


def load_report_bundle_inputs(
    *,
    static_bundle_dir: str | Path,
    dynamic_bundle_dir: str | Path,
    semantic_bundle_dir: str | Path,
) -> Dict[str, Any]:
    static_dir = Path(static_bundle_dir)
    dynamic_dir = Path(dynamic_bundle_dir)
    semantic_dir = Path(semantic_bundle_dir)

    static_manifest = _json_load(static_dir / "manifest.json")
    dynamic_manifest = _json_load(dynamic_dir / "manifest.json")
    semantic_manifest = _json_load(semantic_dir / "manifest.json")

    analysis_root = None
    for candidate in semantic_dir.parents:
        if candidate.name == "analysis":
            analysis_root = candidate
            break

    namespace_contract = {}
    if analysis_root is not None:
        contract_path = analysis_root / "report_namespace_contract.json"
        if contract_path.exists():
            namespace_contract = _json_load(contract_path)

    return {
        "static": {
            "bundle_dir": static_dir,
            "bundle_name": _bundle_name(static_dir, static_manifest),
            "report": _json_load(static_dir / "static_report.json"),
            "summary": _json_load(static_dir / "summary.json"),
            "manifest": static_manifest,
        },
        "dynamic": {
            "bundle_dir": dynamic_dir,
            "bundle_name": _bundle_name(dynamic_dir, dynamic_manifest),
            "report": _json_load(dynamic_dir / "dynamic_report.json"),
            "summary": _json_load(dynamic_dir / "summary.json"),
            "manifest": dynamic_manifest,
        },
        "semantic": {
            "bundle_dir": semantic_dir,
            "bundle_name": _bundle_name(semantic_dir, semantic_manifest),
            "report": _json_load(semantic_dir / "semantic_report.json"),
            "summary": _json_load(semantic_dir / "summary.json"),
            "manifest": semantic_manifest,
            "claim_consumer": _json_load(semantic_dir / "claim_consumer.json"),
            "semantic_merge_input": _json_load(semantic_dir / "semantic_merge_input.json"),
        },
        "namespace_contract": namespace_contract,
    }


@dataclass
class UnifiedReport:
    """Machine-readable unified inconsistency report for Phase 7."""

    report_type: str
    spec_version: str
    passed: bool
    max_severity: str
    num_ranked_findings: int
    input_bundles: Dict[str, Any] = field(default_factory=dict)
    ranked_findings: list[Dict[str, Any]] = field(default_factory=list)
    root_cause_summary: Dict[str, Any] = field(default_factory=dict)
    witness_summary: Dict[str, Any] = field(default_factory=dict)
    semantic_claim_summary: Dict[str, Any] = field(default_factory=dict)
    repair_handoff: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _max_severity(ranked_findings: Sequence[RankedFinding]) -> str:
    if not ranked_findings:
        return "info"
    return max(ranked_findings, key=lambda item: _severity_rank(item.severity)).severity


def _build_human_summary_markdown(report: UnifiedReport) -> str:
    root = dict(report.root_cause_summary or {})
    top_finding = (report.ranked_findings or [{}])[0] if report.ranked_findings else {}
    lines = [
        "# Unified CRE Report Summary",
        "",
        f"- Spec version: `{report.spec_version}`",
        f"- Passed: `{report.passed}`",
        f"- Max severity: `{report.max_severity}`",
        f"- Ranked findings: `{report.num_ranked_findings}`",
        "",
        "## Primary Diagnosis",
        "",
        f"- Claim type: `{root.get('primary_claim_type', '')}`",
        f"- Summary: {root.get('primary_summary', '')}",
        f"- Support status: `{root.get('primary_support_status', '')}`",
        "",
        "## Strongest Evidence",
        "",
        f"- Source: `{top_finding.get('source_namespace', '')}`",
        f"- Severity: `{top_finding.get('severity', '')}`",
        f"- Confidence: `{top_finding.get('confidence', 0.0)}`",
        f"- Summary: {top_finding.get('summary', '')}",
        "",
        "## Next Repair Direction",
        "",
        f"- Direction: `{(report.repair_handoff.get('primary_repair_direction', '') if report.repair_handoff else '')}`",
        f"- Impacted components: `{', '.join(report.repair_handoff.get('impacted_components_union', [])) if report.repair_handoff else ''}`",
    ]
    return "\n".join(lines).strip() + "\n"


def build_unified_report(
    *,
    spec_version: str,
    bundle_inputs: Mapping[str, Any],
) -> UnifiedReport:
    static_report = dict(bundle_inputs["static"]["report"])
    dynamic_report = dict(bundle_inputs["dynamic"]["report"])
    semantic_report = dict(bundle_inputs["semantic"]["report"])
    claim_consumer = dict(bundle_inputs["semantic"]["claim_consumer"])

    normalized = [
        *normalize_static_findings(static_report),
        *normalize_dynamic_findings(dynamic_report),
        *normalize_semantic_claims(semantic_report, claim_consumer),
    ]
    ranked = rank_findings(normalized)
    root_cause_summary = build_root_cause_summary(ranked)
    handoff = build_repair_handoff(
        ranked,
        claim_consumer,
        primary_claim_type_override=str(root_cause_summary.get("primary_claim_type", "")),
    )

    blocking = [item for item in ranked if _severity_rank(item.severity) >= _severity_rank("high")]
    return UnifiedReport(
        report_type="phase7_unified_report.v1",
        spec_version=str(spec_version),
        passed=not blocking,
        max_severity=_max_severity(ranked),
        num_ranked_findings=len(ranked),
        input_bundles={
            "static": {
                "bundle_name": bundle_inputs["static"]["bundle_name"],
                "bundle_dir": str(bundle_inputs["static"]["bundle_dir"]),
            },
            "dynamic": {
                "bundle_name": bundle_inputs["dynamic"]["bundle_name"],
                "bundle_dir": str(bundle_inputs["dynamic"]["bundle_dir"]),
            },
            "semantic": {
                "bundle_name": bundle_inputs["semantic"]["bundle_name"],
                "bundle_dir": str(bundle_inputs["semantic"]["bundle_dir"]),
            },
        },
        ranked_findings=[item.to_dict() for item in ranked],
        root_cause_summary=root_cause_summary,
        witness_summary=build_witness_summary(dynamic_report),
        semantic_claim_summary=build_semantic_claim_summary(semantic_report),
        repair_handoff=handoff.to_dict(),
        metadata={
            "namespace_contract": dict(bundle_inputs.get("namespace_contract", {}) or {}),
            "source_namespaces": ["analysis/static", "analysis/dynamic", "analysis/semantic"],
            "semantic_merge_input": dict(bundle_inputs["semantic"].get("semantic_merge_input", {})),
        },
    )


def write_unified_report(report: UnifiedReport, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return path


def write_report_bundle(
    report: UnifiedReport,
    report_dir: str | Path,
    *,
    namespace_root: str | Path | None = None,
    bundle_name: str = "report_latest",
    namespace: str = REPORT_NAMESPACE,
) -> Dict[str, Path]:
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)

    report_json_path = write_unified_report(report, report_path / "report.json")
    ranked_findings_path = report_path / "ranked_findings.json"
    repair_handoff_path = report_path / "repair_handoff.json"
    report_summary_path = report_path / "report_summary.md"
    summary_path = report_path / "summary.json"
    manifest_path = report_path / "manifest.json"

    ranked_findings_path.write_text(
        json.dumps(report.ranked_findings, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    repair_handoff_path.write_text(
        json.dumps(dict(report.repair_handoff), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    report_summary_path.write_text(
        _build_human_summary_markdown(report),
        encoding="utf-8",
    )
    summary_payload = {
        "report_type": report.report_type,
        "spec_version": report.spec_version,
        "passed": bool(report.passed),
        "max_severity": str(report.max_severity),
        "num_ranked_findings": int(report.num_ranked_findings),
        "primary_claim_type": str((report.root_cause_summary or {}).get("primary_claim_type", "")),
        "repair_ready_claims": len((report.repair_handoff or {}).get("selected_claims", [])),
    }
    summary_path.write_text(json.dumps(summary_payload, indent=2, sort_keys=True), encoding="utf-8")
    manifest_payload = {
        "bundle_type": "report_generation_bundle.v1",
        "namespace": namespace,
        "report_type": report.report_type,
        "spec_version": report.spec_version,
        "report_path": report_json_path.name,
        "ranked_findings_path": ranked_findings_path.name,
        "repair_handoff_path": repair_handoff_path.name,
        "report_summary_path": report_summary_path.name,
        "summary_path": summary_path.name,
        "passed": bool(report.passed),
        "max_severity": str(report.max_severity),
        "num_ranked_findings": int(report.num_ranked_findings),
        "metadata": dict(report.metadata),
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True), encoding="utf-8")

    bundle_paths: Dict[str, Path] = {
        "report_dir": report_path,
        "report_json_path": report_json_path,
        "ranked_findings_path": ranked_findings_path,
        "repair_handoff_path": repair_handoff_path,
        "report_summary_path": report_summary_path,
        "summary_path": summary_path,
        "manifest_path": manifest_path,
    }
    if namespace_root is not None:
        bundle_paths["namespace_manifest_path"] = write_namespace_manifest(
            namespace_root,
            bundle_name=bundle_name,
            report_mode=REPORT_GENERATION_MODE,
            namespace=namespace,
            bundle_paths=bundle_paths,
            report_summary={
                "passed": bool(report.passed),
                "max_severity": str(report.max_severity),
                "num_ranked_findings": int(report.num_ranked_findings),
                "primary_claim_type": str((report.root_cause_summary or {}).get("primary_claim_type", "")),
            },
        )
    return bundle_paths


def run_report_generation(
    *,
    static_bundle_dir: str | Path,
    dynamic_bundle_dir: str | Path,
    semantic_bundle_dir: str | Path,
    spec_ir: Optional[SpecIR] = None,
    spec_cfg_dir=None,
    env_cfg_dir=None,
    detector_cfg_dir=None,
    scene_families: Sequence[str] | None = None,
    output_path: str | Path | None = None,
) -> UnifiedReport:
    effective_spec_ir = spec_ir or load_spec_ir(
        spec_cfg_dir=spec_cfg_dir,
        env_cfg_dir=env_cfg_dir,
        detector_cfg_dir=detector_cfg_dir,
        scene_families=scene_families or ("nominal", "boundary_critical", "shifted"),
    )
    bundle_inputs = load_report_bundle_inputs(
        static_bundle_dir=static_bundle_dir,
        dynamic_bundle_dir=dynamic_bundle_dir,
        semantic_bundle_dir=semantic_bundle_dir,
    )
    report = build_unified_report(
        spec_version=effective_spec_ir.spec_version,
        bundle_inputs=bundle_inputs,
    )
    report.metadata.update(
        {
            "report_namespace": effective_spec_ir.runtime_schema.report_namespaces.get(
                REPORT_GENERATION_MODE,
                REPORT_NAMESPACE,
            ),
            "report_artifacts": list(
                effective_spec_ir.runtime_schema.report_mode_artifacts.get(REPORT_GENERATION_MODE, ())
            ),
            "source_paths": dict(effective_spec_ir.source_paths),
        }
    )
    if output_path is not None:
        write_unified_report(report, output_path)
    return report


def run_report_generation_bundle(
    *,
    static_bundle_dir: str | Path,
    dynamic_bundle_dir: str | Path,
    semantic_bundle_dir: str | Path,
    spec_ir: Optional[SpecIR] = None,
    spec_cfg_dir=None,
    env_cfg_dir=None,
    detector_cfg_dir=None,
    scene_families: Sequence[str] | None = None,
    reports_root: str | Path | None = None,
    bundle_name: str = "report_latest",
    report_dir: str | Path | None = None,
    output_path: str | Path | None = None,
) -> tuple[UnifiedReport, Dict[str, Path]]:
    effective_spec_ir = spec_ir or load_spec_ir(
        spec_cfg_dir=spec_cfg_dir,
        env_cfg_dir=env_cfg_dir,
        detector_cfg_dir=detector_cfg_dir,
        scene_families=scene_families or ("nominal", "boundary_critical", "shifted"),
    )
    report = run_report_generation(
        static_bundle_dir=static_bundle_dir,
        dynamic_bundle_dir=dynamic_bundle_dir,
        semantic_bundle_dir=semantic_bundle_dir,
        spec_ir=effective_spec_ir,
        output_path=output_path,
    )

    namespace = str(report.metadata.get("report_namespace", REPORT_NAMESPACE))
    namespace_root = None
    if report_dir is None:
        if reports_root is None:
            reports_root = Path(__file__).resolve().parents[1] / "reports"
        namespace_root = resolve_report_namespace_root(
            reports_root,
            REPORT_GENERATION_MODE,
            namespaces=effective_spec_ir.runtime_schema.report_namespaces,
        )
        report_dir = namespace_root / str(bundle_name)

    bundle_paths = write_report_bundle(
        report,
        report_dir,
        namespace_root=namespace_root,
        bundle_name=str(bundle_name),
        namespace=namespace,
    )
    if reports_root is not None:
        bundle_paths["namespace_contract_path"] = write_report_namespace_contract(
            reports_root,
            namespaces=effective_spec_ir.runtime_schema.report_namespaces,
            report_mode_artifacts=effective_spec_ir.runtime_schema.report_mode_artifacts,
        )
    return report, bundle_paths


__all__ = [
    "REPORT_NAMESPACE",
    "UnifiedReport",
    "build_unified_report",
    "load_report_bundle_inputs",
    "run_report_generation",
    "run_report_generation_bundle",
    "write_report_bundle",
    "write_unified_report",
]
