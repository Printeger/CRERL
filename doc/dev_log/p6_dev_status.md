# Phase 6 Development Status

Updated: 2026-03-26

## 1. This Iteration Goal

This iteration starts Phase 6 by implementing the first two foundational
pieces from [phase6.md](../roadmap/phase6.md):

- `semantic_claims.py`
- `semantic_inputs.py`

The purpose of this step is to move from:

- "Phase 5 emits dynamic evidence and semantic handoff artifacts"

to:

- "Phase 6 has a stable machine-readable claim schema and a deterministic
  semantic-analysis input builder."

## 2. Implemented Results

### 2.1 Semantic Claim Schema Added

A new file was added:

- `isaac-training/training/analyzers/semantic_claims.py`

It defines the first structured semantic diagnosis schema for Phase 6:

- `SemanticClaim`
- `SemanticCrossCheckResult`
- `SemanticClaimSet`

This schema now standardizes:

- canonical claim types:
  - `C-R`
  - `E-C`
  - `E-R`
- canonical claim statuses:
  - `supported`
  - `weak`
  - `rejected`
- canonical severities
- confidence normalization to `[0, 1]`
- deterministic serialization / round-trip behavior

This gives the semantic layer a stable representation before any provider or
cross-check logic is added.

### 2.2 Deterministic Semantic Input Builder Added

A new file was added:

- `isaac-training/training/analyzers/semantic_inputs.py`

It introduces:

- `StaticBundleContext`
- `DynamicBundleContext`
- `SemanticAnalysisInput`

and deterministic loading/building helpers:

- `load_static_bundle(...)`
- `load_dynamic_bundle(...)`
- `collect_evidence_context(...)`
- `build_prompt_sections(...)`
- `build_semantic_analysis_input(...)`

This builder explicitly reuses Phase 5 artifacts instead of rebuilding runtime
semantic context from scratch.

### 2.3 Phase-5 Semantic Handoff Is Reused Instead of Forked

The new semantic input builder treats the existing dynamic bundle outputs as
the main semantic substrate:

- `dynamic_report.json`
- `dynamic_evidence.json`
- `semantic_inputs.json`

The semantic input builder now carries forward:

- `semantic_contract_type`
- `cross_validation_contract`
- `failure_hotspots`
- `attribution_candidates`
- `prompt_sections`

This keeps Phase 6 aligned with the evidence-first design instead of creating a
separate, divergent semantic input format.

### 2.4 Bundle Context Loading Is Now Stable Enough For Later Analyzer Layers

`semantic_inputs.py` now supports direct loading from report bundle
directories:

- static bundle:
  - `analysis/static/<bundle_name>/`
- dynamic bundle:
  - `analysis/dynamic/<bundle_name>/`

The builder also falls back to the bundle directory name when a manifest does
not explicitly carry `bundle_name`, which makes real-bundle smoke testing more
stable.

### 2.5 Analyzer Package Exports Were Extended

`isaac-training/training/analyzers/__init__.py` now exports the new Phase 6
foundation layer:

- semantic claim schema helpers
- semantic bundle loaders
- semantic input builder helpers

This makes later `semantic_crosscheck.py`, `semantic_provider.py`, and
`semantic_analyzer.py` implementation cleaner.

## 3. Main Files Added or Changed

Code files:

- `isaac-training/training/analyzers/semantic_claims.py`
- `isaac-training/training/analyzers/semantic_inputs.py`
- `isaac-training/training/analyzers/__init__.py`
- `isaac-training/training/unit_test/test_env/test_semantic_analyzer.py`

Documentation/state files:

- `doc/roadmap/phase6.md`
- `doc/dev_log/p6_dev_status.md`
- `Traceability.md`

## 4. How To Validate

### 4.1 Syntax Validation

Run:

```bash
python3 -m py_compile \
  isaac-training/training/analyzers/semantic_claims.py \
  isaac-training/training/analyzers/semantic_inputs.py \
  isaac-training/training/analyzers/__init__.py \
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

- claim normalization and round-trip tests pass
- semantic input builder tests pass
- no Isaac Sim dependency is required

### 4.3 Real Bundle Smoke Test

Run from repo root:

```bash
python3 - <<'PY'
import sys
from pathlib import Path

root = Path('/home/mint/rl_dev/CRERL/isaac-training/training')
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from analyzers.semantic_inputs import build_semantic_analysis_input

payload = build_semantic_analysis_input(
    static_bundle_dir='/tmp/crerl_phase5_round2_reports/analysis/static/static_audit_phase5_round2',
    dynamic_bundle_dir='/tmp/crerl_phase5_round4_reports/analysis/dynamic/dynamic_eval_nominal_vs_shifted',
).to_dict()

print({
    'input_type': payload['input_type'],
    'spec_version': payload['spec_version'],
    'static_bundle_name': payload['static_context']['bundle_name'],
    'dynamic_bundle_name': payload['dynamic_context']['bundle_name'],
    'semantic_contract_type': payload['cross_validation_requirements']['semantic_contract_type'],
    'required_claim_types': payload['cross_validation_requirements']['required_claim_types'],
    'dynamic_evidence_count': len(payload['evidence_context']['evidence_objects']),
})
PY
```

Expected result:

- the semantic input builds successfully from real Phase-4/5 bundles
- the resulting payload exposes the Phase-5 semantic contract

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

- `4 passed`

### 5.3 Real Bundle Smoke Test

Observed result:

- semantic input successfully built from:
  - `static_audit_phase5_round2`
  - `dynamic_eval_nominal_vs_shifted`
- reported fields:
  - `input_type = semantic_analysis_input.v1`
  - `spec_version = v0`
  - `static_bundle_name = static_audit_phase5_round2`
  - `dynamic_bundle_name = dynamic_eval_nominal_vs_shifted`
  - `semantic_contract_type = phase6_dynamic_semantic_contract.v1`
  - `required_claim_types = ['C-R', 'E-C', 'E-R']`
  - `dynamic_evidence_count = 9`

## 6. Current Conclusion

Phase 6 now has its first stable foundation:

- a structured semantic claim schema
- a deterministic semantic-analysis input builder
- a direct bridge from Phase-5 dynamic evidence into Phase-6 semantic inputs

This is enough to begin implementing the next semantic layer pieces without
guessing input structure on the fly.

## 7. Next Step

The next best move is to continue Phase 6 by implementing:

- `semantic_crosscheck.py`
- `semantic_provider.py`

That will make it possible to:

- validate semantic claims against evidence contracts
- test the semantic layer with a mock provider before adding a real LLM backend
