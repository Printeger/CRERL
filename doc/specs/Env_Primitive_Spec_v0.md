# Env Primitive Spec v0
**Project:** CRE-based Generic Obstacle-Avoidance Environment Generator  
**Version:** v0.1  
**Status:** Draft for implementation  
**Target use:** generic obstacle-avoidance RL with constrained flight-height band  
**Primary language:** Python  
**Primary style:** geometry-first, compositional, reproducible

---

# 1. Purpose

This document specifies a minimal but extensible primitive library for generic obstacle-avoidance environments.

The design goals are:

1. support procedurally generated obstacle fields for RL training and evaluation;
2. allow controlled variation in geometry, orientation, support mode, passability, and motion;
3. support static and dynamic obstacles under a unified interface;
4. make environment generation auditable and reproducible;
5. provide enough structure for later CRE analysis:
   - C--R inconsistency,
   - E--C inconsistency,
   - E--R inconsistency.

This specification is intended for implementation, not for final paper writing.

---

# 2. Scope and Assumptions

## 2.1 Environment scope
The environment is a **generic obstacle-avoidance scene**, not a semantic indoor reconstruction task.

The space contains:
- static obstacles,
- optional dynamic obstacles,
- optional passable structures such as perforated slabs,
- bounded workspace,
- constrained UAV flight-height band.

## 2.2 Dynamics scope
This spec covers only **environment geometry and obstacle behavior**, not UAV control dynamics.

UAV state/action/dynamics are handled in the main environment spec.

## 2.3 Vertical abstraction
The environment is assumed to be **2.5D**:
- the UAV operates in 3D coordinates,
- but altitude may be constrained to a limited band,
- so vertical clearance matters,
- while full aerobatic flight is not the primary target.

---

# 3. Design Principles

## 3.1 Primitive-first generation
All environments are constructed from a small set of reusable primitives.

## 3.2 Shape is not enough
Each primitive must include:
- geometry,
- pose,
- orientation,
- support mode,
- dynamic/static status,
- optional passability attributes,
- semantic role.

## 3.3 Composition over realism
The objective is not photo-realism.  
The objective is to generate **controllable and analyzable geometry**.

## 3.4 Reproducibility
Every generated environment must be reproducible from:
- a global scene seed,
- primitive-level seeds when needed,
- a fully serializable config.

---

# 4. Primitive Taxonomy

The v0 primitive library contains the following primitive classes.

## 4.1 Static primitives
1. `box`
2. `cylinder`
3. `slab`
4. `perforated_slab` (specialized slab with holes)

## 4.2 Dynamic primitives
5. `sphere`
6. `capsule`

## 4.3 Planned future primitives
Not included in v0, but interface should not block later addition:
- ellipsoid
- wedge / triangular prism
- articulated multi-part obstacle
- mesh-backed semantic object

---

# 5. Unified Primitive Object Model

Each primitive is represented as a structured object:

```python
primitive = {
    "id": "primitive_0001",
    "type": "box",
    "semantic_role": "barrier",
    "geometry": {...},
    "pose": {...},
    "orientation": {...},
    "support_mode": "grounded",
    "is_dynamic": False,
    "motion": None,
    "perforation": None,
    "material": None,
    "tags": [],
    "spawn_rule": None,
    "metadata": {}
}
```

## 5.1 Required top-level fields

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | str | yes | unique primitive identifier |
| `type` | str | yes | primitive type |
| `semantic_role` | str | yes | functional role in scene |
| `geometry` | dict | yes | size/shape parameters |
| `pose` | dict | yes | position |
| `orientation` | dict | yes | rotation |
| `support_mode` | str | yes | placement/support category |
| `is_dynamic` | bool | yes | static vs dynamic |
| `motion` | dict or null | yes | motion model if dynamic |
| `perforation` | dict or null | yes | hole config if perforated |
| `metadata` | dict | yes | implementation-specific extras |

## 5.2 Allowed semantic roles

Initial controlled vocabulary:

- `barrier`
- `pillar`
- `clutter`
- `bottleneck_boundary`
- `overhead_hazard`
- `moving_agent`
- `moving_disturbance`
- `passable_panel`
- `navigation_gate`
- `occluder`

This field is for analysis, visualization, and rule-based generation.

---

# 6. Coordinate System and Pose Convention

## 6.1 Coordinate system
Use a right-handed world frame:
- `x, y`: horizontal plane
- `z`: vertical axis

## 6.2 Pose
Primitive pose is given by its center:
```python
pose = {
    "x": float,
    "y": float,
    "z": float
}
```

## 6.3 Orientation
Use Euler angles in radians:
```python
orientation = {
    "roll": float,
    "pitch": float,
    "yaw": float
}
```

## 6.4 v0 orientation restriction
To reduce complexity in v0:

