# Phase 10: Unify the RL Training Stack with the CRE Pipeline

## 1. Purpose

Phase 10 is the stage where the project moves from:

- "repair validation can rerun targeted execution paths against repaired specs"

to:

- "the main training stack itself is a first-class CRE execution path rather
  than a partially separate subsystem."

The direct goal of this phase is to make:

- `env.py`
- `train.py`
- `eval.py`
- baseline execution

all consume the same:

- family-based scene specification,
- repaired-spec preview context,
- runtime logging contract,
- analysis/report/repair/validation namespace contract.

This phase corresponds to:

- [doc/roadmap.md](../roadmap.md) `Phase 10. Unify the RL training stack with the CRE pipeline`
- [doc/system_architecture_and _control_flow.md](../system_architecture_and%20_control_flow.md)
  `Layer D. Policy Execution Layer` and `Layer F. Report, Repair, and Validation Layer`
- the Phase 9 close-out contract implemented in:
  - `validation_context_preview.json`
  - `post_repair_evidence.json`
  - `phase10_post_repair_evidence_consumer.v2`

---

## 2. Why Phase 10 Starts Here

Phases 1-9 already established:

- family-based scene configs and runtime profiles,
- unified CRE logging,
- stable baseline / eval / train execution modes,
- static / dynamic / semantic analyzers,
- report generation,
- repair proposal generation,
- repair-validation bundles and post-repair evidence.

What is still missing is the **training-stack integration loop**:

`can the main RL execution stack consume the same scene/spec/repair pipeline end-to-end without ad hoc glue?`

Right now the repository is much closer than before, but it still has a gap:

- `env.py`, `train.py`, and `eval.py` are CRE-aware,
- but they are not yet treated as the authoritative continuation of:
  - `scene family -> logs -> analysis -> repair -> validation`
- and repaired-spec preview context is still mostly threaded through bounded
  rerun adapters rather than a general training-stack contract.

Phase 10 is the stage where that gap gets closed.

---

## 3. Scope of Phase 10

Phase 10 should implement **training-stack unification**, not a new analyzer.

In scope:

- make the RL environment consume the same scene-family backend contract as the
  rest of CRE,
- make training / eval / baseline all accept repaired-spec preview context from
  the same interface,
- make training-time accepted runs directly usable as CRE evidence without
  validation-only wrappers,
- make original-spec vs repaired-spec comparisons reproducible from the same
  execution harness,
- add a small machine-readable integration bundle that records the end-to-end
  wiring state.

Out of scope:

- new witness definitions,
- new semantic reasoning,
- new repair operators,
- deployment / hardware validation,
- benchmark packaging and release engineering.

Those belong to later phases.

---

## 4. Authoritative Phase 10 Inputs

Phase 10 should treat the following as authoritative inputs for `v0`.

### 4.1 Scene-Family Specification Inputs

- `isaac-training/training/cfg/env_cfg/*.yaml`
- `isaac-training/training/envs/env_gen.py`
- `isaac-training/training/envs/runtime/scene_family_bridge.py`

These define the canonical environment-family substrate that training should
consume.

### 4.2 Spec and Repair Context Inputs

- `isaac-training/training/cfg/spec_cfg/*.yaml`
- `analysis/repair/<bundle>/validation_context_preview.json`
- `analysis/validation/<bundle>/post_repair_evidence.json`

These define the canonical repaired-spec preview and the downstream consumer
contract that training/eval must respect.

### 4.3 Execution Entry Points

- `isaac-training/training/scripts/env.py`
- `isaac-training/training/scripts/train.py`
- `isaac-training/training/scripts/eval.py`
- `isaac-training/training/scripts/run_baseline.py`

These are the execution paths that must stop drifting apart.

### 4.4 Runtime Evidence Contract

- `isaac-training/training/envs/cre_logging.py`
- `isaac-training/training/runtime_logging/*.py`
- accepted run directories under `isaac-training/training/logs/`

These remain the authoritative evidence interface for downstream phases.

### 4.5 Namespace and Report Contract

- `analysis/report_namespace_contract.json`
- namespaced bundles under:
  - `analysis/static`
  - `analysis/dynamic`
  - `analysis/semantic`
  - `analysis/report`
  - `analysis/repair`
  - `analysis/validation`

Phase 10 should not invent a parallel, incompatible evidence path.

---

## 5. Required Phase 10 Outputs

Phase 10 should introduce one lightweight integration namespace:

`analysis/integration/<bundle_name>/`

The first machine-readable integration bundle should contain at least:

- `integration_plan.json`
- `execution_matrix.json`
- `run_binding.json`
- `integration_acceptance.json`
- `integration_summary.json`
- `manifest.json`

The first human-readable artifact should contain at least:

- `integration_summary.md`

### 5.1 `integration_plan.json`

This should contain:

- target execution modes,
- scene family scope,
- repaired-spec preview reference,
- expected run types,
- expected output contracts,
- validation linkage.

### 5.2 `execution_matrix.json`

This should record, for each execution mode:

- whether it consumes scene-family backend directly,
- whether it consumes repaired-spec preview directly,
- whether it emits accepted CRE logs directly,
- whether it can participate in original-vs-repaired comparison without
  validation-specific glue.

### 5.3 `run_binding.json`

This should record:

- how `scene_family_backend`
- `scene_logging`
- `validation_context_preview`
- `scene_id_prefix`
- and repaired-spec preview context

