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
    generate_scene,
    make_scene_config_from_request,
)


def test_generate_scene_returns_required_sections():
    cfg = ArenaConfig()
    request = CREScenarioRequest(
        family=CREScenarioFamily.NARROW_CORRIDOR,
        seed=11,
        difficulty=0.6,
        corridor_width=1.2,
    )
    scene_config = make_scene_config_from_request(request, cfg)
    scene = generate_scene(scene_config)

    assert "metadata" in scene
    assert "validation_report" in scene
    assert "primitives" in scene
    assert scene["scene_mode"] == CREScenarioFamily.NARROW_CORRIDOR.value
    assert scene["validation_report"]["valid"] is True


def test_open_scene_uses_navrl_calibrated_workspace_and_density_rules():
    cfg = ArenaConfig()
    request = CREScenarioRequest(
        family=CREScenarioFamily.OPEN,
        seed=19,
        difficulty=0.5,
    )
    scene_config = make_scene_config_from_request(request, cfg)
    scene = generate_scene(scene_config)

    assert scene["workspace"]["size_x"] == 40.0
    assert scene["workspace"]["size_y"] == 40.0
    assert scene["workspace"]["size_z"] == 4.5
    assert scene_config["generator_rules"]["target_occupancy_range"] == (0.010, 0.040)
    assert scene["metadata"]["static_occupancy"] >= scene_config["generator_rules"]["target_occupancy_range"][0]
    assert scene["metadata"].get("retry_exhausted", False) is False


def test_generator_request_flow_and_summary():
    generator = EnvPrimitiveGenerator(ArenaConfig(), seed=3)
    request = CREScenarioRequest(
        family=CREScenarioFamily.DYNAMIC_STRESS,
        seed=3,
        difficulty=0.7,
        dynamic_obstacle_ratio=0.8,
    )
    result = generator.generate_from_request(request)
    summary = generator.summarize_result(result)

    assert result.cre_metadata.family == "dynamic_stress"
    assert summary["dynamic_obstacle_count"] >= 1
    assert len(result.obstacles) >= summary["dynamic_obstacle_count"]
