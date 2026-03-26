"""CLI entrypoint for Phase 6 semantic CRE analysis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _training_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ensure_training_root_on_path() -> None:
    root = _training_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 6 semantic CRE analysis.")
    parser.add_argument(
        "--static-bundle-dir",
        required=True,
        help="Static audit bundle directory under analysis/static/.",
    )
    parser.add_argument(
        "--dynamic-bundle-dir",
        required=True,
        help="Dynamic analysis bundle directory under analysis/dynamic/.",
    )
    parser.add_argument(
        "--provider-mode",
        default="mock",
        help="Semantic provider mode, for example mock or azure_gateway.",
    )
    parser.add_argument(
        "--api-key-env-var",
        default="COMP_OPENAI_API_KEY",
        help="Environment variable used when provider-mode requires an API key.",
    )
    parser.add_argument(
        "--gateway-base-url",
        default="https://comp.azure-api.net/azure",
        help="Base gateway URL for azure_gateway provider mode.",
    )
    parser.add_argument(
        "--deployment-name",
        default="gpt4o",
        help="Deployment name for azure_gateway provider mode.",
    )
    parser.add_argument(
        "--api-version",
        default="2024-02-01",
        help="API version for azure_gateway provider mode.",
    )
    parser.add_argument(
        "--spec-cfg-dir",
        default=str(_training_root() / "cfg" / "spec_cfg"),
        help="Directory containing machine-readable spec config YAMLs.",
    )
    parser.add_argument(
        "--env-cfg-dir",
        default=str(_training_root() / "cfg" / "env_cfg"),
        help="Directory containing scene family config YAMLs.",
    )
    parser.add_argument(
        "--detector-cfg-dir",
        default=str(_training_root() / "cfg" / "detector_cfg"),
        help="Directory containing detector threshold YAMLs.",
    )
    parser.add_argument(
        "--scene-families",
        default="nominal,boundary_critical,shifted",
        help="Comma-separated scene families to include in semantic analysis context.",
    )
    parser.add_argument(
        "--reports-root",
        default=str(_training_root() / "reports"),
        help="Root reports directory used for namespaced semantic audit artifacts.",
    )
    parser.add_argument(
        "--bundle-name",
        default="semantic_audit_latest",
        help="Bundle name under the semantic analysis namespace.",
    )
    parser.add_argument(
        "--report-dir",
        default="",
        help="Optional explicit bundle directory override.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional extra output path for a standalone semantic_report.json copy.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    _ensure_training_root_on_path()

    from analyzers.semantic_analyzer import run_semantic_analysis_bundle
    from analyzers.semantic_provider import build_semantic_provider

    scene_families = [item.strip() for item in args.scene_families.split(",") if item.strip()]
    provider = build_semantic_provider(
        args.provider_mode,
        config={
            "provider_mode": args.provider_mode,
            "api_key_env_var": args.api_key_env_var,
            "base_url": args.gateway_base_url,
            "deployment_name": args.deployment_name,
            "api_version": args.api_version,
        },
    )
    report, bundle_paths = run_semantic_analysis_bundle(
        static_bundle_dir=Path(args.static_bundle_dir),
        dynamic_bundle_dir=Path(args.dynamic_bundle_dir),
        provider=provider,
        spec_cfg_dir=Path(args.spec_cfg_dir),
        env_cfg_dir=Path(args.env_cfg_dir),
        detector_cfg_dir=Path(args.detector_cfg_dir),
        scene_families=scene_families,
        reports_root=Path(args.reports_root),
        bundle_name=args.bundle_name,
        report_dir=Path(args.report_dir) if args.report_dir else None,
        output_path=Path(args.output) if args.output else None,
    )
    print(
        json.dumps(
            {
                "report_dir": str(bundle_paths["report_dir"]),
                "output": str(args.output) if args.output else "",
                "semantic_report_path": str(bundle_paths["semantic_report_path"]),
                "semantic_claims_path": str(bundle_paths["semantic_claims_path"]),
                "semantic_input_path": str(bundle_paths["semantic_input_path"]),
                "semantic_summary_path": str(bundle_paths["semantic_summary_path"]),
                "semantic_merge_input_path": str(bundle_paths["semantic_merge_input_path"]),
                "claim_consumer_path": str(bundle_paths["claim_consumer_path"]),
                "summary_path": str(bundle_paths["summary_path"]),
                "manifest_path": str(bundle_paths["manifest_path"]),
                "namespace_manifest_path": str(bundle_paths.get("namespace_manifest_path", "")),
                "namespace_contract_path": str(bundle_paths.get("namespace_contract_path", "")),
                "provider_mode": args.provider_mode,
                "passed": report.passed,
                "max_severity": report.max_severity,
                "num_findings": report.num_findings,
                "supported_claims": len(report.supported_claims),
                "weak_claims": len(report.weak_claims),
                "rejected_claims": len(report.rejected_claims),
                "most_likely_claim_type": report.human_summary.get("most_likely_claim_type", ""),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
