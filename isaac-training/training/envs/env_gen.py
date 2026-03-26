"""
Spec-aligned environment primitive generator for CRE Phase 1.

This module implements a pure-Python obstacle scene generator based on
`doc/specs/Env_Primitive_Spec_v0.md` and also exposes a thin runtime adapter
for the existing Isaac flight visualization harness.
"""

from __future__ import annotations

import copy
import json
import math
import random
import ast
from collections import deque
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal Isaac/Hydra envs
    class _YamlCompat:
        @staticmethod
        def _strip_comment(line: str) -> str:
            return line.split("#", 1)[0].rstrip()

        @staticmethod
        def _parse_scalar(value: str):
            lowered = value.lower()
            if lowered in {"true", "false"}:
                return lowered == "true"
            if lowered in {"null", "none", "~"}:
                return None
            if value.startswith(("'", '"')) and value.endswith(("'", '"')):
                return value[1:-1]
            if value.startswith(("[", "{", "(", "-")) or value[:1].isdigit():
                try:
                    normalized = (
                        value.replace("true", "True")
                        .replace("false", "False")
                        .replace("null", "None")
                    )
                    return ast.literal_eval(normalized)
                except Exception:
                    pass
            try:
                if "." in value or "e" in lowered:
                    return float(value)
                return int(value)
            except Exception:
                return value

        @classmethod
        def _parse_block(cls, lines, start_idx: int, indent: int):
            if start_idx >= len(lines):
                return {}, start_idx

            line_indent, content = lines[start_idx]
            if content.startswith("- "):
                items = []
                idx = start_idx
                while idx < len(lines):
                    current_indent, current = lines[idx]
                    if current_indent < indent or not current.startswith("- "):
                        break
                    if current_indent != indent:
                        break
                    payload = current[2:].strip()
                    idx += 1
                    if payload == "":
                        child, idx = cls._parse_block(lines, idx, indent + 2)
                        items.append(child)
                    else:
                        items.append(cls._parse_scalar(payload))
                return items, idx

            mapping = {}
            idx = start_idx
            while idx < len(lines):
                current_indent, current = lines[idx]
                if current_indent < indent:
                    break
                if current_indent != indent:
                    break
                key, sep, raw_value = current.partition(":")
                if not sep:
                    raise ValueError(f"Invalid YAML line: {current}")
                key = key.strip()
                value = raw_value.strip()
                idx += 1
                if value == "":
                    if idx < len(lines) and lines[idx][0] > current_indent:
                        child, idx = cls._parse_block(lines, idx, current_indent + 2)
                        mapping[key] = child
                    else:
                        mapping[key] = {}
                else:
                    mapping[key] = cls._parse_scalar(value)
            return mapping, idx

        @classmethod
        def safe_load(cls, text):
            lines = []
            for raw_line in text.splitlines():
                stripped = cls._strip_comment(raw_line)
                if not stripped.strip():
                    continue
                indent = len(stripped) - len(stripped.lstrip(" "))
                lines.append((indent, stripped.lstrip(" ")))
            if not lines:
                return {}
            parsed, _ = cls._parse_block(lines, 0, lines[0][0])
            return parsed

    yaml = _YamlCompat()


ALLOWED_PRIMITIVE_TYPES = {
    "box",
    "cylinder",
    "slab",
    "perforated_slab",
    "sphere",
    "capsule",
}

ALLOWED_SUPPORT_MODES = {
    "grounded",
    "ceiling_attached",
    "floating",
    "wall_attached",
    "free_moving",
}

ALLOWED_SEMANTIC_ROLES = {
    "barrier",
    "pillar",
    "clutter",
    "bottleneck_boundary",
    "overhead_hazard",
    "moving_agent",
    "moving_disturbance",
    "passable_panel",
    "navigation_gate",
    "occluder",
}

ALLOWED_MOTION_TYPES = {"waypoint_patrol", "random_walk", "lane_patrol"}


class SceneMode(Enum):
    NOMINAL = "nominal"
    BOUNDARY_CRITICAL = "boundary_critical"
    SHIFTED = "shifted"
    OPEN = "open"
    NARROW_CORRIDOR = "narrow_corridor"
    VERTICAL_CONSTRAINT = "vertical_constraint"
    DYNAMIC_STRESS = "dynamic_stress"
    MIXED = "mixed"


CREScenarioFamily = SceneMode
ArenaMode = SceneMode


@dataclass
class ArenaConfig:
    size_x: float = 40.0
    size_y: float = 40.0
    size_z: float = 4.5
    drone_radius: float = 0.25
    drone_height: float = 0.15
    start_pos: Tuple[float, float, float] = (-16.0, 0.0, 1.5)
    goal_pos: Tuple[float, float, float] = (16.0, 0.0, 1.5)
    flight_height_min: float = 0.5
    flight_height_max: float = 2.5
    max_tilt_angle: float = 20.0

    def to_workspace(self) -> Dict[str, float]:
        return {
            "size_x": self.size_x,
            "size_y": self.size_y,
            "size_z": self.size_z,
            "flight_height_min": self.flight_height_min,
            "flight_height_max": self.flight_height_max,
        }


@dataclass
class CREScenarioRequest:
    family: CREScenarioFamily
    seed: Optional[int] = None
    difficulty: float = 0.5
    corridor_width: Optional[float] = None
    obstacle_density: Optional[float] = None
    dynamic_obstacle_ratio: float = 0.0
    gravity_tilt_enabled: bool = True
    sub_mode: Optional[str] = None
    preferred_mode: Optional[str] = None


SCENE_CFG_DIR = Path(__file__).resolve().parents[1] / "cfg" / "env_cfg"
FAMILY_TO_SCENE_CFG = {
    SceneMode.NOMINAL: "scene_cfg_nominal.yaml",
    SceneMode.BOUNDARY_CRITICAL: "scene_cfg_boundary_critical.yaml",
    SceneMode.SHIFTED: "scene_cfg_shifted.yaml",
}


@dataclass
class PrimitiveSpec:
    id: str
    type: str
    semantic_role: str
    geometry: Dict[str, Any]
    pose: Dict[str, float]
    orientation: Dict[str, float]
    support_mode: str
    is_dynamic: bool
    motion: Optional[Dict[str, Any]]
    perforation: Optional[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CREScenarioMetadata:
    family: str
    seed: Optional[int]
    requested_difficulty: float
    realized_mode: str
    realized_sub_mode: Optional[str]
    scene_tags: Dict[str, Any]
    estimated_min_gap: Optional[float]
    obstacle_count: int
    static_obstacle_count: int
    dynamic_obstacle_count: int
    requires_vertical_flight: bool
    gravity_tilt_enabled: bool
    solvable: bool
    complexity: float


@dataclass
class SceneLabels:
    local_start: Tuple[float, float, float]
    local_goal: Tuple[float, float, float]
    requires_vertical_flight: bool
    gravity_tilt: Tuple[float, float]


@dataclass
class SpawnObstacle:
    prim_type: str
    position: Tuple[float, float, float]
    scale: Tuple[float, float, float]
    rotation: Tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)
    color: Tuple[float, float, float] = (0.5, 0.5, 0.5)
    is_dynamic: bool = False
    motion_type: str = "static"
    motion_params: Dict[str, Any] = field(default_factory=dict)
    is_hazard: bool = False
    source_primitive_id: Optional[str] = None


@dataclass
class GeneratedSceneResult:
    scene: Dict[str, Any]
    mode: SceneMode
    sub_mode: Optional[str]
    difficulty: float
    obstacles: List[SpawnObstacle]
    labels: SceneLabels
    gravity_tilt_quat: Tuple[float, float, float, float]
    gravity_tilt_euler: Tuple[float, float]
    solvable: bool
    complexity: float
    cre_metadata: CREScenarioMetadata


def _identity_orientation() -> Dict[str, float]:
    return {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}


def _normalize_pose(x: float, y: float, z: float) -> Dict[str, float]:
    return {"x": float(x), "y": float(y), "z": float(z)}


