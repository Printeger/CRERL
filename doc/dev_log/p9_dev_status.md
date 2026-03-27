# Phase 9 Development Status

Updated: 2026-03-27

## 1. This Iteration Goal

This iteration continues the Phase 9 close-out by pushing the bounded rerun path
closer to real repaired execution validation.

The goal of this step is:

- make bounded subprocess reruns resolve real accepted run directories instead
  of treating directory existence as success,
- ensure rerun-triggered metadata stays aligned with the requested
  `scenario_type / scene_cfg_name / scene_id_prefix`,
- and broaden Phase 9 comparison beyond the first success-gap metric.

## 2. Result

Phase 9 now has a stronger repaired-execution validation path and richer
comparison targets.

This implementation batch added or upgraded:

- `isaac-training/training/repair/rerun_adapters.py`
- `isaac-training/training/repair/comparison.py`
- `isaac-training/training/repair/validation_runner.py`
- `isaac-training/training/repair/__init__.py`
- `isaac-training/training/runtime_logging/logger.py`
- `isaac-training/training/runtime_logging/training_log_adapter.py`
- `isaac-training/training/scripts/run_validation_audit.py`
- `isaac-training/training/unit_test/test_env/test_validation_loop.py`
- `isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml`

The result is a deterministic path from:

- a Phase 8 repair bundle with `validation_request.json`

to:

- bounded rerun adapter tasks with mode-specific limits,
- a selectable `preview / auto / subprocess` rerun driver path,
- bounded subprocess task execution that resolves and acceptance-checks repaired
  run directories,
- runtime metadata overrides that keep repaired logs aligned with validation
  intent,
- richer higher-order comparison metrics,
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

### 2.2 `validation_runner.py` Now Resolves Accepted Repaired Runs

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
- resolves repaired run directories via:
  - expected deterministic path
  - or accepted-run discovery under the rerun logs root,
- runs acceptance over the subprocess-produced run,
- and only treats subprocess rerun as successful once a repaired accepted run is
  actually materialized.

In `auto` mode, the runner first attempts bounded subprocess execution and only
falls back to preview if the subprocess path fails to materialize a repaired
accepted run.

### 2.3 Runtime Logging and Training Metadata Now Honor Validation Overrides

`runtime_logging/logger.py` now honors rerun-side environment overrides for:

- run name,
- log base directory,
- and timestamp suppression.

`runtime_logging/training_log_adapter.py` now also honors validation-side
overrides for:

- `scenario_type`
- `scene_cfg_name`
- `scene_id_prefix`

This matters because bounded subprocess reruns need repaired evidence to stay
both:

- in deterministic validation-owned run directories,
- and semantically aligned with the intended rerun family/config.

### 2.4 `comparison.py` Now Computes Richer High-Order Targets

Phase 9 comparison is no longer limited to:

- `nominal_vs_shifted_success_gap`

It now also derives:

- `nominal_vs_shifted_min_distance_gap`
- `nominal_vs_shifted_collision_gap`
- `nominal_vs_shifted_near_violation_gap`
- `nominal_vs_shifted_return_gap`
- `boundary_critical_collision_rate`
- `boundary_critical_near_violation_ratio`
- `boundary_critical_vs_nominal_success_gap`
- `boundary_critical_vs_nominal_min_distance_gap`

It also emits:

- `original_by_source`
- `repaired_by_source`

This gives Phase 9 a stronger basis for family-conditioned repair validation.

### 2.5 `post_repair_evidence.json` Still Carries the Strong Consumer Contract

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

### 2.6 Policy-Level Runtime Expectations Now Declare More of the Validation Contract

`policy_spec_v0.yaml` now exposes:

- `validation_post_repair_evidence_consumer_contract`
- `validation_supported_bounded_rerun_adapters`
- `validation_default_rerun_mode`
- `validation_preview_fallback_allowed`
- `validation_subprocess_rerun_acceptance_required`
- `validation_high_order_targets`

That gives later static checks and downstream phases a canonical place to read
the expected validation-side contract instead of inferring it from code shape.

### 2.7 Focused Phase 9 Tests Now Lock the Adapter, Metadata, and Comparison Path

`test_validation_loop.py` was extended to verify:

- baseline / eval / train rerun tasks all emit stable bounded adapter metadata,
- the rerun task previews contain mode-specific Hydra override sets,
- logger creation honors rerun-side environment overrides,
- training metadata extraction honors validation-side scene overrides,
- the subprocess rerun path can materialize and acceptance-check repaired
  accepted runs through a bounded fake runner,
- the new high-order comparison targets are derived correctly,
- the triggered rerun path still writes a complete validation bundle,
- and `post_repair_evidence.json` exposes the new Phase 10 consumer contract.

This means the current Phase 9 close-out is regression-locked by focused tests.

## 3. Main Files Added or Changed

Core implementation:

- `isaac-training/training/repair/rerun_adapters.py`
- `isaac-training/training/repair/comparison.py`
- `isaac-training/training/repair/validation_runner.py`
- `isaac-training/training/repair/__init__.py`
- `isaac-training/training/runtime_logging/logger.py`
- `isaac-training/training/runtime_logging/training_log_adapter.py`
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
  isaac-training/training/repair/comparison.py \
  isaac-training/training/repair/rerun_adapters.py \
  isaac-training/training/repair/__init__.py \
  isaac-training/training/repair/validation_runner.py \
  isaac-training/training/runtime_logging/logger.py \
  isaac-training/training/runtime_logging/training_log_adapter.py \
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

### 4.3 Focused Adapter / Comparison / Consumer Contract Checks

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
- subprocess rerun results include:
  - `acceptance_passed`
  - `detected_via`
- comparison output includes:
  - richer `nominal_vs_shifted_*` gap metrics
  - `boundary_critical_vs_nominal_*` gap metrics
  - `original_by_source`
  - `repaired_by_source`
- `post_repair_evidence.json` includes:
  - `evidence_schema_version = phase10_post_repair_evidence.v2`
  - `consumer_contract.contract_type = phase10_post_repair_evidence_consumer.v2`
- logger creation respects:
  - `CRE_RUN_NAME_OVERRIDE`
  - `CRE_RUN_LOG_BASE_DIR`
  - `CRE_RUN_USE_TIMESTAMP`
- training metadata extraction respects:
  - `CRE_VALIDATION_SCENARIO_TYPE`
  - `CRE_VALIDATION_SCENE_CFG_NAME`
  - `CRE_VALIDATION_SCENE_ID_PREFIX`

### 4.4 Check Traceability Refresh

Open:

- `Traceability.md`

Expected result:

- the latest staged change summary includes Phase 9

## 5. Validation Results

Validated in this iteration:

- `python3 -m py_compile ...` passed
- `pytest -q ...` passed:
  - `20 passed, 1 skipped`
- focused adapter, comparison, and consumer-contract checks passed:
  - baseline tasks emit `phase9_bounded_baseline_rerun_adapter.v1`
  - eval tasks emit `phase9_bounded_eval_rerun_adapter.v1`
  - train tasks emit `phase9_bounded_train_rerun_adapter.v1`
  - bounded subprocess reruns can complete without fallback once a repaired run
    passes acceptance
  - logger environment overrides place repaired runs under deterministic
    validation-owned paths
  - training metadata extraction honors validation-side family/config overrides
  - richer `nominal_vs_shifted_*` and `boundary_critical_vs_nominal_*` targets
    are present
  - `post_repair_evidence.json` now exposes `phase10_post_repair_evidence_consumer.v2`
- one metadata override test is skipped under system Python when `torch` is not
  available
- `Traceability.md` was refreshed for this Phase 9 implementation batch

This confirms that Phase 9 now has:

- a more realistic bounded rerun adapter substrate,
- a first subprocess-capable rerun path,
- acceptance-aware repaired run resolution,
- richer family-conditioned validation metrics,
- stable mode-aware validation task metadata,
- and a stronger Phase 10 consumer contract for post-repair evidence.

## 6. What Should Be Done Next

The next Phase 9 step should be:

1. continue replacing the preview runner with progressively more faithful
   bounded real execution adapters,
2. broaden high-order target support beyond the current family-gap metrics and
   integrate them into decision policy where useful,
3. finalize the Phase 10 validation consumer over the stabilized evidence
   contract.

That will move Phase 9 from a bounded validation substrate toward a true
post-repair execution validation loop.
