# Phase 5 Development Status

Updated: 2026-03-26

## 1. This Iteration Goal

This iteration continues Phase 5 by moving the dynamic analyzer beyond the
first engineering-only batch and making it more useful for later diagnosis:

- strengthen witness definitions beyond the first-pass kernels
- connect the analyzer to real accepted run directories, not only synthetic runs
- promote family-conditioned / source-conditioned summaries into first-class
  report sections
- integrate static bundle context more tightly
- add a real nominal-vs-shifted matched run pair

This is the bridge from:

- "we can run a first dynamic analyzer"

to:

- "we can produce stable dynamic CRE evidence for later attribution."

## 2. Implemented Results

### 2.1 Dynamic Witness Kernels Were Strengthened

`isaac-training/training/analyzers/dynamic_metrics.py` now computes stronger
engineering witnesses instead of only the first-pass coarse signals.

Changes in this iteration:

- `W_CR` now incorporates:
  - proximity pressure
  - proximity-reward alignment
  - high-return hazardous-episode ratio
- `W_EC` now incorporates:
  - family-conditioned failure pressure
  - family-level critical-state summaries
- `W_ER` now incorporates:
  - source-pair shift
  - family-shift gap
  - family-conditioned comparison summaries

These additions make the witness values more informative for later
specification- and report-level diagnosis.

### 2.2 Dynamic Analyzer Supports Real Accepted-Run Discovery

`isaac-training/training/runtime_logging/episode_writer.py` now supports
discovery of accepted run directories from `training/logs` by:

- `source`
- `scenario_type`
- `scene_cfg_name`

`isaac-training/training/analyzers/dynamic_analyzer.py` can now resolve both:

- explicit `run_dirs`
- discovered accepted run directories from `logs_root`

This means the analyzer can operate directly on real rollout artifacts.

### 2.3 Grouped Runtime Summaries Are Still Present

The dynamic analyzer continues to compute grouped summaries over:

- `source`
- `scenario_type`
- `scene_cfg_name`

These summaries are still useful for report aggregation and comparison views.

### 2.4 Failure Summaries Are Now First-Class Report Sections

The dynamic report now exposes these top-level fields directly:

- `group_summaries`
- `failure_summaries`
- `static_context`

instead of leaving everything inside `metadata`.

The new `failure_summaries` promote family-conditioned and
source-conditioned runtime evidence into report-root structure, which is
easier for later semantic or LLM-facing diagnosis stages to consume.

### 2.5 Static Bundle Context Is Tied More Closely To Dynamic Reports

The dynamic analyzer can now resolve static audit context from:

- an explicit `static_bundle_dir`
- or `reports_root + static_bundle_name`

The report root now carries this context in a stable way through:

- `static_context`

This contains:

- static bundle name
- static spec version
- static pass/fail status
- namespace manifest
- report namespace contract

This tightens the bridge between:

- `analysis/static`
- `analysis/dynamic`

### 2.6 Dynamic CLI Works With Real Accepted Runs

`isaac-training/training/scripts/run_dynamic_audit.py` now supports:

- explicit `--run-dir / --compare-run-dir`
- real accepted-run discovery from:
  - `--logs-root`
  - `--source`
  - `--compare-source`
  - `--scenario-type`
  - `--compare-scenario-type`
  - `--scene-cfg-name`
  - `--compare-scene-cfg-name`

This makes the CLI usable both for synthetic smoke tests and real repository
artifacts under `training/logs`.

### 2.7 Dynamic Analyzer Tests Were Expanded

`isaac-training/training/unit_test/test_env/test_dynamic_analyzer.py` now
validates:

- reward-violation coupling on unsafe reward-rich trajectories
- critical-state undercoverage
- transfer fragility under nominal-vs-shifted contrast
- accepted-run discovery by source / family / scene config
- static bundle context loading
- report-root group/failure summaries
- CLI namespaced dynamic bundle writing

### 2.8 Real Accepted Baseline / Eval / Train Runs Were Analyzed

