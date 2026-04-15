# CRE Three-Demo Experiment Plan

## 1. Purpose

This folder is the **isolated planning workspace** for the three core CRE
demonstrations.

Its job is to prevent the demo work from drifting into ad hoc changes inside:

- `isaac-training/training/cfg/benchmark_cfg/`
- `isaac-training/training/scripts/`
- the main Phase 11 benchmark/release path

until the demo design is stable enough to deserve implementation.

This plan is intentionally stricter than a normal brainstorm note:

- each demo must have one dominant causal claim,
- each demo must freeze what is allowed to change,
- and each demo must define what would count as a convincing success.

## 2. Isolation Rule

All **demo-specific** future files should stay under `cre-demos/`.

Recommended future layout:

```text
cre-demos/
  README.md
  demo1_cr_boundary_lure/
    README.md
  demo2_ec_hidden_wedge/
    README.md
  cfg/
    env_cfg/
    spec_cfg/
  scripts/
  assets/
    screenshots/
    videos/
  reports/
```

Rules:

1. do **not** patch the main benchmark configs first
2. do **not** put demo-only scene YAMLs into the main training config tree
3. do **not** use the main Phase 11 benchmark suite as the first experimental sandbox
4. once a demo is visually and causally clean, it can later be upstreamed

Current dedicated subplans:

- Demo 1:
  - [demo1_cr_boundary_lure/README.md](demo1_cr_boundary_lure/README.md)
- Demo 2:
  - [demo2_ec_hidden_wedge/README.md](demo2_ec_hidden_wedge/README.md)

## 3. Common Demo Contract

All three demos should use the same presentation grammar:

`Clean -> Injected -> Repaired`

Each demo page or report should show:

1. one scene visual
2. one core metric figure
3. one claim type
4. one repair direction
5. one validation result

All three demos should also share these engineering rules:

### 3.1 Fixed evaluation seeds

Use a fixed seed set for all comparisons, for example:

- `11`
- `17`
- `23`
- `31`
- `47`

The seed list must remain identical inside one demo.

### 3.2 Fixed triplet structure

For every demo, produce three comparable variants:

- `clean`
- `injected`
- `repaired`

### 3.3 Fixed evidence surface

Each demo should export the same evidence categories:

- scene screenshot or short video
- run summary
- dynamic report
- semantic/report summary
- validation summary

### 3.4 Fixed visual output set

Each demo should produce:

1. one top-down scene view
2. one trajectory overlay or path-choice visual
3. one metric comparison chart
4. one clean-vs-injected-vs-repaired summary card

### 3.5 One-factor rule

Each demo is only convincing if its main causal factor is isolated:

- Demo 1:
  reward changes, environment fixed
- Demo 2:
  environment coverage changes, reward fixed
- Demo 3:
  evaluation environment shifts, utility metric separated from reward

If this rule is broken, the demo becomes ambiguous and should be rejected.

## 4. Shared Visualization Plan

To keep the three demos easy to compare, use the same visualization stack:

### 4.1 Scene view

Use `test_flight.py` or a dedicated demo scene viewer to capture:

- UAV start position
- goal position
- obstacle layout
- intended risky region
- nominal vs shifted / critical contrast when relevant

### 4.2 Trajectory view

Preferred visuals:

- top-down trajectory overlay across multiple seeds
- heatmap of visited space
- corridor-choice ratio if there are two route options

### 4.3 Metrics view

Preferred chart types:

- grouped bar chart:
  `clean vs injected vs repaired`
- scatter plot:
  `reward vs utility`
- gap chart:
  `nominal vs critical` or `nominal vs shifted`

### 4.4 Final operator-facing artifacts

Each demo should eventually write a small self-contained report under
`cre-demos/reports/<demo_name>/` containing:

- `scene_summary.md`
- `metrics_summary.json`
- `visual_manifest.json`
- `demo_takeaway.md`

## 5. Demo 1: Class I (C-R) Constructive Experiment

### 5.1 Goal

Prove that the **reward definition itself** pushes the learned policy toward a
dangerous boundary region.

