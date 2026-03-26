# Traceability

This file has two jobs:

1. keep a concrete roadmap-to-code traceability matrix for this repo;
2. record the latest staged change summary automatically before each commit.

## Scope Guardrails

- Scope is limited to the current git repository root only.
- The automation stages and commits only files already staged by the user, plus this file when the hook refreshes it.
- No repo-external files, global git hooks, or system-level configs are required.
- The recommended workflow uses a repo-local hook path and a repo-local helper script.

## Roadmap-To-Code Matrix

| Module | Roadmap Phase | Current Code / Docs | Recommendation |
| --- | --- | --- | --- |
| Problem freeze and spec definition | Phase 0 | [doc/roadmap/phase0.md](doc/roadmap/phase0.md), [doc/roadmap/roadmap.md](doc/roadmap/roadmap.md), [doc/CRE_frame_design.pdf](doc/CRE_frame_design.pdf) | `修改`: freeze task, constraints, reward formulas, thresholds, witness definitions, and repair acceptance rules. |
| Core Isaac navigation environment | Phase 1, 4, 7 | [isaac-training/training/scripts/env.py](isaac-training/training/scripts/env.py), [isaac-training/training/cfg/train.yaml](isaac-training/training/cfg/train.yaml) | `复用 + 修改`: keep the environment core, but expose scenario labels, reward decomposition, min obstacle distance, and explicit constraint logs. |
| Procedural scenario generation | Phase 1, 2, 3 | [isaac-training/training/envs/universal_generator.py](isaac-training/training/envs/universal_generator.py) | `复用 + 修改`: reuse difficulty/mode/solvability machinery to build nominal, boundary-critical, and shifted scenario families. |
| Sensor realism and sim2real noise | Phase 1, 3, 7 | [isaac-training/training/envs/livox_mid360.py](isaac-training/training/envs/livox_mid360.py), [isaac-training/training/unit_test/README.md](isaac-training/training/unit_test/README.md) | `复用 + 修改`: wire the Livox model into the main env and make noise/randomization ranges configurable for E-R studies. |
| UAV platform model | Phase 0, 7 | [isaac-training/training/cfg/drone.yaml](isaac-training/training/cfg/drone.yaml), [isaac-training/third_party/OmniDrones/omni_drones/robots/drone/taslab_uav.py](isaac-training/third_party/OmniDrones/omni_drones/robots/drone/taslab_uav.py), [doc/TASLAB_UAV_README.md](doc/TASLAB_UAV_README.md) | `复用 + 修改`: keep the TASLAB airframe assets, then finish env integration and validate sensor mounting and dynamics assumptions. |
| Non-RL baselines and adversarial probes | Phase 2, 3 | [isaac-training/training/scripts/command_generator.py](isaac-training/training/scripts/command_generator.py), [isaac-training/training/unit_test/test_adversarial_gen.py](isaac-training/training/unit_test/test_adversarial_gen.py) | `复用 + 新写`: reuse the adversarial command generator, but add explicit random / greedy-to-goal / conservative-avoidance baseline policies and evaluation harnesses. |
| RL training and evaluation loop | Phase 4 | [isaac-training/training/scripts/train.py](isaac-training/training/scripts/train.py), [isaac-training/training/scripts/eval.py](isaac-training/training/scripts/eval.py), [isaac-training/training/scripts/ppo.py](isaac-training/training/scripts/ppo.py) | `复用 + 修改`: reuse PPO training infrastructure first, then add constrained metrics and possibly a safe-RL baseline. |
| CRE diagnostics and witness computation | Phase 2, 3, 6 | No implementation yet; only design/spec in [doc/roadmap/phase0.md](doc/roadmap/phase0.md) and [doc/CRE_frame_design.pdf](doc/CRE_frame_design.pdf) | `新写`: build IR/spec objects, witness calculators (`W_CR`, `W_EC`, `W_ER`), scoring, and report generation. |
| Repair engine | Phase 5, 6 | No implementation yet; repair ideas only in [doc/roadmap/roadmap.md](doc/roadmap/roadmap.md) and [doc/CRE_frame_design.pdf](doc/CRE_frame_design.pdf) | `新写`: implement reward reweighting, boundary penalty injection, critical scenario injection, and structured domain randomization. |
| Deployment validation stack | Phase 7 | [ros1/map_manager](ros1/map_manager), [ros1/onboard_detector](ros1/onboard_detector), [ros2/navigation_runner/scripts/navigation.py](ros2/navigation_runner/scripts/navigation.py) | `复用 + 修改`: reuse the deployment chain for repaired-policy validation and deployment-gap measurements. |
| LLM / IR orchestration | Design ambition beyond Phase 5 | Mentioned in [doc/CRE_frame_design.pdf](doc/CRE_frame_design.pdf) only | `新写`: if needed later, add IR adapters, LLM analyzers, and repair proposal orchestration after the numeric detector is stable. |

