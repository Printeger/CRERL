"""CLI entrypoint for Phase 10 training-stack integration audit."""

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
    parser = argparse.ArgumentParser(description="Run Phase 10 CRE integration audit.")
    parser.add_argument(
        "--scene-family",
        default="nominal",
        help="Scene family used to build the effective integration binding.",
    )
    parser.add_argument(
        "--repair-preview-path",
        default="",
        help="Optional Phase 9 validation_context_preview.json path.",
    )
    parser.add_argument(
        "--execution-modes",
        default="baseline,eval,train",
        help="Comma-separated execution modes to audit.",
    )
    parser.add_argument(
        "--reports-root",
        default=str(_training_root() / "reports"),
        help="Root reports directory used for namespaced integration artifacts.",
    )
    parser.add_argument(
        "--bundle-name",
        default="integration_latest",
        help="Bundle name under the integration namespace.",
    )
    parser.add_argument(
        "--integration-dir",
        default="",
        help="Optional explicit integration bundle directory override.",
    )
    parser.add_argument(
        "--spec-cfg-dir",
        default=str(_training_root() / "cfg" / "spec_cfg"),
        help="Directory containing machine-readable spec config YAMLs.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional extra output path for a standalone integration_summary.json copy.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _ensure_training_root_on_path()

    from analyzers.report_contract import DEFAULT_REPORT_MODE_ARTIFACTS, DEFAULT_REPORT_NAMESPACES
    from pipeline.integration_bundle import run_integration_audit_bundle

    execution_modes = [item.strip() for item in args.execution_modes.split(",") if item.strip()]
    audit, bundle_paths = run_integration_audit_bundle(
        scene_family=args.scene_family,
        repair_preview_path=args.repair_preview_path,
        execution_modes=execution_modes,
        reports_root=Path(args.reports_root),
        bundle_name=args.bundle_name,
        integration_dir=Path(args.integration_dir) if args.integration_dir else None,
        namespaces=DEFAULT_REPORT_NAMESPACES,
        report_mode_artifacts=DEFAULT_REPORT_MODE_ARTIFACTS,
        spec_cfg_dir=Path(args.spec_cfg_dir),
    )
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(audit.integration_summary, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    print(
        json.dumps(
            {
                "integration_dir": str(bundle_paths["integration_dir"]),
                "integration_plan_path": str(bundle_paths["integration_plan_path"]),
                "execution_matrix_path": str(bundle_paths["execution_matrix_path"]),
                "run_binding_path": str(bundle_paths["run_binding_path"]),
                "integration_acceptance_path": str(bundle_paths["integration_acceptance_path"]),
                "integration_summary_path": str(bundle_paths["integration_summary_path"]),
                "integration_summary_md_path": str(bundle_paths["integration_summary_md_path"]),
                "manifest_path": str(bundle_paths["manifest_path"]),
                "namespace_manifest_path": str(bundle_paths.get("namespace_manifest_path", "")),
                "namespace_contract_path": str(bundle_paths.get("namespace_contract_path", "")),
                "passed": bool(audit.integration_acceptance.get("passed", False)),
                "max_severity": str(audit.integration_acceptance.get("max_severity", "info")),
                "scene_family": audit.scene_family,
                "repair_preview_path": audit.repair_preview_path,
                "comparison_ready_modes": list(audit.integration_summary.get("comparison_ready_modes", []) or []),
                "validation_only_glue_modes": list(audit.integration_summary.get("validation_only_glue_modes", []) or []),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