This is a reward-vs-constraint inconsistency demo, not a scene-coverage demo.

### 5.2 Core causal claim

If the environment is held fixed and only the reward is biased toward progress,
the policy should increasingly prefer the **short but unsafe** route.

### 5.3 Dedicated scene concept

Scene name:

- `demo1_cr_boundary_lure`

Visual concept:

- one start point
- one goal point
- two feasible corridors

Route A:

- short
- high progress reward
- narrow clearance
- close to the wall / obstacle boundary

Route B:

- slightly longer
- visibly safer
- larger clearance
- should be preferred by a healthy reward design

Recommended geometry:

- a static obstacle cluster that creates:
  - one inner "tempting" narrow channel
  - one outer "safe" channel
- no dynamic obstacle in version 1
- same scene for all three variants

### 5.4 What is allowed to change

Allowed:

- reward weights
- reward component balance
- repair-side reward correction

Frozen:

- scene geometry
- start-goal placement
- seed list
- policy architecture
- training budget

### 5.5 Three variants

#### Clean

- balanced progress reward
- meaningful static safety penalty
- intended outcome:
  - policy mainly uses the safer corridor

#### Injected

- increase `reward_progress.weight`
- decrease `reward_safety_static.weight`
- intended outcome:
  - policy hugs the obstacle boundary
  - shorter path looks attractive under reward

#### Repaired

- restore or rebalance safety pressure
- optionally inject boundary-aware penalty shaping
- intended outcome:
  - policy returns toward the safer corridor

### 5.6 Minimum convincing execution mode

Canonical path:

- `train`
- then `eval`

Why:

- the causal story is that reward changes reshape learned behavior
- a pure scripted baseline can help pre-visualize the scene
- but it is not sufficient as the final proof

### 5.7 Must-show metrics

Primary:

- `W_CR`

Secondary:

- `min_distance`
- `near_violation_ratio`
- `collision_rate`
- `short_corridor_choice_ratio` (demo-specific metric)

### 5.8 Must-show visualizations

1. top-down scene with both corridors labeled
2. trajectory overlay:
   - clean trajectories mostly outside
   - injected trajectories crowd the inner boundary
3. grouped bars:
   - `W_CR`
   - `min_distance`
   - `near_violation_ratio`

### 5.9 Success criteria

The demo is convincing only if all conditions hold:

1. the environment stays fixed
2. the injected case shows visibly more boundary-hugging behavior
3. `W_CR` becomes the dominant witness direction
4. `min_distance` drops and `near_violation_ratio` rises
5. the repaired case visibly reverses the trend

Suggested quantitative target:

- injected `short_corridor_choice_ratio` exceeds clean by at least `+40 pp`
- injected `near_violation_ratio` is at least `2x` clean
- repaired `min_distance` recovers at least half of the clean-to-injected loss

### 5.10 What would mean we drifted off target

Reject the demo if:

- the scene geometry changed between clean and injected
- the injected result mainly fails because of unseen critical scenes
- the policy simply crashes everywhere instead of specifically preferring the
  risky route

If that happens, the demo has become:

- `E-C`
- or just a weak broken-training example

## 6. Demo 2: Class II (E-C) Coverage-Insufficiency Experiment

Detailed Chinese subplan:

- [demo2_ec_hidden_wedge/README.md](demo2_ec_hidden_wedge/README.md)

### 6.1 Goal

Prove that the reward is **not the main problem**; the real issue is that the
training environment does not cover the dangerous critical region at all.

This is an environment-vs-constraint demo, not a reward misspecification demo.

### 6.2 Core causal claim

With the reward held fixed, a policy trained on easy/open scenes can look fine
in nominal settings while still failing hard on boundary-critical regions that
were almost never present during training.

### 6.3 Dedicated scene concept

Scene family names:

- training family:
  - `demo2_ec_open_bias_train`
- evaluation family:
  - `demo2_ec_hidden_wedge_eval`

Visual concept:

- training scenes overrepresent:
  - wide corridors
  - clean turns
  - open obstacle spacing
