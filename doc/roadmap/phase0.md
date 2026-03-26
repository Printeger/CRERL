# SPEC-v0: CRE Consistency and Repair for Indoor UAV Obstacle-Avoidance RL

## 1. Document Status
- Version: v0.1
- Date: [TODO: YYYY-MM-DD]
- Owner: [TODO]
- Project: CRE-based Specification Auditing and Repair for Indoor UAV RL
- Scope: Phase 0 problem freezing document
- Status: Draft / Review / Frozen

---

## 2. Project Goal

### 2.1 Core Goal
Build and validate a CRE-consistency auditing-and-repair framework for indoor UAV obstacle-avoidance reinforcement learning.

### 2.2 Practical Goal
Given a UAV RL task specification consisting of constraints, rewards, and environments, the system should:
1. detect likely inconsistencies in the specification before or during training,
2. attribute them to C--R, E--C, or E--R failure modes,
3. generate minimal repairs,
4. verify whether the repaired specification improves safety and deployment robustness.

### 2.3 Non-Goals
This project does **not** aim to:
- design a new state-of-the-art Safe RL optimizer,
- solve sim-to-real transfer in full generality,
- provide complete formal verification of neural policies,
- support all robotics tasks beyond the chosen UAV task in Phase 0.

---

## 3. Task Definition

### 3.1 Task Name
Indoor UAV goal-reaching with obstacle avoidance.

### 3.2 Task Description
A UAV starts from an initial pose in an indoor environment with static obstacles and must reach a goal region while avoiding collisions and maintaining safe motion behavior.

### 3.3 Episode Termination
An episode terminates when any of the following holds:
- the UAV reaches the goal region,
- the UAV collides with an obstacle,
- the UAV leaves the valid workspace,
- the maximum episode length is reached,
- [TODO: add any task-specific termination condition].

### 3.4 Intended Deployment Setting
The eventual deployment setting is indoor autonomous navigation under varying corridor widths, obstacle layouts, and sensing conditions.

---

## 4. Environment Family

### 4.1 Training Environment
Define the nominal training environment as a family of indoor obstacle-avoidance layouts with connected free-space regions and moderate navigation difficulty.

- map type: indoor cluttered layouts composed of open areas, partial bottlenecks, turning regions, and obstacle clusters
- obstacle density: medium
- local bottleneck width range: moderate
- minimum free-space clearance: sufficient for safe traversal under nominal policy behavior
- free-space connectivity: moderate to high
- topology complexity: moderate
- obstacle placement pattern: mixed structured and random placement
- sensor noise: low
- initial pose distribution: sampled in collision-free regions with sufficient clearance from nearby obstacles
- goal distribution: sampled in collision-free regions with sufficient clearance and moderate start-goal distance
- start-goal relation: sampled such that successful navigation requires non-trivial obstacle avoidance rather than near-straight-line motion

Recommended initial implementation ranges:
- obstacle density: 8--14 obstacles per 20m × 20m workspace
- local bottleneck width: 1.8m -- 2.6m
- sensor noise: Gaussian noise with sigma = 0.01 -- 0.03
- minimum initial clearance: >= 1.0m
- minimum goal clearance: >= 1.0m
- start-goal distance: 8.0m -- 16.0m

### 4.2 Deployment Evaluation Family
Define the deployment environment family \( \mathcal{D} \) as:
1. nominal environments,
2. boundary-critical environments,
3. shifted environments.

The purpose of this decomposition is to separate:
- in-distribution generalization,
- safety-boundary stress testing,
- distribution-shift robustness.

#### 4.2.1 Nominal Environments
Nominal evaluation environments follow the same generative family as the training environment but use held-out map seeds and held-out obstacle realizations.

Concrete settings:
- map type: indoor cluttered layouts with connected free-space regions
- obstacle density: same range as training
- local bottleneck width: same range as training
- minimum free-space clearance: same range as training
- topology complexity: same range as training
- sensor noise: same range as training
- initial pose distribution: same distribution family as training
- goal distribution: same distribution family as training
- evaluation map seeds: disjoint from training seeds

Purpose:
- evaluate standard generalization to unseen layouts without intentional safety stress or distribution shift.

#### 4.2.2 Boundary-Critical Environments
Boundary-critical environments are designed to increase exposure to safety-relevant states while preserving the same navigation objective.

These environments emphasize:
- smaller local bottlenecks,
- lower free-space clearance,
- tighter turning regions,
- denser local obstacle interactions,
- start and goal placements that force navigation near safety boundaries.

Concrete settings:
- map type: cluttered indoor layouts with more narrow passages, doorway-like structures, obstacle pinch-points, and sharper turns
- obstacle density: high
- local bottleneck width: smaller than training
- minimum free-space clearance: lower than training
- topology complexity: moderate to high
- obstacle placement pattern: obstacle clusters placed near likely shortest paths
- sensor noise: same as nominal, so that changes mainly probe safety-boundary exposure rather than sensing shift
- initial pose distribution: sampled in collision-free regions but with reduced clearance from nearby obstacles
- goal distribution: more frequently placed behind narrow passages, turning regions, or partially occluded routes

Recommended initial implementation ranges:
- obstacle density: 14--22 obstacles per 20m × 20m workspace
- local bottleneck width: 1.0m -- 1.6m
- sensor noise: Gaussian noise with sigma = 0.01 -- 0.03
- minimum initial clearance: >= 0.5m
- minimum goal clearance: >= 0.6m
- start-goal distance: 8.0m -- 16.0m

Purpose:
- test whether the training environment sufficiently covered constraint-critical states,
- test whether the learned policy remains safe when the feasible region becomes narrow,
- expose C--R and E--C inconsistencies.

#### 4.2.3 Shifted Environments
Shifted environments preserve the obstacle-avoidance task but alter environment statistics relative to training.

These shifts may affect:
- layout style,
- obstacle placement distribution,
- sensing conditions,
- initialization distribution,
- free-space connectivity patterns.

Concrete settings:
- map type: layouts with topology distributions not seen during training, such as more irregular room connectivity, asymmetric branching, dead-end structures, or maze-like subregions
- obstacle density: moderate to medium-high
- local bottleneck width: may overlap with training but differ in spatial arrangement and frequency
- minimum free-space clearance: similar to or slightly below training, but distributed differently
- topology complexity: higher or differently structured than training
- obstacle placement pattern: altered spatial statistics relative to training
- sensor noise: higher than training
- initial pose distribution: shifted toward wall-adjacent or orientation-disadvantaged free-space regions
- goal distribution: more frequent placement behind turns, within visually ambiguous routes, or in layouts requiring longer-horizon planning

Recommended initial implementation ranges:
- obstacle density: 8--16 obstacles per 20m × 20m workspace
- local bottleneck width: 1.6m -- 2.4m
- sensor noise: Gaussian noise with sigma = 0.05 -- 0.10
- minimum initial clearance: >= 0.7m
- minimum goal clearance: >= 0.7m

Purpose:
- evaluate whether the learned policy relies on environment-specific shortcuts,
- test reward and performance stability under shifted environment statistics,
- expose E--R inconsistencies and deployment fragility.

### 4.3 Environment Parameters
List all environment parameters that may vary:

#### 4.3.1 Geometry and Topology
- map seed
- workspace size
- map topology type
- free-space connectivity
- topology complexity
- bottleneck frequency
- local bottleneck width
- turning angle distribution
- dead-end frequency
- branch/junction frequency

#### 4.3.2 Obstacle Configuration
- obstacle count
- obstacle size distribution
- obstacle shape category
- obstacle placement pattern
- obstacle clustering strength
- obstacle proximity to likely shortest paths
- minimum obstacle-to-obstacle spacing

#### 4.3.3 Sensing and Dynamics
- sensor noise level
- sensor dropout probability
- observation corruption type
- dynamics perturbation level
- actuation disturbance level
- control delay [optional]
- sensing delay [optional]

#### 4.3.4 Initialization and Goal Sampling
- initial position distribution
- initial heading distribution
- initial clearance from nearby obstacles
- goal position distribution
- goal clearance from nearby obstacles
- start-goal distance range

#### 4.3.5 Scenario-Level Control
- scenario type (`nominal`, `boundary-critical`, `shifted`)
- safety-critical scenario sampling ratio
- hard-case oversampling ratio
- environment reset curriculum stage [optional]

### 4.4 Design Rationale
The environment family is intentionally defined around indoor obstacle-avoidance properties rather than a single structural template such as corridors.

The key controllable factors are:
- how narrow the locally traversable space becomes,
- how close the agent must fly to obstacles,
- how complex the free-space topology is,
- and how much the deployment distribution differs from the training distribution.

Under this formulation, corridors, doorways, narrow passages, turning regions, and cluttered open areas are all treated as particular realizations of a more general indoor obstacle-avoidance environment family.

---

## 5. State, Action, and Dynamics Assumptions

### 5.1 Observation / State
The policy observes:
- LiDAR range-like observations represented as a tensor of shape `[1, H, V]`, where each entry is `lidar_range - hit_distance`, so nearer obstacles produce larger values
- relative goal direction encoded as a normalized goal-direction vector in the goal-aligned frame
- relative goal distance decomposed into horizontal distance and vertical distance-to-goal
- linear velocity expressed in the goal-aligned frame
- dynamic obstacle features for the closest `N` tracked obstacles, including relative direction, horizontal/vertical distance, obstacle velocity, and coarse size categories
- angular velocity / yaw rate are **not** directly provided to the policy in the current NavRL implementation
- attitude-related features are **not** directly provided to the policy in the current NavRL implementation
- previous action is **not** included in the policy observation in the current NavRL implementation

State dimension:
- low-dimensional vector state: 8
- additional observation blocks:
  - LiDAR tensor: `[1, lidar_hbeams, lidar_vbeams]`
  - dynamic obstacle tensor: `[1, dyn_obs_num, 10]`
  - auxiliary direction tensor used for coordinate transforms: `[1, 3]`

Observation modality:
- hybrid
- the policy receives a hybrid observation consisting of:
  - a LiDAR tensor processed by a CNN,
  - an 8D vector state,
  - a dynamic-obstacle feature tensor processed by an MLP

Partial observability:
- yes
- the current policy observes local LiDAR geometry, relative-goal information, and a local summary of nearby dynamic obstacles, but does not observe the full global map, full future obstacle trajectories, or the complete vehicle attitude / angular-rate state. The implementation therefore assumes partially observable navigation with local geometric sensing and relative-goal guidance.

### 5.2 Action Space
Action type:
- continuous

Action definition:
- policy-level action: a 3D target velocity command in the goal-aligned local frame
- forward velocity: yes
- lateral velocity: yes
- vertical velocity: yes
- yaw rate: not used in the current training setup (`yaw_control=False`)
- implementation note: the policy outputs normalized actions in `[0, 1]^3`, which are rescaled to local-frame target velocities and then converted to world-frame velocities before being passed to a low-level controller

Action bounds:
- normalized policy output: `[0, 1]^3`
- rescaled target-velocity range: `[-2.0, 2.0]^3` m/s in the local goal-aligned frame
- low-level actuator command: the multirotor backend ultimately converts the target velocity into 4 rotor commands in `[-1, 1]`

### 5.3 Dynamics Assumptions
- simulator type: NVIDIA Isaac Sim with PhysX, via OmniDrones / IsaacEnv
- control frequency: approximately `1 / dt = 62.5 Hz`, with `dt = 0.016 s`
- kinematic / dynamic UAV model: dynamic multirotor model with rotor thrust / moment generation, rigid-body dynamics, gravity, and drag
- actuation delay modeled?: yes, approximately, through rotor throttle response parameters (`tau_up`, `tau_down`) in the rotor group
- sensor delay modeled?: no explicit sensing delay is modeled in the current NavRL implementation
- additional assumptions:
  - the policy issues target velocities rather than direct motor thrusts
  - a Lee position controller converts target velocities into rotor-level commands
  - the LiDAR is configured with `attach_yaw_only=True`, so sensing is stabilized against roll / pitch changes in the current setup
  - the current observation pathway does not expose full attitude or angular velocity to the policy, even though these quantities exist in the underlying simulator state

---

## 6. Constraint Specification \(C\)

Let \( C = \{c_1, \dots, c_m\} \).

### 6.1 Constraint List
For each constraint, define:
- name,
- mathematical meaning,
- operational logging field,
- violation condition,
- severity.

#### c1: Collision Avoidance
- Meaning: the UAV must not collide with obstacles.
- Logged variable: `collision_flag`
- Violation condition: `collision_flag == 1`
- Severity: critical

#### c2: Safety Margin
- Meaning: minimum obstacle distance must remain above threshold.
- Logged variable: `min_obstacle_distance`
- Violation condition: `min_obstacle_distance < d_safe`
- Threshold: 0.3 m
- Severity: high

#### c3: Speed Bound
- Meaning: linear speed must remain below threshold.
- Logged variable: `speed_norm`
- Violation condition: `speed_norm > v_max`
- Threshold: 1.5 m/s
- Severity: medium

#### c4: Yaw-Rate Bound
- Meaning: turning motion must remain dynamically feasible and stable.
- Logged variable: `yaw_rate`
- Violation condition: `abs(yaw_rate) > omega_max`
- Threshold: 1.0 rad/s
- Severity: medium

#### c5: Workspace Boundary
- Meaning: the UAV must remain inside the valid indoor workspace.
- Logged variable: `out_of_bounds_flag`
- Violation condition: `out_of_bounds_flag == 1`
- Severity: high

### 6.2 Constraint Priorities
Define priority ordering as follows:
- critical:
  - `c1` Collision Avoidance
- major:
  - `c2` Safety Margin
  - `c5` Workspace Boundary
- minor:
  - `c3` Speed Bound
  - `c4` Yaw-Rate Bound

Recommended interpretation:
- critical constraints correspond to direct safety failures and should dominate severity scoring;
- major constraints correspond to strong safety-related boundary violations;
- minor constraints correspond to motion-feasibility or stability-related violations.

### 6.3 Constraint Cost Form
For learning and evaluation, constraints are represented in both forms:
- hard boolean violations,
- soft costs.

#### 6.3.1 Hard Boolean Violations
For each constraint \(c_j\), define a binary violation indicator:
\[
\mathbbm{1}_{c_j,t} =
\begin{cases}
1, & \text{if constraint } c_j \text{ is violated at step } t, \\
0, & \text{otherwise.}
\end{cases}
\]

