import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ENVS_PATH = ROOT / "envs"
if str(ENVS_PATH) not in sys.path:
    sys.path.insert(0, str(ENVS_PATH))

from env_gen import (
    ArenaConfig,
    CREScenarioFamily,
    CREScenarioRequest,
    EnvPrimitiveGenerator,
    SceneMode,
    compile_scene_config_from_rules,
    generate_scene,
    load_scene_family_config,
    make_scene_config_from_request,
)


@pytest.mark.parametrize(
    ("family", "scene_id"),
    [
        (SceneMode.NOMINAL, "nominal_v0"),
        (SceneMode.BOUNDARY_CRITICAL, "boundary_critical_v0"),
        (SceneMode.SHIFTED, "shifted_v0"),
    ],
)
def test_load_scene_family_config_merges_family_yaml(family, scene_id):
    scene_rules = load_scene_family_config(family)

    assert scene_rules["scene_family"] == family.value
    assert scene_rules["scene_id"] == scene_id
    assert scene_rules["workspace"]["size_x"] == 40.0
    assert scene_rules["templates"]["enabled"] is True


def test_boundary_critical_rules_tighten_clearance_and_template_pressure():
    nominal = load_scene_family_config(SceneMode.NOMINAL)
    critical = load_scene_family_config(SceneMode.BOUNDARY_CRITICAL)

    assert critical["templates"]["max_templates_per_scene"] == 2
    assert critical["distribution_modes"]["route_adjacent_bias"] > nominal["distribution_modes"]["route_adjacent_bias"]
    assert critical["start_goal"]["start_clearance_min"] < nominal["start_goal"]["start_clearance_min"]
    assert critical["background_placement"]["free_space_fraction_min"] < nominal["background_placement"]["free_space_fraction_min"]


def test_shifted_rules_change_template_mix_and_primitive_ratio():
    nominal = load_scene_family_config(SceneMode.NOMINAL)
    shifted = load_scene_family_config(SceneMode.SHIFTED)

    assert shifted["primitive_type_ratio"]["static"] != nominal["primitive_type_ratio"]["static"]
    assert set(shifted["templates"]["candidate_types"]) != set(nominal["templates"]["candidate_types"])
    assert shifted["distribution_modes"]["boundary_adjacent_bias"] != nominal["distribution_modes"]["boundary_adjacent_bias"]


@pytest.mark.parametrize(
    ("family", "difficulty"),
    [
        (CREScenarioFamily.NOMINAL, 0.6),
        (CREScenarioFamily.BOUNDARY_CRITICAL, 0.45),
        (CREScenarioFamily.SHIFTED, 0.55),
    ],
)
def test_generate_scene_returns_required_sections_for_mainline_families(family, difficulty):
    cfg = ArenaConfig()
    request = CREScenarioRequest(
        family=family,
        seed=11,
        difficulty=difficulty,
    )
    scene_config = make_scene_config_from_request(request, cfg)
    scene = generate_scene(scene_config)

    assert "metadata" in scene
    assert "validation_report" in scene
    assert "primitives" in scene
    assert scene["scene_mode"] == family.value
    assert scene["scene_family"] == family.value
    assert len(scene["template_log"]) >= 1
    assert scene["validation_report"]["valid"] is True


@pytest.mark.parametrize(
    ("family", "difficulty", "distance_lo", "distance_hi"),
    [
        (SceneMode.NOMINAL, 0.5, 8.0, 16.0),
        (SceneMode.BOUNDARY_CRITICAL, 0.4, 8.0, 14.0),
        (SceneMode.SHIFTED, 0.5, 8.0, 16.0),
    ],
)
def test_family_scene_uses_rules_and_start_goal_validation(family, difficulty, distance_lo, distance_hi):
    scene_rules = load_scene_family_config(family)
    scene_config = compile_scene_config_from_rules(scene_rules, seed=19, difficulty=difficulty, gravity_tilt_enabled=False)
    scene = generate_scene(scene_config)

    assert scene["workspace"]["size_x"] == 40.0
    assert scene["workspace"]["size_y"] == 40.0
    assert scene["workspace"]["size_z"] == 4.5
    assert scene["scene_mode"] == family.value
    assert scene["validation_report"]["template_presence_valid"] is True
    assert scene["validation_report"]["start_goal_valid"] is True
    assert scene["validation_report"]["start_goal_distance"] >= distance_lo
    assert scene["validation_report"]["start_goal_distance"] <= distance_hi
    assert scene["metadata"].get("retry_exhausted", False) is False


@pytest.mark.parametrize(
    ("family", "difficulty"),
    [
        (CREScenarioFamily.NOMINAL, 0.7),
        (CREScenarioFamily.BOUNDARY_CRITICAL, 0.45),
        (CREScenarioFamily.SHIFTED, 0.55),
    ],
)
def test_generator_request_flow_and_summary_uses_mainline_family(family, difficulty):
    generator = EnvPrimitiveGenerator(ArenaConfig(), seed=3)
    request = CREScenarioRequest(
        family=family,
        seed=3,
        difficulty=difficulty,
    )
    result = generator.generate_from_request(request)
    summary = generator.summarize_result(result)

    assert result.cre_metadata.family == family.value
    assert summary["mode"] == family.value
    assert len(result.obstacles) >= 1


def test_mixed_scene_spreads_static_primitives_across_workspace_quadrants():
    cfg = ArenaConfig()
    request = CREScenarioRequest(
        family=CREScenarioFamily.MIXED,
        seed=29,
        difficulty=0.55,
        dynamic_obstacle_ratio=0.6,
    )
    scene = generate_scene(make_scene_config_from_request(request, cfg))

    quadrants = set()
    for primitive in scene["primitives"]:
        if primitive["is_dynamic"]:
            continue
        x = primitive["pose"]["x"]
        y = primitive["pose"]["y"]
        quadrants.add(("L" if x < 0 else "R", "B" if y < 0 else "T"))

    assert len(quadrants) == 4
