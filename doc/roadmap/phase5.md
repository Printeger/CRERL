# Phase 5: Dynamic Analyzer and Rollout-Based Witness Metrics

## 1. Purpose

Phase 5 is the stage where the project moves from:

- "we can statically audit the spec before training"

to:

- "we can turn accepted rollouts into quantitative CRE witness evidence."

The direct goal of this phase is to implement the first **non-LLM dynamic
analyzer** for the CRE stack.

This analyzer should consume the artifacts stabilized in Phases 2-4:

- accepted CRE runtime logs,
- baseline rollout logs,
- RL rollout logs,
- static audit bundles,

and produce machine-readable dynamic evidence for the three witness families:

- `W_CR`: reward-violation coupling
- `W_EC`: critical-state coverage
- `W_ER`: transfer fragility under environment shift

This phase corresponds to:

- [doc/roadmap.md](../roadmap.md) `Phase 5. Implement the Dynamic Analyzer`
- [doc/system_architecture_and _control_flow.md](../system_architecture_and%20_control_flow.md) `Layer E. Dynamic Analyzer`
- [doc/dev_log/phase_4.md](../dev_log/phase_4.md) `Next Step`

---

## 2. Why Phase 5 Starts Here

Phases 1-4 already established:

- a family-based scene backend,
- acceptance-gated execution paths,
- comparable baseline evidence sources,
- a deterministic machine-readable `SpecIR`,
- a namespaced static audit contract under:
  - `analysis/static`
  - `analysis/dynamic`

What is still missing is the runtime question:

`do the executed policies produce measurable evidence of C-R / E-C / E-R inconsistency?`

This is exactly the role of the dynamic analyzer.

The first dynamic analyzer should not try to solve the full CRE diagnosis
problem. Its first job is narrower and more useful:

1. load accepted run directories deterministically;
2. compute rollout-level and run-level dynamic metrics;
3. aggregate those metrics into the first machine-readable witness report;
4. validate the metric directions on synthetic and known-contrast runs.

That gives later LLM reasoning and repair stages a quantitative runtime base.

---

## 3. Scope of Phase 5

Phase 5 should implement **dynamic witness computation only**.

In scope:

- load accepted run directories from:
  - manual flight
  - baseline rollouts
  - evaluation rollouts
  - training rollouts
- compute the first version of:
  - `W_CR`
  - `W_EC`
  - `W_ER`
- emit machine-readable dynamic reports under the shared report namespace
- validate metrics against synthetic and real known-contrast cases

Out of scope:

- LLM semantic reasoning
- repair proposal generation
- final multi-source report aggregation
- automatic repair validation

Those belong to later phases.

---

## 4. Inputs the Dynamic Analyzer Must Read

The dynamic analyzer should treat the following as the authoritative inputs for
`v0`.

### 4.1 Accepted CRE Run Directories

Run directories under:

`isaac-training/training/logs/<run_id>/`

that have already passed:

- `acceptance.json`

Minimum required artifacts:

- `manifest.json`
- `steps.jsonl`
- `episodes.jsonl`
- `summary.json`
- `acceptance.json`

### 4.2 Runtime Log Schema

The analyzer should consume the canonical Phase 2/3 runtime fields, including:

- `scene_id`
- `scenario_type`
- `scene_cfg_name`
- `position`
- `velocity`
- `yaw_rate`
- `goal_distance`
- `reward_total`
- `reward_components`
- `collision_flag`
- `min_obstacle_distance`
- `near_violation_flag`
- `out_of_bounds_flag`
- `done_type`
- `source`

### 4.3 Static Audit Context

Dynamic analysis should be able to read the current static audit contract and
optionally enrich its own report with:

- spec version
- static bundle references
- report namespace contract

Relevant existing artifacts:

- `analysis/static/<bundle_name>/static_report.json`
- `analysis/report_namespace_contract.json`

### 4.4 SpecIR and Detector Thresholds

Dynamic metrics must be parameterized by the same `SpecIR` / detector config
used by the static analyzer.

Relevant existing inputs:

- `isaac-training/training/analyzers/spec_ir.py`
- `isaac-training/training/cfg/spec_cfg/*.yaml`
- `isaac-training/training/cfg/detector_cfg/detector_thresholds.yaml`
- `isaac-training/training/cfg/detector_cfg/witness_weights.yaml`

---

## 5. First Working Definitions for the Dynamic Witnesses

Phase 5 does not need the final paper-perfect witness definitions.

It needs stable **engineering definitions** that:

- are computable from current logs,
- move in the correct direction on known cases,
- are easy to trace back to raw evidence.

### 5.1 `W_CR`: Reward-Violation Coupling

Question:

`does the execution path earn reward while concentrating near violations or hard boundary events?`

The first implementation should combine several measurable sub-signals:

- near-violation reward concentration
- fraction of positive-reward steps inside near-violation states
- negative correlation between clearance and reward
- collision/out-of-bounds terminal runs with unexpectedly strong return

Engineering intuition:

- if a policy earns disproportionately strong reward while operating near the
  safety boundary, `W_CR` should increase

### 5.2 `W_EC`: Critical-State Coverage

Question:

`does the policy actually visit the critical regions that matter for the declared environment family?`

The first implementation should measure:

- visit rate of near-violation states
- coverage of critical distance bands
- coverage of scene families:
  - `nominal`
  - `boundary_critical`
  - `shifted`
- coverage of dynamic-hazard episodes when the family declares dynamic hazards

Engineering intuition:

- if the spec claims boundary-critical or dynamic-hazard scenarios matter but
  the rollout set rarely reaches those states, `W_EC` should indicate weak
  critical coverage

### 5.3 `W_ER`: Transfer Fragility Under Shift

Question:

`how much does behavior degrade when the environment family changes from nominal to shifted or otherwise OOD?`

The first implementation should compare matched run groups and compute:

- success-rate gap
- collision-rate gap
- min-distance gap
- average-return gap
- near-violation-ratio gap

Engineering intuition:

- if performance is acceptable in `nominal` but degrades sharply in `shifted`,
  `W_ER` should increase

---

## 6. Deliverables

Phase 5 should produce the following deliverables.

### 6.1 Dynamic Metric Kernels

A deterministic metric layer that can compute:

- rollout-level metrics
- run-level aggregates
- pairwise cross-run comparison metrics

### 6.2 Dynamic Analyzer

A higher-level analyzer that:

- reads accepted run directories,
- computes `W_CR / W_EC / W_ER`,
- emits findings and summaries,
- writes namespaced dynamic analysis bundles

### 6.3 Dynamic Report

A machine-readable report, for example:

- `dynamic_report.json`

written under:

- `analysis/dynamic/<bundle_name>/`

with:

- overall status
- metric values
- witness summaries
- comparison groups
- evidence references
- affected scene families / execution modes

### 6.4 Dynamic Validation Fixtures

Synthetic or fixture-based run sets that intentionally encode:

- strong reward-boundary coupling
- weak critical-state coverage
- strong nominal-to-shifted degradation

These fixtures will be the first acceptance gate for the dynamic analyzer.

---

## 7. File-Level Implementation Plan

### 7.1 Metric Kernel Layer

#### File: `isaac-training/training/analyzers/dynamic_metrics.py`

Current state:

- placeholder only

What to implement:

- a structured result schema such as:
  - `DynamicMetricResult`
  - `DynamicWitnessResult`
- deterministic metric helpers for:
  - `compute_reward_violation_coupling(...)`
  - `compute_critical_state_coverage(...)`
  - `compute_transfer_fragility(...)`
- supporting utilities for:
  - reward concentration over near-violation states
  - scene-family-conditioned episode slicing
  - nominal-vs-shifted comparison

Important design decision:

- keep this file focused on metric kernels, not report writing

### 7.2 Dynamic Analyzer Orchestration

#### File: `isaac-training/training/analyzers/dynamic_analyzer.py`

Recommended new file.

What to implement:

- `run_dynamic_analysis(...)`
- `run_dynamic_analysis_bundle(...)`
- grouping logic for:
  - one-run analysis
  - matched-run comparison
  - scene-family-conditioned summaries

Expected outputs:

- per-run metric summary
- witness summary for `W_CR / W_EC / W_ER`
- machine-readable findings

Important design decision:

- this file should orchestrate dynamic metrics the same way
  `detector_runner.py` orchestrates static checks

### 7.3 Runtime Log Loading Helpers

#### File: `isaac-training/training/runtime_logging/episode_writer.py`

Current state:

- basic utility layer only

What to add:

- stable read helpers for:
  - `steps.jsonl`
  - `episodes.jsonl`
  - `summary.json`
  - `acceptance.json`
- convenience loaders such as:
  - `load_run_directory(...)`
  - `load_accepted_run_directory(...)`

Reason:

- the dynamic analyzer should not reimplement ad hoc JSONL loading in multiple places

