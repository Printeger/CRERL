# Phase 7 Development Status

Updated: 2026-03-27

## 1. This Iteration Goal

This iteration continues Phase 7 after the first working report generator.

The concrete goal of this step is to tighten three things without changing the
overall evidence-first architecture:

- tighten ranking and root-cause ordering rules
- stabilize `repair_handoff.json` into a clearer Phase 8-facing contract
- add synthetic merge fixtures for static-vs-semantic conflict cases

## 2. Implemented Results

### 2.1 First Report Merge Kernel Added

A new file was added:

- `isaac-training/training/analyzers/report_merge.py`

It introduces the first deterministic normalization and ranking layer for
Phase 7.

The merge kernel now:

- normalizes static findings into a shared report space
- normalizes dynamic witness findings into the same report space
- normalizes semantic claims into that same report space
- computes deterministic `rank_score`
- derives:
  - `root_cause_summary`
  - `semantic_claim_summary`
  - `witness_summary`
  - `repair_handoff`

This is the first point in the repository where all three analyzer outputs are
translated into one common ranking substrate.

### 2.2 First Unified Report Generator Added

A new file was added:

- `isaac-training/training/analyzers/report_generator.py`

It implements the first `Phase 7` bundle writer under:

- `analysis/report/<bundle_name>/`

The generator now writes:

- `report.json`
- `ranked_findings.json`
- `repair_handoff.json`
- `report_summary.md`
- `summary.json`
- `manifest.json`
- `namespace_manifest.json`

The report now exposes:

- input bundle references
- ranked findings across static / dynamic / semantic namespaces
- one root-cause summary
- witness summary
- semantic claim summary
- repair-ready claim handoff

### 2.3 Report Namespace Contract Was Extended

`isaac-training/training/analyzers/report_contract.py` was extended with the
new Phase 7 namespace:

- `report_generation`
- `analysis/report`

and the required artifact list for the report bundle.

The namespace manifest writer was also updated so the Phase 7 bundle correctly
records the main `report.json` path.

### 2.4 Policy Runtime Expectations Were Updated

`isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml` now includes the
report namespace expectation:

- `report_generation_namespace: analysis/report`
- `report_generation_required_artifacts`

This keeps the Phase 7 bundle contract aligned with the existing machine-readable
policy/runtime expectations.

### 2.5 CLI Entry Point Added

A new script was added:

- `isaac-training/training/scripts/run_report_audit.py`

It provides the first direct CLI entrypoint for Phase 7.

The CLI accepts:

- a static bundle dir
- a dynamic bundle dir
- a semantic bundle dir

and emits a namespaced report bundle plus an optional standalone `report.json`
copy.

### 2.6 Focused Unit Test Added

A new test file was added:

- `isaac-training/training/unit_test/test_env/test_report_generator.py`

The new tests cover:

- bundle generation and namespaced write-out
- repair-handoff generation
- CLI smoke execution

This means the first Phase 7 report path is no longer just a design in the
roadmap; it is now executable and regression-tested.

### 2.7 Traceability Phase Attribution Was Tightened Again

`tools/update_traceability.py` was refined so that Phase 7 report-generation
files are no longer lumped into broader analyzer/config buckets by default.

The phase detector now recognizes:

- `report_*.py`
- `run_report_audit.py`
- the Phase 7-facing update to `policy_spec_v0.yaml`

This keeps `Traceability.md` aligned with the actual active phase of this
implementation step.

### 2.8 Ranking and Root-Cause Ordering Were Tightened

`isaac-training/training/analyzers/report_merge.py` was extended so Phase 7 no
longer chooses the root cause purely from the highest individual ranked record.

The merge layer now adds:

- support-status-aware ranking
- evidence-count-aware ranking
- aggregate claim-type scores
- explicit `selection_mode`
- explicit `selection_reason`
- explicit cross-namespace `conflicts`

Most importantly, it now enforces a `static_blocker_override` path:

- if a high-severity static blocker exists,
- it can override weaker cross-namespace semantic alternatives

This makes Phase 7 behave more like the roadmap intends:

- static blockers first
- then cross-source aggregate evidence

### 2.9 `repair_handoff.json` Was Stabilized into a Phase-8-Facing Contract

`repair_handoff.json` is no longer just a flat list of selected claims.

It is now written as a structured bundle:

- `handoff_type = phase8_repair_handoff.v1`
- `claim_record_schema = phase7_repair_ready_claim.v1`
- `selection_policy = phase7_ranked_claim_selection.v2`
- `primary_claim_type`
- `primary_repair_direction`
- `impacted_components_union`
- `selected_claims`
- `required_evidence_contract`