- evaluation scenes introduce:
  - narrow L-turn
  - boundary-adjacent choke point
  - one blind spot or clutter pocket near the wall

Recommended geometry:

- keep the same high-level task:
  start -> navigate clutter -> reach goal
- make the critical region obvious in screenshots:
  - red wedge / narrow slot / blind corner

### 6.4 What is allowed to change

Allowed:

- training scene-family sampling
- environment distribution
- critical-template coverage
- environment-side repair through oversampling / scenario injection

Frozen:

- reward definition
- reward weights
- policy architecture
- training budget
- core task semantics

### 6.5 Three variants

#### Clean

- reward is frozen
- training distribution includes enough critical geometry
- intended outcome:
  - nominal and critical performance gap is moderate

#### Injected

- reward still frozen
- critical geometry is under-covered during training
- intended outcome:
  - nominal scenes still look acceptable
  - critical scenes fail sharply

#### Repaired

- reward still frozen
- critical scenes injected back into training
- intended outcome:
  - critical-scene gap narrows

### 6.6 Minimum convincing execution mode

Canonical path:

- `train` on training family
- `eval` on:
  - training-like nominal family
  - critical evaluation family

Why:

- this demo is about missing coverage during learning
- without a train/eval split, the claim is too weak

### 6.7 Must-show metrics

Primary:

- `W_EC`

Secondary:

- `boundary_critical_vs_nominal_success_gap`
- `boundary_critical_vs_nominal_min_distance_gap`
- `critical_region_entry_rate` (demo-specific)
- `critical_region_failure_rate` (demo-specific)

### 6.8 Must-show visualizations

1. side-by-side training coverage map vs critical danger mask
2. nominal scene screenshot vs critical scene screenshot
3. grouped bars:
   - nominal success rate
   - critical success rate
   - critical min distance
4. optional heatmap:
   - trajectories rarely enter the critical wedge during injected training

### 6.9 Success criteria

The demo is convincing only if all conditions hold:

1. reward is identical across clean / injected / repaired
2. nominal performance remains relatively okay in the injected case
3. critical-scene performance drops much more strongly
4. `W_EC` becomes the dominant witness direction
5. repaired environment coverage narrows the critical-scene gap

Suggested quantitative target:

- injected nominal success drop is less than `10 pp`
- injected critical success drop is at least `30 pp`
- injected critical min-distance gap widens clearly relative to clean
- repaired case closes at least half of the clean-to-injected critical gap

### 6.10 What would mean we drifted off target

Reject the demo if:

- reward changed
- the injected case only fails because reward weights changed
- all scenes fail equally badly
- the failure is actually caused by nominal-vs-shifted transfer mismatch

If that happens, the demo has become:

- `C-R`
- `E-R`
- or a generic weak-policy demo

## 7. Demo 3: Class III (E-R) Decoupling Experiment

### 7.1 Goal

Prove that a **high reward does not guarantee high real task utility** once the
environment shifts away from the nominal training distribution.

This is an environment-vs-reward decoupling demo, not merely low reward.

### 7.2 Core causal claim

A policy can still collect a relatively strong reward signal in the shifted
environment while its real mission utility drops:

- lower success
- worse safety
- more timeout or stuck behavior

### 7.3 Critical design rule

Before running anything, define a **task utility metric that is not the reward**.

Recommended utility surface:

- `success_rate`
- `collision_rate`
- `timeout_rate`
- `min_distance`
- optional:
  - normalized time-to-goal
  - path efficiency

Do **not** define utility from reward.

### 7.4 Dedicated scene concept

Scene family names:

- train / clean eval:
  - `demo3_er_nominal_gate`
- shifted eval:
  - `demo3_er_shifted_gate_crossing`

Visual concept:

- nominal case:
  - centered doorway
  - expected obstacle spacing
  - static or predictable motion
- shifted case:
  - doorway laterally shifted
  - obstacle density slightly increased
  - optional cross-traffic obstacle or mild sensor bias

The point is not to make the scene impossible.
The point is to create a situation where:

- the reward proxy still looks decent
- but true mission utility drops sharply

### 7.5 What is allowed to change

