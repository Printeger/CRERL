# Phase 9 Development Status

Updated: 2026-03-27

## 1. This Iteration Goal

This iteration continues the Phase 9 close-out by moving the rerun path one step
closer to real execution adapters.

The goal of this step is:

- keep the existing preview path as a stable fallback,
- add a bounded subprocess-based rerun adapter path for baseline / eval / train,
- make the runtime logger honor rerun-specific environment overrides,
- and further stabilize the consumer contract for
  `post_repair_evidence.json`.

## 2. Result

Phase 9 now has the first gradual bridge from preview reruns toward real
execution adapters.

This implementation batch added or upgraded:

- `isaac-training/training/repair/rerun_adapters.py`
- `isaac-training/training/repair/validation_runner.py`
- `isaac-training/training/repair/__init__.py`
- `isaac-training/training/runtime_logging/logger.py`
- `isaac-training/training/scripts/run_validation_audit.py`
- `isaac-training/training/unit_test/test_env/test_validation_loop.py`
- `isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml`

The result is a deterministic path from:

- a Phase 8 repair bundle with `validation_request.json`

to:

- bounded rerun adapter tasks with mode-specific limits,
- a selectable `preview / auto / subprocess` rerun driver path,
- bounded subprocess task execution with preview fallback support,
- runtime logger overrides for controlled repaired run placement,
- higher-order comparison metrics,
- a machine-readable validation decision,
- and `post_repair_evidence.json` with a stable consumer contract for Phase 10.

### 2.1 `rerun_adapters.py` Defines Bounded Execution-Aware Rerun Tasks

A new rerun-adapter layer now provides explicit bounded task specs for:

- `baseline`
- `eval`
- `train`

Each adapter now declares:

- `adapter_type`
- `script_path`
- `hydra_overrides`
- `bounded_limits`
- `supports_real_execution`
- `fallback_runner_mode`

This makes the current rerun path much closer to the future real execution
adapter interface, while still keeping the current execution bounded and
deterministic.

### 2.2 `validation_runner.py` Now Supports `preview / auto / subprocess`

`validation_runner.py` no longer hand-builds opaque preview tasks.

It now:

- infers execution mode from accepted run evidence,
- resolves the corresponding bounded rerun adapter,
- emits mode-specific Hydra override previews,
- supports:
  - `preview`
  - `subprocess`
  - `auto`
- records adapter metadata directly inside `validation_runs.json`,
- and keeps preview as a deterministic fallback when real bounded subprocess
  execution is unavailable.

In `auto` mode, the runner first attempts bounded subprocess execution and only
falls back to preview if the subprocess path fails to materialize a repaired
accepted run.

### 2.3 Runtime Logging Now Honors Bounded Rerun Overrides

`runtime_logging/logger.py` now honors rerun-side environment overrides for:

- run name,
- log base directory,
- and timestamp suppression.

This matters because bounded subprocess reruns need to land repaired evidence in
deterministic, validation-owned locations instead of using the default logging
paths or timestamped run names.

### 2.4 `post_repair_evidence.json` Now Carries a Stronger Consumer Contract

The validation namespace now includes:

- `post_repair_evidence.json`

This artifact contains:

- original run refs,
- repaired run refs,
- rerun tasks,
- rerun task results,
- by-scenario summaries,
- metric deltas,
- validation decision status,
- `evidence_schema_version = phase10_post_repair_evidence.v2`,
- and `consumer_contract.contract_type = phase10_post_repair_evidence_consumer.v2`.

The consumer contract now explicitly declares:

- required top-level fields,
- required metric-delta fields,
- required run-ref fields,
- required rerun-task fields,
- required triggered-result fields,
- and Phase 10 consumer expectations.

This makes the post-repair evidence object much more stable as a downstream
handoff substrate.

### 2.5 Policy-Level Runtime Expectations Now Declare the Validation Contract

`policy_spec_v0.yaml` now exposes:

- `validation_post_repair_evidence_consumer_contract`
- `validation_supported_bounded_rerun_adapters`
- `validation_default_rerun_mode`
- `validation_preview_fallback_allowed`

That gives later static checks and downstream phases a canonical place to read
the expected validation-side contract instead of inferring it from code shape.

### 2.6 Focused Phase 9 Tests Now Lock the Adapter and Rerun Path