Each selected claim now carries:

- `selected_from_rank`
- `required_evidence_refs`
- `selection_basis`

This gives Phase 8 a clearer and more stable handoff target.

### 2.10 Static-vs-Semantic Conflict Fixtures Were Added

Two synthetic report-level fixture bundles were added under:

- `isaac-training/training/unit_test/test_env/fixtures/report_cases/`

New cases:

- `static_semantic_conflict_case.json`
- `semantic_supported_over_static_warning_case.json`

These cases now exercise:

- a static blocker overriding a conflicting semantic supported claim
- a strong semantic supported claim overriding a weaker static warning

This gives Phase 7 much better regression protection around root-cause
selection and repair-handoff derivation.

## 3. Main Files Added or Changed

Code:

- `isaac-training/training/analyzers/report_merge.py`
- `isaac-training/training/analyzers/report_generator.py`
- `isaac-training/training/analyzers/report_contract.py`
- `isaac-training/training/analyzers/__init__.py`
- `isaac-training/training/scripts/run_report_audit.py`
- `isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml`
- `isaac-training/training/unit_test/test_env/test_report_generator.py`
- `isaac-training/training/unit_test/test_env/fixtures/report_cases/static_semantic_conflict_case.json`
- `isaac-training/training/unit_test/test_env/fixtures/report_cases/semantic_supported_over_static_warning_case.json`

Documentation / state:

- `doc/dev_log/p7_dev_status.md`
- `Traceability.md`

## 4. How To Validate

### 4.1 Syntax Validation

Run:

```bash
python3 -m py_compile \
  isaac-training/training/analyzers/report_contract.py \
  isaac-training/training/analyzers/report_merge.py \
  isaac-training/training/analyzers/report_generator.py \
  isaac-training/training/analyzers/__init__.py \
  isaac-training/training/scripts/run_report_audit.py \
  isaac-training/training/unit_test/test_env/test_report_generator.py
```

Expected result:

- no syntax error

### 4.2 Focused Unit Tests

Run:

```bash
pytest -q \
  isaac-training/training/unit_test/test_env/test_report_generator.py
```

Expected result:

- the new Phase 7 report tests pass
- the conflict-fixture root-cause tests pass

### 4.3 Real Bundle CLI Smoke Test

Run:

```bash
python3 isaac-training/training/scripts/run_report_audit.py \
  --static-bundle-dir /tmp/crerl_phase5_round2_reports/analysis/static/static_audit_phase5_round2 \
  --dynamic-bundle-dir /tmp/crerl_phase5_round4_reports/analysis/dynamic/dynamic_eval_nominal_vs_shifted \
  --semantic-bundle-dir /tmp/crerl_phase6_reports_round2/analysis/semantic/semantic_eval_nominal_vs_shifted_round2 \
  --reports-root /tmp/crerl_phase7_reports \
  --bundle-name report_eval_nominal_vs_shifted \
  --output /tmp/crerl_phase7_reports/report_copy.json
```

Expected result:

- a report bundle is written under:
  - `analysis/report/report_eval_nominal_vs_shifted/`
- the bundle contains:
  - `report.json`
  - `ranked_findings.json`
  - `repair_handoff.json`
  - `report_summary.md`
- CLI returns:
  - `primary_claim_type`
  - `repair_ready_claims`
  - `max_severity`

## 5. Validation Results

Validated in this iteration:

- `python3 -m py_compile ...` passed
- `pytest -q test_report_generator.py` passed:
  - `5 passed`
- the real bundle CLI smoke test passed

Observed smoke-test output:

- `passed = true`
- `max_severity = warning`
- `num_ranked_findings = 13`
- `primary_claim_type = C-R`
- `repair_ready_claims = 6`

The new synthetic fixture expectations also passed:

- static blocker vs semantic conflict:
  - `primary_claim_type = C-R`
  - `selection_mode = static_blocker_override`
- semantic supported vs static warning:
  - `primary_claim_type = E-R`
  - `primary_repair_direction = mixed`

This confirms the first Phase 7 report path can already merge real Phase 4-6
artifacts into one namespaced report bundle.

## 6. What Should Be Done Next

The next Phase 7 step should focus on report usability and Phase 8 handoff
quality:

- add more mixed-source conflict fixtures beyond static-vs-semantic
- improve ranked-finding explanations in `report_summary.md`
- tighten selection of repair-ready claims when multiple namespaces agree on
  the same claim type

After that, the repo should be ready to begin Phase 8 repair selection on top
of the unified report bundle rather than on top of three separate analyzer
outputs.
