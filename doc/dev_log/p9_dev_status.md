# Phase 9 Development Status

Updated: 2026-03-27

## 1. This Iteration Goal

This iteration starts the Phase 9 pre-implementation planning step.

The goal of this step is:

- define the first explicit Phase 9 validation-loop plan,
- connect Phase 8 repair outputs to a validation-oriented execution path,
- and freeze the first machine-readable validation-bundle contract.

## 2. Result

Phase 9 now has a formal implementation plan in:

- `doc/roadmap/phase9.md`

The plan makes the next stage concrete instead of leaving it implicit.

It now defines:

- the purpose of Phase 9,
- the authoritative Phase 9 inputs,
- the required validation outputs,
- the first acceptance-rule logic,
- the file-level implementation order,
- and the first exit criteria.

### 2.1 The Phase 8 -> Phase 9 Handoff Is Now Explicit

The new plan treats the following as the canonical Phase 9 handoff:

- `analysis/repair/<bundle>/repair_plan.json`
- `analysis/repair/<bundle>/spec_patch.json`
- `analysis/repair/<bundle>/spec_patch_preview.json`
- `analysis/repair/<bundle>/repair_validation.json`
- `analysis/repair/<bundle>/validation_request.json`

This aligns the roadmap with the actual Phase 8 outputs that are already in the
repo.

### 2.2 The First Validation Namespace Is Defined

The plan now introduces:

- `analysis/validation/<bundle_name>/`

with the first required artifacts:

- `validation_plan.json`
- `validation_runs.json`
- `comparison.json`
- `validation_decision.json`
- `validation_summary.json`
- `validation_summary.md`
- `manifest.json`

This makes the expected Phase 9 bundle shape explicit before implementation.

### 2.3 The First Decision Rules Are Frozen

The plan now defines the first Phase 9 acceptance logic around:

- `ΔConsistency > 0`
- `ΔSafety > 0`
- `ΔPerformance >= -epsilon`

It also freezes deterministic claim-aware mappings for:

- `C-R`
- `E-C`
- `E-R`

This is important because Phase 9 should be evidence-driven, not ad hoc.

### 2.4 The First File-Level Implementation Order Is Frozen

The next implementation sequence is now explicitly:

1. `repair/validation_request_loader.py`
2. preview support in `repair/patch_executor.py`
3. `repair/validation_runner.py`
4. `repair/comparison.py`
5. `repair/decision.py`
6. `scripts/run_validation_audit.py`
7. `unit_test/test_env/test_validation_loop.py`

This gives the repo a clear execution order for Phase 9.

## 3. Main Files Added or Changed

Documentation / state:

- `doc/roadmap/phase9.md`
- `doc/dev_log/p9_dev_status.md`
- `Traceability.md`

## 4. How To Validate

### 4.1 Check That the Phase 9 Plan Exists

Open:

- `doc/roadmap/phase9.md`

Expected result:

- the file exists
- it contains:
  - `Purpose`
  - `Phase 9 Inputs`
  - `Required Validation Outputs`
  - `File-Level Implementation Plan`
  - `Exit Criteria`

### 4.2 Check That the Phase 9 Dev Log Exists

Open:

- `doc/dev_log/p9_dev_status.md`

Expected result:

- the file exists
- it records:
  - what changed
  - how to validate
  - validation results
  - what should be done next

### 4.3 Check Traceability Refresh

Open:

- `Traceability.md`

Expected result:

- the latest staged change summary includes Phase 9

## 5. Validation Results

Validated in this iteration:

- `phase9.md` was created
- `p9_dev_status.md` was created
- the Phase 9 plan now explicitly defines:
  - repair inputs
  - validation outputs
  - decision rules
  - file-level implementation order
- `Traceability.md` was refreshed for this planning update

This confirms that Phase 9 is no longer only implied by the roadmap; it now
has a concrete implementation plan.

## 6. What Should Be Done Next

The next Phase 9 step should be:

1. implement `repair/validation_request_loader.py`
2. extend `repair/patch_executor.py` preview support for validation contexts
3. add `unit_test/test_env/test_validation_loop.py`

That will create the first executable Phase 9 validation substrate on top of
the Phase 8 repair handoff.
