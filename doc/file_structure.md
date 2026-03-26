# Training Folder Target Structure

This document defines the **official gradual target structure** for:

- `isaac-training/training/`

It does **not** attempt to redesign the whole repository.

It also explicitly preserves the current compatibility anchors:

- `cfg/`
- `scripts/`
- `unit_test/`

These three directories should remain valid during migration.

---

## 1. Scope

This document only governs the internal structure of:

- `isaac-training/training/`

It does not redefine:

- `doc/`
- repository root layout
- `third_party/`
- ROS packages
- deployment packages outside `isaac-training/training/`

Human-readable specifications remain under:

- `doc/specs/`

Machine-executable runtime configuration remains under:

- `isaac-training/training/cfg/`

---

## 2. Design Rules

The migration must follow these rules:

1. keep the current runnable entrypoints working;
2. keep Hydra config resolution working;
3. keep Isaac manual validation entrypoints working;
4. move logic out of oversized files gradually;
5. add new subpackages before removing old compatibility paths.

The current compatibility anchors are therefore:

- `cfg/`
- `scripts/`
- `unit_test/`

We keep them first, then thin them later.

---

## 3. Official Gradual Target Structure

```text
isaac-training/training/
├── README.md
│
├── cfg/                                  # compatibility config root, keep
│   ├── train.yaml
│   ├── eval.yaml
│   ├── ppo.yaml
│   ├── sim.yaml
│   ├── drone.yaml
│   ├── env_cfg/
│   │   ├── scene_cfg_base.yaml
│   │   ├── scene_cfg_nominal.yaml
│   │   ├── scene_cfg_boundary_critical.yaml
│   │   └── scene_cfg_shifted.yaml
│   └── detector_cfg/
│       ├── detector_thresholds.yaml
│       └── witness_weights.yaml
│
├── envs/
│   ├── env_gen.py                        # temporary facade / main scene entry
│   ├── cre_logging.py                    # temporary facade / main logging entry
│   ├── livox_mid360.py
│   ├── lidar_processor.py
│   ├── universal_generator.py            # legacy reference only
│   ├── primitives/                       # extracted from env_gen.py over time
│   │   ├── specs.py
│   │   ├── factories.py
│   │   ├── perforation.py
│   │   ├── motion.py
│   │   ├── templates.py
│   │   ├── validation.py
│   │   ├── serialization.py
│   │   ├── config_loader.py
│   │   └── scene_generator.py
│   └── runtime/                          # extracted from scripts/env.py over time
│       ├── indoor_uav_env.py
│       ├── observation_builder.py
│       ├── collision_checker.py
│       └── task_sampler.py
│
├── runtime_logging/
│   ├── schema.py
│   ├── logger.py
│   ├── episode_writer.py
│   └── training_log_adapter.py
│
├── execution/
│   ├── baseline_policies.py
│   ├── batch_rollout.py
│   ├── checkpoint_selector.py
│   └── monitor.py
│
├── analyzers/
│   ├── spec_ir.py
│   ├── static_checks.py
│   ├── dynamic_metrics.py
│   ├── llm_analyzer.py
│   ├── aggregation.py
│   └── detector_runner.py
│
├── repair/
│   ├── proposal_schema.py
│   ├── rule_based_repair.py
│   ├── llm_repair_proposer.py
│   ├── patch_executor.py
│   ├── repair_validator.py
│   └── acceptance.py
│
├── orchestrator/
│   ├── pipeline.py
│   ├── run_experiment.py
│   └── version_manager.py
│
├── scripts/                              # compatibility entrypoints, keep
│   ├── train.py
│   ├── eval.py
│   ├── env.py
│   ├── ppo.py
│   ├── utils.py
│   ├── command_generator.py
│   ├── universal_generator.py            # legacy compatibility shim
│   └── livox_mid360_integration.py       # legacy helper
│
├── unit_test/                            # compatibility test root, keep
│   ├── test_flight.py
│   ├── test_hover.py
│   ├── test_livox_mid360.py
│   ├── test_adversarial_gen.py
│   ├── test_env/
│   │   ├── test_primitives.py
│   │   ├── test_perforated_slab.py
│   │   ├── test_scene_generation.py
│   │   ├── test_serialization_and_motion.py
│   │   ├── test_cre_logging.py
│   │   ├── test_static_analyzer.py
│   │   ├── test_dynamic_analyzer.py
│   │   ├── test_report_aggregation.py
│   │   └── test_repair_validation.py
│   ├── outputs/
│   └── logs/                             # historical only, not mainline
│
├── logs/                                 # main runtime logs
├── reports/                              # detector and audit outputs
├── checkpoints/                          # selected/exported checkpoints
└── artifacts/                            # scenes, figures, exports, misc outputs
```

---

## 4. Directory Roles

### 4.1 `cfg/`

Purpose:

- active runtime configuration root
- Hydra-compatible config location
- scene family configuration source for execution

Rule:

- keep `cfg/` as-is
- do not rename it to `configs/` during current migration

Reason:

- existing entrypoints already depend on this path
- renaming adds churn without architectural benefit

---

### 4.2 `envs/`