- `box`: yaw rotation only
- `cylinder`: vertical by default; horizontal optional
- `slab`: either vertical or horizontal; yaw optional
- `perforated_slab`: same as slab
- `sphere`: orientation ignored
- `capsule`: velocity-aligned or axis-aligned

Arbitrary full 3D rotation is not required in v0.

---

# 7. Support Modes

Each primitive must declare one support mode:

- `grounded`
- `ceiling_attached`
- `floating`
- `wall_attached`
- `free_moving`

## 7.1 Meaning

### grounded
Primitive touches or starts from the floor.

### ceiling_attached
Primitive is attached downward from the ceiling.

### floating
Primitive is statically placed in mid-air.

### wall_attached
Primitive is attached to a side boundary or partition.

### free_moving
Primitive is dynamic and not attached to static boundaries.

---

# 8. Primitive Definitions

## 8.1 Box

### Meaning
Axis-aligned or yaw-rotated cuboid obstacle.

### Geometry schema
```python
geometry = {
    "size_x": float,
    "size_y": float,
    "size_z": float
}
```

### Typical uses
- block obstacle
- barrier segment
- bottleneck boundary
- clutter block
- long wall-like obstacle

### v0 constraints
- all sizes must be positive
- `size_z` may be full-height or partial-height
- roll/pitch default to 0

---

## 8.2 Cylinder

### Meaning
Circular cylinder obstacle.

### Geometry schema
```python
geometry = {
    "radius": float,
    "height": float,
    "axis_mode": "vertical"  # or "horizontal"
}
```

### Typical uses
- pillar
- thin vertical obstacle
- hanging rod
- sparse round obstacle

### v0 constraints
- `axis_mode="vertical"` is the default and recommended mode
- horizontal cylinders are allowed but optional in v0

---

## 8.3 Slab

### Meaning
Thin rectangular plate.

### Geometry schema
```python
geometry = {
    "size_x": float,
    "size_y": float,
    "thickness": float,
    "slab_mode": "vertical"  # or "horizontal"
}
```

### Typical uses
- wall panel
- low ceiling
- overhead beam
- mid-air panel
- pass-through blocker

### v0 constraints
- thickness should be much smaller than the other two dimensions
- `slab_mode` must be explicit

---

## 8.4 Perforated Slab

### Meaning
Thin plate with one or more holes that may be traversable.

### Geometry schema
```python
geometry = {
    "size_x": float,
    "size_y": float,
    "thickness": float,
    "slab_mode": "vertical"  # or "horizontal"
}
```

### Perforation schema
```python
perforation = {
    "enabled": True,
    "hole_count": int,
    "hole_shape": "circle",   # or "rectangle"
    "holes": [
        {
            "shape": "circle",
            "center_u": float,
            "center_v": float,
            "radius": float
        },
        {
            "shape": "rectangle",
            "center_u": float,
            "center_v": float,
            "width": float,
            "height": float
        }
    ],
    "edge_margin_min": float,
    "hole_spacing_min": float
}
```

### Local slab coordinates
Use local 2D coordinates `(u, v)` on the slab surface for hole placement.

### Typical uses
- pass-through panel
- choice gate
- barrier with optional traversal route

### Passability rule
A hole is **nominally traversable** only if it satisfies the UAV clearance condition.

For UAV effective safety radius `r_u` and extra margin `m_s`:

#### Circle hole
\[
r_{\text{hole}} \ge r_u + m_s
\]

#### Rectangular hole
\[
w_{\text{hole}} \ge 2(r_u + m_s), \qquad
h_{\text{hole}} \ge 2(r_u + m_s)
\]

### v0 recommendation
- support 1--3 holes
- support only `circle` and `rectangle`
- disallow hole overlap
- enforce minimum edge margin

---

## 8.5 Sphere

### Meaning
Spherical obstacle.

### Geometry schema
```python
geometry = {
    "radius": float
}
```

### Typical uses
- floating disturbance obstacle
- moving round obstacle
- simplified clutter blob

### Dynamic recommendation
In v0, sphere is primarily useful as a **dynamic obstacle**.

---

## 8.6 Capsule

### Meaning
Cylinder with hemispherical ends.

### Geometry schema
```python
geometry = {
    "radius": float,
    "segment_length": float,
    "axis_mode": "velocity_aligned"  # or "vertical", "horizontal"
}
```

### Typical uses
- simplified pedestrian
- moving agent-like obstacle
- smooth elongated dynamic body

### Dynamic recommendation
In v0, capsule is the primary primitive for **pedestrian-like moving obstacles**.

---

# 9. Motion Specification

Only dynamic primitives use motion models.

## 9.1 Motion schema
```python
motion = {
    "motion_type": "waypoint_patrol",
    "speed_min": float,
    "speed_max": float,
    "accel_limit": float,
    "turn_rate_limit": float,
    "pause_probability": float,
    "trajectory_params": {...},
    "seed": int
}
```

