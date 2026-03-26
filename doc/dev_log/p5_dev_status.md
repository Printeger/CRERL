# Phase 5 Development Status

Updated: 2026-03-26

## 1. This Iteration Goal

This iteration starts Phase 5 by implementing the first usable dynamic-analysis
substrate:

- replace the `dynamic_metrics.py` placeholder with deterministic metric kernels
- add a first `dynamic_analyzer.py`
- add a CLI entrypoint for namespaced dynamic bundles
- add pure-Python tests using synthetic accepted run directories

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

### 2.3 Runtime Log Loading Helpers Expanded

`isaac-training/training/runtime_logging/episode_writer.py` is no longer only a
thin writer wrapper.

It now also provides deterministic helpers to load:

- a run directory
- an accepted run directory
- multiple accepted run directories

This gives the dynamic analyzer one stable place to read runtime evidence from.

### 2.4 Dynamic CLI Entrypoint Added

A new CLI was added:

- `isaac-training/training/scripts/run_dynamic_audit.py`

It can:

- take one or more accepted run directories
- optionally take one or more comparison run directories
- emit a namespaced dynamic analysis bundle
- emit a standalone `dynamic_report.json` copy if requested

### 2.5 First Pure-Python Dynamic Analyzer Tests Added

A new test file was added:

- `isaac-training/training/unit_test/test_env/test_dynamic_analyzer.py`

These tests create synthetic accepted run directories and validate:

- reward-violation coupling rises on unsafe/high-reward trajectories
- critical-state undercoverage is detected
- nominal-vs-shifted transfer fragility is detected
- the dynamic CLI writes a proper namespaced bundle

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
- the CLI bundle generation path works

### 4.3 Dynamic CLI Smoke Test

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

- `4 passed`

### 5.3 Dynamic CLI Smoke Test

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

## 6. Current Conclusion

Phase 5 has now started with a usable first batch:

- dynamic witness kernels exist
- dynamic reports can be emitted
- dynamic bundles can be written under the shared namespace contract
- pure-Python synthetic validation exists

This is enough to begin comparing real accepted rollout directories next.

## 7. Next Step

The next best move is to continue Phase 5 by:

- enriching the dynamic analyzer with richer comparison grouping
- adding standard dynamic fixtures or reusable sample run bundles
- integrating static-bundle context more tightly into dynamic findings
- validating the analyzer on real accepted baseline/train/eval run directories

That will be the point where the project moves from:

- "the dynamic analyzer works on synthetic accepted runs"

to:

- "the dynamic analyzer can be trusted on real CRE rollout evidence."
