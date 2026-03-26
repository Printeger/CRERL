# Phase 2: Runtime Logging Unification

## 1. Purpose

Phase 2 is the stage where the project turns from
"we can run environments and policies"
into
"we can produce analyzable CRE evidence".

The goal is to make all executable paths emit the same
CRE-compatible runtime evidence, so that later phases can build:

- baseline comparisons,
- static/dynamic inconsistency detection,
- report generation,
- repair validation.

This phase corresponds to:

- [doc/roadmap.md](../roadmap.md) `Phase 2. Unify runtime logging`
- [doc/system_architecture_and _control_flow.md](../system_architecture_and%20_control_flow.md) `Layer C. Execution and Logging Layer`

---

## 2. Why This Phase Comes Next

According to the CRE engineering loop:

`spec -> generate scenes -> run policies -> collect logs -> analyze inconsistencies -> propose repair -> validate repair`

the next blocking dependency is `collect logs`.

Without unified logs:

- `test_flight.py` only provides partial manual evidence,
- `env.py` exposes some useful fields but does not yet guarantee a stable exported schema,
- `train.py` and `eval.py` do not yet write CRE trajectory artifacts,
- later analyzers cannot reliably compute witness metrics.

So before writing baseline runners, analyzers, or repair logic, we must first make runtime evidence stable.

---

## 3. Target Outcome

At the end of Phase 2, any supported execution path should be able to export:

- step-level trajectory logs,
- episode-level summaries,
- run-level aggregate metrics,
- scene-bound metadata.

Supported paths in this phase:

1. manual scene inspection / scripted flight:
   - [test_flight.py](../../isaac-training/training/unit_test/test_flight.py)
2. RL training rollouts:
   - [train.py](../../isaac-training/training/scripts/train.py)
3. RL evaluation rollouts:
   - [eval.py](../../isaac-training/training/scripts/eval.py)

All of them should converge on one schema.

---

## 4. Required Log Schema

### 4.1 Step-Level Fields

Every step log must include at least:

- `scene_id`
- `scenario_type`
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

### 4.2 Episode-Level Fields

Every episode summary should include at least:

- `episode_index`
- `seed`
- `scene_id`
- `scenario_type`
- `num_steps`
- `trajectory_length`
- `return_total`
- `reward_components_total`
- `success_flag`
- `collision_flag`
- `out_of_bounds_flag`
- `min_obstacle_distance`
- `near_violation_steps`
- `near_violation_ratio`
- `final_goal_distance`
- `done_type`

### 4.3 Run-Level Aggregates

Every run directory should be able to produce:

- `success_rate`
- `collision_rate`
- `min_distance`
- `average_return`
- `near_violation_ratio`

---

## 5. Canonical Output Layout

The canonical output directory for Phase 2 is:

`isaac-training/training/logs/<run_id>/`

Recommended artifacts:

- `manifest.json`
- `steps.jsonl`
- `episodes.jsonl`
- `summary.json`
- `episodes/episode_XXXX.json`

Legacy ad hoc outputs under:

- `isaac-training/training/unit_test/logs/`
- `isaac-training/training/unit_test/outputs/`

should not remain the mainline logging path.

---

## 6. File-Level Implementation Checklist

This section is the concrete implementation plan for Phase 2.

### 6.1 Schema and Logger Core

#### File: [isaac-training/training/envs/cre_logging.py](../../isaac-training/training/envs/cre_logging.py)

Role:
- current main implementation of step/episode/run logging.

What to keep:
- `StepLog`
- `EpisodeLog`
- `FlightEpisodeLogger`
- `aggregate_log_directory()`

What to add / tighten:
- freeze the canonical field names and meanings,
- add `schema_version` to run manifest,
- add `source` to distinguish:
  - `test_flight`
  - `train`
  - `eval`
  - future `baseline`
