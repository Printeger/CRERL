# INTERFACES.md — 跨模块接口契约

## 图例
- ✅ 已实现（新版）— 接口经过验证，可直接依赖
- 🔶 旧版参考 — 接口存在于旧版代码中，**不保证与新版需求兼容，开发时需先验证，可重构**
- ❌ 待实现 — 尚未实现，需从零创建

> ⚠️ **当前状态**：代码库中**不存在任何已验证的新版 CRE 接口（✅）**。所有 CRE 相关接口均为旧版（🔶）或尚不存在（❌）。旧版 CLI 脚本（`run_*_audit.py`）已全部删除，其接口签名仅作历史参考，新版接口需根据 `doc/CRE_v4.pdf` 重新设计。

---

## 1. 环境 → Collector（TorchRL EnvBase）— RL 框架接口，非 CRE

`NavigationEnv`（经 `TransformedEnv` 包装）暴露 TorchRL `EnvBase` 接口给 `SyncDataCollector`。这是 RL 框架本身的接口，与 CRE 分析无关。

| 方法 / 属性 | 类型 | 状态 |
|------------|------|------|
| `reset()` | `→ TensorDict` | ✅ RL 框架已实现 |
| `step(action: TensorDict)` | `→ TensorDict` | ✅ RL 框架已实现 |
| `observation_spec` | `CompositeSpec` | ✅ RL 框架已实现 |
| `action_spec` | `BoundedTensorSpec [-2, 2]^3` | ✅ RL 框架已实现 |
| `enable_render(bool)` | 副作用 | ✅ RL 框架已实现 |

**TensorDict 中的观测 keys（旧版，需验证是否与新版 CRE 需求匹配）：**
```
("agents", "observation", "state")             # [num_envs, state_dim]
("agents", "observation", "lidar")             # [num_envs, 36, 4]
("agents", "observation", "dynamic_obstacle")  # [num_envs, N, obs_dim]
("agents", "stats", "done_type")               # [num_envs, 1]  int: 0/1/2/3/4
("done")                                       # [num_envs, 1]  bool
("terminated")                                 # [num_envs, 1]  bool
("truncated")                                  # [num_envs, 1]  bool
```

---

## 2. Collector → PPO — RL 框架接口，非 CRE

| 字段 | Shape | 状态 |
|------|-------|------|
| `("agents", "observation", *)` | `[T, num_envs, *]` | ✅ RL 框架已实现 |
| `("agents", "action")` | `[T, num_envs, 3]` | ✅ RL 框架已实现 |
| `("agents", "reward")` | `[T, num_envs, 1]` | ✅ RL 框架已实现 |
| `("next", "done")` | `[T, num_envs, 1]` | ✅ RL 框架已实现 |

`PPO.train(data: TensorDict) → Dict[str, float]` 返回损失统计。

---

## 3. 训练循环 → CRE 日志（旧版参考）

> 🔶 以下接口来自旧版 `training_log_adapter.py` + `train.py`，已删除的旧版 CRE hooks 曾使用此模式。新版 CRE 日志接入方式需根据 Phase 8（Integration）重新设计。

```python
# 旧版模式（仅供参考）
cre_log_adapter.process_batch(data)          # 每个训练迭代
cre_log_adapter.flush_open_episodes(...)     # 训练结束
cre_summary = aggregate_log_directory(...)   # 聚合
run_acceptance_check(run_dir)                # 验收
```

---

## 4. CRE 日志 → 磁盘（旧版参考）

> 🔶 以下文件格式来自旧版实现，新版开发时需先根据 CRE_v4.pdf 确认格式是否沿用。

| 文件 | 旧版 Schema | 状态 |
|------|------------|------|
| `episodes/` | `cre_runtime_log.v1`，每 episode 一个 JSON | 🔶 旧版参考 |
| `manifest.json` | 运行元数据 | 🔶 旧版参考 |
| `summary.json` | 聚合指标 | 🔶 旧版参考 |
| `acceptance_report.json` | acceptance 结果 | 🔶 旧版参考 |

---

## 5. 新版 CRE 分析接口（待设计）

> ❌ 以下接口**尚不存在**，需根据 `doc/CRE_v4.pdf` 重新设计。所有签名在实现前须先写入本文件，经确认后再动手编码。

### Phase 0 — Core Data Schemas
```python
# analyzers/diag_report.py

@dataclass(frozen=True)
class NLInput:
    r_desc: str
    c_desc: str
    e_desc: str
    metadata: dict[str, Any]
```
# 输入：无；这是 Part II §1.2 定义的 canonical 原始描述封装
# 输出：无；作为 strict PDF mode 下 M1 `parse_nl_input` 的 canonical 输入
# 约束：`r_desc` / `c_desc` / `e_desc` 为必填非空字符串；`metadata` 为 free-form 透传字典
状态：[FROZEN] ⚠️ NLInput 签名已冻结；strict PDF mode 下不得再裁掉其 `NLInput -> SpecS` 主链路语义

