import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analyzers.spec_ir import load_environment_spec, load_spec_ir
from envs.cre_logging import STANDARD_REWARD_COMPONENT_KEYS


def test_load_environment_spec_includes_all_primary_scene_families():
    environment_spec = load_environment_spec()

    assert set(environment_spec.keys()) == {"nominal", "boundary_critical", "shifted"}
    assert environment_spec["nominal"].scene_cfg_name == "scene_cfg_nominal.yaml"
    assert environment_spec["boundary_critical"].scene_cfg_name == "scene_cfg_boundary_critical.yaml"
    assert environment_spec["shifted"].scene_cfg_name == "scene_cfg_shifted.yaml"


def test_load_spec_ir_builds_structured_v0_bundle():
    spec_ir = load_spec_ir()

    assert spec_ir.spec_version == "v0"
    assert "collision_avoidance" in spec_ir.constraints
    assert spec_ir.constraints["collision_avoidance"].logged_variable == "collision_flag"

    assert spec_ir.reward_spec.reward_total_field == "reward_total"
    assert set(STANDARD_REWARD_COMPONENT_KEYS).issubset(
        set(spec_ir.reward_spec.standard_component_keys)
    )

    assert spec_ir.policy_spec.policy_type == "velocity_command_uav"
    assert spec_ir.policy_spec.action_type == "continuous"
    assert spec_ir.policy_spec.action_bounds == (-2.0, 2.0)

    assert spec_ir.runtime_schema.schema_version == "cre_runtime_log.v1"
    assert "scene_cfg_name" in spec_ir.runtime_schema.step_required_fields
    assert "reward_progress" in spec_ir.runtime_schema.reward_component_keys
    assert "manifest.json" in spec_ir.runtime_schema.execution_mode_artifacts["train"]
    assert spec_ir.runtime_schema.report_namespaces["static_audit"] == "analysis/static"
    assert spec_ir.runtime_schema.report_namespaces["dynamic_analysis"] == "analysis/dynamic"
    assert spec_ir.runtime_schema.report_namespaces["integration_audit"] == "analysis/integration"
    assert "dynamic_report.json" in spec_ir.runtime_schema.report_mode_artifacts["dynamic_analysis"]
    assert "integration_plan.json" in spec_ir.runtime_schema.report_mode_artifacts["integration_audit"]

    assert "near_violation_distance" in spec_ir.detector_thresholds
    assert "constraint_reward" in spec_ir.witness_weights
