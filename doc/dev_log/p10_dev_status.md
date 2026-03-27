# Phase 10 Development Status

Updated: 2026-03-27

## 1. This Iteration Goal

This iteration starts the first real Phase 10 unification pass.

The goal of this step is:

- make `env.py` consume repaired-preview context directly through native config,
- make `scene_family_bridge.py` expose explicit effective scene/spec binding,
- add the first machine-readable `analysis/integration/<bundle>/` audit path,
- and lock that integration contract with focused regression tests.

## 2. Result

Phase 10 now has its first implemented integration slice.

The key result is that repaired-preview context is no longer only a Phase-9
rerun concern. The main runtime path can now consume it directly at the env /
scene-family binding layer, and there is a dedicated integration namespace that
records whether baseline / eval / train are actually aligned with the CRE
pipeline.

This iteration added three concrete capabilities:

1. **native repaired-preview binding in the env path**
   - `env.py` now passes `cfg.repair` into `build_scene_family_runtime_profile(...)`
   - runtime metadata now exposes:
     - `repair_preview_binding`
     - `effective_scene_binding`
     - `effective_spec_binding`
     - `native_repair_preview_consumption`

2. **explicit effective scene/spec binding in the scene-family bridge**
   - `scene_family_bridge.py` now resolves:
     - validation-context preview payloads
     - repair-preview binding
     - effective scene binding
     - effective spec binding
   - this makes the effective family/config/preview contract serializable and
     testable without launching Isaac

3. **first integration audit bundle**
   - new namespace:
     - `analysis/integration/<bundle>/`
   - new machine-readable artifacts:
     - `integration_plan.json`
     - `execution_matrix.json`
     - `run_binding.json`
     - `integration_acceptance.json`
     - `integration_summary.json`
     - `manifest.json`
   - new human-readable artifact:
     - `integration_summary.md`

## 3. Main Files Added or Changed

Runtime / scene binding:

- `isaac-training/training/scripts/env.py`
- `isaac-training/training/envs/runtime/scene_family_bridge.py`
- `isaac-training/training/cfg/train.yaml`
- `isaac-training/training/cfg/eval.yaml`
- `isaac-training/training/cfg/baseline.yaml`

Integration audit:

- `isaac-training/training/pipeline/integration_bundle.py`
- `isaac-training/training/pipeline/__init__.py`
- `isaac-training/training/scripts/run_integration_audit.py`
- `isaac-training/training/analyzers/report_contract.py`
- `isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml`

Tests / traceability:

- `isaac-training/training/unit_test/test_env/test_integration_stack.py`
- `isaac-training/training/unit_test/test_env/test_spec_ir.py`
- `Traceability.md`

## 4. How To Validate

Recommended focused checks:

```bash
python3 -m py_compile \
  isaac-training/training/envs/runtime/scene_family_bridge.py \
  isaac-training/training/scripts/env.py \
  isaac-training/training/analyzers/report_contract.py \
  isaac-training/training/pipeline/__init__.py \
  isaac-training/training/pipeline/integration_bundle.py \
  isaac-training/training/scripts/run_integration_audit.py \
  isaac-training/training/unit_test/test_env/test_scene_family_bridge.py \
  isaac-training/training/unit_test/test_env/test_integration_stack.py \
  isaac-training/training/unit_test/test_env/test_spec_ir.py
```

```bash
pytest -q \
  isaac-training/training/unit_test/test_env/test_scene_family_bridge.py \
  isaac-training/training/unit_test/test_env/test_integration_stack.py \
  isaac-training/training/unit_test/test_env/test_spec_ir.py
```

```bash
python3 isaac-training/training/scripts/run_integration_audit.py \
  --scene-family nominal \
  --repair-preview-path /tmp/<validation_context_preview>.json \
  --reports-root /tmp/crerl_phase10_reports \
  --bundle-name integration_phase10_smoke \
  --output /tmp/crerl_phase10_reports/integration_summary_copy.json
```

## 5. Validation Results

Validated in this iteration:

- `py_compile` passed for:
  - `scene_family_bridge.py`
  - `env.py`
  - `report_contract.py`
  - `integration_bundle.py`
  - `run_integration_audit.py`
  - the focused test files
- focused pytest passed:
  - `7 passed`
- CLI smoke test passed and wrote:
  - `/tmp/crerl_phase10_reports/analysis/integration/integration_phase10_smoke/`
- the integration smoke result was:
  - `passed = true`
  - `max_severity = info`
  - `comparison_ready_modes = ['baseline', 'eval', 'train']`
  - `validation_only_glue_modes = []`

This confirms the first Phase-10 integration contract is now machine-readable
and the env/runtime layer can bind repaired-preview context directly.

## 6. What Should Be Done Next

The next Phase 10 step should be:

1. extend `training_log_adapter.py` so accepted train/eval/baseline runs carry
   the same effective scene/spec binding metadata more directly,
2. thread repaired-preview context explicitly through `train.py`, `eval.py`,
   and `run_baseline.py`,
3. then run a real original-vs-repaired comparison from the native execution
   harness instead of the Phase 9 validation wrapper.

That will turn the current integration audit from a contract-level proof into a
fully native Phase-10 execution proof.
