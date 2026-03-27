# Phase 11: Create the Benchmark and Release CRE-v1

## 1. Purpose

Phase 11 is the stage where the project moves from:

- "the CRE pipeline works end-to-end inside the repository"

to:

- "the CRE pipeline can be packaged, replayed, and demonstrated as a stable
  benchmark and a release-grade engineering artifact."

The direct goal of this phase is to turn the already unified stack into a
repeatable benchmark suite and a first credible `CRE-v1` release story.

This phase corresponds to:

- [doc/roadmap.md](../roadmap.md) `Phase 11. Create the benchmark and release CRE-v1`
- [doc/system_architecture_and _control_flow.md](../system_architecture_and%20_control_flow.md)
  especially the full loop:
  `spec -> generate scenes -> run policies -> collect logs -> analyze inconsistencies -> propose repair -> validate repair -> update spec`
- the Phase 10 close-out contract implemented in:
  - `analysis/integration/<bundle>/integration_acceptance.json`
  - `analysis/integration/<bundle>/native_execution_consumer.json`
  - accepted native `baseline / eval / train` comparisons

---

## 2. Why Phase 11 Starts Here

Phases 0-10 already established:

- versioned scene/spec objects,
- unified runtime evidence,
- baseline / eval / train execution paths,
- static / dynamic / semantic analysis,
- report / repair / validation loops,
- and native Phase 10 integration proof.

What is still missing is the **benchmark-and-release layer**:

- a stable clean benchmark,
- stable injected inconsistency benchmarks,
- packaged detector/report/repair/validation examples,
- and a reproducible way to demonstrate the whole system without repo-local
  detective work.

Phase 11 is where the project stops being "only an internal integrated system"
and becomes "a repeatable benchmarked framework."

---

## 3. Scope of Phase 11

Phase 11 should implement **benchmark packaging and release orchestration**,
not new witness theory.

In scope:

- define benchmarkable clean and injected spec families,
- package repeatable benchmark cases for:
  - clean
  - injected `C-R`
  - injected `E-C`
  - injected `E-R`
- produce reproducible analysis/report/repair/validation exemplars,
- package a release-grade `CRE-v1` demo path,
- freeze the benchmark/run manifest contract.

Out of scope:

- brand-new witness definitions,
- new LLM reasoning paradigms,
- deployment hardware integration,
- cloud service dependency as a mandatory path.

Those belong to later iterations or optional release hardening.

---

## 4. API-Key Policy for Phase 11

Phase 11 **does not require an API key by default**.

The benchmark and release path should be runnable with:

- existing static/dynamic analyzers,
- semantic bundles produced via:
  - mock provider mode, or
  - previously generated machine-readable semantic artifacts,
- and deterministic evidence-first contracts already implemented in Phases 4-10.

Real provider usage should remain **optional**:

- a real OpenAI/Azure-compatible provider may be enabled for release demos,
- but it must not be a prerequisite for:
  - benchmark generation,
  - benchmark replay,
  - report generation,
  - repair generation,
  - repair validation.

Therefore:

- **you do not need to provide an API key to start Phase 11 planning or the
  first implementation batches**
- API key support should remain a later optional execution path with explicit
  preflight checks

---

## 5. Authoritative Phase 11 Inputs

Phase 11 should treat the following as authoritative inputs for `v1` packaging.

### 5.1 Benchmarkable Spec Inputs

- `isaac-training/training/cfg/spec_cfg/*.yaml`
- `isaac-training/training/cfg/env_cfg/*.yaml`
- clean spec plus injected inconsistency variants

### 5.2 Authoritative Runtime / Analysis Inputs

- accepted run directories under `isaac-training/training/logs/`
- namespaced bundles under:
  - `analysis/static`
  - `analysis/dynamic`
  - `analysis/semantic`
  - `analysis/report`
  - `analysis/repair`
  - `analysis/validation`
  - `analysis/integration`

### 5.3 Native Integration Proof Inputs

- `analysis/integration/<bundle>/integration_acceptance.json`
- `analysis/integration/<bundle>/native_execution_consumer.json`
- native original-vs-repaired comparison bundles for:
  - `baseline`
  - `eval`
  - `train`

