# CRE System Architecture and Control Flow

## 1. Engineering Purpose

This project is **not** primarily a new RL algorithm project.

The engineering goal is to build a **CRE consistency auditing-and-repair system** for indoor UAV obstacle-avoidance RL.

Given a specification

\[
S = (C, R, E, P, L)
\]

where:
- `C`: constraint specification,
- `R`: reward specification,
- `E`: environment family specification,
- `P`: policy / training setup,
- `L`: runtime logs and trajectory evidence,

the system should:

1. construct analyzable environments and executions,
2. collect structured evidence before and during training,
3. detect likely inconsistency types:
   - `C-R`
   - `E-C`
   - `E-R`
4. produce a ranked inconsistency report,
5. propose minimal repairs to `C`, `R`, or `E`,
6. validate whether the repaired specification improves safety and deployment robustness.

## 2. Target Outcome

The desired end state is an engineering loop:

`spec -> generate scenes -> run policies -> collect logs -> analyze inconsistencies -> propose repair -> validate repair -> update spec`

This means the project should eventually support:

- **pre-training auditing** of reward / constraint / environment design,
- **runtime auditing** from trajectories and episode statistics,
- **LLM-assisted semantic diagnosis** for ambiguous conflicts,
- **repair recommendation and validation**,
- **repeatable benchmarks** for clean and injected-inconsistency specs.

The system is successful when we can hand it an indoor UAV RL specification and obtain:

- a reproducible environment/test suite,
- structured logs,
- quantitative inconsistency metrics,
- a human-readable report,
- a validated repair candidate.

## 3. Architectural Principles

1. **Spec-first, not code-first**
   - `C`, `R`, and `E` must be explicit objects, not hidden in scattered scripts.

2. **Environment is a first-class citizen**
   - The environment generator is part of the audited specification, not a background utility.

3. **Logs are mandatory infrastructure**
   - No detector should depend on ad hoc prints or implicit runtime behavior.

4. **LLM is a semantic reasoner, not the only judge**
   - Quantitative metrics must exist independently of the LLM.

5. **Repair must be validated**
   - A repair is not accepted because it looks reasonable; it is accepted because metrics and evaluation improve.

## 4. Canonical System Architecture

The system should be organized into **six layers**.

### Layer A. Specification Layer

Purpose:
- define the audited object precisely.

Artifacts:
- `SPEC-v0` task/constraint/reward definitions,
- environment primitive spec,
- scene generation rules,
- scene family configs,
- future reward/constraint config schemas.

Current files already in this layer:
- `doc/roadmap/phase0.md`
- `doc/specs/Env_Primitive_Spec_v0.md`
- `doc/specs/env_gen_rules.md`
- `isaac-training/training/cfg/env_cfg/scene_cfg_base.yaml`
- `isaac-training/training/cfg/env_cfg/scene_cfg_nominal.yaml`

### Layer B. Scenario and Runtime Substrate

Purpose:
- turn `E` into executable scenes and runtime test instances.

Responsibilities:
- compile scene-family rules into concrete scenes,
- validate geometry and start-goal feasibility,
- spawn scenes in Isaac Sim,
- support manual and scripted scene inspection.

Current mainline modules:
- `isaac-training/training/envs/env_gen.py`
- `isaac-training/training/unit_test/test_flight.py`

Legacy / exploratory module:
- `isaac-training/training/envs/universal_generator.py`

Decision:
- `env_gen.py` is the **mainline CRE scene backend**.
- `universal_generator.py` is retained as a **legacy prototype / idea bank**, not the primary architecture path.

### Layer C. Execution and Logging Layer

Purpose:
- produce analyzable evidence from policies running in the environment.

Responsibilities:
- step-level logs,
- episode-level summaries,
- trajectory export,
- scene metadata binding,
- run-level aggregate metrics.

Current modules:
- `isaac-training/training/envs/cre_logging.py`
- `isaac-training/training/logs/`
- `isaac-training/training/unit_test/test_flight.py`

Current gap:
- training-time logs are still only partially unified with the CRE log schema.

### Layer D. Policy Execution Layer

Purpose:
- produce behavior data under multiple policy sources.

This layer should support three execution modes:

1. **manual / scripted flight validation**
   - current implementation: `test_flight.py`

2. **non-RL baseline policies**
   - planned: random / greedy / conservative policies

3. **RL policies**
   - current baseline stack:
     - `isaac-training/training/scripts/env.py`
     - `isaac-training/training/scripts/train.py`
     - `isaac-training/training/scripts/ppo.py`

Important architectural decision:
- the RL training stack should eventually consume the same family-based scene specification as the scene generator path, rather than evolving as a separate environment logic island.

### Layer E. Analysis Layer

Purpose:
- convert raw spec + logs into inconsistency evidence.

This layer contains three analyzers:

1. **Static Analyzer**
   - reads `C/R/E` specs before training,
   - checks formal and rule-based issues,
   - outputs early warnings and blockers.

2. **Dynamic Analyzer**
   - reads trajectories and episode statistics,
   - computes quantitative metrics such as boundary-seeking, coverage, transfer gap,
   - outputs evidence-backed witness scores.

3. **LLM Analyzer**
   - reads the formal spec plus trajectory summaries/examples,
   - performs semantic diagnosis,
   - proposes likely root causes and candidate repairs.

