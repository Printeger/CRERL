"""Bridge helpers for connecting the legacy training env to scene-family configs."""

from __future__ import annotations

import json
from pathlib import Path
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


def _load_repair_preview_payload(repair_context: Any) -> tuple[dict[str, Any], str]:
    if repair_context is None:
        return {}, ""

    if isinstance(repair_context, dict) and str(repair_context.get("preview_type", "")):
        return dict(repair_context), ""

    preview_value = _cfg_get(repair_context, "validation_context_preview", "")
    if isinstance(preview_value, dict) and str(preview_value.get("preview_type", "")):
        return dict(preview_value), ""

    preview_path = str(preview_value or "")
    if not preview_path:
        return {}, ""

    resolved_path = Path(preview_path)
    if not resolved_path.exists():
        return {
            "preview_type": "phase10_missing_validation_context_preview.v1",
            "preview_error": f"missing preview file: {resolved_path}",
        }, preview_path

    try:
        return json.loads(resolved_path.read_text(encoding="utf-8")), str(resolved_path)
    except Exception as exc:
        return {
            "preview_type": "phase10_invalid_validation_context_preview.v1",
            "preview_error": f"{type(exc).__name__}: {exc}",
        }, str(resolved_path)


def _build_repair_preview_binding(repair_context: Any, *, family_value: str) -> Dict[str, Any]:
    preview_payload, preview_path = _load_repair_preview_payload(repair_context)
    file_previews = list(preview_payload.get("file_previews", []) or [])
    scene_family_scope = [str(item) for item in list(preview_payload.get("scene_family_scope", []) or []) if str(item)]
    preferred_execution_modes = [
        str(item)
        for item in list(preview_payload.get("preferred_execution_modes", []) or [])
        if str(item)
    ]
    validation_targets = [
        str(item)
        for item in list(preview_payload.get("validation_targets", []) or [])
        if str(item)
    ]

    target_files = sorted(
        {
            str(item.get("target_file"))
            for item in file_previews
            if str(item.get("target_file", ""))
        }
    )
    target_paths = sorted(
        {
            str(operation.get("target_path"))
            for item in file_previews
            for operation in list(item.get("operations", []) or [])
            if str(operation.get("target_path", ""))
        }
    )
    operation_count = sum(
        int(item.get("operation_count", len(list(item.get("operations", []) or []))))
        for item in file_previews
    )
    family_in_scope = not scene_family_scope or family_value in scene_family_scope
    preview_bound = bool(preview_payload) and family_in_scope and not preview_payload.get("preview_error")

    return {
        "binding_type": "phase10_repair_preview_binding.v1",
        "preview_bound": bool(preview_bound),
        "preview_path": preview_path,
        "preview_type": str(preview_payload.get("preview_type", "")),
        "preview_mode": str(preview_payload.get("preview_mode", "")),
        "preview_error": str(preview_payload.get("preview_error", "")),
        "repair_bundle_name": str(preview_payload.get("repair_bundle_name", "")),
        "phase9_entrypoint": str(preview_payload.get("phase9_entrypoint", "")),
        "scene_family_scope": scene_family_scope,
        "family_in_scope": bool(family_in_scope),
        "preferred_execution_modes": preferred_execution_modes,
        "validation_targets": validation_targets,
        "target_file_count": len(target_files),
        "target_files": target_files,
        "target_paths": target_paths,
        "operation_count": int(operation_count),
        "source_mutation_performed": bool(preview_payload.get("source_mutation_performed", False)),
    }


def _build_effective_scene_binding(
    *,
    enabled: bool,
    family_value: str,
    scene_cfg_name: str,
    scene_id_prefix: str,
    gravity_tilt_enabled: bool,
    dynamic_obstacles_enabled: bool,
    repair_preview_binding: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "binding_type": "phase10_effective_scene_binding.v1",
        "scene_family_backend_enabled": bool(enabled),
        "requested_family": str(family_value),
        "effective_family": str(family_value),
        "scene_cfg_name": str(scene_cfg_name),
        "scene_id_prefix": str(scene_id_prefix),
        "gravity_tilt_enabled": bool(gravity_tilt_enabled),
        "dynamic_obstacles_enabled": bool(dynamic_obstacles_enabled),
        "repair_preview_bound": bool(repair_preview_binding.get("preview_bound", False)),
        "repair_preview_path": str(repair_preview_binding.get("preview_path", "")),
        "repair_preview_type": str(repair_preview_binding.get("preview_type", "")),
        "scene_family_scope": list(repair_preview_binding.get("scene_family_scope", []) or []),
    }


