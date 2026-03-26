# Phase 6: Semantic Analyzer and Evidence-Grounded Inconsistency Diagnosis

## 1. Purpose

Phase 6 is the stage where the project moves from:

- "we can compute static and dynamic CRE evidence"

to:

- "we can produce grounded semantic diagnoses over `C/R/E` inconsistencies."

The goal of this phase is to implement the first **semantic analyzer** for the
CRE stack.

This analyzer should consume the artifacts stabilized in Phases 4-5:

- machine-readable `SpecIR`,
- static audit bundles,
- dynamic analysis bundles,
- dynamic evidence objects,
- semantic handoff inputs,

and turn them into explicit inconsistency claims, such as:

- `C-R`
- `E-C`
- `E-R`

with evidence-grounded explanations.

This phase corresponds to:

- [doc/roadmap.md](../roadmap.md) `Phase 6. Add the LLM Semantic Analyzer`
- [doc/system_architecture_and _control_flow.md](../system_architecture_and%20_control_flow.md) `Layer E. Analysis Layer`
- [doc/CRE_frame_design.pdf](../CRE_frame_design.pdf) semantic diagnosis and repair-suggestion stage

---

## 2. Why Phase 6 Starts Here

Phases 4-5 already established:

- a deterministic `SpecIR`,
- a namespaced static audit contract,
- accepted runtime logs,
- dynamic witness metrics,
- stable `dynamic_evidence.json`,
- stable `semantic_inputs.json`,
- an explicit cross-validation contract for semantic consumers.

What is still missing is the semantic question:

`given the available quantitative evidence, what kind of inconsistency best explains the observed behavior?`

This is exactly the role of the semantic analyzer.

The first semantic analyzer should not try to solve the whole repair loop.
Its first job is narrower:

1. ingest the formal spec context and accepted evidence bundles;
2. produce structured semantic claims about likely inconsistency type;
3. cross-check those claims against static and dynamic evidence;
4. emit a machine-readable semantic report and a small human-readable diagnosis summary.

That gives Phase 7 a clean multi-source report input, and gives Phase 8 a
better substrate for repair proposal generation.

---

## 3. Scope of Phase 6

Phase 6 should implement **semantic diagnosis only**.

In scope:

- semantic claim generation over static + dynamic evidence
- provider-agnostic semantic analyzer interface
- evidence-grounded prompt construction
- cross-validation of semantic claims against machine evidence
- machine-readable semantic report bundle

Out of scope:

- final merged static/dynamic/semantic report
- automated repair synthesis
- repair validation loop
- policy retraining or environment mutation

Those belong to later phases.

---

## 4. Inputs the Semantic Analyzer Must Read

The semantic analyzer should treat the following as the authoritative inputs for
`v0`.

### 4.1 SpecIR

- `isaac-training/training/analyzers/spec_ir.py`
- `isaac-training/training/cfg/spec_cfg/*.yaml`
- `isaac-training/training/cfg/env_cfg/*.yaml`

The semantic layer must not infer spec structure from prose alone.

### 4.2 Static Audit Bundles

Under:

`analysis/static/<bundle_name>/`

Minimum required artifacts:

- `static_report.json`
- `summary.json`
- `manifest.json`

These provide:

- static findings
- spec/runtime mismatches
- scene-backend capability issues
- execution-mode alignment results

### 4.3 Dynamic Analysis Bundles

Under:

`analysis/dynamic/<bundle_name>/`

Minimum required artifacts:

- `dynamic_report.json`
- `dynamic_evidence.json`
- `semantic_inputs.json`
- `summary.json`
- `manifest.json`

These provide:

- witness scores
- failure hotspots
- grouped runtime summaries
- evidence objects
- semantic handoff contract

### 4.4 Namespace Contract

- `analysis/report_namespace_contract.json`

The semantic analyzer should understand the existing analysis namespace layout
so that later report merging stays deterministic.

### 4.5 Optional Runtime Log References

For `v0`, the semantic analyzer should prefer bundle-level evidence, not raw
rollout replay. But it may keep references to raw run directories:

- `isaac-training/training/logs/<run_id>/`

This is useful for human-readable citations and future deep-dive tooling.

---

## 5. First Architectural Decision: Semantic Layer Must Be Evidence-First

The semantic analyzer is **not** allowed to behave like a free-form reviewer.

It must be constrained by:

- static findings,
- dynamic witness summaries,
- dynamic evidence objects,
- semantic cross-validation contract.

This implies three important design rules:

1. every semantic claim must reference machine evidence;
2. semantic confidence must be separate from witness score;
3. unsupported claims must be rejected or downgraded by the cross-check layer.

So Phase 6 should start by freezing:

- a semantic claim schema,
- a semantic prompt/input schema,
- a semantic cross-check schema.

Only after those are stable should the project add a real LLM backend.

---

## 6. First Working Semantic Outputs

Phase 6 does not need the final polished diagnosis UX.

It needs stable engineering outputs that:

- are grounded in existing evidence,
- are machine-checkable,
- can later feed report generation and repair planning.

### 6.1 Semantic Claim Object

The first semantic analyzer should emit structured claims with at least:

- `claim_id`
- `claim_type`
  - `C-R`
  - `E-C`
  - `E-R`
- `confidence`
- `severity`
- `summary`
- `rationale`
- `supporting_evidence_ids`
- `supporting_witness_ids`
- `supporting_finding_ids`
- `affected_families`
- `affected_sources`
- `affected_scene_cfg_names`
- `repair_direction_hint`

### 6.2 Cross-Validated Semantic Diagnosis

The semantic report should also distinguish:

- `supported_claims`
- `weak_claims`
- `rejected_claims`

This is important because Phase 6 is not just "generate LLM text"; it must
state whether each diagnosis is actually supported by evidence.

### 6.3 Human-Readable Semantic Summary

The first report should also produce a concise human-readable diagnosis block:

- most likely inconsistency type
- strongest supporting evidence
- strongest uncertainty / ambiguity
- minimal next-check or repair direction

---

## 7. Deliverables

Phase 6 should produce the following deliverables.

### 7.1 Semantic Claim Schema

A versioned structured claim representation for:

- supported semantic diagnoses
- rejected or weak diagnoses
- evidence-grounding metadata

### 7.2 Semantic Prompt/Input Builder

A deterministic builder that packages:

- spec context
- static findings
- dynamic witness summaries
- dynamic evidence hotspots
- semantic cross-validation contract

into a stable semantic input for later provider adapters.

### 7.3 Semantic Analyzer

A higher-level analyzer that:

- reads the current spec and evidence bundles,
- produces semantic claims,
- cross-checks them,
- writes a namespaced semantic analysis bundle.

### 7.4 Semantic Report Bundle

A namespaced bundle, for example under:

- `analysis/semantic/<bundle_name>/`

containing at least:

- `semantic_report.json`
- `semantic_claims.json`
- `semantic_summary.md`
- `summary.json`
- `manifest.json`

### 7.5 Synthetic Semantic Fixtures

Fixtures that test:

- supported `C-R` diagnosis
- supported `E-C` diagnosis
- supported `E-R` diagnosis
- over-claim rejection when evidence is weak

---

## 8. File-Level Implementation Plan

### 8.1 Semantic Claim Schema

#### File: `isaac-training/training/analyzers/semantic_claims.py`

Current state:

- missing

What to implement:

- dataclasses for:
  - `SemanticClaim`
  - `SemanticClaimSet`
  - `SemanticCrossCheckResult`
  - `SemanticAnalyzerReport`
- serialization helpers
- claim severity / confidence normalization

Important design decision:

- claims must be provider-agnostic
- no prompt-building logic in this file

### 8.2 Semantic Input Builder

#### File: `isaac-training/training/analyzers/semantic_inputs.py`

Current state:

- missing

What to implement:

- deterministic builders that combine:
  - `SpecIR`
  - static report
  - dynamic report
  - dynamic evidence objects
  - `semantic_inputs.json`
- helper functions such as:
  - `build_semantic_analysis_input(...)`
  - `collect_evidence_context(...)`
  - `build_prompt_sections(...)`

Important design decision:

- this layer should reuse the Phase-5 semantic handoff instead of rebuilding it
- `Phase 6` should treat `semantic_inputs.json` as the main runtime-semantic substrate

### 8.3 Semantic Cross-Check Layer

#### File: `isaac-training/training/analyzers/semantic_crosscheck.py`

Current state:

- missing

What to implement:

- functions such as:
  - `validate_semantic_claims(...)`
  - `check_claim_evidence_support(...)`
  - `check_claim_type_alignment(...)`
  - `check_claim_witness_alignment(...)`
  - `check_claim_scope_alignment(...)`

This layer should verify:

- every claim cites evidence
- `C-R / E-C / E-R` claims align with the witness family they invoke
- family-specific claims cite matching family context
- weakly supported claims are downgraded or rejected

