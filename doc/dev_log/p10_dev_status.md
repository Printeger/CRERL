# Phase 10 Development Status

Updated: 2026-03-27

## 1. This Iteration Goal

This iteration continues the Phase 10 unification pass.

The goal of this step is:

- make accepted `baseline / eval / train` runs carry the same effective
  scene/spec binding more directly,
- make native execution entrypoints consume repaired-preview context through the
  same direct contract,
- and prove a real original-vs-repaired comparison can be launched from the
  native Phase 10 harness instead of only from Phase 9 rerun wrappers.

## 2. Result

Phase 10 now has its first native execution proof, not just an integration
contract proof.

The key result is that:

- `baseline`
- `eval`
- `train`

all emit accepted CRE runs with the same effective scene/spec binding surface,
and a real native `original vs repaired` comparison has been executed against
those accepted runs.

This iteration added four concrete capabilities:

1. **direct run-level binding metadata for accepted train/eval/baseline runs**
   - `training_log_adapter.py` now exports:
     - `build_cre_run_metadata(...)`
     - `build_cre_scene_tags_template(...)`
   - accepted run manifests and summaries now carry:
     - `run_metadata_type = phase10_native_execution_run_metadata.v1`
     - `repair_preview_binding`
     - `effective_scene_binding`
     - `effective_spec_binding`
     - `integration_binding_type`

2. **direct scene/spec binding on step and episode evidence**
   - `TrainingRolloutLogger` now writes the same effective binding metadata into
     `scene_tags`, not only into env runtime metadata.
   - this makes accepted run directories directly comparison-ready without
     validation-only patch-up logic.

3. **native repaired-preview consumption through execution entrypoints**
   - `train.py`, `eval.py`, and baseline rollout execution now thread repaired
     preview binding directly into logger creation and accepted-run evidence.
   - the bounded real-execution adapter now launches via the repository's
     standard `conda activate + setup_conda_env.sh + python` path instead of a
     bare `python3 script.py` subprocess.

4. **real native original-vs-repaired comparison proof**
   - a real native `baseline_greedy` original run and repaired run were both
     executed through the same harness
   - then compared through the CRE dynamic audit path
   - proving the Phase 10 harness can launch native comparison-ready evidence
     without Phase 9 wrapper-only semantics

## 3. Main Files Added or Changed

Runtime evidence / binding:

- `isaac-training/training/envs/cre_logging.py`
- `isaac-training/training/runtime_logging/logger.py`
- `isaac-training/training/runtime_logging/training_log_adapter.py`
- `isaac-training/training/scripts/train.py`
- `isaac-training/training/scripts/eval.py`
- `isaac-training/training/execution/baseline_runner.py`

Native rerun / execution glue:

- `isaac-training/training/repair/rerun_adapters.py`
- `isaac-training/training/repair/validation_runner.py`

Tests / traceability:

- `isaac-training/training/unit_test/test_env/test_training_log_adapter.py`
- `isaac-training/training/unit_test/test_env/test_validation_loop.py`
- `isaac-training/training/unit_test/test_env/test_integration_stack.py`
- `Traceability.md`

## 4. How To Validate

Recommended focused checks:

```bash
python3 -m py_compile \
  isaac-training/training/envs/cre_logging.py \
  isaac-training/training/runtime_logging/logger.py \
  isaac-training/training/runtime_logging/training_log_adapter.py \
  isaac-training/training/scripts/train.py \
  isaac-training/training/scripts/eval.py \
  isaac-training/training/execution/baseline_runner.py \
  isaac-training/training/repair/rerun_adapters.py \
  isaac-training/training/unit_test/test_env/test_training_log_adapter.py \
  isaac-training/training/unit_test/test_env/test_validation_loop.py
```

```bash
pytest -q \
  isaac-training/training/unit_test/test_env/test_validation_loop.py
```

