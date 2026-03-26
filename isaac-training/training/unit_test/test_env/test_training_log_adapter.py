import json
import sys
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_logging.logger import create_run_logger
from runtime_logging.training_log_adapter import (
    TrainingRolloutLogger,
    done_type_code_to_string,
    extract_cre_env_metadata,
)


def test_done_type_code_to_string_maps_expected_values():
    assert done_type_code_to_string(0) == "running"
    assert done_type_code_to_string(1) == "success"
    assert done_type_code_to_string(2) == "collision"
    assert done_type_code_to_string(3) == "out_of_bounds"
    assert done_type_code_to_string(4) == "truncated"
    assert done_type_code_to_string(None, collision_flag=True) == "collision"


def test_training_rollout_logger_emits_episode_artifacts(tmp_path):
    run_logger = create_run_logger(
        source="train",
        run_name="adapter_run",
        base_dir=tmp_path,
        use_timestamp=False,
        near_violation_distance=0.5,
    )
    adapter = TrainingRolloutLogger(
        run_logger,
        num_envs=2,
        dt=0.1,
        source="train",
        scenario_type="legacy_navigation_env",
        scene_cfg_name="legacy_train_env",
        scene_id_prefix="legacy_train_scene",
        seed=11,
    )

    drone_state = torch.zeros(1, 2, 1, 13)
    drone_state[0, 0, 0, :3] = torch.tensor([0.0, 0.0, 1.0])
    drone_state[0, 0, 0, 7:10] = torch.tensor([0.1, 0.0, 0.0])
    drone_state[0, 1, 0, :3] = torch.tensor([1.0, 0.0, 1.2])
    drone_state[0, 1, 0, 7:10] = torch.tensor([0.0, 0.0, 0.0])

    batch = {
        "next": {
            "done": torch.tensor([[True, False]], dtype=torch.bool),
            "truncated": torch.tensor([[False, False]], dtype=torch.bool),
            "info": {
                "drone_state": drone_state,
                "goal_distance": torch.tensor([[0.2, 2.0]], dtype=torch.float32),
                "min_obstacle_distance": torch.tensor([[0.6, 0.4]], dtype=torch.float32),
                "near_violation_flag": torch.tensor([[False, True]], dtype=torch.bool),
                "out_of_bounds_flag": torch.tensor([[False, False]], dtype=torch.bool),
                "collision_flag": torch.tensor([[False, False]], dtype=torch.bool),
                "yaw_rate": torch.tensor([[0.1, 0.0]], dtype=torch.float32),
                "reward_total": torch.tensor([[2.0, 0.5]], dtype=torch.float32),
                "reward_progress": torch.tensor([[1.2, 0.2]], dtype=torch.float32),
                "reward_safety_static": torch.tensor([[0.8, 0.3]], dtype=torch.float32),
                "reward_safety_dynamic": torch.tensor([[0.0, 0.0]], dtype=torch.float32),
                "penalty_smooth": torch.tensor([[0.1, 0.0]], dtype=torch.float32),
                "penalty_height": torch.tensor([[0.0, 0.0]], dtype=torch.float32),
                "done_type": torch.tensor([[1.0, 0.0]], dtype=torch.float32),
            },
        }
    }

    records = adapter.process_batch(batch)
    assert len(records) == 2
    adapter.flush_open_episodes(done_type="manual_exit")

    run_dir = tmp_path / "adapter_run"
    episodes_path = run_dir / "episodes.jsonl"
    steps_path = run_dir / "steps.jsonl"
    assert episodes_path.exists()
    assert steps_path.exists()

    episodes = [json.loads(line) for line in episodes_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(episodes) == 2
    assert {episode["done_type"] for episode in episodes} == {"success", "manual_exit"}
    assert all(episode["source"] == "train" for episode in episodes)
    assert all(episode["scene_cfg_name"] == "legacy_train_env" for episode in episodes)
    assert all(episode["scene_id"].startswith("legacy_train_scene_env_") for episode in episodes)

    steps = [json.loads(line) for line in steps_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(steps) == 2
    assert all(step["source"] == "train" for step in steps)
    assert all(step["scene_cfg_name"] == "legacy_train_env" for step in steps)


def test_extract_cre_env_metadata_prefers_env_runtime_metadata():
    class DummyEnv:
        def get_cre_runtime_metadata(self):
            return {
                "scenario_type": "boundary_critical",
                "scene_cfg_name": "scene_cfg_boundary_critical.yaml",
                "scene_id_prefix": "boundary_scene",
                "done_type_labels": {0: "running", 1: "success"},
            }

    metadata = extract_cre_env_metadata(
        DummyEnv(),
        fallback_scenario_type="legacy_navigation_env",
        fallback_scene_cfg_name="legacy_train_env",
        fallback_scene_id_prefix="legacy_scene",
    )

    assert metadata["scenario_type"] == "boundary_critical"
    assert metadata["scene_cfg_name"] == "scene_cfg_boundary_critical.yaml"
    assert metadata["scene_id_prefix"] == "boundary_scene"
    assert metadata["done_type_labels"][1] == "success"
