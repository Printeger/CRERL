# Phase 3: Baseline Execution and Acceptance-Gated Rollouts

## 1. Purpose

Phase 3 is the stage where the project moves from
"we can emit unified CRE logs"
to
"we can produce comparable evidence from multiple execution modes."

The direct goal of this phase is to add stable non-RL baseline execution paths
on top of the scene-family backend and the Phase 2 log schema.

However, before baseline runners are added, we need one short gating step:

- perform a directory-level aggregation audit on the existing log outputs,
- add one unified run-level acceptance check,
- use that acceptance check to verify that:
  - `test_flight.py`
  - `train.py`
  - `eval.py`
  all emit analyzable CRE artifacts.

Without that gate, Phase 3 would be built on top of logs that are unified in code
but not yet fully accepted as stable evidence.

This phase corresponds to:

- [doc/roadmap.md](../roadmap.md) `Phase 3. Build baseline execution modes`
- [doc/system_architecture_and _control_flow.md](../system_architecture_and%20_control_flow.md) `Layer C. Execution and Logging Layer`
- [doc/system_architecture_and _control_flow.md](../system_architecture_and%20_control_flow.md) `Layer D. Analyzer Layer`

---

## 2. Why Phase 3 Starts with an Acceptance Gate

Phase 2 already introduced:

- a canonical run directory layout,
- unified step and episode schemas,
- shared runtime metadata export,
- run-level aggregation.

What is still missing is a formal answer to:

`when is a run directory good enough to be consumed by later analyzers?`

That question must be answered before baseline execution modes are added.

So Phase 3 begins with a short "Phase 2 close-out" work package:

1. run directory aggregation audit
2. run-level acceptance check
3. acceptance validation on:
   - one manual-flight run
   - one short evaluation run
   - one short training run

Only after that gate passes do we treat the runtime evidence stack as Phase-3-ready.

---

## 3. Immediate Work Package: Acceptance Before Baselines

### 3.1 Goal

Create a single acceptance mechanism that checks whether a run directory under:

`isaac-training/training/logs/<run_id>/`

is complete, schema-valid, and numerically self-consistent.

### 3.2 Required Outcome

For each run directory, the system should be able to produce:

- an `acceptance.json` report,
- a boolean pass/fail decision,
- a list of failed checks,
- a compact metrics summary suitable for later analyzer ingestion.

### 3.3 Why This Matters

This turns Phase 2 artifacts from
"logs we believe are probably usable"
into
"logs that have passed a reproducible gate."

That gate is what will make later baseline comparisons, witness metrics,
and analyzer outputs trustworthy.

---

## 4. Scope of the Acceptance Check

The acceptance check should validate five things:

### 4.1 Artifact Completeness

The run directory contains:

- `manifest.json`
- `steps.jsonl`
- `episodes.jsonl`
- `summary.json`
- `episodes/`

and at least one episode artifact exists.

### 4.2 Schema Completeness

Each step record must include at least:

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

Each episode record must include at least:

- `episode_index`
- `seed`
- `scene_id`
- `scenario_type`
- `scene_cfg_name`
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
- `source`

### 4.3 Cross-File Consistency

The acceptance check should verify:

- `summary.json` matches metrics recomputed from `episodes.jsonl`
- `episode_XXXX.json` summaries agree with their corresponding `episodes.jsonl` rows
- `scene_cfg_name` is not missing or inconsistent across steps and episode summaries
- `source` is stable within a run

### 4.4 Semantic Consistency

The acceptance check should verify:

- `done_type` values come from the canonical set:
  - `running`
  - `success`
  - `collision`
  - `out_of_bounds`
  - `truncated`
  - `manual_regen`
  - `manual_exit`
  - `unknown`
- `reward_components` always include the standard component keys
- `near_violation_ratio` is consistent with `near_violation_steps / num_steps`
- `collision_flag`, `out_of_bounds_flag`, and `done_type` are not obviously contradictory

### 4.5 Run-Level Metric Sufficiency

The acceptance check must confirm that the run directory is sufficient to compute:

- `success_rate`
- `collision_rate`
- `min_distance`
- `average_return`
- `near_violation_ratio`

These are the minimum aggregate metrics Phase 3 baselines must share.

---

## 5. File-Level Implementation Plan

### 5.1 Run Acceptance Core

#### File: `isaac-training/training/runtime_logging/acceptance.py`

Role:

- canonical implementation of run-level acceptance checks

What to implement:

- a small acceptance result schema, for example:
  - `passed`
  - `checks`
  - `errors`
  - `metrics`
  - `run_dir`
  - `source`
- functions such as:
  - `validate_run_directory(run_dir)`
  - `validate_step_schema(step_record)`
  - `validate_episode_schema(episode_record)`
  - `compare_summary_against_episodes(run_dir)`
  - `write_acceptance_report(run_dir, result)`

Important design decision:

- this module should remain deterministic and non-LLM
- it is infrastructure, not diagnosis logic

### 5.2 Logger Export Layer

#### File: `isaac-training/training/runtime_logging/logger.py`

What to add:

- export the acceptance helpers from the stable runtime logging API
- keep downstream callers from importing ad hoc internal modules

