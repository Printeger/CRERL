# CRE Verification README

Updated: 2026-03-27

## 1. What Is Still Not Finished

According to:

- `doc/roadmap.md`
- `doc/roadmap_closeout.md`
- `doc/system_architecture_and _control_flow.md`
- `doc/structure-preview-en.html`

the current roadmap is complete as written, but a few things are still **not
claimed as finished**.

These are the main items that are **not part of the completed roadmap
baseline**:

1. **real-provider semantic demo as a required path**
   - the semantic analyzer supports a mock/offline path by default
   - real provider integration is optional, not required for default
     verification

2. **deployment hardware integration**
   - ROS / onboard / real-robot deployment is not part of the finished
     `CRE-v1` baseline

3. **release hardening / publication polish**
   - benchmark/release packaging exists
   - but paper-grade packaging, polished demos, and external distribution
     hardening are still follow-up work

4. **future roadmap extension**
   - the current roadmap ends at `Phase 11`
   - anything beyond this should be treated as a new roadmap extension, not as
     an unfinished part of the current one

In short:

- **the roadmap baseline is complete**
- **future work still exists**
- but that future work is now post-roadmap work, not unfinished roadmap work

## 2. Main Modules

The system now has six main layers.

### 2.1 Specification Layer

Purpose:
- define the audited object precisely

Main files:
- `doc/specs/Env_Primitive_Spec_v0.md`
- `doc/specs/env_gen_rules.md`
- `isaac-training/training/cfg/spec_cfg/*.yaml`
- `isaac-training/training/cfg/env_cfg/*.yaml`

What this layer owns:
- constraint spec
- reward spec
- policy/runtime expectations
- scene-family rules

### 2.2 Environment and Runtime Substrate

Purpose:
- turn scene-family spec into executable scenes

Main files:
- `isaac-training/training/envs/env_gen.py`
- `isaac-training/training/envs/runtime/scene_family_bridge.py`
- `isaac-training/training/unit_test/test_flight.py`

What this layer owns:
- `nominal / boundary_critical / shifted` scene families
- scene validation
- scene-family binding
- manual scene inspection harness

### 2.3 Execution and Logging Layer

Purpose:
- run policies and emit machine-readable evidence

Main files:
- `isaac-training/training/envs/cre_logging.py`
- `isaac-training/training/runtime_logging/logger.py`
- `isaac-training/training/runtime_logging/training_log_adapter.py`
- `isaac-training/training/runtime_logging/acceptance.py`
- `isaac-training/training/logs/`

What this layer owns:
- step-level logs
- episode-level logs
- run manifests
- acceptance checks for accepted runs

### 2.4 Policy Execution Layer

Purpose:
- produce rollouts from multiple execution modes

Main files:
- `isaac-training/training/scripts/train.py`
- `isaac-training/training/scripts/eval.py`
- `isaac-training/training/scripts/run_baseline.py`
- `isaac-training/training/execution/baseline_runner.py`
- `isaac-training/training/execution/baseline_policies.py`

Execution modes:
- manual flight
- baseline
- eval
- train

### 2.5 Analysis / Report / Repair / Validation Layer

Purpose:
- turn runtime evidence into diagnosis, repair, and repair validation

Main files:
- `isaac-training/training/analyzers/spec_ir.py`
- `isaac-training/training/analyzers/static_checks.py`
- `isaac-training/training/analyzers/dynamic_analyzer.py`
- `isaac-training/training/analyzers/semantic_analyzer.py`
- `isaac-training/training/analyzers/report_generator.py`
- `isaac-training/training/repair/rule_based_repair.py`
- `isaac-training/training/repair/validation_runner.py`

What this layer owns:
- static audit
- dynamic audit
- semantic diagnosis
- unified report
- repair proposal
- repair validation

### 2.6 Integration / Benchmark / Release Layer

Purpose:
- prove the native stack is wired together and package `CRE-v1`

Main files:
- `isaac-training/training/pipeline/integration_bundle.py`
- `isaac-training/training/pipeline/benchmark_suite.py`
- `isaac-training/training/pipeline/release_bundle.py`
- `isaac-training/training/scripts/run_integration_audit.py`
- `isaac-training/training/scripts/run_benchmark_suite.py`
- `isaac-training/training/scripts/run_release_packaging.py`

