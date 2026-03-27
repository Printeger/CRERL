# Phase 9 Development Status

Updated: 2026-03-27

## 1. This Iteration Goal

This iteration advances Phase 9 from the first validation bundle kernel to the
first rerun-capable validation loop.

The goal of this step is:

- push `validation_runner.py` from "read already-existing repaired runs"
  toward "trigger targeted reruns",
- add higher-order comparison targets such as
  `nominal_vs_shifted_success_gap`,
- and stabilize a post-repair evidence artifact that Phase 10 can consume
  directly.

## 2. Result

Phase 9 now has a first rerun-capable validation path and the first explicit
post-repair evidence handoff.

The third implementation batch added or upgraded:

- `isaac-training/training/repair/comparison.py`
- `isaac-training/training/repair/validation_runner.py`
- `isaac-training/training/scripts/run_validation_audit.py`
- `isaac-training/training/unit_test/test_env/test_validation_loop.py`
- `isaac-training/training/analyzers/report_contract.py`
- `isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml`

The result is a deterministic first path from:

- a Phase 8 repair bundle with `validation_request.json`

to:

- targeted validation rerun tasks,
- preview-mode triggered repaired run generation,
- higher-order comparison metrics,
- a machine-readable validation decision,
- and `post_repair_evidence.json` as a Phase 10-ready validation input.

### 2.1 `validation_runner.py` Can Now Trigger Targeted Reruns

`validation_runner.py` no longer only loads pre-existing repaired runs.

It now supports:

- building deterministic rerun tasks from original accepted runs,
- normalizing execution mode, scenario family, and scene config scope,
- emitting command previews for future real execution integration,
- triggering a bounded preview-mode rerun driver,
- and recording rerun task results inside `validation_runs.json`.

The current bounded rerun path is:

- `preview_targeted_rerun.v1`

This does not mutate source files and does not pretend to be a full Isaac
benchmark rerun. It gives Phase 9 a stable post-repair evidence path while
preserving the future interface for true baseline/eval/train replay.

### 2.2 `comparison.py` Now Supports Higher-Order Validation Targets

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

### 2.3 Validation Bundles Now Emit Phase 10-Ready Evidence

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
- and a `phase10_post_repair_evidence.v1` contract marker.

This is the first explicit validation artifact designed to feed the next phase
instead of stopping at a single accept/reject result.

### 2.4 CLI Validation Now Supports Triggered Reruns

`run_validation_audit.py` now supports:

- `--trigger-rerun`
- `--repaired-logs-root`

That means the CLI can now:

- read a repair bundle,
- read original accepted runs,
- trigger preview-mode repaired reruns,
- compare pre/post evidence,
- and emit a full namespaced validation bundle

without requiring the caller to hand-author repaired run directories first.

### 2.5 Phase 9 Tests Now Cover the New Loop

`test_validation_loop.py` was extended to verify:

- `nominal_vs_shifted_success_gap` is derived correctly,
- `trigger_rerun=True` creates repaired accepted runs,
- the CLI trigger path writes a complete validation bundle,
- and `post_repair_evidence.json` is present.

This means the new Phase 9 loop is not only implemented, but regression-locked
by focused tests.

## 3. Main Files Added or Changed

Core implementation:

- `isaac-training/training/repair/comparison.py`
- `isaac-training/training/repair/validation_runner.py`
- `isaac-training/training/repair/__init__.py`
- `isaac-training/training/scripts/run_validation_audit.py`

Contract / config:

- `isaac-training/training/analyzers/report_contract.py`
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
  isaac-training/training/analyzers/report_contract.py \
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

### 4.3 CLI Triggered-Rerun Smoke Test

Run a synthetic repair-bundle + accepted-run smoke test against:

- `isaac-training/training/scripts/run_validation_audit.py`

with:

- two original runs (`nominal`, `shifted`) or a single boundary-critical run,
- `--trigger-rerun`,
- and a temporary `--repaired-logs-root`.

Expected result:

- `analysis/validation/<bundle>/` is created
- `validation_plan.json` exists
- `comparison.json` exists
- `validation_decision.json` exists
- `post_repair_evidence.json` exists
- the triggered rerun path reports `trigger_rerun = true`

### 4.4 Check Traceability Refresh

Open:

- `Traceability.md`

Expected result:

- the latest staged change summary includes Phase 9

## 5. Validation Results

Validated in this iteration:

- `python3 -m py_compile ...` passed
- `pytest -q ...` passed:
  - `15 passed`
- real CLI triggered-rerun smoke test passed with:
  - `accepted = true`
  - `decision_status = accepted`
  - `primary_claim_type = E-R`
  - `original_run_count = 2`
  - `repaired_run_count = 2`
  - `trigger_rerun = true`
  - `post_repair_evidence.json` exists
- `Traceability.md` was refreshed for this Phase 9 implementation batch

This confirms that Phase 9 now has a first rerun-capable validation loop and a
Phase 10-ready post-repair evidence artifact.

## 6. What Should Be Done Next

The next Phase 9 step should be:

1. replace or augment the preview rerun driver with true bounded baseline /
   eval / train execution adapters,
2. widen high-order target support beyond the first family-gap metrics,
3. formalize the Phase 10 consumer contract for `post_repair_evidence.json`.

That will move Phase 9 from the first rerun-capable validation loop to a more
faithful repaired-execution validation stage over real post-repair runs.
