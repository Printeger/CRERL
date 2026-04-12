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
# 输出：ValidationResult { valid: bool, errors: list[str] }

validate_spec_set(
    reward_spec_path: str,
    constraint_spec_path: str,
    policy_spec_path: str,
) -> ValidationResult
# 输入：三份 spec 路径
# 输出：跨文件基础一致性检查结果（字段类型、必填项、版本号匹配）
```
状态：❌ 待实现（Phase 1 DoD 之一）

### Phase 2 — Static Analysis
```python
# analyzers/static_analyzer.py
run_static_analysis(
    reward_spec_path: str,
    constraint_spec_path: str,
    policy_spec_path: str,
    output_dir: str,
) -> StaticReport
# 输入：三份 spec v1 文件
# 输出：结构化静态分析报告（写入 output_dir，同时返回对象）
# 报告须包含：问题列表、类型（C-R/E-C/E-R）、严重等级、可追溯字段
```
状态：❌ 待实现（Phase 2 DoD 之一）；接口签名在 Phase 2 开始前须在此确认

### Phase 3 — Dynamic Analysis
```
待定：需先完成 Phase 2，再根据 CRE_v4.pdf 确定
输入：static report + 运行日志目录
输出：dynamic report
```
状态：❌ 接口未设计

### Phase 4 — Semantic Analysis
```
待定
```
状态：❌

### Phase 5 — Report Generation
```
待定
```
状态：❌

### Phase 6 — Repair
```
待定
```
状态：❌

### Phase 7 — Validation
```
待定
```
状态：❌

### Phase 8 — Integration（接入训练主循环）
```
待定：确定新版 CRE logging 如何嵌入 train.py
```
状态：❌

### Phase 9 — Benchmark Suite
```
待定
```
状态：❌

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