Concretely:
- collision:
  \[
  \mathbbm{1}_{c_1,t} = \mathbbm{1}[\texttt{collision\_flag}_t = 1]
  \]
- safety margin:
  \[
  \mathbbm{1}_{c_2,t} = \mathbbm{1}[\texttt{min\_obstacle\_distance}_t < d_{\mathrm{safe}}]
  \]
- speed bound:
  \[
  \mathbbm{1}_{c_3,t} = \mathbbm{1}[\texttt{speed\_norm}_t > v_{\max}]
  \]
- yaw-rate bound:
  \[
  \mathbbm{1}_{c_4,t} = \mathbbm{1}[|\texttt{yaw\_rate}_t| > \omega_{\max}]
  \]
- workspace boundary:
  \[
  \mathbbm{1}_{c_5,t} = \mathbbm{1}[\texttt{out\_of\_bounds\_flag}_t = 1]
  \]

These binary indicators are used for:
- episode termination logic,
- violation counting,
- safety evaluation,
- CRE inconsistency reporting.

#### 6.3.2 Soft Constraint Costs
To support learning-time monitoring, severity analysis, and repair validation, define soft costs for each constraint.

- collision cost:
  \[
  \tilde c_1(t) = \mathbbm{1}[\texttt{collision\_flag}_t = 1]
  \]

- safety-margin cost:
  \[
  \tilde c_2(t) = \max\bigl(0,\ d_{\mathrm{safe}} - \texttt{min\_obstacle\_distance}_t\bigr)
  \]

- speed cost:
  \[
  \tilde c_3(t) = \max\bigl(0,\ \texttt{speed\_norm}_t - v_{\max}\bigr)
  \]

- yaw-rate cost:
  \[
  \tilde c_4(t) = \max\bigl(0,\ |\texttt{yaw\_rate}_t| - \omega_{\max}\bigr)
  \]

- workspace-boundary cost:
  \[
  \tilde c_5(t) = \mathbbm{1}[\texttt{out\_of\_bounds\_flag}_t = 1]
  \]

These soft costs are used for:
- training-time safety monitoring,
- dynamic inconsistency diagnostics,
- repair scoring,
- optional constrained RL formulations.

#### 6.3.3 Aggregated Constraint Cost
If a single scalar constraint cost is needed, define
\[
\tilde C_t = \sum_{j=1}^{m} \alpha_j \tilde c_j(t),
\]
where \(\alpha_j \ge 0\) is the severity weight of constraint \(c_j\).

Recommended initial weighting:
- \(\alpha_1 = 5.0\) for collision,
- \(\alpha_2 = 3.0\) for safety margin,
- \(\alpha_5 = 3.0\) for workspace boundary,
- \(\alpha_3 = 1.0\) for speed,
- \(\alpha_4 = 1.0\) for yaw rate.

These weights may be adjusted later, but the priority relation
\[
\alpha_1 > \alpha_2 = \alpha_5 > \alpha_3 = \alpha_4
\]
should be preserved.

---

## 7. Reward Specification \(R\)

### 7.1 Reward Design Principle
In the current NavRL implementation, the reward is a dense shaping objective rather than a clean task-spec reward with explicit success bonus and collision penalty.

The implemented reward encourages:
- moving with velocity aligned toward the goal,
- keeping larger clearance from static and dynamic obstacles,
- maintaining smooth velocity changes,
- staying within a reasonable altitude band between start and goal heights.

The current implementation does **not** explicitly include:
- a success bonus,
- a negative per-step time penalty,
- an explicit collision penalty term.

The reward documented in this section should therefore be interpreted as the **current implementation reward** used for policy optimization in NavRL, rather than a minimal task-level reward specification. In the present CRE framework, this implemented shaping reward is the object of diagnosis, repair, and empirical validation.

### 7.2 Reward Components
In the current NavRL implementation, the reward is:
\[
R =
r_{goal}
+ r_{base}
+ r_{safe,static}
+ \mathbf{1}_{dyn}\, r_{safe,dynamic}
- 0.1 \, p_{smooth}
- 8.0 \, p_{height}
\]

#### r1: Goal Progress Reward
- Meaning: reward for moving with velocity aligned with the goal direction.
- Formula:
  \[
  r_{goal} = \langle v, \hat{d}_{goal} \rangle
  \]
  where \( v \) is the UAV linear velocity in world coordinates and \( \hat{d}_{goal} \) is the unit vector from the current state to the goal.
- Weight: `1.0`
- Note: this term encourages motion aligned with the goal direction, but it is not identical to true distance-to-goal decrease.

#### r2: Success Bonus
- Meaning: bonus for reaching the goal region.
- Formula: not implemented in the current NavRL reward.
- Weight: `0`

#### r3: Step Reward / Time Term
- Meaning: the current implementation uses a constant positive step reward instead of a negative time penalty.
- Formula:
  \[
  r_{base} = 1
  \]
- Weight: `1.0`
- Note: this is not a standard time penalty; it is a constant living reward added at every step.

#### r4: Smoothness / Control Penalty
- Meaning: discourage abrupt control changes or excessive action magnitude.
- Formula:
  \[
  p_{smooth} = \| v_t - v_{t-1} \|_2
  \]
- Weight: `0.1`, applied as `-0.1 * p_smooth`

#### r5: Safety Proximity Penalty
- Meaning: reward larger obstacle clearance through a log-distance shaping term.
- Formula:
  \[
  r_{safe,static} = \mathrm{mean}(\log(\max(d_{static}, \epsilon_d)))
  \]
  where \( d_{static} \) is the LiDAR-derived distance to static obstacles and \( \epsilon_d > 0 \) is a small clipping constant used to avoid numerical instability when distances become very small.

  If dynamic obstacles are enabled, an additional term is used:
  \[
  r_{safe,dynamic} = \mathrm{mean}(\log(\max(d_{dynamic}, \epsilon_d)))
  \]
- Weight:
  - static safety term: `1.0`
  - dynamic safety term: `1.0` when dynamic obstacles are present
- Note: although this section is named "penalty", the current implementation uses positive clearance rewards rather than explicit negative proximity penalties.

#### r6: Collision Penalty
- Meaning: strong penalty for collision.
- Formula: not implemented as a separate reward term; collision is handled by episode termination.
- Weight: `0`

#### r7: Height Deviation Penalty
- Meaning: penalize flying too far above or below the height band induced by start and goal heights.
- Formula:
  \[
  p_{height} =
  \begin{cases}
  (z - z_{max}^{band} - 0.2)^2, & z > z_{max}^{band} + 0.2 \\\\
  (z_{min}^{band} - 0.2 - z)^2, & z < z_{min}^{band} - 0.2 \\\\
  0, & \text{otherwise}
  \end{cases}
  \]
- Weight: `8.0`, applied as `-8.0 * p_height`
- Note: this term is part of the current NavRL implementation. If the final V0 environment is instantiated as a strictly planar navigation abstraction, this term should be disabled and set to zero consistently throughout training and evaluation.

### 7.2.1 Implementation Notes
- When dynamic obstacles are disabled:
  \[
  R = r_{goal} + r_{base} + r_{safe,static} - 0.1 p_{smooth} - 8.0 p_{height}
  \]