What this layer owns:
- native integration proof
- benchmark suite packaging
- clean-vs-injected demo packaging
- release close-out evidence

## 3. Canonical Call Flow

The canonical flow is now:

`spec -> scene generation -> execution -> logs -> static/dynamic/semantic analysis -> report -> repair -> validation -> integration -> benchmark -> release`

More concretely:

1. **spec/config**
   - read `cfg/spec_cfg/*.yaml`
   - read `cfg/env_cfg/*.yaml`

2. **scene compilation**
   - `env_gen.py`
   - `scene_family_bridge.py`

3. **execution**
   - manual: `test_flight.py`
   - baseline: `run_baseline.py`
   - eval: `eval.py`
   - train: `train.py`

4. **runtime evidence**
   - `training/logs/<run>/`
   - accepted run schema and run-level acceptance

5. **analysis**
   - `run_static_audit.py`
   - `run_dynamic_audit.py`
   - `run_semantic_audit.py`

6. **unified report**
   - `run_report_audit.py`

7. **repair**
   - `run_repair_audit.py`

8. **repair validation**
   - `run_validation_audit.py`

9. **native integration proof**
   - `run_integration_audit.py`

10. **benchmark and release packaging**
    - `run_benchmark_suite.py`
    - `run_release_packaging.py`

This matches the architecture intent shown in:

- `doc/system_architecture_and _control_flow.md`
- `doc/structure-preview-en.html`

The HTML preview is more conceptual and presentation-oriented, but it aligns
with the implemented stack:

- IR/spec layer
- Static Analyzer
- Dynamic Analyzer
- LLM/Semantic Analyzer
- Repair Engine
- Validation and release packaging

## 4. Module Interface Map

The most useful way to understand the implemented pipeline is to treat each
major module as a stage in an artifact contract chain.

The table below shows:

- what each stage reads,
- what it produces,
- and which downstream stage consumes those outputs.

| Module / Stage | Main Inputs | Main Outputs | Downstream Consumer |
| --- | --- | --- | --- |
| spec/config layer | `cfg/spec_cfg/*.yaml`, `cfg/env_cfg/*.yaml`, spec docs | machine-readable `C/R/E/P` rules, scene-family definitions | `env_gen.py`, `scene_family_bridge.py`, static analyzer, benchmark/release packaging |
| `env_gen.py` | scene-family configs, primitive rules, request seed / difficulty | validated scene config, compiled scene primitives, scene tags | `scene_family_bridge.py`, `test_flight.py`, `env.py` |
| `scene_family_bridge.py` | scene-family config, scene compiler, spec/runtime config | effective scene binding, effective spec binding, runtime metadata | `env.py`, `train.py`, `eval.py`, `run_baseline.py`, integration audit |
| execution entrypoints (`test_flight.py`, `run_baseline.py`, `eval.py`, `train.py`) | effective scene/spec binding, policy/runtime setup, repaired-preview context when applicable | runtime rollouts, raw step/episode evidence, accepted run candidates | logging layer, accepted run directories under `training/logs/` |
| logging layer (`cre_logging.py`, `training_log_adapter.py`, `runtime_logging/acceptance.py`) | rollout stats, scene metadata, done types, reward components | `manifest.json`, `steps.jsonl`, `episodes.jsonl`, `summary.json`, `acceptance.json` | dynamic analyzer, validation runner, native integration proof |
| static audit (`run_static_audit.py`) | spec/config bundle, scene-family rules, detector thresholds | `analysis/static/<bundle>/static_report.json`, `summary.json`, `manifest.json` | semantic analyzer, report generator |
| dynamic audit (`run_dynamic_audit.py`) | accepted run dirs, logs root, optional comparison runs, static bundle context | `analysis/dynamic/<bundle>/dynamic_report.json`, `dynamic_evidence.json`, `semantic_inputs.json` | semantic analyzer, report generator, integration proof |
| semantic audit (`run_semantic_audit.py`) | static bundle, dynamic bundle, semantic input builder, provider mode | `analysis/semantic/<bundle>/semantic_report.json`, `semantic_claims.json`, `semantic_merge_input.json`, `claim_consumer.json` | report generator, later repair/report consumers |
| report audit (`run_report_audit.py`) | static bundle, dynamic bundle, semantic bundle | `analysis/report/<bundle>/report.json`, `ranked_findings.json`, `repair_handoff.json`, `report_summary.md` | repair engine |
| repair audit (`run_repair_audit.py`) | report bundle, repair rules, spec config files | `analysis/repair/<bundle>/repair_plan.json`, `repair_candidates.json`, `spec_patch.json`, `validation_request.json`, `validation_context_preview.json` | validation runner, integration audit |
| validation audit (`run_validation_audit.py`) | repair bundle, original accepted runs, bounded rerun adapters, repair preview | `analysis/validation/<bundle>/validation_decision.json`, `comparison.json`, `validation_runs.json`, `post_repair_evidence.json` | integration audit, Phase 10 native consumer, future post-repair consumers |
| integration audit (`run_integration_audit.py`) | scene-family binding, repair preview, optional native accepted runs, optional comparison bundle | `analysis/integration/<bundle>/integration_summary.json`, `integration_acceptance.json`, `native_execution_consumer.json` | benchmark/release packaging |
| benchmark suite (`run_benchmark_suite.py`) | benchmark case YAMLs, optional integration/native readiness assumptions | `analysis/benchmark/<bundle>/benchmark_cases.json`, `benchmark_matrix.json`, `benchmark_summary.json` | release packaging |
| release packaging (`run_release_packaging.py`) | benchmark bundle, optional integration bundle, spec/env cfg directories | `analysis/release/<bundle>/release_summary.json`, `release_artifacts.json`, `demo_consumer.json`, `release_acceptance.json` | human operator, release close-out, future external packaging |