`test_validation_loop.py` was extended to verify:

- baseline / eval / train rerun tasks all emit stable bounded adapter metadata,
- the rerun task previews contain mode-specific Hydra override sets,
- logger creation honors rerun-side environment overrides,
- the subprocess rerun path can materialize repaired accepted runs through a
  bounded fake runner,
- the triggered rerun path still writes a complete validation bundle,
- and `post_repair_evidence.json` exposes the new Phase 10 consumer contract.

This means the current Phase 9 close-out is regression-locked by focused tests.

## 3. Main Files Added or Changed

Core implementation:

- `isaac-training/training/repair/rerun_adapters.py`
- `isaac-training/training/repair/validation_runner.py`
- `isaac-training/training/repair/__init__.py`
- `isaac-training/training/runtime_logging/logger.py`
- `isaac-training/training/scripts/run_validation_audit.py`

Contract / config:

- `isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml`

Tests:

- `isaac-training/training/unit_test/test_env/test_validation_loop.py`

Documentation / state:

- `doc/dev_log/p9_dev_status.md`
- `Traceability.md`

## 4. How To Validate

### 4.1 Syntax Validation

Run:

```bash
python3 -m py_compile \
  isaac-training/training/repair/rerun_adapters.py \
  isaac-training/training/repair/__init__.py \
  isaac-training/training/repair/validation_runner.py \
  isaac-training/training/runtime_logging/logger.py \
  isaac-training/training/scripts/run_validation_audit.py \
  isaac-training/training/unit_test/test_env/test_validation_loop.py
```

Expected result:

- no syntax error

### 4.2 Focused Unit Tests

Run:

```bash
pytest -q \
  isaac-training/training/unit_test/test_env/test_validation_loop.py \
  isaac-training/training/unit_test/test_env/test_repair_engine.py
```

Expected result:

- the existing Phase 8 repair tests still pass
- the extended Phase 9 validation-loop tests pass
- bounded adapter metadata tests pass
- subprocess rerun adapter tests pass

### 4.3 Focused Adapter / Consumer Contract Checks

Run the focused Phase 9 tests and inspect:

Expected result:

- rerun tasks include:
  - `adapter_type`
  - `script_path`
  - `hydra_overrides`
  - `bounded_limits`
- rerun tasks also include:
  - `env_overrides`
  - `expected_run_dir`
- `post_repair_evidence.json` includes:
  - `evidence_schema_version = phase10_post_repair_evidence.v2`
  - `consumer_contract.contract_type = phase10_post_repair_evidence_consumer.v2`
- logger creation respects:
  - `CRE_RUN_NAME_OVERRIDE`
  - `CRE_RUN_LOG_BASE_DIR`
  - `CRE_RUN_USE_TIMESTAMP`

### 4.4 Check Traceability Refresh

Open:

- `Traceability.md`

Expected result:

- the latest staged change summary includes Phase 9

## 5. Validation Results

Validated in this iteration:

- `python3 -m py_compile ...` passed
- `pytest -q ...` passed:
  - `19 passed`
- focused adapter and consumer-contract checks passed:
  - baseline tasks emit `phase9_bounded_baseline_rerun_adapter.v1`
  - eval tasks emit `phase9_bounded_eval_rerun_adapter.v1`
  - train tasks emit `phase9_bounded_train_rerun_adapter.v1`
  - bounded subprocess reruns can complete without fallback when a repaired run
    is materialized
  - logger environment overrides place repaired runs under deterministic
    validation-owned paths
  - `post_repair_evidence.json` now exposes `phase10_post_repair_evidence_consumer.v2`
- `Traceability.md` was refreshed for this Phase 9 implementation batch

This confirms that Phase 9 now has:

- a more realistic bounded rerun adapter substrate,
- a first subprocess-capable rerun path,
- stable mode-aware validation task metadata,
- and a stronger Phase 10 consumer contract for post-repair evidence.

## 6. What Should Be Done Next

The next Phase 9 step should be:

1. continue replacing the preview runner with progressively more faithful
   bounded real execution adapters,
2. broaden high-order target support beyond the current family-gap metrics,
3. finalize the Phase 10 validation consumer over the stabilized evidence
   contract.

That will move Phase 9 from a bounded validation substrate toward a true
post-repair execution validation loop.
