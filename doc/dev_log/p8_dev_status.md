# Phase 8 Development Status

Updated: 2026-03-27

## 1. This Iteration Goal

This iteration continues the third real Phase 8 implementation batch.

The goal of this step is:

- implement `repair_validator.py`,
- increase the explicit spec-patch preview capability,
- connect the Phase 8 repair bundle to the Phase 9 validation loop,
- and keep the namespaced repair path deterministic and machine-readable.

## 2. Result

Phase 8 now has its first repair bundle that is explicitly Phase-9 ready.

The repair layer now includes the new validator and handoff path:

- `isaac-training/training/repair/repair_validator.py`
- upgraded `isaac-training/training/repair/patch_executor.py`
- upgraded `isaac-training/training/scripts/run_repair_audit.py`
- `isaac-training/training/unit_test/test_env/test_repair_engine.py`

The result is a deterministic Phase 8 path from:

- Phase 7 `repair_handoff.json`

to:

- structured repair candidates
- a selected preview patch
- a machine-readable `RepairPlan`
- a preflight acceptance verdict
- a namespaced repair bundle under `analysis/repair/<bundle>/`
- a `repair_validation.json` bundle artifact
- a `validation_request.json` artifact that Phase 9 can consume directly

### 2.1 `repair_validator.py` Was Implemented

`repair_validator.py` is no longer a placeholder.

The new validator now checks:

- selected candidate resolution
- selected patch coherence
- selected-candidate / selected-patch alignment
- supported operator-family compliance
- effective patch changes
- target file/path declaration
- declared Phase 9 validation targets
- compatibility with the Phase 8 acceptance gate

The validator writes a machine-readable:

- `phase8_repair_validator.v1`

and also builds:

- `phase9_validation_request.v1`

This is the first real contract between the Phase 8 repair layer and the future
Phase 9 validation loop.

### 2.2 `patch_executor.py` Now Exposes Stronger Preview Artifacts

`patch_executor.py` still writes the Phase 8 namespaced bundle, but it now also
adds a clearer preview layer.

The namespaced repair bundle now writes at least:

- `repair_plan.json`
- `repair_candidates.json`
- `spec_patch.json`
- `spec_patch_preview.json`
- `repair_summary.json`
- `repair_summary.md`
- `acceptance.json`
- `repair_validation.json`
- `validation_request.json`
- `manifest.json`
- `namespace_manifest.json`

The new preview artifact makes it explicit that Phase 8 is still
non-destructive:

- preview mode is `non_destructive`
- source mutation is not performed
- each operation records whether it would actually change a value

This keeps the repair layer auditable while making it easier for Phase 9 to
reason about the selected delta.

### 2.3 `run_repair_audit.py` Now Produces Phase-9-Ready Bundles

`run_repair_audit.py` now does more than candidate generation and bundle
writing.

It now:

- generates the repair plan
- runs preflight acceptance
- runs repair validation
- builds the Phase 9 validation request
- writes all three outputs into the namespaced repair bundle

This is the first point where Phase 8 produces a stable namespaced output under:

- `analysis/repair/<bundle>/`

### 2.4 Focused Repair-Engine Tests Were Extended Again

`isaac-training/training/unit_test/test_env/test_repair_engine.py` now also
checks:

- repair acceptance over a generated `RepairPlan`
- repair bundle writing under the new namespace
- CLI smoke-test execution of `run_repair_audit.py`
- direct repair validation
- direct Phase 9 validation-request construction

This means the Phase 8 repair layer now covers:

- candidate generation
- preflight acceptance
- repair validation
- namespaced repair bundle writing
- Phase 9 handoff artifact generation
- CLI entrypoint execution

## 3. Main Files Added or Changed

Code:

- `isaac-training/training/repair/repair_validator.py`
- `isaac-training/training/repair/patch_executor.py`
- `isaac-training/training/repair/acceptance.py`
- `isaac-training/training/repair/__init__.py`
- `isaac-training/training/scripts/run_repair_audit.py`
- `isaac-training/training/unit_test/test_env/test_repair_engine.py`
- `isaac-training/training/analyzers/report_contract.py`
- `isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml`

Documentation / state:

- `doc/dev_log/p8_dev_status.md`
- `Traceability.md`

## 4. How To Validate

### 4.1 Syntax Validation

Run:

```bash
python3 -m py_compile \
  isaac-training/training/analyzers/report_contract.py \
  isaac-training/training/repair/proposal_schema.py \
  isaac-training/training/repair/rule_based_repair.py \
  isaac-training/training/repair/patch_executor.py \
  isaac-training/training/repair/acceptance.py \
  isaac-training/training/repair/repair_validator.py \
  isaac-training/training/repair/__init__.py \
  isaac-training/training/scripts/run_repair_audit.py \
  isaac-training/training/unit_test/test_env/test_repair_engine.py
```

Expected result:

- no syntax error

### 4.2 Focused Unit Tests

Run:

```bash
pytest -q isaac-training/training/unit_test/test_env/test_repair_engine.py
```

Expected result:

- the first repair-engine tests pass
- each major claim type produces a candidate in the expected repair family
- repair acceptance succeeds on the synthetic fixtures
- the namespaced repair bundle can be written successfully
- repair validation succeeds on the synthetic fixtures
- a Phase 9 validation-request artifact can be produced

### 4.3 CLI Smoke Test

Run:

```bash
python3 isaac-training/training/scripts/run_repair_audit.py \
  --report-bundle-dir <phase7_report_bundle> \
  --reports-root /tmp/crerl_phase8_reports \
  --bundle-name repair_cli_smoke
```

Expected result:

- the command exits successfully
- `analysis/repair/<bundle>/` is created
- `repair_plan.json`, `acceptance.json`, `repair_validation.json`,
  `validation_request.json`, and `namespace_manifest.json` exist

### 4.4 Check Traceability Refresh

Open:

- `Traceability.md`

Expected result:

- latest staged change summary includes Phase 8

## 5. Validation Results

Validated in this iteration:

- `python3 -m py_compile ...` passed
- `pytest -q test_repair_engine.py` passed:
  - `7 passed`
- real CLI smoke test passed with:
  - `passed = true`
  - `phase9_ready = true`
  - `primary_claim_type = E-C`
  - `candidate_count = 2`
- a namespaced repair bundle was confirmed under:
  - `analysis/repair/repair_cli_round3`
- the bundle now also includes:
  - `spec_patch_preview.json`
  - `repair_validation.json`
  - `validation_request.json`
- `Traceability.md` was refreshed for this implementation update

This confirms that the Phase 8 repair layer now has:

- a working repair candidate kernel
- a working acceptance preflight
- a working repair validator
- a working namespaced repair-bundle writer
- a working CLI entrypoint on top of the Phase 7 handoff contract
- a first explicit handoff artifact for the Phase 9 validation loop

## 6. What Should Be Done Next

The next Phase 8 step should be:

1. add richer spec-patch preview semantics for multi-file or mixed-component repairs
2. introduce a first `patch apply preview` / dry-run diff helper
3. start the real Phase 9 validation loop implementation on top of
   `validation_request.json`

That will move the system from repair proposal generation to repair validation
readiness.