def _validate_positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def _make_primitive(
    primitive_id: str,
    primitive_type: str,
    semantic_role: str,
    geometry: Dict[str, Any],
    pose: Dict[str, float],
    orientation: Optional[Dict[str, float]] = None,
    support_mode: str = "grounded",
    is_dynamic: bool = False,
    motion: Optional[Dict[str, Any]] = None,
    perforation: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> PrimitiveSpec:
    if primitive_type not in ALLOWED_PRIMITIVE_TYPES:
        raise ValueError(f"Unsupported primitive type: {primitive_type}")
    if support_mode not in ALLOWED_SUPPORT_MODES:
        raise ValueError(f"Unsupported support mode: {support_mode}")
    if semantic_role not in ALLOWED_SEMANTIC_ROLES:
        raise ValueError(f"Unsupported semantic role: {semantic_role}")
    return PrimitiveSpec(
        id=primitive_id,
        type=primitive_type,
        semantic_role=semantic_role,
        geometry=dict(geometry),
        pose=dict(pose),
        orientation=dict(orientation or _identity_orientation()),
        support_mode=support_mode,
        is_dynamic=is_dynamic,
        motion=None if motion is None else dict(motion),
        perforation=None if perforation is None else dict(perforation),
        metadata=dict(metadata or {}),
    )


def make_box(
    primitive_id: str,
    size_x: float,
    size_y: float,
    size_z: float,
    x: float,
    y: float,
    z: float,
    yaw: float = 0.0,
    support_mode: str = "grounded",
    semantic_role: str = "barrier",
) -> PrimitiveSpec:
    _validate_positive("size_x", size_x)
    _validate_positive("size_y", size_y)
    _validate_positive("size_z", size_z)
    return _make_primitive(
        primitive_id=primitive_id,
        primitive_type="box",
        semantic_role=semantic_role,
        geometry={"size_x": size_x, "size_y": size_y, "size_z": size_z},
        pose=_normalize_pose(x, y, z),
        orientation={"roll": 0.0, "pitch": 0.0, "yaw": yaw},
        support_mode=support_mode,
    )


def make_cylinder(
    primitive_id: str,
    radius: float,
    height: float,
    x: float,
    y: float,
    z: float,
    axis_mode: str = "vertical",
    yaw: float = 0.0,
    support_mode: str = "grounded",
    semantic_role: str = "pillar",
) -> PrimitiveSpec:
    _validate_positive("radius", radius)
    _validate_positive("height", height)
    if axis_mode not in {"vertical", "horizontal"}:
        raise ValueError(f"Unsupported axis_mode: {axis_mode}")
    return _make_primitive(
        primitive_id=primitive_id,
        primitive_type="cylinder",
        semantic_role=semantic_role,
        geometry={"radius": radius, "height": height, "axis_mode": axis_mode},
        pose=_normalize_pose(x, y, z),
        orientation={"roll": 0.0, "pitch": 0.0, "yaw": yaw},
        support_mode=support_mode,
    )


def make_slab(
    primitive_id: str,
    size_x: float,
    size_y: float,
    thickness: float,
    x: float,
    y: float,
    z: float,
    slab_mode: str,
    yaw: float = 0.0,
    support_mode: str = "grounded",
    semantic_role: str = "barrier",
) -> PrimitiveSpec:
    _validate_positive("size_x", size_x)
    _validate_positive("size_y", size_y)
    _validate_positive("thickness", thickness)
    if slab_mode not in {"vertical", "horizontal"}:
        raise ValueError(f"Unsupported slab_mode: {slab_mode}")
    return _make_primitive(
        primitive_id=primitive_id,
        primitive_type="slab",
        semantic_role=semantic_role,
        geometry={
            "size_x": size_x,
            "size_y": size_y,
            "thickness": thickness,
            "slab_mode": slab_mode,
        },
        pose=_normalize_pose(x, y, z),
        orientation={"roll": 0.0, "pitch": 0.0, "yaw": yaw},
        support_mode=support_mode,
    )


def make_perforated_slab(
    primitive_id: str,
    size_x: float,
    size_y: float,
    thickness: float,
    x: float,
    y: float,
    z: float,
    slab_mode: str,
    holes: List[Dict[str, Any]],
    edge_margin_min: float,
    hole_spacing_min: float,
    yaw: float = 0.0,
    support_mode: str = "grounded",
    semantic_role: str = "passable_panel",
) -> PrimitiveSpec:
    _validate_positive("size_x", size_x)
    _validate_positive("size_y", size_y)
    _validate_positive("thickness", thickness)
    _validate_positive("edge_margin_min", edge_margin_min)
    if hole_spacing_min < 0:
        raise ValueError("hole_spacing_min must be non-negative")
    if slab_mode not in {"vertical", "horizontal"}:
        raise ValueError(f"Unsupported slab_mode: {slab_mode}")
    perforation = {
        "enabled": True,
        "hole_count": len(holes),
        "hole_shape": holes[0]["shape"] if holes else None,
        "holes": [dict(hole) for hole in holes],
        "edge_margin_min": edge_margin_min,
        "hole_spacing_min": hole_spacing_min,
    }
    return _make_primitive(
        primitive_id=primitive_id,
        primitive_type="perforated_slab",
        semantic_role=semantic_role,
        geometry={
            "size_x": size_x,
            "size_y": size_y,
            "thickness": thickness,
            "slab_mode": slab_mode,
        },
        pose=_normalize_pose(x, y, z),
        orientation={"roll": 0.0, "pitch": 0.0, "yaw": yaw},
        support_mode=support_mode,
        perforation=perforation,
    )


def make_sphere(
    primitive_id: str,
    radius: float,
    x: float,
    y: float,
    z: float,
    support_mode: str = "free_moving",
    semantic_role: str = "moving_disturbance",
    motion: Optional[Dict[str, Any]] = None,
) -> PrimitiveSpec:
    _validate_positive("radius", radius)
    return _make_primitive(
        primitive_id=primitive_id,
        primitive_type="sphere",
        semantic_role=semantic_role,
        geometry={"radius": radius},
        pose=_normalize_pose(x, y, z),
        support_mode=support_mode,
        is_dynamic=True,
        motion=motion,
    )


def make_capsule(
    primitive_id: str,
    radius: float,
    segment_length: float,
    x: float,
    y: float,
    z: float,
    axis_mode: str = "velocity_aligned",
    support_mode: str = "free_moving",
    semantic_role: str = "moving_agent",
    motion: Optional[Dict[str, Any]] = None,
) -> PrimitiveSpec:
    _validate_positive("radius", radius)
    _validate_positive("segment_length", segment_length)
    if axis_mode not in {"velocity_aligned", "vertical", "horizontal"}:
        raise ValueError(f"Unsupported axis_mode: {axis_mode}")
    return _make_primitive(
        primitive_id=primitive_id,
        primitive_type="capsule",
        semantic_role=semantic_role,
        geometry={
            "radius": radius,
            "segment_length": segment_length,
            "axis_mode": axis_mode,
        },
        pose=_normalize_pose(x, y, z),
        support_mode=support_mode,
        is_dynamic=True,
        motion=motion,
    )


def _primitive_from_dict(data: Dict[str, Any]) -> PrimitiveSpec:
    return PrimitiveSpec(
        id=data["id"],
        type=data["type"],
        semantic_role=data["semantic_role"],
        geometry=dict(data["geometry"]),
        pose=dict(data["pose"]),
        orientation=dict(data["orientation"]),
        support_mode=data["support_mode"],
        is_dynamic=bool(data["is_dynamic"]),
        motion=None if data.get("motion") is None else dict(data["motion"]),
        perforation=None if data.get("perforation") is None else dict(data["perforation"]),
        metadata=dict(data.get("metadata", {})),
    )


def _primitive_to_dict(primitive: PrimitiveSpec) -> Dict[str, Any]:
    return asdict(primitive)


def _aabb_half_extents(primitive: PrimitiveSpec) -> Tuple[float, float, float]:
    g = primitive.geometry
    if primitive.type == "box":
        return g["size_x"] / 2.0, g["size_y"] / 2.0, g["size_z"] / 2.0
    if primitive.type == "cylinder":
        if g.get("axis_mode", "vertical") == "vertical":
            return g["radius"], g["radius"], g["height"] / 2.0
        return g["height"] / 2.0, g["radius"], g["radius"]
    if primitive.type in {"slab", "perforated_slab"}:
        if g["slab_mode"] == "horizontal":
            return g["size_x"] / 2.0, g["size_y"] / 2.0, g["thickness"] / 2.0
        return g["size_x"] / 2.0, g["thickness"] / 2.0, g["size_y"] / 2.0
    if primitive.type == "sphere":
        return g["radius"], g["radius"], g["radius"]
    if primitive.type == "capsule":
        radius = g["radius"]
        segment = g["segment_length"]
        axis_mode = g.get("axis_mode", "velocity_aligned")
        if axis_mode == "vertical":
            return radius, radius, segment / 2.0 + radius
        return segment / 2.0 + radius, radius, radius
    raise ValueError(f"Unsupported primitive type: {primitive.type}")


def _aabb_bounds(primitive: PrimitiveSpec) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    hx, hy, hz = _aabb_half_extents(primitive)
    px, py, pz = primitive.pose["x"], primitive.pose["y"], primitive.pose["z"]
    return (px - hx, py - hy, pz - hz), (px + hx, py + hy, pz + hz)


def _intersects(a: PrimitiveSpec, b: PrimitiveSpec, tolerance: float = 0.0) -> bool:
    (amin, amax) = _aabb_bounds(a)
    (bmin, bmax) = _aabb_bounds(b)
    return (
        amin[0] < bmax[0] - tolerance and amax[0] > bmin[0] + tolerance and
        amin[1] < bmax[1] - tolerance and amax[1] > bmin[1] + tolerance and
        amin[2] < bmax[2] - tolerance and amax[2] > bmin[2] + tolerance
    )


def _intersects_with_margin(
    a: PrimitiveSpec,
    b: PrimitiveSpec,
    margin_xy: float = 0.2,
    margin_z: float = 0.05,
) -> bool:
    (amin, amax) = _aabb_bounds(a)
    (bmin, bmax) = _aabb_bounds(b)
    return (
        amin[0] - margin_xy < bmax[0] and amax[0] + margin_xy > bmin[0] and
        amin[1] - margin_xy < bmax[1] and amax[1] + margin_xy > bmin[1] and
        amin[2] - margin_z < bmax[2] and amax[2] + margin_z > bmin[2]
    )


def _distance_to_point_xy(primitive: PrimitiveSpec, point: Tuple[float, float, float]) -> float:
    px, py = primitive.pose["x"], primitive.pose["y"]
    return math.sqrt((px - point[0]) ** 2 + (py - point[1]) ** 2)


def _sample_navrl_height(rng: random.Random, workspace: Dict[str, float]) -> float:
    candidates = [1.0, 1.5, 2.0, min(4.0, workspace["size_z"] - 0.2)]
    weights = [0.15, 0.20, 0.25, 0.40]
    return rng.choices(candidates, weights=weights, k=1)[0]


def _is_candidate_valid(
    candidate: PrimitiveSpec,
    existing: Sequence[PrimitiveSpec],
    workspace: Dict[str, Any],
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
    clearance_xy: float = 0.35,
) -> bool:
    if not validate_primitive(candidate, workspace)["valid"]:
        return False
    if _distance_to_point_xy(candidate, start) < 1.5:
        return False
    if _distance_to_point_xy(candidate, goal) < 1.5:
        return False
    for other in existing:
        if _intersects_with_margin(candidate, other, margin_xy=clearance_xy, margin_z=0.05):
            return False
    return True


def _try_place_primitive(
    make_candidate,
    existing: Sequence[PrimitiveSpec],
    workspace: Dict[str, Any],
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
    attempts: int = 50,
):
    for _ in range(attempts):
        candidate = make_candidate()
        if _is_candidate_valid(candidate, existing, workspace, start, goal):
            return candidate
    return None


def _approx_static_occupancy(primitives: Sequence[PrimitiveSpec], workspace: Dict[str, Any]) -> float:
    area = max(workspace["size_x"] * workspace["size_y"], 1.0)
    occupied = 0.0
    for primitive in primitives:
        if primitive.is_dynamic:
            continue
        hx, hy, _ = _aabb_half_extents(primitive)
        occupied += max(0.0, 2.0 * hx) * max(0.0, 2.0 * hy)
    return min(1.0, occupied / area)


def _lane_is_clear(
    y: float,
    z: float,
    x_min: float,
    x_max: float,
    static_primitives: Sequence[PrimitiveSpec],
    lane_half_width: float = 0.6,
) -> bool:
    for primitive in static_primitives:
        mn, mx = _aabb_bounds(primitive)
        if mx[0] < x_min or mn[0] > x_max:
            continue
        if z < mn[2] - 0.1 or z > mx[2] + 0.1:
            continue
        if (mn[1] - lane_half_width) <= y <= (mx[1] + lane_half_width):
            return False
    return True


def _candidate_pose_intersects(
    primitive: PrimitiveSpec,
    candidate_pose: Tuple[float, float, float],
    others: Sequence[PrimitiveSpec],
    margin_xy: float = 0.15,
    margin_z: float = 0.05,
) -> bool:
    moved = PrimitiveSpec(
        id=primitive.id,
        type=primitive.type,
        semantic_role=primitive.semantic_role,
        geometry=dict(primitive.geometry),
        pose=_normalize_pose(*candidate_pose),
        orientation=dict(primitive.orientation),
        support_mode=primitive.support_mode,
        is_dynamic=primitive.is_dynamic,
        motion=None if primitive.motion is None else dict(primitive.motion),
        perforation=None if primitive.perforation is None else dict(primitive.perforation),
        metadata=dict(primitive.metadata),
    )
    return any(_intersects_with_margin(moved, other, margin_xy=margin_xy, margin_z=margin_z) for other in others)


def _validate_motion(motion: Optional[Dict[str, Any]]) -> List[str]:
    errors: List[str] = []
    if motion is None:
        return errors
    motion_type = motion.get("motion_type")
    if motion_type not in ALLOWED_MOTION_TYPES:
        errors.append(f"unsupported motion_type: {motion_type}")
    for field_name in ["speed_min", "speed_max", "accel_limit", "turn_rate_limit"]:
        if field_name not in motion:
            errors.append(f"missing motion field: {field_name}")
    if motion.get("speed_min", 0.0) > motion.get("speed_max", 0.0):
        errors.append("speed_min cannot exceed speed_max")
    return errors


def _validate_perforation(primitive: PrimitiveSpec) -> List[str]:
    errors: List[str] = []
    if primitive.perforation is None:
        return errors

    g = primitive.geometry
    perforation = primitive.perforation
    holes = perforation.get("holes", [])
    edge_margin = perforation.get("edge_margin_min", 0.0)
    spacing_min = perforation.get("hole_spacing_min", 0.0)
    width = g["size_x"]
    height = g["size_y"]

    bounding_boxes: List[Tuple[float, float, float, float]] = []
    for hole in holes:
        shape = hole.get("shape")
        if shape == "circle":
            radius = hole.get("radius", -1.0)
            if radius <= 0:
                errors.append("circle hole radius must be positive")
                continue
            min_u = hole["center_u"] - radius
            max_u = hole["center_u"] + radius
            min_v = hole["center_v"] - radius
            max_v = hole["center_v"] + radius
        elif shape == "rectangle":
            hole_w = hole.get("width", -1.0)
            hole_h = hole.get("height", -1.0)
            if hole_w <= 0 or hole_h <= 0:
                errors.append("rectangle hole dimensions must be positive")
                continue
            min_u = hole["center_u"] - hole_w / 2.0
            max_u = hole["center_u"] + hole_w / 2.0
            min_v = hole["center_v"] - hole_h / 2.0
            max_v = hole["center_v"] + hole_h / 2.0
        else:
            errors.append(f"unsupported hole shape: {shape}")
            continue

        if min_u < -width / 2.0 + edge_margin or max_u > width / 2.0 - edge_margin:
            errors.append("hole violates edge_margin_min on u-axis")
        if min_v < -height / 2.0 + edge_margin or max_v > height / 2.0 - edge_margin:
            errors.append("hole violates edge_margin_min on v-axis")

        bounding_boxes.append((min_u, max_u, min_v, max_v))

    for i in range(len(bounding_boxes)):
        for j in range(i + 1, len(bounding_boxes)):
            a = bounding_boxes[i]
            b = bounding_boxes[j]
            overlap_u = min(a[1], b[1]) - max(a[0], b[0])
            overlap_v = min(a[3], b[3]) - max(a[2], b[2])
            if overlap_u > -spacing_min and overlap_v > -spacing_min:
                errors.append("holes overlap or violate hole_spacing_min")
    return errors


def _point_to_aabb_distance(point: Tuple[float, float, float], primitive: PrimitiveSpec) -> float:
    (mn, mx) = _aabb_bounds(primitive)
    dx = max(mn[0] - point[0], 0.0, point[0] - mx[0])
    dy = max(mn[1] - point[1], 0.0, point[1] - mx[1])
    dz = max(mn[2] - point[2], 0.0, point[2] - mx[2])
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _validate_required_template_presence(scene: Dict[str, Any]) -> Tuple[bool, List[str]]:
    validation_rules = dict(scene.get("validation_rules", {}))
    if not validation_rules.get("require_template_presence", False):
        return True, []
    templates = list(scene.get("templates", []))
    template_logs = list(scene.get("template_log", []))
    if not templates:
        return False, ["scene requires at least one template but none were configured"]
    realized = [log for log in template_logs if not log.get("skipped", False)]
    if not realized:
        return False, ["scene requires at least one realized template but all template placements were skipped"]
    return True, []


def _validate_start_goal(scene: Dict[str, Any], primitives: Sequence[PrimitiveSpec]) -> Dict[str, Any]:
    start_goal_rules = dict(scene.get("start_goal_rules", {}))
    workspace = scene["workspace"]
    start = tuple(scene["start"])
    goal = tuple(scene["goal"])
    errors: List[str] = []

    def inside_workspace(point: Tuple[float, float, float]) -> bool:
        return (
            -workspace["size_x"] / 2.0 <= point[0] <= workspace["size_x"] / 2.0 and
            -workspace["size_y"] / 2.0 <= point[1] <= workspace["size_y"] / 2.0 and
            0.0 <= point[2] <= workspace["size_z"]
        )

    if not inside_workspace(start):
        errors.append("start lies outside workspace bounds")
    if not inside_workspace(goal):
        errors.append("goal lies outside workspace bounds")

    start_goal_distance = math.dist(start, goal)
    d_min = float(start_goal_rules.get("start_goal_distance_min", 0.0))
    d_max = float(start_goal_rules.get("start_goal_distance_max", float("inf")))
    if start_goal_distance < d_min:
        errors.append(f"start-goal distance {start_goal_distance:.2f} is below minimum {d_min:.2f}")
    if start_goal_distance > d_max:
        errors.append(f"start-goal distance {start_goal_distance:.2f} exceeds maximum {d_max:.2f}")

    if primitives:
        start_clearance = min(_point_to_aabb_distance(start, primitive) for primitive in primitives)
        goal_clearance = min(_point_to_aabb_distance(goal, primitive) for primitive in primitives)
    else:
        start_clearance = float("inf")
        goal_clearance = float("inf")

    start_clearance_min = float(start_goal_rules.get("start_clearance_min", 0.0))
    if start_clearance < start_clearance_min:
        errors.append(f"start clearance {start_clearance:.2f} is below minimum {start_clearance_min:.2f}")

    goal_clearance_min = float(start_goal_rules.get("goal_clearance_min", 0.0))
    if goal_clearance < goal_clearance_min:
        errors.append(f"goal clearance {goal_clearance:.2f} is below minimum {goal_clearance_min:.2f}")

    goal_boundary_clearance = min(
        workspace["size_x"] / 2.0 - abs(goal[0]),
        workspace["size_y"] / 2.0 - abs(goal[1]),
        goal[2],
        workspace["size_z"] - goal[2],
    )
    goal_boundary_clearance_min = float(start_goal_rules.get("goal_boundary_clearance_min", 0.0))
    if goal_boundary_clearance < goal_boundary_clearance_min:
        errors.append(
            f"goal boundary clearance {goal_boundary_clearance:.2f} is below minimum "
            f"{goal_boundary_clearance_min:.2f}"
        )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "start_goal_distance": start_goal_distance,
        "start_clearance": start_clearance,
        "goal_clearance": goal_clearance,
        "goal_boundary_clearance": goal_boundary_clearance,
    }


def _hole_clearance_dimensions(hole: Dict[str, Any]) -> Tuple[float, float]:
    if hole["shape"] == "circle":
        diameter = 2.0 * float(hole["radius"])
        return diameter, diameter
    return float(hole["width"]), float(hole["height"])


