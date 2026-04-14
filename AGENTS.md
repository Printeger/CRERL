# AGENTS.md — Session Bootstrap

本项目在 Isaac Sim + TorchRL 的无人机自主避障 RL 训练框架中集成 CRE（Constraint-Reward-Environment）框架，目标是评估并提升 reward/constraint/environment specification 的质量，最终实现全流程自动化。**CRE 开发从零开始，当前进度为 Phase 1（Spec 设计），尚未有任何 CRE 模块实现**。

---

## 目录结构（实际存在）

```
CRERL/
├── AGENTS.md              # 本文件 — 会话启动引导
├── DECISIONS.md           # 架构决策记录
├── INTERFACES.md          # 跨模块接口契约
├── STATUS.md              # Phase/模块完成状态
├── Traceability.md        # 空文件，待填写
├── doc/
│   ├── CRE_v4.pdf         # 主要理论和 Handbook（权威来源）
│   └── cre_dev/           # 开发文档
│       ├── CRE_v4_summary.md          # ★ CRE_v4.pdf 核心结论摘要（新 Agent 快速入口）
│       ├── drone_interface_report.md  # 旧版参考
│       └── rl_code_structure_audit_2026-04-11.md  # 旧版参考
└── isaac-training/training/
    ├── cfg/
    │   ├── train.yaml / eval.yaml / ppo.yaml / sim.yaml / baseline.yaml / drone.yaml
    │   ├── env_cfg/       # scene_cfg_base/nominal/shifted/boundary_critical.yaml
    │   └── spec_cfg/      # ← 已删除，新版 spec 格式待根据 CRE_v4.pdf 定义
    ├── scripts/           # RL 训练脚本（CRE 相关旧版脚本已删除）
    │   ├── train.py / eval.py / ppo.py / env.py / utils.py
    │   ├── run_baseline.py / run_dashboard.py
    │   └── run_release_packaging.py  # 🔶 旧版参考，待重建
    ├── envs/
    │   ├── cre_logging.py           # 🔶 旧版参考（接口需验证）
    │   ├── universal_generator.py
    │   ├── primitives/              # 场景生成组件
    │   └── runtime/                 # 运行时环境组件
    ├── runtime_logging/             # 🔶 旧版参考（接口需验证）
    │   ├── training_log_adapter.py
    │   ├── logger.py
    │   ├── acceptance.py
    │   ├── episode_writer.py
    │   └── schema.py
    ├── dashboard/                   # 监控 UI（🔶 旧版参考）
    ├── unit_test/                   # 单元测试（含 test_env/ 子目录，🔶 旧版参考）
    └── logs/                        # 🔶 旧版实际训练日志（可作测试数据参考）
```

### 需要从零创建的内容

以下内容**不存在于代码库**，需根据 CRE_v4.pdf 从零设计和实现：

| 内容 | 路径 | 说明 |
|------|------|------|
| 新版 spec 文件 | `cfg/spec_cfg/` | reward/constraint/policy spec，从 v1 起命名 |
| 分析包 | `analyzers/` | CRE 分析核心逻辑 |
| 修复包 | `repair/` | 修复和验证逻辑 |
| Pipeline 包 | `pipeline/` | 集成、benchmark、发布 |
| CRE CLI 脚本 | `scripts/run_*.py` | 旧版已删除，需重建 |

---

## 编码规则

- **数据格式**：env/policy/collector 边界一律用 TorchRL `TensorDict`，禁止使用 `gym.Env` 或裸 numpy。
- **配置管理**：所有超参数走 Hydra（`cfg/`），脚本中不允许硬编码数值。
- **新建包位置**：`analyzers/`、`repair/`、`pipeline/` 均在 `isaac-training/training/` 下创建。
- **Spec 版本控制**：新版 spec 从 `*_v1.yaml` 开始命名；后续变更创建更高版本，禁止原地修改；每次命名决策在 DECISIONS.md 记录。
- **旧版代码只读参考**：`envs/cre_logging.py`、`runtime_logging/` 等旧版模块只能阅读参考，不能直接调用或视为已完成。
- **RL 框架接口**（参考，可能随新版 CRE 设计调整）：observation keys 为 `("agents","observation","state/lidar/dynamic_obstacle")`；done 编码 `done_type` 为 0=running/1=success/2=collision/3=out_of_bounds/4=truncated。

---

## ⛔ CRE-PDF 强制对齐协议（不可绕过）

> **这是 2026-04-12 审计后追加的强制规则。** 历史实现存在严重偏差（详见 `REFACTOR_ROADMAP.md` 偏差清单），根本原因是 agent 未充分阅读 PDF 即开始编码。以下规则旨在从源头杜绝此类偏差。**任何 agent 在任何 Phase 均必须遵守，优先级高于其他一切规则。**

### 协议 P1：先读 PDF，后动代码

实现任何 CRE 分析模块（M1–M8、DP、PO）前，**必须先读 `doc/CRE_v4.pdf` 中该模块对应的章节**（Part II 对应章节 §2–§10），并在代码注释中标注所依据的 PDF 公式编号（如 `# Eq.(11) Part I §3.3`）。

