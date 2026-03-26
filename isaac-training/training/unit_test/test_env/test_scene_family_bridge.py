import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from envs.runtime.scene_family_bridge import (
    build_scene_family_runtime_profile,
    sample_start_goal_from_profile,
)


def test_build_scene_family_runtime_profile_uses_family_yaml():
    profile = build_scene_family_runtime_profile(
        {
            "enabled": True,
            "family": "boundary_critical",
            "difficulty": 0.45,
            "gravity_tilt_enabled": False,
        },
        seed=23,
    )

    assert profile["enabled"] is True
    assert profile["family"] == "boundary_critical"
    assert profile["scene_cfg_name"] == "scene_cfg_boundary_critical.yaml"
    assert profile["scene_id_prefix"] == "boundary_critical_v0"
    assert profile["workspace"]["size_x"] == 40.0
    assert profile["dynamic_obstacles_enabled"] is False


def test_sample_start_goal_from_profile_respects_distance_band():
    profile = build_scene_family_runtime_profile(
        {
            "enabled": True,
            "family": "shifted",
            "difficulty": 0.55,
            "gravity_tilt_enabled": False,
        },
        seed=31,
    )

    start, goal = sample_start_goal_from_profile(profile, seed=37)
    distance = math.dist(start, goal)
    rules = profile["start_goal_rules"]

    assert rules["start_goal_distance_min"] <= distance <= rules["start_goal_distance_max"]
    assert profile["workspace"]["flight_height_min"] <= start[2] <= profile["workspace"]["flight_height_max"]
    assert profile["workspace"]["flight_height_min"] <= goal[2] <= profile["workspace"]["flight_height_max"]
