# Phase 5 Development Status

Updated: 2026-03-26

## 1. This Iteration Goal

This iteration continues Phase 5 by pushing the dynamic analyzer from
"working on accepted runs" toward "producing stable runtime evidence objects
for later semantic diagnosis."

The concrete goals were:

- add more real matched run pairs, not only one `baseline_greedy` nominal-vs-shifted pair
- stabilize grouped failure summaries into reusable dynamic evidence objects
- prepare explicit semantic-diagnosis inputs for Phase 6
- keep the analyzer grounded in real accepted run directories and namespaced
  report bundles

## 2. Implemented Results

### 2.1 Stronger Phase-5 Witness Kernels Are Preserved

`isaac-training/training/analyzers/dynamic_metrics.py` now remains on the
stronger Phase-5 witness definitions introduced previously:

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

### 2.4 Dynamic Bundles Now Carry Stable Phase-6 Input Artifacts

Dynamic analysis bundles now include:

- `dynamic_report.json`
- `dynamic_evidence.json`
- `semantic_inputs.json`
- `summary.json`
- `manifest.json`
- `namespace_manifest.json`

This was wired through:

- `isaac-training/training/analyzers/dynamic_analyzer.py`
- `isaac-training/training/analyzers/report_contract.py`
- `isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml`

So the dynamic namespace contract now explicitly includes the two new
semantic-handoff artifacts.

### 2.5 `run_acceptance_check(...)` Was Stabilized

`isaac-training/training/runtime_logging/acceptance.py` now re-validates after
writing `acceptance.json`.

That means newly generated runs can become accepted in one pass instead of
requiring an immediate second acceptance call. This makes real matched-run
generation much more stable.

### 2.6 More Real Matched Run Pairs Were Added

This iteration extended the repository’s real accepted nominal-vs-shifted
matched pairs from one to three baseline sources:

- `baseline_greedy`
- `baseline_random`
- `baseline_conservative`

New real shifted accepted runs:

- `baseline_greedy_rollout_20260326_223636`
- `baseline_random_rollout_20260326_225913`
- `baseline_conservative_rollout_20260326_225934`

These now pair with existing accepted nominal runs:

- `baseline_greedy_rollout_20260326_190209`
- `baseline_random_rollout_20260326_190148`
- `baseline_conservative_rollout_20260326_190217`

### 2.7 Real Nominal-vs-Shifted Aggregate Comparison Added

On top of the three individual matched pairs, an aggregate real comparison was
also validated over all three baseline sources together:

- nominal set:
  - `baseline_random`
  - `baseline_greedy`
  - `baseline_conservative`
- shifted set:
  - `baseline_random`
  - `baseline_greedy`
  - `baseline_conservative`

This gives the project a stronger real runtime contrast set than a single pair.

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
  --source baseline_greedy \
  --scenario-type nominal \
  --compare-source baseline_greedy \
  --compare-scenario-type shifted \
  --reports-root /tmp/crerl_phase5_round2_reports \
  --bundle-name dynamic_baseline_greedy_nominal_vs_shifted \
  --static-bundle-name static_audit_phase5_round2 \
  --output /tmp/crerl_phase5_round2_reports/dynamic_baseline_greedy_nominal_vs_shifted_copy.json

python3 isaac-training/training/scripts/run_dynamic_audit.py \
  --logs-root isaac-training/training/logs \
  --source baseline_random \
  --scenario-type nominal \
  --compare-source baseline_random \
  --compare-scenario-type shifted \
  --reports-root /tmp/crerl_phase5_round3_reports \
  --bundle-name dynamic_baseline_random_nominal_vs_shifted \
  --static-bundle-name static_audit_phase5_round2 \
  --output /tmp/crerl_phase5_round3_reports/dynamic_baseline_random_nominal_vs_shifted_copy.json

python3 isaac-training/training/scripts/run_dynamic_audit.py \
  --logs-root isaac-training/training/logs \
  --source baseline_conservative \
  --scenario-type nominal \
  --compare-source baseline_conservative \
  --compare-scenario-type shifted \
  --reports-root /tmp/crerl_phase5_round3_reports \
  --bundle-name dynamic_baseline_conservative_nominal_vs_shifted \
  --static-bundle-name static_audit_phase5_round2 \
  --output /tmp/crerl_phase5_round3_reports/dynamic_baseline_conservative_nominal_vs_shifted_copy.json
```

Expected result:

- all three matched-pair dynamic analyses pass
- each report contains:
  - `evidence_objects`
  - `semantic_inputs`

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

- new real shifted accepted runs were generated successfully:
  - `baseline_random_rollout_20260326_225913`
  - `baseline_conservative_rollout_20260326_225934`
- together with the earlier:
  - `baseline_greedy_rollout_20260326_223636`

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

### 5.6 Real Aggregate Baseline Nominal-vs-Shifted Analysis

Observed result:

- primary run set contained all three accepted nominal baseline runs
- comparison run set contained all three accepted shifted baseline runs
- the report root successfully carried:
  - `evidence_objects`
  - `semantic_inputs`
  - `static_context`
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

## 6. Current Conclusion

Phase 5 now has a stronger runtime-evidence layer:

- dynamic witness kernels are stronger than the original first-pass version
- real matched run pairs now exist for all three baseline sources
- grouped failure summaries are promoted into stable evidence objects
- dynamic bundles now carry explicit semantic-diagnosis inputs
- static and dynamic evidence can be tied together in the same namespaced bundle

This is a better handoff point for Phase 6 than the earlier report-only version.

## 7. Next Step

The next best move is to keep finishing Phase 5 by:

- adding matched run pairs beyond baselines, especially `eval` and `train`
- refining the evidence-object schema into a more explicit inconsistency
  attribution substrate
- defining the exact semantic prompt inputs and cross-check hooks that Phase 6
  will consume

That is the point where the project moves from:

- "the dynamic analyzer emits stronger machine-readable runtime evidence"

to:

- "the semantic analyzer can reason over stable, grounded dynamic evidence."