```python
@dataclass(frozen=True)
class Constraint:
    k_id: str
    predicate: Callable[[State, Action], int]
    sigma: Literal["hard", "soft", "info"]
    scope: Literal["instantaneous", "episodic", "cumulative"]
    zeta: float | None
    lam: float | None
    delta: float
```
# 输入：无；这是 Part II §1.2 p.22 定义的 canonical 约束数据结构
# 输出：无；作为 `SpecS.C` 的成员类型，被 M2/M4/M7/M8 只读消费
# 约束：`k_id` 为唯一约束 ID；`predicate` 满足 `O_j: S×A -> {0,1}`；
#       `sigma ∈ {"hard","soft","info"}`；`scope ∈ {"instantaneous","episodic","cumulative"}`；
#       `zeta` 仅在 `sigma=="soft"` 时要求非空；`lam` 为 soft constraint 可选惩罚权重；
#       `delta` 对应覆盖阈值 `delta_j > 0`
状态：[FROZEN] ⚠️ Constraint 签名已冻结；当前实现应与该 dataclass 接口保持一致

```python
@dataclass(frozen=True)
class RewardDAG:
    nodes: list[RewardTerm]
    edges: list[tuple[str, str]]
```
# 输入：无；这是 Part II §1.2 p.22 定义的 canonical reward DAG 结构
# 输出：无；作为 `SpecS.R` 的成员类型，被后续 M2/M5/M7 只读消费
# 约束：`nodes` 为 `list[RewardTerm]`；`edges` 为 `(parent_id, child_id)` 的字符串二元组列表；
#       运行时实现需将容器归一化为只读存储，禁止 in-place mutation
状态：[FROZEN] ⚠️ RewardDAG 签名已冻结；当前实现应与该 dataclass 接口保持一致

```python
@dataclass(frozen=True)
class SpecS:
    spec_id: str
    E_tr: TrainingEnvDistribution
    E_dep: list[Environment]   # [e_0, e_1, ..., e_n]; e_0 is nominal
    R: RewardDAG
    C: list[Constraint]        # length m
    Pi: PolicyClass
    version: int = 0
```
# 输入：无；这是跨模块共享的 canonical schema
# 输出：无；作为后续 M1/M2/M4/M7/M8 的只读输入/输出成员类型
# 约束：`SpecS` 必须为 `@dataclass(frozen=True)`，repair 流程只能返回新的 `SpecS`
# 备注：`TrainingEnvDistribution`、`Environment`、`RewardDAG`、`Constraint`、`PolicyClass`
#       由 `analyzers/diag_report.py` 同文件定义，供 `SpecS` 类型标注直接引用
状态：[FROZEN] ⚠️ SpecS 签名已冻结，待实现

```python
@dataclass(frozen=True)
class AmbiguityFlag:
    flag_type: Literal[
        "UNDEFINED_THRESHOLD",
        "MISSING_ENV_SCOPE",
        "REWARD_UNDERSPECIFIED",
        "CONSTRAINT_OVERLAP",
        "TEMPORAL_AMBIGUITY",
    ]
    location: str
    impact_score: float
```
# 输入：无；这是 Part II §1.2 p.22 定义的 canonical ambiguity marker
# 输出：无；作为 M1 输出中的 `list[AmbiguityFlag]` 成员类型，被后续 `DiagReport.flags`
#       和追溯流程只读消费
# 约束：`flag_type` 必须属于 PDF 给出的五个 canonical 枚举值；`location` 为 `SpecS`
#       内的 dot-separated JSON path；`impact_score` 为估计的 `|DeltaPsiCRE|` reduction，
#       取值必须在 [0, 1]
# 备注：虽然 PDF 伪代码写作 `@dataclass`，但本项目按 `REFACTOR_ROADMAP.md` Phase 0
#       统一冻结所有 core schema，因此 `AmbiguityFlag` 在实现层固定为
#       `@dataclass(frozen=True)` passive schema
状态：[FROZEN] ⚠️ AmbiguityFlag 签名已冻结；strict PDF mode 下由 M1 `parse_nl_input` / ambiguity escalation 主链路生成

> 说明：`D-I21` 已恢复 strict PDF canonical path，`NLInput` 与 `AmbiguityFlag`
> 不再只是被动保留的数据结构，而是 M1 / LLM-α 主链路的 canonical 输入输出。

```python
@dataclass(frozen=True)
class DiscrepancyRecord:
    ...
```
# 输入：无；这是 Part II §1.2 pp.22–23 中被 `DiagReport.discrepancy` 引用的依赖类型
# 输出：无；当前仅保留 passive placeholder schema，不在 Phase 0 推断其内部字段
# 约束：本 PDF 摘录只给出类型名，未内联字段；因此实现层先冻结类型存在性，
#       后续若在更完整 PDF 章节中发现字段定义，再通过独立接口决策扩展
状态：[FROZEN] ⚠️ DiscrepancyRecord 作为 DiagReport 依赖类型已冻结；当前实现为 passive placeholder