Allowed:

- evaluation environment distribution
- shifted geometry / noise / traffic pattern
- robustness-side repair through domain randomization or family rebalance

Frozen:

- nominal reward definition
- nominal training setup
- task utility metric
- policy architecture

### 7.6 Three variants

#### Clean

- nominal train
- nominal eval
- intended outcome:
  - reward and utility are reasonably aligned

#### Injected

- nominal train
- shifted eval
- intended outcome:
  - average reward stays deceptively decent
  - true utility drops

#### Repaired

- nominal train with robustness-side repair
- shifted eval
- intended outcome:
  - reward-utility decoupling shrinks

### 7.7 Minimum convincing execution mode

Canonical path:

- `train` on nominal
- `eval` on nominal
- `eval` on shifted

Why:

- this demo is explicitly about transfer
- without a nominal-vs-shifted comparison, the claim is not established

### 7.8 Must-show metrics

Primary:

- `W_ER`

Secondary:

- `nominal_vs_shifted_success_gap`
- `nominal_vs_shifted_min_distance_gap`
- `average_return`
- `timeout_rate`
- optional demo-specific:
  - `utility_reward_scatter_correlation`

### 7.9 Must-show visualizations

1. side-by-side nominal vs shifted scene screenshot
2. grouped bars:
   - `average_return`
   - `success_rate`
   - `min_distance`
3. scatter plot:
   - x-axis = reward / return
   - y-axis = task utility
4. short video pair:
   - nominal success
   - shifted near-failure / timeout / unsafe passage

### 7.10 Success criteria

The demo is convincing only if all conditions hold:

1. reward stays non-trivially high in shifted evaluation
2. task utility drops substantially in shifted evaluation
3. `W_ER` becomes the dominant witness direction
4. robustness-side repair narrows the reward-utility decoupling

Suggested quantitative target:

- shifted `average_return` remains at least `80%` of nominal
- shifted `success_rate` drops by at least `30 pp`
- or shifted `timeout_rate` / safety degradation rises sharply
- repaired case recovers utility more than reward alone would predict

### 7.11 What would mean we drifted off target

Reject the demo if:

- shifted reward collapses together with utility
- the scene shift is so extreme that the policy just catastrophically fails
- utility is defined using reward itself
- the real issue is actually missing critical training coverage

If that happens, the demo has become:

- just a hard OOD failure
- or a disguised `E-C` case

## 8. Recommended Build Order

To maximize visible progress and avoid confusion, implement in this order:

1. **Demo 1 first**
   - easiest causal isolation
   - easiest visual story
   - easiest top-down path overlay

2. **Demo 2 second**
   - stronger train/eval split
   - needs explicit coverage visualization

3. **Demo 3 third**
   - most conceptually subtle
   - requires freezing a utility metric before execution

## 9. Demo-Specific Output Checklist

For each demo, the final isolated bundle should contain:

```text
cre-demos/reports/<demo_name>/
  scene_clean.png
  scene_injected.png
  scene_repaired.png
  trajectory_overlay.png
  metrics_comparison.png
  takeaway.md
  summary.json
```

The `takeaway.md` for each demo should answer only four questions:

1. what changed?
2. what stayed fixed?
3. what is the main witness direction?
4. why is this specifically `C-R`, `E-C`, or `E-R`?

## 10. One-Page Anti-Drift Summary

Use this as the fast sanity check before implementation starts.

| Demo | Allowed to change | Must stay fixed | Main proof | Main failure mode to avoid |
| --- | --- | --- | --- | --- |
| Demo 1 / `C-R` | reward terms | environment | policy prefers short unsafe route | accidentally changing scene coverage |
| Demo 2 / `E-C` | training environment coverage | reward | nominal okay, critical region bad | accidentally making reward wrong |
| Demo 3 / `E-R` | shifted evaluation environment | reward and utility definition | reward stays decent while utility drops | using reward as utility |

## 11. Decision Rule

If a proposed implementation cannot be explained in one sentence using the
table above, stop and redesign it inside this folder first.

That is the whole point of this document.
