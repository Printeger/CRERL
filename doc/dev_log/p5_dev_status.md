# Phase 5 Development Status

Updated: 2026-03-26

## 1. This Iteration Goal

This iteration continues Phase 5 by turning the first dynamic-analysis batch
into something that can operate on real accepted CRE evidence:

- connect the dynamic analyzer to real accepted run directories, not only synthetic runs
- enrich comparison grouping
- integrate static bundle context more tightly
- validate the analyzer on real accepted baseline / eval / train run directories

This is the bridge from:

- "we have accepted rollout logs and a static analyzer"

to:

- "we can compute the first rollout-based CRE witness metrics."

## 2. Implemented Results

### 2.1 Dynamic Metric Kernels Implemented

`isaac-training/training/analyzers/dynamic_metrics.py` is no longer a stub.

It now computes the first engineering versions of:

- `W_CR`: reward-violation coupling
- `W_EC`: critical-state coverage
- `W_ER`: transfer fragility under shift

The implementation is deterministic and pure Python. It works directly from
accepted run-directory payloads and current detector/spec thresholds.

### 2.2 Dynamic Analyzer Orchestration Added

A new module was added:

- `isaac-training/training/analyzers/dynamic_analyzer.py`

It now provides:

- `run_dynamic_analysis(...)`
- `run_dynamic_analysis_bundle(...)`
- namespaced dynamic bundle writing under:
  - `analysis/dynamic/<bundle_name>/`

The report format is machine-readable and mirrors the style already used by the
static analyzer.

### 2.3 Runtime Log Loading Helpers Expanded Further

`isaac-training/training/runtime_logging/episode_writer.py` is no longer only a
thin writer wrapper.

It now also provides deterministic helpers to load:

- a run directory
- an accepted run directory
- multiple accepted run directories
- accepted run discovery from `training/logs` using filters such as:
  - `source`
  - `scenario_type`
  - `scene_cfg_name`

This gives the dynamic analyzer one stable place to read runtime evidence from.

### 2.4 Comparison Grouping Added

`isaac-training/training/analyzers/dynamic_analyzer.py` now computes structured
group summaries for both primary and comparison run sets.

It now exposes grouping over:

- `source`
- `scenario_type`
- `scene_cfg_name`

This means dynamic reports no longer only contain global witness values. They
also include grouped runtime summaries that are directly usable by later
reporting and diagnosis stages.

### 2.5 Static Bundle Context Is Now Loaded Into Dynamic Reports

The dynamic analyzer can now resolve and load static audit context from:

- an explicit `static_bundle_dir`
- or a `reports_root + static_bundle_name`

The dynamic report metadata now records:

- static bundle name
- static bundle paths
- static spec version
- static pass/fail status
- namespace manifest
- report namespace contract

This is the first real bridge between:

- `analysis/static`

and:

- `analysis/dynamic`

### 2.6 Dynamic CLI Entrypoint Expanded

`isaac-training/training/scripts/run_dynamic_audit.py` now supports both:

- explicit `--run-dir / --compare-run-dir`
- accepted-run discovery from:
  - `--logs-root`
  - `--source`
  - `--compare-source`
  - `--scenario-type`
  - `--compare-scenario-type`
  - `--scene-cfg-name`
  - `--compare-scene-cfg-name`

This makes the CLI usable against real run directories already stored under
`training/logs`.

### 2.7 Dynamic Analyzer Tests Expanded

A new test file was added:

- `isaac-training/training/unit_test/test_env/test_dynamic_analyzer.py`

These tests now create synthetic accepted run directories and validate:

- reward-violation coupling rises on unsafe/high-reward trajectories
- critical-state undercoverage is detected
- nominal-vs-shifted transfer fragility is detected
- accepted-run discovery works by source / family / scene config
- static bundle context is loaded into dynamic metadata
- the dynamic CLI writes a proper namespaced bundle
- the CLI discovery path works without explicit `--run-dir`

### 2.8 Real Accepted Run Validation Added

This iteration also validated the dynamic analyzer on real accepted run
directories already present in the repository:

- real baseline runs
- real evaluation runs
- real training runs

Those validations were executed against:

- `isaac-training/training/logs/`

using the dynamic CLI with accepted-run discovery filters.

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
- the dynamic analyzer distinguishes the intended synthetic contrasts
- accepted-run discovery and static-context loading work
- the CLI bundle generation path works

### 4.3 Synthetic Dynamic CLI Smoke Test

Run a small synthetic accepted-run pair through:

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

### 4.4 Real Accepted-Run Validation

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

- `6 passed`

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

## 6. Current Conclusion

Phase 5 now has a usable second batch:

- dynamic witness kernels exist
- dynamic reports can be emitted
- dynamic bundles can be written under the shared namespace contract
- accepted-run discovery is supported
- comparison grouping exists
- static bundle context is integrated into dynamic reports
- pure-Python synthetic validation exists
- real accepted baseline / eval / train runs have all been analyzed successfully

## 7. Next Step

The next best move is to continue Phase 5 by:

- improving the witness definitions from "engineering kernels" toward
  stronger CRE-specific evidence
- adding family-conditioned and source-conditioned failure summaries directly as
  first-class report sections
- adding more real matched run pairs, especially nominal-vs-shifted accepted runs
- preparing the first bridge from dynamic findings into the later semantic / LLM
  diagnosis layer

That will be the point where the project moves from:

- "the dynamic analyzer works on real accepted CRE evidence"

to:

- "the dynamic analyzer can support inconsistency attribution and later report aggregation."
