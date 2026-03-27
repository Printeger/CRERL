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
_Updated: `2026-03-27T15:04:11`_

- Scope: `/home/mint/rl_dev/CRERL`
- Branch: `main`
- Source: `staged diff`
- Impacted phases: `Phase 2, Phase 3, Phase 4, Phase 7, Phase 9`
- Diff stat: 8 files changed, 593 insertions(+), 63 deletions(-)

### Changed Files
- `M` [doc/dev_log/p9_dev_status.md](doc/dev_log/p9_dev_status.md) [Project Docs]
- `M` [isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml](isaac-training/training/cfg/spec_cfg/policy_spec_v0.yaml) [Specification Config]
- `M` [isaac-training/training/repair/comparison.py](isaac-training/training/repair/comparison.py) [isaac-training]
- `M` [isaac-training/training/repair/rerun_adapters.py](isaac-training/training/repair/rerun_adapters.py) [isaac-training]
- `M` [isaac-training/training/repair/validation_runner.py](isaac-training/training/repair/validation_runner.py) [isaac-training]
- `M` [isaac-training/training/runtime_logging/training_log_adapter.py](isaac-training/training/runtime_logging/training_log_adapter.py) [Runtime Logging]
- `M` [isaac-training/training/unit_test/test_env/test_validation_loop.py](isaac-training/training/unit_test/test_env/test_validation_loop.py) [Training Tests]
<!-- TRACEABILITY:END -->
