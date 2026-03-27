# Phase 11 Development Status

Updated: 2026-03-27

## 1. This Iteration Goal

This iteration starts Phase 11 implementation.

The goal of this step is:

- freeze the first benchmark case objects under `cfg/benchmark_cfg/`,
- implement the first machine-readable benchmark suite builder,
- add a CLI entrypoint for namespaced benchmark packaging,
- and lock the first regression tests for benchmark-manifest correctness.

## 2. Result

Phase 11 now has its first executable benchmark-packaging path.

The key result is that:

- benchmark cases are no longer only a roadmap idea,
- they now exist as machine-readable suite inputs,
- and the repository can package them into:
  - `analysis/benchmark/<bundle>/`

This iteration added four concrete capabilities:

1. **machine-readable benchmark case configs**
   - new benchmark case YAMLs now exist under:
     - `isaac-training/training/cfg/benchmark_cfg/clean_nominal.yaml`
     - `isaac-training/training/cfg/benchmark_cfg/injected_cr.yaml`
     - `isaac-training/training/cfg/benchmark_cfg/injected_ec.yaml`
     - `isaac-training/training/cfg/benchmark_cfg/injected_er.yaml`
   - the grouped suite manifest now exists at:
     - `isaac-training/training/cfg/benchmark_cfg/benchmark_suite_v1.yaml`

2. **first benchmark suite compiler**
   - `pipeline/benchmark_suite.py` now:
     - loads the suite manifest,
     - resolves referenced spec/env configs,
     - checks execution-mode compatibility against the existing runtime contract,
     - produces:
       - `benchmark_manifest.json`
       - `benchmark_cases.json`
       - `benchmark_matrix.json`
       - `benchmark_summary.json`
       - `benchmark_summary.md`

3. **namespaced benchmark packaging CLI**
   - `scripts/run_benchmark_suite.py` now packages benchmark bundles into:
     - `analysis/benchmark/<bundle>/`
   - the benchmark namespace is now part of the shared report contract
   - `policy_spec_v0.yaml` now records benchmark artifact expectations

4. **first benchmark regression coverage**
   - `test_benchmark_suite.py` now verifies:
     - real benchmark cases load correctly,
     - the namespaced bundle is written,
     - the CLI smoke path works,
     - and all four initial cases are Phase-10-native-ready

## 3. Main Files Added or Changed

Benchmark configs:

- `isaac-training/training/cfg/benchmark_cfg/clean_nominal.yaml`
- `isaac-training/training/cfg/benchmark_cfg/injected_cr.yaml`
- `isaac-training/training/cfg/benchmark_cfg/injected_ec.yaml`
- `isaac-training/training/cfg/benchmark_cfg/injected_er.yaml`
- `isaac-training/training/cfg/benchmark_cfg/benchmark_suite_v1.yaml`

Benchmark pipeline / contract:

- `isaac-training/training/pipeline/benchmark_suite.py`
- `isaac-training/training/pipeline/__init__.py`
- `isaac-training/training/scripts/run_benchmark_suite.py`
- `isaac-training/training/analyzers/report_contract.py`
- `isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml`

Tests / traceability:

- `isaac-training/training/unit_test/test_env/test_benchmark_suite.py`
- `Traceability.md`

## 4. How To Validate

Recommended focused checks:

```bash
python3 -m py_compile \
  isaac-training/training/analyzers/report_contract.py \
  isaac-training/training/pipeline/benchmark_suite.py \
  isaac-training/training/pipeline/__init__.py \
  isaac-training/training/scripts/run_benchmark_suite.py \
  isaac-training/training/unit_test/test_env/test_benchmark_suite.py
```

```bash
pytest -q isaac-training/training/unit_test/test_env/test_benchmark_suite.py
```

```bash
python3 isaac-training/training/scripts/run_benchmark_suite.py \
  --reports-root /tmp/crerl_phase11_reports \
  --bundle-name benchmark_phase11_smoke \
  --output /tmp/crerl_phase11_reports/benchmark_summary_copy.json
```

## 5. Validation Results

Validated in this iteration:

- `py_compile` passed for:
  - `report_contract.py`
  - `benchmark_suite.py`
  - `pipeline/__init__.py`
  - `run_benchmark_suite.py`
  - `test_benchmark_suite.py`
- focused pytest passed:
  - `3 passed`
- benchmark CLI smoke test passed and wrote:
  - `/tmp/crerl_phase11_reports/analysis/benchmark/benchmark_phase11_smoke/`
- the benchmark smoke summary is:
  - `suite_name = cre_v1_minimal_benchmark`
  - `case_count = 4`
  - `ready_case_count = 4`
  - `phase10_native_ready_case_count = 4`

This confirms the first Phase 11 batch is complete:

- clean / injected benchmark cases are frozen as machine-readable objects,
- the suite can be compiled into a namespaced benchmark bundle,
- and the benchmark namespace is now part of the shared evidence contract.

## 6. What Should Be Done Next

The next Phase 11 step should be:

1. extend the benchmark suite from packaging-only to replay-oriented execution metadata,
2. implement `pipeline/release_bundle.py`,
3. add `scripts/run_release_packaging.py`,
4. and start building the first release-grade clean-vs-injected demo bundle.
