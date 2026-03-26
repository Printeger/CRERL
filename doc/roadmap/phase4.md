# Phase 4: Static Analyzer and Pre-Training Spec Audit

## 1. Purpose

Phase 4 is the stage where the project moves from:

- "we can generate scenes and collect consistent runtime evidence"

to:

- "we can catch obvious design problems in `C/R/E` before spending time on training."

The immediate goal is to implement the first **non-LLM static analyzer** for the
CRE stack.

This analyzer should operate before RL training and before dynamic witness
computation. It is meant to detect specification-level issues that are visible
from:

- the frozen task/constraint/reward definitions,
- scene-family configs,
- detector thresholds,
- scene-generation rules,
- and known runtime/logging requirements.

This phase corresponds to:

- [doc/roadmap.md](../roadmap.md) `Phase 4. Implement the Static Analyzer`
- [doc/system_architecture_and _control_flow.md](../system_architecture_and%20_control_flow.md) `Layer E. Analysis Layer`
- [doc/CRE_frame_design.pdf](../CRE_frame_design.pdf) static consistency analysis before repair

---

## 2. Why Phase 4 Starts Here

Phases 1-3 already established:

- a family-based scene backend,
- unified CRE runtime logs,
- acceptance-gated execution paths,
- comparable baseline evidence sources.

What is still missing is a training-time question:

`is the audited specification already suspicious before we run policies at all?`

This is exactly the role of the static analyzer.

The static analyzer should not try to solve the full CRE problem. Its first job
is narrower and more useful:

1. normalize `C/R/E` into one machine-readable IR;
2. run deterministic rule-based checks;
3. emit a machine-readable static report;
4. fail early on known synthetic inconsistencies.

That gives later dynamic analysis a cleaner foundation and reduces wasted RL
cycles on clearly broken specs.

---

## 3. Scope of Phase 4

Phase 4 should implement **static pre-training auditing only**.

In scope:

- build a versioned `SpecIR` for `C`, `R`, and `E`
- implement deterministic static checks
- emit machine-readable static findings
- support synthetic inconsistent spec fixtures for validation

Out of scope:

- trajectory-based witness metrics
- LLM semantic reasoning
- repair proposal generation
- final multi-source report aggregation

Those belong to later phases.

---

## 4. Input Artifacts the Static Analyzer Must Read

The analyzer should treat the following as the authoritative inputs for `v0`:

### 4.1 Spec and Rules Documents

- `doc/roadmap/phase0.md`
- `doc/specs/Env_Primitive_Spec_v0.md`
- `doc/specs/env_gen_rules.md`

These remain the human-readable source of truth.

### 4.2 Executable Scene Family Configs

- `isaac-training/training/cfg/env_cfg/scene_cfg_base.yaml`
- `isaac-training/training/cfg/env_cfg/scene_cfg_nominal.yaml`
- `isaac-training/training/cfg/env_cfg/scene_cfg_boundary_critical.yaml`
- `isaac-training/training/cfg/env_cfg/scene_cfg_shifted.yaml`

These are the executable environment-spec layer.

### 4.3 Detector and Runtime Thresholds

- `isaac-training/training/cfg/detector_cfg/detector_thresholds.yaml`
- `isaac-training/training/cfg/detector_cfg/witness_weights.yaml`

These provide the currently active numeric thresholds and transitional detector semantics.

### 4.4 Runtime Environment Facts

- `isaac-training/training/scripts/env.py`
- `isaac-training/training/envs/env_gen.py`
- `isaac-training/training/envs/cre_logging.py`

These are needed so static checks can answer questions like:

- is a declared constraint actually represented in runtime fields?
- does a reward component named in spec correspond to a real logged component?
- do scene-family declarations correspond to generator capabilities?

---

## 5. First Architectural Decision: Add a Transitional Machine-Readable Spec Mirror

The current repository has strong human-readable documentation, but not yet a
fully executable spec package for `C` and `R`.

So Phase 4 should introduce a transitional machine-readable mirror of the v0
spec instead of trying to parse Markdown directly.

Recommended new config files:

- `isaac-training/training/cfg/spec_cfg/constraint_spec_v0.yaml`
- `isaac-training/training/cfg/spec_cfg/reward_spec_v0.yaml`
- `isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml`

Why this is the right compromise:

- Phase 0 documents stay the reviewable source of truth
- the analyzer gets stable structured inputs
- later phases can version and patch these configs without scraping prose

