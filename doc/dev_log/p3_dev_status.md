# Phase 3 Development Status

Updated: 2026-03-26

## 1. Phase Goal

The current Phase 3 entry task is:

- wire `run_acceptance_check(...)` into the three main execution paths
  - `isaac-training/training/unit_test/test_flight.py`
  - `isaac-training/training/scripts/train.py`
  - `isaac-training/training/scripts/eval.py`
- then perform one real directory-level audit for each path
  - one manual flight run
  - one short evaluation run
  - one short training run

The purpose of this step is to move from:

- "the acceptance checker exists as a library"

to:

- "the main execution entrypoints either emit accepted CRE run directories or expose the real runtime blocker clearly"

## 2. Implemented Results

### 2.1 Acceptance Is Now Wired Into All Three Entry Paths

The following entrypoints now invoke run-level acceptance after writing CRE logs:

- `isaac-training/training/unit_test/test_flight.py`
- `isaac-training/training/scripts/train.py`
- `isaac-training/training/scripts/eval.py`

The acceptance report is written as:

- `acceptance.json`

inside the run directory whenever the run directory exists and the path reaches logger finalization.

### 2.2 Manual Flight Path Supports Automated Exit and Audit

`test_flight.py` now supports:

- `+test_flight.auto_exit_steps=<N>`
- `+test_flight.auto_goal_on_start=<bool>`
- `+test_flight.auto_acceptance_on_exit=<bool>`

This makes it possible to run a bounded manual-flight audit in headless mode and immediately validate the generated run directory.

### 2.3 Train/Eval Paths Have Minimal Audit-Oriented Knobs

To support short audit runs:

- `train.py` now supports `+skip_periodic_eval=True`
- `eval.py` now supports `+checkpoint_path=...`

These changes make it possible to run short audit-oriented entrypoint invocations without being forced into the normal long evaluation cadence or a hard-coded checkpoint path.

### 2.4 The Remaining Runtime Blocker Is Now Narrowed Down

During real short `train.py` and `eval.py` audit attempts, the failure point is no longer the Phase 3 acceptance logic.

The current blocker is the legacy Orbit import chain reached by:

- `training/scripts/env.py`
- `omni.isaac.orbit.sim.__init__`
- `sim/converters/...`
- `omni.isaac.orbit.utils.assets`
- `omni.isaac.core.utils.nucleus.get_assets_root_path()`

This means:

- Phase 3 acceptance wiring is in place
- real `train/eval` directory-level acceptance is still blocked by runtime startup dependencies in the legacy training stack

## 3. Main Files Changed

Code files:

- `isaac-training/training/scripts/train.py`
- `isaac-training/training/scripts/eval.py`
- `isaac-training/training/unit_test/test_flight.py`
- `isaac-training/training/scripts/env.py`

Documentation/state files:

- `doc/dev_log/p3_dev_status.md`
- `Traceability.md`

## 4. How To Validate

### 4.1 Syntax Validation

Run:

```bash
python -m py_compile \
  isaac-training/training/scripts/env.py \
  isaac-training/training/scripts/train.py \
  isaac-training/training/scripts/eval.py \
  isaac-training/training/unit_test/test_flight.py
```

Expected result:

- no syntax error

### 4.2 Manual Flight Directory-Level Audit

Run from `isaac-training/`:

```bash
source /home/mint/rl_dev/setup_conda_env.sh
/home/mint/miniconda3/envs/NavRL/bin/python \
  training/unit_test/test_flight.py \
  headless=True \
  +test_flight.auto_exit_steps=5 \
  +test_flight.auto_acceptance_on_exit=True
```

What to verify:

- a new `test_flight_<timestamp>` directory appears under:
  - `isaac-training/training/logs/`
- the run directory contains:
  - `manifest.json`
  - `steps.jsonl`
  - `episodes.jsonl`
  - `summary.json`
  - `acceptance.json`

### 4.3 Short Train Audit Attempt

Run from `isaac-training/`:

```bash
source /home/mint/rl_dev/setup_conda_env.sh
export HYDRA_FULL_ERROR=1
/home/mint/miniconda3/envs/NavRL/bin/python \
  training/scripts/train.py \
  headless=True \
  wandb.mode=offline \
  env.num_envs=1 \
  env.max_episode_length=20 \
  env_dyn.num_obstacles=0 \
  max_frame_num=1 \
  algo.training_frame_num=1 \
  algo.training_epoch_num=1 \
  algo.num_minibatches=1 \
  +skip_periodic_eval=True
```

What to verify:

- either a `train_*` CRE log run directory is produced and validated
- or the process exposes a reproducible runtime blocker before logger finalization

### 4.4 Short Eval Audit Attempt

Run from `isaac-training/`:

```bash
source /home/mint/rl_dev/setup_conda_env.sh
export HYDRA_FULL_ERROR=1
/home/mint/miniconda3/envs/NavRL/bin/python \
  training/scripts/eval.py \
  headless=True \
  wandb.mode=offline \
  env.num_envs=1 \
  env.max_episode_length=20 \
  env_dyn.num_obstacles=0 \
  +checkpoint_path=./wandb/offline-run-20251209_201022-c9so0klx/files/checkpoint_final.pt
```

What to verify:

- either an `eval_*` CRE log run directory is produced and validated
- or the process exposes a reproducible runtime blocker before logger finalization

## 5. Validation Results

Validation run on 2026-03-26:

### 5.1 `py_compile`

Result:

- passed

### 5.2 Acceptance Unit Test

Command:

```bash
pytest -q isaac-training/training/unit_test/test_env/test_run_acceptance.py
```

Result:

- `6 passed`

### 5.3 Manual Flight Audit

Observed run directory:

- `isaac-training/training/logs/test_flight_20260326_172937`

Observed artifacts:

- `manifest.json`
- `steps.jsonl`
- `episodes.jsonl`
- `summary.json`
- `acceptance.json`

Acceptance result:

- passed

Observed metrics:

- `episode_count = 1`
- `done_type_counts = {"manual_exit": 1}`
- `min_distance = 3.514289379119873`
- `collision_rate = 0.0`
- `near_violation_ratio = 0.0`

### 5.4 Short Train Audit

Result:

- startup reached Isaac Sim and WandB offline run creation
- no CRE training run directory was produced
- audit did not reach logger finalization

Observed blocker:

- runtime import chain enters `omni.isaac.orbit.sim.__init__`
- this triggers `sim/converters` and then `omni.isaac.orbit.utils.assets`
- the process blocks on `omni.isaac.core.utils.nucleus.get_assets_root_path()`

Current conclusion:

- acceptance integration is not the blocker
- the legacy training stack still has a runtime startup dependency that must be isolated before real train-run acceptance can pass

### 5.5 Short Eval Audit

Result:

- startup reached Isaac Sim and WandB offline run creation
- no CRE evaluation run directory was produced
- audit did not reach logger finalization

Observed blocker:

- same Orbit/Nucleus import chain as the short-train path

Current conclusion:

- the short-eval path is blocked by the same legacy runtime dependency

## 6. Current Status

Phase 3 entrypoint acceptance wiring is now complete at the code level.

Real directory-level audit status is:

- `test_flight.py`: passed
- `train.py`: blocked by runtime startup dependency
- `eval.py`: blocked by runtime startup dependency

So this Phase 3 subtask is only partially closed:

- acceptance integration: done
- three-path real acceptance closure: not yet done

## 7. What To Do Next

The next task should be:

- isolate or remove the legacy Orbit `sim/__init__ -> converters -> nucleus` dependency from the training/eval startup path

Recommended next step:

1. narrow `env.py` imports further so training/eval do not pull the full Orbit converter stack during startup
2. rerun one short `train.py` audit
3. rerun one short `eval.py` audit
4. confirm both now emit valid run directories with `acceptance.json`

Only after that should Phase 3 continue to:

- non-RL baseline policies
- baseline runner
- baseline CLI
