"""CLI entrypoint for Phase 4 static CRE analysis."""

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
    parser = argparse.ArgumentParser(description="Run Phase 4 static CRE analysis.")
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
        help="Comma-separated scene families to include in the static audit.",
    )
    parser.add_argument(
        "--checks",
        default="",
        help="Optional comma-separated subset of static checks to run.",
    )
    parser.add_argument(
        "--output",
        default=str(_training_root() / "reports" / "static_report.json"),
        help="Output path for the machine-readable static report.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _ensure_training_root_on_path()

    from analyzers.detector_runner import run_static_analysis

    scene_families = [item.strip() for item in args.scene_families.split(",") if item.strip()]
    checks = [item.strip() for item in args.checks.split(",") if item.strip()]
    report = run_static_analysis(
        spec_cfg_dir=Path(args.spec_cfg_dir),
        env_cfg_dir=Path(args.env_cfg_dir),
        detector_cfg_dir=Path(args.detector_cfg_dir),
        scene_families=scene_families,
        check_ids=checks or None,
        output_path=Path(args.output),
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "passed": report.passed,
                "max_severity": report.max_severity,
                "num_findings": report.num_findings,
                "scene_family_set": report.scene_family_set,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