### 5.4 Release-Orchestration Inputs

- benchmark case manifests
- release templates / summaries
- optional provider configuration in mock/offline mode by default

---

## 6. Required Phase 11 Outputs

Phase 11 should introduce two lightweight namespaces:

- `analysis/benchmark/<bundle_name>/`
- `analysis/release/<bundle_name>/`

The first machine-readable benchmark bundle should contain at least:

- `benchmark_manifest.json`
- `benchmark_cases.json`
- `benchmark_matrix.json`
- `benchmark_summary.json`
- `manifest.json`

The first machine-readable release bundle should contain at least:

- `release_plan.json`
- `release_artifacts.json`
- `demo_matrix.json`
- `release_summary.json`
- `manifest.json`

The first human-readable artifacts should contain at least:

- `benchmark_summary.md`
- `release_summary.md`

---

## 7. Initial Phase 11 Benchmark Scope

The first version should package a minimal but meaningful benchmark suite:

1. **Clean benchmark**
   - nominal spec
   - expected low inconsistency signal

2. **Injected `C-R` benchmark**
   - reward/constraint conflict variant
   - expected static + semantic + repair response

3. **Injected `E-C` benchmark**
   - coverage/critical-scene mismatch variant
   - expected dynamic + semantic + repair response

4. **Injected `E-R` benchmark**
   - shifted robustness mismatch variant
   - expected dynamic + semantic + repair response

Each benchmark case should carry:

- spec references,
- env-family references,
- expected execution modes,
- expected analyzers,
- expected report/repair/validation flow.

---

## 8. File-Level Implementation Plan

Phase 11 should start with the following files.

1. **`isaac-training/training/cfg/benchmark_cfg/*.yaml`**
   - define clean and injected benchmark cases
   - define grouped suite manifests

2. **`isaac-training/training/pipeline/benchmark_suite.py`**
   - compile benchmark configs into executable suite plans
   - freeze benchmark manifest schema

3. **`isaac-training/training/scripts/run_benchmark_suite.py`**
   - CLI entrypoint for benchmark generation and replay

4. **`isaac-training/training/pipeline/release_bundle.py`**
   - package benchmark outputs, report artifacts, repair-validation exemplars
   - write release-grade machine-readable bundle

5. **`isaac-training/training/scripts/run_release_packaging.py`**
   - CLI entrypoint for release packaging

6. **`isaac-training/training/unit_test/test_env/test_benchmark_suite.py`**
   - focused regression coverage for benchmark-manifest correctness

7. **`isaac-training/training/unit_test/test_env/test_release_bundle.py`**
   - focused regression coverage for release bundle shape and required artifacts

---

## 9. Suggested Implementation Batches

### Batch A. Benchmark Case Freezing

Goal:

- freeze the first benchmark case manifest and suite config
- ensure clean / `C-R` / `E-C` / `E-R` cases are explicit objects

### Batch B. Benchmark Replay and Namespaced Packaging

Goal:

- generate `analysis/benchmark/<bundle>/`
- prove the benchmark suite is replayable from machine-readable manifests

### Batch C. Release Bundle and Demo Matrix

Goal:

- generate `analysis/release/<bundle>/`
- package an end-to-end clean-vs-injected demonstration
- keep real LLM provider usage optional

---

## 10. Exit Criteria

Phase 11 can be considered complete when:

1. clean and injected benchmark cases are frozen as machine-readable suite
   objects.
2. the system can repeatedly demonstrate:
   - detection
   - attribution
   - repair proposal
   - repair validation
   on benchmarked cases.
3. a machine-readable benchmark bundle exists and can be regenerated without ad
   hoc manual steps.
4. a machine-readable release bundle exists and clearly states the packaged
   demo/evidence surface of `CRE-v1`.
5. the default benchmark/release path does not require a live API key.

---

## 11. What Phase 11 Should Unlock Next

If Phase 11 is completed, the project will be in a much better position for:

- stable research packaging,
- repeatable clean-vs-injected demonstrations,
- publishable engineering artifacts,
- and later optional integration of real-provider semantic demos without
  disturbing the evidence-first core pipeline.