```bash
bash -lc 'eval "$(conda shell.bash hook)" && conda activate NavRL && \
  source /home/mint/rl_dev/setup_conda_env.sh && \
  CRE_RUN_LOG_BASE_DIR=/tmp/crerl_phase10_native_logs \
  CRE_RUN_USE_TIMESTAMP=0 \
  CRE_RUN_NAME_OVERRIDE=phase10_baseline_original \
  python isaac-training/training/scripts/run_baseline.py \
    headless=True baseline.name=greedy baseline.num_episodes=1 \
    env.num_envs=1 env.max_episode_length=25 \
    scene_family_backend.family=nominal repair.validation_context_preview='
```

```bash
bash -lc 'eval "$(conda shell.bash hook)" && conda activate NavRL && \
  source /home/mint/rl_dev/setup_conda_env.sh && \
  CRE_RUN_LOG_BASE_DIR=/tmp/crerl_phase10_native_logs \
  CRE_RUN_USE_TIMESTAMP=0 \
  CRE_RUN_NAME_OVERRIDE=phase10_baseline_repaired \
  python isaac-training/training/scripts/run_baseline.py \
    headless=True baseline.name=greedy baseline.num_episodes=1 \
    env.num_envs=1 env.max_episode_length=25 scene_family_backend.family=nominal \
    repair.validation_context_preview=/tmp/crerl_phase10_native_compare_reports/analysis/repair/repair_phase10_native_compare/validation_context_preview.json'
```

```bash
bash -lc 'eval "$(conda shell.bash hook)" && conda activate NavRL && \
  source /home/mint/rl_dev/setup_conda_env.sh && \
  python isaac-training/training/scripts/run_dynamic_audit.py \
    --run-dir /tmp/crerl_phase10_native_logs/phase10_baseline_original \
    --compare-run-dir /tmp/crerl_phase10_native_logs/phase10_baseline_repaired \
    --reports-root /tmp/crerl_phase10_reports \
    --bundle-name dynamic_phase10_native_original_vs_repaired \
    --static-bundle-dir /tmp/crerl_phase5_round2_reports/analysis/static/static_audit_phase5_round2 \
    --output /tmp/crerl_phase10_reports/dynamic_report_copy.json'
```

## 5. Validation Results

Validated in this iteration:

- `py_compile` passed for:
  - `cre_logging.py`
  - `logger.py`
  - `training_log_adapter.py`
  - `train.py`
  - `eval.py`
  - `baseline_runner.py`
  - `rerun_adapters.py`
  - the focused test files
- focused pytest passed:
  - `17 passed, 1 skipped`
- real native accepted runs were produced for:
  - `phase10_baseline_original`
  - `phase10_baseline_repaired`
  - `phase10_eval_repaired`
  - `phase10_train_repaired`
- the repaired `baseline / eval / train` runs all expose:
  - `run_metadata_type = phase10_native_execution_run_metadata.v1`
  - `integration_binding_type = phase10_env_runtime_binding.v1`
  - `repair_preview_bound = true`
  - `effective_scene_binding_type = phase10_effective_scene_binding.v1`
  - `effective_spec_binding_type = phase10_effective_spec_binding.v1`
- native dynamic comparison smoke test passed and wrote:
  - `/tmp/crerl_phase10_reports/analysis/dynamic/dynamic_phase10_native_original_vs_repaired/`
- the native comparison result was:
  - `passed = true`
  - `max_severity = warning`
  - `primary_run_ids = ['phase10_baseline_original']`
  - `comparison_run_ids = ['phase10_baseline_repaired']`
  - `W_CR = 0.0`
  - `W_EC = 0.46666666666666673`
  - `W_ER = 0.0`

This confirms the Phase 10 native harness can now:

- emit accepted runs with direct effective scene/spec binding,
- consume repaired-preview context without Phase 9 wrapper-only semantics,
- and launch a real original-vs-repaired comparison from the same execution
  substrate.

## 6. What Should Be Done Next

The next Phase 10 step should be:

1. extend the native comparison proof from `baseline` to explicit
   `eval/train original-vs-repaired` pairs,
2. add a small Phase 10 integration consumer that summarizes native accepted
   run bindings and native comparison outputs in one namespaced bundle,
3. then decide whether Phase 10 can be formally closed and Phase 11 planning
   can begin.