```python
@dataclass(frozen=True)
class DiagReport:
    spec_id: str
    timestamp: str
    phi_cr2: float
    phi_ec_bar: float
    phi_er3: float
    phi_cr1: float | None
    phi_ec2: float | None
    phi_ec3: float | None
    phi_ec_per_j: list[float] | None
    phi_er1: float | None
    phi_er2: float | None
    kappa_cr: float | None
    gamma_ec: float | None
    delta_er: float | None
    psi_cre: float
    ci_95: dict[str, tuple[float, float]]
    flags: list[str]
    discrepancy: list[DiscrepancyRecord] | None
    failure_hypothesis: str | None
    repair_targets: list[str] | None
```
# 输入：无；这是 Part II §1.2 pp.22–23 定义的 canonical 诊断报告结构
# 输出：无；作为后续 M2/M3/M4/M5/M7/M8 的共享只读报告载体
# 约束：`DiagReport` 必须为 `@dataclass(frozen=True)`；canonical reporters `phi_cr2`、
#       `phi_ec_bar`、`phi_er3` 与 composite `psi_cre` 在最终实现中必须满足 [0,1]；
#       supplementary / enhanced reporters 在 computation skipped 时可为 `None`；
#       `ci_95` 为 `reporter_name -> (lo, hi)` 映射；`flags` 为 error/warning code 列表；
#       `discrepancy` 在未运行 Stage III 时可为 `None`；`failure_hypothesis` /
#       `repair_targets` 在未运行 M4 时可为 `None`
# 备注：`discrepancy`、`failure_hypothesis`、`repair_targets` 虽分别由 Stage III / M4
#       等后续阶段填充，但仍属于 PDF canonical report schema，必须在 Phase 0 先冻结，
#       防止后续模块自创替代报告结构
状态：[FROZEN] ⚠️ DiagReport 签名已冻结；当前实现先冻结字段布局，字段级 contract tests 与校验逻辑待下一步补齐

```python
@dataclass(frozen=True)
class RepairProposal:
    proposal_id: str
    spec_prime: SpecS
    operator_class: str
    declared_side_effects: dict[str, str]
    semantic_justification: str
    predicted_delta_psi: float | None
    rough_delta_psi: float | None
```
# 输入：无；这是 Part II §1.2 p.23 定义的 canonical repair proposal schema
# 输出：无；作为 M7 repair generation 的候选提案数据结构，被 M7/M8/pipeline 只读消费
# 约束：`RepairProposal` 必须为 `@dataclass(frozen=True)`；`proposal_id` 为 UUID 字符串；
#       `spec_prime` 必须是修复后候选 `SpecS`；`operator_class` 必须来自 `V_R`
#       operator vocabulary；`declared_side_effects` 为 `dim -> description` 的字符串映射；
#       `semantic_justification` 最大 200 tokens；`predicted_delta_psi` 为 LLM 预测改进值，
#       `rough_delta_psi` 由 M7.rank_proposals Stage 1 回填，二者在未计算时可为 `None`
状态：[FROZEN] ⚠️ RepairProposal 签名已冻结；下一步可直接进入合约测试与字段级校验

```python
@dataclass(frozen=True)
class AcceptanceVerdict:
    accepted: bool
    c1_pass: bool
    c2_pass: bool
    c3_pass: bool
    c4_pass: bool
    s_sem: float
    intent_preserved: bool
    rejection_feedback: str | None
```
# 输入：无；这是 Part II §1.2 p.23 定义的 canonical acceptance verdict schema
# 输出：无；作为 M8 acceptance / validation 的标准结果数据结构，被 M8/pipeline 只读消费
# 约束：`AcceptanceVerdict` 必须为 `@dataclass(frozen=True)`；`accepted`、`c1_pass`、
#       `c2_pass`、`c3_pass`、`c4_pass`、`intent_preserved` 必须是布尔值；`s_sem`
#       必须是实数且落在 `[0,1]`；`rejection_feedback` 为 `str | None`，在 rejection
#       场景下由 M8 填充语义或验收反馈
状态：[FROZEN] ⚠️ AcceptanceVerdict 签名已冻结；下一步可直接进入合约测试与字段级校验

