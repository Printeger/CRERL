# Phase 10 Development Status

Updated: 2026-03-30

## 1. This Iteration Goal

This iteration closes out Phase 10.

The goal of this step is:

- extend native `original-vs-repaired` proof from `baseline` to explicit
  `eval` and `train` pairs,
- add a small integration-side consumer that summarizes native accepted run
  bindings and native comparison results in one namespaced bundle,
- and determine whether the Phase 10 exit criteria are now satisfied.

## 2. Result

Phase 10 now has a full native close-out proof.

The key result is that:

- `baseline`
- `eval`
- `train`

all now have:

- accepted native `original` and `repaired` runs,
- real native `original-vs-repaired` dynamic comparison bundles,
- and one machine-readable Phase 10 integration bundle that summarizes the
  native binding state and the comparison proof in one place.

This iteration added three concrete capabilities:

1. **native eval/train original-vs-repaired comparison proof**
   - real native `eval` and `train` `original` runs were produced alongside the
     already-existing repaired runs
   - both pairs were compared through the same CRE dynamic-audit path already
     used for native baseline proof
   - this means the native Phase 10 harness now proves comparison readiness for
     all three execution modes, not only `baseline`

2. **a dedicated Phase 10 native execution consumer**
   - `integration_bundle.py` now writes:
     - `native_execution_consumer.json`
   - this consumer summarizes:
     - accepted native run bindings,
     - `baseline / eval / train` binding readiness,
     - and native comparison bundle outcomes
   - the integration namespace now carries both contract-level and proof-level
     evidence

3. **machine-readable close-out evidence for Phase 10**
   - `analysis/integration/integration_phase10_native_closeout/` now states:
     - `native_ready_modes = ['baseline', 'eval', 'train']`
     - `comparison_proven_modes = ['baseline', 'eval', 'train']`
     - `validation_only_glue_modes = []`
   - against the Phase 10 roadmap, this is the first bundle that directly shows
     the RL stack is aligned with the CRE pipeline at the native execution
     level

## 3. Main Files Added or Changed

Phase 10 integration bundle / consumer:

- `isaac-training/training/pipeline/integration_bundle.py`
- `isaac-training/training/scripts/run_integration_audit.py`
- `isaac-training/training/analyzers/report_contract.py`
- `isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml`

Focused tests / traceability:

- `isaac-training/training/unit_test/test_env/test_integration_stack.py`
- `Traceability.md`

## 4. How To Validate

Recommended focused checks:

```bash
python3 -m py_compile \
  isaac-training/training/analyzers/report_contract.py \
  isaac-training/training/pipeline/integration_bundle.py \
  isaac-training/training/scripts/run_integration_audit.py \
  isaac-training/training/unit_test/test_env/test_integration_stack.py
```

```bash
pytest -q isaac-training/training/unit_test/test_env/test_integration_stack.py
```

```bash
python3 isaac-training/training/scripts/run_dynamic_audit.py \
  --run-dir /tmp/crerl_phase10_native_logs/phase10_eval_original \
  --compare-run-dir /tmp/crerl_phase10_native_logs/phase10_eval_repaired \
  --reports-root /tmp/crerl_phase10_reports \
  --bundle-name dynamic_phase10_eval_native_original_vs_repaired \
  --static-bundle-dir /tmp/crerl_phase5_round2_reports/analysis/static/static_audit_phase5_round2 \
  --output /tmp/crerl_phase10_reports/dynamic_eval_report_copy.json
```

```bash
python3 isaac-training/training/scripts/run_dynamic_audit.py \
  --run-dir /tmp/crerl_phase10_native_logs/phase10_train_original \
  --compare-run-dir /tmp/crerl_phase10_native_logs/phase10_train_repaired \
  --reports-root /tmp/crerl_phase10_reports \
  --bundle-name dynamic_phase10_train_native_original_vs_repaired \
  --static-bundle-dir /tmp/crerl_phase5_round2_reports/analysis/static/static_audit_phase5_round2 \
  --output /tmp/crerl_phase10_reports/dynamic_train_report_copy.json
```

```bash
python3 isaac-training/training/scripts/run_integration_audit.py \
  --scene-family nominal \
  --repair-preview-path /tmp/crerl_phase10_native_compare_reports/analysis/repair/repair_phase10_native_compare/validation_context_preview.json \
  --reports-root /tmp/crerl_phase10_reports \
  --bundle-name integration_phase10_native_closeout \
  --native-run-dir /tmp/crerl_phase10_native_logs/phase10_baseline_original \
  --native-run-dir /tmp/crerl_phase10_native_logs/phase10_baseline_repaired \
  --native-run-dir /tmp/crerl_phase10_native_logs/phase10_eval_original \
  --native-run-dir /tmp/crerl_phase10_native_logs/phase10_eval_repaired \
  --native-run-dir /tmp/crerl_phase10_native_logs/phase10_train_original \
  --native-run-dir /tmp/crerl_phase10_native_logs/phase10_train_repaired \
  --comparison-bundle-dir /tmp/crerl_phase10_reports/analysis/dynamic/dynamic_phase10_native_original_vs_repaired \
  --comparison-bundle-dir /tmp/crerl_phase10_reports/analysis/dynamic/dynamic_phase10_eval_native_original_vs_repaired \
  --comparison-bundle-dir /tmp/crerl_phase10_reports/analysis/dynamic/dynamic_phase10_train_native_original_vs_repaired \
  --output /tmp/crerl_phase10_reports/integration_closeout_summary_copy.json
```

## 5. Validation Results

Validated in this iteration:

- `py_compile` passed for:
  - `report_contract.py`
  - `integration_bundle.py`
  - `run_integration_audit.py`
  - `test_integration_stack.py`
- focused pytest passed:
  - `4 passed`
- accepted native runs exist and pass acceptance for:
  - `phase10_baseline_original`
  - `phase10_baseline_repaired`
  - `phase10_eval_original`
  - `phase10_eval_repaired`
  - `phase10_train_original`
  - `phase10_train_repaired`
- native dynamic comparison bundles now exist for:
  - `dynamic_phase10_native_original_vs_repaired`
  - `dynamic_phase10_eval_native_original_vs_repaired`
  - `dynamic_phase10_train_native_original_vs_repaired`
- the native comparison results are:
  - `baseline`
    - `passed = true`
    - `W_CR = 0.0`
    - `W_EC = 0.46666666666666673`
    - `W_ER = 0.0`
  - `eval`
    - `passed = true`
    - `W_CR = 0.0`
    - `W_EC = 0.46666666666666673`
    - `W_ER = 0.0`
  - `train`
    - `passed = true`
    - `W_CR = 0.125`
    - `W_EC = 0.46666666666666673`
    - `W_ER = 0.0`
- the integration close-out bundle now reports:
  - `passed = true`
  - `max_severity = info`
  - `native_ready_modes = ['baseline', 'eval', 'train']`
  - `comparison_proven_modes = ['baseline', 'eval', 'train']`
  - `validation_only_glue_modes = []`

This confirms the Phase 10 exit criteria are now satisfied:

1. `env.py`, `train.py`, `eval.py`, and `run_baseline.py` all consume the same
   family-based scene contract directly.
2. repaired preview context is injected through the native execution stack.
3. accepted runs from `baseline / eval / train` are directly analyzer-ready.
4. `original-vs-repaired` comparisons can be launched from the same native
   harness for all three execution modes.
5. a machine-readable `analysis/integration/<bundle>/` close-out bundle now
   states the RL stack is aligned with the CRE pipeline.

## 6. What Should Be Done Next

Phase 10 can now be considered complete.

The next step should be to begin Phase 11 planning and implementation around:

1. benchmark packaging,
2. repeatable clean-vs-injected end-to-end demonstrations,
3. and a higher-level release-ready CRE integration story built on the now
   unified execution stack.

## 7. Follow-Up Alignment (2026-03-30)

This follow-up tightens the native training stack so it is less of a legacy
island and closer to the `test_flight.py` / `env_gen.py` mainline path.

### What changed

- `env.py` now resolves the drone model the same way `test_flight.py` does:
  prefer the configured model (for example `TaslabUAV`) and fall back to
  `Hummingbird` only if the registry does not expose it.
- when `scene_family_backend.enabled = true`, `NavigationEnv` now uses
  `UniversalArenaGenerator + ArenaSpawner` to build the shared scene from
  `env_gen.py` instead of relying only on the legacy terrain obstacle path.
- LiDAR now consumes a single merged scan mesh built from:
  - `/World/ground`
  - the static obstacles spawned by `env_gen.py`
  which keeps Orbit `RayCaster` compatible while letting the training stack see
  the authoritative CRE static scene.
- env-gen dynamic obstacles now feed the training env's dynamic-obstacle state
  directly through the existing analytic obstacle interface.
- `training_log_adapter.py` now preserves richer native scene metadata in
  `manifest.json` / `summary.json`, including:
  - `scene_id`
  - `shared_scene_tags`
  - `shared_scene_complexity`
  - `shared_scene_obstacle_count`
  - `shared_scene_dynamic_obstacle_count`

### How to validate

```bash
python3 -m py_compile \
  isaac-training/training/scripts/env.py \
  isaac-training/training/runtime_logging/training_log_adapter.py \
  isaac-training/training/scripts/train.py
```

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate NavRL
source /home/mint/rl_dev/setup_conda_env.sh
cd /home/mint/rl_dev/CRERL
python isaac-training/training/scripts/train.py \
  headless=True \
  wandb.mode=offline \
  scene_family_backend.family=nominal \
  env.num_envs=1 \
  env.max_episode_length=64 \
  max_frame_num=64 \
  save_interval=999999 \
  eval_interval=999999 \
  +skip_periodic_eval=True
```

After the run finishes, inspect the newest `train_rollout_*` directory:

```bash
python3 - <<'PY'
import json
from pathlib import Path
run = sorted(Path('isaac-training/training/logs').glob('train_rollout_*'))[-1]
meta = json.loads((run / 'manifest.json').read_text())['run_metadata']
print(run)
print(meta['scene_id'])
print(meta['scene_cfg_name'])
print(meta['shared_scene_tags'])
print(meta['shared_scene_complexity'])
PY
```

### Validation results

- `py_compile` passed
- the short native `train.py` smoke run passed
- the newest accepted run (`train_rollout_20260330_175430`) confirms:
  - `scene_id = nominal_v0`
  - `scene_cfg_name = scene_cfg_nominal.yaml`
  - `shared_scene_obstacle_count = 12`
  - `shared_scene_dynamic_obstacle_count = 0`
  - `shared_scene_complexity = 0.08750711987984028`
  - `acceptance passed = true`

### What this means

Phase 10 remains complete, but the native execution stack is now better aligned
with the intended CRE architecture:

- `train.py` is no longer only consuming scene-family metadata
- it now also consumes `env_gen.py`'s shared scene backend directly
- and the resulting accepted runs expose that scene binding more explicitly in
  the machine-readable evidence surface
