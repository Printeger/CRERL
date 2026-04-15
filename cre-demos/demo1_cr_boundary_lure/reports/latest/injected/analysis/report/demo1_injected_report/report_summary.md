# Unified CRE Report Summary

- Spec version: `demo1-v0`
- Passed: `True`
- Max severity: `medium`
- Ranked findings: `13`

## Primary Diagnosis

- Claim type: `C-R`
- Summary: Reward-boundary coupling is elevated.
- Support status: `machine_derived`
- Selection mode: `aggregate_claim_score`
- Why selected: Selected `C-R` from aggregated cross-namespace score with strongest supporting finding in `analysis/dynamic`.

## Strongest Evidence

- Source: `analysis/dynamic`
- Severity: `medium`
- Confidence: `0.7180302016989563`
- Summary: Reward-boundary coupling is elevated.

## Root-Cause Ordering

1. `C-R` score=`2.982746` findings=`6`
2. `E-C` score=`1.607333` findings=`4`
3. `E-R` score=`1.474125` findings=`3`

## Cross-Source Conflicts

- `static_dynamic_claim_type_conflict`: `analysis/static` -> `E-C`, `analysis/dynamic` -> `C-R`
- `static_semantic_claim_type_conflict`: `analysis/static` -> `E-C`, `analysis/semantic` -> `C-R`

## Next Repair Direction

- Direction: `reward`
- Impacted components: `C, E, R`
- Selected claims: `6`

## Repair Order

1. [C-R] `reward` from `analysis/static` via `ranked_finding_backfill`
   Summary: No suspicious reward proxy patterns were detected.
   Evidence refs: /home/mint/rl_dev/crerl_v1/cre-demos/demo1_cr_boundary_lure/cfg/spec_injected/reward_spec_v0.yaml, /home/mint/rl_dev/crerl_v1/cre-demos/demo1_cr_boundary_lure/cfg/spec_injected/policy_spec_v0.yaml
2. [C-R] `reward` from `analysis/static` via `ranked_finding_backfill`
   Summary: All required constraints map to runtime fields and threshold references.
   Evidence refs: /home/mint/rl_dev/crerl_v1/cre-demos/demo1_cr_boundary_lure/cfg/spec_injected/constraint_spec_v0.yaml
3. [C-R] `reward` from `analysis/dynamic` via `ranked_finding_backfill`
   Summary: Reward-boundary coupling is elevated.
   Evidence refs: demo1_injected
4. [E-C] `environment` from `analysis/static` via `ranked_finding_backfill`
   Summary: Scene families cover the current constraint activation requirements.
   Evidence refs: /home/mint/rl_dev/crerl_v1/cre-demos/demo1_cr_boundary_lure/cfg/env_cfg/scene_cfg_nominal.yaml, /home/mint/rl_dev/crerl_v1/cre-demos/demo1_cr_boundary_lure/cfg/spec_injected/constraint_spec_v0.yaml
5. [E-R] `mixed` from `analysis/static` via `ranked_finding_backfill`
   Summary: Scene backend capability matches the declared family requirements.
   Evidence refs: /home/mint/rl_dev/crerl_v1/cre-demos/demo1_cr_boundary_lure/cfg/env_cfg/scene_cfg_nominal.yaml, /home/mint/rl_dev/crerl_v1/isaac-training/training/envs/env_gen.py
6. [E-R] `mixed` from `analysis/static` via `ranked_finding_backfill`
   Summary: Reward component execution modes align with the supported execution paths.
   Evidence refs: /home/mint/rl_dev/crerl_v1/cre-demos/demo1_cr_boundary_lure/cfg/spec_injected/reward_spec_v0.yaml, /home/mint/rl_dev/crerl_v1/cre-demos/demo1_cr_boundary_lure/cfg/spec_injected/policy_spec_v0.yaml
