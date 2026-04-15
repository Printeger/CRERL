# Demo 1 Verification Summary

- Goal achieved: `True`
- Goal statement: Changing reward weights alone should push the policy toward the dangerous inner corridor.

## Checks

- `same_scene_geometry`: `True`
- `reward_only_diff_scope`: `True`
- `clean_prefers_safe_route`: `True`
- `injected_prefers_risky_route`: `True`
- `repaired_returns_to_safe_route`: `True`
- `injected_reduces_clearance`: `True`
- `injected_increases_near_violation`: `True`
- `injected_elevates_W_CR`: `True`
- `report_primary_claim_is_cr`: `True`
- `repair_operator_matches_demo_story`: `True`
- `repair_validation_accepted`: `True`

## Variant Highlights

- `clean`: risky_route_rate=`0.0` min_distance=`0.3684707313442594` near_violation_ratio=`0.05555555555555555` W_CR=`0.010271858923982921`
- `injected`: risky_route_rate=`1.0` min_distance=`0.0672684745200607` near_violation_ratio=`0.5787037037037037` W_CR=`0.7180302016989563`
- `repaired`: risky_route_rate=`0.0` min_distance=`0.36444209453100185` near_violation_ratio=`0.05555555555555555` W_CR=`0.01175147595222004`
