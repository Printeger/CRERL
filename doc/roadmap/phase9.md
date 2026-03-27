# Phase 9: Repair Validation Loop and Evidence-Based Repair Acceptance

## 1. Purpose

Phase 9 is the stage where the project moves from:

- "we can generate explicit repair proposals"

to:

- "we can decide, using evidence, whether a proposed repair actually helped."

The direct goal of this phase is to implement the first **repair-validation
loop** for the CRE stack.

This validation layer should consume the artifacts stabilized in Phases 2-8:

- accepted runtime log bundles,
- static audit bundles,
- dynamic analysis bundles,
- semantic analysis bundles,
- unified Phase 7 report bundles,
- Phase 8 repair bundles,
- `repair_validation.json`,
- `validation_request.json`,

and turn them into one controlled validation substrate that explains:

- what repaired specification was evaluated,
- what baseline or policy execution path was rerun,
- which metrics were compared,
- whether consistency improved,
- whether safety improved,
- whether performance regressed beyond tolerance,
- and whether the repair should be accepted or rejected.

This phase corresponds to:

- [doc/roadmap.md](../roadmap.md) `Phase 9. Build the repair-validation loop`
- [doc/system_architecture_and _control_flow.md](../system_architecture_and%20_control_flow.md)
  `Stage 5. Repair and validate`
- the Phase 8 handoff contract implemented in:
  - `repair_validation.json`
  - `validation_request.json`

---

## 2. Why Phase 9 Starts Here

Phases 4-8 already established:

- deterministic static audit bundles under `analysis/static`,
- accepted runtime logs and dynamic witness bundles under `analysis/dynamic`,
- evidence-grounded semantic claims under `analysis/semantic`,
- ranked unified reports under `analysis/report`,
- namespaced repair bundles under `analysis/repair`,
- a machine-readable Phase 9 handoff in `validation_request.json`.

What is still missing is the **repair outcome loop**:

`given a repair proposal, how do we rerun the right evaluations and decide whether the repair should be accepted?`

Phase 9 is that loop.

The first Phase 9 implementation should not try to:

- retrain from scratch for every repair,
- automatically mutate and overwrite the canonical spec files,
- or jump immediately to deployment hardware validation.

Its first job is narrower and more useful:

1. load a Phase 8 repair bundle;
2. interpret the `validation_request.json` contract;
3. rerun targeted evaluation using the existing execution stack;
4. compare original and repaired evidence;
5. produce an explicit accept/reject decision with reasons.

That gives the project its first full closed loop:

`report -> repair -> validation decision`

---

## 3. Scope of Phase 9

Phase 9 should implement **repair validation only**.

In scope:

- validation-request loading
- repaired-spec preview execution
- targeted baseline / eval / train reruns
- original vs repaired metric comparison
- accept / reject decision logic
- machine-readable validation bundle generation

Out of scope:

- arbitrary in-place mutation of canonical spec files
- unconstrained retraining campaigns
- large-scale hyperparameter search
- deployment / real robot acceptance

Those belong to later stages.

---

## 4. Phase 9 Inputs

The repair-validation loop should treat the following as authoritative Phase 9
inputs for `v0`.

### 4.1 Phase 8 Repair Bundle

Under:

`analysis/repair/<bundle_name>/`

Minimum required artifacts:

- `repair_plan.json`
- `spec_patch.json`
- `spec_patch_preview.json`
- `repair_validation.json`
- `validation_request.json`
- `manifest.json`

Optional but expected:

- `repair_summary.json`
- `repair_summary.md`

### 4.2 Original Evidence Context

The validation loop must be able to recover the pre-repair evidence from:

- `analysis/report/<bundle_name>/`
- `analysis/dynamic/<bundle_name>/`
- `analysis/static/<bundle_name>/`
- accepted run directories under `training/logs/`

This is required because Phase 9 compares:

- original evidence
- repaired evidence

### 4.3 Specification and Config Sources

The validation loop must read:

- `cfg/spec_cfg/*.yaml`
- `cfg/env_cfg/*.yaml`

and build a **preview-only repaired spec state** before rerunning execution.

### 4.4 Report Namespace Contract

The validation loop must consume:

- `analysis/report_namespace_contract.json`

This remains the canonical source for:

- upstream namespace locations,
- artifact compatibility,
- and output namespace expectations for validation bundles.

---

## 5. Required Validation Outputs

Phase 9 should introduce a new namespace:

`analysis/validation/<bundle_name>/`

The first machine-readable validation bundle should contain at least:

- `validation_plan.json`
- `validation_runs.json`
- `comparison.json`
- `validation_decision.json`
- `validation_summary.json`
- `manifest.json`

The first human-readable bundle should contain at least:

- `validation_summary.md`

### 5.1 `validation_plan.json`

This should contain:

- input repair bundle references,
- selected execution modes,
- selected scene families,
- target metrics,
- acceptance thresholds,
- comparison protocol.

### 5.2 `validation_runs.json`

This should record:

- original run references,
- repaired run references,
- rerun mode,
- run status,
- artifact locations.

### 5.3 `comparison.json`

This should contain explicit pre/post comparison values for at least:

- consistency-related metrics
- safety-related metrics
- performance-related metrics

### 5.4 `validation_decision.json`

This should be the canonical decision artifact and contain:

- `accepted: true/false`
- `decision_type`
- `acceptance_rule`
- `decision_rationale`
- `metric_deltas`
- `blocked_by`
- `next_action`

### 5.5 `validation_summary.md`

This should explain:

- what was rerun,
- what improved,
- what regressed,
- why the repair was accepted or rejected,
- what should be tried next if rejected.

---

## 6. Initial Phase 9 Validation Scope

Phase 9 does not need the final large-scale benchmark loop yet.

It needs a controlled first validation scope that matches the current stack.

### 6.1 Supported Execution Modes

The first version should support:

- baseline reruns
- eval reruns
- train reruns only when already configured for short targeted runs

### 6.2 Supported Repair Families

The first version should validate repairs for:

- `C-R`
- `E-C`
- `E-R`

using the repair bundle contracts already stabilized in Phase 8.

### 6.3 Supported Comparison Metrics

The first version should compare at least:

- consistency witness direction:
  - `W_CR`
  - `W_EC`
  - `W_ER`
- safety metrics:
  - `collision_rate`
  - `min_distance`
  - `near_violation_ratio`
- performance metrics:
  - `average_return`
  - `success_rate`

### 6.4 Explicit Non-Goals for Phase 9

Do not implement yet:

- full retraining sweeps across many seeds
- automatic canonical spec overwrite on acceptance
- deployment / ROS-side acceptance
- repair history ranking across many generations

Phase 9 should stay evidence-first and targeted.

---

## 7. First Validation Rules

Phase 9 does not need final acceptance theory.

It needs stable engineering rules that are:

- deterministic,
- easy to audit,
- aligned with the roadmap,
- and conservative.

### 7.1 Primary Acceptance Rule

The first validation loop should explicitly check:

- `ΔConsistency > 0`
- `ΔSafety > 0`
- `ΔPerformance >= -epsilon`

Where:

- `ΔConsistency` is derived from the claim-relevant witness or metric family
- `ΔSafety` is derived from safety metrics such as `min_distance`,
  `collision_rate`, and `near_violation_ratio`
- `ΔPerformance` is derived from success or return metrics

### 7.2 Claim-Type-Aware Metric Mapping

The first version should use deterministic mappings:

- `C-R`
  - prioritize `W_CR`, `min_distance`, `near_violation_ratio`
- `E-C`
  - prioritize `W_EC`, `boundary_critical` coverage/safety metrics
- `E-R`
  - prioritize `W_ER`, `nominal_vs_shifted` gap metrics

### 7.3 Bounded Regression Rule

Even if the targeted witness improves, reject the repair if:

- collision rate worsens materially
- minimum distance drops materially
- success or return drops beyond configured tolerance

### 7.4 Missing-Evidence Rule

Reject or mark inconclusive when:

- reruns fail,
- required artifacts are missing,
- comparison metrics cannot be computed,
- the execution mode required by `validation_request.json` is unavailable.

---

## 8. File-Level Implementation Plan

The current repair and execution stack already exists, but Phase 9 is still
missing as a formal pipeline.

Phase 9 should be implemented in this order.

### 8.1 `repair/repair_validator.py`

Keep the current validator as the entry-side contract checker.

Phase 9 should consume, not replace, this file.