```python
# analyzers/cfg.py
@dataclass(frozen=True)
class CFGSchema:
    eta_flag: float = 0.15
    llm_retry_limit: int = 3
    delta_j_default: float = 0.50
    n_ref_traj: int = 500
    n_mc_kj: int = 1000
    critical_region_radius: float = 0.10
    ec_aggregation_mode: Literal["mean", "min"] = "mean"
    eps_stab: float = 1e-6
    enhanced_estimators_enabled: bool = True
    eta_disc: float = 0.15
    tau_low: float = 0.30
    tau_high: float = 0.70
    lambda_expand: float = 0.50
    n_rechk: int = 1
    f_steepness: float = 8.0
    f_inflection: float = 0.50
    w_cr: float = 0.333
    w_ec: float = 0.333
    w_er: float = 0.334
    b_bootstrap: int = 1000
    k_detect: float = 1.5
    k_alarm: float = 3.0
    tau_alarm_psi: float = 0.75
    k_proposals: int = 3
    eta_edit: float = 0.20
    n_rank_episodes: int = 50
    eps_rank: float = 0.02
    ranking_mode: str = "rollout_first"
    tau_sem: float = 0.80
    eps_perf: float = 0.05
    n_max_iterations: int = 5

CFG: CFGSchema
```
# 输入：无；这是 Part II §1.3 Table 4 pp.23–24 定义的全局配置常量集合
# 输出：模块级 singleton `CFG`，在 pipeline 启动时加载；所有字段允许后续被环境变量或 YAML
#       配置覆盖，但默认值语义必须与 Table 4 保持一致
# 约束：`CFG` 不得被其他模块用第二套 dataclass / dict / Hydra 子结构替代；M5 与
#       `pipeline/orchestrator.py` 必须复用这一 singleton；启动时必须验证
#       `abs(w_cr + w_ec + w_er - 1.0) < 1e-9` 且三者均严格大于 0，违反时抛
#       `CONFIG_WEIGHT_SUM_ERROR`
# 备注：字段分组对应 M1 ambiguity detection、M2/M3 estimators、Stage III discrepancy
#       protocol、M5 composite scoring、M7 repair generation、M8 acceptance；本接口当前只冻结
#       字段布局与默认值，不在此阶段规定具体覆盖加载机制的实现细节
状态：[FROZEN] ⚠️ CFG 签名已冻结；后续 `analyzers/m5.py` 与 `pipeline/orchestrator.py` 必须复用同一 `CFG` singleton

```python
# analyzers/errors.py
CREErrorSeverity = Literal["HALT", "WARN"]

class CREErrorCode:
    SPEC_PARSE_FAILURE: ClassVar[str]
    NULL_REWARD: ClassVar[str]
    EMPTY_CONSTRAINT_SET: ClassVar[str]
    EMPTY_ENV_SET: ClassVar[str]
    AMBIGUITY_UNRESOLVABLE: ClassVar[str]
    PRECHECK_TYPE_MISMATCH: ClassVar[str]
    PRECHECK_DOMAIN_TRIVIAL: ClassVar[str]
    PRECHECK_COVERAGE_INSUFFICIENT: ClassVar[str]
    PRECHECK_SOFT_NO_TOLERANCE: ClassVar[str]
    DEGENERATE_CR1_VAR: ClassVar[str]
    BOUNDARY_BASELINE_DEGENERATE: ClassVar[str]
    ER_CORRELATION_DEGENERATE: ClassVar[str]
    NO_HARD_CONSTRAINTS: ClassVar[str]
    WRONG_SEVERITY: ClassVar[str]
    EMPTY_KJ_ESTIMATE: ClassVar[str]
    EMPTY_HARD_CONSTRAINTS: ClassVar[str]
    INSUFFICIENT_TRAJECTORIES: ClassVar[str]
    MISSING_NOMINAL_UTILITY: ClassVar[str]
    MISSING_ENV_SCORES: ClassVar[str]
    SCORE_OUT_OF_RANGE: ClassVar[str]
    SINGLE_ENV_WARN: ClassVar[str]
    SINGLE_CONSTRAINT_DIVERSITY: ClassVar[str]
    ZERO_CONSTRAINT_ACTIVATIONS: ClassVar[str]
    KJ_EMPTY_WARN: ClassVar[str]
    REWARD_OUT_OF_RANGE: ClassVar[str]
    CANONICAL_VIOLATION_ERROR: ClassVar[str]
    GRADIENT_UNAVAILABLE: ClassVar[str]
    SIM_MODEL_NOT_FITTED: ClassVar[str]
    LATENT_INCONSISTENCY: ClassVar[str]
    CRITIC_QUALITY_WARN: ClassVar[str]
    POINT_ESTIMATE_MUTATED: ClassVar[str]
    M6_HYPOTHESIS_UNAVAILABLE: ClassVar[str]
    SEMANTIC_OVERWRITE_ERROR: ClassVar[str]
    EMPTY_REPAIR_TARGETS: ClassVar[str]
    TRANSFORM_INPUT_OUT_OF_RANGE: ClassVar[str]
    TRANSFORM_K_NON_POSITIVE: ClassVar[str]
    TRANSFORM_X0_BOUNDARY: ClassVar[str]
    REPORTER_OUT_OF_RANGE: ClassVar[str]
    CONFIG_WEIGHT_SUM_ERROR: ClassVar[str]
    INSUFFICIENT_BOOTSTRAP_SAMPLES: ClassVar[str]
    CI_INVERSION_WARN: ClassVar[str]
    THRESHOLD_ORDER_VIOLATED: ClassVar[str]
    SMALL_CALIBRATION_CORPUS: ClassVar[str]
    INVALID_AGGREGATION_MODE: ClassVar[str]
    UNRELATED_SPECS: ClassVar[str]
    EDIT_DISTANCE_NEGATIVE: ClassVar[str]
    UNKNOWN_OPERATOR: ClassVar[str]
    MISSING_SIDE_EFFECTS_DECLARATION: ClassVar[str]
    JUSTIFICATION_TRUNCATED: ClassVar[str]
    NO_PROPOSALS_GENERATED: ClassVar[str]
    PROPOSAL_REJECTED_MINIMALITY: ClassVar[str]
    LLM_ONLY_MODE_SAFETY_CRITICAL: ClassVar[str]
    ROUGH_SCORE_UNAVAILABLE: ClassVar[str]
    PROPOSAL_REJECTED_DIAGNOSTIC: ClassVar[str]
    PROPOSAL_REJECTED_SAFETY: ClassVar[str]
    PROPOSAL_REJECTED_UTILITY: ClassVar[str]
    SEM_SCORE_OUT_OF_RANGE: ClassVar[str]
    DEPARSING_FAILURE: ClassVar[str]
    HARD_REJECT: ClassVar[str]
    NO_PROPOSALS_AFTER_FILTER: ClassVar[str]
    LLM_RETRY_EXHAUSTED: ClassVar[str]
    PRECHECK_FATAL: ClassVar[str]

@dataclass(frozen=True)
class ErrorDescriptor:
    error_code: str
    severity: CREErrorSeverity
    module: str
    description: str

class CREError(Exception):
    error_code: ClassVar[str]
    severity: ClassVar[CREErrorSeverity]
    module: ClassVar[str]

class ConfigWeightSumError(CREError): ...

ERROR_REGISTRY: dict[str, ErrorDescriptor]
```
# 输入：无；这是 Part II §11 pp.49–51 定义的 canonical error surface
# 输出：统一的 `CREError` 基类、`CREErrorCode` 字符串常量命名空间、以及供后续模块查询的
#       `ERROR_REGISTRY`
# 约束：Table 5 中每个错误码都必须作为 `CREErrorCode.CODE_NAME` 可访问；每个正式错误子类
#       必须绑定唯一 `error_code`；`CONFIG_WEIGHT_SUM_ERROR` 必须在正式注册表中存在；`cfg.py`
#       与后续 `pipeline/orchestrator.py` 都必须复用这一错误体系，不得再保留字符串占位错误
# 备注：本接口冻结的是 Phase 0 的统一错误码格式与扩展面；后续模块不得自创新的错误码命名规则
#       或绕过 `CREError`
状态：[FROZEN] ⚠️ CREError 签名已冻结；这是 Phase 0 的 canonical error surface，后续模块不得自创错误码格式

