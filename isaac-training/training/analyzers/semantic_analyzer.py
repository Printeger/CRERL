"""Phase 6 semantic analyzer and namespaced semantic bundle writer."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from analyzers.report_contract import (
    DEFAULT_REPORT_NAMESPACES,
    SEMANTIC_ANALYSIS_MODE,
    resolve_report_namespace_root,
    write_namespace_manifest,
    write_report_namespace_contract,
)
from analyzers.semantic_claims import (
    SemanticClaim,
    SemanticClaimSet,
    SemanticCrossCheckResult,
)
from analyzers.semantic_crosscheck import validate_semantic_claims
from analyzers.semantic_inputs import build_semantic_analysis_input
from analyzers.semantic_provider import MockSemanticProvider, SemanticProvider
from analyzers.spec_ir import SpecIR, load_spec_ir


SEMANTIC_ANALYSIS_NAMESPACE = DEFAULT_REPORT_NAMESPACES[SEMANTIC_ANALYSIS_MODE]
SEVERITY_ORDER = {
    "info": 0,
    "warning": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def _claim_payloads(claims: Sequence[SemanticClaim]) -> List[Dict[str, Any]]:
    return [claim.to_dict() for claim in claims]


def _crosscheck_payloads(cross_checks: Sequence[SemanticCrossCheckResult]) -> List[Dict[str, Any]]:
    return [cross_check.to_dict() for cross_check in cross_checks]


def _severity_rank(value: str) -> int:
    return SEVERITY_ORDER.get(str(value).lower(), 0)


def _max_severity(claims: Sequence[Mapping[str, Any]]) -> str:
    if not claims:
        return "info"
    return max(claims, key=lambda item: _severity_rank(str(item.get("severity", "info")))).get(
        "severity",
        "info",
    )


def _primary_claim(claims: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    if not claims:
        return {}
    return dict(
        max(
            claims,
            key=lambda item: (
                float(item.get("confidence", 0.0) or 0.0),
                _severity_rank(str(item.get("severity", "info"))),
            ),
        )
    )


def _build_human_summary(report: "SemanticAnalyzerReport") -> Dict[str, Any]:
    strongest_supported = _primary_claim(report.supported_claims)
    strongest_weak = _primary_claim(report.weak_claims)
    top_claim = strongest_supported or strongest_weak
    next_step = ""
    if strongest_supported:
        next_step = strongest_supported.get("repair_direction_hint", "")
    elif strongest_weak:
        next_step = "collect more dynamic evidence before acting on weak semantic claims"

    return {
        "most_likely_claim_type": top_claim.get("claim_type", ""),
        "most_likely_claim_summary": top_claim.get("summary", ""),
        "strongest_supported_claim_id": strongest_supported.get("claim_id", ""),
        "strongest_uncertainty_claim_id": strongest_weak.get("claim_id", ""),
        "next_check_or_repair_direction": next_step,
    }


def _claim_to_finding(claim: Mapping[str, Any], *, index: int) -> Dict[str, Any]:
    return {
        "finding_id": f"{claim.get('claim_id', 'claim')}:{index}",
        "claim_id": str(claim.get("claim_id", "")),
        "claim_type": str(claim.get("claim_type", "unknown")),
        "status": str(claim.get("status", "weak")),
        "severity": str(claim.get("severity", "warning")),
        "confidence": float(claim.get("confidence", 0.0) or 0.0),
        "summary": str(claim.get("summary", "")),
        "supporting_evidence_ids": list(claim.get("supporting_evidence_ids", []) or []),
        "supporting_witness_ids": list(claim.get("supporting_witness_ids", []) or []),
        "supporting_finding_ids": list(claim.get("supporting_finding_ids", []) or []),
    }


def _claim_set_from_report(report: "SemanticAnalyzerReport") -> SemanticClaimSet:
    return SemanticClaimSet(
        supported_claims=[SemanticClaim.from_dict(item) for item in report.supported_claims],
        weak_claims=[SemanticClaim.from_dict(item) for item in report.weak_claims],
        rejected_claims=[SemanticClaim.from_dict(item) for item in report.rejected_claims],
        cross_checks=[SemanticCrossCheckResult(**dict(item)) for item in report.cross_checks],
        metadata=dict(report.metadata.get("claim_set_metadata", {}) or {}),
    )


@dataclass
class SemanticAnalyzerReport:
    """Machine-readable semantic diagnosis report."""

    report_type: str
    spec_version: str
    static_bundle_name: str
    dynamic_bundle_name: str
    passed: bool
    max_severity: str
    num_findings: int
    supported_claims: List[Dict[str, Any]] = field(default_factory=list)
    weak_claims: List[Dict[str, Any]] = field(default_factory=list)
    rejected_claims: List[Dict[str, Any]] = field(default_factory=list)
    cross_checks: List[Dict[str, Any]] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    human_summary: Dict[str, Any] = field(default_factory=dict)
    semantic_input: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_semantic_report(
    *,
    spec_version: str,
    static_bundle_name: str,
    dynamic_bundle_name: str,
    claim_set: SemanticClaimSet,
    semantic_input: Mapping[str, Any],
    metadata: Optional[Mapping[str, Any]] = None,
) -> SemanticAnalyzerReport:
    supported_claims = _claim_payloads(claim_set.supported_claims)
    weak_claims = _claim_payloads(claim_set.weak_claims)
    rejected_claims = _claim_payloads(claim_set.rejected_claims)
    all_claims = [*supported_claims, *weak_claims, *rejected_claims]
    findings = [
        _claim_to_finding(claim, index=index)
        for index, claim in enumerate(all_claims, start=1)
    ]
    blocking_claims = [
        claim
        for claim in [*supported_claims, *weak_claims]
        if _severity_rank(str(claim.get("severity", "info"))) >= _severity_rank("high")
    ]
    report = SemanticAnalyzerReport(
        report_type="semantic_analyzer_report.v1",
        spec_version=str(spec_version),
        static_bundle_name=str(static_bundle_name),
        dynamic_bundle_name=str(dynamic_bundle_name),
        passed=not blocking_claims,
        max_severity=_max_severity(all_claims),
        num_findings=len(all_claims),
        supported_claims=supported_claims,
        weak_claims=weak_claims,
        rejected_claims=rejected_claims,
        cross_checks=_crosscheck_payloads(claim_set.cross_checks),
        findings=findings,
        semantic_input=dict(semantic_input),
        metadata={
            **dict(metadata or {}),
            "claim_set_metadata": dict(claim_set.metadata or {}),
        },
    )
    report.human_summary = _build_human_summary(report)
    return report


def write_semantic_report(report: SemanticAnalyzerReport, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return path


def build_semantic_summary_markdown(report: SemanticAnalyzerReport) -> str:
    strongest_supported = report.human_summary.get("strongest_supported_claim_id", "")
    strongest_uncertainty = report.human_summary.get("strongest_uncertainty_claim_id", "")
    lines = [
        "# Semantic Diagnosis Summary",
        "",
        f"- Spec version: `{report.spec_version}`",
        f"- Static bundle: `{report.static_bundle_name}`",
        f"- Dynamic bundle: `{report.dynamic_bundle_name}`",
        f"- Passed: `{report.passed}`",
        f"- Max severity: `{report.max_severity}`",
        f"- Supported claims: `{len(report.supported_claims)}`",
        f"- Weak claims: `{len(report.weak_claims)}`",
        f"- Rejected claims: `{len(report.rejected_claims)}`",
        "",
        "## Top Diagnosis",
        "",
        f"- Claim type: `{report.human_summary.get('most_likely_claim_type', '')}`",
        f"- Summary: {report.human_summary.get('most_likely_claim_summary', '')}",
        f"- Strongest supported claim: `{strongest_supported}`",
        f"- Strongest uncertainty: `{strongest_uncertainty}`",
        f"- Next direction: {report.human_summary.get('next_check_or_repair_direction', '')}",
    ]
    return "\n".join(lines).strip() + "\n"


def run_semantic_analysis(
    *,
    static_bundle_dir: str | Path,
    dynamic_bundle_dir: str | Path,
    provider: Optional[SemanticProvider] = None,
    spec_ir: Optional[SpecIR] = None,
    spec_cfg_dir=None,
    env_cfg_dir=None,
    detector_cfg_dir=None,
    scene_families: Sequence[str] | None = None,
    output_path: str | Path | None = None,
) -> SemanticAnalyzerReport:
    effective_spec_ir = spec_ir or load_spec_ir(
        spec_cfg_dir=spec_cfg_dir,
        env_cfg_dir=env_cfg_dir,
        detector_cfg_dir=detector_cfg_dir,
        scene_families=scene_families or ("nominal", "boundary_critical", "shifted"),
    )
    semantic_input = build_semantic_analysis_input(
        spec_ir=effective_spec_ir,
        static_bundle_dir=static_bundle_dir,
        dynamic_bundle_dir=dynamic_bundle_dir,
    )
    effective_provider = provider or MockSemanticProvider()
    claims = effective_provider.generate_claims(semantic_input)
    claim_set = validate_semantic_claims(claims, semantic_input=semantic_input)
    semantic_input_payload = semantic_input.to_dict()
    report = build_semantic_report(
        spec_version=effective_spec_ir.spec_version,
        static_bundle_name=str(semantic_input_payload.get("static_context", {}).get("bundle_name", "")),
        dynamic_bundle_name=str(semantic_input_payload.get("dynamic_context", {}).get("bundle_name", "")),
        claim_set=claim_set,
        semantic_input=semantic_input_payload,
        metadata={
            "detector_type": "semantic",
            "provider_name": getattr(effective_provider, "provider_name", effective_provider.__class__.__name__),
            "provider_mode": "mock" if isinstance(effective_provider, MockSemanticProvider) else "custom",
            "source_paths": dict(effective_spec_ir.source_paths),
            "report_namespace": effective_spec_ir.runtime_schema.report_namespaces.get(
                SEMANTIC_ANALYSIS_MODE,
                SEMANTIC_ANALYSIS_NAMESPACE,
            ),
            "report_artifacts": list(
                effective_spec_ir.runtime_schema.report_mode_artifacts.get(SEMANTIC_ANALYSIS_MODE, ())
            ),
            "static_bundle_dir": str(static_bundle_dir),
            "dynamic_bundle_dir": str(dynamic_bundle_dir),
        },
    )
    if output_path is not None:
        write_semantic_report(report, output_path)
    return report


def write_semantic_analysis_bundle(
    report: SemanticAnalyzerReport,
    report_dir: str | Path,
    *,
    namespace_root: str | Path | None = None,
    bundle_name: str = "semantic_audit_latest",
    namespace: str = SEMANTIC_ANALYSIS_NAMESPACE,
) -> Dict[str, Path]:
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)

    semantic_report_path = write_semantic_report(report, report_path / "semantic_report.json")
    semantic_claims_path = report_path / "semantic_claims.json"
    semantic_input_path = report_path / "semantic_input.json"
    semantic_summary_path = report_path / "semantic_summary.md"
    summary_path = report_path / "summary.json"
    manifest_path = report_path / "manifest.json"

    semantic_claims_path.write_text(
        json.dumps(_claim_set_from_report(report).to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    semantic_input_path.write_text(
        json.dumps(dict(report.semantic_input), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    semantic_summary_path.write_text(
        build_semantic_summary_markdown(report),
        encoding="utf-8",
    )

    summary_payload = {
        "report_type": report.report_type,
        "spec_version": report.spec_version,
        "static_bundle_name": report.static_bundle_name,
        "dynamic_bundle_name": report.dynamic_bundle_name,
        "passed": bool(report.passed),
        "max_severity": str(report.max_severity),
        "num_findings": int(report.num_findings),
        "supported_claims": len(report.supported_claims),
        "weak_claims": len(report.weak_claims),
        "rejected_claims": len(report.rejected_claims),
    }
    summary_path.write_text(
        json.dumps(summary_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    manifest_payload = {
        "bundle_type": "semantic_analysis_bundle.v1",
        "namespace": namespace,
        "report_type": report.report_type,
        "spec_version": report.spec_version,
        "static_bundle_name": report.static_bundle_name,
        "dynamic_bundle_name": report.dynamic_bundle_name,
        "report_path": semantic_report_path.name,
        "semantic_claims_path": semantic_claims_path.name,
        "semantic_input_path": semantic_input_path.name,
        "semantic_summary_path": semantic_summary_path.name,
        "summary_path": summary_path.name,
        "passed": bool(report.passed),
        "max_severity": str(report.max_severity),
        "num_findings": int(report.num_findings),
        "metadata": dict(report.metadata),
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True), encoding="utf-8")

    bundle_paths: Dict[str, Path] = {
        "report_dir": report_path,
        "semantic_report_path": semantic_report_path,
        "semantic_claims_path": semantic_claims_path,
        "semantic_input_path": semantic_input_path,
        "semantic_summary_path": semantic_summary_path,
        "summary_path": summary_path,
        "manifest_path": manifest_path,
    }
    if namespace_root is not None:
        bundle_paths["namespace_manifest_path"] = write_namespace_manifest(
            namespace_root,
            bundle_name=bundle_name,
            report_mode=SEMANTIC_ANALYSIS_MODE,
            namespace=namespace,
            bundle_paths=bundle_paths,
            report_summary={
                "passed": bool(report.passed),
                "max_severity": str(report.max_severity),
                "num_findings": int(report.num_findings),
                "supported_claims": len(report.supported_claims),
                "weak_claims": len(report.weak_claims),
                "rejected_claims": len(report.rejected_claims),
            },
        )
    return bundle_paths


def run_semantic_analysis_bundle(
    *,
    static_bundle_dir: str | Path,
    dynamic_bundle_dir: str | Path,
    provider: Optional[SemanticProvider] = None,
    spec_ir: Optional[SpecIR] = None,
    spec_cfg_dir=None,
    env_cfg_dir=None,
    detector_cfg_dir=None,
    scene_families: Sequence[str] | None = None,
    reports_root: str | Path | None = None,
    bundle_name: str = "semantic_audit_latest",
    report_dir: str | Path | None = None,
    output_path: str | Path | None = None,
) -> tuple[SemanticAnalyzerReport, Dict[str, Path]]:
    effective_spec_ir = spec_ir or load_spec_ir(
        spec_cfg_dir=spec_cfg_dir,
        env_cfg_dir=env_cfg_dir,
        detector_cfg_dir=detector_cfg_dir,
        scene_families=scene_families or ("nominal", "boundary_critical", "shifted"),
    )
    report = run_semantic_analysis(
        static_bundle_dir=static_bundle_dir,
        dynamic_bundle_dir=dynamic_bundle_dir,
        provider=provider,
        spec_ir=effective_spec_ir,
        output_path=output_path,
    )

    namespace = str(report.metadata.get("report_namespace", SEMANTIC_ANALYSIS_NAMESPACE))
    namespace_root = None
    if report_dir is None:
        if reports_root is None:
            reports_root = Path(__file__).resolve().parents[1] / "reports"
        namespace_root = resolve_report_namespace_root(
            reports_root,
            SEMANTIC_ANALYSIS_MODE,
            namespaces=effective_spec_ir.runtime_schema.report_namespaces,
        )
        report_dir = namespace_root / str(bundle_name)

    bundle_paths = write_semantic_analysis_bundle(
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
    "SEMANTIC_ANALYSIS_NAMESPACE",
    "SemanticAnalyzerReport",
    "build_semantic_report",
    "build_semantic_summary_markdown",
    "run_semantic_analysis",
    "run_semantic_analysis_bundle",
    "write_semantic_analysis_bundle",
    "write_semantic_report",
]