### 8.2 `repair/validation_request_loader.py`

Add a small loader that:

- reads `validation_request.json`
- validates required fields
- resolves original report / repair bundle references
- normalizes execution targets

This should become the first stable Phase 9 input parser.

### 8.3 `repair/patch_executor.py`

Extend the existing preview logic so Phase 9 can build a **previewed repaired
spec state** without mutating source files.

Responsibilities:

- materialize a preview object for patched spec/config values
- expose file/path/value deltas in a deterministic structure
- support temporary evaluation contexts

The first version should remain preview-only.

### 8.4 `repair/validation_runner.py`

Implement the first targeted rerun driver.

Responsibilities:

- choose the correct execution path from the validation request
- launch baseline / eval / train reruns in a bounded way
- store repaired run references
- preserve machine-readable run metadata

### 8.5 `repair/comparison.py`

Implement original vs repaired metric comparison.

Responsibilities:

- load original evidence
- load repaired evidence
- compute metric deltas
- compute claim-aware acceptance signals

### 8.6 `repair/decision.py`

Implement the first explicit decision rule.

Responsibilities:

- apply the Phase 9 acceptance rule
- classify:
  - accepted
  - rejected
  - inconclusive
- emit machine-readable rationale

### 8.7 `scripts/run_validation_audit.py`

Add a CLI that:

- reads a Phase 8 repair bundle
- reruns the requested execution mode(s)
- compares original vs repaired evidence
- writes an `analysis/validation/<bundle_name>/` bundle

### 8.8 `unit_test/test_env/test_validation_loop.py`

Add focused tests for:

- validation-request loading
- repaired preview state construction
- comparison logic
- acceptance rule
- deterministic output on synthetic repair fixtures

---

## 9. Suggested Bundle Schema for `v0`

The first validation bundle should follow this shape:

```text
analysis/validation/<bundle_name>/
  validation_plan.json
  validation_runs.json
  comparison.json
  validation_decision.json
  validation_summary.json
  validation_summary.md
  manifest.json
```

Recommended metadata fields:

- `bundle_type = validation_bundle.v1`
- `validation_plan_type = phase9_validation_plan.v1`
- `comparison_schema = phase9_metric_comparison.v1`
- `decision_schema = phase9_validation_decision.v1`

---

## 10. Implementation Order

Recommended execution order:

1. add `validation_request_loader.py`
2. extend preview support in `patch_executor.py`
3. implement `validation_runner.py`
4. implement `comparison.py`
5. implement `decision.py`
6. add `run_validation_audit.py`
7. add `test_validation_loop.py`

This keeps the work aligned with the already-stable Phase 8 repair handoff.

---

## 11. Validation Strategy

Phase 9 validation should start from synthetic and report-level tests, then
move to targeted real reruns.

### 11.1 Synthetic Repair-to-Decision Tests

Create fixtures where:

- repaired metrics improve clearly
- repaired metrics regress clearly
- repaired metrics are mixed / inconclusive
- required evidence is missing

Expected result:

- the validation loop returns the correct decision class
- the metric-delta rationale is machine-readable

### 11.2 Real Repair-Bundle Smoke Tests

Run Phase 9 over real Phase 8 repair bundles produced from:

- baseline matched pairs
- eval matched pairs
- train matched pairs

Expected result:

- a validation bundle is generated
- comparison outputs are deterministic
- the decision artifact is machine-readable and traceable

### 11.3 Non-Destructive Preview Check

Expected result:

- Phase 9 can evaluate a repaired preview state
- source files remain unchanged unless explicitly requested later

---

## 12. Exit Criteria

Phase 9 is complete when:

1. a Phase 8 repair bundle can be turned into a machine-readable validation bundle;
2. original vs repaired evidence is compared deterministically;
3. the system emits an explicit accepted / rejected / inconclusive decision;
4. the decision is justified by consistency, safety, and performance deltas;
5. the repaired validation path does not require scraping ad hoc analyzer output.

---

## 13. Immediate Next Step

The most effective first implementation batch is:

1. add `repair/validation_request_loader.py`
2. extend `repair/patch_executor.py` preview support for validation contexts
3. add `unit_test/test_env/test_validation_loop.py`

That gives the project its first real Phase 9 validation substrate without yet
requiring a full large-scale rerun framework.