### Phase 0 — LLM Infrastructure
```python
# analyzers/llm_gateway.py

@dataclass(frozen=True)
class LLMConfig:
    provider: Literal["comp_openai"]
    base_url: str
    api_version: str
    api_key_env: str
    deployment: str
    timeout_s: float = 60.0
    max_retries: int = 3
    temperature: float = 0.0
    max_tokens: int = 1024

@dataclass(frozen=True)
class LLMRequest:
    messages: tuple[dict[str, Any], ...]
    response_format: Literal["text", "json"] = "text"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str
    finish_reason: str | None
    raw_payload: dict[str, Any] = field(default_factory=dict)

class LLMGateway(Protocol):
    def complete(self, request: LLMRequest, config: LLMConfig) -> LLMResponse: ...

class CompOpenAIGateway(LLMGateway):
    ...
```
# 输入：Hydra `cfg/llm/comp_openai.yaml` 与 module-level deployment 选择
# 输出：供 M1 / M4 / M7 / M8 复用的统一 completion gateway
# 约束：strict PDF mode 下 canonical provider 固定为 COMP OpenAI gateway；认证头为 `api-key`；
#       配置中的 `base_url` 保存 gateway 根地址，实际请求端点在运行时解析为
#       `https://comp.azure-api.net/azure/openai/deployments/{deployment}`；
#       真实密钥与 deployment 名只允许来自环境变量，不得写入仓库
# 备注：本接口冻结的是共享接入面，不替代 `SpecS` / `DiagReport` / `RepairProposal` /
#       `AcceptanceVerdict` 的 canonical 跨模块 contract
状态：[FROZEN] ⚠️ LLM access surface 已冻结；M1/M4/M7/M8 必须复用同一 gateway / config 路径

