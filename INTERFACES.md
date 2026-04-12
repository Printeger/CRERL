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

### Phase 2 — Static Analysis
```python
# analyzers/static_analyzer.py
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
状态：[FROZEN] ⚠️ 接口已冻结，待实现（Phase 2 DoD 之一）

### Phase 3 — Dynamic Analysis
```python
# analyzers/dynamic_analyzer.py
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
状态：[FROZEN] ⚠️ 接口已冻结，待实现

### Phase 4 — Semantic Analysis
```python
# analyzers/semantic_analyzer.py

@dataclass
class SemanticIssue:
    issue_id: str          # 格式: SA-001, SA-002, ...
    issue_type: str        # "C-R" | "E-C" | "E-R" | "composite"
    severity: str          # "error" | "warning" | "info"
    rule_id: str
    description: str
    traceable_fields: list[str]
    evidence: dict         # 含 phi 值、阈值、来源 issue_ids

@dataclass
class SemanticReport:
    spec_versions: dict[str, str]
    psi_cre: float                  # Ψ_CRE ∈ [0, 1]
    phi_cr: float                   # φ²_CR 边界趋近评分
    phi_ec: float                   # φ̄¹_EC 均值关键态覆盖率
    phi_er: float | None            # φ³_ER reward-utility 去耦（oracle 不可用时为 None）
    issues: list[SemanticIssue]
    summary: dict                   # 含 alarm: bool, psi_cre, by_type, by_severity
    output_path: str | None

run_semantic_analysis(
    static_report: StaticReport,
    dynamic_report: DynamicReport,
    reward_spec_path: str,
    constraint_spec_path: str,
    output_dir: str | None = None,
) -> SemanticReport
# 输入：Phase 2 StaticReport + Phase 3 DynamicReport + reward/constraint spec 路径
# 输出：SemanticReport（同时写入 output_dir/semantic_report.json，若 output_dir 非 None）
# 计算：φ²_CR、φ̄¹_EC、φ³_ER（oracle 不可用时跳过）、Ψ_CRE
# 语义分析：rule-based（替代 LLM-β，依据 D-LLM-α）
```
状态：[FROZEN] ⚠️ 接口已冻结，待实现

### Phase 5 — Report Generation
```python
# analyzers/report_generator.py

@dataclass
class CREReport:
    report_id: str                        # 格式: CRE-<timestamp>
    spec_versions: dict[str, str]
    static_issues: list[StaticIssue]
    dynamic_issues: list[StaticIssue]
    semantic_issues: list[SemanticIssue]
    psi_cre: float
    alarm: bool
    summary: dict[str, Any]
    output_path: str | None

def generate_report(
    static_report: StaticReport,
    dynamic_report: DynamicReport,
    semantic_report: SemanticReport,
    output_dir: str | None = None,
) -> CREReport:
# 输入：Phase 2 StaticReport + Phase 3 DynamicReport + Phase 4 SemanticReport
# 输出：CREReport（同时写入 output_dir/report.json，若 output_dir 非 None）
# psi_cre 和 alarm 直接从 semantic_report 透传，不重新计算
# summary 含 total、by_phase、by_severity、alarm、psi_cre
```
状态：[FROZEN] ⚠️ 接口已冻结，待实现

### Phase 6 — Repair
```python
# repair/repair_generator.py

@dataclass
class RepairPatch:
    patch_id: str                   # 格式: PATCH-001, PATCH-002, ...
    target_spec: str                # "reward" | "constraint" | "env"
    target_field: str               # YAML 路径, 如 reward_terms[0].weight
    operation: str                  # "set" | "add" | "remove"
    old_value: Any
    new_value: Any
    rationale: str
    source_issue_ids: list[str]

@dataclass
class RepairResult:
    report_id: str                  # 透传自 CREReport.report_id
    patches: list[RepairPatch]
    summary: dict[str, Any]         # total_patches, by_target_spec, source_issue_count
    output_path: str | None

def generate_repair(
    cre_report: CREReport,
    output_dir: str | None = None,
) -> RepairResult:
# 输入：Phase 5 CREReport
# 输出：RepairResult（同时写入 output_dir/repair_result.json，若 output_dir 非 None）
# 首版只生成修复建议，不自动写入 spec 文件
# 规则驱动：每类 issue_type 对应固定修复模板（见实现说明）
```
状态：[FROZEN] ⚠️ 接口已冻结，待实现