### 7.4 Report Contract Integration

#### File: `isaac-training/training/analyzers/report_contract.py`

Current state:

- static and dynamic namespaces already defined

What to add:

- confirm dynamic bundle naming guidance
- confirm required dynamic artifacts
- ensure dynamic bundle manifests match the static bundle contract style

This phase should fully activate the `analysis/dynamic` branch, not just reserve it.

### 7.5 CLI Entrypoint

#### File: `isaac-training/training/scripts/run_dynamic_audit.py`

Recommended new file.

What to implement:

- a lightweight CLI parallel to `run_static_audit.py`
- inputs:
  - one or more `--run-dir`
  - optional `--compare-run-dir`
  - optional `--reports-root`
  - optional `--bundle-name`
- outputs:
  - namespaced dynamic report bundle
  - stdout summary

This should be the main manual entrypoint for Phase 5 validation.

### 7.6 Detector Runner Integration

#### File: `isaac-training/training/analyzers/detector_runner.py`

What to add:

- optional dynamic-analysis entrypoints, or a clean handoff to
  `dynamic_analyzer.py`
- keep the naming and bundle-writing conventions aligned with static analysis

Short-term acceptable compromise:

- static and dynamic runners may remain separate modules
- but they should share:
  - report namespaces
  - bundle structure
  - summary semantics

### 7.7 Tests

#### File: `isaac-training/training/unit_test/test_env/test_dynamic_analyzer.py`

Recommended new file.

What to implement:

- synthetic log fixtures for:
  - reward near boundary
  - missing critical-state exposure
  - strong nominal-shifted transfer gap
- assertions for:
  - metric direction
  - bundle generation
  - report schema completeness

This should become the main acceptance gate for Phase 5.

---

## 8. Recommended Implementation Order

1. Replace the placeholder in `dynamic_metrics.py` with the first deterministic metric kernels.
2. Add stable run-directory loaders in `runtime_logging/`.
3. Create `dynamic_analyzer.py`.
4. Add `run_dynamic_audit.py`.
5. Add synthetic dynamic log fixtures and `test_dynamic_analyzer.py`.
6. Validate the analyzer on:
   - accepted baseline run directories
   - accepted train/eval run directories
   - synthetic bad-run fixtures
7. Only after the dynamic analyzer is stable, start Phase 6 semantic/LLM diagnosis.

---

## 9. Validation Strategy

Phase 5 should be validated in three ways.

### 9.1 Clean Accepted-Run Validation

Run the dynamic analyzer on current accepted CRE run directories.

Expected result:

- report is generated successfully
- the dynamic bundle is written under `analysis/dynamic`
- no schema failure occurs on accepted logs

### 9.2 Known-Contrast Validation

Compare known execution modes, such as:

- `random` vs `conservative`
- `greedy` vs `conservative`
- `nominal` vs `shifted`

Expected result:

- conservative policies should show safer distance/collision profiles
- greedy policies should show stronger boundary-seeking signals
- shifted comparisons should reveal measurable degradation where appropriate

### 9.3 Synthetic Bad-Run Validation

Run the dynamic analyzer on intentionally crafted log fixtures.

Expected result:

- the intended witness direction is detected
- the report points to the correct metric family
- the result is deterministic and repeatable without Isaac Sim

This is the most important validation for Phase 5.

---

## 10. Exit Criteria

Phase 5 is complete when:

- `dynamic_metrics.py` computes deterministic rollout-based metric kernels
- a machine-readable dynamic report can be emitted under `analysis/dynamic`
- the analyzer can distinguish at least one known `W_CR` contrast
- the analyzer can distinguish at least one known `W_EC` contrast
- the analyzer can distinguish at least one known `W_ER` contrast
- synthetic bad-run fixtures trigger the expected metric direction changes
- the analyzer can run on accepted run directories without Isaac Sim

---

## 11. Non-Goals for This Phase

Phase 5 does **not** need to:

- use the LLM
- produce repair proposals
- merge static + dynamic + LLM findings into the final unified report
- decide final inconsistency class with full semantic attribution

Those belong to later phases.

---

## 12. What Comes Immediately After Phase 5

Once the dynamic analyzer is stable, the next step is:

- Phase 6 semantic / LLM-assisted diagnosis

At that point the project will have:

- pre-training static evidence
- rollout-based dynamic evidence
- accepted namespaced report bundles for both static and dynamic analysis

That is the right handoff point for:

- semantic diagnosis
- repair proposal ranking
- later unified report aggregation.
