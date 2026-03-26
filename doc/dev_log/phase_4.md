# Phase 4 Development Log

Updated: 2026-03-26

## 1. This Iteration Goal

This iteration continues Phase 4 with the next static-analyzer expansion batch:

- add another group of synthetic bad-spec fixtures
- add a `scene-backend capability` static check
- extend execution-mode alignment from reward components to:
  - runtime log artifact level
  - static report artifact / namespace level
- add a higher-level static audit report namespace so static audit artifacts can merge cleanly with later analysis/report pipeline stages

This batch is the bridge from:

- "we can emit a static audit bundle"

to:

- "we can validate whether the declared scene families are actually expressible by the current backend, and whether the execution/report artifact contract is internally aligned."

## 2. Implemented Results

### 2.1 Additional Synthetic Bad-Spec Fixtures Added

The fixture pack under:

- `isaac-training/training/unit_test/test_env/fixtures/static_specs/`

was expanded with:

- `scene_backend_capability_gap.yaml`
  - injects an unsupported template candidate into `scene_cfg_shifted.yaml`
- `report_namespace_misalignment.yaml`
  - changes `policy_spec_v0.runtime_expectations.static_audit_namespace`

These fixtures complement the existing ones and now cover:

- reward/constraint conflict
- missing runtime field binding
- scene-family undercoverage
- scene-family structural invalidity
- execution-mode misalignment
- scene-backend capability mismatch
- report namespace mismatch

### 2.2 Scene-Backend Capability Check Implemented

`isaac-training/training/analyzers/static_checks.py` now implements:

- `check_scene_backend_capability(...)`

Current behavior:

- compares declared scene families against the current `env_gen` backend support set
- checks template candidate types against the actual supported rule-template types
- checks whether dynamic-obstacle claims are expressible by the backend configuration path
- checks whether perforation requirements are expressible by the current family/backend combination

This is the first explicit static check that reasons about:

- what the spec claims the environment can do
- versus what the current generator/backend can actually express

### 2.3 Execution-Mode Alignment Expanded To Artifact Level

`check_execution_mode_alignment(...)` was extended beyond reward-component mode tagging.

It now also validates:

- supported execution modes declared in `policy_spec_v0.yaml`
- required rollout log artifacts for:
  - `manual`
  - `train`
  - `eval`
  - `baseline`
- required static audit namespace
- required static audit report artifacts

This turns execution-mode alignment into a stronger contract:

- reward components must align with execution paths
- runtime log artifacts must align with execution paths
- static audit report artifacts must align with the declared report namespace

### 2.4 Spec IR Runtime Contract Expanded

`isaac-training/training/analyzers/spec_ir.py` now carries a richer runtime/report contract:

- `execution_mode_artifacts`
- `report_mode_artifacts`
- `report_namespaces`

`policy_spec_v0.yaml` was also expanded so the machine-readable policy/runtime assumptions now include:

- `supported_execution_modes`
- `rollout_required_artifacts`
- `static_audit_namespace`
- `static_audit_required_artifacts`

This makes the static analyzer less dependent on hidden assumptions and more explicit about artifact contracts.

### 2.5 Static Audit Report Namespace Added

`isaac-training/training/analyzers/detector_runner.py` now supports a higher-level static audit namespace.

The current default namespace is:

- `analysis/static`

The static audit bundle path is now resolved under:

- `training/reports/analysis/static/<bundle_name>/`

and the namespace root now also gets:

- `namespace_manifest.json`

This creates a stable landing zone for:

- current static analyzer bundles
- future dynamic-analysis bundles
- later merged analysis/report orchestration

### 2.6 CLI Updated To Emit Namespaced Static Audit Bundles

`isaac-training/training/scripts/run_static_audit.py` now supports:

- `--reports-root`
- `--bundle-name`
- optional `--report-dir` override
- optional standalone `--output`

Current default behavior:

- writes the static audit bundle into the namespaced reports tree
- writes:
  - `static_report.json`
  - `summary.json`
  - `manifest.json`
  - `namespace_manifest.json`
- optionally writes an extra standalone copy of `static_report.json`

## 3. Main Files Added or Changed

Code/config files:

- `isaac-training/training/runtime_logging/acceptance.py`
- `isaac-training/training/analyzers/spec_ir.py`
- `isaac-training/training/analyzers/static_checks.py`
- `isaac-training/training/analyzers/detector_runner.py`
- `isaac-training/training/analyzers/__init__.py`
- `isaac-training/training/envs/env_gen.py`
- `isaac-training/training/scripts/run_static_audit.py`
- `isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml`
- `isaac-training/training/unit_test/test_env/test_spec_ir.py`
- `isaac-training/training/unit_test/test_env/test_static_analyzer.py`
- `isaac-training/training/unit_test/test_env/fixtures/static_specs/scene_backend_capability_gap.yaml`
- `isaac-training/training/unit_test/test_env/fixtures/static_specs/report_namespace_misalignment.yaml`

Documentation/state files:

- `doc/dev_log/phase_4.md`
- `Traceability.md`

## 4. How To Validate

### 4.1 Syntax Validation

Run:

```bash
python3 -m py_compile \
  isaac-training/training/runtime_logging/acceptance.py \
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
- synthetic bad-spec fixtures trigger the intended failures

### 4.3 Namespaced Static Audit Bundle Smoke Test

Run from repo root:

```bash
python3 isaac-training/training/scripts/run_static_audit.py \
  --reports-root /tmp/crerl_reports_root \
  --bundle-name static_audit_cli_check \
  --output /tmp/crerl_reports_root/static_report_copy.json
```

Expected result:

- the bundle directory exists at:
  - `/tmp/crerl_reports_root/analysis/static/static_audit_cli_check/`
- it contains:
  - `static_report.json`
  - `summary.json`
  - `manifest.json`
- the namespace root contains:
  - `namespace_manifest.json`
- the standalone copy is also written

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

- `14 passed`

### 5.3 Namespaced Static Audit Bundle Smoke Test

Observed result:

- `run_static_audit.py` completed successfully
- the namespaced bundle directory was written successfully
- `namespace_manifest.json` was written successfully
- stdout summary reported:
  - `passed = true`
  - `max_severity = warning`
  - `num_findings = 8`

## 6. Current Conclusion

The Phase 4 static analyzer now covers a meaningfully larger slice of the pre-training audit problem:

- it validates more of the scene-family config structure
- it validates backend expressivity against declared family claims
- it validates execution-mode alignment at both reward and artifact levels
- it emits namespaced static audit bundles that can be consumed by later pipeline stages

This is enough to support the next step:

- broadening static checks again where the gaps are still obvious
- then starting the first Phase 5 dynamic analyzer implementation on top of a cleaner static pre-filter

## 7. Next Step

The next best move is:

- add a dedicated scene-backend capability check for generator-feature parity beyond template names, especially dynamic hazards and shifted-distribution semantics
- add static checks that validate report/artifact contracts for later dynamic-analysis stages
- then start Phase 5 with the first rollout-based dynamic analyzer consuming the now-stable static and runtime evidence contract