未标注 PDF 公式编号的函数 = 未完成，不得合并。

### 协议 P2：先定数据结构，后写算法

每个 Phase 开始前，**必须先在 `INTERFACES.md` 中声明该 Phase 所有函数的完整签名**（参数类型、返回类型、错误码），经 commander review 冻结后，才能开始实现。

禁止 agent 自创数据结构替代 PDF 规定的标准结构（`DiagReport`、`SpecS`、`RepairProposal`、`AcceptanceVerdict`）。

### 协议 P3：先写合约测试，后写实现

每个函数实现前，**必须先把 PDF Part II 中对应的 Test Standards（T1–Tn）写成 pytest 用例**（此时预期全部 fail）。实现完成后，所有合约测试必须通过，才能标记为完成。

合约测试必须包含数值精度要求（如 `assert abs(phi_cr2 - 0.0) < 1e-9`），不允许只做"不崩溃"检查。

### 协议 P4：TRACEABILITY.md 是完成的充要条件

每个函数实现完成后，**必须在 `TRACEABILITY.md` 中填写对应行**：

```
| PDF 章节 | 公式/函数名 | 实现文件 | 实现函数 | 合约测试 | 状态 |
```

`TRACEABILITY.md` 中未填写 = 未完成，STATUS.md 不得勾选该 DoD 条目。

### 协议 P5：旧版实现移入 legacy/，不得直接修改

历史遗留的 `static_analyzer.py`、`dynamic_analyzer.py`、`semantic_analyzer.py`、`report_generator.py`、`repair_generator.py`、`validator.py` 已被移入 `analyzers/legacy/` 和 `repair/legacy/`（见 `REFACTOR_ROADMAP.md`）。

- **禁止**在 legacy/ 文件上直接修改来"修复偏差"
- **必须**在正确路径（如 `analyzers/m2.py`）新建符合 PDF 的实现
- legacy/ 文件只可只读引用，了解旧版思路

### 协议 P6：权重和检验是启动前置条件

任何调用 `compute_psi_cre` 的代码，**必须先验证** `w_cr + w_ec + w_er = 1.0`（误差 < 1e-9）。
不满足则抛出 `CONFIG_WEIGHT_SUM_ERROR`，管线不得继续。

---

## 当前 Phase

**Phase 1 — Spec 设计（未开始）**

CRE 开发进度为零。代码库中不存在任何 CRE 分析模块，旧版 CRE 相关脚本和 spec 文件均已删除。

**Phase 1 的核心任务（按顺序）**：
1. 读 `doc/CRE_v4.pdf`，理解 CRE 对 spec 格式的要求
2. 设计并创建三份 spec 文件：`reward_spec_v1.yaml`、`constraint_spec_v1.yaml`、`policy_spec_v1.yaml`
3. 建立 Spec 校验器（`analyzers/spec_validator.py`）：schema 验证 + 基础一致性检查

**Phase 1 完成判定**：见 `STATUS.md` Phase 1 DoD 列表，全部勾选 ✅ 后才算完成。

> ⛔ **强制规则**：任何 Phase 的任务结束前，必须更新 `STATUS.md`（勾选 DoD、更新日期、写明下一步）。未更新 STATUS.md 视为任务未完成，不得开启下一 Phase。

---

## 每次新会话必读清单

按顺序阅读，不可跳过：

1. `doc/cre_dev/CRE_v4_summary.md` — CRE_v4.pdf 核心结论摘要（快速阅读入口；含三类不一致定义、六阶段管线、Ψ_CRE 评分、必须遵守的架构约束、对本项目的直接影响）
   - 时间充裕时仍应阅读 `doc/CRE_v4.pdf` 原文；摘要以 PDF 为权威来源
2. `DECISIONS.md` — 所有架构决策及其原因（**启动任何 Phase 前先检查对应阻塞性决策是否存在**）
3. `INTERFACES.md` — 跨模块接口契约，含接口确认协议和 Phase 串行风险缓解策略（§6）
4. `STATUS.md` — 当前完成状态和下一步行动（文件级别）
5. `REFACTOR_ROADMAP.md` — ⚠️ **重构路线图**（2026-04-12 起新增）：记录所有已发现的 PDF 偏差、重构阶段计划（Phase 0–8）、每个 Step 的执行协议。**任何与 CRE 分析模块相关的任务，必须先读此文件确认当前重构阶段**。

## 每次任务结束强制动作

> ⛔ **不可跳过**：完成任何可交付产物（文件创建、代码实现、设计决策）后，会话结束前必须：
> 1. 在 `STATUS.md` 中勾选已完成的 DoD 条目（`[ ]` → `[x]`）
> 2. 更新 `STATUS.md` 顶部"最后更新"日期
> 3. 在"立即下一步"中写明下一个具体行动项
>
> **违反此规则 = 任务未完成**，即使产物文件存在，下一个 Agent 也将无法判断进度。

## 开发环境

- 需要使用命令进入conda环境进行开发和训练：`conda activate NavRL`