Purpose:

- scene generation
- environment runtime logic
- sensor helpers

Short-term rule:

- keep `env_gen.py` and `cre_logging.py` as facade modules
- gradually extract logic into `envs/primitives/` and `envs/runtime/`

Long-term direction:

- `env_gen.py` becomes a thin scene backend entrypoint
- `scripts/env.py` stops owning low-level runtime helpers directly

---

### 4.3 `runtime_logging/`

Purpose:

- formal log schema
- episode/step writers
- adapters from training/runtime code

Short-term rule:

- new code should start landing here
- existing callers may still use `envs/cre_logging.py`

Migration direction:

- `envs/cre_logging.py` should gradually delegate to this package

---

### 4.4 `execution/`

Purpose:

- baseline policy execution
- batch rollout logic
- monitoring/checkpoint utilities not tied to PPO internals

Rule:

- keep PPO entrypoints under `scripts/` for now
- put newly added baseline and rollout orchestration here

---

### 4.5 `analyzers/`

Purpose:

- static checks
- dynamic witness computation
- LLM-based semantic diagnosis
- multi-source report aggregation

Rule:

- this is a new mainline package
- analyzer logic should not be buried inside training scripts

---

### 4.6 `repair/`

Purpose:

- repair proposal representation
- rule-based and LLM-based repair generation
- patch execution
- repair validation and acceptance

Rule:

- all repair-loop code should live here instead of being mixed into analyzers or scripts

---

### 4.7 `orchestrator/`

Purpose:

- top-level audit pipeline
- top-level repair cycle
- version and artifact coordination

Rule:

- orchestration code should call lower layers
- lower layers should not depend on orchestrator code

---

### 4.8 `scripts/`

Purpose:

- compatibility entrypoint layer

This directory stays for now because it already hosts:

- `train.py`
- `eval.py`
- `env.py`

Rule:

- keep these files callable
- reduce their internal ownership over time
- move reusable logic out, but preserve the entrypoint path

Long-term direction:

- `scripts/*.py` become thin wrappers

---

### 4.9 `unit_test/`

Purpose:

- compatibility test root
- manual validation harnesses
- environment and logging unit tests

Rule:

- keep the current directory name
- do not rename to `tests/` during the current migration stage

Reason:

- current tooling and habits already reference `unit_test/`
- the rename is low-value compared with stabilizing the CRE pipeline

---

### 4.10 Artifact directories

Main runtime outputs:

- `logs/`
- `reports/`
- `checkpoints/`
- `artifacts/`

Rules:

- `logs/` is the authoritative runtime log location
- `unit_test/logs/` is historical only
- scene JSON exports, figures, and auxiliary outputs may go under `artifacts/`

---

## 5. Migration Phases Inside `training/`

### Phase A: stabilize current mainline

Keep working:

- `cfg/`
- `envs/env_gen.py`
- `envs/cre_logging.py`
- `scripts/train.py`
- `scripts/eval.py`
- `scripts/env.py`
- `unit_test/test_flight.py`

Do not rename directories yet.

---

### Phase B: add new packages without breaking old paths

Add:

- `runtime_logging/`
- `execution/`
- `analyzers/`
- `repair/`
- `orchestrator/`
- `envs/primitives/`
- `envs/runtime/`

At this stage, old paths still work.

---

### Phase C: extract logic out of oversized files

From `envs/env_gen.py`, move out:

- primitive schema logic
- template generation
- validation
- serialization
- config loading

From `envs/cre_logging.py`, move out:

- schema
- episode writer
- training adapters

From `scripts/env.py`, move out:

- observation builder
- collision checking
- task sampling

---

### Phase D: thin-wrapper stage

Convert:

- `scripts/train.py`
- `scripts/eval.py`
- `scripts/env.py`

into thin wrappers around:

- `execution/`
- `envs/runtime/`
- `runtime_logging/`
- `orchestrator/`

---

### Phase E: optional cleanup

Only after the new mainline is stable:

- review whether `unit_test/` should be renamed
- review whether more legacy files can be removed
- review whether `env_gen.py` and `cre_logging.py` can become re-export shims only

---

## 6. Mainline vs Legacy

### Mainline

These are part of the target CRE mainline:

- `cfg/`
- `envs/env_gen.py`
- `envs/cre_logging.py`
- `envs/livox_mid360.py`
- `envs/lidar_processor.py`
- `scripts/train.py`
- `scripts/eval.py`
- `scripts/env.py`
- `unit_test/test_flight.py`
- `unit_test/test_env/`
- `runtime_logging/`
- `execution/`
- `analyzers/`
- `repair/`
- `orchestrator/`

### Legacy / compatibility only

These should not define the new backbone:

- `envs/universal_generator.py`
- `scripts/universal_generator.py`
- `scripts/livox_mid360_integration.py`
- `unit_test/test_arena_viz.py`
- `unit_test/test_universal_viz.py`

They may remain temporarily, but they are not the target architecture.

---

## 7. One-Sentence Rule

Inside `isaac-training/training/`, any restructure should directly help:

`scene families -> execution -> logs -> analyzers -> repair loop`

If it does not, postpone it.