Possible additions:

- `load_run_summary(run_dir)`
- `run_acceptance_check(run_dir)`

### 5.3 Existing Logger Semantics

#### File: `isaac-training/training/envs/cre_logging.py`

What to verify or tighten if needed:

- summary metric recomputation stays deterministic
- `reward_components_total` is stable across runs
- episode summary generation never omits canonical fields
- `summary.json` is always regeneration-safe from `episodes.jsonl`

This file should remain the semantic owner of the raw log schema.

### 5.4 Manual Flight Validation Path

#### File: `isaac-training/training/unit_test/test_flight.py`

What to add:

- optional end-of-run acceptance invocation
- print the acceptance decision and failed checks
- ensure manual quit and regenerate flows still produce acceptable artifacts

Short-term acceptable simplification:

- the acceptance check may run only when an episode was actually exported

### 5.5 Training and Evaluation Paths

#### File: `isaac-training/training/scripts/train.py`

What to add:

- run the acceptance check on the final training run directory
- log pass/fail and core metrics to stdout and WandB

#### File: `isaac-training/training/scripts/eval.py`

What to add:

- same acceptance check invocation as `train.py`
- fail loudly if evaluation logs are structurally incomplete

### 5.6 Tests

#### File: `isaac-training/training/unit_test/test_env/test_run_acceptance.py`

New test file.

What to verify:

- valid run directory passes acceptance
- missing `manifest.json` fails
- missing required step fields fails
- inconsistent `summary.json` fails
- missing standard reward component keys fails
- invalid `done_type` fails

#### File: `isaac-training/training/unit_test/test_env/test_cre_logging.py`

Add or tighten:

- summary recomputation expectations
- cross-file consistency checks

#### File: `isaac-training/training/unit_test/test_env/test_training_log_adapter.py`

Add or tighten:

- emitted `done_type` values remain canonical
- emitted `scene_cfg_name` remains stable
- emitted reward components remain complete across all records

---

## 6. Directory-Level Aggregation Audit Plan

Before writing baseline policies, we should perform one audit over real run directories.

The audit set should include:

1. one `test_flight.py` run
2. one short `eval.py` run
3. one short `train.py` run

For each run directory:

- recompute aggregates from `episodes.jsonl`
- compare against `summary.json`
- run the acceptance check
- save `acceptance.json`

Expected output per run:

- `pass/fail`
- failed check names if any
- recomputed aggregate metrics
- run metadata:
  - `source`
  - `scene_cfg_name`
  - `scenario_type`

This audit is the explicit close-out step for Phase 2.

---

## 7. Phase-3 Proper: Baseline Execution Modes

Once the acceptance gate is in place, Phase 3 proceeds with baseline execution.

### 7.1 Goal

Provide non-RL baselines that produce CRE logs under the same schema as:

- manual flight
- RL training
- RL evaluation

### 7.2 Baselines to Add

- random policy
- greedy-to-goal policy
- conservative avoider policy

### 7.3 Files to Implement Next

#### File: `isaac-training/training/execution/baseline_policies.py`

What to do:

- replace placeholders with concrete policies
- keep policies pure and deterministic when seeded

#### File: `isaac-training/training/execution/baseline_runner.py`

New file.

What to do:

- load scene families
- execute a chosen baseline over a seeded batch of scenes
- write logs through the same runtime logger

#### File: `isaac-training/training/scripts/run_baseline.py`

New file.

What to do:

- provide a CLI entrypoint for baseline rollouts
- save outputs into `isaac-training/training/logs/`
- invoke the run-level acceptance check at the end

---

## 8. Recommended Execution Order

The recommended order is:

1. implement `runtime_logging/acceptance.py`
2. add `test_run_acceptance.py`
3. wire acceptance invocation into:
   - `test_flight.py`
   - `train.py`
   - `eval.py`
4. run the three-path directory audit
5. fix any remaining schema or summary inconsistencies
6. implement concrete baseline policies
7. add a baseline runner
8. add a baseline CLI entrypoint

This order keeps Phase 3 grounded in accepted artifacts rather than best-effort logs.

---

## 9. Exit Criteria

Phase 3 should be considered complete only when all of the following are true:

1. every mainline run directory can produce an `acceptance.json`
2. `test_flight.py`, `train.py`, and `eval.py` all pass the acceptance gate
3. at least three baseline modes exist:
   - random
   - greedy
   - conservative
4. baseline runs write the same canonical CRE artifacts as RL/manual runs
5. baseline logs show distinguishable safety/performance tradeoffs

---

## 10. Non-Goals

Phase 3 does **not** yet implement:

- witness metrics
- static inconsistency detection
- dynamic inconsistency diagnosis
- LLM semantic diagnosis
- repair suggestion

This phase is still about producing trustworthy comparable evidence.

---

## 11. What This Enables Next

Once this phase is complete:

- Phase 4 can consume accepted run directories rather than raw logs
- dynamic witness computation can compare RL and non-RL baselines directly
- analyzer code no longer needs per-script parsing logic
- later repair validation can use the same acceptance gate as a first sanity check

In short:

Phase 3 is the "accepted evidence plus baseline comparison" phase.