## 9.2 Allowed motion types in v0
- `waypoint_patrol`
- `random_walk`
- `lane_patrol`

## 9.3 waypoint_patrol
Dynamic object moves between predefined waypoints.

### Required params
```python
trajectory_params = {
    "waypoints": [[x1, y1, z1], [x2, y2, z2], ...],
    "loop": bool
}
```

### Recommended uses
- capsule pedestrian
- sphere moving obstacle

## 9.4 random_walk
Dynamic object samples local headings and moves with obstacle/boundary repulsion.

### Required params
```python
trajectory_params = {
    "heading_resample_interval": int,
    "repulsion_gain": float
}
```

### Recommended uses
- sphere disturbance obstacle

## 9.5 lane_patrol
Dynamic object moves approximately along a straight or curved lane.

### Required params
```python
trajectory_params = {
    "path_points": [[x1, y1, z1], [x2, y2, z2], ...],
    "loop": bool
}
```

### Recommended uses
- capsule pedestrian in structured traffic-like motion

## 9.6 v0 motion constraints
- all dynamic obstacles must remain within workspace bounds
- motion speed must remain within configured range
- dynamic obstacle collision with static obstacles should be prevented by path design or local correction
- no multi-agent social simulation is required in v0

---

# 10. Scene Composition Templates

Primitives should not only be sampled independently.  
They should also support higher-level composition templates.

## 10.1 Required v0 composition templates

### bottleneck
A traversable narrowing formed by two or more static obstacles.

### pillar_field
A sparse or dense set of cylinders distributed over an area.

### clutter_cluster
A local cluster of boxes, cylinders, or mixed primitives.

### low_clearance_passage
A traversable region under a slab or beam.

### perforated_barrier
A slab or wall-like structure with one or more passable holes.

### moving_crossing
One or more dynamic primitives crossing a likely UAV route.

## 10.2 Template output
Each template expands into a set of primitive objects.  
The template itself should also be logged as a semantic scene component.

---

# 11. Placement Constraints and Validation Rules

All primitive placement must pass validation before scene acceptance.

## 11.1 Required validation checks

### Geometry validity
- all dimensions > 0
- no invalid hole sizes
- no negative thickness or radius

### Workspace validity
- primitive center and occupied volume must lie within workspace

### Non-overlap validity
- static primitives must not overlap beyond allowed tolerance
- dynamic spawn poses must not intersect static obstacles

### Support-mode validity
- `grounded` objects must touch floor
- `ceiling_attached` objects must connect to ceiling
- `floating` objects must remain inside the valid flight region
- `wall_attached` objects must be anchored to side structures if walls exist

### Perforation validity
- holes must lie fully inside slab
- holes must not overlap
- holes must satisfy `edge_margin_min`
- holes must satisfy `hole_spacing_min`

### Navigation validity
Generated scene should satisfy at least one of:
- guaranteed start-goal connectivity,
- intentionally disconnected case flagged as invalid for train mode,
- explicitly marked as failure-case scene for analysis mode

## 11.2 Optional quality checks
- minimum obstacle spacing
- minimum free-space volume
- bottleneck count
- dynamic obstacle route feasibility

---

# 12. Scene-Level Config Schema

A scene generator config should follow this structure:

```python
scene_config = {
    "scene_id": "scene_0001",
    "seed": 42,
    "workspace": {
        "size_x": 20.0,
        "size_y": 20.0,
        "size_z": 4.0,
        "flight_height_min": 0.8,
        "flight_height_max": 2.2
    },
    "primitive_budget": {
        "box": [2, 8],
        "cylinder": [4, 20],
        "slab": [0, 4],
        "perforated_slab": [0, 2],
        "sphere": [0, 4],
        "capsule": [0, 3]
    },
    "templates": [
        {"type": "pillar_field", "count": 1},
        {"type": "bottleneck", "count": 1},
        {"type": "moving_crossing", "count": 1}
    ],
    "generator_rules": {
        "allow_floating_static": False,
        "allow_dynamic_obstacles": True,
        "enforce_connectivity": True,
        "max_overlap_tolerance": 0.0
    }
}
```

---

# 13. Required Python Interfaces

The implementation should expose the following minimal interfaces.

## 13.1 Primitive data structure

```python
from dataclasses import dataclass
from typing import Optional, Literal, Any

@dataclass
class PrimitiveSpec:
    id: str
    type: str
    semantic_role: str
    geometry: dict
    pose: dict
    orientation: dict
    support_mode: str
    is_dynamic: bool
    motion: Optional[dict]
    perforation: Optional[dict]
    metadata: dict
```

## 13.2 Primitive factory interface

```python
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
    ...
```

