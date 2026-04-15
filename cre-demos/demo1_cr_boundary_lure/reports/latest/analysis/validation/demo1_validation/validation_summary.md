# Validation Summary

- Repair bundle: `demo1_injected_repair`
- Primary claim type: `C-R`
- Decision: `accepted`
- Accepted: `True`
- Original runs: `1`
- Repaired runs: `1`

## Metric Deltas

- `W_CR`: original=`0.7180302016989563` repaired=`0.01175147595222004` improvement=`0.7062787257467362`
- `W_EC`: original=`0.1824074074074074` repaired=`0.0777777777777778` improvement=`0.1046296296296296`
- `W_ER`: original=`0.0` repaired=`0.0` improvement=`-0.0`
- `average_return`: original=`20.332736712594777` repaired=`21.2380898865634` improvement=`0.9053531739686242`
- `collision_rate`: original=`0.3333333333333333` repaired=`0.0` improvement=`0.3333333333333333`
- `episode_count`: original=`6.0` repaired=`6.0` improvement=`0.0`
- `min_distance`: original=`0.0672684745200607` repaired=`0.36444209453100185` improvement=`0.29717362001094116`
- `near_violation_distance`: original=`0.6` repaired=`0.6` improvement=`0.0`
- `near_violation_ratio`: original=`0.5787037037037037` repaired=`0.05555555555555555` improvement=`0.5231481481481481`
- `out_of_bounds_rate`: original=`0.0` repaired=`0.0` improvement=`0.0`
- `risky_route_rate`: original=`1.0` repaired=`0.0` improvement=`-1.0`
- `safe_route_rate`: original=`0.0` repaired=`1.0` improvement=`1.0`
- `success_rate`: original=`0.6666666666666666` repaired=`1.0` improvement=`0.33333333333333337`

## Decision Rationale

Repair improves consistency and safety, satisfies claim-specific family-gap checks, and stays within the allowed performance regression bound.