Two practical rules follow from this map:

1. **Information should move forward as namespaced artifacts**
   - not as implicit runtime state
   - when debugging, inspect the nearest upstream bundle first

2. **Rule changes should move from upstream to downstream**
   - first `cfg/spec_cfg` or `cfg/env_cfg`
   - then scene/runtime binding
   - then execution/logging
   - then analyzers
   - finally report/repair/validation/integration/benchmark/release

If you change this order, you often end up patching downstream interpretation
without actually changing the audited object or the evidence source.

## 5. Before You Verify Anything

Use two execution contexts:

1. **Lightweight checks**
   - use `python3`
   - good for:
     - focused unit tests
     - report/packaging CLIs
     - doc/contract checks

2. **Real execution checks**
   - use the `NavRL` environment
   - needed for:
     - `test_flight.py`
     - `run_baseline.py`
     - `train.py`
     - `eval.py`
     - Isaac/Omni-based reruns

Suggested setup:

```bash
cd /home/mint/rl_dev/CRERL
conda activate NavRL
```

Important note:

- **API key is not required for the default verification path**
- semantic verification can be done with `--provider-mode mock`

## 6. Module-by-Module Verification Plan

This section is the recommended order if you want to personally verify each
module.

### Step A. Verify the Specification / IR Layer

Goal:
- confirm the machine-readable spec/config layer is loadable and consistent

Recommended checks:

```bash
pytest -q \
  isaac-training/training/unit_test/test_env/test_spec_ir.py \
  isaac-training/training/unit_test/test_env/test_scene_family_bridge.py
```

What to look for:
- spec files load
- scene-family bridge loads `nominal / boundary_critical / shifted`
- policy/runtime expectations are available

### Step B. Verify the Scene Backend

Goal:
- confirm the environment substrate is valid and reproducible

Recommended checks:

```bash
pytest -q \
  isaac-training/training/unit_test/test_env/test_scene_generation.py \
  isaac-training/training/unit_test/test_env/test_primitives.py \
  isaac-training/training/unit_test/test_env/test_perforated_slab.py \
  isaac-training/training/unit_test/test_env/test_serialization_and_motion.py
```

Manual inspection:

```bash
conda activate NavRL
python isaac-training/training/unit_test/test_flight.py headless=False
```