def _validate_traversable_perforations(scene: Dict[str, Any], primitives: Sequence[PrimitiveSpec]) -> Dict[str, Any]:
    validation_rules = dict(scene.get("validation_rules", {}))
    perforated = [primitive for primitive in primitives if primitive.type == "perforated_slab"]
    if not perforated:
        return {
            "valid": True,
            "errors": [],
            "required": bool(validation_rules.get("require_traversable_perforation", False)),
            "perforated_count": 0,
            "traversable_count": 0,
        }

    drone_radius = float(scene.get("drone_profile", {}).get("radius", ArenaConfig.drone_radius))
    drone_height = float(scene.get("drone_profile", {}).get("height", ArenaConfig.drone_height))
    required_width = 2.0 * drone_radius + 0.10
    required_height = max(2.0 * drone_radius, drone_height) + 0.10

    errors: List[str] = []
    traversable_count = 0
    for primitive in perforated:
        holes = (primitive.perforation or {}).get("holes", [])
        if any(
            hole_width >= required_width and hole_height >= required_height
            for hole_width, hole_height in (_hole_clearance_dimensions(hole) for hole in holes)
        ):
            traversable_count += 1
        else:
            errors.append(
                f"{primitive.id} does not provide a hole wide/tall enough for the UAV "
                f"({required_width:.2f}m x {required_height:.2f}m)"
            )

    required = bool(validation_rules.get("require_traversable_perforation", False))
    return {
        "valid": (traversable_count == len(perforated)) if required else True,
        "errors": errors,
        "required": required,
        "perforated_count": len(perforated),
        "traversable_count": traversable_count,
    }


def validate_primitive(primitive: PrimitiveSpec, workspace: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    if primitive.type not in ALLOWED_PRIMITIVE_TYPES:
        errors.append(f"invalid type: {primitive.type}")
    if primitive.support_mode not in ALLOWED_SUPPORT_MODES:
        errors.append(f"invalid support_mode: {primitive.support_mode}")

    hx, hy, hz = _aabb_half_extents(primitive)
    px, py, pz = primitive.pose["x"], primitive.pose["y"], primitive.pose["z"]
    size_x = workspace["size_x"]
    size_y = workspace["size_y"]
    size_z = workspace["size_z"]
    flight_height_min = workspace["flight_height_min"]
    flight_height_max = workspace["flight_height_max"]
    tol = 1e-4

    if px - hx < -size_x / 2.0 - tol or px + hx > size_x / 2.0 + tol:
        errors.append("primitive volume exceeds workspace x bounds")
    if py - hy < -size_y / 2.0 - tol or py + hy > size_y / 2.0 + tol:
        errors.append("primitive volume exceeds workspace y bounds")
    if pz - hz < -tol or pz + hz > size_z + tol:
        errors.append("primitive volume exceeds workspace z bounds")

    if primitive.support_mode == "grounded" and abs((pz - hz) - 0.0) > 0.08:
        errors.append("grounded primitive must touch floor")
    if primitive.support_mode == "ceiling_attached" and abs((pz + hz) - size_z) > 0.08:
        errors.append("ceiling_attached primitive must touch ceiling")
    if primitive.support_mode == "floating":
        if pz - hz < flight_height_min - 0.2 or pz + hz > flight_height_max + 0.2:
            errors.append("floating primitive must stay near valid flight band")
    if primitive.support_mode == "wall_attached":
        touches_wall = (
            abs((px - hx) + size_x / 2.0) <= 0.08 or
            abs((px + hx) - size_x / 2.0) <= 0.08 or
            abs((py - hy) + size_y / 2.0) <= 0.08 or
            abs((py + hy) - size_y / 2.0) <= 0.08
        )
        if not touches_wall:
            errors.append("wall_attached primitive must anchor to a side boundary")
    if primitive.support_mode == "free_moving" and not primitive.is_dynamic:
        errors.append("free_moving primitive must be dynamic")

    errors.extend(_validate_perforation(primitive))
    errors.extend(_validate_motion(primitive.motion))

    valid = len(errors) == 0
    return {
        "primitive_id": primitive.id,
        "valid": valid,
        "errors": errors,
    }


def _build_occupancy_grid(
    primitives: Sequence[PrimitiveSpec],
    workspace: Dict[str, Any],
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
) -> np.ndarray:
    resolution = 0.5
    grid_w = int(math.ceil(workspace["size_x"] / resolution))
    grid_h = int(math.ceil(workspace["size_y"] / resolution))
    grid = np.zeros((grid_w, grid_h), dtype=bool)
    probe_z = max(
        workspace["flight_height_min"],
        min(workspace["flight_height_max"], (start[2] + goal[2]) / 2.0),
    )

    for primitive in primitives:
        if primitive.is_dynamic:
            continue
        (mn, mx) = _aabb_bounds(primitive)
        if probe_z < mn[2] or probe_z > mx[2]:
            continue
        for ix in range(grid_w):
            for iy in range(grid_h):
                wx = -workspace["size_x"] / 2.0 + (ix + 0.5) * resolution
                wy = -workspace["size_y"] / 2.0 + (iy + 0.5) * resolution
                if mn[0] <= wx <= mx[0] and mn[1] <= wy <= mx[1]:
                    grid[ix, iy] = True

    def clamp_index(x: float, y: float) -> Tuple[int, int]:
        ix = max(0, min(grid_w - 1, int((x + workspace["size_x"] / 2.0) / resolution)))
        iy = max(0, min(grid_h - 1, int((y + workspace["size_y"] / 2.0) / resolution)))
        return ix, iy

    start_idx = clamp_index(start[0], start[1])
    goal_idx = clamp_index(goal[0], goal[1])
    grid[start_idx] = False
    grid[goal_idx] = False
    return grid


def _check_connectivity(
    primitives: Sequence[PrimitiveSpec],
    workspace: Dict[str, Any],
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
) -> bool:
    resolution = 0.5
    grid = _build_occupancy_grid(primitives, workspace, start, goal)
    grid_w, grid_h = grid.shape

    def clamp_index(x: float, y: float) -> Tuple[int, int]:
        ix = max(0, min(grid_w - 1, int((x + workspace["size_x"] / 2.0) / resolution)))
        iy = max(0, min(grid_h - 1, int((y + workspace["size_y"] / 2.0) / resolution)))
        return ix, iy

    start_idx = clamp_index(start[0], start[1])
    goal_idx = clamp_index(goal[0], goal[1])
    queue: deque[Tuple[int, int]] = deque([start_idx])
    visited = {start_idx}
    directions = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)]

    while queue:
        cx, cy = queue.popleft()
        if (cx, cy) == goal_idx:
            return True
        for dx, dy in directions:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < grid_w and 0 <= ny < grid_h and (nx, ny) not in visited and not grid[nx, ny]:
                visited.add((nx, ny))
                queue.append((nx, ny))
    return False


def validate_scene(scene: Dict[str, Any]) -> Dict[str, Any]:
    workspace = scene["workspace"]
    primitives = [
        primitive if isinstance(primitive, PrimitiveSpec) else _primitive_from_dict(primitive)
        for primitive in scene["primitives"]
    ]
    start = tuple(scene["start"])
    goal = tuple(scene["goal"])

    primitive_reports = [validate_primitive(primitive, workspace) for primitive in primitives]
    geometry_valid = all(report["valid"] for report in primitive_reports)

    overlap_errors: List[Tuple[str, str]] = []
    max_overlap_tolerance = scene.get("generator_rules", {}).get("max_overlap_tolerance", 0.0)
    for idx, primitive in enumerate(primitives):
        for other in primitives[idx + 1:]:
            if primitive.is_dynamic and other.is_dynamic:
                continue
            if _intersects(primitive, other, tolerance=max_overlap_tolerance):
                if primitive.is_dynamic or other.is_dynamic:
                    overlap_errors.append((primitive.id, other.id))
                elif not primitive.metadata.get("allow_overlap", False) and not other.metadata.get("allow_overlap", False):
                    overlap_errors.append((primitive.id, other.id))

    connectivity_valid = _check_connectivity(primitives, workspace, start, goal)
    template_presence = _validate_required_template_presence(scene)
    start_goal_report = _validate_start_goal(scene, primitives)
    perforation_report = _validate_traversable_perforations(scene, primitives)
    validation_rules = dict(scene.get("validation_rules", {}))
    allow_failure_analysis_only = bool(validation_rules.get("allow_failure_analysis_only", False))

    strict_valid = (
        geometry_valid and
        len(overlap_errors) == 0 and
        connectivity_valid and
        template_presence[0] and
        start_goal_report["valid"] and
        perforation_report["valid"]
    )
    validation_status = (
        geometry_valid and len(overlap_errors) == 0
        if allow_failure_analysis_only
        else strict_valid
    )

    primitive_counts: Dict[str, int] = {}
    for primitive in primitives:
        primitive_counts[primitive.type] = primitive_counts.get(primitive.type, 0) + 1

    dynamic_obstacle_count = sum(primitive.is_dynamic for primitive in primitives)
    traversable_hole_count = 0
    for primitive in primitives:
        if primitive.perforation and primitive.perforation.get("enabled", False):
            traversable_hole_count += primitive.perforation.get("hole_count", 0)

    return {
        "valid": validation_status,
        "strict_valid": strict_valid,
        "geometry_valid": geometry_valid,
        "workspace_valid": all("workspace" not in err for report in primitive_reports for err in report["errors"]),
        "overlap_valid": len(overlap_errors) == 0,
        "navigation_valid": connectivity_valid,
        "connectivity_status": "connected" if connectivity_valid else "disconnected",
        "template_presence_valid": template_presence[0],
        "template_presence_errors": template_presence[1],
        "start_goal_valid": start_goal_report["valid"],
        "start_goal_errors": start_goal_report["errors"],
        "start_goal_distance": start_goal_report["start_goal_distance"],
        "start_clearance": start_goal_report["start_clearance"],
        "goal_clearance": start_goal_report["goal_clearance"],
        "goal_boundary_clearance": start_goal_report["goal_boundary_clearance"],
        "traversable_perforation_valid": perforation_report["valid"],
        "traversable_perforation_errors": perforation_report["errors"],
        "traversable_perforated_count": perforation_report["traversable_count"],
        "primitive_reports": primitive_reports,
        "overlap_errors": overlap_errors,
        "primitive_counts": primitive_counts,
        "dynamic_obstacle_count": dynamic_obstacle_count,
        "traversable_hole_count": traversable_hole_count,
    }


def scene_to_json(scene: Dict[str, Any], path: str) -> None:
    serializable = dict(scene)
    serializable["primitives"] = [
        _primitive_to_dict(primitive) if isinstance(primitive, PrimitiveSpec) else primitive
        for primitive in scene["primitives"]
    ]
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")


def scene_from_json(path: str) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data["primitives"] = [_primitive_from_dict(primitive) for primitive in data["primitives"]]
    return data


def _next_id(counter: List[int], prefix: str = "primitive") -> str:
    current = counter[0]
    counter[0] += 1
    return f"{prefix}_{current:04d}"


def _uniform_pose(
    rng: random.Random,
    workspace: Dict[str, float],
    margin_xy: float,
    z: float,
) -> Tuple[float, float, float]:
    x = rng.uniform(-workspace["size_x"] / 2.0 + margin_xy, workspace["size_x"] / 2.0 - margin_xy)
    y = rng.uniform(-workspace["size_y"] / 2.0 + margin_xy, workspace["size_y"] / 2.0 - margin_xy)
    return x, y, z