def _build_effective_spec_binding(repair_preview_binding: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "binding_type": "phase10_effective_spec_binding.v1",
        "repair_preview_bound": bool(repair_preview_binding.get("preview_bound", False)),
        "repair_preview_path": str(repair_preview_binding.get("preview_path", "")),
        "repair_preview_type": str(repair_preview_binding.get("preview_type", "")),
        "repair_bundle_name": str(repair_preview_binding.get("repair_bundle_name", "")),
        "phase9_entrypoint": str(repair_preview_binding.get("phase9_entrypoint", "")),
        "target_file_count": int(repair_preview_binding.get("target_file_count", 0)),
        "target_files": list(repair_preview_binding.get("target_files", []) or []),
        "target_paths": list(repair_preview_binding.get("target_paths", []) or []),
        "operation_count": int(repair_preview_binding.get("operation_count", 0)),
        "validation_targets": list(repair_preview_binding.get("validation_targets", []) or []),
        "preferred_execution_modes": list(repair_preview_binding.get("preferred_execution_modes", []) or []),
    }


def build_scene_family_runtime_profile(
    scene_family_backend: Any,
    *,
    seed: int,
    repair_context: Any = None,
) -> Dict[str, Any]:
    enabled = bool(_cfg_get(scene_family_backend, "enabled", False))
    family_value = str(_cfg_get(scene_family_backend, "family", "nominal"))
    difficulty = float(_cfg_get(scene_family_backend, "difficulty", 0.5))
    gravity_tilt_enabled = bool(_cfg_get(scene_family_backend, "gravity_tilt_enabled", False))
    repair_preview_binding = _build_repair_preview_binding(repair_context, family_value=family_value)

    if not enabled:
        effective_scene_binding = _build_effective_scene_binding(
            enabled=False,
            family_value=family_value,
            scene_cfg_name="",
            scene_id_prefix=f"{family_value}_{seed:04d}",
            gravity_tilt_enabled=gravity_tilt_enabled,
            dynamic_obstacles_enabled=False,
            repair_preview_binding=repair_preview_binding,
        )
        return {
            "enabled": False,
            "family": family_value,
            "difficulty": difficulty,
            "gravity_tilt_enabled": gravity_tilt_enabled,
            "repair_preview_binding": repair_preview_binding,
            "effective_scene_binding": effective_scene_binding,
            "effective_spec_binding": _build_effective_spec_binding(repair_preview_binding),
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
    scene_cfg_name = FAMILY_TO_SCENE_CFG.get(family_enum)
    scene_id_prefix = str(compiled.get("scene_id", f"{family_enum.value}_{seed:04d}"))
    effective_scene_binding = _build_effective_scene_binding(
        enabled=True,
        family_value=family_enum.value,
        scene_cfg_name=scene_cfg_name or "",
        scene_id_prefix=scene_id_prefix,
        gravity_tilt_enabled=gravity_tilt_enabled,
        dynamic_obstacles_enabled=bool(generator_rules.get("allow_dynamic_obstacles", False)),
        repair_preview_binding=repair_preview_binding,
    )

    return {
        "enabled": True,
        "family": family_enum.value,
        "seed": int(seed),
        "difficulty": difficulty,
        "gravity_tilt_enabled": gravity_tilt_enabled,
        "scene_cfg_name": scene_cfg_name,
        "scene_id_prefix": scene_id_prefix,
        "scene_rules": scene_rules,
        "compiled_scene_config": compiled,
        "workspace": dict(compiled.get("workspace", {})),
        "start_goal_rules": dict(compiled.get("start_goal_rules", {})),
        "distribution_modes": dict(compiled.get("distribution_modes", {})),
        "validation_rules": dict(compiled.get("validation_rules", {})),
        "generator_rules": generator_rules,
        "dynamic_obstacles_enabled": bool(generator_rules.get("allow_dynamic_obstacles", False)),
        "repair_preview_binding": repair_preview_binding,
        "effective_scene_binding": effective_scene_binding,
        "effective_spec_binding": _build_effective_spec_binding(repair_preview_binding),
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
