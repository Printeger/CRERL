# Scene Generation Rules 40x40x4.5 v0
**Project:** CRE-based Generic Obstacle-Avoidance RL  
**Version:** v0.1  
**Status:** Draft for implementation  
**Scene type:** 40×40×4.5 generic obstacle-avoidance training scene  
**Primary purpose:** training / evaluation / CRE stress testing

---

# 1. Purpose

This document specifies the scene generation rules for a 40m × 40m × 4.5m generic obstacle-avoidance environment.

The goals are:

1. generate scenes suitable for UAV obstacle-avoidance RL;
2. avoid purely uniform random obstacle placement;
3. ensure each scene contains both background obstacle variability and at least one meaningful local structure;
4. support nominal, boundary-critical, and shifted environment families;
5. ensure start-goal tasks are valid, non-trivial, and analyzable.

---

# 2. Workspace Definition

## 2.1 Horizontal workspace
- workspace size: 40m x 40m x 4.5m
- coordinates:
  - \(x \in [0, 40]\)
  - \(y \in [0, 40]\)
  - \(z \in [0, 4.5]\)

## 2.2 Vertical workspace
- vertical space is handled separately through flight-height band
- current scene generation rules primarily define planar obstacle layout
- vertical obstacle effects may be added through slabs, hanging objects, or height-band restrictions

## 2.3 Valid navigable region
The valid navigable region is the free space inside the workspace after obstacle occupancy is subtracted.

---

# 3. Scene Generation Philosophy

Each scene is generated as:

\[
\text{Scene} =
\text{Background Obstacle Field}
+
\text{Structured Local Templates}
+
\text{Start/Goal Sampling}
+
\text{Validation}
\]

This means:
- obstacle placement is partly random but not purely random,
- every scene contains at least one structured difficulty source,
- start and goal are sampled under explicit geometric constraints,
- invalid scenes are rejected and regenerated.

---

# 4. Scene Families

The generator supports three scene families:

1. `nominal`
2. `boundary_critical`
3. `shifted`

---

## 4.1 Nominal Scene Family

### Purpose
Nominal scenes are used for baseline training and in-distribution evaluation.

### Characteristics
- moderate obstacle density
- moderate local bottleneck frequency
- moderate free-space complexity
- sufficient obstacle clearance around start and goal
- at least one structured local template, but not overly restrictive

### Recommended ranges
- background obstacle count: 6--12
- structured templates per scene: 1
- local bottleneck width: moderate
- start clearance: high
- goal clearance: high

---

## 4.2 Boundary-Critical Scene Family

### Purpose
Boundary-critical scenes are used to expose:
- safety-boundary behavior,
- under-coverage of critical states,
- narrow-clearance decision making.

### Characteristics
- higher obstacle density or tighter local placement
- smaller local bottleneck width
- more near-obstacle start/goal configurations
- stronger local geometric pressure near likely routes
- one or two structured critical templates

### Recommended ranges
- background obstacle count: 10--16
- structured templates per scene: 1--2
- local bottleneck width: small
- start clearance: reduced
- goal clearance: reduced
- dynamic obstacles: optional, not required in v0

---

## 4.3 Shifted Scene Family

### Purpose
Shifted scenes are used to test transfer and environment-dependent shortcut behavior.

### Characteristics
- obstacle placement pattern differs from nominal training
- template type frequency differs from nominal
- geometry statistics partially shift
- may include changed obstacle-type proportions or changed local clutter distributions
- does not necessarily increase total difficulty, but changes distribution

### Recommended ranges
- background obstacle count: 6--14
- structured templates per scene: 1--2
- altered primitive-type ratio
- altered template placement distribution
- altered dynamic crossing pattern if dynamic obstacles are enabled

---

# 5. Primitive Budget Rules

Each scene is composed from the primitive library defined in `Env_Primitive_Spec_v0.md`.

## 5.1 Allowed primitive types
- `box`
- `cylinder`
- `slab`
- `perforated_slab`
- `sphere`
- `capsule`

## 5.2 Recommended primitive budget for v0
For a single scene:

- `box`: 2--8
- `cylinder`: 4--16
- `slab`: 0--2
- `perforated_slab`: 0--1
- `sphere`: 0--3
- `capsule`: 0--2

## 5.3 Primitive role guidance
- `box`: static barrier / clutter / bottleneck boundary
- `cylinder`: static pillar / sparse obstacle
- `slab`: low-clearance blocker / wall-like panel
- `perforated_slab`: traversable barrier / path-choice structure
- `sphere`: optional dynamic disturbance obstacle
- `capsule`: optional pedestrian-like dynamic obstacle

---

# 6. Obstacle Placement Strategy

Obstacle placement must not be purely uniform random.

Use a mixture of:
1. background random placement,
2. structure-aware placement,
3. route-adjacent placement,
4. optional boundary-adjacent placement.

---

## 6.1 Background random placement

### Purpose
Provide general obstacle variability and basic avoidance demand.