map into each of:

- `baseline`
- `eval`
- `train`

### 5.4 `integration_acceptance.json`

This should say whether the training stack is considered Phase-10 unified, with
checks such as:

- direct scene-family binding,
- direct runtime metadata binding,
- direct repaired-preview binding,
- consistent accepted-run output,
- comparison-readiness.

### 5.5 `integration_summary.md`

This should explain:

- what is already unified,
- what still requires validation-only adapter glue,
- what prevents the training stack from being a fully native CRE execution
  substrate.

---

## 6. Initial Phase 10 Unification Scope

Phase 10 does not need to fully redesign RL training.

It needs a controlled integration scope that matches the current system.

### 6.1 Direct Scene-Family Backend Consumption

The first version should ensure:

- `env.py`
- `train.py`
- `eval.py`
- `run_baseline.py`

all consume the same family-based scene backend contract without special-case
logic islands.

### 6.2 Direct Repaired-Spec Preview Consumption

The first version should ensure:

- repaired preview context can be passed into the main training/eval/baseline
  harnesses directly,
- not only via Phase 9 rerun wrappers.

### 6.3 Direct CRE Logging and Acceptance

The first version should ensure that runs produced from the unified training
stack:

- already satisfy CRE accepted-run expectations,
- already expose consistent `scene_id / scenario_type / scene_cfg_name`,
- and do not require bespoke post-processing before later analysis.

### 6.4 Direct Comparison Readiness

The first version should support:

- original-spec vs repaired-spec
- nominal vs shifted
- boundary-critical vs nominal

comparisons from the same execution harness, not from separate ad hoc tooling.

---

## 7. First Engineering Rules for Phase 10

Phase 10 should follow these integration rules.

### 7.1 One Scene Contract

Training, evaluation, baselines, and validation should all read the same
family-based scene contract.

No execution path should invent its own incompatible scene metadata layer.

### 7.2 One Runtime Evidence Contract

Every execution mode must produce accepted CRE logs that already satisfy:

- runtime acceptance,
- family metadata binding,
- comparison-readiness.

### 7.3 One Repaired-Preview Contract

Repaired-spec preview context should be consumable through one stable interface.

The training stack should not require a Phase 9-only wrapper to understand
patched spec context.

### 7.4 Integration Before Scale

Phase 10 should prioritize:

- correct wiring,
- deterministic evidence,
- machine-readable integration status,

before large-scale training campaigns.

---

## 8. File-Level Implementation Plan

The most direct implementation order is:

1. **`isaac-training/training/scripts/env.py`**
   - make repaired-preview context a first-class runtime input
   - expose effective scene/spec binding in `get_cre_runtime_metadata()`

2. **`isaac-training/training/envs/runtime/scene_family_bridge.py`**
   - unify scene-family compilation for both standard and repaired-preview
     execution
   - make effective family/config selection explicit and serializable

3. **`isaac-training/training/runtime_logging/training_log_adapter.py`**
   - ensure unified training/eval/baseline runs expose the same effective scene
     and preview metadata
   - keep accepted-run outputs directly comparison-ready

4. **`isaac-training/training/scripts/train.py`**
   - consume repaired-preview context directly
   - emit integration-ready accepted runs without validation-only glue

5. **`isaac-training/training/scripts/eval.py`**
   - same direct repaired-preview and scene-family binding

6. **`isaac-training/training/scripts/run_baseline.py`**
   - align with the same direct repaired-preview binding path

7. **`isaac-training/training/pipeline/integration_bundle.py`** or equivalent
   - create the first machine-readable `analysis/integration` bundle writer

8. **`isaac-training/training/scripts/run_integration_audit.py`**
   - CLI entrypoint for Phase 10 integration checks

9. **`isaac-training/training/unit_test/test_env/test_integration_stack.py`**
   - focused regression suite for direct scene/spec/log binding

---

## 9. Suggested Implementation Batches

### Batch A. Native Repaired-Preview Binding

Goal:

- let `env.py`, `train.py`, `eval.py`, and `run_baseline.py` consume repaired
  preview context without relying on validation-only rerun wrappers.

### Batch B. Integration Bundle and Acceptance

Goal:

- create `analysis/integration/<bundle>/`
- make integration status machine-readable
- lock the unified contract with focused tests

### Batch C. Real Original-vs-Repaired Training Stack Comparison

Goal:

- run real baseline / eval / train comparisons from the same native harness
- confirm no validation-only glue is required for standard CRE comparison.

---

## 10. Exit Criteria

Phase 10 can be considered complete when:

1. `env.py`, `train.py`, `eval.py`, and `run_baseline.py` all consume the same
   family-based scene contract directly.
2. repaired preview context can be injected into the native execution stack
   without relying on Phase 9-specific wrapper-only semantics.
3. unified accepted runs from baseline / eval / train are directly usable by
   the CRE analyzers and comparison tooling.
4. original-spec vs repaired-spec comparisons can be launched from the same
   execution harness.
5. a machine-readable `analysis/integration/<bundle>/` bundle exists and can
   state whether the RL stack is truly aligned with the CRE pipeline.

---

## 11. What Phase 10 Should Unlock Next

If Phase 10 is completed, the project will be in a much better position for
Phase 11:

- benchmark packaging,
- repeatable clean-vs-injected demonstrations,
- release-ready end-to-end examples,
- and a more credible `CRE-v1` engineering story.