Current status:
- this layer is conceptually defined in `CRE_frame_design.pdf`,
- but is **mostly not implemented yet**.

### Layer F. Report, Repair, and Validation Layer

Purpose:
- turn analyzer outputs into decisions.

Responsibilities:
- merge static/dynamic/LLM findings,
- produce ranked inconsistency reports,
- generate repair candidates,
- rerun validation on repaired specs,
- accept/reject repairs by quantitative criteria.

Current status:
- not yet implemented as a formal pipeline.

## 5. Reorganized Mapping of Existing Work

The current codebase already contains useful pieces, but they need to be reinterpreted under the above architecture.

### 5.1 What is already usable

#### Specification and environment generation
- primitive schema and validation in `env_gen.py`
- family config loading and scene compilation in `env_gen.py`
- nominal family scene config YAMLs

#### Runtime inspection and logging
- `test_flight.py` as scene visualization and manual validation harness
- `cre_logging.py` as step/episode/run logging backend

#### RL baseline stack
- `env.py` as current NavigationEnv
- `train.py` as baseline RL training entry
- `ppo.py` as current policy/training algorithm

#### Sensor/runtime utilities
- `livox_mid360.py`
- `lidar_processor.py`

#### Tests
- unit tests for scene generation, primitive validity, perforated slabs, dynamic motion, and logging

### 5.2 What should be demoted from “main flow”

These modules are not useless, but they should no longer define the canonical architecture:

- `universal_generator.py`
  - role after reorganization:
    - legacy prototype
    - geometric mode exploration
    - reference for future structured scene families

- ad hoc unit-test logs under `training/unit_test/logs`
  - role after reorganization:
    - historical artifacts only
    - mainline runtime logs belong in `training/logs`

### 5.3 What is still missing

1. unified spec IR for `C/R/E`
2. detector metrics implementation
3. witness computation pipeline
4. inconsistency report generator
5. repair engine
6. repair validation loop
7. training-stack integration with the scene-family backend

## 6. Canonical Control Flow

The project should now follow this control flow.

### Stage 0. Freeze the audited specification

Inputs:
- task definition,
- constraint set,
- reward definition,
- environment family config.

Outputs:
- explicit, versioned spec documents and config files.

### Stage 1. Compile the environment specification

Inputs:
- `scene_cfg_*.yaml`
- primitive rules

Process:
- compile family rules,
- sample valid start/goal,
- generate scene,
- validate geometry and traversability,
- export scene metadata.

Outputs:
- executable scene instance,
- scene validation report.

### Stage 2. Execute policies and collect evidence

Execution modes:
- manual flight test,
- non-RL baseline rollout,
- RL training/evaluation rollout.

Outputs:
- step logs,
- episode logs,
- run summary,
- scene-bound trajectory evidence.

### Stage 3. Run analysis

3.1 Static analysis
- inspect `C/R/E` before training.

3.2 Dynamic analysis
- compute metrics from rollouts and logs.

3.3 LLM semantic analysis
- interpret conflicts and missing cases semantically.

Outputs:
- issue candidates,
- confidence scores,
- witness metrics,
- supporting examples.

### Stage 4. Aggregate and report

Process:
- merge findings across analyzers,
- rank by severity and confidence,
- produce a structured inconsistency report.

Outputs:
- human-readable report,
- machine-readable report for downstream repair.

### Stage 5. Repair and validate

Process:
- generate candidate repairs,
- apply minimal changes to `C`, `R`, or `E`,
- rerun targeted evaluation,
- compare repaired vs original metrics.

Outputs:
- accepted / rejected repair,
- updated spec version,
- repair history.

## 7. Immediate Architecture Decisions

These should be treated as current project decisions unless replaced by a later document.

1. `env_gen.py` is the authoritative CRE scene backend.
2. `scene_cfg_*.yaml` is the authoritative environment-family input interface.
3. `cre_logging.py` is the authoritative runtime log schema.
4. `test_flight.py` is the main manual validation harness for scene/runtime inspection.
5. `env.py + train.py + ppo.py` remain the baseline RL execution stack, but should be gradually moved under the same spec-and-log pipeline.
6. `universal_generator.py` is legacy/exploratory, not the canonical system backbone.
7. LLM must be integrated as a semantic analyzer and repair suggester, but not as the sole source of inconsistency truth.

## 8. What “Done” Means Under the New Architecture

Under the new architecture, a subsystem is only considered complete when:

1. its input/output interface is explicit,
2. it is connected to the next layer in the canonical control flow,
3. it emits reproducible artifacts,
4. it is validated by tests or repeatable runs.

This means:
- a generator is not complete if it only visualizes scenes,
- a training environment is not complete if it cannot emit CRE logs,
- an analyzer is not complete if it cannot produce a machine-readable report,
- a repair is not complete if it is not quantitatively validated.

## 9. Authoritative Next Step

The immediate next step is **not** to keep adding isolated environment features.

The immediate next step is to build the missing central chain:

`spec -> logs -> analyzers -> report -> repair validation`

Environment, training, and visualization work should now be evaluated by one question:

**Does this change make the CRE audit-and-repair loop more complete and more reliable?**