What to look for:
- scene generation succeeds
- family switching works
- LiDAR and runtime scene rendering work

### Step C. Verify the Logging Layer

Goal:
- confirm all CRE runtime evidence is structurally correct

Recommended checks:

```bash
pytest -q \
  isaac-training/training/unit_test/test_env/test_cre_logging.py \
  isaac-training/training/unit_test/test_env/test_training_log_adapter.py \
  isaac-training/training/unit_test/test_env/test_run_acceptance.py
```

What to look for:
- `manifest.json`
- `steps.jsonl`
- `episodes.jsonl`
- `summary.json`
- `acceptance.json`

### Step D. Verify Baseline Execution

Goal:
- confirm baseline execution paths are alive and produce accepted runs

Lightweight checks:

```bash
pytest -q \
  isaac-training/training/unit_test/test_env/test_baseline_policies.py \
  isaac-training/training/unit_test/test_env/test_baseline_runner.py
```

Real run:

```bash
conda activate NavRL
python isaac-training/training/scripts/run_baseline.py headless=True baseline.name=greedy
```

What to look for:
- accepted run directory under `isaac-training/training/logs/`
- `success_rate / collision_rate / min_distance / average_return`

### Step E. Verify the Static Analyzer

Goal:
- confirm pre-training audit works

Recommended checks:

```bash
pytest -q isaac-training/training/unit_test/test_env/test_static_analyzer.py
```

CLI smoke test:

```bash
python3 isaac-training/training/scripts/run_static_audit.py \
  --reports-root /tmp/crerl_verify_reports \
  --bundle-name static_verify \
  --output /tmp/crerl_verify_reports/static_report_copy.json
```

Expected artifact:
- `/tmp/crerl_verify_reports/analysis/static/static_verify/`

### Step F. Verify the Dynamic Analyzer

Goal:
- confirm accepted runs can be turned into witness evidence

Recommended checks:

```bash
pytest -q isaac-training/training/unit_test/test_env/test_dynamic_analyzer.py
```

CLI smoke test using real accepted runs already in repo logs:

```bash
python3 isaac-training/training/scripts/run_dynamic_audit.py \
  --run-dir isaac-training/training/logs/baseline_greedy_rollout_20260326_190209 \
  --compare-run-dir isaac-training/training/logs/baseline_greedy_rollout_20260326_223636 \
  --reports-root /tmp/crerl_verify_reports \
  --bundle-name dynamic_verify \
  --output /tmp/crerl_verify_reports/dynamic_report_copy.json
```

Expected artifact:
- `/tmp/crerl_verify_reports/analysis/dynamic/dynamic_verify/`

### Step G. Verify the Semantic Analyzer

Goal:
- confirm semantic diagnosis works in evidence-first mode

Recommended checks:

```bash
pytest -q isaac-training/training/unit_test/test_env/test_semantic_analyzer.py
```

CLI smoke test:

```bash
python3 isaac-training/training/scripts/run_semantic_audit.py \
  --static-bundle-dir /tmp/crerl_verify_reports/analysis/static/static_verify \
  --dynamic-bundle-dir /tmp/crerl_verify_reports/analysis/dynamic/dynamic_verify \
  --provider-mode mock \
  --reports-root /tmp/crerl_verify_reports \
  --bundle-name semantic_verify \
  --output /tmp/crerl_verify_reports/semantic_report_copy.json
```

Expected artifact:
- `/tmp/crerl_verify_reports/analysis/semantic/semantic_verify/`

### Step H. Verify Unified Report Generation

Goal:
- confirm `static + dynamic + semantic` merge correctly

Recommended checks:

```bash
pytest -q isaac-training/training/unit_test/test_env/test_report_generator.py
```

CLI smoke test:

```bash
python3 isaac-training/training/scripts/run_report_audit.py \
  --static-bundle-dir /tmp/crerl_verify_reports/analysis/static/static_verify \
  --dynamic-bundle-dir /tmp/crerl_verify_reports/analysis/dynamic/dynamic_verify \
  --semantic-bundle-dir /tmp/crerl_verify_reports/analysis/semantic/semantic_verify \
  --reports-root /tmp/crerl_verify_reports \
  --bundle-name report_verify \
  --output /tmp/crerl_verify_reports/report_copy.json
```

