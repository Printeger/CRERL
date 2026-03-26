import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENVS_PATH = ROOT / "envs"
if str(ENVS_PATH) not in sys.path:
    sys.path.insert(0, str(ENVS_PATH))

from env_gen import ArenaConfig, _primitive_color, make_box, make_capsule, make_slab, make_sphere, validate_primitive


def test_make_box_and_validate():
    cfg = ArenaConfig()
    primitive = make_box(
        "box_0001",
        size_x=1.0,
        size_y=0.8,
        size_z=1.2,
        x=0.0,
        y=0.0,
        z=0.6,
    )
    report = validate_primitive(primitive, cfg.to_workspace())
    assert report["valid"] is True
    assert report["errors"] == []


def test_make_capsule_dynamic():
    primitive = make_capsule(
        "capsule_0001",
        radius=0.2,
        segment_length=0.8,
        x=0.0,
        y=0.0,
        z=1.2,
        motion={
            "motion_type": "waypoint_patrol",
            "speed_min": 0.5,
            "speed_max": 1.0,
            "accel_limit": 2.0,
            "turn_rate_limit": 1.0,
            "pause_probability": 0.0,
            "trajectory_params": {"waypoints": [[0, 0, 1.2], [1, 0, 1.2]], "loop": True},
            "seed": 7,
        },
    )
    assert primitive.is_dynamic is True
    assert primitive.motion["motion_type"] == "waypoint_patrol"


def test_primitive_colors_distinguish_base_element_types():
    box = make_box("box_color", 1.0, 0.8, 1.0, 0.0, 0.0, 0.5)
    slab = make_slab("slab_color", 1.5, 1.0, 0.1, 0.0, 0.0, 1.2, slab_mode="horizontal")
    sphere = make_sphere("sphere_color", 0.2, 0.0, 0.0, 1.0)
    capsule = make_capsule(
        "capsule_color",
        radius=0.2,
        segment_length=0.8,
        x=0.0,
        y=0.0,
        z=1.2,
        motion={
            "motion_type": "random_walk",
            "speed_min": 0.5,
            "speed_max": 1.0,
            "accel_limit": 2.0,
            "turn_rate_limit": 1.0,
            "pause_probability": 0.0,
            "trajectory_params": {"heading_resample_interval": 20, "repulsion_gain": 1.0},
            "seed": 7,
        },
    )

    colors = {
        _primitive_color(box),
        _primitive_color(slab),
        _primitive_color(sphere),
        _primitive_color(capsule),
    }
    assert len(colors) == 4
