# Phase 9 Development Status

Updated: 2026-03-27

## 1. This Iteration Goal

This iteration closes the remaining gap between the first rerun-capable
validation loop and a more faithful bounded rerun substrate for Phase 10.

The goal of this step is:

- replace the ad hoc preview rerun task shape with more realistic bounded
  baseline / eval / train rerun adapters,
- make the rerun task metadata stable enough for future real execution
  integration,
- and lock down the consumer contract inside `post_repair_evidence.json` so
  Phase 10 can consume it deterministically.

## 2. Result

Phase 9 now has a more realistic bounded rerun adapter layer and a stronger
Phase-10-facing post-repair evidence contract.

This implementation batch added or upgraded:

- `isaac-training/training/repair/rerun_adapters.py`
- `isaac-training/training/repair/comparison.py`
- `isaac-training/training/repair/validation_runner.py`
- `isaac-training/training/repair/__init__.py`
- `isaac-training/training/scripts/run_validation_audit.py`
- `isaac-training/training/unit_test/test_env/test_validation_loop.py`
- `isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml`

The result is a deterministic path from:

- a Phase 8 repair bundle with `validation_request.json`

to:

- bounded rerun adapter tasks with mode-specific limits,
- preview-mode triggered repaired run generation that already mirrors baseline /
  eval / train execution classes,
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

### 2.2 `validation_runner.py` Now Uses the Bounded Adapter Contract

`validation_runner.py` no longer hand-builds opaque preview tasks.

It now:

- infers execution mode from accepted run evidence,
- resolves the corresponding bounded rerun adapter,
- emits mode-specific Hydra override previews,
- records adapter metadata directly inside `validation_runs.json`,
- and uses the same adapter-aware logic when synthesizing repaired run
  summaries.

This is still a preview-mode bounded rerun path, but it is no longer an ad hoc
driver. It is now a deterministic surrogate for future real reruns.

### 2.3 `comparison.py` Still Preserves Higher-Order Validation Targets

`comparison.py` was extended beyond flat summary metrics.

It now computes:

- `original_by_scenario`
- `repaired_by_scenario`

and can derive higher-order targets such as:

- `boundary_critical_success_rate`
- `critical_family_min_distance`
- `shifted_min_distance`
- `nominal_vs_shifted_success_gap`

This makes Phase 9 more aligned with the roadmap's requirement that `E-R`
repairs should be judged on family-conditioned transfer gaps, not only on
single scalar witnesses.

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

That gives later static checks and downstream phases a canonical place to read
the expected validation-side contract instead of inferring it from code shape.

### 2.6 Focused Phase 9 Tests Now Lock the Adapter and Consumer Contract

`test_validation_loop.py` was extended to verify:

- baseline / eval / train rerun tasks all emit stable bounded adapter metadata,
- the rerun task previews contain mode-specific Hydra override sets,
- the triggered rerun path still writes a complete validation bundle,
- and `post_repair_evidence.json` exposes the new Phase 10 consumer contract.

This means the current Phase 9 close-out is regression-locked by focused tests.

## 3. Main Files Added or Changed

Core implementation:

- `isaac-training/training/repair/rerun_adapters.py`
- `isaac-training/training/repair/comparison.py`
- `isaac-training/training/repair/validation_runner.py`
- `isaac-training/training/repair/__init__.py`
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
  isaac-training/training/repair/comparison.py \
  isaac-training/training/repair/validation_runner.py \
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

### 4.3 Focused Adapter / Consumer Contract Checks

Run the focused Phase 9 tests and inspect:

Expected result:

- rerun tasks include:
  - `adapter_type`
  - `script_path`
  - `hydra_overrides`
  - `bounded_limits`
- `post_repair_evidence.json` includes:
  - `evidence_schema_version = phase10_post_repair_evidence.v2`
  - `consumer_contract.contract_type = phase10_post_repair_evidence_consumer.v2`

### 4.4 Check Traceability Refresh

Open:

- `Traceability.md`

Expected result:

- the latest staged change summary includes Phase 9

## 5. Validation Results

Validated in this iteration:

- `python3 -m py_compile ...` passed
- `pytest -q ...` passed:
  - `17 passed`
- focused adapter and consumer-contract checks passed:
  - baseline tasks emit `phase9_bounded_baseline_rerun_adapter.v1`
  - eval tasks emit `phase9_bounded_eval_rerun_adapter.v1`
  - train tasks emit `phase9_bounded_train_rerun_adapter.v1`
  - `post_repair_evidence.json` now exposes `phase10_post_repair_evidence_consumer.v2`
- `Traceability.md` was refreshed for this Phase 9 implementation batch

This confirms that Phase 9 now has:

- a more realistic bounded rerun adapter substrate,
- stable mode-aware validation task metadata,
- and a stronger Phase 10 consumer contract for post-repair evidence.

## 6. What Should Be Done Next

The next Phase 9 step should be:

1. replace the current preview bounded runner with progressively more faithful
   real execution adapters,
2. broaden high-order target support beyond the current family-gap metrics,
3. finalize the Phase 10 validation consumer over the stabilized evidence
   contract.

That will move Phase 9 from a bounded validation substrate toward a true
post-repair execution validation loop.