```python
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
    ...
```

```python
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
    ...
```

```python
def make_perforated_slab(
    primitive_id: str,
    size_x: float,
    size_y: float,
    thickness: float,
    x: float,
    y: float,
    z: float,
    slab_mode: str,
    holes: list,
    edge_margin_min: float,
    hole_spacing_min: float,
    yaw: float = 0.0,
    support_mode: str = "grounded",
    semantic_role: str = "passable_panel",
) -> PrimitiveSpec:
    ...
```

```python
def make_sphere(
    primitive_id: str,
    radius: float,
    x: float,
    y: float,
    z: float,
    support_mode: str = "free_moving",
    semantic_role: str = "moving_disturbance",
    motion: Optional[dict] = None,
) -> PrimitiveSpec:
    ...
```

```python
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
    motion: Optional[dict] = None,
) -> PrimitiveSpec:
    ...
```

## 13.3 Scene generator interface

```python
def generate_scene(scene_config: dict) -> dict:
    """
    Returns a scene dictionary containing:
    - scene metadata
    - primitive list
    - template list
    - validation report
    """
    ...
```

## 13.4 Validation interface

```python
def validate_primitive(primitive: PrimitiveSpec, workspace: dict) -> dict:
    """
    Returns per-primitive validation result.
    """
    ...
```

```python
def validate_scene(scene: dict) -> dict:
    """
    Returns scene-level validation report:
    - geometry validity
    - overlap validity
    - workspace validity
    - navigation validity
    """
    ...
```

## 13.5 Serialization interface

```python
def scene_to_json(scene: dict, path: str) -> None:
    ...
```

```python
def scene_from_json(path: str) -> dict:
    ...
```

---

# 14. Recommended Internal Module Layout

```text
env_primitives/
├── specs.py
├── factories.py
├── motion.py
├── perforation.py
├── templates.py
├── validation.py
├── scene_generator.py
├── serialization.py
└── tests/
    ├── test_primitives.py
    ├── test_perforated_slab.py
    ├── test_motion.py
    ├── test_validation.py
    └── test_scene_generation.py
```

---

# 15. Logging Requirements

Each generated primitive should be logged with at least:

- primitive id
- primitive type
- semantic role
- dynamic/static flag
- support mode
- pose
- orientation
- geometry params
- perforation params if any
- motion params if any

Each scene should log:

- scene id
- seed
- workspace
- primitive counts by type
- template counts
- validation status
- connectivity status
- dynamic obstacle count
- traversable-hole count

---

# 16. Acceptance Criteria for v0 Implementation

A v0 implementation is considered acceptable if it can:

1. generate valid scenes from seed-controlled config;
2. instantiate all six primitive types;
3. support at least:
   - `box`
   - `cylinder`
   - `slab`
   - `perforated_slab`
   - `sphere`
   - `capsule`
4. support at least:
   - one static template (`bottleneck` or `pillar_field`)
   - one passable template (`perforated_barrier`)
   - one dynamic template (`moving_crossing`)
5. validate scene geometry and workspace constraints;
6. serialize and reload scenes reproducibly;
7. produce a machine-readable validation report.

---

# 17. Recommended v0 Defaults

## 17.1 Geometry defaults
- box size range: moderate clutter and barrier sizes
- cylinder radius range: pillar-like
- slab thickness: thin relative to span
- sphere radius: small-to-medium dynamic obstacle
- capsule radius/length: pedestrian-like dynamic obstacle

## 17.2 Motion defaults
- capsule default motion: `waypoint_patrol`
- sphere default motion: `random_walk` or `waypoint_patrol`

## 17.3 Perforation defaults
- one or two holes per perforated slab
- circular or rectangular holes only
- enforce UAV passability margin

---

# 18. Non-Goals for v0

The following are explicitly out of scope for v0:
- full semantic room layout generation
- photorealistic assets
- arbitrary mesh obstacles
- dense human crowd simulation
- articulated moving objects
- full 6-DoF obstacle physics
- complex social behavior models for pedestrians

---

# 19. Open Questions

The following remain open after v0:
- whether horizontal cylinders are enabled by default
- whether floating static obstacles are allowed in train mode
- whether dynamic sphere obstacles are part of the main benchmark or only augmentation
- whether perforated slabs appear in nominal training or only in stress-test sets
- whether capsule motion is purely patrol-based or includes heading randomness

These questions should not block the initial implementation.

---

# 20. Implementation Order Recommendation

Recommended order:

## Phase A
- box
- cylinder
- slab
- scene validation
- basic templates

## Phase B
- perforated_slab
- hole validation
- passability checks

## Phase C
- sphere motion
- capsule motion
- moving_crossing template

## Phase D
- serialization
- logging
- scene statistics
- benchmark config presets

This order minimizes implementation risk while enabling early environment bring-up.