def _clamp_start_goal(cfg: ArenaConfig) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    margin_xy = 2.0
    start = (
        max(-cfg.size_x / 2.0 + margin_xy, min(cfg.size_x / 2.0 - margin_xy, cfg.start_pos[0])),
        max(-cfg.size_y / 2.0 + margin_xy, min(cfg.size_y / 2.0 - margin_xy, cfg.start_pos[1])),
        min(max(cfg.start_pos[2], cfg.flight_height_min), cfg.flight_height_max),
    )
    goal = (
        max(-cfg.size_x / 2.0 + margin_xy, min(cfg.size_x / 2.0 - margin_xy, cfg.goal_pos[0])),
        max(-cfg.size_y / 2.0 + margin_xy, min(cfg.size_y / 2.0 - margin_xy, cfg.goal_pos[1])),
        min(max(cfg.goal_pos[2], cfg.flight_height_min), cfg.flight_height_max),
    )
    return start, goal


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _deep_merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dicts(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _load_yaml_file(path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Scene config at {path} must load to a dict.")
    return data


def load_scene_family_config(
    scene_family: str | SceneMode,
    cfg_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    cfg_dir = cfg_dir or SCENE_CFG_DIR
    family_value = scene_family.value if isinstance(scene_family, SceneMode) else str(scene_family)

    base_cfg = {}
    base_path = cfg_dir / "scene_cfg_base.yaml"
    if base_path.exists():
        base_cfg = _load_yaml_file(base_path)

    family_enum = SceneMode(family_value)
    family_cfg_name = FAMILY_TO_SCENE_CFG.get(family_enum)
    if family_cfg_name is None:
        raise ValueError(f"No scene cfg mapping registered for family '{family_value}'.")

    family_path = cfg_dir / family_cfg_name
    if not family_path.exists():
        if base_cfg:
            merged = copy.deepcopy(base_cfg)
            merged["scene_family"] = family_value
            return merged
        raise FileNotFoundError(f"Missing scene config file: {family_path}")

    family_cfg = _load_yaml_file(family_path)
    merged = _deep_merge_dicts(base_cfg, family_cfg)
    merged["scene_family"] = family_value
    merged["scene_cfg_name"] = family_cfg_name
    return merged


def _sample_float_range(rng: random.Random, value: Any, default: float) -> float:
    if value is None:
        return float(default)
    if isinstance(value, (list, tuple)) and len(value) == 2:
        lo, hi = float(value[0]), float(value[1])
        if hi < lo:
            lo, hi = hi, lo
        return rng.uniform(lo, hi)
    return float(value)


def _sample_int_range(rng: random.Random, value: Any, default: int) -> int:
    if value is None:
        return int(default)
    if isinstance(value, (list, tuple)) and len(value) == 2:
        lo, hi = int(value[0]), int(value[1])
        if hi < lo:
            lo, hi = hi, lo
        return rng.randint(lo, hi)
    return int(value)


def _sample_boundary_band_point(
    rng: random.Random,
    workspace: Dict[str, float],
    band_min: float,
    band_max: float,
) -> Tuple[float, float]:
    half_x = workspace["size_x"] / 2.0
    half_y = workspace["size_y"] / 2.0
    side = rng.choice(["left", "right", "bottom", "top"])
    offset = rng.uniform(band_min, band_max)
    if side == "left":
        return (-half_x + offset, rng.uniform(-half_y + band_max, half_y - band_max))
    if side == "right":
        return (half_x - offset, rng.uniform(-half_y + band_max, half_y - band_max))
    if side == "bottom":
        return (rng.uniform(-half_x + band_max, half_x - band_max), -half_y + offset)
    return (rng.uniform(-half_x + band_max, half_x - band_max), half_y - offset)


def _sample_interior_point(
    rng: random.Random,
    workspace: Dict[str, float],
    boundary_clearance: float,
) -> Tuple[float, float]:
    half_x = workspace["size_x"] / 2.0
    half_y = workspace["size_y"] / 2.0
    return (
        rng.uniform(-half_x + boundary_clearance, half_x - boundary_clearance),
        rng.uniform(-half_y + boundary_clearance, half_y - boundary_clearance),
    )


def _sample_start_goal_pair(
    workspace: Dict[str, float],
    start_goal_cfg: Dict[str, Any],
    seed: int,
) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    rng = random.Random(seed)
    band_min = float(start_goal_cfg.get("start_band_min", 0.5))
    band_max = float(start_goal_cfg.get("start_band_max", 1.5))
    goal_boundary_clearance = float(start_goal_cfg.get("goal_boundary_clearance_min", 1.0))
    d_min = float(start_goal_cfg.get("start_goal_distance_min", 8.0))
    d_max = float(start_goal_cfg.get("start_goal_distance_max", 16.0))
    z_min = workspace["flight_height_min"]
    z_max = workspace["flight_height_max"]

    for _ in range(200):
        sx, sy = _sample_boundary_band_point(rng, workspace, band_min, band_max)
        gx, gy = _sample_interior_point(rng, workspace, goal_boundary_clearance)
        sz = rng.uniform(z_min, z_max)
        gz = rng.uniform(z_min, z_max)
        dist = math.sqrt((sx - gx) ** 2 + (sy - gy) ** 2 + (sz - gz) ** 2)
        if d_min <= dist <= d_max:
            return (sx, sy, sz), (gx, gy, gz)

    start = (-workspace["size_x"] / 2.0 + band_max, 0.0, (z_min + z_max) / 2.0)
    goal = (0.0, 0.0, (z_min + z_max) / 2.0)
    return start, goal


def _sample_route_adjacent_center(
    rng: random.Random,
    workspace: Dict[str, float],
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
    margin_xy: float,
    lateral_span: float = 2.0,
) -> Tuple[float, float]:
    half_x = workspace["size_x"] / 2.0
    half_y = workspace["size_y"] / 2.0
    t = rng.uniform(0.30, 0.70)
    base_x = start[0] * (1.0 - t) + goal[0] * t
    base_y = start[1] * (1.0 - t) + goal[1] * t
    dx = goal[0] - start[0]
    dy = goal[1] - start[1]
    norm = math.hypot(dx, dy)
    if norm < 1e-6:
        perp_x, perp_y = 0.0, 1.0
    else:
        perp_x, perp_y = -dy / norm, dx / norm
    offset = rng.uniform(-lateral_span, lateral_span)
    x = base_x + perp_x * offset
    y = base_y + perp_y * offset
    x = max(-half_x + margin_xy, min(half_x - margin_xy, x))
    y = max(-half_y + margin_xy, min(half_y - margin_xy, y))
    return x, y


def _reserve_structured_budget(
    template_type: str,
    template_cfg: Dict[str, Any],
    static_ratio_cfg: Dict[str, float],
) -> Dict[str, int]:
    if template_type == "bottleneck":
        return {"box": 2}
    if template_type == "perforated_barrier":
        return {"perforated_slab": 1}
    if template_type == "low_clearance_passage":
        return {"slab": 1, "box": 2}
    if template_type == "moving_crossing":
        return {"sphere": 1, "capsule": 1}
    if template_type == "pillar_field":
        return {"cylinder": 4}
    if template_type == "clutter_cluster":
        total = int(template_cfg.get("obstacle_count", 4))
        box_ratio = float(static_ratio_cfg.get("box", 0.5))
        cyl_ratio = float(static_ratio_cfg.get("cylinder", 0.5))
        ratio_sum = max(box_ratio + cyl_ratio, 1e-6)
        box_count = int(round(total * box_ratio / ratio_sum))
        return {"box": box_count, "cylinder": max(0, total - box_count)}
    return {}


def _compile_scene_rule_templates(
    scene_rules: Dict[str, Any],
    difficulty: float,
    seed: int,
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    rng = random.Random(seed + 17)
    templates_cfg = dict(scene_rules.get("templates", {}))
    params_cfg = dict(scene_rules.get("template_params", {}))
    static_ratio_cfg = dict(scene_rules.get("primitive_type_ratio", {}).get("static", {}))
    if not templates_cfg.get("enabled", False):
        return [], {}

    min_templates = int(templates_cfg.get("min_templates_per_scene", 0))
    max_templates = int(templates_cfg.get("max_templates_per_scene", min_templates))
    if max_templates < min_templates:
        max_templates = min_templates
    num_templates = rng.randint(min_templates, max_templates) if max_templates > 0 else 0
    candidate_types = [
        template_type
        for template_type in templates_cfg.get("candidate_types", [])
        if params_cfg.get(template_type, {}).get("enabled", True)
    ]
    rng.shuffle(candidate_types)
    selected = candidate_types[:num_templates]

    compiled: List[Dict[str, Any]] = []
    reserved_budget: Dict[str, int] = {}
    for template_type in selected:
        param_cfg = dict(params_cfg.get(template_type, {}))
        placement_mode = param_cfg.get("placement_mode", "random_free_region")
        template_cfg: Dict[str, Any] = {"type": template_type, "count": 1, "placement_mode": placement_mode}

        if template_type == "bottleneck":
            template_cfg["gap_width"] = _sample_float_range(rng, param_cfg.get("width_range"), 2.2)
            template_cfg["length_override"] = _sample_float_range(rng, param_cfg.get("length_range"), 3.0)
        elif template_type == "clutter_cluster":
            template_cfg["cluster_obstacle_count"] = _sample_int_range(rng, param_cfg.get("obstacle_count_range"), 4)
            template_cfg["cluster_radius"] = _sample_float_range(rng, param_cfg.get("cluster_radius_range"), 2.0)
        elif template_type == "perforated_barrier":
            template_cfg["panel_width"] = _sample_float_range(rng, param_cfg.get("size_x_range"), 3.0)
            template_cfg["panel_height"] = _sample_float_range(rng, param_cfg.get("size_y_range"), 3.0)
            template_cfg["thickness"] = _sample_float_range(rng, param_cfg.get("thickness_range"), 0.15)
            template_cfg["hole_count"] = _sample_int_range(rng, param_cfg.get("hole_count_range"), 1)
            template_cfg["hole_shape_candidates"] = list(param_cfg.get("hole_shape_candidates", ["rectangle"]))
            template_cfg["hole_margin_min"] = float(param_cfg.get("hole_margin_min", 0.25))
            template_cfg["hole_spacing_min"] = float(param_cfg.get("hole_spacing_min", 0.25))
            template_cfg["corridor_width"] = max(0.9, template_cfg["panel_width"] * 0.38)

        reserved = _reserve_structured_budget(template_type, template_cfg, static_ratio_cfg)
        for primitive_type, count in reserved.items():
            reserved_budget[primitive_type] = reserved_budget.get(primitive_type, 0) + count
        compiled.append(template_cfg)

    return compiled, reserved_budget


def _compile_background_templates(
    scene_rules: Dict[str, Any],
    difficulty: float,
    reserved_budget: Dict[str, int],
) -> List[Dict[str, Any]]:
    primitive_budget = dict(scene_rules.get("primitive_budget", {}))
    static_ratio_cfg = dict(scene_rules.get("primitive_type_ratio", {}).get("static", {}))
    dynamic_cfg = dict(scene_rules.get("dynamic_obstacles", {}))
    templates: List[Dict[str, Any]] = []

    def budget_target(primitive_type: str) -> int:
        budget = primitive_budget.get(primitive_type, [0, 0])
        low = int(budget[0]) if isinstance(budget, (list, tuple)) else int(budget)
        high = int(budget[1]) if isinstance(budget, (list, tuple)) and len(budget) > 1 else low
        if high < low:
            low, high = high, low
        target = int(round(low + (high - low) * difficulty))
        return max(0, target - reserved_budget.get(primitive_type, 0))

    cylinder_target = budget_target("cylinder")
    if cylinder_target > 0:
        templates.append({"type": "pillar_field", "count": 1, "target_count": cylinder_target})

    box_target = budget_target("box")
    if box_target > 0:
        templates.append({"type": "box_field", "count": 1, "target_count": box_target})

    slab_target = budget_target("slab")
    if slab_target > 0:
        templates.append({"type": "slab_field", "count": 1, "target_count": slab_target})

    perforated_target = budget_target("perforated_slab")
    if perforated_target > 0:
        templates.append({"type": "perforated_field", "count": 1, "target_count": perforated_target})

    if dynamic_cfg.get("enabled", False) and int(dynamic_cfg.get("max_dynamic_count", 0)) > 0:
        sphere_target = budget_target("sphere")
        capsule_target = budget_target("capsule")
        dynamic_target = min(
            int(dynamic_cfg.get("max_dynamic_count", 0)),
            sphere_target + capsule_target,
        )
        if dynamic_target > 0:
            templates.append({
                "type": "dynamic_field",
                "count": 1,
                "target_count": dynamic_target,
                "sphere_fraction": float(scene_rules.get("primitive_type_ratio", {}).get("dynamic", {}).get("sphere", 0.5)),
            })

    return templates


def compile_scene_config_from_rules(
    scene_rules: Dict[str, Any],
    seed: Optional[int] = None,
    difficulty: float = 0.5,
    gravity_tilt_enabled: Optional[bool] = None,
) -> Dict[str, Any]:
    scene_rules = copy.deepcopy(scene_rules)
    resolved_seed = int(scene_rules.get("seed", 0) if seed is None else seed)
    workspace = dict(scene_rules["workspace"])
    start, goal = _sample_start_goal_pair(workspace, dict(scene_rules.get("start_goal", {})), resolved_seed)
    structured_templates, reserved_budget = _compile_scene_rule_templates(scene_rules, difficulty, resolved_seed, start, goal)
    background_templates = _compile_background_templates(scene_rules, difficulty, reserved_budget)
    templates = [*structured_templates, *background_templates]

    background_cfg = dict(scene_rules.get("background_placement", {}))
    free_min = float(background_cfg.get("free_space_fraction_min", 0.35))
    free_max = float(background_cfg.get("free_space_fraction_max", 0.85))
    occupancy_scale = float(background_cfg.get("occupancy_estimate_scale", 0.02))
    occupancy_range = (
        max(0.0, (1.0 - free_max) * occupancy_scale),
        max(0.0, (1.0 - free_min) * occupancy_scale),
    )
    validation_cfg = dict(scene_rules.get("validation", {}))

    return {
        "scene_id": str(scene_rules.get("scene_id", f"{scene_rules.get('scene_family', 'scene')}_{resolved_seed:04d}")),
        "seed": resolved_seed,
        "workspace": workspace,
        "start": start,
        "goal": goal,
        "difficulty": float(difficulty),
        "scene_mode": str(scene_rules.get("scene_family", "nominal")),
        "scene_cfg_name": scene_rules.get("scene_cfg_name"),
        "sub_mode": None,
        "corridor_width": None,
        "obstacle_density": float(difficulty),
        "dynamic_obstacle_ratio": float(difficulty),
        "gravity_tilt_enabled": bool(scene_rules.get("gravity_tilt_enabled", True) if gravity_tilt_enabled is None else gravity_tilt_enabled),
        "templates": templates,
        "primitive_budget": copy.deepcopy(scene_rules.get("primitive_budget", {})),
        "generator_rules": {
            "allow_floating_static": True,
            "allow_dynamic_obstacles": bool(scene_rules.get("dynamic_obstacles", {}).get("enabled", False)),
            "enforce_connectivity": bool(validation_cfg.get("enforce_connectivity", True)),
            "max_overlap_tolerance": float(validation_cfg.get("max_overlap_tolerance", 0.0)),
            "scene_retry_budget": int(background_cfg.get("max_rejection_trials", 200)),
            "target_occupancy_range": occupancy_range,
        },
        "scene_family": str(scene_rules.get("scene_family", "nominal")),
        "distribution_modes": copy.deepcopy(scene_rules.get("distribution_modes", {})),
        "start_goal_rules": copy.deepcopy(scene_rules.get("start_goal", {})),
        "validation_rules": validation_cfg,
    }


def _build_navrl_mixed_templates(
    seed: int,
    difficulty: float,
    obstacle_density: Optional[float],
    dynamic_ratio: float,
) -> Tuple[List[Dict[str, Any]], float, float]:
    """
    Build a single mixed-scene template plan.

    The mixed scene is intentionally composed as a set of globally distributed
    primitive fields instead of center-biased local clusters. This keeps the
    spatial density more even across the workspace while preserving a mix of
    primitive types.
    """
    rng = random.Random(seed)
    density = _clamp_unit(
        obstacle_density if obstacle_density is not None else (0.45 + 0.45 * difficulty)
    )
    dynamic_density = _clamp_unit(dynamic_ratio if dynamic_ratio > 0.0 else (0.25 + 0.55 * difficulty))

    static_scale = 1.0 + rng.uniform(-0.08, 0.08)
    dynamic_scale = 1.0 + rng.uniform(-0.10, 0.10)

    templates = [
        {"type": "pillar_field", "count": 1, "scale": static_scale},
        {"type": "box_field", "count": 1, "scale": static_scale},
        {"type": "slab_field", "count": 1, "scale": static_scale},
        {"type": "perforated_field", "count": 1, "scale": static_scale},
        {"type": "dynamic_field", "count": 1, "scale": dynamic_scale},
    ]
    return templates, density, dynamic_density


def _jittered_grid_positions(
    rng: random.Random,
    workspace: Dict[str, float],
    margin_xy: float,
    cell_size: float,
    jitter_ratio: float = 0.35,
) -> List[Tuple[float, float]]:
    x_min = -workspace["size_x"] / 2.0 + margin_xy
    x_max = workspace["size_x"] / 2.0 - margin_xy
    y_min = -workspace["size_y"] / 2.0 + margin_xy
    y_max = workspace["size_y"] / 2.0 - margin_xy
    if x_min >= x_max or y_min >= y_max:
        return []

    x_centers: List[float] = []
    y_centers: List[float] = []
    x = x_min + cell_size / 2.0
    while x <= x_max - cell_size / 2.0 + 1e-6:
        x_centers.append(x)
        x += cell_size
    if not x_centers:
        x_centers = [(x_min + x_max) / 2.0]

    y = y_min + cell_size / 2.0
    while y <= y_max - cell_size / 2.0 + 1e-6:
        y_centers.append(y)
        y += cell_size
    if not y_centers:
        y_centers = [(y_min + y_max) / 2.0]

    jitter = cell_size * jitter_ratio
    positions: List[Tuple[float, float]] = []
    for cx in x_centers:
        for cy in y_centers:
            px = max(x_min, min(x_max, cx + rng.uniform(-jitter, jitter)))
            py = max(y_min, min(y_max, cy + rng.uniform(-jitter, jitter)))
            positions.append((px, py))
    rng.shuffle(positions)
    return positions


def _template_bottleneck(
    workspace: Dict[str, float],
    rng: random.Random,
    counter: List[int],
    difficulty: float,
    gap_width: Optional[float],
    length_override: Optional[float],
    placement_mode: Optional[str],
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
    existing: Sequence[PrimitiveSpec],
) -> Tuple[List[PrimitiveSpec], Dict[str, Any]]:
    gap = gap_width if gap_width is not None else max(1.0, 2.4 - 1.0 * difficulty)
    slab_length = float(length_override) if length_override is not None else (1.8 + 1.2 * difficulty)
    thickness = 0.4
    wall_height = min(workspace["size_z"] - 0.2, _sample_navrl_height(rng, workspace))
    if placement_mode == "route_adjacent":
        center_x, center_y = _sample_route_adjacent_center(rng, workspace, start, goal, margin_xy=2.5, lateral_span=2.0)
    else:
        center_x, center_y, _ = _uniform_pose(rng, workspace, margin_xy=3.0, z=0.0)
    left_y = -(gap / 2.0 + slab_length / 2.0)
    right_y = +(gap / 2.0 + slab_length / 2.0)

    primitives = [
        make_box(
            _next_id(counter),
            size_x=thickness,
            size_y=slab_length,
            size_z=wall_height,
            x=center_x,
            y=center_y + left_y,
            z=wall_height / 2.0,
            support_mode="grounded",
            semantic_role="bottleneck_boundary",
        ),
        make_box(
            _next_id(counter),
            size_x=thickness,
            size_y=slab_length,
            size_z=wall_height,
            x=center_x,
            y=center_y + right_y,
            z=wall_height / 2.0,
            support_mode="grounded",
            semantic_role="bottleneck_boundary",
        ),
    ]
    if not all(_is_candidate_valid(primitive, [*existing, *[p for p in primitives if p is not primitive]], workspace, start, goal, clearance_xy=0.2) for primitive in primitives):
        return [], {"type": "bottleneck", "gap_width": gap, "skipped": True}
    return primitives, {"type": "bottleneck", "gap_width": gap}


def _template_pillar_field(
    workspace: Dict[str, float],
    rng: random.Random,
    counter: List[int],
    difficulty: float,
    obstacle_density: Optional[float],
    density_scale: float,
    count_override: Optional[int],
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
    existing: Sequence[PrimitiveSpec],
) -> Tuple[List[PrimitiveSpec], Dict[str, Any]]:
    density = difficulty if obstacle_density is None else max(difficulty, obstacle_density)
    count = int(count_override) if count_override is not None else max(12, int(round((18 + density * 20) * density_scale)))
    primitives: List[PrimitiveSpec] = []
    positions = _jittered_grid_positions(rng, workspace, margin_xy=2.0, cell_size=2.2)
    for x, y in positions:
        if len(primitives) >= count:
            break
        radius = rng.uniform(0.2, 0.5)
        height = _sample_navrl_height(rng, workspace)

        def make_candidate():
            return make_cylinder(
                _next_id(counter),
                radius=radius,
                height=height,
                x=x,
                y=y,
                z=height / 2.0,
                axis_mode="vertical",
                support_mode="grounded",
                semantic_role="pillar",
            )

        candidate = _try_place_primitive(
            make_candidate,
            [*existing, *primitives],
            workspace,
            start,
            goal,
            attempts=80,
        )
        if candidate is not None:
            primitives.append(candidate)
    return primitives, {"type": "pillar_field", "count": len(primitives)}


def _template_box_field(
    workspace: Dict[str, float],
    rng: random.Random,
    counter: List[int],
    difficulty: float,
    obstacle_density: Optional[float],
    density_scale: float,
    count_override: Optional[int],
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
    existing: Sequence[PrimitiveSpec],
) -> Tuple[List[PrimitiveSpec], Dict[str, Any]]:
    density = difficulty if obstacle_density is None else max(difficulty, obstacle_density)
    count = int(count_override) if count_override is not None else max(6, int(round((8 + density * 12) * density_scale)))
    primitives: List[PrimitiveSpec] = []
    positions = _jittered_grid_positions(rng, workspace, margin_xy=2.0, cell_size=3.0)
    for x, y in positions:
        if len(primitives) >= count:
            break

        def make_candidate():
            sx = rng.uniform(0.4, 1.1)
            sy = rng.uniform(0.4, 1.1)
            sz = rng.choice([1.0, 1.5, 2.0])
            yaw = rng.uniform(-math.pi, math.pi)
            return make_box(
                _next_id(counter),
                size_x=sx,
                size_y=sy,
                size_z=sz,
                x=x,
                y=y,
                z=sz / 2.0,
                yaw=yaw,
                support_mode="grounded",
                semantic_role="clutter",
            )

        candidate = _try_place_primitive(
            make_candidate,
            [*existing, *primitives],
            workspace,
            start,
            goal,
            attempts=40,
        )
        if candidate is not None:
            primitives.append(candidate)
    return primitives, {"type": "box_field", "count": len(primitives)}


def _template_slab_field(
    workspace: Dict[str, float],
    rng: random.Random,
    counter: List[int],
    difficulty: float,
    obstacle_density: Optional[float],
    density_scale: float,
    count_override: Optional[int],
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
    existing: Sequence[PrimitiveSpec],
) -> Tuple[List[PrimitiveSpec], Dict[str, Any]]:
    density = difficulty if obstacle_density is None else max(difficulty, obstacle_density)
    count = int(count_override) if count_override is not None else max(2, int(round((3 + density * 4) * density_scale)))
    primitives: List[PrimitiveSpec] = []
    positions = _jittered_grid_positions(rng, workspace, margin_xy=2.5, cell_size=4.5)
    mid_height = (workspace["flight_height_min"] + workspace["flight_height_max"]) / 2.0
    for x, y in positions:
        if len(primitives) >= count:
            break

        def make_candidate():
            yaw = rng.uniform(-math.pi, math.pi)
            if rng.random() < 0.5:
                size_x = rng.uniform(1.4, 2.4)
                size_y = rng.uniform(0.7, 1.3)
                thickness = 0.1
                z = min(workspace["flight_height_max"] + 0.15, mid_height + rng.uniform(0.15, 0.55))
                return make_slab(
                    _next_id(counter),
                    size_x=size_x,
                    size_y=size_y,
                    thickness=thickness,
                    x=x,
                    y=y,
                    z=z,
                    slab_mode="horizontal",
                    yaw=yaw,
                    support_mode="floating",
                    semantic_role="overhead_hazard",
                )
            size_x = rng.uniform(1.2, 2.0)
            size_y = rng.uniform(1.0, 1.8)
            thickness = 0.1
            z = size_y / 2.0
            return make_slab(
                _next_id(counter),
                size_x=size_x,
                size_y=size_y,
                thickness=thickness,
                x=x,
                y=y,
                z=z,
                slab_mode="vertical",
                yaw=yaw,
                support_mode="grounded",
                semantic_role="barrier",
            )

        candidate = _try_place_primitive(
            make_candidate,
            [*existing, *primitives],
            workspace,
            start,
            goal,
            attempts=40,
        )
        if candidate is not None:
            primitives.append(candidate)
    return primitives, {"type": "slab_field", "count": len(primitives)}


def _template_perforated_field(
    workspace: Dict[str, float],
    rng: random.Random,
    counter: List[int],
    difficulty: float,
    obstacle_density: Optional[float],
    density_scale: float,
    count_override: Optional[int],
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
    existing: Sequence[PrimitiveSpec],
) -> Tuple[List[PrimitiveSpec], Dict[str, Any]]:
    density = difficulty if obstacle_density is None else max(difficulty, obstacle_density)
    count = int(count_override) if count_override is not None else max(1, int(round((2 + density * 3) * density_scale)))
    primitives: List[PrimitiveSpec] = []
    positions = _jittered_grid_positions(rng, workspace, margin_xy=2.8, cell_size=5.2)
    mid_height = (workspace["flight_height_min"] + workspace["flight_height_max"]) / 2.0
    for x, y in positions:
        if len(primitives) >= count:
            break

        def make_candidate():
            panel_width = rng.uniform(1.8, 2.6)
            panel_height = rng.uniform(1.8, 2.8)
            hole_width = rng.uniform(0.9, 1.4)
            hole_height = rng.uniform(0.9, 1.5)
            hole_height = min(hole_height, panel_height - 0.4)
            hole_center_z = min(max(mid_height, hole_height / 2.0 + 0.2), panel_height - hole_height / 2.0 - 0.2)
            yaw = rng.uniform(-math.pi, math.pi)
            holes = [
                {
                    "shape": "rectangle",
                    "center_u": 0.0,
                    "center_v": hole_center_z - panel_height / 2.0,
                    "width": hole_width,
                    "height": hole_height,
                }
            ]
            return make_perforated_slab(
                _next_id(counter),
                size_x=panel_width,
                size_y=panel_height,
                thickness=0.1,
                x=x,
                y=y,
                z=panel_height / 2.0,
                slab_mode="vertical",
                holes=holes,
                edge_margin_min=0.2,
                hole_spacing_min=0.2,
                yaw=yaw,
                support_mode="grounded",
                semantic_role="passable_panel",
            )

        candidate = _try_place_primitive(
            make_candidate,
            [*existing, *primitives],
            workspace,
            start,
            goal,
            attempts=40,
        )
        if candidate is not None:
            primitives.append(candidate)
    return primitives, {"type": "perforated_field", "count": len(primitives)}


def _template_dynamic_field(
    workspace: Dict[str, float],
    rng: random.Random,
    counter: List[int],
    difficulty: float,
    dynamic_ratio: float,
    density_scale: float,
    count_override: Optional[int],
    sphere_fraction: float,
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
    existing: Sequence[PrimitiveSpec],
) -> Tuple[List[PrimitiveSpec], Dict[str, Any]]:
    dynamic_density = max(difficulty, dynamic_ratio)
    count = int(count_override) if count_override is not None else max(2, int(round((2 + dynamic_density * 4) * density_scale)))
    primitives: List[PrimitiveSpec] = []
    positions = _jittered_grid_positions(rng, workspace, margin_xy=2.8, cell_size=5.5)
    mid_height = (workspace["flight_height_min"] + workspace["flight_height_max"]) / 2.0
    for idx, (x, y) in enumerate(positions):
        if len(primitives) >= count:
            break

        def make_candidate():
            z = min(
                workspace["size_z"] - 0.35,
                max(0.35, mid_height + rng.uniform(-0.35, 0.35)),
            )
            speed = rng.uniform(0.6, 1.4)
            motion = _make_motion(
                "random_walk",
                speed_min=speed * 0.7,
                speed_max=speed,
                trajectory_params={
                    "heading_resample_interval": rng.randint(16, 28),
                    "repulsion_gain": 1.0,
                },
                seed=rng.randint(0, 10_000),
            )
            use_capsule = (idx / max(count, 1)) >= float(sphere_fraction)
            if use_capsule:
                return make_capsule(
                    _next_id(counter),
                    radius=0.18,
                    segment_length=0.8,
                    x=x,
                    y=y,
                    z=z,
                    axis_mode="horizontal",
                    semantic_role="moving_agent",
                    motion=motion,
                )
            return make_sphere(
                _next_id(counter),
                radius=0.2,
                x=x,
                y=y,
                z=z,
                semantic_role="moving_disturbance",
                motion=motion,
            )

        candidate = _try_place_primitive(
            make_candidate,
            [*existing, *primitives],
            workspace,
            start,
            goal,
            attempts=30,
        )
        if candidate is not None:
            primitives.append(candidate)
    return primitives, {"type": "dynamic_field", "count": len(primitives)}


def _template_clutter_cluster(
    workspace: Dict[str, float],
    rng: random.Random,
    counter: List[int],
    difficulty: float,
    count_override: Optional[int],
    cluster_radius: Optional[float],
    placement_mode: Optional[str],
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
    existing: Sequence[PrimitiveSpec],
) -> Tuple[List[PrimitiveSpec], Dict[str, Any]]:
    count = int(count_override) if count_override is not None else int(4 + difficulty * 6)
    cluster_radius_value = float(cluster_radius) if cluster_radius is not None else 2.2
    if placement_mode == "route_adjacent":
        center_x, center_y = _sample_route_adjacent_center(rng, workspace, start, goal, margin_xy=2.5, lateral_span=2.5)
    else:
        center_x, center_y, _ = _uniform_pose(rng, workspace, margin_xy=3.0, z=0.0)
    primitives: List[PrimitiveSpec] = []
    for _ in range(count):
        def make_candidate():
            offset_x = rng.uniform(-cluster_radius_value, cluster_radius_value)
            offset_y = rng.uniform(-cluster_radius_value, cluster_radius_value)
            if rng.random() < 0.5:
                sx = rng.uniform(0.4, 1.1)
                sy = rng.uniform(0.4, 1.1)
                sz = rng.uniform(1.0, 2.0)
                return make_box(
                    _next_id(counter),
                    size_x=sx,
                    size_y=sy,
                    size_z=sz,
                    x=center_x + offset_x,
                    y=center_y + offset_y,
                    z=sz / 2.0,
                    support_mode="grounded",
                    semantic_role="clutter",
                )
            cylinder_radius = rng.uniform(0.2, 0.45)
            height = rng.choice([1.0, 1.5, 2.0])
            return make_cylinder(
                _next_id(counter),
                radius=cylinder_radius,
                height=height,
                x=center_x + offset_x,
                y=center_y + offset_y,
                z=height / 2.0,
                support_mode="grounded",
                semantic_role="clutter",
            )

        candidate = _try_place_primitive(
            make_candidate,
            [*existing, *primitives],
            workspace,
            start,
            goal,
            attempts=60,
        )
        if candidate is not None:
            primitives.append(candidate)
    return primitives, {"type": "clutter_cluster", "count": len(primitives)}


def _template_low_clearance_passage(
    workspace: Dict[str, float],
    rng: random.Random,
    counter: List[int],
    difficulty: float,
    sub_mode: Optional[str],
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
    existing: Sequence[PrimitiveSpec],
) -> Tuple[List[PrimitiveSpec], Dict[str, Any]]:
    center_x = rng.uniform(-workspace["size_x"] / 6.0, workspace["size_x"] / 6.0)
    passage_width = 2.2 - 0.8 * difficulty
    slab_thickness = 0.1
    clearance = workspace["flight_height_min"] + 0.5 - 0.25 * difficulty
    clearance = max(workspace["flight_height_min"] + 0.15, clearance)
    slab_length = 3.5
    ceiling_z = clearance + slab_thickness / 2.0
    post_height = ceiling_z

    primitives = [
        make_slab(
            _next_id(counter),
            size_x=slab_length,
            size_y=passage_width,
            thickness=slab_thickness,
            x=center_x,
            y=0.0,
            z=ceiling_z,
            slab_mode="horizontal",
            support_mode="floating",
            semantic_role="overhead_hazard",
        ),
        make_box(
            _next_id(counter),
            size_x=0.35,
            size_y=0.35,
            size_z=post_height,
            x=center_x - slab_length / 2.0 + 0.4,
            y=passage_width / 2.0 + 0.25,
            z=post_height / 2.0,
            support_mode="grounded",
            semantic_role="barrier",
        ),
        make_box(
            _next_id(counter),
            size_x=0.35,
            size_y=0.35,
            size_z=post_height,
            x=center_x + slab_length / 2.0 - 0.4,
            y=-(passage_width / 2.0 + 0.25),
            z=post_height / 2.0,
            support_mode="grounded",
            semantic_role="barrier",
        ),
    ]

    if sub_mode == "hazards":
        for side in (-1.0, 1.0):
            wire_length = workspace["size_z"] - clearance
            primitives.append(
                make_cylinder(
                    _next_id(counter),
                    radius=0.05,
                    height=wire_length,
                    x=center_x + side * 0.9,
                    y=side * 0.6,
                    z=workspace["size_z"] - wire_length / 2.0,
                    axis_mode="vertical",
                    support_mode="ceiling_attached",
                    semantic_role="overhead_hazard",
                )
            )

    if not all(_is_candidate_valid(primitive, [*existing, *[p for p in primitives if p is not primitive]], workspace, start, goal, clearance_xy=0.1) for primitive in primitives):
        return [], {
            "type": "low_clearance_passage",
            "clearance_height": clearance,
            "sub_mode": sub_mode,
            "skipped": True,
        }

    return primitives, {
        "type": "low_clearance_passage",
        "clearance_height": clearance,
        "sub_mode": sub_mode,
    }


def _template_perforated_barrier(
    workspace: Dict[str, float],
    rng: random.Random,
    counter: List[int],
    difficulty: float,
    corridor_width: Optional[float],
    panel_width: Optional[float],
    panel_height_override: Optional[float],
    thickness: Optional[float],
    hole_count: Optional[int],
    hole_shape_candidates: Optional[Sequence[str]],
    hole_margin_min: float,
    hole_spacing_min: float,
    placement_mode: Optional[str],
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
    existing: Sequence[PrimitiveSpec],
) -> Tuple[List[PrimitiveSpec], Dict[str, Any]]:
    hole_width = corridor_width if corridor_width is not None else max(0.9, 1.8 - 0.6 * difficulty)
    hole_height = max(0.8, workspace["flight_height_max"] - workspace["flight_height_min"] - 0.2)
    hole_center_z = (workspace["flight_height_min"] + workspace["flight_height_max"]) / 2.0
    panel_height = float(panel_height_override) if panel_height_override is not None else min(workspace["size_z"] - 0.2, workspace["flight_height_max"] + 1.0)
    panel_width = float(panel_width) if panel_width is not None else 3.0
    panel_thickness = float(thickness) if thickness is not None else 0.1
    if placement_mode == "route_adjacent":
        center_x, center_y = _sample_route_adjacent_center(rng, workspace, start, goal, margin_xy=3.0, lateral_span=2.5)
    else:
        center_x, center_y, _ = _uniform_pose(rng, workspace, margin_xy=3.0, z=0.0)
    shapes = list(hole_shape_candidates or ["rectangle"])
    desired_hole_count = max(1, int(hole_count or 1))
    holes = []
    if desired_hole_count == 1:
        shape = rng.choice(shapes)
        hole = {
            "shape": shape,
            "center_u": 0.0,
            "center_v": hole_center_z - panel_height / 2.0,
        }
        if shape == "circle":
            hole["radius"] = min(hole_width, hole_height) / 2.0
        else:
            hole["width"] = hole_width
            hole["height"] = hole_height
        holes.append(hole)
    else:
        centers_u = [-panel_width * 0.18, panel_width * 0.18]
        for center_u in centers_u[:desired_hole_count]:
            shape = rng.choice(shapes)
            hole = {
                "shape": shape,
                "center_u": center_u,
                "center_v": hole_center_z - panel_height / 2.0,
            }
            if shape == "circle":
                hole["radius"] = min(hole_width * 0.45, hole_height * 0.45)
            else:
                hole["width"] = hole_width * 0.85
                hole["height"] = hole_height
            holes.append(hole)
    primitive = make_perforated_slab(
        _next_id(counter),
        size_x=panel_width,
        size_y=panel_height,
        thickness=panel_thickness,
        x=center_x,
        y=center_y,
        z=panel_height / 2.0,
        slab_mode="vertical",
        holes=holes,
        edge_margin_min=hole_margin_min,
        hole_spacing_min=hole_spacing_min,
        support_mode="grounded",
        semantic_role="passable_panel",
    )
    if not _is_candidate_valid(primitive, existing, workspace, start, goal, clearance_xy=0.1):
        return [], {"type": "perforated_barrier", "hole_width": hole_width, "hole_height": hole_height, "skipped": True}
    return [primitive], {"type": "perforated_barrier", "hole_width": hole_width, "hole_height": hole_height}


def _make_motion(
    motion_type: str,
    speed_min: float,
    speed_max: float,
    trajectory_params: Dict[str, Any],
    seed: int,
) -> Dict[str, Any]:
    return {
        "motion_type": motion_type,
        "speed_min": speed_min,
        "speed_max": speed_max,
        "accel_limit": 2.0,
        "turn_rate_limit": 1.2,
        "pause_probability": 0.0,
        "trajectory_params": dict(trajectory_params),
        "seed": seed,
    }


def _template_moving_crossing(
    workspace: Dict[str, float],
    rng: random.Random,
    counter: List[int],
    difficulty: float,
    dynamic_ratio: float,
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
    existing: Sequence[PrimitiveSpec],
) -> Tuple[List[PrimitiveSpec], Dict[str, Any]]:
    dynamic_count = max(2, int(round(2 + 3 * max(difficulty, dynamic_ratio))))
    primitives: List[PrimitiveSpec] = []
    mid_height = (workspace["flight_height_min"] + workspace["flight_height_max"]) / 2.0
    static_primitives = [primitive for primitive in existing if not primitive.is_dynamic]
    for idx in range(dynamic_count):
        z = mid_height + rng.uniform(-0.15, 0.15)
        candidate_ys = np.linspace(-workspace["size_y"] / 3.0, workspace["size_y"] / 3.0, 11)
        rng.shuffle(candidate_ys)
        y = None
        for candidate_y in candidate_ys:
            if _lane_is_clear(float(candidate_y), z, -workspace["size_x"] / 3.0, workspace["size_x"] / 3.0, static_primitives):
                y = float(candidate_y)
                break
        if y is None:
            continue
        speed = rng.uniform(0.6, 1.4)
        if idx % 2 == 0:
            motion = _make_motion(
                "waypoint_patrol",
                speed_min=speed * 0.8,
                speed_max=speed,
                trajectory_params={
                    "waypoints": [
                        [-workspace["size_x"] / 3.0, y, z],
                        [workspace["size_x"] / 3.0, y, z],
                    ],
                    "loop": True,
                },
                seed=rng.randint(0, 10_000),
            )
            candidate = make_capsule(
                _next_id(counter),
                radius=0.18,
                segment_length=0.8,
                x=-workspace["size_x"] / 3.0,
                y=y,
                z=z,
                axis_mode="horizontal",
                semantic_role="moving_agent",
                motion=motion,
            )
            if _is_candidate_valid(candidate, [*existing, *primitives], workspace, start, goal, clearance_xy=0.2):
                primitives.append(candidate)
        else:
            motion = _make_motion(
                "random_walk",
                speed_min=speed * 0.6,
                speed_max=speed,
                trajectory_params={
                    "heading_resample_interval": 20,
                    "repulsion_gain": 1.0,
                },
                seed=rng.randint(0, 10_000),
            )
            candidate = make_sphere(
                _next_id(counter),
                radius=0.2,
                x=0.0,
                y=y,
                z=z,
                semantic_role="moving_disturbance",
                motion=motion,
            )
            if _is_candidate_valid(candidate, [*existing, *primitives], workspace, start, goal, clearance_xy=0.2):
                primitives.append(candidate)
    return primitives, {"type": "moving_crossing", "count": dynamic_count}


def _generate_template(
    template_cfg: Dict[str, Any],
    workspace: Dict[str, float],
    rng: random.Random,
    counter: List[int],
    difficulty: float,
    scene_config: Dict[str, Any],
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
    existing: Sequence[PrimitiveSpec],
) -> Tuple[List[PrimitiveSpec], List[Dict[str, Any]]]:
    template_type = template_cfg["type"]
    count = int(template_cfg.get("count", 1))
    scale = float(template_cfg.get("scale", 1.0))
    all_primitives: List[PrimitiveSpec] = []
    logs: List[Dict[str, Any]] = []

    for _ in range(count):
        current_existing = [*existing, *all_primitives]
        if template_type == "bottleneck":
            primitives, log = _template_bottleneck(
                workspace,
                rng,
                counter,
                difficulty,
                template_cfg.get("gap_width") or scene_config.get("corridor_width"),
                template_cfg.get("length_override"),
                template_cfg.get("placement_mode"),
                start,
                goal,
                current_existing,
            )
        elif template_type == "pillar_field":
            primitives, log = _template_pillar_field(
                workspace,
                rng,
                counter,
                difficulty,
                scene_config.get("obstacle_density"),
                scale,
                template_cfg.get("target_count"),
                start,
                goal,
                current_existing,
            )
        elif template_type == "box_field":
            primitives, log = _template_box_field(
                workspace,
                rng,
                counter,
                difficulty,
                scene_config.get("obstacle_density"),
                scale,
                template_cfg.get("target_count"),
                start,
                goal,
                current_existing,
            )
        elif template_type == "clutter_cluster":
            primitives, log = _template_clutter_cluster(
                workspace,
                rng,
                counter,
                difficulty,
                template_cfg.get("cluster_obstacle_count"),
                template_cfg.get("cluster_radius"),
                template_cfg.get("placement_mode"),
                start,
                goal,
                current_existing,
            )
        elif template_type == "slab_field":
            primitives, log = _template_slab_field(
                workspace,
                rng,
                counter,
                difficulty,
                scene_config.get("obstacle_density"),
                scale,
                template_cfg.get("target_count"),
                start,
                goal,
                current_existing,
            )
        elif template_type == "perforated_field":
            primitives, log = _template_perforated_field(
                workspace,
                rng,
                counter,
                difficulty,
                scene_config.get("obstacle_density"),
                scale,
                template_cfg.get("target_count"),
                start,
                goal,
                current_existing,
            )
        elif template_type == "low_clearance_passage":
            primitives, log = _template_low_clearance_passage(
                workspace,
                rng,
                counter,
                difficulty,
                scene_config.get("sub_mode"),
                start,
                goal,
                current_existing,
            )
        elif template_type == "perforated_barrier":
            primitives, log = _template_perforated_barrier(
                workspace,
                rng,
                counter,
                difficulty,
                template_cfg.get("corridor_width") or scene_config.get("corridor_width"),
                template_cfg.get("panel_width"),
                template_cfg.get("panel_height"),
                template_cfg.get("thickness"),
                template_cfg.get("hole_count"),
                template_cfg.get("hole_shape_candidates"),
                float(template_cfg.get("hole_margin_min", 0.2)),
                float(template_cfg.get("hole_spacing_min", 0.2)),
                template_cfg.get("placement_mode"),
                start,
                goal,
                current_existing,
            )
        elif template_type == "dynamic_field":
            primitives, log = _template_dynamic_field(
                workspace,
                rng,
                counter,
                difficulty,
                scene_config.get("dynamic_obstacle_ratio", 0.0),
                scale,
                template_cfg.get("target_count"),
                float(template_cfg.get("sphere_fraction", 0.5)),
                start,
                goal,
                current_existing,
            )
        elif template_type == "moving_crossing":
            primitives, log = _template_moving_crossing(
                workspace,
                rng,
                counter,
                difficulty,
                scene_config.get("dynamic_obstacle_ratio", 0.0),
                start,
                goal,
                current_existing,
            )
        else:
            raise ValueError(f"Unsupported template type: {template_type}")
        all_primitives.extend(primitives)
        logs.append(log)
    return all_primitives, logs


def generate_scene(scene_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a scene dictionary containing:
    - scene metadata
    - primitive list
    - template list
    - validation report
    """
    base_seed = int(scene_config.get("seed", 0))
    generator_rules = dict(scene_config.get("generator_rules", {}))
    retry_budget = int(generator_rules.get("scene_retry_budget", 20))
    occupancy_min, occupancy_max = generator_rules.get("target_occupancy_range", (0.03, 0.10))

    workspace = dict(scene_config["workspace"])
    cfg = ArenaConfig(
        size_x=workspace["size_x"],
        size_y=workspace["size_y"],
        size_z=workspace["size_z"],
        flight_height_min=workspace["flight_height_min"],
        flight_height_max=workspace["flight_height_max"],
    )
    start = tuple(scene_config.get("start") or _clamp_start_goal(cfg)[0])
    goal = tuple(scene_config.get("goal") or _clamp_start_goal(cfg)[1])
    difficulty = float(scene_config.get("difficulty", 0.5))

    last_scene: Optional[Dict[str, Any]] = None
    for attempt_idx in range(retry_budget):
        attempt_seed = base_seed + attempt_idx
        rng = random.Random(attempt_seed)
        counter = [1]
        all_primitives: List[PrimitiveSpec] = []
        template_logs: List[Dict[str, Any]] = []

        for template_cfg in scene_config.get("templates", []):
            primitives, logs = _generate_template(
                template_cfg,
                workspace,
                rng,
                counter,
                difficulty,
                scene_config,
                start,
                goal,
                all_primitives,
            )
            all_primitives.extend(primitives)
            template_logs.extend(logs)

        scene = {
            "scene_id": scene_config.get("scene_id", f"scene_{base_seed:04d}"),
            "seed": base_seed,
            "effective_seed": attempt_seed,
            "generation_attempt": attempt_idx,
            "workspace": workspace,
            "start": start,
            "goal": goal,
            "templates": list(scene_config.get("templates", [])),
            "template_log": template_logs,
            "generator_rules": generator_rules,
            "distribution_modes": copy.deepcopy(scene_config.get("distribution_modes", {})),
            "start_goal_rules": copy.deepcopy(scene_config.get("start_goal_rules", {})),
            "validation_rules": copy.deepcopy(scene_config.get("validation_rules", {})),
            "primitive_budget": copy.deepcopy(scene_config.get("primitive_budget", {})),
            "difficulty": difficulty,
            "scene_mode": scene_config.get("scene_mode", SceneMode.MIXED.value),
            "scene_family": scene_config.get("scene_family", scene_config.get("scene_mode", SceneMode.MIXED.value)),
            "scene_cfg_name": scene_config.get("scene_cfg_name"),
            "sub_mode": scene_config.get("sub_mode"),
            "corridor_width": scene_config.get("corridor_width"),
            "obstacle_density": scene_config.get("obstacle_density"),
            "dynamic_obstacle_ratio": scene_config.get("dynamic_obstacle_ratio", 0.0),
            "gravity_tilt_enabled": scene_config.get("gravity_tilt_enabled", True),
            "primitives": [_primitive_to_dict(primitive) for primitive in all_primitives],
        }

        validation = validate_scene(scene)
        primitive_counts = validation["primitive_counts"]

        estimated_min_gap = None
        for log in template_logs:
            for candidate_key in ("gap_width", "hole_width", "clearance_height"):
                if candidate_key in log:
                    value = log[candidate_key]
                    estimated_min_gap = value if estimated_min_gap is None else min(estimated_min_gap, value)

        static_occupancy = _approx_static_occupancy(all_primitives, workspace)
        gap_norm = 0.5 if estimated_min_gap is None else min(estimated_min_gap / 2.5, 1.0)
        complexity = min(
            1.0,
            static_occupancy * 3.5 +
            (1.0 - gap_norm) * 0.35 +
            validation["dynamic_obstacle_count"] * 0.08,
        )

        scene["metadata"] = {
            "primitive_counts": primitive_counts,
            "dynamic_obstacle_count": validation["dynamic_obstacle_count"],
            "traversable_hole_count": validation["traversable_hole_count"],
            "traversable_perforated_count": validation["traversable_perforated_count"],
            "validation_status": validation["valid"],
            "connectivity_status": validation["connectivity_status"],
            "start_goal_distance": validation["start_goal_distance"],
            "estimated_min_gap": estimated_min_gap,
            "complexity": complexity,
            "static_occupancy": static_occupancy,
        }
        scene["validation_report"] = validation
        last_scene = scene

        occupancy_ok = occupancy_min <= static_occupancy <= occupancy_max
        if validation["valid"] and occupancy_ok:
            return scene

    assert last_scene is not None
    last_scene["metadata"]["retry_exhausted"] = True
    return last_scene


def _euler_to_quaternion(roll: float, pitch: float, yaw: float) -> Tuple[float, float, float, float]:
    cr, sr = math.cos(roll / 2.0), math.sin(roll / 2.0)
    cp, sp = math.cos(pitch / 2.0), math.sin(pitch / 2.0)
    cy, sy = math.cos(yaw / 2.0), math.sin(yaw / 2.0)
    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy
    return (w, x, y, z)


def _primitive_color(primitive: PrimitiveSpec) -> Tuple[float, float, float]:
    if primitive.type == "box":
        return (0.92, 0.48, 0.18)
    if primitive.type == "cylinder":
        if primitive.is_dynamic:
            return (0.40, 0.82, 0.32)
        return (0.20, 0.55, 0.90)
    if primitive.type == "slab":
        if primitive.semantic_role == "overhead_hazard":
            return (0.82, 0.24, 0.24)
        return (0.78, 0.30, 0.52)
    if primitive.type == "perforated_slab":
        return (0.92, 0.78, 0.22)
    if primitive.type == "sphere":
        return (0.16, 0.78, 0.42)
    if primitive.type == "capsule":
        return (0.54, 0.86, 0.22)
    return (0.60, 0.60, 0.62)


def _rect_hole_bbox(hole: Dict[str, Any]) -> Tuple[float, float, float, float]:
    shape = hole["shape"]
    if shape == "circle":
        radius = hole["radius"]
        return (
            hole["center_u"] - radius,
            hole["center_u"] + radius,
            hole["center_v"] - radius,
            hole["center_v"] + radius,
        )
    return (
        hole["center_u"] - hole["width"] / 2.0,
        hole["center_u"] + hole["width"] / 2.0,
        hole["center_v"] - hole["height"] / 2.0,
        hole["center_v"] + hole["height"] / 2.0,
    )


def _spawn_segments_for_perforated_slab(primitive: PrimitiveSpec) -> List[SpawnObstacle]:
    g = primitive.geometry
    perforation = primitive.perforation or {}
    holes = perforation.get("holes", [])
    if not holes:
        base = _primitive_to_spawn_obstacle(primitive)
        return [base] if base is not None else []

    hole = holes[0]
    min_u, max_u, min_v, max_v = _rect_hole_bbox(hole)
    size_x = g["size_x"]
    size_y = g["size_y"]
    thickness = g["thickness"]
    px, py, pz = primitive.pose["x"], primitive.pose["y"], primitive.pose["z"]
    yaw = primitive.orientation.get("yaw", 0.0)

    segments: List[Tuple[float, float, float, float, float, float]] = []
    left_w = max(0.0, (size_x / 2.0) + min_u)
    right_w = max(0.0, (size_x / 2.0) - max_u)
    bottom_h = max(0.0, (size_y / 2.0) + min_v)
    top_h = max(0.0, (size_y / 2.0) - max_v)

    if left_w > 1e-6:
        segments.append((left_w, size_y, thickness, -size_x / 2.0 + left_w / 2.0, 0.0, 0.0))
    if right_w > 1e-6:
        segments.append((right_w, size_y, thickness, size_x / 2.0 - right_w / 2.0, 0.0, 0.0))
    if bottom_h > 1e-6:
        segments.append((max_u - min_u, bottom_h, thickness, (min_u + max_u) / 2.0, -size_y / 2.0 + bottom_h / 2.0, 0.0))
    if top_h > 1e-6:
        segments.append((max_u - min_u, top_h, thickness, (min_u + max_u) / 2.0, size_y / 2.0 - top_h / 2.0, 0.0))

    obstacles: List[SpawnObstacle] = []
    for idx, (sx, sy, sz, ox, oy, oz) in enumerate(segments):
        if sx <= 1e-6 or sy <= 1e-6 or sz <= 1e-6:
            continue
        if g["slab_mode"] == "vertical":
            obstacle = SpawnObstacle(
                prim_type="cube",
                position=(px + ox, py, pz + oy),
                scale=(sx / 2.0, thickness / 2.0, sy / 2.0),
                rotation=_euler_to_quaternion(0.0, 0.0, yaw),
                color=_primitive_color(primitive),
                is_dynamic=False,
                source_primitive_id=f"{primitive.id}_segment_{idx}",
            )
        else:
            obstacle = SpawnObstacle(
                prim_type="cube",
                position=(px + ox, py + oy, pz),
                scale=(sx / 2.0, sy / 2.0, thickness / 2.0),
                rotation=_euler_to_quaternion(0.0, 0.0, yaw),
                color=_primitive_color(primitive),
                is_dynamic=False,
                source_primitive_id=f"{primitive.id}_segment_{idx}",
            )
        obstacles.append(obstacle)
    return obstacles


def _primitive_to_spawn_obstacle(primitive: PrimitiveSpec) -> Optional[SpawnObstacle]:
    px, py, pz = primitive.pose["x"], primitive.pose["y"], primitive.pose["z"]
    yaw = primitive.orientation.get("yaw", 0.0)
    color = _primitive_color(primitive)
    motion = primitive.motion or {}
    is_hazard = primitive.semantic_role == "overhead_hazard"

    if primitive.type == "box":
        g = primitive.geometry
        return SpawnObstacle(
            prim_type="cube",
            position=(px, py, pz),
            scale=(g["size_x"] / 2.0, g["size_y"] / 2.0, g["size_z"] / 2.0),
            rotation=_euler_to_quaternion(0.0, 0.0, yaw),
            color=color,
            is_dynamic=primitive.is_dynamic,
            motion_type=motion.get("motion_type", "static"),
            motion_params=motion,
            is_hazard=is_hazard,
            source_primitive_id=primitive.id,
        )

    if primitive.type == "cylinder":
        g = primitive.geometry
        axis_mode = g.get("axis_mode", "vertical")
        if axis_mode == "vertical":
            rotation = _euler_to_quaternion(0.0, 0.0, yaw)
            scale = (g["radius"], g["radius"], g["height"] / 2.0)
        else:
            rotation = _euler_to_quaternion(0.0, math.pi / 2.0, yaw)
            scale = (g["radius"], g["radius"], g["height"] / 2.0)
        return SpawnObstacle(
            prim_type="cylinder",
            position=(px, py, pz),
            scale=scale,
            rotation=rotation,
            color=color,
            is_dynamic=primitive.is_dynamic,
            motion_type=motion.get("motion_type", "static"),
            motion_params=motion,
            is_hazard=is_hazard,
            source_primitive_id=primitive.id,
        )

    if primitive.type == "slab":
        g = primitive.geometry
        if g["slab_mode"] == "horizontal":
            scale = (g["size_x"] / 2.0, g["size_y"] / 2.0, g["thickness"] / 2.0)
            position = (px, py, pz)
        else:
            scale = (g["size_x"] / 2.0, g["thickness"] / 2.0, g["size_y"] / 2.0)
            position = (px, py, pz)
        return SpawnObstacle(
            prim_type="cube",
            position=position,
            scale=scale,
            rotation=_euler_to_quaternion(0.0, 0.0, yaw),
            color=color,
            is_dynamic=False,
            is_hazard=is_hazard,
            source_primitive_id=primitive.id,
        )

    if primitive.type == "perforated_slab":
        return None

    if primitive.type == "sphere":
        g = primitive.geometry
        return SpawnObstacle(
            prim_type="sphere",
            position=(px, py, pz),
            scale=(g["radius"], g["radius"], g["radius"]),
            color=color,
            is_dynamic=True,
            motion_type=motion.get("motion_type", "static"),
            motion_params=motion,
            source_primitive_id=primitive.id,
        )

    if primitive.type == "capsule":
        g = primitive.geometry
        axis_mode = g.get("axis_mode", "velocity_aligned")
        if axis_mode == "vertical":
            rotation = _euler_to_quaternion(0.0, 0.0, 0.0)
        else:
            rotation = _euler_to_quaternion(0.0, math.pi / 2.0, yaw)
        return SpawnObstacle(
            prim_type="cylinder",
            position=(px, py, pz),
            scale=(g["radius"], g["radius"], g["segment_length"] / 2.0 + g["radius"]),
            rotation=rotation,
            color=color,
            is_dynamic=True,
            motion_type=motion.get("motion_type", "static"),
            motion_params=motion,
            source_primitive_id=primitive.id,
        )
    return None


def _scene_primitives_from_scene(scene: Dict[str, Any]) -> List[PrimitiveSpec]:
    return [
        primitive if isinstance(primitive, PrimitiveSpec) else _primitive_from_dict(primitive)
        for primitive in scene["primitives"]
    ]


def _build_spawn_obstacles(primitives: Sequence[PrimitiveSpec]) -> List[SpawnObstacle]:
    obstacles: List[SpawnObstacle] = []
    for primitive in primitives:
        if primitive.type == "perforated_slab":
            obstacles.extend(_spawn_segments_for_perforated_slab(primitive))
            continue
        obstacle = _primitive_to_spawn_obstacle(primitive)
        if obstacle is not None:
            obstacles.append(obstacle)
    return obstacles


def make_scene_config_from_request(request: CREScenarioRequest, cfg: Optional[ArenaConfig] = None) -> Dict[str, Any]:
    if request.family in {SceneMode.NOMINAL, SceneMode.BOUNDARY_CRITICAL, SceneMode.SHIFTED}:
        scene_rules = load_scene_family_config(request.family)
        if cfg is not None:
            workspace = scene_rules.setdefault("workspace", {})
            workspace["size_x"] = cfg.size_x
            workspace["size_y"] = cfg.size_y
            workspace["size_z"] = cfg.size_z
            workspace["flight_height_min"] = cfg.flight_height_min
            workspace["flight_height_max"] = cfg.flight_height_max
        return compile_scene_config_from_rules(
            scene_rules,
            seed=request.seed,
            difficulty=request.difficulty,
            gravity_tilt_enabled=request.gravity_tilt_enabled,
        )

    cfg = cfg or ArenaConfig()
    start, goal = _clamp_start_goal(cfg)
    difficulty = max(0.0, min(1.0, request.difficulty))
    retry_budget = 32
    scene_mode = CREScenarioFamily.MIXED.value
    sub_mode = None
    corridor_width = None
    templates, obstacle_density, dynamic_ratio = _build_navrl_mixed_templates(
        seed=int(request.seed or 0),
        difficulty=difficulty,
        obstacle_density=request.obstacle_density,
        dynamic_ratio=request.dynamic_obstacle_ratio,
    )
    target_occupancy_range = (
        0.012,
        min(0.058, 0.036 + 0.022 * obstacle_density),
    )

    return {
        "scene_id": f"{scene_mode}_{request.seed or 0:04d}",
        "seed": int(request.seed or 0),
        "workspace": cfg.to_workspace(),
        "start": start,
        "goal": goal,
        "difficulty": difficulty,
        "scene_mode": scene_mode,
        "sub_mode": sub_mode,
        "corridor_width": corridor_width,
        "obstacle_density": obstacle_density,
        "dynamic_obstacle_ratio": dynamic_ratio,
        "gravity_tilt_enabled": request.gravity_tilt_enabled,
        "templates": templates,
        "primitive_budget": {
            "box": [0, 256],
            "cylinder": [0, 256],
            "slab": [0, 64],
            "perforated_slab": [0, 64],
            "sphere": [0, 64],
            "capsule": [0, 64],
        },
        "generator_rules": {
            "allow_floating_static": True,
            "allow_dynamic_obstacles": True,
            "enforce_connectivity": True,
            "max_overlap_tolerance": 0.0,
            "scene_retry_budget": retry_budget,
            "target_occupancy_range": target_occupancy_range,
        },
    }


class EnvPrimitiveGenerator:
    """
    Compatibility wrapper used by test_flight.py.
    """

    def __init__(self, cfg: Optional[ArenaConfig] = None, seed: Optional[int] = None):
        self.cfg = cfg or ArenaConfig()
        self.seed = seed
        self._current_result: Optional[GeneratedSceneResult] = None
        self._current_primitives: List[PrimitiveSpec] = []
        self._runtime_state: Dict[str, Dict[str, Any]] = {}

    def reset(self, scene_config: Dict[str, Any]) -> GeneratedSceneResult:
        scene = generate_scene(scene_config)
        primitives = _scene_primitives_from_scene(scene)
        validation = scene["validation_report"]

        if scene.get("gravity_tilt_enabled", True):
            rng = random.Random(scene["seed"])
            max_angle = math.radians(self.cfg.max_tilt_angle)
            roll = rng.uniform(-max_angle, max_angle)
            pitch = rng.uniform(-max_angle, max_angle)
            gravity_tilt_quat = _euler_to_quaternion(roll, pitch, 0.0)
            gravity_tilt_euler = (math.degrees(roll), math.degrees(pitch))
        else:
            gravity_tilt_quat = (1.0, 0.0, 0.0, 0.0)
            gravity_tilt_euler = (0.0, 0.0)

        obstacles = _build_spawn_obstacles(primitives)
        scene_tags = {
            "scene_id": scene["scene_id"],
            "family": scene.get("scene_family", scene["scene_mode"]),
            "scene_cfg_name": scene.get("scene_cfg_name"),
            "seed": scene["seed"],
            "difficulty": scene["difficulty"],
            "sub_mode": scene.get("sub_mode"),
            "template_count": len(scene["templates"]),
            "connectivity_status": scene["metadata"]["connectivity_status"],
        }
        metadata = CREScenarioMetadata(
            family=scene.get("scene_family", scene["scene_mode"]),
            seed=scene["seed"],
            requested_difficulty=scene["difficulty"],
            realized_mode=scene["scene_mode"],
            realized_sub_mode=scene.get("sub_mode"),
            scene_tags=scene_tags,
            estimated_min_gap=scene["metadata"]["estimated_min_gap"],
            obstacle_count=len(obstacles),
            static_obstacle_count=sum(not obstacle.is_dynamic for obstacle in obstacles),
            dynamic_obstacle_count=sum(obstacle.is_dynamic for obstacle in obstacles),
            requires_vertical_flight=scene["scene_mode"] == CREScenarioFamily.VERTICAL_CONSTRAINT.value or scene.get("sub_mode") == "vertical",
            gravity_tilt_enabled=scene.get("gravity_tilt_enabled", True),
            solvable=bool(validation["navigation_valid"]),
            complexity=float(scene["metadata"]["complexity"]),
        )
        labels = SceneLabels(
            local_start=tuple(scene["start"]),
            local_goal=tuple(scene["goal"]),
            requires_vertical_flight=metadata.requires_vertical_flight,
            gravity_tilt=gravity_tilt_euler,
        )

        result = GeneratedSceneResult(
            scene=scene,
            mode=SceneMode(scene["scene_mode"]),
            sub_mode=scene.get("sub_mode"),
            difficulty=scene["difficulty"],
            obstacles=obstacles,
            labels=labels,
            gravity_tilt_quat=gravity_tilt_quat,
            gravity_tilt_euler=gravity_tilt_euler,
            solvable=validation["navigation_valid"],
            complexity=scene["metadata"]["complexity"],
            cre_metadata=metadata,
        )
        self._current_result = result
        self._current_primitives = primitives
        self._runtime_state = self._initialize_runtime_state(primitives, scene["workspace"], scene["seed"])
        return result

    def generate_from_request(self, request: CREScenarioRequest) -> GeneratedSceneResult:
        config = make_scene_config_from_request(request, self.cfg)
        return self.reset(config)

    def generate_from_scene_rules(
        self,
        scene_rules: Dict[str, Any],
        seed: Optional[int] = None,
        difficulty: float = 0.5,
        gravity_tilt_enabled: Optional[bool] = None,
    ) -> GeneratedSceneResult:
        config = compile_scene_config_from_rules(
            scene_rules=scene_rules,
            seed=seed,
            difficulty=difficulty,
            gravity_tilt_enabled=gravity_tilt_enabled,
        )
        return self.reset(config)

    def generate_from_scene_family(
        self,
        scene_family: str | SceneMode,
        seed: Optional[int] = None,
        difficulty: float = 0.5,
        gravity_tilt_enabled: Optional[bool] = None,
    ) -> GeneratedSceneResult:
        scene_rules = load_scene_family_config(scene_family)
        if self.cfg is not None:
            workspace = scene_rules.setdefault("workspace", {})
            workspace["size_x"] = self.cfg.size_x
            workspace["size_y"] = self.cfg.size_y
            workspace["size_z"] = self.cfg.size_z
            workspace["flight_height_min"] = self.cfg.flight_height_min
            workspace["flight_height_max"] = self.cfg.flight_height_max
        return self.generate_from_scene_rules(
            scene_rules=scene_rules,
            seed=seed,
            difficulty=difficulty,
            gravity_tilt_enabled=gravity_tilt_enabled,
        )

    def summarize_result(self, result: GeneratedSceneResult) -> Dict[str, Any]:
        return {
            "mode": result.mode.value,
            "sub_mode": result.sub_mode,
            "difficulty": result.difficulty,
            "solvable": result.solvable,
            "complexity": result.complexity,
            "obstacle_count": len(result.obstacles),
            "dynamic_obstacle_count": sum(obstacle.is_dynamic for obstacle in result.obstacles),
            "estimated_min_gap": result.cre_metadata.estimated_min_gap,
            "gravity_tilt": result.gravity_tilt_euler,
            "scene_tags": dict(result.cre_metadata.scene_tags),
        }

    def _initialize_runtime_state(
        self,
        primitives: Sequence[PrimitiveSpec],
        workspace: Dict[str, Any],
        seed: int,
    ) -> Dict[str, Dict[str, Any]]:
        state: Dict[str, Dict[str, Any]] = {}
        for primitive in primitives:
            if not primitive.is_dynamic:
                continue
            motion = primitive.motion or {}
            trajectory = motion.get("trajectory_params", {})
            state[primitive.id] = {
                "rng": random.Random(motion.get("seed", seed)),
                "waypoint_idx": 0,
                "heading": 0.0,
                "workspace": workspace,
                "trajectory": trajectory,
            }
        return state

    def update_dynamic_obstacles(self, dt: float) -> List[Tuple[float, float, float]]:
        if self._current_result is None:
            return []

        for primitive in self._current_primitives:
            if not primitive.is_dynamic or not primitive.motion:
                continue
            runtime = self._runtime_state[primitive.id]
            motion = primitive.motion
            speed = (motion["speed_min"] + motion["speed_max"]) / 2.0
            motion_type = motion["motion_type"]
            workspace = runtime["workspace"]
            others = [other for other in self._current_primitives if other.id != primitive.id]
            hx, hy, hz = _aabb_half_extents(primitive)

            def clamp_candidate(candidate: Tuple[float, float, float]) -> Tuple[float, float, float]:
                x, y, z = candidate
                margin_xy = 0.2
                x = max(-workspace["size_x"] / 2.0 + hx + margin_xy, min(workspace["size_x"] / 2.0 - hx - margin_xy, x))
                y = max(-workspace["size_y"] / 2.0 + hy + margin_xy, min(workspace["size_y"] / 2.0 - hy - margin_xy, y))
                z = max(hz + 0.05, min(workspace["size_z"] - hz - 0.05, z))
                return (x, y, z)

            def candidate_is_free(candidate: Tuple[float, float, float]) -> Optional[Tuple[float, float, float]]:
                candidate = clamp_candidate(candidate)
                moved = PrimitiveSpec(
                    id=primitive.id,
                    type=primitive.type,
                    semantic_role=primitive.semantic_role,
                    geometry=dict(primitive.geometry),
                    pose=_normalize_pose(*candidate),
                    orientation=dict(primitive.orientation),
                    support_mode=primitive.support_mode,
                    is_dynamic=primitive.is_dynamic,
                    motion=None if primitive.motion is None else dict(primitive.motion),
                    perforation=None if primitive.perforation is None else dict(primitive.perforation),
                    metadata=dict(primitive.metadata),
                )
                if not validate_primitive(moved, workspace)["valid"]:
                    return None
                if _candidate_pose_intersects(primitive, candidate, others, margin_xy=0.15, margin_z=0.05):
                    return None
                return candidate

            if motion_type in {"waypoint_patrol", "lane_patrol"}:
                waypoint_key = "waypoints" if motion_type == "waypoint_patrol" else "path_points"
                points = motion["trajectory_params"][waypoint_key]
                idx = runtime["waypoint_idx"]
                target = points[idx]
                current = np.array([primitive.pose["x"], primitive.pose["y"], primitive.pose["z"]], dtype=float)
                target_vec = np.array(target, dtype=float) - current
                distance = float(np.linalg.norm(target_vec))
                if distance < 1e-5:
                    runtime["waypoint_idx"] = (idx + 1) % len(points)
                else:
                    step = min(distance, speed * dt)
                    direction = target_vec / max(distance, 1e-6)
                    candidate = tuple((current + direction * step).tolist())
                    free_candidate = candidate_is_free(candidate)
                    if free_candidate is None:
                        if len(points) > 1:
                            runtime["waypoint_idx"] = (idx - 1) % len(points)
                        continue
                    primitive.pose = _normalize_pose(*free_candidate)
                    if step >= distance - 1e-5:
                        runtime["waypoint_idx"] = (idx + 1) % len(points)

            elif motion_type == "random_walk":
                rng = runtime["rng"]
                interval = max(1, int(motion["trajectory_params"].get("heading_resample_interval", 20)))
                runtime["step_count"] = runtime.get("step_count", 0) + 1
                if runtime["step_count"] % interval == 1:
                    runtime["heading"] = rng.uniform(-math.pi, math.pi)

                trial_headings = [
                    runtime["heading"],
                    math.pi - runtime["heading"],
                    -runtime["heading"],
                    runtime["heading"] + rng.uniform(-math.pi / 2.0, math.pi / 2.0),
                ]
                for heading in trial_headings:
                    dx = math.cos(heading) * speed * dt
                    dy = math.sin(heading) * speed * dt
                    candidate = (
                        primitive.pose["x"] + dx,
                        primitive.pose["y"] + dy,
                        primitive.pose["z"],
                    )
                    free_candidate = candidate_is_free(candidate)
                    if free_candidate is None:
                        continue
                    runtime["heading"] = heading
                    primitive.pose = _normalize_pose(*free_candidate)
                    break

        self._current_result.obstacles = _build_spawn_obstacles(self._current_primitives)
        return [obstacle.position for obstacle in self._current_result.obstacles]


class ArenaSpawner:
    """
    Isaac Sim scene spawner with the same surface API as the older arena spawner.
    """

    def __init__(self, stage, base_path: str = "/World/Scene"):
        self.stage = stage
        self.base_path = base_path
        self.spawned_prims: List[str] = []

    def clear(self):
        for prim_path in self.spawned_prims:
            prim = self.stage.GetPrimAtPath(prim_path)
            if prim.IsValid():
                self.stage.RemovePrim(prim_path)
        self.spawned_prims = []

    def spawn(self, result: GeneratedSceneResult) -> List[str]:
        from pxr import Gf, UsdGeom, UsdPhysics

        self.clear()
        root = UsdGeom.Xform.Define(self.stage, self.base_path)
        xform = UsdGeom.Xformable(root.GetPrim())
        xform.ClearXformOpOrder()
        q = result.gravity_tilt_quat
        if q != (1.0, 0.0, 0.0, 0.0):
            xform.AddOrientOp().Set(Gf.Quatf(q[0], q[1], q[2], q[3]))

        for index, obstacle in enumerate(result.obstacles):
            prim_path = f"{self.base_path}/obstacle_{index}"
            if obstacle.prim_type == "cube":
                prim = UsdGeom.Cube.Define(self.stage, prim_path)
            elif obstacle.prim_type == "cylinder":
                prim = UsdGeom.Cylinder.Define(self.stage, prim_path)
            elif obstacle.prim_type == "sphere":
                prim = UsdGeom.Sphere.Define(self.stage, prim_path)
            else:
                continue

            UsdPhysics.CollisionAPI.Apply(prim.GetPrim())
            xf = UsdGeom.Xformable(prim.GetPrim())
            xf.ClearXformOpOrder()
            xf.AddTranslateOp().Set(Gf.Vec3d(*obstacle.position))
            if obstacle.rotation != (1.0, 0.0, 0.0, 0.0):
                xf.AddOrientOp().Set(Gf.Quatf(*obstacle.rotation))
            xf.AddScaleOp().Set(Gf.Vec3d(*obstacle.scale))
            if hasattr(prim, "GetDisplayColorAttr"):
                prim.GetDisplayColorAttr().Set([obstacle.color])
            self.spawned_prims.append(prim_path)
        return self.spawned_prims

    def update_positions(self, positions: List[Tuple[float, float, float]]):
        from pxr import Gf, UsdGeom

        for prim_path, position in zip(self.spawned_prims, positions):
            prim = self.stage.GetPrimAtPath(prim_path)
            if not prim.IsValid():
                continue
            xf = UsdGeom.Xformable(prim)
            translate_op = None
            for op in xf.GetOrderedXformOps():
                if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
                    translate_op = op
                    break
            if translate_op is None:
                translate_op = xf.AddTranslateOp()
            translate_op.Set(Gf.Vec3d(*position))


UniversalArenaGenerator = EnvPrimitiveGenerator
