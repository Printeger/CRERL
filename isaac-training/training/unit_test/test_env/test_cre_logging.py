import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENVS_PATH = ROOT / "envs"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ENVS_PATH) not in sys.path:
    sys.path.insert(0, str(ENVS_PATH))

from cre_logging import (
    FlightEpisodeLogger,
    SCHEMA_VERSION,
    STANDARD_REWARD_COMPONENT_KEYS,
    _default_logs_dir,
    aggregate_log_directory,
)


def test_default_logs_dir_points_to_training_logs():
    logs_dir = _default_logs_dir()
    assert logs_dir.name == "logs"
    assert logs_dir.parent.name == "training"


def test_episode_logger_writes_complete_artifacts_and_schema(tmp_path):
    logger = FlightEpisodeLogger(
        run_name="unit_test_run",
        base_dir=tmp_path,
        near_violation_distance=0.5,
        use_timestamp=False,
        source="test_flight",
    )
    logger.reset(
        episode_index=0,
        seed=7,
        scene_id="scene_alpha",
        scenario_type="open",
        scene_cfg_name="scene_cfg_nominal.yaml",
        scene_tags={"scene_id": "scene_alpha", "family": "open"},
    )
    logger.log_step(
        step_idx=0,
        sim_time=0.0,
        scene_id="scene_alpha",
        scenario_type="open",
        position=(0.0, 0.0, 1.0),
        velocity=(0.1, 0.0, 0.0),
        yaw_rate=0.2,
        goal_distance=4.0,
        reward_total=1.5,
        reward_components={"progress": 0.8, "safety": 0.7},
        collision_flag=False,
        min_obstacle_distance=0.45,
        out_of_bounds_flag=False,
        done_type="running",
        scene_cfg_name="scene_cfg_nominal.yaml",
    )
    logger.log_step(
        step_idx=1,
        sim_time=0.1,
        scene_id="scene_alpha",
        scenario_type="open",
        position=(0.1, 0.0, 1.0),
        velocity=(0.2, 0.0, 0.0),
        yaw_rate=0.1,
        goal_distance=0.3,
        reward_total=2.0,
        reward_components={"progress": 1.2, "safety": 0.8},
        collision_flag=False,
        min_obstacle_distance=0.6,
        out_of_bounds_flag=False,
        done_type="success",
        scene_cfg_name="scene_cfg_nominal.yaml",
    )
    episode_summary = logger.finalize_episode(done_type="success")

    run_dir = tmp_path / "unit_test_run"
    assert (run_dir / "steps.jsonl").exists()
    assert (run_dir / "episodes.jsonl").exists()
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "episodes" / "episode_0000.json").exists()
    assert episode_summary["scene_id"] == "scene_alpha"
    assert episode_summary["scenario_type"] == "open"
    assert episode_summary["done_type"] == "success"
    assert episode_summary["source"] == "test_flight"
    assert episode_summary["scene_cfg_name"] == "scene_cfg_nominal.yaml"

    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source"] == "test_flight"
    assert manifest["schema_version"] == SCHEMA_VERSION

    step_record = json.loads((run_dir / "steps.jsonl").read_text(encoding="utf-8").splitlines()[0])
    required_fields = {
        "scene_id",
        "scenario_type",
        "position",
        "velocity",
        "yaw_rate",
        "goal_distance",
        "reward_total",
        "reward_components",
        "collision_flag",
        "min_obstacle_distance",
        "near_violation_flag",
        "out_of_bounds_flag",
        "done_type",
        "source",
        "scene_cfg_name",
    }
    assert required_fields.issubset(step_record.keys())
    assert set(STANDARD_REWARD_COMPONENT_KEYS).issubset(step_record["reward_components"].keys())


def test_aggregate_log_directory_computes_acceptance_metrics(tmp_path):
    logger = FlightEpisodeLogger(
        run_name="aggregate_run",
        base_dir=tmp_path,
        near_violation_distance=0.5,
        use_timestamp=False,
    )

    logger.reset(
        episode_index=0,
        seed=1,
        scene_id="scene_success",
        scenario_type="open",
        scene_tags={"scene_id": "scene_success", "family": "open"},
    )
    logger.log_step(
        step_idx=0,
        sim_time=0.0,
        scene_id="scene_success",
        scenario_type="open",
        position=(0.0, 0.0, 1.0),
        velocity=(0.2, 0.0, 0.0),
        yaw_rate=0.0,
        goal_distance=0.2,
        reward_total=3.0,
        reward_components={"progress": 2.0, "safety": 1.0},
        collision_flag=False,
        min_obstacle_distance=0.45,
        out_of_bounds_flag=False,
        done_type="success",
    )
    logger.finalize_episode(done_type="success")

    logger.reset(
        episode_index=1,
        seed=2,
        scene_id="scene_collision",
        scenario_type="dynamic_stress",
        scene_tags={"scene_id": "scene_collision", "family": "dynamic_stress"},
    )
    logger.log_step(
        step_idx=0,
        sim_time=0.0,
        scene_id="scene_collision",
        scenario_type="dynamic_stress",
        position=(1.0, 0.0, 1.0),
        velocity=(0.0, 0.0, 0.0),
        yaw_rate=0.3,
        goal_distance=5.0,
        reward_total=-2.0,
        reward_components={"progress": -1.0, "safety": -1.0},
        collision_flag=True,
        min_obstacle_distance=0.2,
        out_of_bounds_flag=False,
        done_type="collision",
    )
    logger.finalize_episode(done_type="collision")

    summary = aggregate_log_directory(tmp_path / "aggregate_run")
    assert summary["episode_count"] == 2
    assert summary["success_rate"] == 0.5
    assert summary["collision_rate"] == 0.5
    assert summary["min_distance"] == 0.2
    assert summary["average_return"] == 0.5
    assert summary["near_violation_ratio"] == 1.0
