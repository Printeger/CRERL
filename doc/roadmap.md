# CRE Engineering Roadmap

This roadmap is the **integration roadmap** for the CRE project.

It reorganizes the current work around the architecture in
`doc/system_architecture_and _control_flow.md`.

Detailed draft notes such as `doc/roadmap/phase0.md` remain useful, but this file is the main execution order.

The file-level migration mapping is maintained in:
`doc/module_migration_checklist.md`.

## Phase 0. Freeze the audited object

### Goal
Turn the project from “a UAV RL codebase with ideas” into “a versioned CRE specification”.

### Deliverables
- freeze `SPEC-v0`
- freeze the environment primitive spec
- freeze scene generation rules
- define the versioned interfaces for:
  - `C`
  - `R`
  - `E`
  - logs
  - reports

### Use existing work
- `doc/roadmap/phase0.md`
- `doc/specs/Env_Primitive_Spec_v0.md`
- `doc/specs/env_gen_rules.md`
- `isaac-training/training/cfg/env_cfg/*.yaml`

### Exit criteria
- no ambiguity about task success/failure
- `C`, `R`, and `E` can all be mapped to code/config fields
- the scene-family input schema is considered stable enough for downstream integration

## Phase 1. Consolidate the environment substrate

### Goal
Make `env_gen.py` the authoritative scene backend for CRE.

### Deliverables
- finalize `nominal`, `boundary_critical`, and `shifted` family configs
- keep scene generation reproducible from seed
- ensure scene validation covers:
  - overlap
  - connectivity
  - start-goal validity
  - traversable template validity
- make `test_flight.py` the standard scene inspection harness

### Use existing work
- `isaac-training/training/envs/env_gen.py`
- `isaac-training/training/unit_test/test_flight.py`
- current unit tests under `isaac-training/training/unit_test/test_env/`

### Missing pieces
- add `scene_cfg_boundary_critical.yaml`
- add `scene_cfg_shifted.yaml`
- align scene family behavior more tightly with rules doc

### Exit criteria
- all three scene families generate valid scenes
- same seed gives same scene
- manual scene inspection runs through `test_flight.py`

## Phase 2. Unify runtime logging

### Goal
Make every executable path emit CRE-compatible evidence.

### Deliverables
- standardize step-level and episode-level logs
- ensure logs contain:
  - `scene_id`
  - `scenario_type`
  - position / velocity / yaw rate
  - goal distance
  - reward total / reward components
  - collision flag
  - minimum obstacle distance
  - near-violation flag
  - out-of-bounds flag
  - done type
- unify manual flight logs and training logs under one schema

### Use existing work
- `isaac-training/training/envs/cre_logging.py`
- `isaac-training/training/logs/`
- partial runtime fields already exposed in `env.py`

### Missing pieces
- make `env.py` and training loop emit the same CRE log structure as `test_flight.py`
- remove reliance on ad hoc unit-test logging outputs

### Exit criteria
- one episode can be exported as a full trajectory artifact
- run-level aggregates can compute:
  - success rate
  - collision rate
  - min distance
  - average return
  - near-violation ratio

## Phase 3. Build baseline execution modes

### Goal
Create stable evidence sources before full CRE diagnosis.

### Deliverables
- non-RL baseline policies:
  - random
  - greedy-to-goal
  - conservative avoider
- baseline rollout runner over the same scene-family backend
- baseline evaluation scripts using the unified log schema

### Use existing work
- `test_flight.py` for manual rollout structure
- current policy/runtime stack in `train.py`, `env.py`, and `ppo.py`

### Missing pieces
- formal non-RL policy runner
- batch evaluation entrypoint over scene families

### Exit criteria
- baseline policies produce distinguishable safety/performance tradeoffs
- logs clearly reflect those differences

## Phase 4. Implement the Static Analyzer

### Goal
Catch obvious design issues before training.

### Deliverables
- a spec IR for `C`, `R`, and `E`
- static checks for:
  - reward/constraint direct conflicts
  - missing/never-activated constraints
  - suspicious reward proxies
  - scene-family coverage mismatches
- machine-readable static report

### Use existing work
- phase 0 specs
- family configs
- scene validation rules in `env_gen.py`

### Missing pieces
- formal IR
- rule engine / pattern matcher
- report schema

### Exit criteria
- static analyzer can flag at least known synthetic spec issues before running RL

## Phase 5. Implement the Dynamic Analyzer

### Goal
Turn rollouts into quantitative CRE witness metrics.

### Deliverables
- compute dynamic metrics for:
  - `W_CR` / reward-violation coupling
  - `W_EC` / critical-state coverage
  - `W_ER` / transfer fragility under environment shift
- support:
  - exploratory rollouts
  - baseline-policy rollouts
  - RL-policy rollouts
- machine-readable dynamic report

### Use existing work
- unified logs
- environment families
- RL and non-RL execution paths

### Missing pieces
- actual witness implementations
- cross-environment comparison pipeline
- metric visualization utilities

### Exit criteria
- synthetic inconsistency cases produce the expected metric direction changes

## Phase 6. Add the LLM Semantic Analyzer