The static analyzer should therefore read:

- `doc/*` for reference and traceability
- `cfg/spec_cfg/*` plus `cfg/env_cfg/*` for actual machine execution

---

## 6. Deliverables

Phase 4 should produce the following deliverables.

### 6.1 Spec IR

A normalized `SpecIR` object containing at least:

- `spec_version`
- `constraint_spec`
- `reward_spec`
- `environment_spec`
- `policy_spec`
- `runtime_schema_expectations`

### 6.2 Static Checks

The first version of the static analyzer should support at least these check classes:

1. reward/constraint direct conflicts
2. missing or unbound constraints
3. suspicious reward proxies
4. scene-family coverage mismatches
5. scene/runtime schema mismatches

### 6.3 Static Report

A machine-readable static report, for example:

- `static_report.json`

with:

- overall status
- finding list
- severity
- evidence
- affected spec paths
- recommended next action

### 6.4 Test Fixtures

Synthetic spec fixtures that intentionally encode:

- one `C-R` inconsistent case
- one `E-C` under-coverage case
- one environment/runtime binding mismatch

These fixtures will be the first acceptance gate for the analyzer.

---

## 7. File-Level Implementation Plan

### 7.1 Spec IR

#### File: `isaac-training/training/analyzers/spec_ir.py`

Current state:

- placeholder only

What to implement:

- dataclasses for:
  - `ConstraintSpec`
  - `RewardComponentSpec`
  - `RewardSpec`
  - `EnvironmentFamilySpec`
  - `PolicySpec`
  - `RuntimeSchemaSpec`
  - `SpecIR`
- loader functions such as:
  - `load_spec_ir(...)`
  - `load_constraint_spec(...)`
  - `load_reward_spec(...)`
  - `load_environment_spec(...)`
- normalization rules so scene-family configs and detector thresholds land in a stable IR

Important design decision:

- `SpecIR` should be purely structural and deterministic
- it should not contain finding logic

### 7.2 Static Rules

#### File: `isaac-training/training/analyzers/static_checks.py`

Current state:

- placeholder only

What to implement:

- `StaticCheckResult`
- `run_static_checks(spec_ir)`
- separate check helpers for:
  - `check_constraint_runtime_binding(...)`
  - `check_reward_constraint_conflicts(...)`
  - `check_reward_proxy_suspicion(...)`
  - `check_scene_family_coverage(...)`
  - `check_required_runtime_fields(...)`

Each check should emit:

- `check_id`
- `passed`
- `severity`
- `summary`
- `details`
- `affected_paths`
- `recommended_action`

### 7.3 Static Detector Entry Point

#### File: `isaac-training/training/analyzers/detector_runner.py`

Current state:

- placeholder only

What to implement:

- a stable entrypoint for Phase 4, for example:
  - `run_static_analysis(...)`
- load `SpecIR`
- run static checks
- compute a small summary
- emit a machine-readable report structure

This file should be the phase-level integration point, not the home of check logic.

### 7.4 Report Schema

#### File: `isaac-training/training/analyzers/aggregation.py`

Current state:

- placeholder only

Phase 4 requirement:

- do not implement full multi-source aggregation yet
- but do define a report container usable by the static analyzer

Recommended minimum:

- `StaticAnalyzerReport`
- `FindingRecord`
- report summary fields:
  - `spec_version`
  - `scene_family_set`
  - `num_findings`
  - `max_severity`
  - `passed`

### 7.5 Transitional Spec Configs

#### New directory: `isaac-training/training/cfg/spec_cfg/`

Files to add:

- `constraint_spec_v0.yaml`
- `reward_spec_v0.yaml`
- `policy_spec_v0.yaml`

These files should mirror the current Phase 0 definitions closely enough to support deterministic checks.

Recommended contents:

- constraint names, thresholds, runtime/logging field names, severity
- reward component names, sign, intended effect, expected logged key
- policy assumptions relevant to static analysis

### 7.6 CLI or Script Entry

#### New file: `isaac-training/training/scripts/run_static_audit.py`

Purpose:

- run the static analyzer from the command line
- accept a spec/config bundle
- emit `static_report.json`

Recommended behavior:

- no Isaac simulation required
- no training required
- should run in a plain Python environment

### 7.7 Tests

#### New file: `isaac-training/training/unit_test/test_env/test_static_analyzer.py`

Should test at least:

- loading `SpecIR`
- successful report generation on nominal v0 spec
- detection of a synthetic direct reward/constraint conflict
- detection of a missing runtime binding
- detection of an under-covered scene-family declaration

#### Optional helper fixtures

Suggested fixture location:

- `isaac-training/training/unit_test/test_env/fixtures/static_specs/`

Suggested fixtures:

- `nominal_clean.yaml`
- `reward_constraint_conflict.yaml`
- `missing_constraint_binding.yaml`
- `scene_family_undercoverage.yaml`

---

## 8. The First Static Checks To Implement

The analyzer should start with checks that are both useful and realistically
derivable from the current codebase.

### 8.1 Constraint Runtime Binding Check

Question:

`Does every declared constraint map to an actual runtime field or threshold?`

Examples:

- if a constraint declares `logged_variable = min_obstacle_distance`, does the runtime log schema provide it?
- if a constraint declares `out_of_bounds_flag`, is that field actually emitted by the environment/logging path?

Failure class:

- missing runtime binding

### 8.2 Reward/Constraint Direct Conflict Check

Question:

`Does the reward structure explicitly incentivize behavior that pushes toward a declared forbidden region?`

Examples:

- progress reward present but no meaningful safety penalty near obstacle boundary
- high speed encouragement combined with strict speed bound and no balancing term

This first version can be heuristic and rule-based rather than formally optimal.

Failure class:

- likely `C-R` inconsistency

### 8.3 Suspicious Reward Proxy Check

Question:

`Is a reward component acting as a proxy that may not actually represent the intended task objective?`

Examples:

- strong progress shaping without success bonus
- constant per-step positive reward that could reward lingering
- proxy term present without corresponding task-completion emphasis

Failure class:

- suspicious reward proxy

### 8.4 Scene-Family Coverage Check

Question:

`Do the declared scene families actually cover the critical situation types referenced by constraints or deployment assumptions?`

Examples:

- dynamic-obstacle-related constraints exist, but a family config disables dynamic obstacles everywhere
- shifted-family expectations are declared but the shifted config is missing or too similar to nominal

Failure class:

- likely `E-C` under-coverage

### 8.5 Scene Backend Capability Check

Question:

`Can the current scene backend express what the spec claims exists?`

Examples:

- spec requires perforated traversable bottlenecks, but scene generator config never includes them
- spec says family uses dynamic hazards, but backend request path does not enable dynamic primitives

Failure class:

- environment-spec mismatch

---

## 9. Recommended Implementation Order

1. Add `cfg/spec_cfg/` transitional machine-readable spec files.
2. Implement `SpecIR` loading and normalization in `spec_ir.py`.
3. Implement the first three static checks:
   - constraint runtime binding
   - reward/constraint conflict
   - suspicious reward proxy
4. Add scene-family coverage and backend capability checks.
5. Implement `run_static_audit.py`.
6. Add synthetic fixtures and `test_static_analyzer.py`.
7. Only after the static analyzer is stable, start Phase 5 dynamic metrics.

---

## 10. Validation Strategy

Phase 4 should be validated in two ways.

### 10.1 Clean Spec Validation

Run the static analyzer on the current nominal v0 spec bundle.

Expected result:

- report is generated successfully
- no critical blocker is emitted for the known-good baseline spec

### 10.2 Synthetic Bad Spec Validation

Run the static analyzer on intentionally inconsistent fixtures.

Expected result:

- the intended finding is detected
- the finding severity is stable
- the report points to the correct affected spec path or rule

This is the most important validation for Phase 4.

---

## 11. Exit Criteria

Phase 4 is complete when:

- `SpecIR` can be built deterministically from the v0 spec/config bundle
- the static analyzer emits a machine-readable report
- the analyzer can flag at least one known synthetic `C-R` issue
- the analyzer can flag at least one known synthetic `E-C` issue
- the analyzer can flag at least one runtime-binding/schema mismatch
- the analyzer can run without Isaac Sim or training

---

## 12. Non-Goals for This Phase

Phase 4 does **not** need to:

- compute dynamic witness metrics
- compare rollout distributions
- use the LLM
- propose repairs
- merge findings into the final unified inconsistency report

Those belong to later phases.

---

## 13. What Comes Immediately After Phase 4

Once the static analyzer is stable, the next step is:

- Phase 5 dynamic analysis over accepted CRE run directories

At that point the project will have:

- pre-training static evidence
- runtime dynamic evidence
- a clean handoff point for later LLM diagnosis and repair.
