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
| Core Isaac navigation environment | Phase 1, 2, 4, 7, 10 | [isaac-training/training/scripts/env.py](isaac-training/training/scripts/env.py), [isaac-training/training/cfg/train.yaml](isaac-training/training/cfg/train.yaml), [isaac-training/training/cfg/eval.yaml](isaac-training/training/cfg/eval.yaml) | `复用 + 修改`: keep the environment core, but expose scenario labels, reward decomposition, min obstacle distance, target position, GUI goal markers, explicit constraint logs, and env-local reset/boundary behavior for vectorized train/eval parity. |
| Procedural scenario generation | Phase 1, 2, 3, 10 | [isaac-training/training/envs/env_gen.py](isaac-training/training/envs/env_gen.py), [isaac-training/training/envs/runtime/scene_family_bridge.py](isaac-training/training/envs/runtime/scene_family_bridge.py), [isaac-training/training/cfg/env_cfg/scene_cfg_nominal.yaml](isaac-training/training/cfg/env_cfg/scene_cfg_nominal.yaml) | `复用 + 修改`: keep `env_gen.py` as the main family backend, tune family YAMLs directly, make training consume the same bounded scene-family contract, and keep nominal edge-fill placement controls config-driven. |
| Sensor realism and sim2real noise | Phase 1, 3, 7 | [isaac-training/training/envs/livox_mid360.py](isaac-training/training/envs/livox_mid360.py), [isaac-training/training/unit_test/README.md](isaac-training/training/unit_test/README.md) | `复用 + 修改`: wire the Livox model into the main env and make noise/randomization ranges configurable for E-R studies. |
| UAV platform model | Phase 0, 7 | [isaac-training/training/cfg/drone.yaml](isaac-training/training/cfg/drone.yaml), [isaac-training/third_party/OmniDrones/omni_drones/robots/drone/taslab_uav.py](isaac-training/third_party/OmniDrones/omni_drones/robots/drone/taslab_uav.py), [doc/TASLAB_UAV_README.md](doc/TASLAB_UAV_README.md) | `复用 + 修改`: keep the TASLAB airframe assets, then finish env integration and validate sensor mounting and dynamics assumptions. |
| Non-RL baselines and adversarial probes | Phase 2, 3 | [isaac-training/training/scripts/command_generator.py](isaac-training/training/scripts/command_generator.py), [isaac-training/training/unit_test/test_adversarial_gen.py](isaac-training/training/unit_test/test_adversarial_gen.py) | `复用 + 新写`: reuse the adversarial command generator, but add explicit random / greedy-to-goal / conservative-avoidance baseline policies and evaluation harnesses. |
| RL training and evaluation loop | Phase 4, 10 | [isaac-training/training/scripts/train.py](isaac-training/training/scripts/train.py), [isaac-training/training/scripts/eval.py](isaac-training/training/scripts/eval.py), [isaac-training/training/scripts/ppo.py](isaac-training/training/scripts/ppo.py), [isaac-training/training/runtime_logging/training_log_adapter.py](isaac-training/training/runtime_logging/training_log_adapter.py) | `复用 + 修改`: reuse PPO training infrastructure first, then add constrained metrics, keep train/eval scene-family defaults aligned, normalize rollout batch layouts for CRE logging, and make `eval.py` run one direct checkpoint evaluation instead of repeatedly nesting eval inside a collector loop. |
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
_Updated: `2026-04-15T18:00:00`_

- Scope: `/home/mint/rl_dev/crerl_v1`
- Branch: `main`
- Source: `staged diff`
- Impacted phases: `Phase 11`
- Diff stat: 137 files changed, 65762 insertions(+)

