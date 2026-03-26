"""Bridge helpers for connecting the legacy training env to scene-family configs."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from envs.env_gen import (
    FAMILY_TO_SCENE_CFG,
    SceneMode,
    _sample_start_goal_pair,
    compile_scene_config_from_rules,
    load_scene_family_config,
)


def _cfg_get(section: Any, key: str, default: Any) -> Any:
    if section is None:
        return default
    try:
        if key in section:
            return section[key]
    except Exception:
        pass
    return getattr(section, key, default)


def build_scene_family_runtime_profile(
    scene_family_backend: Any,
    *,
    seed: int,
) -> Dict[str, Any]:
    enabled = bool(_cfg_get(scene_family_backend, "enabled", False))
    family_value = str(_cfg_get(scene_family_backend, "family", "nominal"))
    difficulty = float(_cfg_get(scene_family_backend, "difficulty", 0.5))
    gravity_tilt_enabled = bool(_cfg_get(scene_family_backend, "gravity_tilt_enabled", False))

    if not enabled:
        return {
            "enabled": False,
            "family": family_value,
            "difficulty": difficulty,
            "gravity_tilt_enabled": gravity_tilt_enabled,
        }

    family_enum = SceneMode(family_value)
    scene_rules = load_scene_family_config(family_enum)
    compiled = compile_scene_config_from_rules(
        scene_rules,
        seed=seed,
        difficulty=difficulty,
        gravity_tilt_enabled=gravity_tilt_enabled,
    )
    generator_rules = dict(compiled.get("generator_rules", {}))

    return {
        "enabled": True,
        "family": family_enum.value,
        "seed": int(seed),
        "difficulty": difficulty,
        "gravity_tilt_enabled": gravity_tilt_enabled,
        "scene_cfg_name": FAMILY_TO_SCENE_CFG.get(family_enum),
        "scene_id_prefix": str(compiled.get("scene_id", f"{family_enum.value}_{seed:04d}")),
        "scene_rules": scene_rules,
        "compiled_scene_config": compiled,
        "workspace": dict(compiled.get("workspace", {})),
        "start_goal_rules": dict(compiled.get("start_goal_rules", {})),
        "distribution_modes": dict(compiled.get("distribution_modes", {})),
        "validation_rules": dict(compiled.get("validation_rules", {})),
        "generator_rules": generator_rules,
        "dynamic_obstacles_enabled": bool(generator_rules.get("allow_dynamic_obstacles", False)),
    }


def sample_start_goal_from_profile(
    profile: Dict[str, Any],
    *,
    seed: int,
) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    compiled = profile.get("compiled_scene_config") or {}
    if not profile.get("enabled"):
        return tuple(compiled.get("start", (0.0, 0.0, 1.5))), tuple(compiled.get("goal", (0.0, 0.0, 1.5)))

    workspace = dict(profile.get("workspace", {}))
    start_goal_rules = dict(profile.get("start_goal_rules", {}))
    start, goal = _sample_start_goal_pair(workspace, start_goal_rules, int(seed))
    return tuple(start), tuple(goal)


__all__ = [
    "build_scene_family_runtime_profile",
    "sample_start_goal_from_profile",
]