Expected artifact:
- `/tmp/crerl_verify_reports/analysis/report/report_verify/`

### Step I. Verify Repair Proposal

Goal:
- confirm the report can be turned into structured repair candidates

Recommended checks:

```bash
pytest -q isaac-training/training/unit_test/test_env/test_repair_engine.py
```

CLI smoke test:

```bash
python3 isaac-training/training/scripts/run_repair_audit.py \
  --report-bundle-dir /tmp/crerl_verify_reports/analysis/report/report_verify \
  --reports-root /tmp/crerl_verify_reports \
  --bundle-name repair_verify \
  --output /tmp/crerl_verify_reports/repair_plan_copy.json
```

Expected artifact:
- `/tmp/crerl_verify_reports/analysis/repair/repair_verify/`

### Step J. Verify Repair Validation

Goal:
- confirm original-vs-repaired comparison works

Recommended checks:

```bash
pytest -q isaac-training/training/unit_test/test_env/test_validation_loop.py
```

CLI smoke test:

```bash
python3 isaac-training/training/scripts/run_validation_audit.py \
  --repair-bundle-dir /tmp/crerl_verify_reports/analysis/repair/repair_verify \
  --logs-root isaac-training/training/logs \
  --trigger-rerun \
  --rerun-mode auto \
  --reports-root /tmp/crerl_verify_reports \
  --bundle-name validation_verify \
  --output /tmp/crerl_verify_reports/validation_decision_copy.json
```

Expected artifact:
- `/tmp/crerl_verify_reports/analysis/validation/validation_verify/`

### Step K. Verify Native Integration

Goal:
- confirm the native stack can be summarized as one integration proof

Recommended checks:

```bash
pytest -q isaac-training/training/unit_test/test_env/test_integration_stack.py
```

CLI smoke test:

```bash
python3 isaac-training/training/scripts/run_integration_audit.py \
  --scene-family nominal \
  --reports-root /tmp/crerl_verify_reports \
  --bundle-name integration_verify \
  --output /tmp/crerl_verify_reports/integration_summary_copy.json
```

Expected artifact:
- `/tmp/crerl_verify_reports/analysis/integration/integration_verify/`

### Step L. Verify Benchmark and Release Packaging

Goal:
- confirm `CRE-v1` packaging works without a live API key

Recommended checks:

```bash
pytest -q \
  isaac-training/training/unit_test/test_env/test_benchmark_suite.py \
  isaac-training/training/unit_test/test_env/test_release_bundle.py
```

Benchmark packaging:

```bash
python3 isaac-training/training/scripts/run_benchmark_suite.py \
  --reports-root /tmp/crerl_verify_reports \
  --bundle-name benchmark_verify \
  --output /tmp/crerl_verify_reports/benchmark_summary_copy.json
```

Release packaging:

```bash
python3 isaac-training/training/scripts/run_release_packaging.py \
  --reports-root /tmp/crerl_verify_reports \
  --bundle-name release_verify \
  --integration-bundle-dir /tmp/crerl_phase10_reports/analysis/integration/integration_phase10_native_closeout \
  --output /tmp/crerl_verify_reports/release_summary_copy.json
```

Expected artifacts:
- `/tmp/crerl_verify_reports/analysis/benchmark/benchmark_verify/`
- `/tmp/crerl_verify_reports/analysis/release/release_verify/`

## 7. Full End-to-End Verification

If you want to verify the **whole pipeline**, use this order:

1. run `test_flight.py` once
2. run one baseline rollout
3. generate:
   - static bundle
   - dynamic bundle
   - semantic bundle
   - report bundle
   - repair bundle
   - validation bundle
   - integration bundle
   - benchmark bundle
   - release bundle

If you want a **one-command smoke test**, use:

```bash
bash isaac-training/training/scripts/run_full_smoke_test.sh \
  --reports-root /tmp/crerl_verify_reports \
  --bundle-prefix verify
```

This script will:

- activate `conda activate NavRL`
- run the full smoke-test chain from static -> release
- write per-step CLI outputs under the reports root
- write a combined summary at:
  - `/tmp/crerl_verify_reports/full_smoke_summary.json`

The shortest reproducible full chain is:

```bash
python3 isaac-training/training/scripts/run_static_audit.py \
  --reports-root /tmp/crerl_verify_reports \
  --bundle-name static_verify

python3 isaac-training/training/scripts/run_dynamic_audit.py \
  --run-dir isaac-training/training/logs/baseline_greedy_rollout_20260326_190209 \
  --compare-run-dir isaac-training/training/logs/baseline_greedy_rollout_20260326_223636 \
  --reports-root /tmp/crerl_verify_reports \
  --bundle-name dynamic_verify

python3 isaac-training/training/scripts/run_semantic_audit.py \
  --static-bundle-dir /tmp/crerl_verify_reports/analysis/static/static_verify \
  --dynamic-bundle-dir /tmp/crerl_verify_reports/analysis/dynamic/dynamic_verify \
  --provider-mode mock \
  --reports-root /tmp/crerl_verify_reports \
  --bundle-name semantic_verify

python3 isaac-training/training/scripts/run_report_audit.py \
  --static-bundle-dir /tmp/crerl_verify_reports/analysis/static/static_verify \
  --dynamic-bundle-dir /tmp/crerl_verify_reports/analysis/dynamic/dynamic_verify \
  --semantic-bundle-dir /tmp/crerl_verify_reports/analysis/semantic/semantic_verify \
  --reports-root /tmp/crerl_verify_reports \
  --bundle-name report_verify

python3 isaac-training/training/scripts/run_repair_audit.py \
  --report-bundle-dir /tmp/crerl_verify_reports/analysis/report/report_verify \
  --reports-root /tmp/crerl_verify_reports \
  --bundle-name repair_verify

python3 isaac-training/training/scripts/run_validation_audit.py \
  --repair-bundle-dir /tmp/crerl_verify_reports/analysis/repair/repair_verify \
  --logs-root isaac-training/training/logs \
  --trigger-rerun \
  --rerun-mode auto \
  --reports-root /tmp/crerl_verify_reports \
  --bundle-name validation_verify

python3 isaac-training/training/scripts/run_integration_audit.py \
  --scene-family nominal \
  --reports-root /tmp/crerl_verify_reports \
  --bundle-name integration_verify

python3 isaac-training/training/scripts/run_benchmark_suite.py \
  --reports-root /tmp/crerl_verify_reports \
  --bundle-name benchmark_verify

python3 isaac-training/training/scripts/run_release_packaging.py \
  --reports-root /tmp/crerl_verify_reports \
  --bundle-name release_verify \
  --integration-bundle-dir /tmp/crerl_phase10_reports/analysis/integration/integration_phase10_native_closeout
```

At the end, check these namespaces:

- `analysis/static`
- `analysis/dynamic`
- `analysis/semantic`
- `analysis/report`
- `analysis/repair`
- `analysis/validation`
- `analysis/integration`
- `analysis/benchmark`
- `analysis/release`

## 8. What “Correct” Looks Like

For a healthy verification result, you should expect:

1. accepted run directories under `isaac-training/training/logs/`
2. every analysis stage to emit a namespaced bundle
3. `release_summary.json` to show:
   - `api_key_required_by_default = false`
4. release close-out to show:
   - `phase11_exit_ready = true`

## 9. Practical Advice

If you want the fastest confidence path:

1. run the focused tests first
2. run `test_flight.py` once
3. run one baseline rollout
4. run the audit chain from static -> release

If you want the deepest confidence path:

1. verify each module in order from A to L
2. then rerun the full chain with your own generated run directories instead of
   the existing repository examples

## 10. Bottom Line

The current repo is no longer just a collection of separate scripts.

It is now a layered CRE pipeline with:

- spec/config
- scene backend
- execution/logging
- analyzers
- report/repair/validation
- integration
- benchmark
- release

The roadmap baseline is complete, but this README is the practical checklist
for verifying that the implementation actually behaves the way the completed
roadmap says it should.
