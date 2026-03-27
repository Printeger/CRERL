# Phase 8: Repair Engine and Structured Spec-Patch Generation

## 1. Purpose

Phase 8 is the stage where the project moves from:

- "we can explain what is wrong and rank likely inconsistency types"

to:

- "we can generate explicit, auditable repair proposals over `C`, `R`, and `E`."

The direct goal of this phase is to implement the first **repair engine** for
the CRE stack.

This repair layer should consume the artifacts stabilized in Phases 4-7:

- machine-readable `SpecIR`,
- static audit bundles,
- dynamic analysis bundles,
- semantic analysis bundles,
- unified Phase 7 report bundles,
- `repair_handoff.json`,
- `claim_consumer.json`,
- `semantic_merge_input.json`,

and turn them into one controlled repair substrate that explains:

- what claim the repair targets,
- what component of `C`, `R`, or `E` will be changed,
- what exact delta is proposed,
- why the delta is minimal,
- what later Phase 9 validation should measure.

This phase corresponds to:

- [doc/roadmap.md](../roadmap.md) `Phase 8. Implement the repair engine`
- [doc/system_architecture_and _control_flow.md](../system_architecture_and%20_control_flow.md)
  `Layer F. Report, Repair, and Validation Layer`
- the Phase 7 handoff contract implemented in `repair_handoff.json`

---

## 2. Why Phase 8 Starts Here

Phases 4-7 already established:

- a deterministic static audit contract under `analysis/static`,
- accepted runtime logs and dynamic witness bundles under `analysis/dynamic`,
- evidence-grounded semantic claims under `analysis/semantic`,
- one namespaced unified report under `analysis/report`,
- a structured `repair_handoff.json` with:
  - ranked repair-ready claims,
  - impacted components,
  - repair direction hints,
  - evidence references,
  - repair ordering.

What is still missing is the **repair proposal layer**:

`given a ranked report and a repair handoff, what explicit spec patch should be proposed next?`

Phase 8 is that layer.

The first repair engine should not try to:

- retrain the policy,
- automatically accept a repair,
- mutate files in-place without traceability,
- or jump directly to deployment validation.

Its first job is narrower and more useful:

1. load the repair-facing outputs from Phase 7;
2. map repair-ready claims into a small library of allowed repair operators;
3. produce explicit spec deltas over `C`, `R`, or `E`;
4. write a machine-readable repair bundle for Phase 9 validation.

That gives Phase 9 a clean evaluation target instead of forcing validation to
guess what the repair was supposed to change.

---

## 3. Scope of Phase 8

Phase 8 should implement **repair proposal generation only**.

In scope:

- claim-to-repair mapping
- repair operator selection
- structured spec patch representation
- patch preview / non-destructive execution planning
- repair history tracking
- machine-readable repair bundle generation

Out of scope:

- retraining as part of repair generation
- repair acceptance / rejection
- quantitative post-repair comparison
- deployment validation

Those belong to Phase 9.

---

## 4. Phase 8 Inputs

The repair engine should treat the following as the authoritative Phase 8
inputs for `v0`.

### 4.1 Unified Report Bundle

Under:

`analysis/report/<bundle_name>/`

Minimum required artifacts:

- `report.json`
- `ranked_findings.json`
- `repair_handoff.json`
- `summary.json`
- `manifest.json`

Optional but expected:

- `report_summary.md`

### 4.2 Semantic Repair Context

Under:

`analysis/semantic/<bundle_name>/`

Minimum required artifacts:

- `claim_consumer.json`
- `semantic_merge_input.json`

These remain useful because they preserve semantic rationale and supported
claim structure that may be richer than the flattened report bundle.

### 4.3 Specification and Config Sources

The repair engine must also read:

- `cfg/spec_cfg/*.yaml`
- `cfg/env_cfg/*.yaml`
- relevant source-path references embedded in `SpecIR`

This is the authoritative source of what can actually be patched.

### 4.4 Report Namespace Contract

The repair engine must consume:

- `analysis/report_namespace_contract.json`

This is the canonical source of:

- expected upstream namespaces,
- artifact compatibility,
- report-mode artifact requirements,
- output namespace expectations for repair bundles.

---

## 5. Required Repair Outputs

Phase 8 should introduce a new namespace:

`analysis/repair/<bundle_name>/`

