# Phase 3 Development Status

Updated: 2026-03-26

## 1. Phase Goal

The current Phase 3 close-out task is:

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

- "the main execution entrypoints all emit accepted CRE run directories under the same schema"

## 2. Implemented Results

### 2.1 Acceptance Is Wired Into All Three Entry Paths

The following entrypoints now invoke run-level acceptance after writing CRE logs:

- `isaac-training/training/unit_test/test_flight.py`
- `isaac-training/training/scripts/train.py`
- `isaac-training/training/scripts/eval.py`

The acceptance report is written as:

- `acceptance.json`

inside the run directory for all three paths.

### 2.2 Manual Flight Path Supports Bounded Audit Runs

`test_flight.py` supports:

- `+test_flight.auto_exit_steps=<N>`
- `+test_flight.auto_goal_on_start=<bool>`
- `+test_flight.auto_acceptance_on_exit=<bool>`

This makes it possible to run a bounded manual-flight audit in headless mode and immediately validate the generated run directory.

### 2.3 Train/Eval Paths Now Finish Real Audit Runs

The short audit runs now complete end-to-end instead of stalling before logger finalization.

Key fixes landed in the runtime path:

- `env.py`
  - lightweight Orbit shim coverage was extended so the legacy training env can start without re-entering the full Orbit converter/Nucleus dependency chain
  - the LiDAR base-link path now follows the configured drone model instead of hardcoding `Hummingbird_0`
- `training_log_adapter.py`
  - fixed TensorDict truthiness handling in rollout extraction
- `train.py`
  - when `+skip_periodic_eval=True`, no empty `train_eval_rollout` run directory is created anymore

### 2.4 Phase 3 Close-Out Result

The three-path directory-level audit target is now achieved:

- one accepted `test_flight` run directory
- one accepted short `eval` run directory
- one accepted short `train` run directory

All three runs emit the same CRE run artifact set:

- `manifest.json`
- `steps.jsonl`
- `episodes.jsonl`
- `summary.json`
- `acceptance.json`

## 3. Main Files Changed

Code files:

- `isaac-training/training/scripts/env.py`
- `isaac-training/training/runtime_logging/training_log_adapter.py`
- `isaac-training/training/scripts/train.py`

Documentation/state files:

- `doc/dev_log/p3_dev_status.md`
- `Traceability.md`

## 4. How To Validate

### 4.1 Syntax Validation

Run:

```bash
python -m py_compile \
  isaac-training/training/scripts/env.py \
  isaac-training/training/runtime_logging/training_log_adapter.py \
  isaac-training/training/scripts/train.py \
  isaac-training/training/scripts/eval.py \
  isaac-training/training/runtime_logging/acceptance.py \
  isaac-training/training/unit_test/test_env/test_run_acceptance.py
```

Expected result:

- no syntax error

### 4.2 Acceptance Unit Test

Run:

```bash
pytest -q isaac-training/training/unit_test/test_env/test_run_acceptance.py
```

Expected result:

- all tests pass

### 4.3 Manual Flight Directory-Level Audit

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
- `acceptance.json` reports `"passed": true`

### 4.4 Short Eval Directory-Level Audit

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
  max_frame_num=1 \
  algo.training_frame_num=1 \
  +checkpoint_path=./wandb/offline-run-20260326_180500-tw5zsid8/files/checkpoint_final.pt
```

What to verify:

- a new `eval_rollout_<timestamp>` directory appears under:
  - `isaac-training/training/logs/`
- the run directory contains:
  - `manifest.json`
  - `steps.jsonl`
  - `episodes.jsonl`
  - `summary.json`
  - `acceptance.json`
- `acceptance.json` reports `"passed": true`

### 4.5 Short Train Directory-Level Audit

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

- a new `train_rollout_<timestamp>` directory appears under:
  - `isaac-training/training/logs/`
- the run directory contains:
  - `manifest.json`
  - `steps.jsonl`
  - `episodes.jsonl`
  - `summary.json`
  - `acceptance.json`
- `acceptance.json` reports `"passed": true`
- no empty `train_eval_rollout_*` directory is produced for this short-run mode

## 5. Validation Results

Validation run on 2026-03-26:

### 5.1 `py_compile`

Command:

```bash
python -m py_compile \
  isaac-training/training/scripts/env.py \
  isaac-training/training/runtime_logging/training_log_adapter.py \
  isaac-training/training/scripts/train.py \
  isaac-training/training/scripts/eval.py \
  isaac-training/training/runtime_logging/acceptance.py \
  isaac-training/training/unit_test/test_env/test_run_acceptance.py
```

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

Acceptance result:

- passed

Observed metrics:

- `episode_count = 1`
- `success_rate = 0.0`
- `collision_rate = 0.0`
- `min_distance = 3.514289379119873`
- `average_return = 0.0`
- `near_violation_ratio = 0.0`

### 5.4 Short Eval Audit

Observed run directory:

- `isaac-training/training/logs/eval_rollout_20260326_180829`

Acceptance result:

- passed

Observed metrics:

- `episode_count = 1`
- `success_rate = 0.0`
- `collision_rate = 0.0`
- `min_distance = 0.9031753540039062`
- `average_return = 3.834489345550537`
- `near_violation_ratio = 0.0`

### 5.5 Short Train Audit

Observed run directory:

- `isaac-training/training/logs/train_rollout_20260326_180849`

Acceptance result:

- passed

Observed metrics:

- `episode_count = 1`
- `success_rate = 0.0`
- `collision_rate = 0.0`
- `min_distance = 0.5617828369140625`
- `average_return = 3.356431007385254`
- `near_violation_ratio = 0.0`

Additional observation:

- no `train_eval_rollout_20260326_1808*` directory was created in the short-train run after the `+skip_periodic_eval=True` guard fix

## 6. Current Conclusion

This Phase 3 close-out target is complete:

- run-level acceptance is wired into all three main execution paths
- all three paths have produced real accepted CRE run directories
- Phase 2 logging is now not only schema-consistent in code, but also validated at directory level on real entrypoint executions

## 7. What To Do Next

The next step is to move from logging/acceptance infrastructure into baseline execution:

- implement `Phase 3 baseline execution modes`
  - `random`
  - `greedy`
  - `conservative`
- make those baselines emit the same CRE run directories
- run the same acceptance and aggregation checks on baseline outputs

After that, the project can start the first analyzer implementation on top of a stable multi-source log stream.