This iteration continued to validate the analyzer against real accepted run
directories already present in:

- `isaac-training/training/logs/`

Real accepted analyses were executed for:

- baseline runs
- evaluation runs
- training runs

### 2.9 A Real Nominal-vs-Shifted Matched Pair Was Added

A real `shifted` run was generated through the actual baseline execution path:

- `baseline_greedy`
- `scene_family_backend.family=shifted`

and then re-accepted through the shared run-level acceptance check.

That run now forms a real matched pair with the existing accepted
`baseline_greedy` nominal run:

- nominal:
  - `baseline_greedy_rollout_20260326_190209`
- shifted:
  - `baseline_greedy_rollout_20260326_223636`

This pair was then analyzed through the shared dynamic CLI and namespaced
report bundle flow.

## 3. Main Files Added or Changed

Code files:

- `isaac-training/training/analyzers/dynamic_metrics.py`
- `isaac-training/training/analyzers/dynamic_analyzer.py`
- `isaac-training/training/analyzers/__init__.py`
- `isaac-training/training/runtime_logging/episode_writer.py`
- `isaac-training/training/runtime_logging/__init__.py`
- `isaac-training/training/scripts/run_dynamic_audit.py`
- `isaac-training/training/unit_test/test_env/test_dynamic_analyzer.py`

Documentation/state files:

- `doc/roadmap/phase5.md`
- `doc/dev_log/p5_dev_status.md`
- `Traceability.md`

## 4. How To Validate

### 4.1 Syntax Validation

Run:

```bash
python3 -m py_compile \
  isaac-training/training/analyzers/dynamic_metrics.py \
  isaac-training/training/analyzers/dynamic_analyzer.py \
  isaac-training/training/analyzers/__init__.py \
  isaac-training/training/runtime_logging/episode_writer.py \
  isaac-training/training/runtime_logging/__init__.py \
  isaac-training/training/scripts/run_dynamic_audit.py \
  isaac-training/training/unit_test/test_env/test_dynamic_analyzer.py
```

Expected result:

- no syntax error

### 4.2 Pure Python Dynamic Analyzer Tests

Run:

```bash
pytest -q isaac-training/training/unit_test/test_env/test_dynamic_analyzer.py
```

Expected result:

- tests pass without Isaac Sim
- stronger witness signals remain stable
- accepted-run discovery works
- report-root group/failure summaries are emitted
- static-context loading works
- CLI namespaced bundle generation works

### 4.3 Synthetic Dynamic CLI Smoke Test

Run:

```bash
python3 isaac-training/training/scripts/run_dynamic_audit.py \
  --run-dir <accepted_nominal_run_dir> \
  --compare-run-dir <accepted_shifted_run_dir> \
  --reports-root /tmp/crerl_phase5_reports \
  --bundle-name phase5_smoke \
  --output /tmp/crerl_phase5_reports/dynamic_report_copy.json
```

Expected result:

- the bundle is written under:
  - `/tmp/crerl_phase5_reports/analysis/dynamic/phase5_smoke/`
- stdout returns a machine-readable summary
- the synthetic contrast produces non-trivial `W_EC` / `W_ER` scores

### 4.4 Real Accepted Baseline / Eval / Train Validation

Generate one real static bundle first:

```bash
python3 isaac-training/training/scripts/run_static_audit.py \
  --reports-root /tmp/crerl_phase5_real_reports \
  --bundle-name static_audit_phase5_real \
  --output /tmp/crerl_phase5_real_reports/static_report_copy.json
```

Then validate real accepted baseline runs:

```bash
python3 isaac-training/training/scripts/run_dynamic_audit.py \
  --logs-root isaac-training/training/logs \
  --source baseline_random \
  --source baseline_greedy \
  --source baseline_conservative \
  --reports-root /tmp/crerl_phase5_real_reports \
  --bundle-name dynamic_baseline_real \
  --static-bundle-name static_audit_phase5_real \
  --output /tmp/crerl_phase5_real_reports/dynamic_baseline_copy.json
```