The first machine-readable repair bundle should contain at least:

- `repair_plan.json`
- `repair_candidates.json`
- `spec_patch.json`
- `repair_summary.json`
- `manifest.json`

The first human-readable bundle should contain at least:

- `repair_summary.md`

### 5.1 `repair_plan.json`

This should be the canonical Phase 8 repair bundle and contain:

- bundle metadata
- input report references
- selected primary repair target
- operator selection rationale
- selected claim records
- targeted `C/R/E` components
- patch scope
- expected validation objectives for Phase 9

### 5.2 `repair_candidates.json`

This should contain the candidate set before final selection, including:

- `candidate_id`
- `origin_claim_id`
- `claim_type`
- `target_component`
- `operator_type`
- `priority`
- `estimated_edit_cost`
- `expected_metric_direction`

### 5.3 `spec_patch.json`

This should contain the explicit delta that would later be applied or previewed:

- `patch_type`
- `target_file`
- `target_path`
- `operation`
- `before`
- `after`
- `rationale`

### 5.4 `repair_summary.md`

This should explain:

- what repair was selected,
- why it was selected,
- what it changes,
- what Phase 9 should validate next.

---

## 6. Initial Repair Scope

Phase 8 does not need the full future repair library.

It needs a controlled, interpretable first set that matches the roadmap.

### 6.1 `C-R` Repairs

Initial operators:

- reward reweighting
- safety-penalty strengthening
- boundary-aware penalty injection
- proxy-dominance reduction

Expected target files:

- `cfg/spec_cfg/reward_spec_v0.yaml`
- future reward/runtime config mirrors

### 6.2 `E-C` Repairs

Initial operators:

- critical scenario injection
- family oversampling
- curriculum rebalance
- boundary-critical density increase

Expected target files:

- `cfg/env_cfg/scene_cfg_boundary_critical.yaml`
- `cfg/env_cfg/scene_cfg_shifted.yaml`
- scene-family distribution rules

### 6.3 `E-R` Repairs

Initial operators:

- structured domain randomization increase
- shifted-family rebalance
- robustness-oriented family expansion
- environment-family weight rebalance

Expected target files:

- `cfg/env_cfg/*.yaml`
- environment family distribution rules
- selected runtime schema expectations if justified

### 6.4 Explicit Non-Goals for Phase 8

Do not implement yet:

- unconstrained arbitrary YAML mutation
- direct code patch generation for large Python modules
- policy-network surgery
- automatic retraining loops

Phase 8 should stay auditable and spec-facing.

---

## 7. First Repair-Selection Rules

Phase 8 does not need final repair theory.

It needs stable engineering rules that are:

- deterministic,
- easy to audit,
- conservative,
- aligned with the Phase 7 handoff.

### 7.1 Primary Selection Rule

The first repair engine should start from:

- `repair_handoff.primary_claim_type`
- `repair_handoff.primary_repair_direction`
- `repair_handoff.repair_order[0]`

This is the anchor for primary repair proposal generation.

### 7.2 Minimality Rule

Prefer the smallest patch that:

- targets the primary claim type,
- touches the fewest components,
- preserves other spec sections whenever possible,
- is expressible as a structured delta.

### 7.3 Evidence Coverage Rule

A repair candidate should only be promoted when:

- it has at least one linked claim,
- it has at least one evidence reference,
- it has a clear expected metric direction,
- it has a concrete target path in `C`, `R`, or `E`.

### 7.4 Conflict Rule

If multiple claim types appear in the handoff:

- the primary claim type drives candidate generation first,
- secondary claim types may be included only as explicitly marked secondary candidates,
- Phase 8 should not silently merge incompatible repairs.

### 7.5 Output Determinism Rule

Given the same:

- report bundle,
- semantic repair context,
- spec files,

the repair engine should emit the same candidate set and selected patch.

---

## 8. File-Level Implementation Plan

The current repair package already exists but is mostly placeholder code.

Phase 8 should upgrade it in this order.

### 8.1 `repair/proposal_schema.py`

Upgrade the placeholder dataclass into a stable repair schema layer.

Add at least:

- `RepairCandidate`
- `SpecPatchOperation`
- `SpecPatch`
- `RepairPlan`
- `RepairBundleSummary`

This file should become the machine-readable core of Phase 8.

### 8.2 `repair/rule_based_repair.py`