### Rules
- place a subset of primitives using constrained random sampling
- enforce:
  - obstacle-obstacle minimum spacing
  - obstacle-boundary minimum spacing
  - no large overlapping occupied regions
  - no immediate blocking of all start-goal routes

### Recommended share
- nominal: 60%--80% of total primitives
- boundary-critical: 40%--60%
- shifted: 50%--70%

---

## 6.2 Structure-aware placement

### Purpose
Generate local geometric patterns that create meaningful navigation choices or risks.

### Rules
At least one structured template must be inserted into every scene.

Allowed templates:
- `bottleneck`
- `clutter_cluster`
- `perforated_barrier`
- `low_clearance_passage`
- `pillar_field`
- `moving_crossing` (optional if dynamics enabled)

### Recommended share
- nominal: exactly 1 template
- boundary-critical: 1--2 templates
- shifted: 1--2 templates, with altered template distribution

---

## 6.3 Route-adjacent placement

### Purpose
Make the obstacle field interact with likely shortest paths, rather than remaining irrelevant clutter.

### Rule
A subset of obstacles may be sampled near the rough corridor connecting start and goal, or near bottleneck templates.

This should be used carefully:
- enough to create decision pressure,
- not so much that scenes become mostly blocked.

### Recommended use
- nominal: low
- boundary-critical: medium to high
- shifted: medium, but with different local patterning

---

## 6.4 Boundary-adjacent placement

### Purpose
Increase wall-like pressure or near-boundary navigation difficulty.

### Rule
A subset of static primitives may be placed near workspace edges, but must not collapse the valid navigable region.

### Recommended use
- nominal: low
- boundary-critical: medium
- shifted: optional

---

# 7. Structured Template Rules

At least one template must be selected per scene.

---

## 7.1 Bottleneck

### Meaning
A locally narrow traversable region formed by two or more obstacles.

### Construction
- two box obstacles
- two cylinder groups
- box + cylinder combination

### Parameters
- bottleneck width
- bottleneck length
- local orientation
- placement center

### Rule
The bottleneck must remain traversable in train/eval mode unless the scene is explicitly marked as failure-analysis-only.

---

## 7.2 Clutter Cluster

### Meaning
A local region with higher-than-background obstacle density.

### Construction
- 3--8 small/medium obstacles in a local patch
- may mix boxes and cylinders

### Parameters
- cluster radius
- cluster density
- obstacle type mixture

### Rule
A clutter cluster should increase local route complexity without fully sealing off large workspace regions.

---

## 7.3 Perforated Barrier

### Meaning
A wall-like or panel-like structure with one or more holes.

### Construction
- one perforated slab
- optionally flanked by boxes or cylinders

### Parameters
- slab orientation
- hole count
- hole shape
- hole size
- hole position

### Rule
At least one hole must be nominally traversable if the scene is intended for standard train/eval use.

---

## 7.4 Low Clearance Passage

### Meaning
A region where vertical clearance is locally reduced.

### Construction
- horizontal slab
- optional side boundaries

### Parameters
- passage height
- passage span
- placement relative to route

### Rule
Use only if vertical clearance is part of the current task abstraction.

---

## 7.5 Pillar Field

### Meaning
A field of distributed cylindrical obstacles.

### Construction
- multiple cylinders distributed over a subregion

### Parameters
- field size
- pillar count
- pillar spacing
- local alignment / randomness

### Rule
A pillar field should be traversable but should force non-trivial local path adaptation.

---

## 7.6 Moving Crossing

### Meaning
A dynamic obstacle crosses a likely UAV route.

### Construction
- one or more sphere/capsule objects
- waypoint patrol or lane patrol motion

### Rule
Use as an optional template in later stages or shifted environments.
Not mandatory in v0 nominal scenes.

---

# 8. Start and Goal Sampling Rules

Start and goal must be sampled under geometric constraints.

---

## 8.1 Start Sampling

### Main training rule
The start position should be sampled **inside** the workspace, near the boundary, not outside it.

### Recommended start region
Sample start from a boundary-adjacent inner band:
- distance to workspace boundary: 0.5m -- 1.5m

### Additional constraints
- minimum clearance to any obstacle:
  \[
  d(\text{start}, \text{obstacles}) \ge d_{\text{start-clear}}
  \]
- recommended:
  \[
  d_{\text{start-clear}} \ge 1.0 \text{ m}
  \]

### Rationale
This preserves the “entering from outside” feel without introducing external workspace semantics.

---

## 8.2 Goal Sampling

### Goal region
Sample goal from the interior free-space region.

### Constraints
- minimum obstacle clearance:
  \[
  d(\text{goal}, \text{obstacles}) \ge d_{\text{goal-clear}}
  \]
- minimum boundary clearance:
  \[
  d(\text{goal}, \partial\Omega) \ge d_{\text{goal-boundary}}
  \]

Recommended:
- \(d_{\text{goal-clear}} \ge 1.0\) m
- \(d_{\text{goal-boundary}} \ge 1.0\) m

