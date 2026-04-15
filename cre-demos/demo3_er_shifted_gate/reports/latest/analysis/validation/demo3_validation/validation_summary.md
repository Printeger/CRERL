# Validation Summary

- Repair bundle: `demo3_injected_repair`
- Primary claim type: `E-R`
- Decision: `accepted`
- Accepted: `True`
- Original runs: `2`
- Repaired runs: `2`

## Metric Deltas

- `U_task_v1_mean`: original=`0.41089794655587203` repaired=`0.5923298500456808` improvement=`0.1814319034898088`
- `average_return`: original=`26.61832601818973` repaired=`27.824983262465494` improvement=`1.206657244275764`
- `clearance_score_mean`: original=`0.31218583045206744` repaired=`0.44279197321146174` improvement=`0.1306061427593943`
- `collision_rate`: original=`0.125` repaired=`0.0` improvement=`0.125`
- `critical_region_entry_rate`: original=`0.2916666666666667` repaired=`0.5` improvement=`0.20833333333333331`
- `episode_count`: original=`12.0` repaired=`12.0` improvement=`0.0`
- `min_distance`: original=`0.09302546143575302` repaired=`0.3666710895236958` improvement=`0.2736456280879428`
- `near_violation_distance`: original=`0.55` repaired=`0.55` improvement=`0.0`
- `near_violation_ratio`: original=`0.2817028985507246` repaired=`0.04710144927536232` improvement=`0.2346014492753623`
- `nominal_vs_shifted_collision_gap`: original=`0.25` repaired=`0.0` improvement=`0.25`
- `nominal_vs_shifted_min_distance_gap`: original=`1.121042380931291` repaired=`0.7643881226874071` improvement=`0.35665425824388397`
- `nominal_vs_shifted_near_violation_gap`: original=`0.5634057971014492` repaired=`0.09420289855072464` improvement=`0.4692028985507246`
- `nominal_vs_shifted_return_gap`: original=`1.8835946175460236` repaired=`0.922823249698606` improvement=`0.9607713678474177`
- `nominal_vs_shifted_success_gap`: original=`0.6666666666666667` repaired=`0.16666666666666663` improvement=`0.5000000000000001`
- `out_of_bounds_rate`: original=`0.0` repaired=`0.0` improvement=`0.0`
- `path_efficiency_score_mean`: original=`0.9281905810318831` repaired=`0.9685153723756542` improvement=`0.040324791343771094`
- `reward_utility_correlation`: original=`0.9563385842114138` repaired=`0.6767261987607307` improvement=`-0.2796123854506831`
- `shifted_min_distance`: original=`-0.46749572902989256` repaired=`-0.015522971820007725` improvement=`0.45197275720988483`
- `success_rate`: original=`0.6666666666666666` repaired=`0.9166666666666667` improvement=`0.2500000000000001`
- `time_efficiency_score_mean`: original=`0.8269363874081026` repaired=`0.9703244882030261` improvement=`0.14338810079492348`
- `timeout_rate`: original=`0.20833333333333334` repaired=`0.08333333333333333` improvement=`-0.125`

## Decision Rationale

Repair improves consistency and safety, satisfies claim-specific family-gap checks, and stays within the allowed performance regression bound.