- add `scene_cfg_name` to episode metadata if available,
- standardize `done_type` values:
  - `running`
  - `success`
  - `collision`
  - `out_of_bounds`
  - `truncated`
  - `manual_regen`
  - `manual_exit`
  - `unknown`
- keep `reward_components_total` deterministic and stable,
- ensure run summary always computes:
  - `success_rate`
  - `collision_rate`
  - `min_distance`
  - `average_return`
  - `near_violation_ratio`

Definition of done:
- this file becomes the canonical semantic owner of runtime log schema.

#### File: [isaac-training/training/runtime_logging/schema.py](../../isaac-training/training/runtime_logging/schema.py)

Role:
- stable public export layer for the schema.

What to do:
- keep it as the canonical import point for `StepLog` and `EpisodeLog`,
- document that downstream code should import schema types from here rather than directly depending on `envs.cre_logging`.

#### File: [isaac-training/training/runtime_logging/logger.py](../../isaac-training/training/runtime_logging/logger.py)

Role:
- stable public logger entrypoint.

What to do:
- add a factory helper such as `create_run_logger(...)`,
- centralize logger construction here,
- avoid each caller reimplementing run directory conventions.

---

### 6.2 Manual Flight Path

#### File: [isaac-training/training/unit_test/test_flight.py](../../isaac-training/training/unit_test/test_flight.py)

Role:
- standard scene inspection and manual evidence collection harness.

Current strengths:
- already binds scene metadata,
- already computes geometry-based proximity metrics,
- already writes logs through `FlightEpisodeLogger`.

What to add / tighten:
- ensure every step writes:
  - `scene_id`
  - `scenario_type`
  - `yaw_rate`
  - `goal_distance`
  - `min_obstacle_distance`
  - `near_violation_flag`
  - `out_of_bounds_flag`
  - `done_type`
- explicitly add:
  - `source = test_flight`
  - `scene_cfg_name`
- standardize manual termination reasons:
  - arena regenerate -> `manual_regen`
  - manual quit -> `manual_exit`
- keep `collision_proxy` only as an implementation detail or clearly labeled fallback,
- stop relying on legacy ad hoc per-episode files outside the canonical run directory.

Short-term acceptable simplification:
- `reward_total` may remain `0.0` or placeholder during manual flight,
  but the field must still exist.

---

### 6.3 Environment Runtime Fields

#### File: [isaac-training/training/scripts/env.py](../../isaac-training/training/scripts/env.py)

Role:
- current RL runtime environment and most important bridge to training-time evidence.

Current strengths:
- already exposes many useful fields through `stats` and `info`, including:
  - `goal_distance`
  - `min_obstacle_distance`
  - `near_violation_flag`
  - `out_of_bounds_flag`
  - `collision_flag`
  - `yaw_rate`
  - `speed_norm`
  - `reward_total`
  - reward components

What to add / tighten:
- inject scene-bound metadata:
  - `scene_id`
  - `scenario_type`
  - `scene_cfg_name`
- keep numeric `done_type` for training if needed,
  but also provide a stable string mapping for logging/export,
- freeze reward component names:
  - `reward_progress`
  - `reward_safety_static`
  - `reward_safety_dynamic`
  - `penalty_smooth`
  - `penalty_height`
- ensure `near_violation_flag` uses the same threshold as the logger,
- ensure per-episode accumulators in `stats` are stable enough for export.

Important decision:
- `env.py` should become "loggable by construction", not just a training-only environment.

---

### 6.4 Training and Evaluation Adapters

#### File: [isaac-training/training/runtime_logging/training_log_adapter.py](../../isaac-training/training/runtime_logging/training_log_adapter.py)

Role:
- adapter from TensorDict-based RL rollouts to the CRE logging schema.

Status:
- currently only a placeholder and should be filled in during this phase.

What to implement:
- conversion helpers from environment rollout data to step records,
- conversion helpers from finished episodes to episode summaries,
- mapping from numeric `done_type` in `env.py` to canonical string `done_type`,
- reward-component extraction from `info`.

