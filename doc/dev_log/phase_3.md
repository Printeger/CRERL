# Phase 3 Development Log

Updated: 2026-03-26

## This Iteration

This iteration implements the first concrete work item from:

- `doc/roadmap/phase3.md`

The implemented scope is:

- `isaac-training/training/runtime_logging/acceptance.py`
- corresponding unit tests for run-level acceptance checks
- stable logger-layer exports for the new acceptance helpers

## Result

The repository now has a deterministic run-level acceptance module that can validate a CRE log run directory under:

- `isaac-training/training/logs/<run_id>/`

The new acceptance check covers:

- artifact completeness
- step schema completeness
- episode schema completeness
- summary consistency against `episodes.jsonl`
- cross-file consistency
- canonical `done_type` validation
- standard reward-component key validation
- run-level metric sufficiency

It can also write:

- `acceptance.json`

into the run directory as a machine-readable acceptance report.

## Main Code Added

### Runtime Acceptance Core

- `isaac-training/training/runtime_logging/acceptance.py`

Implemented public helpers include:

- `load_run_summary(...)`
- `validate_step_schema(...)`
- `validate_episode_schema(...)`
- `compare_summary_against_episodes(...)`
- `validate_run_directory(...)`
- `write_acceptance_report(...)`
- `run_acceptance_check(...)`

### Stable Export Layer

- `isaac-training/training/runtime_logging/logger.py`

This file now re-exports the acceptance API so later callers do not need ad hoc internal imports.

### Tests

- `isaac-training/training/unit_test/test_env/test_run_acceptance.py`

This test file verifies:

- valid run directory passes
- missing `manifest.json` fails
- missing required step field fails
- inconsistent `summary.json` fails
- missing standard reward-component keys fails
- invalid `done_type` fails

## How To Validate

### 1. Syntax Check

Run:

```bash
python -m py_compile \
  isaac-training/training/runtime_logging/acceptance.py \
  isaac-training/training/runtime_logging/logger.py \
  isaac-training/training/unit_test/test_env/test_run_acceptance.py
```

Expected result:

- no syntax errors

### 2. Acceptance and Logger Unit Tests

Run:

```bash
pytest -q \
  isaac-training/training/unit_test/test_env/test_cre_logging.py \
  isaac-training/training/unit_test/test_env/test_run_acceptance.py
```

Expected result:

- all tests pass

## Validation Results

Validation run on 2026-03-26:

### `py_compile`

Result:

- passed

### `pytest`

Command:

```bash
pytest -q \
  isaac-training/training/unit_test/test_env/test_cre_logging.py \
  isaac-training/training/unit_test/test_env/test_run_acceptance.py
```

Result:

- `9 passed`

## What This Enables Next

With the acceptance module now in place, the next Phase 3 step is:

- wire `run_acceptance_check(...)` into:
  - `test_flight.py`
  - `train.py`
  - `eval.py`

After that, we should perform the first real directory-level audit over:

- one manual-flight run
- one short evaluation run
- one short training run

Only then should the project move on to:

- concrete non-RL baseline policies
- baseline runner
- baseline CLI entrypoint
