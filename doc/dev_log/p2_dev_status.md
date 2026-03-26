# Phase 2 Development Status

Updated: 2026-03-26

## 1. Phase Goal

Phase 2 is the runtime logging unification phase.

Its engineering goal is to turn the project from:

- "the environment and policies can run"

into:

- "all main execution paths can emit analyzable CRE evidence"

The target paths are:

- manual flight / scene inspection:
  - `isaac-training/training/unit_test/test_flight.py`
- RL training rollouts:
  - `isaac-training/training/scripts/train.py`
- RL evaluation rollouts:
  - `isaac-training/training/scripts/eval.py`

## 2. Implemented Results

### 2.1 Unified Runtime Log Schema

The canonical runtime schema is now centered in:

- `isaac-training/training/envs/cre_logging.py`
- `isaac-training/training/runtime_logging/schema.py`
- `isaac-training/training/runtime_logging/logger.py`

The schema now supports:

- step-level records
- episode-level summaries
- run-level aggregate summaries
- canonical artifact layout under:
  - `isaac-training/training/logs/<run_id>/`

Canonical artifacts produced by the logger:

- `manifest.json`
- `steps.jsonl`
- `episodes.jsonl`
- `summary.json`
- `episodes/episode_XXXX.json`

### 2.2 Required Fields Are Unified

The main schema now consistently carries:

- `scene_id`
- `scenario_type`
- `scene_cfg_name`
- `position`
- `velocity`
- `yaw_rate`
- `goal_distance`
- `reward_total`
- `reward_components`
- `collision_flag`
- `min_obstacle_distance`
- `near_violation_flag`
- `out_of_bounds_flag`
- `done_type`
- `source`

### 2.3 Reward Component Names Were Frozen

Reward components are now normalized through the standard key set:

- `reward_progress`
- `reward_safety_static`
- `reward_safety_dynamic`
- `penalty_smooth`
- `penalty_height`
- `manual_control`

This prevents different execution paths from emitting different reward-component shapes.

### 2.4 Environment Metadata Export Was Tightened

`env.py` now exports runtime metadata through a stable environment interface instead of relying only on ad hoc logging config values.

The environment now provides:

- `scenario_type`
- `scene_cfg_name`
- `scene_id_prefix`
- `done_type_labels`

and this metadata is consumed by:

- `train.py`
- `eval.py`
- `runtime_logging/training_log_adapter.py`

### 2.5 Scene Family Metadata Reaches the Logs

Scene-family-generated environments now propagate real scene config identity into the generated scene metadata:

- `scene_cfg_name`
- `family`
- `scene_tags`

This allows:

- `test_flight.py`
- training/eval log adapters
- later analyzers

to reason over the actual scene family configuration rather than fallback placeholders.

### 2.6 Three Execution Paths Converge on the Same Schema

The current state is:

- `test_flight.py` uses the canonical runtime logger
- `train.py` uses the shared training rollout adapter and canonical run logger
- `eval.py` uses the same training rollout adapter and canonical run logger

In code terms, the project now has one mainline CRE logging pipeline rather than three incompatible per-script formats.

## 3. Main Files Changed During Phase 2

Key implementation files:

- `isaac-training/training/envs/cre_logging.py`
- `isaac-training/training/runtime_logging/schema.py`
- `isaac-training/training/runtime_logging/logger.py`
- `isaac-training/training/runtime_logging/training_log_adapter.py`
- `isaac-training/training/scripts/env.py`
- `isaac-training/training/scripts/train.py`
- `isaac-training/training/scripts/eval.py`
- `isaac-training/training/unit_test/test_flight.py`
- `isaac-training/training/envs/env_gen.py`

Key test files:

- `isaac-training/training/unit_test/test_env/test_cre_logging.py`
- `isaac-training/training/unit_test/test_env/test_training_log_adapter.py`
- `isaac-training/training/unit_test/test_env/test_scene_family_bridge.py`

## 4. How To Validate Phase 2

### 4.1 Syntax and Import-Level Validation

Run:

```bash
python -m py_compile \
  isaac-training/training/envs/cre_logging.py \
  isaac-training/training/runtime_logging/schema.py \
  isaac-training/training/runtime_logging/logger.py \
  isaac-training/training/runtime_logging/training_log_adapter.py \
  isaac-training/training/scripts/env.py \
  isaac-training/training/scripts/train.py \
  isaac-training/training/scripts/eval.py \
  isaac-training/training/unit_test/test_flight.py
```

Expected result:

- no syntax error

### 4.2 Logger Smoke Test

Use the `NavRL` environment to run a minimal logger smoke test.

What to verify:

- `steps.jsonl` is created
- `episodes.jsonl` is created
- `summary.json` is created
- step records contain the standard reward component keys
- `scene_cfg_name` survives into the episode summary

### 4.3 Training Adapter Smoke Test

Use the `NavRL` environment to run a synthetic rollout through:

- `TrainingRolloutLogger`
- `env_gen` scene-family-backed metadata

What to verify:

- adapter-emitted steps contain canonical reward component keys
- `done_type` maps correctly from numeric code to canonical string
- `scene_cfg_name` survives into emitted step logs
- generated scene metadata carries the correct scene family config name

### 4.4 Optional End-to-End Runtime Validation

For full closure, run:

- one `test_flight.py` session
- one short `eval.py` run
- one short `train.py` run

and inspect the produced run directories under:

- `isaac-training/training/logs/`

This is still the recommended final close-out step before Phase 3 acceptance gating.

## 5. Validation Results

The following validations were run successfully on 2026-03-26:

### 5.1 `py_compile`

Result:

- passed

### 5.2 Logger Smoke Test

Result:

- passed

Observed check:

- standard reward component keys were present in emitted step logs
- `scene_cfg_name == scene_cfg_nominal.yaml` was preserved in the episode summary

### 5.3 Training Adapter + Scene Metadata Smoke Test

Result:

- passed

Observed check:

- adapter-emitted logs preserved `scene_cfg_name`
- `done_type` was mapped to canonical string values
- standard reward component keys were present
- generated nominal scene metadata preserved:
  - `scene_cfg_name == scene_cfg_nominal.yaml`

### 5.4 Test-Level Coverage

Relevant unit tests now exist for:

- logger behavior
- aggregate metrics
- training rollout adapter field mapping
- scene-family metadata bridging

Note:

- a fully end-to-end Isaac GUI validation across all three execution paths was not completed as part of this status update
- current confidence is therefore:
  - code-path validated
  - smoke-tested
  - not yet fully simulator-acceptance-closed

## 6. Current Assessment

Phase 2 is effectively implemented at the code and integration level.

Practical status:

- schema unification: complete
- metadata export unification: complete
- training/eval/manual logging convergence: complete
- aggregate metric generation: complete
- end-to-end acceptance across real run directories: still recommended as the final close-out step

So the current engineering judgement is:

- Phase 2 implementation: essentially complete
- Phase 2 closure: pending final run-level acceptance gating

## 7. What Comes Next

The next step is not to add analyzers immediately.

The correct next action is:

- add a unified run-level acceptance check
- audit real run directories from:
  - `test_flight.py`
  - `train.py`
  - `eval.py`

That work is now planned in:

- `doc/roadmap/phase3.md`

Phase 3 should therefore begin with:

- directory-level aggregation audit
- `acceptance.json` generation
- a common pass/fail gate for run directories