### Phase 1 — M1 Specification Parsing
```python
# analyzers/m1.py

parse_nl_input(
    nl_input: NLInput,
    cfg: CFGSchema = CFG,
    llm_client: LLMGateway | None = None,
) -> tuple[SpecS, list[AmbiguityFlag]]
# 输入：canonical `NLInput`
# 输出：canonical `SpecS` 与 `list[AmbiguityFlag]`
# 约束：这是 Stage I / LLM-α 的 canonical 主链路；`TRACEABILITY.md` 中的 M1 行只能追溯到
#       本函数，不得由 YAML adapter 顶替

parse_yaml_input(
    reward_spec_path: str,
    constraint_spec_path: str,
    policy_spec_path: str,
    env_spec_path: str,
) -> tuple[SpecS, list[AmbiguityFlag]]
# 输入：四份结构化 YAML spec 路径
# 输出：canonical `SpecS` 与 `list[AmbiguityFlag]`
# 约束：这是 compatibility / offline fallback adapter；可以服务于现有 YAML 资产，
#       但不能作为 `M1.parse_nl_input` 的实现函数，也不能被记录为 canonical PDF 完成项

detect_and_escalate_ambiguities(
    spec: SpecS,
    ambiguity_flags: list[AmbiguityFlag],
    cfg: CFGSchema = CFG,
    llm_client: LLMGateway | None = None,
) -> list[AmbiguityFlag]
# 输入：canonical `SpecS` + `parse_nl_input()` 原始返回的 `ambiguity_flags`
# 输出：`list[AmbiguityFlag]`
# 约束：只输出 PDF Part II §1.2 p.22 中定义的五类 canonical flags；若 ambiguity
#       超过 escalation 阈值，需保留人工确认 / pipeline halt 所需信息

run_symbolic_precheck(spec: SpecS) -> list[str]
# 输入：canonical `SpecS`
# 输出：warning / error code 列表
# 约束：只负责 Part II §2.1.3 的 symbolic pre-check，不替代 schema validation
```
状态：[FROZEN] ⚠️ 接口已冻结；`parse_nl_input()` 是 canonical M1，`parse_yaml_input()` 仅为 compatibility adapter（见 `D-I20` / `D-I21`）

### Phase 1 — Spec 校验器
```python
# analyzers/spec_validator.py
validate_spec_file(spec_path: str) -> ValidationResult
# 输入：单份 spec YAML 路径
# 输出：ValidationResult { valid: bool, errors: list[str], warnings: list[str] }

validate_spec_set(
    reward_spec_path: str,
    constraint_spec_path: str,
    policy_spec_path: str,
    env_spec_path: str,
) -> ValidationResult
# 输入：四份 spec 路径
# 输出：跨文件基础一致性检查结果（字段类型、必填项、版本号匹配、warnings）
```
状态：[FROZEN] ✅ 已实现（Phase 1 DoD 之一）

### Phase 2 — Static Analysis（historical / legacy）
```python
# analyzers/legacy/static_analyzer.py
run_static_analysis(
    reward_spec_path: str,
    constraint_spec_path: str,
    policy_spec_path: str,
    env_spec_path: str,
    output_dir: str | None = None,
) -> StaticReport
# 输入：四份 spec 路径 + 可选输出目录
# 输出：StaticReport（同时写入 output_dir/static_report.json，若 output_dir 非 None）
# 报告须包含：问题列表、类型（C-R/E-C/E-R）、严重等级、可追溯字段
```
状态：[FROZEN] 🔶 历史接口已迁入 legacy/；不构成 strict PDF canonical phase

### Phase 3 — Dynamic Analysis（historical / legacy）
```python
# analyzers/legacy/dynamic_analyzer.py
run_dynamic_analysis(
    static_report: StaticReport,
    log_dir: str,
    reward_spec_path: str,
    constraint_spec_path: str,
    output_dir: str | None = None,
) -> DynamicReport
# 输入：StaticReport + 运行日志目录 + reward/constraint spec 路径
# 输出：DynamicReport（同时写入 output_dir/dynamic_report.json，若 output_dir 非 None）

@dataclass
class DynamicIssue:
    issue_id: str
    issue_type: str
    severity: str
    rule_id: str
    description: str
    traceable_fields: list[str]
    evidence: dict

@dataclass
class DynamicReport:
    spec_versions: dict[str, str]
    episode_count: int
    issues: list[DynamicIssue]
    summary: dict
    output_path: str | None
```
状态：[FROZEN] 🔶 历史接口已迁入 legacy/；不构成 strict PDF canonical phase

### Phase 4 — M4 Failure Hypothesis & Repair Target Prioritization
```python
# analyzers/m4.py

generate_failure_hypothesis(
    diag_report: DiagReport,
    spec: SpecS,
    cfg: CFGSchema = CFG,
    llm_client: LLMGateway | None = None,
) -> tuple[str | None, list[str]]
# 输入：已含 canonical numerical reporters 的 `DiagReport` + read-only `SpecS`
# 输出：`(failure_hypothesis, repair_targets)`
# 约束：这是 Part II §7.1.1 的单一 canonical LLM-β 调用；caller 只可在 diff guard
#       通过后，把返回值写回 `DiagReport.failure_hypothesis` / `DiagReport.repair_targets`；
#       若调用后任何数值 reporter、`ci_95`、`flags` 或 `discrepancy` 被覆盖，必须抛出
#       `SEMANTIC_OVERWRITE_ERROR`
```
状态：[FROZEN] ⚠️ 接口已冻结；M4 已恢复为 canonical LLM-β 路线

> 若实现层需要把 prompt 组装、target 排序或 diff guard 拆成多个 helper，
> 这些 helper 只能标记为 non-canonical internal helper，不得出现在 `TRACEABILITY.md`
> 或跨模块接口契约中。