### 8.4 Semantic Analyzer

#### File: `isaac-training/training/analyzers/semantic_analyzer.py`

Current state:

- missing

What to implement:

- a high-level runner that:
  - loads `SpecIR`
  - loads static bundle context
  - loads dynamic bundle context
  - builds semantic inputs
  - invokes a semantic provider adapter
  - cross-validates returned claims
  - emits the semantic report

Suggested entrypoints:

- `run_semantic_analysis(...)`
- `write_semantic_analysis_bundle(...)`

### 8.5 Provider Adapter Layer

#### File: `isaac-training/training/analyzers/semantic_provider.py`

Current state:

- missing

What to implement in the first pass:

- a provider-agnostic interface, for example:
  - `SemanticProvider.generate_claims(semantic_input) -> claim payload`
- a deterministic fixture/mock provider for tests
- a place to later add a real LLM backend without changing the analyzer contract

Important design decision:

- the first implementation should be testable without network access
- provider integration should be swappable

### 8.6 CLI Entrypoint

#### File: `isaac-training/training/scripts/run_semantic_audit.py`

Current state:

- missing

What to implement:

- CLI that accepts:
  - static bundle dir or bundle name
  - dynamic bundle dir or bundle name
  - output path / reports root
  - optional provider mode
- writes namespaced semantic report bundle

### 8.7 Tests

#### File: `isaac-training/training/unit_test/test_env/test_semantic_analyzer.py`

Current state:

- missing

What to implement:

- pure Python tests for:
  - semantic input building
  - semantic claim schema
  - cross-validation success
  - cross-validation rejection
  - bundle writing

#### Fixtures directory:

- `isaac-training/training/unit_test/test_env/fixtures/semantic_specs/`

Suggested fixtures:

- `supported_cr_claim.json`
- `supported_ec_claim.json`
- `supported_er_claim.json`
- `unsupported_overclaim.json`

### 8.8 Report Contract Update

#### File: `isaac-training/training/analyzers/report_contract.py`

Current state:

- supports:
  - `analysis/static`
  - `analysis/dynamic`

What to extend:

- add:
  - `analysis/semantic`
- define expected semantic bundle artifacts

This should happen before full report generation so the namespace remains
stable.

---

## 9. Recommended Implementation Order

The safest implementation order is:

1. add semantic claim schema
2. add semantic input builder
3. add semantic cross-check layer
4. add mock provider adapter
5. add semantic analyzer
6. add CLI entrypoint
7. add synthetic fixtures and tests
8. only then connect a real LLM backend

This keeps the phase testable and deterministic from the start.

---

## 10. Validation Plan

Phase 6 should be validated in three layers.

### 10.1 Pure Schema / Cross-Check Tests

Validate:

- claim schema serialization
- evidence reference validation
- witness-to-claim alignment
- unsupported over-claim rejection

### 10.2 Synthetic Bundle Validation

Feed known synthetic `static + dynamic` bundles and ensure:

- a `C-R` case yields a supported `C-R` claim
- an `E-C` case yields a supported `E-C` claim
- an `E-R` case yields a supported `E-R` claim
- ambiguous evidence yields weak or rejected claims

### 10.3 Real Evidence Smoke Test

Run semantic analysis on the accepted real bundles already produced in Phase 5:

- baseline nominal-vs-shifted aggregate dynamic bundle
- `eval nominal-vs-shifted` dynamic bundle
- `train nominal-vs-shifted` dynamic bundle
- the latest static audit bundle

Expected result:

- semantic bundle writes successfully
- claims are grounded in real `evidence_ids` / `witness_ids`
- no claim is accepted without support

---

## 11. Exit Criteria

Phase 6 is complete when:

1. a semantic bundle can be produced from existing static + dynamic bundles
2. semantic claims are emitted in a machine-readable schema
3. claims are cross-validated against evidence before acceptance
4. at least synthetic `C-R / E-C / E-R` cases are diagnosed in the correct direction
5. at least one real accepted bundle can produce a grounded semantic diagnosis

At that point the project is ready for:

- Phase 7 unified report generation
- Phase 8 repair proposal generation

---

## 12. What Phase 6 Should Not Try To Solve

Phase 6 should not yet:

- merge every analyzer into one final user-facing report
- choose the final repair automatically
- rerun training or evaluation
- mutate the spec directly

Those are later pipeline responsibilities.

Phase 6 succeeds if it turns evidence into **grounded semantic diagnosis**, not
if it already closes the repair loop.
