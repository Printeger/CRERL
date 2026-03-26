# Phase 6 Development Status

Updated: 2026-03-26

## 1. This Iteration Goal

This iteration continues Phase 6 by implementing the next two foundational
pieces from [phase6.md](../roadmap/phase6.md):

- `semantic_crosscheck.py`
- `semantic_provider.py`

The purpose of this step is to move from:

- "Phase 6 has a claim schema and deterministic semantic-analysis input"

to:

- "Phase 6 can deterministically generate semantic claims with a mock provider
  and cross-validate them against machine evidence."

## 2. Implemented Results

### 2.0 Repo-Local Workflow Rule Was Corrected

The repo-local standing instruction layer was corrected so the dev-log naming
rule now means:

- `p{N}_dev_status.md`

where `{N}` is the actual affected roadmap phase number.

It no longer means a literal file named:

- `px_dev_status.md`

The mistakenly created `doc/dev_log/px_dev_status.md` file was removed, and the
repo-local rule in `AGENTS.md` now explicitly says to attach workflow/meta
changes to the nearest affected numbered phase instead.

### 2.1 Semantic Cross-Check Layer Added

A new file was added:

- `isaac-training/training/analyzers/semantic_crosscheck.py`

It implements the first deterministic semantic cross-validation layer:

- `check_claim_type_alignment(...)`
- `check_claim_evidence_support(...)`
- `check_claim_witness_alignment(...)`
- `check_claim_scope_alignment(...)`
- `validate_semantic_claims(...)`

This layer now enforces the evidence-first rule from the Phase 6 plan:

- unsupported claim types are rejected
- claims without known evidence refs are rejected
- claims with weak witness alignment are downgraded
- scope alignment is checked against families, sources, and scene config names

### 2.2 Mock Semantic Provider Added

A new file was added:

- `isaac-training/training/analyzers/semantic_provider.py`

It defines:

- `SemanticProvider`
- `MockSemanticProvider`
- `generate_mock_claims(...)`

The mock provider is deterministic and provider-agnostic. It uses the existing
Phase-5 dynamic semantic handoff to generate claims from:

- witness summaries
- failure hotspots
- evidence objects
- cross-validation contract metadata

This gives the semantic layer a testable claim-generation path before any real
LLM backend is introduced.

### 2.3 Mock Provider and Cross-Check Now Work Together

The Phase 6 stack can now perform the first full semantic mini-loop:

1. build a semantic analysis input from real bundles
2. generate candidate semantic claims with the mock provider
3. cross-check those claims against machine evidence
4. classify them into:
   - `supported`
   - `weak`
   - `rejected`

This is the first end-to-end semantic pipeline fragment in the repository.

### 2.4 Analyzer Exports Were Extended Again

`isaac-training/training/analyzers/__init__.py` now exports:

- semantic cross-check helpers
- mock provider interface
- mock provider generation helper

This keeps the next Phase-6 files (`semantic_analyzer.py`, CLI, tests) from
having to reach into module internals.

### 2.5 Real Bundle Semantic Smoke Test Now Works

This iteration also verified the new semantic layer on top of real bundles:

- static bundle:
  - `static_audit_phase5_round2`
- dynamic bundle:
  - `dynamic_eval_nominal_vs_shifted`

The real-bundle semantic smoke test now confirms:

- semantic input loading works
- mock provider emits claims
- cross-check returns at least one supported real claim
- the strongest supported claim is `E-R`, which is consistent with the
  `nominal vs shifted` evaluation contrast

## 3. Main Files Added or Changed

Code files:

- `isaac-training/training/analyzers/semantic_crosscheck.py`
- `isaac-training/training/analyzers/semantic_provider.py`
- `isaac-training/training/analyzers/__init__.py`
- `isaac-training/training/unit_test/test_env/test_semantic_analyzer.py`

Documentation/state files:

- `doc/dev_log/p6_dev_status.md`
- `Traceability.md`

## 4. How To Validate

### 4.1 Syntax Validation

Run:

```bash
python3 -m py_compile \
  isaac-training/training/analyzers/semantic_crosscheck.py \
  isaac-training/training/analyzers/semantic_provider.py \
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

- semantic claim schema tests still pass
- mock provider tests pass
- semantic cross-check tests pass
- no Isaac Sim dependency is required

### 4.3 Real Bundle Semantic Smoke Test

Run from repo root:

```bash
python3 - <<'PY'
import sys
from pathlib import Path

root = Path('/home/mint/rl_dev/CRERL/isaac-training/training')
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from analyzers.semantic_inputs import build_semantic_analysis_input
from analyzers.semantic_provider import MockSemanticProvider
from analyzers.semantic_crosscheck import validate_semantic_claims

semantic_input = build_semantic_analysis_input(
    static_bundle_dir='/tmp/crerl_phase5_round2_reports/analysis/static/static_audit_phase5_round2',
    dynamic_bundle_dir='/tmp/crerl_phase5_round4_reports/analysis/dynamic/dynamic_eval_nominal_vs_shifted',
)
claims = MockSemanticProvider().generate_claims(semantic_input)
claim_set = validate_semantic_claims(claims, semantic_input=semantic_input)

print({
    'generated_claims': len(claims),
    'supported_claims': len(claim_set.supported_claims),
    'weak_claims': len(claim_set.weak_claims),
    'rejected_claims': len(claim_set.rejected_claims),
    'top_claim_type': claim_set.supported_claims[0].claim_type if claim_set.supported_claims else '',
    'top_claim_status': claim_set.supported_claims[0].status if claim_set.supported_claims else '',
    'semantic_contract_type': claim_set.metadata.get('semantic_contract_type', ''),
})
PY
```

Expected result:

- claims are generated from real bundle context
- at least one supported claim is returned
- the result still stays grounded in the Phase-5 semantic contract

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

- `7 passed`

### 5.3 Real Bundle Semantic Smoke Test

Observed result:

- semantic input successfully built from:
  - `static_audit_phase5_round2`
  - `dynamic_eval_nominal_vs_shifted`
- mock provider generated:
  - `2` claims
- cross-check classified them as:
  - `supported_claims = 1`
  - `weak_claims = 1`
  - `rejected_claims = 0`
- strongest supported claim:
  - `claim_type = E-R`
  - `status = supported`
- semantic contract remained:
  - `semantic_contract_type = phase6_dynamic_semantic_contract.v1`

## 6. Current Conclusion

Phase 6 now has a usable deterministic semantic core:

- a structured claim schema
- a deterministic semantic input builder
- a mock semantic provider
- a semantic cross-check layer

This is enough to begin wiring the first actual semantic analyzer without
guessing either input format or claim-validation logic.

## 7. Next Step

The next best move is to continue Phase 6 by implementing:

- `semantic_analyzer.py`
- `run_semantic_audit.py`

That will make it possible to:

- turn the mock semantic mini-loop into a namespaced semantic report bundle
- validate bundle writing before integrating a real LLM backend
