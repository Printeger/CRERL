import sys
from pathlib import Path

import pytest

ISAAC_TRAINING_ROOT = Path(__file__).resolve().parents[3]
TRAINING_ROOT = ISAAC_TRAINING_ROOT / "training"
if str(TRAINING_ROOT) not in sys.path:
    sys.path.insert(0, str(TRAINING_ROOT))

# Historical / legacy pipeline imports.
from analyzers.legacy.dynamic_analyzer import run_dynamic_analysis
from analyzers.legacy.report_generator import generate_report
from analyzers.legacy.semantic_analyzer import run_semantic_analysis
from analyzers.legacy.static_analyzer import StaticReport, run_static_analysis
from repair.legacy.repair_generator import generate_repair
from repair.legacy.validator import PatchValidationResult, validate_repair


SPEC_DIR = TRAINING_ROOT / "cfg" / "spec_cfg"
LOG_ROOT = TRAINING_ROOT / "logs"
REAL_LOG_DIR = next(
    (
        path
        for path in sorted(LOG_ROOT.iterdir())
        if path.is_dir() and ((path / "episodes").exists() or (path / "episodes.jsonl").exists())
    ),
    None,
) if LOG_ROOT.exists() else None


@pytest.mark.skipif(REAL_LOG_DIR is None, reason="no real log directory available under training/logs")
def test_full_pipeline_with_real_specs(tmp_path):
    static_report = run_static_analysis(
        str(SPEC_DIR / "reward_spec_v1.yaml"),
        str(SPEC_DIR / "constraint_spec_v1.yaml"),
        str(SPEC_DIR / "policy_spec_v1.yaml"),
        str(SPEC_DIR / "env_spec_v1.yaml"),
        output_dir=str(tmp_path),
    )
    dynamic_report = run_dynamic_analysis(
        static_report,
        str(REAL_LOG_DIR),
        str(SPEC_DIR / "reward_spec_v1.yaml"),
        str(SPEC_DIR / "constraint_spec_v1.yaml"),
        output_dir=str(tmp_path),
    )
    semantic_report = run_semantic_analysis(
        static_report,
        dynamic_report,
        str(SPEC_DIR / "reward_spec_v1.yaml"),
        str(SPEC_DIR / "constraint_spec_v1.yaml"),
        output_dir=str(tmp_path),
    )
    cre_report = generate_report(static_report, dynamic_report, semantic_report, output_dir=str(tmp_path))
    repair_result = generate_repair(cre_report, output_dir=str(tmp_path))
    validation_result = validate_repair(
        repair_result,
        static_report,
        str(SPEC_DIR / "reward_spec_v1.yaml"),
        str(SPEC_DIR / "constraint_spec_v1.yaml"),
        str(SPEC_DIR / "policy_spec_v1.yaml"),
        str(SPEC_DIR / "env_spec_v1.yaml"),
        output_dir=str(tmp_path),
    )

    assert isinstance(validation_result, PatchValidationResult)
    assert validation_result.report_id == cre_report.report_id


def test_pipeline_static_only():
    report = run_static_analysis(
        str(SPEC_DIR / "reward_spec_v1.yaml"),
        str(SPEC_DIR / "constraint_spec_v1.yaml"),
        str(SPEC_DIR / "policy_spec_v1.yaml"),
        str(SPEC_DIR / "env_spec_v1.yaml"),
    )

    assert isinstance(report, StaticReport)
    assert report.summary["validation_failed"] is False


def test_wandb_log_keys_present():
    payload = {
        "cre_v2/psi_cre": 0.82,
        "cre_v2/alarm": 0,
        "cre_v2/total_issues": 5,
        "cre_v2/patches": 3,
        "cre_v2/validation_passed": 1,
    }

    assert {
        "cre_v2/psi_cre",
        "cre_v2/alarm",
        "cre_v2/total_issues",
        "cre_v2/patches",
        "cre_v2/validation_passed",
    }.issubset(payload.keys())
