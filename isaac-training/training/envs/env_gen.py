"""
Spec-aligned environment primitive generator for CRE Phase 1.

This module implements a pure-Python obstacle scene generator based on
`doc/specs/Env_Primitive_Spec_v0.md` and also exposes a thin runtime adapter
for the existing Isaac flight visualization harness.
"""

from __future__ import annotations

import json
import math
import random
from collections import deque
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np


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
    validation_status = geometry_valid and len(overlap_errors) == 0 and connectivity_valid

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
        "geometry_valid": geometry_valid,
        "workspace_valid": all("workspace" not in err for report in primitive_reports for err in report["errors"]),
        "overlap_valid": len(overlap_errors) == 0,
        "navigation_valid": connectivity_valid,
        "connectivity_status": "connected" if connectivity_valid else "disconnected",
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


def _template_bottleneck(
    workspace: Dict[str, float],
    rng: random.Random,
    counter: List[int],
    difficulty: float,
    gap_width: Optional[float],
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
    existing: Sequence[PrimitiveSpec],
) -> Tuple[List[PrimitiveSpec], Dict[str, Any]]:
    gap = gap_width if gap_width is not None else max(1.0, 2.4 - 1.0 * difficulty)
    slab_length = 1.8 + 1.2 * difficulty
    thickness = 0.4
    wall_height = min(workspace["size_z"] - 0.2, _sample_navrl_height(rng, workspace))
    center_x = rng.uniform(-workspace["size_x"] / 6.0, workspace["size_x"] / 6.0)
    left_y = -(gap / 2.0 + slab_length / 2.0)
    right_y = +(gap / 2.0 + slab_length / 2.0)

    primitives = [
        make_box(
            _next_id(counter),
            size_x=thickness,
            size_y=slab_length,
            size_z=wall_height,
            x=center_x,
            y=left_y,
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
            y=right_y,
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
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
    existing: Sequence[PrimitiveSpec],
) -> Tuple[List[PrimitiveSpec], Dict[str, Any]]:
    density = difficulty if obstacle_density is None else max(difficulty, obstacle_density)
    count = int(16 + density * 24)
    primitives: List[PrimitiveSpec] = []
    for _ in range(count):
        radius = rng.uniform(0.2, 0.5)
        height = _sample_navrl_height(rng, workspace)

        def make_candidate():
            x, y, _ = _uniform_pose(rng, workspace, margin_xy=2.0, z=0.0)
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


def _template_clutter_cluster(
    workspace: Dict[str, float],
    rng: random.Random,
    counter: List[int],
    difficulty: float,
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
    existing: Sequence[PrimitiveSpec],
) -> Tuple[List[PrimitiveSpec], Dict[str, Any]]:
    count = int(4 + difficulty * 6)
    center_x = rng.uniform(-workspace["size_x"] / 3.0, workspace["size_x"] / 3.0)
    center_y = rng.uniform(-workspace["size_y"] / 3.0, workspace["size_y"] / 3.0)
    primitives: List[PrimitiveSpec] = []
    for _ in range(count):
        def make_candidate():
            offset_x = rng.uniform(-2.2, 2.2)
            offset_y = rng.uniform(-2.2, 2.2)
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
            radius = rng.uniform(0.2, 0.45)
            height = rng.choice([1.0, 1.5, 2.0])
            return make_cylinder(
                _next_id(counter),
                radius=radius,
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
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
    existing: Sequence[PrimitiveSpec],
) -> Tuple[List[PrimitiveSpec], Dict[str, Any]]:
    hole_width = corridor_width if corridor_width is not None else max(0.9, 1.8 - 0.6 * difficulty)
    hole_height = max(0.8, workspace["flight_height_max"] - workspace["flight_height_min"] - 0.2)
    hole_center_z = (workspace["flight_height_min"] + workspace["flight_height_max"]) / 2.0
    panel_height = min(workspace["size_z"] - 0.2, workspace["flight_height_max"] + 1.0)
    panel_width = 3.0
    center_x = rng.uniform(-workspace["size_x"] / 8.0, workspace["size_x"] / 8.0)
    holes = [
        {
            "shape": "rectangle",
            "center_u": 0.0,
            "center_v": hole_center_z - panel_height / 2.0,
            "width": hole_width,
            "height": hole_height,
        }
    ]
    primitive = make_perforated_slab(
        _next_id(counter),
        size_x=panel_width,
        size_y=panel_height,
        thickness=0.1,
        x=center_x,
        y=0.0,
        z=panel_height / 2.0,
        slab_mode="vertical",
        holes=holes,
        edge_margin_min=0.2,
        hole_spacing_min=0.2,
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
    all_primitives: List[PrimitiveSpec] = []
    logs: List[Dict[str, Any]] = []

    for _ in range(count):
        if template_type == "bottleneck":
            primitives, log = _template_bottleneck(
                workspace,
                rng,
                counter,
                difficulty,
                template_cfg.get("gap_width") or scene_config.get("corridor_width"),
                start,
                goal,
                existing,
            )
        elif template_type == "pillar_field":
            primitives, log = _template_pillar_field(
                workspace,
                rng,
                counter,
                difficulty,
                scene_config.get("obstacle_density"),
                start,
                goal,
                existing,
            )
        elif template_type == "clutter_cluster":
            primitives, log = _template_clutter_cluster(workspace, rng, counter, difficulty, start, goal, existing)
        elif template_type == "low_clearance_passage":
            primitives, log = _template_low_clearance_passage(
                workspace,
                rng,
                counter,
                difficulty,
                scene_config.get("sub_mode"),
                start,
                goal,
                existing,
            )
        elif template_type == "perforated_barrier":
            primitives, log = _template_perforated_barrier(
                workspace,
                rng,
                counter,
                difficulty,
                scene_config.get("corridor_width"),
                start,
                goal,
                existing,
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
                existing,
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
            "difficulty": difficulty,
            "scene_mode": scene_config.get("scene_mode", SceneMode.MIXED.value),
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
            "validation_status": validation["valid"],
            "connectivity_status": validation["connectivity_status"],
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
    role = primitive.semantic_role
    if role == "bottleneck_boundary":
        return (0.55, 0.45, 0.3)
    if role == "overhead_hazard":
        return (0.7, 0.35, 0.25)
    if primitive.type in {"sphere", "capsule"}:
        return (0.25, 0.75, 0.35)
    if primitive.type == "perforated_slab":
        return (0.55, 0.6, 0.75)
    return (0.55, 0.55, 0.58)


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
    cfg = cfg or ArenaConfig()
    start, goal = _clamp_start_goal(cfg)
    difficulty = max(0.0, min(1.0, request.difficulty))
    obstacle_density = request.obstacle_density
    corridor_width = request.corridor_width
    dynamic_ratio = request.dynamic_obstacle_ratio
    retry_budget = 24
    target_occupancy_range = (0.008, 0.03)

    templates: List[Dict[str, Any]]
    scene_mode = request.family.value
    sub_mode = request.sub_mode

    if request.family == CREScenarioFamily.OPEN:
        if obstacle_density is None:
            obstacle_density = 0.35 + 0.45 * difficulty
        templates = [
            {"type": "pillar_field", "count": 2},
            {"type": "clutter_cluster", "count": 1},
        ]
        target_occupancy_range = (0.010, 0.040)
    elif request.family == CREScenarioFamily.NARROW_CORRIDOR:
        if corridor_width is None:
            corridor_width = max(0.9, 1.8 - 0.7 * difficulty)
        if sub_mode == "vertical":
            templates = [{"type": "perforated_barrier", "count": 1}]
        elif sub_mode == "sloped":
            templates = [{"type": "low_clearance_passage", "count": 1}]
        else:
            templates = [{"type": "bottleneck", "count": 1}]
        target_occupancy_range = (0.001, 0.015)
    elif request.family == CREScenarioFamily.VERTICAL_CONSTRAINT:
        templates = [{"type": "low_clearance_passage", "count": 1}]
        if sub_mode == "hazards":
            # hazard mode is realized by the sub_mode flag inside the low-clearance template
            pass
        target_occupancy_range = (0.002, 0.02)
    elif request.family == CREScenarioFamily.DYNAMIC_STRESS:
        if obstacle_density is None:
            obstacle_density = 0.30 + 0.40 * difficulty
        if dynamic_ratio <= 0.0:
            dynamic_ratio = max(0.5, difficulty)
        templates = [
            {"type": "pillar_field", "count": 1},
            {"type": "moving_crossing", "count": 1},
        ]
        target_occupancy_range = (0.004, 0.02)
    else:
        if obstacle_density is None:
            obstacle_density = 0.35 + 0.40 * difficulty
        if dynamic_ratio <= 0.0:
            dynamic_ratio = max(0.35, difficulty * 0.8)
        templates = [
            {"type": "pillar_field", "count": 1},
            {"type": "clutter_cluster", "count": 1},
            {"type": "bottleneck", "count": 1},
            {"type": "moving_crossing", "count": 1},
        ]
        target_occupancy_range = (0.008, 0.035)

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
            "box": [0, 12],
            "cylinder": [0, 20],
            "slab": [0, 4],
            "perforated_slab": [0, 2],
            "sphere": [0, 4],
            "capsule": [0, 4],
        },
        "generator_rules": {
            "allow_floating_static": True,
            "allow_dynamic_obstacles": request.family in {CREScenarioFamily.DYNAMIC_STRESS, CREScenarioFamily.MIXED},
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
            "family": scene["scene_mode"],
            "seed": scene["seed"],
            "difficulty": scene["difficulty"],
            "sub_mode": scene.get("sub_mode"),
            "template_count": len(scene["templates"]),
            "connectivity_status": scene["metadata"]["connectivity_status"],
        }
        metadata = CREScenarioMetadata(
            family=scene["scene_mode"],
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