### Goal
Use the LLM where it is strongest: semantic diagnosis and repair suggestion.

### Deliverables
- natural-language rendering of `C`, `R`, `E`, and selected trajectory evidence
- structured LLM prompts for:
  - inconsistency diagnosis
  - missing edge-case identification
  - repair proposal
- cross-validation logic between LLM claims and static/dynamic evidence

### Important principle
- the LLM is **not** the sole detector
- the LLM augments static and dynamic evidence

### Exit criteria
- the system can produce semantically rich diagnoses that are grounded in measurable evidence

## Phase 7. Build the report generator

### Goal
Produce one unified inconsistency report per spec/run.

### Deliverables
- merge static, dynamic, and LLM findings
- severity ranking
- root-cause summary
- witness summary
- repair suggestions
- machine-readable and human-readable outputs

### Exit criteria
- a single report explains:
  - what is wrong
  - why it is classified as `C-R`, `E-C`, or `E-R`
  - what evidence supports that claim
  - what the minimal next repair should be

## Phase 8. Implement the repair engine

### Goal
Move from diagnosis to controlled repair proposals.

### Initial repair scope
- `C-R`:
  - reward reweighting
  - boundary-aware penalty injection
- `E-C`:
  - critical scenario injection
  - oversampling / curriculum rebalance
- `E-R`:
  - structured domain randomization
  - environment-family rebalance

### Deliverables
- repair candidate generator
- spec patch representation
- repair history tracking

### Exit criteria
- each repair can be represented as an explicit delta on `C`, `R`, or `E`

## Phase 9. Build the repair-validation loop

### Goal
Make repair acceptance evidence-based.

### Deliverables
- rerun pipeline for repaired specs
- compare original vs repaired metrics
- accept/reject rule using:
  - consistency improvement
  - safety improvement
  - bounded performance regression

### Example acceptance rule
- `ΔConsistency > 0`
- `ΔSafety > 0`
- `ΔPerformance >= -epsilon`

### Exit criteria
- the system can automatically say whether a proposed repair helped

## Phase 10. Unify the RL training stack with the CRE pipeline

### Goal
Stop treating training as a separate subsystem.

### Deliverables
- connect `env.py` to the same family-based scene specification path
- ensure training/evaluation emit unified CRE logs
- support clean spec vs repaired spec comparisons from the same training harness

### Use existing work
- `isaac-training/training/scripts/env.py`
- `isaac-training/training/scripts/train.py`
- `isaac-training/training/scripts/ppo.py`

### Exit criteria
- training, evaluation, logging, and CRE analysis form one continuous pipeline

## Phase 11. Create the benchmark and release CRE-v1

### Goal
Produce the first stable research/engineering version of the framework.

### Deliverables
- clean spec benchmark
- injected `C-R` inconsistent benchmark
- injected `E-C` inconsistent benchmark
- injected `E-R` inconsistent benchmark
- detector report examples
- repair-validation examples
- short system paper / technical report support artifacts

### Exit criteria
- the system can repeatedly demonstrate:
  - detection
  - attribution
  - repair proposal
  - repair validation

## Recommended immediate next sequence

If we optimize for momentum, the next concrete implementation order should be:

1. finish scene family configs (`boundary_critical`, `shifted`)
2. fully unify runtime logging across `test_flight.py` and `env.py`
3. add non-RL baseline runners
4. implement the static analyzer
5. implement the dynamic analyzer
6. add LLM semantic analysis
7. build report + repair + validation loop

## Current project status under this roadmap

### Already available
- versioned spec/config substrate for:
  - `C`
  - `R`
  - `E`
  - logs
  - reports
- authoritative scene-family backend with:
  - `nominal`
  - `boundary_critical`
  - `shifted`
- unified CRE runtime logging across:
  - manual flight
  - baseline
  - eval
  - train
- non-RL baseline execution modes
- static analyzer
- dynamic analyzer
- semantic analyzer with evidence-first contract and optional provider path
- unified report generator
- repair engine
- repair-validation loop
- native Phase 10 integration proof for:
  - `baseline`
  - `eval`
  - `train`
- Phase 11 benchmark bundle and release bundle packaging
- benchmark/release close-out evidence showing:
  - clean and injected benchmark cases are frozen
  - release path supports clean-vs-injected end-to-end demo packaging
  - default release flow does not require a live API key

### Partially available
- optional real-provider semantic demo path
- publishable paper / technical report polish
- release hardening beyond the current `CRE-v1` evidence-first packaging scope

### Not part of the current roadmap baseline
- mandatory cloud/provider dependency
- deployment hardware integration as a required release path
- brand-new witness paradigms beyond the current `C-R / E-C / E-R` stack

### Formal status
- `Phase 0` through `Phase 11` are now considered complete against the current roadmap definition
- the roadmap is therefore complete as written
- any next step should be treated as:
  - roadmap extension
  - release hardening
  - or post-`CRE-v1` iteration planning

## One-sentence project rule

From this point on, any new module should be justified by how it helps complete:

`spec -> execution -> logs -> analysis -> report -> repair -> validation`
