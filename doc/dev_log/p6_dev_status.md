# Phase 6 Development Status

Updated: 2026-03-26

## 1. This Iteration Goal

This iteration continues Phase 6 by implementing the next two files from
[phase6.md](../roadmap/phase6.md):

- `semantic_analyzer.py`
- `run_semantic_audit.py`

The goal of this step is to move from:

- "Phase 6 can build semantic inputs, generate mock claims, and cross-check them"

to:

- "Phase 6 can package that workflow into a namespaced semantic analysis bundle
  under `analysis/semantic/<bundle_name>/`."

## 2. Implemented Results

### 2.1 Semantic Analyzer Added

A new file was added:

- `isaac-training/training/analyzers/semantic_analyzer.py`

It now provides the first higher-level semantic analyzer layer for Phase 6:

- `run_semantic_analysis(...)`
- `build_semantic_report(...)`
- `write_semantic_report(...)`
- `build_semantic_summary_markdown(...)`
- `write_semantic_analysis_bundle(...)`
- `run_semantic_analysis_bundle(...)`

This analyzer now performs the full deterministic Phase 6 flow:

1. read `SpecIR`
2. read a static audit bundle
3. read a dynamic analysis bundle
4. build a semantic input
5. generate claims with the provider
6. cross-check claims against machine evidence
7. write a machine-readable semantic report bundle

### 2.2 Namespaced Semantic Bundle Contract Added

The shared report contract now includes a semantic mode:

- `semantic_analysis`
- namespace: `analysis/semantic`

The expected semantic bundle artifacts are now:

- `semantic_report.json`
- `semantic_claims.json`
- `semantic_input.json`
- `semantic_summary.md`
- `summary.json`
- `manifest.json`
- `namespace_manifest.json`

This keeps Phase 6 aligned with the existing Phase 4 static bundle and Phase 5
dynamic bundle layout.

### 2.3 Semantic CLI Entrypoint Added

A new script was added:

- `isaac-training/training/scripts/run_semantic_audit.py`

It can now run the Phase 6 semantic analyzer directly from:

- one static audit bundle
- one dynamic analysis bundle

and write a namespaced semantic bundle under:

- `analysis/semantic/<bundle_name>/`

The current supported provider mode is:

- `mock`

This is intentional for this stage; it keeps semantic analysis deterministic
while the evidence-grounding contract stabilizes.

### 2.4 Semantic Analyzer Exports Were Extended

`isaac-training/training/analyzers/__init__.py` now exports:

- semantic analyzer report types
- semantic analyzer bundle helpers
- semantic analyzer namespace constants

This keeps the next Phase 6 steps from needing to import private module paths.

### 2.5 Policy Runtime Expectations Were Extended

`isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml` now includes the
semantic-analysis namespace and required artifact list.

That keeps the machine-readable policy/runtime expectations aligned with the new
semantic bundle layer instead of leaving semantic outputs as an implicit side
channel.

## 3. Main Files Added or Changed

Code files:

- `isaac-training/training/analyzers/report_contract.py`
- `isaac-training/training/analyzers/semantic_analyzer.py`
- `isaac-training/training/analyzers/__init__.py`
- `isaac-training/training/scripts/run_semantic_audit.py`
- `isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml`
- `isaac-training/training/unit_test/test_env/test_semantic_analyzer.py`

Documentation/state files:

- `doc/dev_log/p6_dev_status.md`
- `Traceability.md`

## 4. How To Validate

### 4.1 Syntax Validation

Run:

```bash
python3 -m py_compile \
  isaac-training/training/analyzers/report_contract.py \
  isaac-training/training/analyzers/semantic_claims.py \
  isaac-training/training/analyzers/semantic_inputs.py \
  isaac-training/training/analyzers/semantic_crosscheck.py \
  isaac-training/training/analyzers/semantic_provider.py \
  isaac-training/training/analyzers/semantic_analyzer.py \
  isaac-training/training/analyzers/__init__.py \
  isaac-training/training/scripts/run_semantic_audit.py \
  isaac-training/training/unit_test/test_env/test_semantic_analyzer.py
```

Expected result:

- no syntax error

### 4.2 Pure Python Unit Test

Run:

```bash
pytest -q isaac-training/training/unit_test/test_env/test_semantic_analyzer.py
```

Expected result:

- semantic input tests still pass
- semantic claim and cross-check tests still pass
- semantic analyzer bundle-writing tests pass
- no Isaac Sim dependency is required

### 4.3 Real Bundle Semantic CLI Smoke Test

Run:

```bash
python3 isaac-training/training/scripts/run_semantic_audit.py \
  --static-bundle-dir /tmp/crerl_phase5_round2_reports/analysis/static/static_audit_phase5_round2 \
  --dynamic-bundle-dir /tmp/crerl_phase5_round4_reports/analysis/dynamic/dynamic_eval_nominal_vs_shifted \
  --reports-root /tmp/crerl_phase6_reports \
  --bundle-name semantic_eval_nominal_vs_shifted \
  --output /tmp/crerl_phase6_reports/semantic_report_copy.json
```

Expected result:

- a new semantic bundle is written under:
  - `/tmp/crerl_phase6_reports/analysis/semantic/semantic_eval_nominal_vs_shifted/`
- the CLI prints:
  - `passed`
  - `max_severity`
  - `supported_claims`
  - `weak_claims`
  - `rejected_claims`
  - `most_likely_claim_type`

## 5. Validation Results

Validation run on 2026-03-26:

### 5.1 `py_compile`

Result:

- passed

### 5.2 Unit Test

Command:

```bash
pytest -q isaac-training/training/unit_test/test_env/test_semantic_analyzer.py
```

Result:

- `10 passed`

### 5.3 Real Bundle Semantic CLI Smoke Test

Observed result:

- semantic bundle successfully written to:
  - `/tmp/crerl_phase6_reports/analysis/semantic/semantic_eval_nominal_vs_shifted/`
- generated semantic result:
  - `passed = true`
  - `max_severity = warning`
  - `num_findings = 2`
  - `supported_claims = 1`
  - `weak_claims = 1`
  - `rejected_claims = 0`
  - `most_likely_claim_type = E-R`

## 6. Current Conclusion

Phase 6 now has a usable namespaced semantic bundle pipeline.

The semantic layer can now:

- consume existing static + dynamic bundles
- build a deterministic semantic input
- generate and cross-check semantic claims
- write a stable machine-readable semantic bundle
- emit a concise human-readable semantic summary

## 7. Next Step

The next Phase 6 step should be:

- implement the higher-level semantic report merge path
- define the claim-consumer / cross-check interface that Phase 7 repair logic
  will read
- optionally add a real provider adapter behind the same provider interface

Before any real LLM backend is introduced, the semantic bundle contract should
remain deterministic and evidence-first.