Implement the first rule-based repair candidate generator.

Responsibilities:

- read `repair_handoff.json`
- map claim types to operator families
- emit candidate repairs
- score candidates by:
  - primary-claim alignment
  - edit cost
  - scope
  - evidence support

### 8.3 `repair/patch_executor.py`

Implement non-destructive patch planning and preview.

Responsibilities:

- convert selected candidate into structured patch operations
- optionally materialize preview files or preview payloads
- avoid mutating source files by default

The first version should support preview generation, not auto-apply.

### 8.4 `repair/acceptance.py`

Implement lightweight preflight acceptance for repair proposals.

Responsibilities:

- schema completeness checks
- supported operator checks
- file/path existence checks
- patch minimality checks

This is not Phase 9 validation. It is only proposal sanity checking.

### 8.5 `repair/repair_validator.py`

Keep this file narrow for now.

First version responsibilities:

- validate that a generated patch is internally coherent
- validate that expected Phase 9 metrics are declared
- validate that the selected repair remains within the allowed repair library

### 8.6 `repair/llm_repair_proposer.py`

Do not make this the main path.

For `v0`, it should remain optional and secondary.

If touched at all in Phase 8, it should consume the same:

- `repair_handoff.json`
- `semantic_merge_input.json`
- `claim_consumer.json`

and emit candidates in the same schema as the rule-based path.

### 8.7 `scripts/run_repair_audit.py`

Add a CLI that:

- reads a Phase 7 report bundle
- optionally reads semantic repair context
- runs repair candidate generation
- writes an `analysis/repair/<bundle_name>/` bundle

### 8.8 `unit_test/test_env/test_repair_engine.py`

Add focused tests for:

- candidate generation
- primary-claim routing
- patch schema generation
- conflict handling
- deterministic output on synthetic report fixtures

---

## 9. Suggested Bundle Schema for `v0`

The first repair bundle should follow this shape:

```text
analysis/repair/<bundle_name>/
  repair_plan.json
  repair_candidates.json
  spec_patch.json
  repair_summary.json
  repair_summary.md
  manifest.json
```

Recommended metadata fields:

- `bundle_type = repair_generation_bundle.v1`
- `repair_plan_type = phase8_repair_plan.v1`
- `repair_candidate_schema = phase8_repair_candidate.v1`
- `spec_patch_schema = phase8_spec_patch.v1`

---

## 10. Implementation Order

Recommended execution order:

1. upgrade `proposal_schema.py`
2. implement `rule_based_repair.py`
3. implement `patch_executor.py`
4. implement `acceptance.py`
5. implement `repair_validator.py`
6. add `run_repair_audit.py`
7. add `test_repair_engine.py`

This keeps the work aligned with the already-stable report handoff.

---

## 11. Validation Strategy

Phase 8 validation should start from synthetic and report-level tests, not
full retraining.

### 11.1 Synthetic Report-to-Repair Tests

Create fixtures where:

- `C-R` is primary
- `E-C` is primary
- `E-R` is primary
- mixed-source conflict exists

Expected result:

- the repair engine chooses the correct operator family
- the selected patch targets the correct component

### 11.2 Real Bundle Smoke Tests

Run Phase 8 over real Phase 7 report bundles from:

- baseline matched pairs
- eval matched pairs
- train matched pairs

Expected result:

- a repair bundle is generated
- the selected patch is deterministic
- the bundle is machine-readable and traceable

### 11.3 Non-Destructive Preview Check

Expected result:

- Phase 8 can preview structured patches
- no source file is mutated unless explicitly requested

---

## 12. Exit Criteria

Phase 8 is complete when:

1. a Phase 7 report bundle can be turned into a machine-readable repair bundle;
2. each repair can be represented as an explicit delta on `C`, `R`, or `E`;
3. repair candidates are selected deterministically from the ranked handoff;
4. the repair engine supports at least the initial `C-R / E-C / E-R` operator families;
5. Phase 9 can consume the repair bundle without scraping analyzer-specific outputs.

---

## 13. Immediate Next Step

The most effective first implementation batch is:

1. upgrade `repair/proposal_schema.py`
2. implement `repair/rule_based_repair.py`
3. add `unit_test/test_env/test_repair_engine.py`

That gives the project its first real Phase 8 repair candidate path without
yet needing patch application or validation reruns.