---

## 8.3 Start-Goal Distance

The Euclidean distance between start and goal must satisfy:
\[
d(\text{start}, \text{goal}) \in [d_{\min}, d_{\max}]
\]

Recommended:
- \(d_{\min} = 8.0\) m
- \(d_{\max} = 16.0\) m

### Rationale
This prevents:
- trivial tasks,
- overly long tasks,
- highly local start-goal pairs that bypass the obstacle structure.

---

## 8.4 Reachability Rule

A scene is valid for train/eval mode only if:
- the start and goal are geometrically connected through free space,
- or the scene is explicitly marked as analysis-only.

---

# 9. Validation Rules

Every generated scene must pass validation.

## 9.1 Required checks

### Geometry validity
- all primitive dimensions are valid
- no invalid perforation definitions
- primitive poses are inside allowed workspace

### Overlap validity
- static-static overlaps not allowed
- dynamic spawn positions must not intersect static geometry

### Start-goal validity
- start in free space
- goal in free space
- start-goal distance valid
- start-goal connectivity valid

### Traversability validity
- any required bottleneck or perforated structure must be traversable if the scene is not marked as stress-only

### Density sanity
- obstacle field must not be too sparse or too blocked
- free-space fraction must lie within configurable bounds

---

## 9.2 Optional checks
- number of local bottlenecks
- minimum corridor width
- number of disconnected free-space components
- number of critical-state candidates
- number of dynamic crossing interactions

---

# 10. Scene Generator Config Template

```python id="pu4yl0"
scene_config = {
    "scene_family": "nominal",  # nominal / boundary_critical / shifted
    "scene_id": "scene_0001",
    "seed": 42,
    "workspace": {
        "size_x": 40.0,
        "size_y": 40.0,
        "size_z": 4.5,
        "flight_height_min": 0.8,
        "flight_height_max": 2.2
    },
    "primitive_budget": {
        "box": [2, 8],
        "cylinder": [4, 16],
        "slab": [0, 2],
        "perforated_slab": [0, 1],
        "sphere": [0, 3],
        "capsule": [0, 2]
    },
    "distribution_modes": {
        "background": "constrained_random",
        "structure": "template_driven",
        "route_adjacent_bias": 0.3,
        "boundary_adjacent_bias": 0.2
    },
    "templates": [
        {"type": "bottleneck", "count": 1}
    ],
    "start_goal": {
        "start_band_min": 0.5,
        "start_band_max": 1.5,
        "start_clearance_min": 1.0,
        "goal_clearance_min": 1.0,
        "goal_boundary_clearance_min": 1.0,
        "start_goal_distance_min": 8.0,
        "start_goal_distance_max": 16.0
    },
    "validation": {
        "enforce_connectivity": True,
        "allow_failure_analysis_only": False,
        "max_overlap_tolerance": 0.0
    }
}
```
# 11. Recommended Family Presets
## 11.1 Nominal Preset
background obstacles: medium
templates: exactly 1
dynamic obstacles: off by default
route-adjacent bias: low to medium
boundary-adjacent bias: low
## 11.2 Boundary-Critical Preset
background obstacles: medium-high
templates: 1--2
local bottlenecks narrower
route-adjacent bias: medium-high
start/goal clearance reduced
dynamic obstacles: optional
11.3 Shifted Preset
obstacle total count similar to nominal
template distribution changed
primitive-type mix changed
placement pattern changed
dynamic pattern optionally changed
noise and motion variation may increase
# 12. Logging Requirements

For every generated scene, log:

scene_id
scene_family
seed
primitive counts by type
template counts
start position
goal position
workspace size
free-space connectivity result
validation status
traversable-hole count
dynamic obstacle count
bottleneck count
estimated min local clearance

# 13. Acceptance Criteria for Scene Generation v0

The generator is acceptable for v0 if it can:

generate reproducible scenes from seed;
generate all three families:
nominal
boundary_critical
shifted
ensure every train/eval scene contains at least one structured local template;
sample valid start and goal positions under the defined constraints;
reject invalid or disconnected scenes;
export scene config and validation results;
generate at least 100 valid scenes with acceptance rate ≥ 95% under default nominal settings.
# 14. Open Questions

The following may remain open after v0 drafting:

whether dynamic obstacles are enabled in nominal training by default,
whether perforated barriers appear in nominal training or only in analysis sets,
whether low-clearance vertical structures are part of the main benchmark,
whether route-adjacent obstacle bias is estimated from start-goal line or from a coarser planner,
whether clutter clusters are always traversable or may occasionally form analysis-only dead zones.

These questions must not block initial implementation.

# 15. Implementation Order Recommendation
Phase A
workspace definition
constrained random background placement
static primitive placement
validation
start-goal sampling
Phase B
bottleneck template
clutter_cluster template
perforated_barrier template
Phase C
scene family presets
shifted distribution rules
logging and export
Phase D
dynamic sphere/capsule
moving_crossing template
mixed static+dynamic benchmark scenes