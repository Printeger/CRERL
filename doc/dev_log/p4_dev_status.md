# Phase 4 Development Log

Updated: 2026-03-26

## 1. This Iteration Goal

This iteration closes Phase 4 by finishing the last missing static-audit pieces:

- refine `scene-backend capability` checks with:
  - dynamic hazard semantics
  - shifted-distribution semantics
- unify the `static / dynamic` report namespace contract
- keep the static analyzer machine-readable, deterministic, and runnable without Isaac Sim

This is the final bridge from:

- "we have a useful static analyzer"

to:

- "we have a Phase-4-complete pre-training static audit layer with stable report contracts."

## 2. Implemented Results

### 2.1 Scene-Backend Capability Checks Refined

`isaac-training/training/analyzers/static_checks.py` now performs finer-grained backend capability checks.

The `check_scene_backend_capability(...)` logic now validates:

- unsupported template candidates
- dynamic backend expressibility
- dynamic motion-profile presence for enabled dynamic hazards
- supported dynamic motion types
- valid dynamic speed ranges
- perforation expressibility
- whether `shifted` is materially distinct from `nominal`

This means the check no longer only answers:

- "is the family name supported?"

It now also answers:

- "can the current backend express the dynamic hazard semantics and shifted-distribution semantics that the scene family claims to have?"

### 2.2 Dynamic Hazard Semantic Fixtures Added

The synthetic fixture pack under:

- `isaac-training/training/unit_test/test_env/fixtures/static_specs/`

was expanded with:

- `dynamic_hazard_profile_gap.yaml`
  - enables dynamic hazards but injects unsupported motion types and invalid speed ranges
- `shifted_distribution_gap.yaml`
  - makes `shifted` effectively collapse back toward `nominal`

These fixtures now give the static analyzer direct negative tests for the two main remaining environment/backend semantic gaps.

### 2.3 Unified Static/Dynamic Report Namespace Contract Added

A new shared contract module was added:

- `isaac-training/training/analyzers/report_contract.py`

It defines:

- report modes:
  - `static_audit`
  - `dynamic_analysis`
- default namespaces:
  - `analysis/static`
  - `analysis/dynamic`
- expected bundle artifact sets for each report mode

This lifts report layout rules out of the static CLI and turns them into a reusable analyzer-layer contract.

### 2.4 Spec IR Runtime Contract Expanded Again

`isaac-training/training/analyzers/spec_ir.py` now carries the shared report contract directly into the IR:

- `report_namespaces`
- `report_mode_artifacts`

`isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml` was also extended so runtime expectations now explicitly include:

- `static_audit_namespace`
- `static_audit_required_artifacts`
- `dynamic_analysis_namespace`
- `dynamic_analysis_required_artifacts`

This makes the policy/runtime spec aware of both current static artifacts and future dynamic analyzer artifacts.

### 2.5 Execution-Mode Alignment Now Covers Report Artifacts Too

`check_execution_mode_alignment(...)` now validates:

- reward component execution-mode alignment
- rollout log artifact requirements
- static audit namespace alignment
- dynamic analysis namespace alignment
- static audit artifact requirements
- dynamic analysis artifact requirements

So execution-mode alignment is now checked at three levels:

- reward component level
- runtime log artifact level
- analyzer report artifact / namespace level

### 2.6 Top-Level Reports Namespace Contract Is Now Emitted

The static audit runner now writes not only a bundle, but also a higher-level namespace contract:

- bundle:
  - `analysis/static/<bundle_name>/static_report.json`
  - `analysis/static/<bundle_name>/summary.json`
  - `analysis/static/<bundle_name>/manifest.json`
- namespace:
  - `analysis/static/namespace_manifest.json`
- top-level contract:
  - `analysis/report_namespace_contract.json`

This means later dynamic analyzers and report pipeline stages can join the same namespace tree instead of inventing a parallel layout.

### 2.7 Phase 4 Exit Criteria Are Now Satisfied

At this point, the project has:

- a deterministic machine-readable `SpecIR`
- deterministic static checks
- synthetic bad-spec validation coverage for:
  - `C-R` conflict
  - `E-C` undercoverage
  - runtime/schema mismatch
  - scene-family structural invalidity
  - backend capability mismatch
  - execution/report namespace mismatch
- a machine-readable static report
- a namespaced report contract
- a pure-Python execution path without Isaac Sim

This satisfies the intended Phase 4 exit condition.

## 3. Main Files Added or Changed

Code/config files:

- `isaac-training/training/analyzers/report_contract.py`
- `isaac-training/training/analyzers/spec_ir.py`
- `isaac-training/training/analyzers/static_checks.py`
- `isaac-training/training/analyzers/detector_runner.py`
- `isaac-training/training/analyzers/__init__.py`
- `isaac-training/training/envs/env_gen.py`
- `isaac-training/training/runtime_logging/acceptance.py`
- `isaac-training/training/scripts/run_static_audit.py`
- `isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml`
- `isaac-training/training/unit_test/test_env/test_spec_ir.py`
- `isaac-training/training/unit_test/test_env/test_static_analyzer.py`
- `isaac-training/training/unit_test/test_env/fixtures/static_specs/dynamic_hazard_profile_gap.yaml`
- `isaac-training/training/unit_test/test_env/fixtures/static_specs/shifted_distribution_gap.yaml`
- `isaac-training/training/unit_test/test_env/fixtures/static_specs/report_namespace_misalignment.yaml`
- `isaac-training/training/unit_test/test_env/fixtures/static_specs/scene_backend_capability_gap.yaml`

Documentation/state files:

- `doc/dev_log/phase_4.md`
- `Traceability.md`

## 4. How To Validate

### 4.1 Syntax Validation

Run:

```bash
python3 -m py_compile \
  isaac-training/training/runtime_logging/acceptance.py \
  isaac-training/training/analyzers/report_contract.py \
  isaac-training/training/analyzers/aggregation.py \
  isaac-training/training/analyzers/static_checks.py \
  isaac-training/training/analyzers/detector_runner.py \
  isaac-training/training/analyzers/spec_ir.py \
  isaac-training/training/analyzers/__init__.py \
  isaac-training/training/envs/env_gen.py \
  isaac-training/training/scripts/run_static_audit.py \
  isaac-training/training/unit_test/test_env/test_spec_ir.py \
  isaac-training/training/unit_test/test_env/test_static_analyzer.py
```

Expected result:

- no syntax error

### 4.2 Pure Python Unit Tests

Run:

```bash
pytest -q \
  isaac-training/training/unit_test/test_env/test_spec_ir.py \
  isaac-training/training/unit_test/test_env/test_static_analyzer.py
```

Expected result:

- tests pass without Isaac Sim
- dynamic-hazard fixtures fail for the correct reasons
- shifted-semantic fixtures fail for the correct reasons
- report namespace mismatch fixtures fail for the correct reasons

### 4.3 Phase-4 Closeout Smoke Test

Run from repo root:

```bash
python3 isaac-training/training/scripts/run_static_audit.py \
  --reports-root /tmp/crerl_reports_root_phase4 \
  --bundle-name static_audit_phase4_closeout \
  --output /tmp/crerl_reports_root_phase4/static_report_copy.json
```

Expected result:

- the static bundle is written under:
  - `/tmp/crerl_reports_root_phase4/analysis/static/static_audit_phase4_closeout/`
- the static namespace manifest is written:
  - `/tmp/crerl_reports_root_phase4/analysis/static/namespace_manifest.json`
- the top-level report namespace contract is written:
  - `/tmp/crerl_reports_root_phase4/analysis/report_namespace_contract.json`
- the current v0 bundle still passes with warning-level findings only

## 5. Validation Results

Validation run on 2026-03-26:

### 5.1 `py_compile`

Result:

- passed

### 5.2 Pure Python Tests

Command:

```bash
pytest -q \
  isaac-training/training/unit_test/test_env/test_spec_ir.py \
  isaac-training/training/unit_test/test_env/test_static_analyzer.py
```

Result:

- `16 passed`

### 5.3 Phase-4 Closeout Smoke Test

Observed result:

- `run_static_audit.py` completed successfully
- the namespaced static bundle was written successfully
- `analysis/static/namespace_manifest.json` was written successfully
- `analysis/report_namespace_contract.json` was written successfully
- stdout summary reported:
  - `passed = true`
  - `max_severity = warning`
  - `num_findings = 8`

## 6. Current Conclusion

Phase 4 can now be considered complete.

The repository now has a usable static pre-training audit layer that:

- reads a deterministic machine-readable spec bundle
- checks constraint/reward/environment consistency
- checks scene-family structure and backend expressivity
- checks runtime/report artifact contracts
- emits stable namespaced static audit artifacts
- rejects synthetic bad specs in a repeatable pure-Python workflow

This is a strong enough base to start rollout-based dynamic analysis in the next phase.

## 7. Next Step

The next best move is to start Phase 5:

- implement the first dynamic analyzer on top of:
  - CRE runtime logs
  - baseline rollouts
  - static audit bundles
- begin with rollout-level metrics such as:
  - success/collision gap
  - min-distance distributions
  - near-violation concentration
  - family-conditioned failure summaries

That will be the first stage where the project moves from:

- "the spec looks suspicious before training"

to:

- "the executed policies produce measurable witness evidence of inconsistency."
