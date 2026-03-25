import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENVS_PATH = ROOT / "envs"
if str(ENVS_PATH) not in sys.path:
    sys.path.insert(0, str(ENVS_PATH))

from env_gen import (
    ArenaConfig,
    CREScenarioFamily,
    CREScenarioRequest,
    EnvPrimitiveGenerator,
    _build_spawn_obstacles,
    make_box,
    make_capsule,
    scene_from_json,
    scene_to_json,
)


def test_scene_json_round_trip(tmp_path):
    generator = EnvPrimitiveGenerator(ArenaConfig(), seed=5)
    result = generator.generate_from_request(
        CREScenarioRequest(
            family=CREScenarioFamily.OPEN,
            seed=5,
            difficulty=0.3,
        )
    )
    output = tmp_path / "scene.json"
    scene_to_json(result.scene, str(output))
    loaded = scene_from_json(str(output))

    assert loaded["scene_id"] == result.scene["scene_id"]
    assert len(loaded["primitives"]) == len(result.scene["primitives"])


def test_dynamic_motion_update_changes_positions():
    generator = EnvPrimitiveGenerator(ArenaConfig(), seed=17)
    result = generator.generate_from_request(
        CREScenarioRequest(
            family=CREScenarioFamily.DYNAMIC_STRESS,
            seed=17,
            difficulty=0.8,
            dynamic_obstacle_ratio=0.8,
        )
    )
    before = [obstacle.position for obstacle in result.obstacles]
    after = generator.update_dynamic_obstacles(0.2)

    assert len(after) == len(before)
    assert any(a != b for a, b in zip(after, before))


def test_dynamic_motion_avoids_static_collision():
    cfg = ArenaConfig()
    generator = EnvPrimitiveGenerator(cfg, seed=23)
    generator.generate_from_request(
        CREScenarioRequest(
            family=CREScenarioFamily.OPEN,
            seed=23,
            difficulty=0.2,
        )
    )

    static_box = make_box(
        "static_block",
        size_x=2.0,
        size_y=2.0,
        size_z=2.0,
        x=0.0,
        y=0.0,
        z=1.0,
    )
    moving_capsule = make_capsule(
        "moving_capsule",
        radius=0.2,
        segment_length=0.8,
        x=-1.6,
        y=0.0,
        z=1.0,
        axis_mode="horizontal",
        motion={
            "motion_type": "waypoint_patrol",
            "speed_min": 1.0,
            "speed_max": 1.0,
            "accel_limit": 2.0,
            "turn_rate_limit": 1.0,
            "pause_probability": 0.0,
            "trajectory_params": {"waypoints": [[-1.6, 0.0, 1.0], [1.6, 0.0, 1.0]], "loop": True},
            "seed": 9,
        },
    )

    generator._current_primitives = [static_box, moving_capsule]
    generator._current_result.obstacles = _build_spawn_obstacles(generator._current_primitives)
    generator._runtime_state = generator._initialize_runtime_state(generator._current_primitives, cfg.to_workspace(), 23)
    generator._runtime_state[moving_capsule.id]["waypoint_idx"] = 1

    generator.update_dynamic_obstacles(1.0)

    updated = next(primitive for primitive in generator._current_primitives if primitive.id == moving_capsule.id)
    assert updated.pose["x"] <= -1.0