### Changed Files
- `M` [cre-demos/demo1_cr_boundary_lure/README.md](cre-demos/demo1_cr_boundary_lure/README.md) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/assets/screenshots/demo1_metric_board.svg](cre-demos/demo1_cr_boundary_lure/assets/screenshots/demo1_metric_board.svg) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/assets/screenshots/demo1_scene_topdown.svg](cre-demos/demo1_cr_boundary_lure/assets/screenshots/demo1_scene_topdown.svg) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/assets/screenshots/demo1_trajectory_overlay.svg](cre-demos/demo1_cr_boundary_lure/assets/screenshots/demo1_trajectory_overlay.svg) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/assets/videos/demo1_replay.html](cre-demos/demo1_cr_boundary_lure/assets/videos/demo1_replay.html) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/cfg/detector_cfg/detector_thresholds.yaml](cre-demos/demo1_cr_boundary_lure/cfg/detector_cfg/detector_thresholds.yaml) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/cfg/detector_cfg/witness_weights.yaml](cre-demos/demo1_cr_boundary_lure/cfg/detector_cfg/witness_weights.yaml) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/cfg/env_cfg/scene_cfg_base.yaml](cre-demos/demo1_cr_boundary_lure/cfg/env_cfg/scene_cfg_base.yaml) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/cfg/env_cfg/scene_cfg_nominal.yaml](cre-demos/demo1_cr_boundary_lure/cfg/env_cfg/scene_cfg_nominal.yaml) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/cfg/scene_layout.yaml](cre-demos/demo1_cr_boundary_lure/cfg/scene_layout.yaml) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/cfg/spec_clean/constraint_spec_v0.yaml](cre-demos/demo1_cr_boundary_lure/cfg/spec_clean/constraint_spec_v0.yaml) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/cfg/spec_clean/policy_spec_v0.yaml](cre-demos/demo1_cr_boundary_lure/cfg/spec_clean/policy_spec_v0.yaml) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/cfg/spec_clean/reward_spec_v0.yaml](cre-demos/demo1_cr_boundary_lure/cfg/spec_clean/reward_spec_v0.yaml) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/cfg/spec_injected/constraint_spec_v0.yaml](cre-demos/demo1_cr_boundary_lure/cfg/spec_injected/constraint_spec_v0.yaml) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/cfg/spec_injected/policy_spec_v0.yaml](cre-demos/demo1_cr_boundary_lure/cfg/spec_injected/policy_spec_v0.yaml) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/cfg/spec_injected/reward_spec_v0.yaml](cre-demos/demo1_cr_boundary_lure/cfg/spec_injected/reward_spec_v0.yaml) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/cfg/spec_repaired/constraint_spec_v0.yaml](cre-demos/demo1_cr_boundary_lure/cfg/spec_repaired/constraint_spec_v0.yaml) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/cfg/spec_repaired/policy_spec_v0.yaml](cre-demos/demo1_cr_boundary_lure/cfg/spec_repaired/policy_spec_v0.yaml) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/cfg/spec_repaired/reward_spec_v0.yaml](cre-demos/demo1_cr_boundary_lure/cfg/spec_repaired/reward_spec_v0.yaml) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/analysis/report_namespace_contract.json](cre-demos/demo1_cr_boundary_lure/reports/latest/analysis/report_namespace_contract.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/analysis/validation/demo1_validation/comparison.json](cre-demos/demo1_cr_boundary_lure/reports/latest/analysis/validation/demo1_validation/comparison.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/analysis/validation/demo1_validation/manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/analysis/validation/demo1_validation/manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/analysis/validation/demo1_validation/post_repair_evidence.json](cre-demos/demo1_cr_boundary_lure/reports/latest/analysis/validation/demo1_validation/post_repair_evidence.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/analysis/validation/demo1_validation/validation_decision.json](cre-demos/demo1_cr_boundary_lure/reports/latest/analysis/validation/demo1_validation/validation_decision.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/analysis/validation/demo1_validation/validation_plan.json](cre-demos/demo1_cr_boundary_lure/reports/latest/analysis/validation/demo1_validation/validation_plan.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/analysis/validation/demo1_validation/validation_runs.json](cre-demos/demo1_cr_boundary_lure/reports/latest/analysis/validation/demo1_validation/validation_runs.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/analysis/validation/demo1_validation/validation_summary.json](cre-demos/demo1_cr_boundary_lure/reports/latest/analysis/validation/demo1_validation/validation_summary.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/analysis/validation/demo1_validation/validation_summary.md](cre-demos/demo1_cr_boundary_lure/reports/latest/analysis/validation/demo1_validation/validation_summary.md) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/analysis/validation/namespace_manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/analysis/validation/namespace_manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/analysis/dynamic/demo1_clean_dynamic/dynamic_evidence.json](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/analysis/dynamic/demo1_clean_dynamic/dynamic_evidence.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/analysis/dynamic/demo1_clean_dynamic/dynamic_report.json](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/analysis/dynamic/demo1_clean_dynamic/dynamic_report.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/analysis/dynamic/demo1_clean_dynamic/manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/analysis/dynamic/demo1_clean_dynamic/manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/analysis/dynamic/demo1_clean_dynamic/semantic_inputs.json](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/analysis/dynamic/demo1_clean_dynamic/semantic_inputs.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/analysis/dynamic/demo1_clean_dynamic/summary.json](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/analysis/dynamic/demo1_clean_dynamic/summary.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/analysis/dynamic/namespace_manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/analysis/dynamic/namespace_manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/analysis/report_namespace_contract.json](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/analysis/report_namespace_contract.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/analysis/static/demo1_clean_static/manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/analysis/static/demo1_clean_static/manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/analysis/static/demo1_clean_static/static_report.json](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/analysis/static/demo1_clean_static/static_report.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/analysis/static/demo1_clean_static/summary.json](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/analysis/static/demo1_clean_static/summary.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/analysis/static/namespace_manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/analysis/static/namespace_manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/logs/demo1_clean/acceptance.json](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/logs/demo1_clean/acceptance.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/logs/demo1_clean/episodes.jsonl](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/logs/demo1_clean/episodes.jsonl) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/logs/demo1_clean/episodes/episode_0000.json](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/logs/demo1_clean/episodes/episode_0000.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/logs/demo1_clean/episodes/episode_0001.json](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/logs/demo1_clean/episodes/episode_0001.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/logs/demo1_clean/episodes/episode_0002.json](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/logs/demo1_clean/episodes/episode_0002.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/logs/demo1_clean/episodes/episode_0003.json](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/logs/demo1_clean/episodes/episode_0003.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/logs/demo1_clean/episodes/episode_0004.json](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/logs/demo1_clean/episodes/episode_0004.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/logs/demo1_clean/episodes/episode_0005.json](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/logs/demo1_clean/episodes/episode_0005.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/logs/demo1_clean/manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/logs/demo1_clean/manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/logs/demo1_clean/steps.jsonl](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/logs/demo1_clean/steps.jsonl) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/logs/demo1_clean/summary.json](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/logs/demo1_clean/summary.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/route_summary.json](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/route_summary.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/clean/trajectory_records.json](cre-demos/demo1_cr_boundary_lure/reports/latest/clean/trajectory_records.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/dynamic/demo1_injected_dynamic/dynamic_evidence.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/dynamic/demo1_injected_dynamic/dynamic_evidence.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/dynamic/demo1_injected_dynamic/dynamic_report.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/dynamic/demo1_injected_dynamic/dynamic_report.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/dynamic/demo1_injected_dynamic/manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/dynamic/demo1_injected_dynamic/manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/dynamic/demo1_injected_dynamic/semantic_inputs.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/dynamic/demo1_injected_dynamic/semantic_inputs.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/dynamic/demo1_injected_dynamic/summary.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/dynamic/demo1_injected_dynamic/summary.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/dynamic/namespace_manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/dynamic/namespace_manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/demo1_injected_repair/acceptance.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/demo1_injected_repair/acceptance.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/demo1_injected_repair/manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/demo1_injected_repair/manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/demo1_injected_repair/repair_candidates.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/demo1_injected_repair/repair_candidates.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/demo1_injected_repair/repair_plan.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/demo1_injected_repair/repair_plan.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/demo1_injected_repair/repair_summary.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/demo1_injected_repair/repair_summary.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/demo1_injected_repair/repair_summary.md](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/demo1_injected_repair/repair_summary.md) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/demo1_injected_repair/repair_validation.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/demo1_injected_repair/repair_validation.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/demo1_injected_repair/spec_patch.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/demo1_injected_repair/spec_patch.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/demo1_injected_repair/spec_patch_preview.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/demo1_injected_repair/spec_patch_preview.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/demo1_injected_repair/validation_context_preview.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/demo1_injected_repair/validation_context_preview.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/demo1_injected_repair/validation_request.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/demo1_injected_repair/validation_request.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/namespace_manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/repair/namespace_manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/report/demo1_injected_report/manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/report/demo1_injected_report/manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/report/demo1_injected_report/ranked_findings.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/report/demo1_injected_report/ranked_findings.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/report/demo1_injected_report/repair_handoff.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/report/demo1_injected_report/repair_handoff.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/report/demo1_injected_report/report.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/report/demo1_injected_report/report.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/report/demo1_injected_report/report_summary.md](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/report/demo1_injected_report/report_summary.md) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/report/demo1_injected_report/summary.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/report/demo1_injected_report/summary.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/report/namespace_manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/report/namespace_manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/report_namespace_contract.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/report_namespace_contract.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/semantic/demo1_injected_semantic/claim_consumer.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/semantic/demo1_injected_semantic/claim_consumer.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/semantic/demo1_injected_semantic/manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/semantic/demo1_injected_semantic/manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/semantic/demo1_injected_semantic/semantic_claims.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/semantic/demo1_injected_semantic/semantic_claims.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/semantic/demo1_injected_semantic/semantic_input.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/semantic/demo1_injected_semantic/semantic_input.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/semantic/demo1_injected_semantic/semantic_merge_input.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/semantic/demo1_injected_semantic/semantic_merge_input.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/semantic/demo1_injected_semantic/semantic_report.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/semantic/demo1_injected_semantic/semantic_report.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/semantic/demo1_injected_semantic/semantic_summary.md](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/semantic/demo1_injected_semantic/semantic_summary.md) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/semantic/demo1_injected_semantic/summary.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/semantic/demo1_injected_semantic/summary.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/semantic/namespace_manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/semantic/namespace_manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/static/demo1_injected_static/manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/static/demo1_injected_static/manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/static/demo1_injected_static/static_report.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/static/demo1_injected_static/static_report.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/static/demo1_injected_static/summary.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/static/demo1_injected_static/summary.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/static/namespace_manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/analysis/static/namespace_manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/logs/demo1_injected/acceptance.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/logs/demo1_injected/acceptance.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/logs/demo1_injected/episodes.jsonl](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/logs/demo1_injected/episodes.jsonl) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/logs/demo1_injected/episodes/episode_0000.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/logs/demo1_injected/episodes/episode_0000.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/logs/demo1_injected/episodes/episode_0001.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/logs/demo1_injected/episodes/episode_0001.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/logs/demo1_injected/episodes/episode_0002.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/logs/demo1_injected/episodes/episode_0002.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/logs/demo1_injected/episodes/episode_0003.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/logs/demo1_injected/episodes/episode_0003.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/logs/demo1_injected/episodes/episode_0004.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/logs/demo1_injected/episodes/episode_0004.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/logs/demo1_injected/episodes/episode_0005.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/logs/demo1_injected/episodes/episode_0005.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/logs/demo1_injected/manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/logs/demo1_injected/manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/logs/demo1_injected/steps.jsonl](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/logs/demo1_injected/steps.jsonl) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/logs/demo1_injected/summary.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/logs/demo1_injected/summary.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/route_summary.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/route_summary.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/injected/trajectory_records.json](cre-demos/demo1_cr_boundary_lure/reports/latest/injected/trajectory_records.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/analysis/dynamic/demo1_repaired_dynamic/dynamic_evidence.json](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/analysis/dynamic/demo1_repaired_dynamic/dynamic_evidence.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/analysis/dynamic/demo1_repaired_dynamic/dynamic_report.json](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/analysis/dynamic/demo1_repaired_dynamic/dynamic_report.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/analysis/dynamic/demo1_repaired_dynamic/manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/analysis/dynamic/demo1_repaired_dynamic/manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/analysis/dynamic/demo1_repaired_dynamic/semantic_inputs.json](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/analysis/dynamic/demo1_repaired_dynamic/semantic_inputs.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/analysis/dynamic/demo1_repaired_dynamic/summary.json](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/analysis/dynamic/demo1_repaired_dynamic/summary.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/analysis/dynamic/namespace_manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/analysis/dynamic/namespace_manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/analysis/report_namespace_contract.json](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/analysis/report_namespace_contract.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/analysis/static/demo1_repaired_static/manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/analysis/static/demo1_repaired_static/manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/analysis/static/demo1_repaired_static/static_report.json](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/analysis/static/demo1_repaired_static/static_report.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/analysis/static/demo1_repaired_static/summary.json](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/analysis/static/demo1_repaired_static/summary.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/analysis/static/namespace_manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/analysis/static/namespace_manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/logs/demo1_repaired/acceptance.json](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/logs/demo1_repaired/acceptance.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/logs/demo1_repaired/episodes.jsonl](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/logs/demo1_repaired/episodes.jsonl) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/logs/demo1_repaired/episodes/episode_0000.json](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/logs/demo1_repaired/episodes/episode_0000.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/logs/demo1_repaired/episodes/episode_0001.json](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/logs/demo1_repaired/episodes/episode_0001.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/logs/demo1_repaired/episodes/episode_0002.json](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/logs/demo1_repaired/episodes/episode_0002.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/logs/demo1_repaired/episodes/episode_0003.json](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/logs/demo1_repaired/episodes/episode_0003.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/logs/demo1_repaired/episodes/episode_0004.json](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/logs/demo1_repaired/episodes/episode_0004.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/logs/demo1_repaired/episodes/episode_0005.json](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/logs/demo1_repaired/episodes/episode_0005.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/logs/demo1_repaired/manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/logs/demo1_repaired/manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/logs/demo1_repaired/steps.jsonl](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/logs/demo1_repaired/steps.jsonl) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/logs/demo1_repaired/summary.json](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/logs/demo1_repaired/summary.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/route_summary.json](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/route_summary.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/trajectory_records.json](cre-demos/demo1_cr_boundary_lure/reports/latest/repaired/trajectory_records.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/verification/config_snapshot_manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/verification/config_snapshot_manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/verification/reward_diff.md](cre-demos/demo1_cr_boundary_lure/reports/latest/verification/reward_diff.md) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/verification/seed_manifest.json](cre-demos/demo1_cr_boundary_lure/reports/latest/verification/seed_manifest.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/verification/verification_summary.json](cre-demos/demo1_cr_boundary_lure/reports/latest/verification/verification_summary.json) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/reports/latest/verification/verification_summary.md](cre-demos/demo1_cr_boundary_lure/reports/latest/verification/verification_summary.md) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/scripts/run_demo1.py](cre-demos/demo1_cr_boundary_lure/scripts/run_demo1.py) [cre-demos]
- `A` [cre-demos/demo1_cr_boundary_lure/test_demo1_pipeline.py](cre-demos/demo1_cr_boundary_lure/test_demo1_pipeline.py) [cre-demos]
- `M` [doc/dev_log/p11_dev_status.md](doc/dev_log/p11_dev_status.md) [Project Docs]
<!-- TRACEABILITY:END -->
