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
5. `isaac-training/training/envs/cre_logging.py`（🔶 旧版参考，了解日志字段设计思路）
6. `isaac-training/training/runtime_logging/training_log_adapter.py`（🔶 旧版参考，了解 TensorDict 适配思路）

## 每次任务结束强制动作

> ⛔ **不可跳过**：完成任何可交付产物（文件创建、代码实现、设计决策）后，会话结束前必须：
> 1. 在 `STATUS.md` 中勾选已完成的 DoD 条目（`[ ]` → `[x]`）
> 2. 更新 `STATUS.md` 顶部"最后更新"日期
> 3. 在"立即下一步"中写明下一个具体行动项
>
> **违反此规则 = 任务未完成**，即使产物文件存在，下一个 Agent 也将无法判断进度。
