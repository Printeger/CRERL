# Demo 3 Shift / Repair Diff

## Clean -> Injected

- `distribution_modes.route_adjacent_bias`: `0.42` -> `0.28`
- `distribution_modes.boundary_adjacent_bias`: `0.12` -> `0.04`
- `distribution_modes.shifted_distribution_bias`: `0.18` -> `0.06`
- `templates.min_templates_per_scene`: `1` -> `1`

## Injected -> Repaired

- `distribution_modes.route_adjacent_bias`: `0.28` -> `0.48`
- `distribution_modes.boundary_adjacent_bias`: `0.04` -> `0.16`
- `distribution_modes.shifted_distribution_bias`: `0.06` -> `0.28`
- `templates.min_templates_per_scene`: `1` -> `2`
- `validation_rules.require_shifted_semantics`: `False` -> `True`

Reward and utility remain frozen; only shifted-family preparation differs.
