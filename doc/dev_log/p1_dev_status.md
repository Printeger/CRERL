# Phase 1 Development Status

Updated: 2026-04-10

## 1. This Iteration Goal

This iteration tightens the `nominal` scene-family config for short RL smoke
training.

The goal of this step is:

- shrink the nominal workspace from `40 x 40` to `15 x 15` while preserving the
  existing `4.5m` vertical extent,
- reduce obstacle budgets and large template dimensions so the smaller scene
  does not become disproportionately cluttered,
- and keep start/goal sampling aligned with the reduced workspace.

## 2. Implemented Results

The following nominal-scene updates were applied:

- `workspace.size_x` and `workspace.size_y` now use `15.0`
- primitive budgets were reduced for:
  - `box`
  - `cylinder`
  - dynamic obstacle placeholders
- background placement spacing and free-space targets were retuned for the
  smaller footprint
- nominal template dimensions were reduced for:
  - `bottleneck`
  - `clutter_cluster`
  - `perforated_barrier`
- start/goal sampling constraints were tightened to:
  - shorter valid start-goal distances
  - slightly smaller clearances and boundary bands

The main changed file is:

- `isaac-training/training/cfg/env_cfg/scene_cfg_nominal.yaml`

## 3. How To Validate

Run a focused pure-Python scene compile and validation check:

```bash
PYTHONPATH=isaac-training/training python - <<'PY'
from envs.env_gen import (
    compile_scene_config_from_rules,
    load_scene_family_config,
    validate_scene,
    UniversalArenaGenerator,
    ArenaConfig,
)

rules = load_scene_family_config("nominal")
for seed in range(5):
    compiled = compile_scene_config_from_rules(rules, seed=seed, difficulty=0.5)
    arena_cfg = ArenaConfig(
        size_x=compiled["workspace"]["size_x"],
        size_y=compiled["workspace"]["size_y"],
        size_z=compiled["workspace"]["size_z"],
        start_pos=tuple(compiled["start"]),
        goal_pos=tuple(compiled["goal"]),
        flight_height_min=compiled["workspace"]["flight_height_min"],
        flight_height_max=compiled["workspace"]["flight_height_max"],
    )
    result = UniversalArenaGenerator(arena_cfg, seed=seed).generate_from_scene_family(
        "nominal",
        seed=seed,
        difficulty=0.5,
        gravity_tilt_enabled=False,
    )
    report = validate_scene(result.scene)
    assert report["valid"], (seed, report)
print("nominal 15x15 validation passed for seeds 0-4")
PY
```

## 4. Validation Results

The following focused validation was run successfully on 2026-04-10:

- `PYTHONPATH=isaac-training/training python ...`
  - loaded the updated `nominal` scene-family config
  - compiled the scene rules at `difficulty=0.5`
  - generated real scenes through `UniversalArenaGenerator`
  - validated the generated scenes with `validate_scene(...)`
- seeds checked:
  - `0`
  - `1`
  - `2`
  - `3`
  - `4`
- result:
  - all five generated scenes were `valid = true`
  - all five generated scenes were `strict_valid = true`
  - realized obstacle counts were between `4` and `6`
  - dynamic obstacle count remained `0` as expected

## 5. What Should Be Done Next

The next step should be:

1. run a short `train.py` smoke training on the smaller nominal scene,
2. inspect whether LiDAR coverage and route pressure still feel appropriate in
   practice,
3. and then decide whether `boundary_critical` and `shifted` should also get a
   matching small-workspace variant.

## 6. Follow-Up Density Increase (2026-04-10)

This follow-up increases the realized obstacle density of the `15 x 15`
`nominal` family so short visible training runs better exercise local obstacle
avoidance.

### What changed

- raised the `nominal` primitive budgets for:
  - `box`
  - `cylinder`
  - `slab`
  - `perforated_slab`
- reduced background spacing and free-space targets so more obstacles can fit
  into the smaller workspace
- increased template count pressure to:
  - `min_templates_per_scene = 3`
  - `max_templates_per_scene = 4`
- enlarged the realized clutter load by increasing:
  - clutter-cluster obstacle count
  - perforated-barrier panel size / hole count
  - bottleneck span range

The main changed file is:

- `isaac-training/training/cfg/env_cfg/scene_cfg_nominal.yaml`

### How To Validate

Run a focused pure-Python scene compile and validation check:

```bash
PYTHONPATH=isaac-training/training python - <<'PY'
from envs.env_gen import (
    ArenaConfig,
    UniversalArenaGenerator,
    compile_scene_config_from_rules,
    load_scene_family_config,
    validate_scene,
)

rules = load_scene_family_config("nominal")
for seed in range(5):
    compiled = compile_scene_config_from_rules(rules, seed=seed, difficulty=0.5)
    arena_cfg = ArenaConfig(
        size_x=compiled["workspace"]["size_x"],
        size_y=compiled["workspace"]["size_y"],
        size_z=compiled["workspace"]["size_z"],
        start_pos=tuple(compiled["start"]),
        goal_pos=tuple(compiled["goal"]),
        flight_height_min=compiled["workspace"]["flight_height_min"],
        flight_height_max=compiled["workspace"]["flight_height_max"],
    )
    result = UniversalArenaGenerator(arena_cfg, seed=seed).generate_from_scene_family(
        "nominal",
        seed=seed,
        difficulty=0.5,
        gravity_tilt_enabled=False,
    )
    report = validate_scene(result.scene)
    assert report["valid"], (seed, report)
    print(seed, report["primitive_counts"], len(result.scene["primitives"]))
print("nominal dense validation passed for seeds 0-4")
PY
```

### Validation Results

- `PYTHONPATH=isaac-training/training python ...`
  - loaded the denser `nominal` scene-family config
  - compiled the scene rules at `difficulty=0.5`
  - generated real scenes through `UniversalArenaGenerator`
  - validated the generated scenes with `validate_scene(...)`
- seeds checked:
  - `0`
  - `1`
  - `2`
  - `3`
  - `4`
- result:
  - all five generated scenes were `valid = true`
  - all five generated scenes were `strict_valid = true`
  - realized primitive counts were between `29` and `34`
  - the realized primitive mix was dominated by:
    - `cylinder`
    - `box`
    - `slab`
    - occasional `perforated_slab`

## 7. Follow-Up Edge-Fill Placement (2026-04-10)

This follow-up makes the dense `15 x 15` nominal family visibly use the edge
area of each env instead of concentrating background obstacles near the center.

### What changed

- `scene_cfg_nominal.yaml` now enables boundary-fill placement controls under
  `background_placement`:
  - `fill_to_boundary`
  - `field_boundary_margin_xy`
  - `structured_boundary_margin_xy`
  - `cover_edges`
- `env_gen.py` now threads those controls into the compiled background field
  templates instead of relying only on hard-coded `2.0m+` sampling margins.
- `_jittered_grid_positions(...)` now supports `cover_edges=True`, which places
  grid centers across the full configured sampling interval and jitters edge
  centers inward so obstacles can populate the boundary band without violating
  workspace bounds.
- goal-height sampling now respects `goal_boundary_clearance_min`, matching the
  start/goal generator with validation.
- the nominal occupancy target was retuned for the new packed edge-fill density
  so valid scenes do not exhaust the retry budget unnecessarily.
- `test_scene_generation.py` was updated to reflect the current `15 x 15`
  nominal scene-family contract instead of the old `40 x 40` nominal default.

### How To Validate

```bash
python -m py_compile \
  isaac-training/training/envs/env_gen.py \
  isaac-training/training/unit_test/test_env/test_scene_generation.py
```

```bash
pytest -q isaac-training/training/unit_test/test_env/test_scene_generation.py
```

Run a focused boundary-fill generation check:

```bash
python -c 'import sys; sys.path.insert(0,"isaac-training/training"); from envs.env_gen import load_scene_family_config, compile_scene_config_from_rules, generate_scene, validate_scene; cfg=load_scene_family_config("nominal"); [print(seed, validate_scene(generate_scene(compile_scene_config_from_rules(cfg, seed=seed, difficulty=1.0)))["valid"]) for seed in range(1001,1006)]'
```

### Validation Results

- `python -m py_compile ...`
  - passed
- `pytest -q isaac-training/training/unit_test/test_env/test_scene_generation.py`
  - `15 passed`
- focused nominal scene generation:
  - seeds `0-4` at `difficulty=0.5` passed `valid = true` and
    `strict_valid = true`
  - seeds `1001-1005` at `difficulty=1.0` passed `valid = true` and
    `strict_valid = true`
  - `retry_exhausted = false` for the checked seeds
  - the `difficulty=1.0` scenes realized `43-48` primitives
  - each checked `difficulty=1.0` scene had `17-25` obstacles within `0.75m`
    of an env boundary