- When dynamic obstacles are enabled:
  \[
  R = r_{goal} + r_{base} + r_{safe,static} + r_{safe,dynamic} - 0.1 p_{smooth} - 8.0 p_{height}
  \]

### 7.2.2 Variable and Numerical Conventions
The following conventions are used in the reward implementation:

- \(v\): UAV linear velocity in world coordinates.
- \(\hat{d}_{goal}\): unit vector pointing from the current UAV position to the goal position.
- \(d_{static}\): vector of static-obstacle distances returned by the local range sensor.
- \(d_{dynamic}\): vector of dynamic-obstacle distances, used only when dynamic obstacles are enabled.
- \(\mathrm{mean}(\cdot)\): arithmetic mean over valid obstacle-distance samples in the current observation.
- \(\mathbf{1}_{dyn}\): indicator variable equal to `1` when dynamic obstacles are enabled and `0` otherwise.
- \(\epsilon_d\): distance clipping constant used in the log-distance terms to prevent undefined values at very small distances.

Recommended initial setting:
- \(\epsilon_d = 10^{-3}\) or another simulator-consistent positive minimum distance.

Implementation note:
- the log-distance shaping terms should always be computed with clipped distances, i.e.,
  \[
  \log(\max(d,\epsilon_d)),
  \]
  to ensure numerical stability.

### 7.2.3 Terminal Transition Handling
The current reward design does not introduce an additional terminal reward for success, collision, or timeout beyond the shaping terms listed above, unless explicitly implemented elsewhere in the environment wrapper.

This implies:
- reaching the goal region does not automatically add a separate success bonus,
- collision does not automatically add a separate negative reward shock,
- collision and other terminal events mainly affect return through episode termination rather than through explicit terminal reward terms.

If a later implementation introduces terminal shaping, it must be documented separately and versioned as a reward specification change.

### 7.3 Reward–Constraint Relation
The implemented reward has several direct or indirect interactions with the constraint set defined in Section 6.

#### 7.3.1 Relation to c1: Collision Avoidance
- There is no explicit collision penalty term in the reward.
- Collision affects optimization primarily through episode termination rather than a direct reward shock.
- This may weaken the immediate optimization signal associated with collision events.

#### 7.3.2 Relation to c2: Safety Margin
- The clearance terms \(r_{safe,static}\) and \(r_{safe,dynamic}\) positively reward larger distances from obstacles.
- However, because progress is encouraged separately through \(r_{goal}\), the resulting optimization may still prefer fast but boundary-seeking trajectories in constrained layouts.
- Therefore, the current reward does not guarantee consistency with the formal safety-margin constraint.

#### 7.3.3 Relation to c3: Speed Bound
- No explicit speed penalty term is included in the reward.
- This means the speed constraint is enforced at the constraint level rather than through direct reward shaping.
- If aggressive motion improves progress reward, reward–constraint tension may arise.

#### 7.3.4 Relation to c4: Yaw-Rate Bound
- No explicit yaw-rate penalty term is included beyond the smoothness penalty.
- The smoothness term may partially discourage abrupt motion, but it is not equivalent to enforcing a formal yaw-rate bound.

#### 7.3.5 Relation to c5: Workspace Boundary
- No explicit workspace-boundary reward term is included.
- The workspace constraint is therefore represented only at the constraint and termination level.

Summary:
- the current reward contains partial safety shaping,
- but several hard constraints remain outside the reward itself,
- which makes the current implementation a natural object for C--R inconsistency analysis.

### 7.4 Reward Components Explicitly Excluded
List reward terms intentionally not included:
- explicit success bonus on entering the goal region
- explicit negative time penalty per step
- explicit collision penalty term
- explicit yaw-control reward
- explicit attitude stabilization reward
- explicit previous-action penalty
- explicit separate speed-limit penalty

### 7.5 Expected Failure Modes in Reward Design
Potential risks:
- over-emphasis on progress may induce boundary-seeking,
- lack of an explicit success bonus may under-emphasize actually entering the goal region,
- the constant per-step reward may encourage longer episodes instead of faster completion,
- safety is encouraged through dense shaping rather than a formal safety-margin constraint,
- collision causes termination but does not add a separate negative reward shock,
- environment-specific proxy reward may not transfer,
- progress is defined through velocity alignment rather than true distance-to-goal decrease, which may admit local shortcut behavior,
- no explicit speed or attitude penalty is used at the reward level, which may hide deployment-relevant instability.

### 7.6 Scope of This Reward Specification
This section documents the reward currently implemented in NavRL and used in the present CRE analysis.

It should not be interpreted as the only valid reward design for indoor UAV obstacle avoidance. Instead:
- this reward serves as the current optimization objective,
- the final task evaluation will rely on task success, safety violations, and deployment robustness,
- and later reward repairs may modify selected terms while preserving the overall task semantics.

Allowed reward-edit operations in later repair stages may include:
- reweighting existing reward terms,
- replacing the constant step reward with a time penalty,
- adding explicit terminal success or collision terms,
- modifying safety shaping coefficients.

Core task semantics that should remain unchanged:
- the UAV must reach the goal,
- obstacle avoidance remains mandatory,
- the environment objective remains indoor autonomous navigation rather than reward maximization in isolation.

---

## 8. Policy Class and Learning Setup

### 8.1 Policy Class
- policy type: feedforward neural actor-critic policy
- stochastic / deterministic: stochastic during training, deterministic / mean-action during evaluation
- memoryless / recurrent: memoryless

### 8.2 RL Algorithm
- algorithm: PPO
- safe RL mechanism: none explicit in the current NavRL training loop; safety is encouraged via reward shaping and episode termination rather than a separate constrained optimization layer
- implementation library: TorchRL / TensorDict with OmniDrones on Isaac Sim

### 8.3 Training Budget
- steps / episodes: current default training budget is max_frame_num = 12e8 environment frames
- seeds: current Phase 0 uses seed = 0 for implementation bring-up; later evaluation will use multi-seed training and reporting.

This section is recorded here because the interpretation of CRE consistency depends on the admissible policy class \\( \Pi \\).

---

## 9. CRE Formal Objects

### 9.1 Specification
Define the CRE specification as
\[
\mathcal{S} = (E_{\mathrm{tr}}, \mathcal{D}, R, C, \Pi),
\]
where:
- \(E_{\mathrm{tr}}\) is the training environment distribution,
- \(\mathcal{D}\) is the deployment evaluation family,
- \(R\) is the implemented training reward specification,
- \(C = \{c_1, \dots, c_m\}\) is the constraint set,
- \(\Pi\) is the admissible policy class.

For deployment-level evaluation, we additionally define a task utility function
\[
U^E(\pi),
\]
which is used to evaluate task-level success independently of the exact shaping reward used for optimization.

In the current V0 indoor UAV setting, the default deployment utility is:
\[
U^E(\pi) = \mathrm{Succ}^E(\pi),
\]
where \(\mathrm{Succ}^E(\pi)\) is the success rate of policy \(\pi\) in environment family member \(E\).

### 9.2 Deployment-Consistent Policy
For any \(E \in \mathcal{D}\), define:

- task utility:
  \[
  U^E(\pi)
  \]
- episode-level violation probability for constraint \(c_j\):
  \[
  P_j^E(\pi)
  =
  \Pr_{\tau \sim (\pi,E)}\left(\exists t \le T:\ \mathbbm{1}_{c_j,t}=1\right)
  \]
- deployment instability:
  \[
  \Delta_{\mathcal{D}}(\pi)
  =
  \sup_{E,E' \in \mathcal{D}}
  \left[
  \alpha_U \left| U^E(\pi) - U^{E'}(\pi) \right|
  +
  \sum_{j=1}^{m} \alpha_j
  \left| P_j^E(\pi) - P_j^{E'}(\pi) \right|
  \right]
  \]
  where \(\alpha_U \ge 0\) and \(\alpha_j \ge 0\) are instability weights.

A policy \(\pi \in \Pi\) is deployment-consistent if it satisfies:

1. task utility above threshold across deployment environments:
   \[
   \inf_{E \in \mathcal{D}} U^E(\pi) \ge \tau_U
   \]

2. all constraint violation rates below tolerance:
   \[
   \sup_{E \in \mathcal{D}} P_j^E(\pi) \le \epsilon_j,
   \qquad j = 1,\dots,m
   \]

3. bounded deployment instability:
   \[
   \Delta_{\mathcal{D}}(\pi) \le \delta_{\mathrm{gen}}
   \]

Formal thresholds:
- \(\tau_U =\) minimum acceptable deployment utility
- \(\epsilon_j =\) maximum acceptable violation rate for constraint \(c_j\)
- \(\delta_{\mathrm{gen}} =\) maximum acceptable deployment instability

Recommended initial V0 interpretation:
- \(\tau_U\): minimum success rate under deployment evaluation
- \(\epsilon_j\): maximum episode-level violation probability
- \(\delta_{\mathrm{gen}}\): maximum allowed cross-environment performance-and-safety variation

Recommended initial V0 values for later calibration:
- \(\tau_U = 0.80\)
- \(\epsilon_1 = 0.05\) for collision
- \(\epsilon_2 = 0.10\) for safety-margin violation
- \(\epsilon_3 = 0.15\) for speed violation
- \(\epsilon_4 = 0.15\) for yaw-rate violation
- \(\epsilon_5 = 0.05\) for out-of-bounds
- \(\delta_{\mathrm{gen}} = 0.15\)

These values are placeholders for Phase 0 and should be refined after initial environment bring-up and baseline evaluation.

### 9.3 CRE Consistency
The specification \(\mathcal{S}\) is CRE-consistent if there exists at least one deployment-consistent policy:
\[
\exists \pi \in \Pi
\quad \text{s.t.} \quad
\pi \text{ satisfies the deployment-consistency conditions above.}
\]

Equivalently, define the feasible deployment-consistent policy set:
\[
\mathcal{F}(\mathcal{S})
=
\left\{
\pi \in \Pi :
\inf_{E \in \mathcal{D}} U^E(\pi) \ge \tau_U,\
\sup_{E \in \mathcal{D}} P_j^E(\pi) \le \epsilon_j,\ \forall j,\
\Delta_{\mathcal{D}}(\pi) \le \delta_{\mathrm{gen}}
\right\}.
\]

Then:
- \(\mathcal{S}\) is CRE-consistent iff \(\mathcal{F}(\mathcal{S}) \neq \varnothing\),
- \(\mathcal{S}\) is CRE-inconsistent iff \(\mathcal{F}(\mathcal{S}) = \varnothing\).

### 9.4 Consistency Margin
Define the consistency margin \(\rho(\mathcal{S})\) as
\[
\rho(\mathcal{S})
=
\sup_{\pi \in \Pi}
\min
\left\{
\inf_{E \in \mathcal{D}} U^E(\pi) - \tau_U,\ 
\epsilon_1 - \sup_{E \in \mathcal{D}} P_1^E(\pi),\
\dots,\
\epsilon_m - \sup_{E \in \mathcal{D}} P_m^E(\pi),\
\delta_{\mathrm{gen}} - \Delta_{\mathcal{D}}(\pi)
\right\}.
\]

Interpretation:
- \(\rho(\mathcal{S}) > 0\): consistent with slack
- \(\rho(\mathcal{S}) = 0\): on the boundary
- \(\rho(\mathcal{S}) < 0\): inconsistent

Role in the framework:
- the sign of \(\rho(\mathcal{S})\) determines whether the specification is feasible in principle,
- the magnitude of \(\rho(\mathcal{S})\) measures how robustly feasible or infeasible the specification is,
- later repair stages aim to increase \(\rho(\mathcal{S})\) with minimal specification edits.

Implementation note:
- in practice, \(\rho(\mathcal{S})\) will be estimated empirically using a finite candidate policy set, trained policies, or detector-assisted surrogates rather than computed exactly.

---

## 10. Diagnostic Decomposition

The definitions in Section 9 provide the global CRE consistency criterion.  
The purpose of the present section is different: to define structured diagnostic views that help explain *why* a specification may fail.

These diagnostic decompositions are not the formal definition of CRE consistency. Instead, they are observable or computable witnesses that guide:
- inconsistency reporting,
- root-cause attribution,
- repair proposal ranking.

### 10.1 C--R Inconsistency
Definition:
Reward structure encourages actions or trajectories that increase safety risk or violate constraints.

This failure mode is expected when high reward is systematically associated with:
- near-boundary states,
- actual constraint violations,
- aggressive motion patterns that reduce safety slack.

Planned witness / metrics:

#### (a) Reward--Violation Coupling
\[
\kappa_{CR}
=
\mathrm{Corr}\!\left(
r_t,\ 
\mathbbm{1}[m_{\mathrm{safe}}(s_t) < \delta_{\mathrm{crit}}]
\right)
\]
where:
- \(r_t\) is the instantaneous reward,
- \(m_{\mathrm{safe}}(s_t) = d_{\min}(s_t) - d_{\mathrm{safe}}\) is the safety-margin slack,
- \(\delta_{\mathrm{crit}} \ge 0\) defines the near-critical band.

Interpretation:
- larger positive \(\kappa_{CR}\) indicates that high reward tends to occur near safety-critical states.

#### (b) Boundary-Seeking Score
\[
B_{CR}
=
\Pr\!\left(
m_{\mathrm{safe}}(s_t) < \delta_{\mathrm{crit}}
\;\middle|\;
r_t \ge q_{0.9}(r)
\right)
\]
where \(q_{0.9}(r)\) is the 90th percentile of instantaneous reward.

Interpretation:
- high \(B_{CR}\) indicates that top-reward states are concentrated near the safety boundary.

#### (c) Goal-Progress vs Safety Tension
\[
T_{CR}
=
\mathrm{Corr}\!\left(
r_{goal,t},\ 
- m_{\mathrm{safe}}(s_t)
\right)
\]
Interpretation:
- positive \(T_{CR}\) suggests that stronger goal-aligned progress tends to coincide with smaller safety margins.

Planned use:
- C--R diagnostics will be used to identify whether reward shaping itself may be driving unsafe behavior, especially in narrow or cluttered indoor layouts.

### 10.2 E--C Inconsistency
Definition:
Training environments under-cover states where constraints become critical.

This failure mode is expected when:
- safety-relevant near-boundary states are rare in training,
- major constraints are seldom activated before deployment testing,
- the learned policy encounters boundary conditions in deployment that were not sufficiently represented during training.

Planned witness / metrics:

#### (a) Critical-State Coverage
For each constraint \(c_j\), define the critical-state set
\[
\mathcal{K}_j
=
\{s : m_j(s) < \delta_j^{\mathrm{crit}}\}
\]
and estimate its visitation under training and boundary-critical evaluation:
\[
\Gamma_{EC}^{(j)}
=
\frac{
\hat{\nu}_{\mathrm{tr}}(\mathcal{K}_j)
}{
\hat{\nu}_{\mathrm{bc}}(\mathcal{K}_j) + \varepsilon
}
\]
where:
- \(\hat{\nu}_{\mathrm{tr}}\) is the empirical visitation frequency under training environments,
- \(\hat{\nu}_{\mathrm{bc}}\) is the empirical visitation frequency under boundary-critical environments.

Interpretation:
- low \(\Gamma_{EC}^{(j)}\) suggests under-coverage of critical states during training.

#### (b) Constraint Activation Frequency
\[
A_j^{\mathrm{tr}}
=
\Pr_{E_{\mathrm{tr}}}\!\left(m_j(s_t) < \delta_j^{\mathrm{crit}}\right)
\]
Interpretation:
- if \(A_j^{\mathrm{tr}}\) is near zero for an important constraint, that constraint is effectively inactive during training.

#### (c) Critical-State Diversity
Let the critical states for \(c_j\) be clustered into bins or latent regions. Define:
\[
H_j
=
-\sum_k p_{j,k}\log p_{j,k}
\]
where \(p_{j,k}\) is the empirical fraction of visits to the \(k\)-th critical-state cluster.

Interpretation:
- low diversity means that even when a constraint becomes active, the training distribution may cover only a narrow subset of critical situations.

Planned use:
- E--C diagnostics will be used to justify boundary-critical scenario injection and curriculum oversampling.

### 10.3 E--R Inconsistency
Definition:
Environment structure allows reward shortcuts or unstable reward proxies that do not transfer.

This failure mode is expected when:
- reward remains high while task utility or safety degrades under shifted environments,
- the policy exploits environment-specific regularities,
- the training reward does not track real deployment success robustly.

Planned witness / metrics:

#### (a) Deployment Utility Gap
\[
\Delta_U(\pi)
=
\max_{E \in \mathcal{D}_{\mathrm{shift}}}
\left|
U^E(\pi) - U^{E_{\mathrm{tr}}}(\pi)
\right|
\]

Interpretation:
- large \(\Delta_U\) indicates poor transfer of task-level performance.

#### (b) Deployment Reward Gap
\[
\Delta_R(\pi)
=
\max_{E \in \mathcal{D}_{\mathrm{shift}}}
\left|
J_R^E(\pi) - J_R^{E_{\mathrm{tr}}}(\pi)
\right|
\]
where
\[
J_R^E(\pi)
=
\mathbb{E}_{\tau \sim (\pi,E)}
\left[
\sum_{t=0}^{T} \gamma^t r_t
\right].
\]

Interpretation:
- large \(\Delta_R\) indicates that the reward itself is unstable under environment shift.

#### (c) Reward--Utility Decoupling
\[
D_{ER}(\pi)
=
\max_{E \in \mathcal{D}_{\mathrm{shift}}}
\left|
\frac{
J_R^E(\pi) - J_R^{E_{\mathrm{tr}}}(\pi)
}{
|J_R^{E_{\mathrm{tr}}}(\pi)| + \varepsilon
}
-
\frac{
U^E(\pi) - U^{E_{\mathrm{tr}}}(\pi)
}{
|U^{E_{\mathrm{tr}}}(\pi)| + \varepsilon
}
\right|
\]

Interpretation:
- large \(D_{ER}\) indicates that reward variation and task-performance variation are not aligned, which is a strong sign of reward proxy or shortcut behavior.

#### (d) Intervention Sensitivity
Let \(T\) denote a controlled environment intervention, such as:
- increased sensor noise,
- shifted start distribution,
- altered obstacle placement pattern,
- changed free-space topology.

Define:
\[
I_{ER}(\pi)
=
\max_{T \in \mathcal{T}}
\left|
U^{T(E_{\mathrm{tr}})}(\pi) - U^{E_{\mathrm{tr}}}(\pi)
\right|
\]

Interpretation:
- large intervention sensitivity suggests brittle dependence on environment-specific regularities.

Planned use:
- E--R diagnostics will be used to justify structured domain randomization and reward repair.

### 10.4 Diagnostic Role in the Framework
The diagnostic decomposition in this section serves four purposes:

1. to provide interpretable evidence for the global inconsistency claim in Section 9,
2. to distinguish likely root causes across reward, environment, and safety interactions,
3. to rank candidate repairs,
4. to evaluate whether a repair reduces the intended type of inconsistency.

Operational note:
- Section 9 defines whether a specification is globally feasible in principle,
- Section 10 defines how the framework detects and explains likely failure modes in practice.

---

## 11. Repair Space

### 11.1 Allowed Repair Types
The system is allowed to modify the specification only within a controlled and auditable repair space.

The system is allowed to modify:
- reward weights,
- safety-related reward terms,
- scenario sampling distribution,
- environment randomization range,
- boundary-critical scenario frequency,
- reward component scaling,
- addition of explicit terminal success or collision reward terms,
- replacement of constant living reward with a time penalty,
- clipping or normalization of reward terms,
- training environment mixture proportions across nominal / boundary-critical / shifted scenarios.

Allowed reward-space edits include:
- reweighting \(r_{goal}\), \(r_{base}\), \(r_{safe,static}\), \(r_{safe,dynamic}\), \(p_{smooth}\), \(p_{height}\),
- adding a boundary-aware safety penalty,
- replacing the constant step reward with a negative per-step time penalty,
- adding explicit success bonus and/or collision penalty terms,
- clipping or normalizing unstable shaping terms such as log-distance rewards.

Allowed environment-space edits include:
- increasing the sampling frequency of safety-critical layouts,
- increasing bottleneck frequency,
- narrowing the bottleneck-width distribution,
- increasing obstacle density within a physically valid range,
- expanding sensor-noise randomization ranges,
- modifying the sampling distribution of start and goal states,
- enabling structured domain randomization over topology, obstacle placement, and sensing conditions.

Allowed constraint-adjacent edits are restricted to:
- changing detector thresholds used for near-violation analysis,
- changing curriculum exposure to critical states,
- refining soft safety shaping around existing hard constraints.

The system is **not** allowed to silently modify the hard constraint semantics themselves unless such a change is explicitly approved and versioned as a specification revision.

### 11.2 Forbidden or Restricted Repairs
The system must not:
- change the task goal semantics,
- remove core safety constraints without explicit approval,
- introduce non-physical scenarios,
- change the environment in a way that invalidates the indoor obstacle-avoidance task,
- alter workspace geometry beyond physically meaningful indoor layouts,
- make obstacles unrealistically sparse merely to inflate apparent safety,
- increase success by trivially shortening the task or collapsing the start-goal distance distribution,
- redefine success conditions without explicit approval,
- suppress violations only through logging or evaluation changes,
- disable critical sensors or constraints solely to improve training stability,
- introduce reward terms that no longer correspond to interpretable navigation objectives.

Restricted repairs requiring explicit approval include:
- modification of hard safety thresholds \(d_{\mathrm{safe}}, v_{\max}, \omega_{\max}\),
- removal of any existing major or critical constraint,
- switching from planar / 2.5D abstraction to a substantially different dynamics model,
- replacing the current policy class \(\Pi\) with a materially more expressive class,
- changing the deployment evaluation family \(\mathcal{D}\).

Principle:
- repairs may improve specification consistency,
- but they must preserve task intent, safety meaning, and physical plausibility.

### 11.3 Initial Repair Library
The initial repair library is intentionally limited to a small set of interpretable and implementable operations.

#### 11.3.1 C--R Repair
- reward reweighting,
- boundary-aware penalty injection,
- replacement of constant living reward with time penalty,
- explicit terminal success bonus,
- explicit terminal collision penalty,
- clipping / normalization of unstable safety shaping terms.

Recommended initial forms:
- reward reweighting:
  \[
  R' = \sum_i w_i' r_i
  \]
  with edited weights \(w_i'\);
- boundary-aware penalty injection:
  \[
  R' = R - \lambda_{\mathrm{bdry}} \max(0, d_{\mathrm{warn}} - d_{\min})
  \]
- collision penalty insertion:
  \[
  R' = R - \lambda_{\mathrm{col}} \, \mathbbm{1}[\texttt{collision\_flag}=1]
  \]
- time penalty replacement:
  \[
  r_{base}' = -\lambda_{\mathrm{time}}
  \]
  instead of a constant positive living reward.

#### 11.3.2 E--C Repair
- critical scenario injection,
- curriculum oversampling,
- start-state redistribution toward low-clearance states,
- goal redistribution toward bottleneck-crossing tasks,
- increased obstacle clustering near likely shortest paths.

Recommended initial forms:
- critical scenario injection:
  increase the sampling ratio of boundary-critical layouts in the training distribution;
- curriculum oversampling:
  expose the policy to low-clearance scenarios more frequently during later training stages;
- constraint-specific replay / evaluation emphasis:
  if a major constraint is rarely activated in training, increase the frequency of environments where its critical state set is visited.

#### 11.3.3 E--R Repair
- structured domain randomization,
- topology randomization,
- sensor-noise randomization,
- start / goal distribution broadening,
- obstacle placement pattern diversification.

Recommended initial forms:
- structured domain randomization over:
  - obstacle count,
  - obstacle placement pattern,
  - local bottleneck width,
  - sensor noise,
  - initial heading,
  - free-space connectivity;
- shifted-layout augmentation:
  introduce layout families not dominant in the nominal training distribution.

#### 11.3.4 Repair Candidate Ranking
Repair candidates are ranked according to:
1. expected improvement in \(\Psi_{\mathrm{CRE}}\),
2. expected safety improvement,
3. expected reduction in diagnostic witness values for the targeted inconsistency type,
4. edit minimality,
5. task-intent preservation.

#### 11.3.5 Repair Versioning
Every accepted repair must be versioned and logged with:
- repair ID,
- source specification ID,
- edited components,
- rationale,
- target inconsistency type,
- expected effect,
- measured post-repair effect.

---

## 12. Acceptance Rules

### 12.1 Detector Acceptance
A diagnostic module is considered usable if:
- it produces stable outputs across seeds,
- it distinguishes clean and injected inconsistent specifications,
- it provides interpretable evidence.

More specifically, a detector is accepted for Phase 1/2 use if it satisfies all of the following:

#### 12.1.1 Stability
For repeated runs under the same specification family and comparable seeds, the detector should produce:
- consistent ranking of the dominant inconsistency type,
- low variance in the main diagnostic score,
- qualitatively consistent explanations.

Recommended initial acceptance thresholds:
- coefficient of variation of the main detector score \(< 0.20\),
- dominant inconsistency type agreement across seeds \(\ge 80\%\).

#### 12.1.2 Discrimination
The detector should separate:
- clean specifications,
- C--R injected specifications,
- E--C injected specifications,
- E--R injected specifications.

Recommended initial acceptance threshold:
- the injected inconsistency type should be ranked as top-1 or top-2 in at least \(80\%\) of test runs.

#### 12.1.3 Interpretability
The detector output must include:
- issue type,
- supporting metrics,
- affected reward / constraint / environment components,
- severity estimate,
- at least one interpretable explanation tied to logged variables.

A detector failing to provide interpretable evidence is not accepted even if its raw score is numerically predictive.

### 12.2 Repair Acceptance
A repair is accepted only if:
- overall consistency score improves,
- safety does not degrade,
- task performance drop is bounded,
- the specification edit is judged acceptable.

Formal acceptance rule:
Given the original specification \(\mathcal{S}\) and repaired specification \(\mathcal{S}'\), accept the repair if

\[
\Psi_{\mathrm{CRE}}(\mathcal{S}') - \Psi_{\mathrm{CRE}}(\mathcal{S}) > 0
\]

and

\[
\mathrm{Safety}(\mathcal{S}') \ge \mathrm{Safety}(\mathcal{S}),
\]

and

\[
U_{\mathrm{nom}}(\mathcal{S}') \ge U_{\mathrm{nom}}(\mathcal{S}) - \epsilon_{\mathrm{perf}},
\]

and

\[
d_{\mathrm{spec}}(\mathcal{S}, \mathcal{S}') \le \eta_{\mathrm{edit}},
\]

where:
- \(\Psi_{\mathrm{CRE}}\) is the overall consistency score,
- \(\mathrm{Safety}\) is the chosen safety summary metric,
- \(U_{\mathrm{nom}}\) is nominal deployment utility,
- \(\epsilon_{\mathrm{perf}}\) is the maximum tolerated nominal performance drop,
- \(d_{\mathrm{spec}}\) is the specification edit distance,
- \(\eta_{\mathrm{edit}}\) is the maximum acceptable edit size.

Recommended initial operational definitions:
- \(\mathrm{Safety}\): negative weighted violation score or equivalently inverse violation burden,
- \(U_{\mathrm{nom}}\): nominal success rate,
- \(\epsilon_{\mathrm{perf}} = 0.05\),
- \(\eta_{\mathrm{edit}}\): chosen relative to allowed reward/environment edit ranges.

Additional targeted acceptance condition:
If the repair is targeted at inconsistency type \(X \in \{\mathrm{C\!-\!R}, \mathrm{E\!-\!C}, \mathrm{E\!-\!R}\}\), then the corresponding witness must improve:
- C--R repair:
  \[
  B_{CR}(\mathcal{S}') < B_{CR}(\mathcal{S})
  \quad \text{or} \quad
  \kappa_{CR}(\mathcal{S}') < \kappa_{CR}(\mathcal{S})
  \]
- E--C repair:
  \[
  \Gamma_{EC}^{(j)}(\mathcal{S}') > \Gamma_{EC}^{(j)}(\mathcal{S})
  \]
  for at least one major constraint \(c_j\)
- E--R repair:
  \[
  \Delta_U(\mathcal{S}') < \Delta_U(\mathcal{S})
  \quad \text{and/or} \quad
  D_{ER}(\mathcal{S}') < D_{ER}(\mathcal{S})
  \]

A repair is rejected if any of the following occurs:
- collision rate increases materially,
- success rate drops beyond \(\epsilon_{\mathrm{perf}}\),
- the repair relies on non-physical environment edits,
- the repaired specification violates the forbidden-repair rules in Section 11.2.

---

## 13. Evaluation Plan

### 13.1 Specifications to Test
The following specifications will be tested:

- clean specification
- C--R inconsistent specification
- E--C inconsistent specification
- E--R inconsistent specification
- optionally, a mixed inconsistency specification combining two or more inconsistency types

Definitions:
- **clean specification**: the baseline indoor UAV obstacle-avoidance specification judged reasonable by design;
- **C--R inconsistent specification**: a specification in which reward design is intentionally modified to increase conflict with safety constraints;
- **E--C inconsistent specification**: a specification in which training environments under-cover constraint-critical states;
- **E--R inconsistent specification**: a specification in which the reward can be exploited through environment-specific regularities or fails to transfer under shifted environments.

Recommended initial injection strategies:
- C--R injection:
  - increase progress weight,
  - retain weak explicit collision shaping,
  - maintain low boundary penalty;
- E--C injection:
  - reduce critical-scenario sampling,
  - remove low-clearance layouts from training;
- E--R injection:
  - narrow training topology distribution,
  - reduce environmental diversity,
  - increase reliance on layout-specific regularities.

### 13.2 Evaluation Environments
The following environment families will be used:

- nominal,
- boundary-critical,
- shifted,
- optional mixed-stress environments for later robustness analysis.

#### 13.2.1 Nominal
Used to evaluate:
- standard generalization to held-out in-distribution layouts,
- nominal task utility,
- baseline training stability.

#### 13.2.2 Boundary-Critical
Used to evaluate:
- safety-margin behavior,
- major-constraint activation,
- E--C under-coverage,
- C--R boundary-seeking risk.

#### 13.2.3 Shifted
Used to evaluate:
- deployment fragility,
- reward-transfer stability,
- E--R inconsistency,
- sensitivity to topology and sensing changes.

#### 13.2.4 Optional Mixed-Stress Set
Later versions may include environments that combine:
- narrow bottlenecks,
- higher sensor noise,
- shifted topology,
to evaluate robustness under simultaneously adverse conditions.

### 13.3 Core Metrics
The following core metrics will be tracked:

#### 13.3.1 Task Utility
- success rate,
- average final goal distance,
- path efficiency / trajectory length ratio [optional],
- average episode length.

#### 13.3.2 Safety
- collision rate,
- out-of-bounds rate,
- safety-margin violation rate,
- minimum obstacle distance statistics,
- near-violation step ratio,
- weighted violation score.

#### 13.3.3 Reward and Optimization
- average episode return,
- reward component sums,
- reward variance,
- reward--utility decoupling.

#### 13.3.4 Transfer and Robustness
- transfer gap,
- deployment utility gap \(\Delta_U\),
- deployment reward gap \(\Delta_R\),
- intervention sensitivity \(I_{ER}\).

#### 13.3.5 CRE Diagnostics
- CRE score \(\Psi_{\mathrm{CRE}}\),
- C--R witness values (\(\kappa_{CR}, B_{CR}, T_{CR}\)),
- E--C witness values (\(\Gamma_{EC}^{(j)}, A_j^{\mathrm{tr}}, H_j\)),
- E--R witness values (\(\Delta_U, \Delta_R, D_{ER}, I_{ER}\)),
- consistency-margin surrogate / empirical feasibility indicator [TODO: depending on implementation].

#### 13.3.6 Repair Evaluation
- pre-repair vs post-repair metric differences,
- repair edit cost,
- target witness improvement,
- safety improvement,
- nominal utility retention.

### 13.4 Evaluation Protocol
Recommended initial protocol:
- train on the designated training environment distribution,
- evaluate on nominal, boundary-critical, and shifted environment families,
- report per-seed and aggregated statistics,
- compare:
  - original specification,
  - repaired specification,
  - optional partial-repair baselines.

Recommended reporting:
- mean ± standard deviation over seeds,
- metric breakdown by environment family,
- diagnostic reports for representative failure cases.

---

## 14. Deliverables for Phase 0 Freeze

The following items must be fixed before entering Phase 1:
1. task definition,
2. environment family definition,
3. constraint list,
4. reward decomposition,
5. allowed repair space,
6. preliminary CRE formal objects,
7. planned evaluation metrics.

In addition, the following implementation-facing artifacts should exist in at least draft form:
8. initial environment configuration template,
9. logging field specification,
10. detector metric draft,
11. clean / injected specification plan,
12. reward-version record for the current NavRL implementation.

Minimum acceptance condition for Phase 0 freeze:
- all Sections 1--14 are internally consistent,
- no major ambiguity remains in task semantics, constraints, or reward interpretation,
- the environment family and metric definitions are sufficiently concrete for Phase 1 implementation,
- at least one clean and one injected specification can be instantiated from the written design.

Freeze decision:
- Approved / Not Approved
- Reviewer: [TODO]
- Date: [TODO]

If not approved, unresolved blocking items must be listed explicitly before Phase 1 begins.

---

## 15. Open Questions
List unresolved issues that are allowed to remain open after Phase 0:

1. **Height-Dimension Consistency**
   - Is the V0 system finalized as a strictly planar navigation abstraction, or as a 2.5D abstraction with retained altitude-band shaping?
   - This affects whether the current height penalty remains active in the baseline specification.

2. **Detector Quantification Details**
   - Which witness will serve as the primary detector statistic for each inconsistency type in Phase 1?
   - In particular, the final prioritization among \(\kappa_{CR}\), \(B_{CR}\), \(\Gamma_{EC}^{(j)}\), and \(D_{ER}\) is not yet frozen.

3. **Acceptance Threshold Calibration**
   - The initial values of \(\tau_U\), \(\epsilon_j\), \(\delta_{\mathrm{gen}}\), \(\epsilon_{\mathrm{perf}}\), and \(\eta_{\mathrm{edit}}\) are provisional.
   - These thresholds must be calibrated after initial simulator bring-up and baseline rollouts.

4. **Dynamic Obstacle Scope**
   - The current reward implementation supports dynamic-obstacle terms, but the V0 indoor avoidance benchmark may initially use only static obstacles.
   - The exact role of dynamic obstacles in early CRE validation remains open.

5. **Baseline Expansion**
   - Phase 0 freezes PPO as the initial baseline, but later stages may introduce explicit constrained RL baselines for comparison.
   - The timing and scope of such additions are not yet frozen.

6. **Exact Empirical Estimation of \(\rho(\mathcal{S})\)**
   - The formal consistency margin is defined in Section 9, but its practical estimator in large neural policy spaces is not yet finalized.
   - Early stages may rely on empirical feasibility surrogates rather than direct approximation of \(\rho(\mathcal{S})\).

Allowed principle:
- open questions may remain after Phase 0,
- but they must not block:
  - environment implementation,
  - logging implementation,
  - clean vs injected specification construction,
  - initial detector bring-up.