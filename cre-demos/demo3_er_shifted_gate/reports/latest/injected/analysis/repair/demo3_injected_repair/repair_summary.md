# Repair Summary

- Plan type: `phase8_repair_plan.v1`
- Source report bundle: `demo3_injected_report`
- Primary claim type: `E-R`
- Primary repair direction: `environment`
- Acceptance passed: `True`
- Acceptance max severity: `info`

## Selected Candidate

- Candidate id: `candidate:repair_handoff:scene_backend_capability:6:increase_shifted_boundary_bias`
- Operator type: `increase_shifted_boundary_bias`
- Target component: `E`
- Target file: `cre-demos/demo3_er_shifted_gate/cfg/env_injected/scene_cfg_shifted.yaml`
- Estimated edit cost: `1.0`

## Patch Preview

- Patch id: `patch:repair_handoff:scene_backend_capability:6:increase_shifted_boundary_bias`
- Patch type: `phase8_spec_patch.v1`
- Operations: `1`

## Phase 9 Validation Targets

- `W_ER`
- `nominal_vs_shifted_success_gap`
- `shifted_min_distance`

## Rationale

Selected `increase_shifted_boundary_bias` as the first repair operator for `E-R` based on Phase 7 handoff ordering and minimal edit cost. The primary claim type was overridden to `E-R` for this repair pass.