Recommended API:
- `extract_step_records_from_tensordict(...)`
- `finalize_finished_episodes(...)`

This file is the key bridge that prevents `train.py` and `eval.py` from growing custom logging logic.

#### File: [isaac-training/training/scripts/train.py](../../isaac-training/training/scripts/train.py)

Role:
- RL training entrypoint.

What to add:
- create a CRE run logger at startup,
- after each collector batch:
  - extract step-level data from rollout tensors,
  - flush completed episodes into `episodes.jsonl`,
- write logs under `isaac-training/training/logs/`,
- tag outputs with `source = train`,
- optionally call run summary generation at the end of training.

What not to do:
- do not fork a second ad hoc logging format beside the CRE schema.

#### File: [isaac-training/training/scripts/eval.py](../../isaac-training/training/scripts/eval.py)

Role:
- RL evaluation entrypoint.

What to add:
- same CRE logger integration as `train.py`,
- tag outputs with `source = eval`,
- export complete evaluation trajectories,
- ensure metrics and artifacts follow the same schema as training/manual flight.

---

### 6.5 Validation and Tests

#### File: [isaac-training/training/unit_test/test_env/test_cre_logging.py](../../isaac-training/training/unit_test/test_env/test_cre_logging.py)

Role:
- unit tests for logger behavior.

What to add / verify:
- step-level field completeness,
- episode-level field completeness,
- run summary correctness,
- `done_type` resolution behavior,
- JSON export behavior.

#### File: [isaac-training/training/unit_test/test_env/test_training_log_adapter.py](../../isaac-training/training/unit_test/test_env/test_training_log_adapter.py)

Role:
- new test file for training/eval bridge logic.

What to verify:
- `env.py info/stats -> StepLog` mapping is complete,
- numeric done codes map correctly to canonical string values,
- reward components are exported consistently,
- aggregates computed from emitted logs match expectations.

---

## 7. Recommended Execution Order

The recommended implementation order is:

1. finalize the schema in `cre_logging.py`
2. expose stable public imports in `runtime_logging/schema.py` and `runtime_logging/logger.py`
3. finish `test_flight.py` integration so manual runs become the reference path
4. tighten `env.py` runtime metadata and reward-component exposure
5. implement `training_log_adapter.py`
6. integrate logging into `train.py`
7. integrate logging into `eval.py`
8. add tests for schema, adapters, and aggregates

This order minimizes risk because:

- manual flight logging already works as a partial prototype,
- `env.py` already exposes many runtime fields,
- adapters can be tested before modifying RL training loops too heavily.

---

## 8. Exit Criteria

Phase 2 is complete when all of the following are true:

1. one episode can be exported as a full trajectory artifact
2. `test_flight.py`, `train.py`, and `eval.py` all emit the same CRE log schema
3. run directories under `isaac-training/training/logs/` are sufficient to compute:
   - `success_rate`
   - `collision_rate`
   - `min_distance`
   - `average_return`
   - `near_violation_ratio`
4. no mainline execution path depends on ad hoc unit-test logging directories
5. later phases can consume these logs without custom per-script parsing

---

## 9. Non-Goals of Phase 2

Phase 2 does **not** aim to:

- implement non-RL baseline policies,
- implement witness metrics,
- implement static or dynamic analyzers,
- implement repair logic,
- redesign the RL algorithm.

Those belong to later phases.

The only purpose here is to make runtime evidence reliable and reusable.

---

## 10. What This Enables Next

Once Phase 2 is complete, the next stages become well-posed:

- Phase 3:
  build baseline execution modes on top of the same log schema
- Phase 4:
  static analyzer can rely on stable spec/runtime interfaces
- Phase 5:
  dynamic analyzer can compute witness metrics from exported logs
- Phase 7-9:
  reports, repair suggestions, and repair validation can all operate on standard artifacts

In other words:

Phase 2 is the evidence infrastructure phase.