### Phase 5 — M7 Repair Proposal Generation
```python
# repair/m7.py

compute_spec_edit_distance(
    spec: SpecS,
    spec_prime: SpecS,
) -> float
# 输入：原始 `SpecS` 与候选修复后的 `SpecS'`
# 输出：`d_spec(S, S')`

generate_repair_proposals(
    spec: SpecS,
    diag_report: DiagReport,
    cfg: CFGSchema = CFG,
    llm_client: LLMGateway | None = None,
) -> list[RepairProposal]
# 输入：canonical `SpecS` + `DiagReport`
# 输出：`list[RepairProposal]`
# 约束：这是 Part II §8.1.2 的 LLM-δ 主链路；每个 proposal 都必须复用
#       `diag_report.py` 中冻结的 canonical `RepairProposal`

filter_by_minimality(
    proposals: list[RepairProposal],
    spec: SpecS,
    cfg: CFGSchema = CFG,
) -> list[RepairProposal]
# 输入：repair proposal 候选集 + 原始 `SpecS`
# 输出：满足 `d_spec <= eta_edit` 的 proposal 子集

rank_proposals(
    proposals: list[RepairProposal],
    spec: SpecS,
    diag_report: DiagReport,
    cfg: CFGSchema = CFG,
) -> list[RepairProposal]
# 输入：通过 minimality 的 proposal 列表
# 输出：按 Stage 1 rollout 估计 + Stage 2 `predicted_delta_psi` 排序后的 proposal 列表
```
状态：[FROZEN] ⚠️ 接口已冻结；M7 已恢复为 canonical LLM-δ 路线

### Phase 6 — M8 Acceptance & Semantic Consistency
```python
# repair/m8.py

evaluate_acceptance_criteria(
    spec: SpecS,
    spec_prime: SpecS,
    diag_orig: DiagReport,
    diag_prime: DiagReport,
    cfg: CFGSchema = CFG,
) -> AcceptanceVerdict
# 输入：原始 `SpecS` / `DiagReport` 与候选 `SpecS'` / `DiagReport'`
# 输出：只包含 C1–C4 判定结果的 `AcceptanceVerdict`
# 约束：C1–C4 与 semantic consistency 分离；`accepted=True` 仅表示 C1–C4 通过，
#       不能替代 `verify_semantic_consistency()` 的 semantic gate

verify_semantic_consistency(
    nl_orig: NLInput,
    spec_prime: SpecS,
    cfg: CFGSchema = CFG,
    llm_client: LLMGateway | None = None,
) -> tuple[float, bool]
# 输入：原始自然语言输入 `NLInput` + 候选修复后的 `SpecS'`
# 输出：`(s_sem, intent_preserved)`
# 约束：这是 Part II §9.1.2 的 canonical LLM-ε 调用；实现层需先将 `spec_prime`
#       通过 deterministic serializer 反解为 `nl_prime` 再交给 LLM；semantic gate
#       独立于 C1–C4，最终接受条件为 `(all C1–C4 pass) AND (s_sem >= tau_sem) AND intent_preserved`

run_acceptance_loop(
    nl_orig: NLInput,
    spec: SpecS,
    proposals: list[RepairProposal],
    diag_report: DiagReport,
    cfg: CFGSchema = CFG,
    llm_client: LLMGateway | None = None,
) -> tuple[SpecS | None, AcceptanceVerdict, Literal["ACCEPT", "HARD_REJECT"]]
# 输入：原始 `NLInput` + `SpecS` + 已排序 proposal 列表 + 原始 `DiagReport`
# 输出：`(accepted_spec, verdict, exit_code)`
# 约束：必须先评估 C1–C4，再单独调用 `verify_semantic_consistency()` 施加 semantic gate，
#       并遵守 `N_max` 循环上限；`exit_code ∈ {"ACCEPT","HARD_REJECT"}`；不得再引入
#       `RepairResult` / `PatchValidationResult` 作为 strict PDF mode 的替代输出
```
状态：[FROZEN] ⚠️ 接口已冻结；M8 已恢复为 canonical LLM-ε 路线

> strict PDF mode 下，以下结构只能保留为 legacy / compatibility / historical artifacts，
> 不得再作为跨模块 canonical contract：`SemanticReport`、`CREReport`、
> `RepairPatch`、`RepairResult`、`PatchValidationResult`。

### Phase 7 — Pipeline Orchestrator
```python
# pipeline/orchestrator.py

run_cre_pipeline(
    nl_input: NLInput,
    cfg: CFGSchema = CFG,
    llm_client: LLMGateway | None = None,
) -> tuple[DiagReport, AcceptanceVerdict | None]
# 输入：canonical `NLInput` + `CFG`
# 输出：`DiagReport` 与可选 `AcceptanceVerdict`
# 顺序：M1 -> M2 -> M3 -> [DP] -> M5 -> M4 -> [loop: M7 -> M8]
# 约束：任何模块执行前都必须先检查 `w_cr + w_ec + w_er = 1.0`；若失败则抛
#       `CONFIG_WEIGHT_SUM_ERROR` 并停止 pipeline
```
状态：[FROZEN] ⚠️ 接口已冻结；strict PDF mode 下所有训练/benchmark 接入都应通过 orchestrator，而非旧版 report/repair patch 链路

### Phase 9 — Benchmark Suite
```python
# scripts/run_benchmark.py