Validate real accepted eval runs:

```bash
python3 isaac-training/training/scripts/run_dynamic_audit.py \
  --logs-root isaac-training/training/logs \
  --source eval \
  --reports-root /tmp/crerl_phase5_real_reports \
  --bundle-name dynamic_eval_real \
  --static-bundle-name static_audit_phase5_real \
  --output /tmp/crerl_phase5_real_reports/dynamic_eval_copy.json
```

Validate real accepted train runs:

```bash
python3 isaac-training/training/scripts/run_dynamic_audit.py \
  --logs-root isaac-training/training/logs \
  --source train \
  --reports-root /tmp/crerl_phase5_real_reports \
  --bundle-name dynamic_train_real \
  --static-bundle-name static_audit_phase5_real \
  --output /tmp/crerl_phase5_real_reports/dynamic_train_copy.json
```

Optional real compare-group validation:

```bash
python3 isaac-training/training/scripts/run_dynamic_audit.py \
  --logs-root isaac-training/training/logs \
  --source baseline_greedy \
  --compare-source baseline_conservative \
  --reports-root /tmp/crerl_phase5_real_reports \
  --bundle-name dynamic_baseline_compare_real \
  --static-bundle-name static_audit_phase5_real \
  --output /tmp/crerl_phase5_real_reports/dynamic_baseline_compare_copy.json
```

### 4.5 Real Nominal-vs-Shifted Matched-Pair Validation

Generate one real shifted run:

```bash
cd /home/mint/rl_dev/CRERL/isaac-training
conda run -n NavRL python training/scripts/run_baseline.py \
  baseline.name=greedy \
  baseline.num_episodes=1 \
  scene_family_backend.family=shifted \
  headless=True
```

Re-run acceptance on that new shifted run:

```bash
cd /home/mint/rl_dev/CRERL/isaac-training/training
python3 - <<'PY'
from runtime_logging.logger import run_acceptance_check
from pathlib import Path
run_dir = Path('/home/mint/rl_dev/CRERL/isaac-training/training/logs/baseline_greedy_rollout_20260326_223636')
print(run_acceptance_check(run_dir, write_report=True))
PY
```

Then analyze the real matched pair:

```bash
cd /home/mint/rl_dev/CRERL
python3 isaac-training/training/scripts/run_static_audit.py \
  --reports-root /tmp/crerl_phase5_round2_reports \
  --bundle-name static_audit_phase5_round2 \
  --output /tmp/crerl_phase5_round2_reports/static_report_copy.json

python3 isaac-training/training/scripts/run_dynamic_audit.py \
  --logs-root isaac-training/training/logs \
  --source baseline_greedy \
  --scenario-type nominal \
  --compare-source baseline_greedy \
  --compare-scenario-type shifted \
  --reports-root /tmp/crerl_phase5_round2_reports \
  --bundle-name dynamic_baseline_greedy_nominal_vs_shifted \
  --static-bundle-name static_audit_phase5_round2 \
  --output /tmp/crerl_phase5_round2_reports/dynamic_baseline_greedy_nominal_vs_shifted_copy.json
```

Expected result:

- the real matched pair is discovered successfully
- the emitted report includes first-class:
  - `group_summaries`
  - `failure_summaries`
  - `static_context`
- `W_ER` becomes non-zero under the real nominal-vs-shifted contrast

## 5. Validation Results

Validation run on 2026-03-26:

### 5.1 `py_compile`

Result:

- passed

### 5.2 Pure Python Tests

Command:

```bash
pytest -q isaac-training/training/unit_test/test_env/test_dynamic_analyzer.py
```

Result:

- `7 passed`

### 5.3 Synthetic Dynamic CLI Smoke Test

Observed result:

- `run_dynamic_audit.py` completed successfully
- the namespaced dynamic bundle was written successfully
- stdout summary reported:
  - `passed = false`
  - `max_severity = high`
  - `num_findings = 3`
  - witness scores:
    - `W_CR = 0.0`
    - `W_EC = 0.5833333333333334`
    - `W_ER = 0.8033333333333333`

This is the expected direction for the synthetic nominal-vs-shifted contrast
used in the smoke test.

### 5.4 Real Accepted Baseline Dynamic Analysis

Observed result:

- real accepted baseline runs were discovered successfully from `training/logs`
- the namespaced dynamic bundle was written successfully
- stdout summary reported:
  - `passed = true`
  - `max_severity = warning`
  - `num_findings = 3`
  - witness scores:
    - `W_CR = 0.25756709572967057`
    - `W_EC = 0.25`
    - `W_ER = 0.0`

### 5.5 Real Accepted Eval Dynamic Analysis

Observed result:

- real accepted eval runs were discovered successfully
- the namespaced dynamic bundle was written successfully
- stdout summary reported:
  - `passed = true`
  - `max_severity = medium`
  - `num_findings = 3`
  - witness scores:
    - `W_CR = 0.0`
    - `W_EC = 0.5833333333333334`
    - `W_ER = 0.0`

### 5.6 Real Accepted Train Dynamic Analysis

Observed result:

- real accepted train runs were discovered successfully
- the namespaced dynamic bundle was written successfully
- stdout summary reported:
  - `passed = true`
  - `max_severity = warning`
  - `num_findings = 3`
  - witness scores:
    - `W_CR = 0.4`
    - `W_EC = 0.33333333333333337`
    - `W_ER = 0.0`

### 5.7 Real Compare-Group Validation

Observed result:

- the compare-group path resolved:
  - primary source: `baseline_greedy`
  - comparison source: `baseline_conservative`
- the report metadata correctly included:
  - static bundle context
  - group summaries by source / scenario / scene config
- stdout summary reported:
  - `passed = true`
  - `max_severity = medium`
  - `num_findings = 3`
  - witness scores:
    - `W_CR = 0.0`
    - `W_EC = 0.5833333333333334`
    - `W_ER = 0.043113627047455125`

### 5.8 Real Nominal-vs-Shifted Matched-Pair Validation

Observed result:

- a real shifted accepted run was generated:
  - `baseline_greedy_rollout_20260326_223636`
- it was paired with the real nominal accepted run:
  - `baseline_greedy_rollout_20260326_190209`
- the emitted report now contains first-class:
  - `group_summaries`
  - `failure_summaries`
  - `static_context`
- stdout summary reported:
  - `passed = true`
  - `max_severity = warning`
  - `num_findings = 3`
  - witness scores:
    - `W_CR = 0.0`
    - `W_EC = 0.46666666666666673`
    - `W_ER = 0.14285714285714285`

## 6. Current Conclusion

Phase 5 now has a usable stronger second batch:

- dynamic witness kernels exist
- witness definitions are stronger than the first engineering-only kernels
- dynamic reports can be emitted
- dynamic bundles can be written under the shared namespace contract
- accepted-run discovery is supported
- comparison grouping exists
- family-conditioned and source-conditioned failure summaries are first-class
  report sections
- static bundle context is integrated into dynamic reports
- pure-Python synthetic validation exists
- real accepted baseline / eval / train runs have all been analyzed successfully
- a real nominal-vs-shifted matched pair now exists and has been analyzed

## 7. Next Step

The next best move is to continue Phase 5 by:

- adding more real matched run pairs beyond the first `baseline_greedy`
  nominal-vs-shifted pair
- turning the current grouped failure summaries into more stable dynamic evidence
  objects for later semantic diagnosis
- refining witness calibration against real failure cases instead of only
  rule-based engineering thresholds
- preparing the first bridge from dynamic findings into the later semantic / LLM
  diagnosis layer

That will be the point where the project moves from:

- "the dynamic analyzer works on real accepted CRE evidence"

to:

- "the dynamic analyzer can support inconsistency attribution and later report aggregation."
