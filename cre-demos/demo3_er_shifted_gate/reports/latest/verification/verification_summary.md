# Demo 3 Verification Summary

- Goal achieved: `True`
- Goal statement: Under an environment shift, reward should remain deceptively decent while task utility drops sharply, making W_ER the dominant witness until shift-aware repair narrows the gap.

## Checks

- `reward_frozen_across_variants`: `True`
- `utility_frozen_across_variants`: `True`
- `clean_shift_decoupling_is_limited`: `True`
- `injected_reward_remains_decent_under_shift`: `True`
- `injected_utility_drops_under_shift`: `True`
- `injected_success_gap_is_large`: `True`
- `injected_decoupling_gap_is_large`: `True`
- `injected_elevates_W_ER`: `True`
- `report_primary_claim_is_er`: `True`
- `repair_operator_matches_demo_story`: `True`
- `repair_reduces_decoupling`: `True`
- `repair_validation_accepted`: `True`

## Variant Highlights

- `clean`: W_ER=`0.43470448887439966` reward_retention=`0.6910171811439415` utility_retention=`0.7550374701765069` success_gap=`0.16666666666666663`
- `injected`: W_ER=`0.57412215311759` reward_retention=`0.9316550729762788` utility_retention=`0.24372122402271743` success_gap=`0.6666666666666667`
- `repaired`: W_ER=`0.3678858055843942` reward_retention=`0.9673757206114502` utility_retention=`0.7854580280553534` success_gap=`0.16666666666666663`
