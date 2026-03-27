# Phase 9 Development Status

Updated: 2026-03-27

## 1. This Iteration Goal

This iteration starts the first real Phase 9 implementation batch.

The goal of this step is:

- implement `repair/validation_request_loader.py`,
- extend `repair/patch_executor.py` with validation-context preview support,
- and add focused tests for the first Phase 9 validation substrate.

## 2. Result

Phase 9 now has its first executable validation substrate on top of the Phase 8
repair handoff.

The first implementation batch added or upgraded:

- `isaac-training/training/repair/validation_request_loader.py`
- `isaac-training/training/repair/patch_executor.py`
- `isaac-training/training/unit_test/test_env/test_validation_loop.py`

The result is a deterministic first path from:

- `analysis/repair/<bundle>/validation_request.json`

to:

- a normalized Phase 9 validation input
- a non-destructive validation-context preview
- focused tests over the first validation-loop substrate

### 2.1 `validation_request_loader.py` Was Implemented

`validation_request_loader.py` is the first explicit Phase 9 input parser.

It now:

- reads a Phase 8 repair bundle
- validates required repair artifacts
- loads:
  - `repair_plan.json`
  - `spec_patch.json`
  - `spec_patch_preview.json`
  - `validation_context_preview.json`
  - `repair_validation.json`
  - `validation_request.json`
  - `manifest.json`
- normalizes:
  - preferred execution modes
  - scene family scope
  - validation targets
- exposes:
  - `phase9_ready`
  - `request_valid`
  - `blockers`
  - resolved artifact paths

This is the first stable loader that Phase 9 can build on.

### 2.2 `patch_executor.py` Now Builds Validation-Context Preview

`patch_executor.py` still writes the Phase 8 repair bundle, but it now also
builds a richer preview specifically for Phase 9.

The new artifact is:

- `validation_context_preview.json`

This preview:

- remains non-destructive
- loads the real target YAML / JSON config
- reconstructs the patched preview state in memory
- records:
  - original document
  - patched document
  - per-operation before/after
  - whether the operation would actually change a value

This makes the Phase 8 -> Phase 9 handoff much more useful, because Phase 9 no
longer has to infer the patched state from raw patch operations alone.

### 2.3 `validation_request.json` Was Strengthened

The Phase 8 validator now emits richer Phase 9 request fields, including:

- `preferred_execution_modes`
- `scene_family_scope`
- `comparison_mode`

This means the first Phase 9 loader does not need to guess the intended
rerun scope from bundle naming alone.

### 2.4 Focused Phase 9 Tests Were Added

A new file was added:

- `isaac-training/training/unit_test/test_env/test_validation_loop.py`

The tests verify:

- a repair bundle can be loaded as a normalized Phase 9 validation input
- the validation-context preview reconstructs patched config state correctly
- the preview artifact is actually written into the repair bundle

This means Phase 9 is no longer only planned; it now has a small but working
validation-input substrate.

## 3. Main Files Added or Changed

Documentation / state:

- `doc/dev_log/p9_dev_status.md`
- `Traceability.md`

## 4. How To Validate

### 4.1 Syntax Validation

Run:

```bash
python3 -m py_compile \
  isaac-training/training/analyzers/report_contract.py \
  isaac-training/training/repair/patch_executor.py \
  isaac-training/training/repair/repair_validator.py \
  isaac-training/training/repair/validation_request_loader.py \
  isaac-training/training/repair/__init__.py \
  isaac-training/training/scripts/run_repair_audit.py \
  isaac-training/training/unit_test/test_env/test_repair_engine.py \
  isaac-training/training/unit_test/test_env/test_validation_loop.py
```

Expected result:

- no syntax error

### 4.2 Focused Unit Tests

Run:

```bash
pytest -q \
  isaac-training/training/unit_test/test_env/test_repair_engine.py \
  isaac-training/training/unit_test/test_env/test_validation_loop.py
```

Expected result:

- the repair bundle tests still pass
- the new Phase 9 validation-loop substrate tests pass

### 4.3 CLI + Loader Smoke Test

Run a real `run_repair_audit.py` smoke test, then load the resulting repair
bundle through `validation_request_loader.py`.

Expected result:

- the repair bundle is generated successfully
- the loader reports:
  - `phase9_ready = true`
  - `request_valid = true`
- `validation_context_preview.json` exists and is non-empty

### 4.4 Check Traceability Refresh

Open:

- `Traceability.md`

Expected result:

- the latest staged change summary includes Phase 9

## 5. Validation Results

Validated in this iteration:

- `python3 -m py_compile ...` passed
- `pytest -q ...` passed:
  - `10 passed`
- real CLI + loader smoke test passed with:
  - `phase9_ready = true`
  - `request_valid = true`
  - `primary_claim_type = E-R`
  - `preferred_execution_modes = ['baseline', 'eval']`
  - `scene_family_scope = ['nominal', 'shifted']`
- `Traceability.md` was refreshed for this planning update

This confirms that Phase 9 now has a working first validation-input substrate
on top of the Phase 8 repair bundle path.

## 6. What Should Be Done Next

The next Phase 9 step should be:

1. implement `repair/validation_runner.py`
2. implement `repair/comparison.py`
3. implement the first validation decision rule and `run_validation_audit.py`

That will move Phase 9 from validation-input preparation to the first real
repair acceptance / rejection loop.
