# Phase 5 Development Status

Updated: 2026-03-26

## 1. This Iteration Goal

This iteration continues Phase 5 by pushing the dynamic analyzer from
"working on accepted runs" toward "producing stable runtime evidence objects
and semantic handoff inputs for later inconsistency diagnosis."

The concrete goals were:

- add more real matched run pairs, not only one `baseline_greedy` nominal-vs-shifted pair
- stabilize grouped failure summaries into reusable dynamic evidence objects
- prepare explicit semantic-diagnosis inputs for Phase 6
- add real `eval` and `train` nominal-vs-shifted matched pairs
- keep the analyzer grounded in real accepted run directories and namespaced
  report bundles

## 2. Implemented Results

### 2.1 Stronger Phase-5 Witness Kernels Are Preserved

`isaac-training/training/analyzers/dynamic_metrics.py` remains on the stronger
Phase-5 witness definitions introduced previously:

- `W_CR` includes proximity pressure and reward-alignment effects
- `W_EC` includes family-conditioned failure pressure
- `W_ER` includes family/source shift signals

This iteration builds on those kernels rather than replacing them.

### 2.2 Dynamic Evidence Objects Added

A new module was added:

- `isaac-training/training/analyzers/dynamic_evidence.py`

It introduces stable, machine-readable dynamic evidence objects for the
Phase-5 to Phase-6 handoff.

The new evidence layer produces:

- witness summary evidence objects
- failure-hotspot evidence objects

These objects are designed to be easier for later semantic diagnosis to
consume than raw grouped metadata.

### 2.3 Dynamic Reports Now Expose First-Class Semantic Handoff Fields

`isaac-training/training/analyzers/dynamic_analyzer.py` now emits these
top-level fields directly in the dynamic report:

- `group_summaries`
- `failure_summaries`
- `static_context`
- `evidence_objects`
- `semantic_inputs`

This means later phases no longer need to reconstruct semantic inputs from
`metadata` or ad hoc report parsing.

### 2.4 Phase-6 Semantic Contract Is Now Explicit

`semantic_inputs.json` and the mirrored `semantic_inputs` field inside
`dynamic_report.json` now carry a stable Phase-6-facing contract.

The semantic handoff now explicitly includes:

- `semantic_input_type = dynamic_semantic_input.v1`
- `semantic_contract_type = phase6_dynamic_semantic_contract.v1`
- `witness_overview`
- `attribution_candidates`
- `failure_hotspots`
- `prompt_sections`
- `cross_validation_contract`
- `prompt_seeds`

The `cross_validation_contract` now tells Phase 6 how semantic claims must be
grounded back into dynamic evidence:

- supported claim types:
  - `C-R`
  - `E-C`
  - `E-R`
- required evidence fields:
  - `evidence_refs`
  - `severity`
  - `score`
  - `summary`
  - `attribution_hints`
- explicit witness mapping:
  - `C-R -> W_CR`
  - `E-C -> W_EC`
  - `E-R -> W_ER`

### 2.5 Dynamic Bundles Now Carry Stable Phase-6 Input Artifacts

Dynamic analysis bundles now include:

- `dynamic_report.json`
- `dynamic_evidence.json`
- `semantic_inputs.json`
- `summary.json`
- `manifest.json`
- `namespace_manifest.json`

This is wired through:

- `isaac-training/training/analyzers/dynamic_analyzer.py`
- `isaac-training/training/analyzers/report_contract.py`
- `isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml`

So the dynamic namespace contract now explicitly includes the semantic-handoff
artifacts.

### 2.6 `run_acceptance_check(...)` Was Stabilized

`isaac-training/training/runtime_logging/acceptance.py` now re-validates after
writing `acceptance.json`.

That means newly generated runs can become accepted in one pass instead of
requiring an immediate second acceptance call. This makes real matched-run
generation much more stable.

### 2.7 More Real Baseline Matched Run Pairs Were Added

This iteration extended the repository’s real accepted nominal-vs-shifted
matched pairs from one to three baseline sources:

- `baseline_greedy`
- `baseline_random`
- `baseline_conservative`

Real shifted accepted runs:

- `baseline_greedy_rollout_20260326_223636`
- `baseline_random_rollout_20260326_225913`
- `baseline_conservative_rollout_20260326_225934`

These now pair with existing accepted nominal runs:

- `baseline_greedy_rollout_20260326_190209`
- `baseline_random_rollout_20260326_190148`
- `baseline_conservative_rollout_20260326_190217`

### 2.8 Real `eval` and `train` Matched Pairs Were Added

This iteration also confirmed real accepted nominal-vs-shifted matched pairs
for the two non-baseline execution paths:

- `eval`
  - nominal: `eval_rollout_20260326_180829`
  - shifted: `eval_rollout_20260326_230927`
- `train`
  - nominal: `train_rollout_20260326_180849`
  - shifted: `train_rollout_20260326_230948`

All four run directories now carry:

- `acceptance.json`
- `summary.json`
- `episodes.jsonl`
- `manifest.json`

And all four are accepted with the expected scene-family metadata:

- `scenario_type = nominal/shifted`
- `scene_cfg_name = scene_cfg_nominal.yaml / scene_cfg_shifted.yaml`

### 2.9 Real Nominal-vs-Shifted Aggregate Comparison Added

On top of the three individual baseline matched pairs, an aggregate real
comparison was also validated over all three baseline sources together:

- nominal set:
  - `baseline_random`
  - `baseline_greedy`
  - `baseline_conservative`
- shifted set:
  - `baseline_random`
  - `baseline_greedy`
  - `baseline_conservative`

This gives the project a stronger real runtime contrast set than a single pair.

### 2.10 Phase-6-Facing Dynamic Evidence Is Now Stable Enough To Consume

The dynamic analyzer now outputs a more stable inconsistency-attribution
substrate:

- `evidence_objects`
  - witness summaries
  - failure hotspots
- `semantic_inputs`
  - structured witness overview
  - attribution candidates
  - prompt sections
  - cross-validation contract

This means Phase 6 can start from a stable, machine-readable dynamic evidence
layer rather than re-parsing grouped summaries ad hoc.

## 3. Main Files Added or Changed

Code files:

- `isaac-training/training/analyzers/dynamic_evidence.py`
- `isaac-training/training/analyzers/dynamic_analyzer.py`
- `isaac-training/training/analyzers/dynamic_metrics.py`
- `isaac-training/training/analyzers/__init__.py`
- `isaac-training/training/analyzers/report_contract.py`
- `isaac-training/training/runtime_logging/acceptance.py`
- `isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml`
- `isaac-training/training/unit_test/test_env/test_dynamic_analyzer.py`

Documentation/state files:

- `doc/dev_log/p5_dev_status.md`
- `Traceability.md`

## 4. How To Validate

### 4.1 Syntax Validation

Run:

```bash
python3 -m py_compile \
  isaac-training/training/analyzers/dynamic_evidence.py \
  isaac-training/training/analyzers/dynamic_analyzer.py \
  isaac-training/training/analyzers/dynamic_metrics.py \
  isaac-training/training/analyzers/__init__.py \
  isaac-training/training/analyzers/report_contract.py \
  isaac-training/training/runtime_logging/acceptance.py \
  isaac-training/training/unit_test/test_env/test_dynamic_analyzer.py \
  isaac-training/training/unit_test/test_env/test_run_acceptance.py \
  isaac-training/training/unit_test/test_env/test_static_analyzer.py \
  isaac-training/training/unit_test/test_env/test_spec_ir.py
```

Expected result:

- no syntax error

### 4.2 Pure Python Regression Suite

Run:

```bash
pytest -q \
  isaac-training/training/unit_test/test_env/test_dynamic_analyzer.py \
  isaac-training/training/unit_test/test_env/test_run_acceptance.py \
  isaac-training/training/unit_test/test_env/test_static_analyzer.py \
  isaac-training/training/unit_test/test_env/test_spec_ir.py
```

Expected result:

- dynamic analyzer tests pass
- run acceptance tests still pass
- static/spec IR compatibility is preserved

### 4.3 Real Shifted Baseline Generation

Generate new real shifted runs:

```bash
cd /home/mint/rl_dev/CRERL/isaac-training

conda run -n NavRL python training/scripts/run_baseline.py \
  baseline.name=random \
  baseline.num_episodes=1 \
  scene_family_backend.family=shifted \
  headless=True

conda run -n NavRL python training/scripts/run_baseline.py \
  baseline.name=conservative \
  baseline.num_episodes=1 \
  scene_family_backend.family=shifted \
  headless=True
```

Expected result:

- new accepted `shifted` baseline run directories appear under:
  - `isaac-training/training/logs/`

### 4.4 Real Matched-Pair Dynamic Analyses

Run:

```bash
python3 isaac-training/training/scripts/run_static_audit.py \
  --reports-root /tmp/crerl_phase5_round2_reports \
  --bundle-name static_audit_phase5_round2 \
  --output /tmp/crerl_phase5_round2_reports/static_report_copy.json

python3 isaac-training/training/scripts/run_dynamic_audit.py \
  --logs-root isaac-training/training/logs \
  --source baseline_random \
  --scenario-type nominal \
  --compare-source baseline_random \
  --compare-scenario-type shifted \
  --reports-root /tmp/crerl_phase5_round3_reports \
  --bundle-name dynamic_baseline_random_nominal_vs_shifted \
  --output /tmp/crerl_phase5_round3_reports/dynamic_baseline_random_nominal_vs_shifted_copy.json

python3 isaac-training/training/scripts/run_dynamic_audit.py \
  --logs-root isaac-training/training/logs \
  --source baseline_conservative \
  --scenario-type nominal \
  --compare-source baseline_conservative \
  --compare-scenario-type shifted \
  --reports-root /tmp/crerl_phase5_round3_reports \
  --bundle-name dynamic_baseline_conservative_nominal_vs_shifted \
  --output /tmp/crerl_phase5_round3_reports/dynamic_baseline_conservative_nominal_vs_shifted_copy.json

python3 isaac-training/training/scripts/run_dynamic_audit.py \
  --logs-root isaac-training/training/logs \
  --source eval \
  --scenario-type nominal \
  --compare-source eval \
  --compare-scenario-type shifted \
  --reports-root /tmp/crerl_phase5_round4_reports \
  --bundle-name dynamic_eval_nominal_vs_shifted \
  --static-bundle-dir /tmp/crerl_phase5_round2_reports/analysis/static/static_audit_phase5_round2 \
  --output /tmp/crerl_phase5_round4_reports/dynamic_eval_nominal_vs_shifted_copy.json

python3 isaac-training/training/scripts/run_dynamic_audit.py \
  --logs-root isaac-training/training/logs \
  --source train \
  --scenario-type nominal \
  --compare-source train \
  --compare-scenario-type shifted \
  --reports-root /tmp/crerl_phase5_round4_reports \
  --bundle-name dynamic_train_nominal_vs_shifted \
  --static-bundle-dir /tmp/crerl_phase5_round2_reports/analysis/static/static_audit_phase5_round2 \
  --output /tmp/crerl_phase5_round4_reports/dynamic_train_nominal_vs_shifted_copy.json
```

Expected result:

- all matched-pair dynamic analyses pass
- each report contains:
  - `evidence_objects`
  - `semantic_inputs`
- `semantic_inputs` carries:
  - `semantic_contract_type = phase6_dynamic_semantic_contract.v1`
  - `cross_validation_contract.contract_type = phase6_cross_validation_contract.v1`

### 4.5 Real Aggregate Baseline Nominal-vs-Shifted Analysis

Run:

```bash
python3 isaac-training/training/scripts/run_dynamic_audit.py \
  --logs-root isaac-training/training/logs \
  --source baseline_random \
  --source baseline_greedy \
  --source baseline_conservative \
  --scenario-type nominal \
  --compare-source baseline_random \
  --compare-source baseline_greedy \
  --compare-source baseline_conservative \
  --compare-scenario-type shifted \
  --reports-root /tmp/crerl_phase5_round3_reports \
  --bundle-name dynamic_baseline_all_nominal_vs_shifted_context \
  --static-bundle-dir /tmp/crerl_phase5_round2_reports/analysis/static/static_audit_phase5_round2 \
  --output /tmp/crerl_phase5_round3_reports/dynamic_baseline_all_nominal_vs_shifted_context_copy.json
```

Expected result:

- the aggregate report passes
- the aggregate report includes:
  - `dynamic_evidence.json`
  - `semantic_inputs.json`
- the aggregate report root contains:
  - `evidence_objects`
  - `semantic_inputs`
  - `static_context.bundle_name = static_audit_phase5_round2`

## 5. Validation Results

Validation run on 2026-03-26:

### 5.1 `py_compile`

Result:

- passed

### 5.2 Pure Python Regression Suite

Command:

```bash
pytest -q \
  isaac-training/training/unit_test/test_env/test_dynamic_analyzer.py \
  isaac-training/training/unit_test/test_env/test_run_acceptance.py \
  isaac-training/training/unit_test/test_env/test_static_analyzer.py \
  isaac-training/training/unit_test/test_env/test_spec_ir.py
```

Result:

- `29 passed`

### 5.3 Real Shifted Run Generation

Observed result:

- new real shifted accepted baseline runs were generated successfully:
  - `baseline_random_rollout_20260326_225913`
  - `baseline_conservative_rollout_20260326_225934`
- together with the earlier:
  - `baseline_greedy_rollout_20260326_223636`
- real shifted accepted non-baseline runs were also confirmed:
  - `eval_rollout_20260326_230927`
  - `train_rollout_20260326_230948`

### 5.4 Real Random Nominal-vs-Shifted Matched Pair

Observed result:

- `passed = true`
- `max_severity = warning`
- `num_findings = 3`
- witness scores:
  - `W_CR = 0.259951114654541`
  - `W_EC = 0.2666666666666667`
  - `W_ER = 0.14285714285714285`

### 5.5 Real Conservative Nominal-vs-Shifted Matched Pair

Observed result:

- `passed = true`
- `max_severity = warning`
- `num_findings = 3`
- witness scores:
  - `W_CR = 0.2543450991312663`
  - `W_EC = 0.2666666666666667`
  - `W_ER = 0.14285714285714285`

### 5.6 Real `eval` Nominal-vs-Shifted Matched Pair

Observed result:

- primary:
  - `eval_rollout_20260326_180829`
- comparison:
  - `eval_rollout_20260326_230927`
- `passed = true`
- `max_severity = warning`
- `num_findings = 3`
- witness scores:
  - `W_CR = 0.0`
  - `W_EC = 0.46666666666666673`
  - `W_ER = 0.14285714285714285`

### 5.7 Real `train` Nominal-vs-Shifted Matched Pair

Observed result:

- primary:
  - `train_rollout_20260326_180502`
  - `train_rollout_20260326_180849`
- comparison:
  - `train_rollout_20260326_230948`
- `passed = true`
- `max_severity = warning`
- `num_findings = 3`
- witness scores:
  - `W_CR = 0.257961908976237`
  - `W_EC = 0.2666666666666667`
  - `W_ER = 0.14341271254044488`

### 5.8 Real Aggregate Baseline Nominal-vs-Shifted Analysis

Observed result:

- primary run set contained all three accepted nominal baseline runs
- comparison run set contained all three accepted shifted baseline runs
- the namespaced bundle successfully wrote:
  - `dynamic_report.json`
  - `dynamic_evidence.json`
  - `semantic_inputs.json`
  - `summary.json`
  - `manifest.json`
- stdout summary reported:
  - `passed = true`
  - `max_severity = info`
  - `num_findings = 3`
  - witness scores:
    - `W_CR = 0.16531465973687137`
    - `W_EC = 0.2`
    - `W_ER = 0.14285714285714285`

### 5.9 Semantic Handoff Contract Check

Observed result on the new round-4 report:

- `semantic_inputs.semantic_contract_type = phase6_dynamic_semantic_contract.v1`
- `semantic_inputs.cross_validation_contract.contract_type = phase6_cross_validation_contract.v1`
- `semantic_inputs.attribution_candidates` is populated
- `semantic_inputs.failure_hotspots` is populated
- `evidence_objects` is populated
- `static_context.bundle_name = static_audit_phase5_round2`

## 6. Current Conclusion

Phase 5 now has a much stronger runtime-evidence layer:

- dynamic witness kernels are stronger than the original first-pass version
- real matched run pairs now exist for:
  - all three baseline sources
  - `eval`
  - `train`
- grouped failure summaries are promoted into stable evidence objects
- dynamic bundles now carry explicit semantic-diagnosis inputs
- the semantic handoff contract is explicit and machine-readable
- static and dynamic evidence can be tied together in the same namespaced bundle

This is a much better handoff point for Phase 6 than the earlier report-only
version.

## 7. Next Step

The next best move is to close Phase 5 and open Phase 6 by:

- stabilizing the inconsistency-attribution substrate into a clearer claim schema
- adding semantic cross-check consumers on top of `semantic_inputs.json`
- starting the Phase-6 semantic diagnosis loop on top of the now-stable dynamic evidence layer