def run_benchmark(
    benchmark_dir: str,
    output_dir: str | None = None,
) -> dict[str, dict]:
# 输入：benchmark_cfg/ 根目录
# 输出：{case_name: {"alarm": bool, "psi_cre": float, "total_issues": int}}
# 同时写入 output_dir/benchmark_results.json（若非 None）
# 对每个 case 子目录跑 run_static_analysis + run_semantic_analysis
# 期望结果：clean_nominal → alarm=False；injected_* → alarm=True

# cfg/benchmark_cfg/ 目录结构：
# benchmark_cfg/
# ├── clean_nominal/
# │   ├── reward_spec_v1.yaml
# │   ├── constraint_spec_v1.yaml
# │   ├── policy_spec_v1.yaml
# │   └── env_spec_v1.yaml
# ├── injected_cr/   # reward term weight 与 hard constraint 共享变量
# ├── injected_ec/   # shift_operators: []
# └── injected_er/   # E_dep.deployment_envs: []
```
状态：[FROZEN] ⚠️ 接口已冻结，待实现

### Phase 10 — Release Packaging
```
待定
```
状态：❌

> 规则：每个 Phase 开始前，负责人须先在此补充具体签名，经确认后才能动手编码。实现完成后将 ❌ 改为 ✅。

---

## 6. 接口确认机制（强制协议）

> 本节规定接口契约的生命周期管理规则，所有 Agent 必须遵守。

### 6.1 接口状态三级制

每个接口条目在本文件中使用以下三级状态，**独立于实现状态**：

| 状态标记 | 含义 | 可以依赖？ |
|---------|------|-----------|
| `[FROZEN]` | 签名已冻结，跨 Agent 可依赖 | ✅ 可以 |
| `[DRAFT]` | 草案，可能变更，仅本 Phase 内部使用 | ⚠️ 谨慎 |
| `[PENDING]` | 尚未设计，禁止依赖 | ❌ 禁止 |

### 6.2 强制变更协议

1. **先改接口，再动代码**：任何跨模块函数签名变更，必须先在本文件将状态改为 `[DRAFT]`，写明新签名，再修改代码
2. **冻结需要确认**：`[DRAFT]` → `[FROZEN]` 需在 `DECISIONS.md` 中留记录（接口 ID + 确认日期 + 确认原因）
3. **新增跨模块调用**：新增调用前必须在本文件中有对应接口记录（至少 `[DRAFT]` 状态）
4. **实现与接口不符时**：以本文件为准，代码需对齐，不得反向修改本文件来迁就代码

### 6.3 Phase 串行风险缓解：接口提前冻结策略

**问题**：Phase N 的 DoD 严格依赖 Phase N-1 全部完成，一旦某 Phase 卡住整个项目停摆。

**解决方案**：接口签名可以比实现**提前冻结**。以下接口可以在对应 Phase 开始之前并行设计：

```
Phase 1 实施期间可并行冻结：
  ├── Phase 2 的 StaticReport schema（输入输出格式）→ 写入 §5 Phase 2 条目
  └── Phase 3 的日志字段映射方案草案 → 写入 §5 Phase 3 条目

Phase 2 实施期间可并行冻结：
  ├── Phase 3 的 DynamicReport schema
  └── Phase 4 的 utility oracle 接口（独立于 R，需提前确认！见 CRE_v4 §3.6）

Phase 3 实施期间可并行冻结：
  └── Phase 5 的 CRE Report 汇总格式
```

**状态追踪**：STATUS.md 每个 Phase 条目增加一行"接口就绪"标记，区分"接口 [FROZEN]"和"实现完成"，后续 Phase 可以在接口冻结后立即开始设计，不必等待前序实现完成。

### 6.4 决策依赖关系（阻塞性决策链）

以下决策是各 Phase 的硬性前置条件，未在 `DECISIONS.md` 中记录则不得开始对应 Phase：

| 决策 ID | 内容 | 阻塞的 Phase |
|---------|------|-------------|
| D-S1 | reward spec 字段格式（字段名/类型/单位/必填项） | Phase 1 |
| D-S2 | constraint spec 字段格式（约束名/类型/阈值/严重等级） | Phase 1 |
| D-S3 | policy spec 字段格式（动作/观测/频率） | Phase 1 |
| D-S4 | StaticReport 输出 schema（JSON/YAML 结构） | Phase 2 |
| D-S5 | 旧版日志字段映射方案（哪些字段复用/重新定义） | Phase 3 |
| D-S6 | Utility Oracle 实现方式（独立性必须满足 CRE §3.6） | Phase 4 |
| D-S7 | CRE Report 汇总格式（问题列表/严重等级/可追溯字段） | Phase 5 |

> 每个 Phase 启动前，Agent 的第一步是检查上表中对应的决策是否已在 `DECISIONS.md` 中存在。不存在则先补充决策记录，再开始实现。
