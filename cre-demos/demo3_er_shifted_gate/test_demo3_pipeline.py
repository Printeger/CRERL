from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


DEMO_ROOT = Path(__file__).resolve().parent
SCRIPT_PATH = DEMO_ROOT / "scripts" / "run_demo3.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("demo3_run_demo3", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_demo3_pipeline_reaches_goal(tmp_path):
    module = _load_module()
    verification = module.run_demo3_pipeline(
        output_root=tmp_path / "reports",
        asset_root=tmp_path / "assets",
        clean_output=True,
    )

    assert verification["goal_achieved"] is True
    assert verification["checks"]["injected_reward_remains_decent_under_shift"]["passed"] is True
    assert verification["checks"]["injected_utility_drops_under_shift"]["passed"] is True
    assert verification["checks"]["injected_elevates_W_ER"]["passed"] is True
    assert verification["checks"]["repair_validation_accepted"]["passed"] is True


def test_demo3_pipeline_is_rerun_safe(tmp_path):
    module = _load_module()
    output_root = tmp_path / "reports"
    asset_root = tmp_path / "assets"

    first_verification = module.run_demo3_pipeline(
        output_root=output_root,
        asset_root=asset_root,
        clean_output=True,
    )
    second_verification = module.run_demo3_pipeline(
        output_root=output_root,
        asset_root=asset_root,
        clean_output=False,
    )

    assert first_verification["goal_achieved"] is True
    assert second_verification["goal_achieved"] is True
    assert second_verification["checks"]["injected_reward_remains_decent_under_shift"]["passed"] is True
    assert second_verification["checks"]["injected_utility_drops_under_shift"]["passed"] is True
    assert second_verification["checks"]["injected_elevates_W_ER"]["passed"] is True
    assert second_verification["checks"]["repair_validation_accepted"]["passed"] is True