## Recommended Build Order

1. Freeze `SPEC-v0` so every reward, constraint, and threshold maps to a code variable.
2. Upgrade the env logs so Phase 1 data is exportable without retraining architecture changes.
3. Build baseline policies and four injected specs for Phase 2-3.
4. Implement witness calculators and a small CRE report generator.
5. Add repair operators and evaluate them on the injected benchmark.
6. Only then connect an LLM layer if it still adds leverage.

## Repo-Local Vibe Coding Workflow

1. Stage only the files you want included in the next commit.
2. Run `tools/vibe-sync.sh "your commit message"`.
3. The repo-local pre-commit hook refreshes the auto summary below.
4. The helper script commits the staged files plus refreshed `Traceability.md`.
5. The helper script pushes the current branch to `origin`.

This keeps the workflow inside the current repo and avoids touching files outside the package.

## Latest Staged Change Summary

<!-- TRACEABILITY:BEGIN -->
_Updated: `2026-03-26T15:45:01`_

- Scope: `/home/mint/rl_dev/CRERL`
- Branch: `main`
- Source: `staged diff`
- Impacted phases: `Phase 0, Phase 1, Phase 4, Phase 7`
- Diff stat: 70 files changed, 7394 insertions(+), 246 deletions(-)

### Changed Files
- `A` [doc/CRE_frame_design.pdf](doc/CRE_frame_design.pdf) [Project Docs]
- `A` [doc/TASLAB_UAV_README.md](doc/TASLAB_UAV_README.md) [Project Docs]
- `A` [doc/file_structure.md](doc/file_structure.md) [Project Docs]
- `A` [doc/module_migration_checklist.md](doc/module_migration_checklist.md) [Project Docs]
- `A` [doc/roadmap.md](doc/roadmap.md) [Project Docs]
- `A` [doc/roadmap/phase0.md](doc/roadmap/phase0.md) [Spec / Roadmap]
- `A` [doc/roadmap/roadmap.md](doc/roadmap/roadmap.md) [Spec / Roadmap]
- `A` [doc/specs/Env_Primitive_Spec_v0.md](doc/specs/Env_Primitive_Spec_v0.md) [Project Docs]
- `A` [doc/specs/env_gen_rules.md](doc/specs/env_gen_rules.md) [Project Docs]
- `A` [doc/system_architecture_and _control_flow.md](doc/system_architecture_and _control_flow.md) [Project Docs]
- `A` [isaac-training/training/README.md](isaac-training/training/README.md) [isaac-training]
- `A` [isaac-training/training/analyzers/__init__.py](isaac-training/training/analyzers/__init__.py) [isaac-training]
- `A` [isaac-training/training/analyzers/aggregation.py](isaac-training/training/analyzers/aggregation.py) [isaac-training]
- `A` [isaac-training/training/analyzers/detector_runner.py](isaac-training/training/analyzers/detector_runner.py) [isaac-training]
- `A` [isaac-training/training/analyzers/dynamic_metrics.py](isaac-training/training/analyzers/dynamic_metrics.py) [isaac-training]
- `A` [isaac-training/training/analyzers/llm_analyzer.py](isaac-training/training/analyzers/llm_analyzer.py) [isaac-training]
- `A` [isaac-training/training/analyzers/spec_ir.py](isaac-training/training/analyzers/spec_ir.py) [isaac-training]
- `A` [isaac-training/training/analyzers/static_checks.py](isaac-training/training/analyzers/static_checks.py) [isaac-training]
- `A` [isaac-training/training/artifacts/.gitkeep](isaac-training/training/artifacts/.gitkeep) [isaac-training]
- `A` [isaac-training/training/cfg/detector_cfg/detector_thresholds.yaml](isaac-training/training/cfg/detector_cfg/detector_thresholds.yaml) [Training Config]
- `A` [isaac-training/training/cfg/detector_cfg/witness_weights.yaml](isaac-training/training/cfg/detector_cfg/witness_weights.yaml) [Training Config]
- `A` [isaac-training/training/cfg/env_cfg/scene_cfg_base.yaml](isaac-training/training/cfg/env_cfg/scene_cfg_base.yaml) [Training Config]
- `A` [isaac-training/training/cfg/env_cfg/scene_cfg_boundary_critical.yaml](isaac-training/training/cfg/env_cfg/scene_cfg_boundary_critical.yaml) [Training Config]
- `A` [isaac-training/training/cfg/env_cfg/scene_cfg_nominal.yaml](isaac-training/training/cfg/env_cfg/scene_cfg_nominal.yaml) [Training Config]
- `A` [isaac-training/training/cfg/env_cfg/scene_cfg_shifted.yaml](isaac-training/training/cfg/env_cfg/scene_cfg_shifted.yaml) [Training Config]
- `A` [isaac-training/training/checkpoints/.gitkeep](isaac-training/training/checkpoints/.gitkeep) [isaac-training]
- `A` [isaac-training/training/envs/__init__.py](isaac-training/training/envs/__init__.py) [Procedural Env / Sensors]
- `M` [isaac-training/training/envs/env_gen.py](isaac-training/training/envs/env_gen.py) [Procedural Env / Sensors]
- `A` [isaac-training/training/envs/primitives/__init__.py](isaac-training/training/envs/primitives/__init__.py) [Procedural Env / Sensors]
- `A` [isaac-training/training/envs/primitives/config_loader.py](isaac-training/training/envs/primitives/config_loader.py) [Procedural Env / Sensors]
- `A` [isaac-training/training/envs/primitives/factories.py](isaac-training/training/envs/primitives/factories.py) [Procedural Env / Sensors]
- `A` [isaac-training/training/envs/primitives/motion.py](isaac-training/training/envs/primitives/motion.py) [Procedural Env / Sensors]
- `A` [isaac-training/training/envs/primitives/perforation.py](isaac-training/training/envs/primitives/perforation.py) [Procedural Env / Sensors]
- `A` [isaac-training/training/envs/primitives/scene_generator.py](isaac-training/training/envs/primitives/scene_generator.py) [Procedural Env / Sensors]
- `A` [isaac-training/training/envs/primitives/serialization.py](isaac-training/training/envs/primitives/serialization.py) [Procedural Env / Sensors]
- `A` [isaac-training/training/envs/primitives/specs.py](isaac-training/training/envs/primitives/specs.py) [Procedural Env / Sensors]
- `A` [isaac-training/training/envs/primitives/templates.py](isaac-training/training/envs/primitives/templates.py) [Procedural Env / Sensors]
- `A` [isaac-training/training/envs/primitives/validation.py](isaac-training/training/envs/primitives/validation.py) [Procedural Env / Sensors]
- `A` [isaac-training/training/envs/runtime/__init__.py](isaac-training/training/envs/runtime/__init__.py) [Procedural Env / Sensors]
- `A` [isaac-training/training/envs/runtime/collision_checker.py](isaac-training/training/envs/runtime/collision_checker.py) [Procedural Env / Sensors]
- `A` [isaac-training/training/envs/runtime/indoor_uav_env.py](isaac-training/training/envs/runtime/indoor_uav_env.py) [Procedural Env / Sensors]
- `A` [isaac-training/training/envs/runtime/observation_builder.py](isaac-training/training/envs/runtime/observation_builder.py) [Procedural Env / Sensors]
- `A` [isaac-training/training/envs/runtime/task_sampler.py](isaac-training/training/envs/runtime/task_sampler.py) [Procedural Env / Sensors]
- `A` [isaac-training/training/execution/__init__.py](isaac-training/training/execution/__init__.py) [isaac-training]
- `A` [isaac-training/training/execution/baseline_policies.py](isaac-training/training/execution/baseline_policies.py) [isaac-training]
- `A` [isaac-training/training/execution/batch_rollout.py](isaac-training/training/execution/batch_rollout.py) [isaac-training]
- `A` [isaac-training/training/execution/checkpoint_selector.py](isaac-training/training/execution/checkpoint_selector.py) [isaac-training]
- `A` [isaac-training/training/execution/monitor.py](isaac-training/training/execution/monitor.py) [isaac-training]
- `A` [isaac-training/training/orchestrator/__init__.py](isaac-training/training/orchestrator/__init__.py) [isaac-training]
- `A` [isaac-training/training/orchestrator/pipeline.py](isaac-training/training/orchestrator/pipeline.py) [isaac-training]
- `A` [isaac-training/training/orchestrator/run_experiment.py](isaac-training/training/orchestrator/run_experiment.py) [isaac-training]
- `A` [isaac-training/training/orchestrator/version_manager.py](isaac-training/training/orchestrator/version_manager.py) [isaac-training]
- `A` [isaac-training/training/repair/__init__.py](isaac-training/training/repair/__init__.py) [isaac-training]
- `A` [isaac-training/training/repair/acceptance.py](isaac-training/training/repair/acceptance.py) [isaac-training]
- `A` [isaac-training/training/repair/llm_repair_proposer.py](isaac-training/training/repair/llm_repair_proposer.py) [isaac-training]
- `A` [isaac-training/training/repair/patch_executor.py](isaac-training/training/repair/patch_executor.py) [isaac-training]
- `A` [isaac-training/training/repair/proposal_schema.py](isaac-training/training/repair/proposal_schema.py) [isaac-training]
- `A` [isaac-training/training/repair/repair_validator.py](isaac-training/training/repair/repair_validator.py) [isaac-training]
- `A` [isaac-training/training/repair/rule_based_repair.py](isaac-training/training/repair/rule_based_repair.py) [isaac-training]
- `A` [isaac-training/training/reports/.gitkeep](isaac-training/training/reports/.gitkeep) [isaac-training]
- `A` [isaac-training/training/runtime_logging/__init__.py](isaac-training/training/runtime_logging/__init__.py) [isaac-training]
- `A` [isaac-training/training/runtime_logging/episode_writer.py](isaac-training/training/runtime_logging/episode_writer.py) [isaac-training]
- `A` [isaac-training/training/runtime_logging/logger.py](isaac-training/training/runtime_logging/logger.py) [isaac-training]
- `A` [isaac-training/training/runtime_logging/schema.py](isaac-training/training/runtime_logging/schema.py) [isaac-training]
- `A` [isaac-training/training/runtime_logging/training_log_adapter.py](isaac-training/training/runtime_logging/training_log_adapter.py) [isaac-training]
- `M` [isaac-training/training/unit_test/test_env/test_primitives.py](isaac-training/training/unit_test/test_env/test_primitives.py) [Training Tests]
- `M` [isaac-training/training/unit_test/test_env/test_scene_generation.py](isaac-training/training/unit_test/test_env/test_scene_generation.py) [Training Tests]
- `M` [isaac-training/training/unit_test/test_env/test_serialization_and_motion.py](isaac-training/training/unit_test/test_env/test_serialization_and_motion.py) [Training Tests]
- `M` [isaac-training/training/unit_test/test_flight.py](isaac-training/training/unit_test/test_flight.py) [Training Tests]
<!-- TRACEABILITY:END -->