### Phase 7 — Validation
```python
# repair/validator.py

@dataclass
class PatchValidationResult:
    report_id: str                  # 透传自 RepairResult.report_id
    patches_applied: int
    issues_before: list[str]        # 修复前 issue_ids
    issues_after: list[str]         # 修复后 issue_ids
    issues_resolved: list[str]      # before - after
    issues_introduced: list[str]    # after - before
    passed: bool                    # issues_introduced==[] 且有改善或原本干净
    summary: dict[str, Any]
    output_path: str | None

def validate_repair(
    repair_result: RepairResult,
    static_report: StaticReport,
    reward_spec_path: str,
    constraint_spec_path: str,
    policy_spec_path: str,
    env_spec_path: str,
    output_dir: str | None = None,
) -> PatchValidationResult:
# 输入：Phase 6 RepairResult + Phase 2 StaticReport（作为 before 基准）+ 四份 spec 路径
# 输出：PatchValidationResult（同时写入 output_dir/validation_result.json，若非 None）
# 策略：内存级 patch 应用，不写入真实 spec 文件
# passed = issues_introduced==[] 且 (issues_resolved != [] 或 issues_before == [])
```
状态：[FROZEN] ⚠️ 接口已冻结，待实现

### Phase 8 — Integration（接入训练主循环）
```python
# train.py 收尾区追加（wandb.finish() 之前）

# train.yaml 新增字段组：
# spec_cfg:
#   reward: cfg/spec_cfg/reward_spec_v1.yaml
#   constraint: cfg/spec_cfg/constraint_spec_v1.yaml
#   policy: cfg/spec_cfg/policy_spec_v1.yaml
#   env: cfg/spec_cfg/env_spec_v1.yaml

# 接入代码模式：
try:
    from analyzers.static_analyzer import run_static_analysis
    from analyzers.dynamic_analyzer import run_dynamic_analysis
    from analyzers.semantic_analyzer import run_semantic_analysis
    from analyzers.report_generator import generate_report
    from repair.repair_generator import generate_repair
    from repair.validator import validate_repair

    _static = run_static_analysis(
        cfg.spec_cfg.reward, cfg.spec_cfg.constraint,
        cfg.spec_cfg.policy, cfg.spec_cfg.env,
        output_dir=cre_run_logger.run_dir,
    )
    _dynamic = run_dynamic_analysis(
        _static, cre_run_logger.run_dir,
        cfg.spec_cfg.reward, cfg.spec_cfg.constraint,
        output_dir=cre_run_logger.run_dir,
    )
    _semantic = run_semantic_analysis(
        _static, _dynamic,
        cfg.spec_cfg.reward, cfg.spec_cfg.constraint,
        output_dir=cre_run_logger.run_dir,
    )
    _report = generate_report(_static, _dynamic, _semantic,
                              output_dir=cre_run_logger.run_dir)
    _repair = generate_repair(_report, output_dir=cre_run_logger.run_dir)
    _validation = validate_repair(
        _repair, _static,
        cfg.spec_cfg.reward, cfg.spec_cfg.constraint,
        cfg.spec_cfg.policy, cfg.spec_cfg.env,
        output_dir=cre_run_logger.run_dir,
    )
    wandb.run.log({
        "cre_v2/psi_cre": _semantic.psi_cre,
        "cre_v2/alarm": int(_semantic.summary["alarm"]),
        "cre_v2/total_issues": _report.summary["total"],
        "cre_v2/patches": len(_repair.patches),
        "cre_v2/validation_passed": int(_validation.passed),
    })
except Exception as _e:
    import warnings
    warnings.warn(f"[CRE v2] 分析流水线异常（不影响训练结果）: {_e}")
```
状态：[FROZEN] ⚠️ 接口已冻结，待实现

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
