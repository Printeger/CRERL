# STATUS.md — Phase & 模块完成状态

最后更新：2026-04-12

---

## 当前真实状态：从零开始

CRE 框架开发进度为零。代码库中**不存在任何可用的 CRE 分析模块**。  
所有旧版 CRE 相关代码（CLI 脚本、日志模块、spec 文件）均已删除或仅为旧版参考，不构成开发进度。

> **Phase 定义权威来源**：`doc/CRE_v4.pdf`。下方 Phase 总览是基于 CRE_v4.pdf 的初步规划，**开发前必须先读 PDF 核对，如有出入以 PDF 为准并更新本文件**。

---

## Phase 总览与 DoD

### Phase 1 — Spec 设计 ❌ 未开始

**目标**：定义三份 YAML spec 文件的完整格式，作为后续所有分析的输入合约。

**DoD（以下全部满足才算完成）：**
- [ ] `cfg/spec_cfg/reward_spec_v1.yaml` 存在，包含：字段名、类型、单位、必填项、版本号
- [ ] `cfg/spec_cfg/constraint_spec_v1.yaml` 存在，包含：约束名、类型、阈值、严重等级
- [ ] `cfg/spec_cfg/policy_spec_v1.yaml` 存在，包含：动作空间、观测空间、执行频率
- [ ] 三份文件有 JSON Schema 或等效的 schema 校验器可通过
- [ ] `DECISIONS.md` 中有关于 spec 格式设计依据的记录

**可验证产物**：
```
cfg/spec_cfg/reward_spec_v1.yaml
cfg/spec_cfg/constraint_spec_v1.yaml
cfg/spec_cfg/policy_spec_v1.yaml
analyzers/spec_validator.py  （或等效 schema 文件）
```

---

### Phase 2 — Spec 校验与静态分析 ❌ 未开始

**目标**：基于 Phase 1 的 spec，检测三份 spec 之间的静态矛盾（C-R 冲突、E-C 不匹配、E-R 不匹配）。

**依赖**：Phase 1 全部 DoD 已满足。

**DoD：**
- [ ] `analyzers/` 包存在，可 `import analyzers`
- [ ] 输入：三份 spec v1 文件；输出：结构化静态分析报告（JSON/YAML）
- [ ] 能检测至少以下三类问题：C-R 冲突、E-C 不匹配、E-R 不匹配
- [ ] `INTERFACES.md` 中有 Phase 2 分析函数的签名记录
- [ ] 单元测试通过（含至少一个阳性案例：输入有冲突的 spec，期望报告含对应问题）

**可验证产物**：
```
analyzers/__init__.py
analyzers/spec_validator.py
analyzers/static_analyzer.py
unit_test/test_env/test_static_analyzer.py  （通过）
analysis/static/<bundle>/  （运行一次后产生）
```

---

### Phase 3 — Dynamic Analysis ❌ 未开始

**目标**：从真实运行日志中检测动态行为与 spec 的不一致。

**依赖**：Phase 2 DoD 已满足。

**DoD：**
- [ ] 输入：静态分析 bundle + 运行日志目录；输出：动态分析报告
- [ ] 能读取 `logs/` 下的旧版日志（或新版日志），字段映射决策已在 `DECISIONS.md` 记录
- [ ] 单元测试通过

**可验证产物**：
```
analyzers/dynamic_analyzer.py
unit_test/test_env/test_dynamic_analyzer.py  （通过）
```

---

### Phase 4 — Semantic Analysis ❌ 未开始

**目标**：跨模态语义不一致检测（结合静态+动态结果做语义推断）。

**依赖**：Phase 3 DoD 已满足。

**DoD：**
- [ ] 输入：静态 bundle + 动态 bundle；输出：语义分析报告
- [ ] 单元测试通过

---

### Phase 5 — Report Generation ❌ 未开始

**目标**：将前三阶段分析结果汇总为结构化 CRE 报告。

**依赖**：Phase 4 DoD 已满足。

**DoD：**
- [ ] 输出报告格式在 `INTERFACES.md` 中有定义
- [ ] 报告含问题列表、严重等级、可追溯到 spec 字段
- [ ] 单元测试通过

---

### Phase 6 — Repair ❌ 未开始

**目标**：基于 Phase 5 报告，生成规则驱动的自动修复建议（patch）。

**依赖**：Phase 5 DoD 已满足。

**DoD：**
- [ ] 输入：CRE 报告；输出：修复补丁列表（可应用到 spec 文件）
- [ ] 单元测试通过

---

### Phase 7 — Validation ❌ 未开始

**目标**：验证修复后的 spec 是否消除了原有问题。

**依赖**：Phase 6 DoD 已满足。

**DoD：**
- [ ] 输入：修复后 spec；输出：验证报告（对比修复前后）
- [ ] 修复后的 spec 通过 Phase 2 静态分析（无原问题）
- [ ] 单元测试通过

---

### Phase 8 — Integration ❌ 未开始

**目标**：将 CRE 分析流程接入训练主循环（`train.py`），实现运行时自动记录和 acceptance check。

**依赖**：Phase 7 DoD 已满足。

**DoD：**
- [ ] `train.py` 中集成新版 CRE logging（接口设计符合 `INTERFACES.md`）
- [ ] 训练结束后自动生成 CRE 报告并写入 WandB
- [ ] acceptance check 通过后训练才视为合格运行
- [ ] 集成测试通过

---

### Phase 9 — Benchmark Suite ❌ 未开始

**目标**：通过注入已知缺陷的 spec 验证检测器的有效性。

**依赖**：Phase 8 DoD 已满足。

**DoD：**
- [ ] `cfg/benchmark_cfg/` 存在，含 clean_nominal 和三类注入 case
- [ ] clean_nominal → acceptance PASS
- [ ] injected_cr / injected_ec / injected_er → acceptance FAIL
- [ ] 结果可复现

---

### Phase 10 — Release Packaging ❌ 未开始

**目标**：打包所有产物，产出可发布的 CRE 分析套件。

**依赖**：Phase 9 DoD 已满足。

**DoD：**
- [ ] `Traceability.md` 填写完整（spec 字段 → 实现代码的映射）
- [ ] `README.md` 填写完整
- [ ] 发布包（tarball/zip）可生成

---

## 旧版基础设施（全部为参考材料，不构成开发进度）

> ⚠️ 以下所有内容均来自旧版开发，**不保证与新版 CRE 需求兼容**，不构成任何开发进度。可作为设计思路参考，开发时需先验证，可自由重构或重写。

| 模块 | 路径 | 说明 |
|------|------|------|
| 训练主循环（RL 部分） | `scripts/train.py` | 🔶 RL 训练逻辑可参考；其中 CRE hooks 为旧版，不可依赖 |
| 实际训练日志 | `logs/train_rollout_20260411_215734/` | 🔶 可作为 Phase 3 Dynamic Analysis 的测试数据，格式需验证 |
| 实际 eval 日志 | `logs/train_eval_rollout_20260411_215734/` | 🔶 同上 |
| CRE 日志核心 | `envs/cre_logging.py` | 🔶 旧版日志器，接口和字段需验证 |
| TensorDict 适配器 | `runtime_logging/training_log_adapter.py` | 🔶 旧版适配器 |
| 运行日志器 | `runtime_logging/logger.py` | 🔶 旧版 |
| Acceptance Check | `runtime_logging/acceptance.py` | 🔶 旧版，规则需与新版对齐 |
| Episode Writer | `runtime_logging/episode_writer.py` | 🔶 旧版 |
| Schema | `runtime_logging/schema.py` | 🔶 旧版 schema，新版可能需重新定义 |
| Eval 循环 | `scripts/eval.py` | 🔶 RL eval 逻辑可参考；CRE hooks 为旧版 |
| 旧版 spec 文件 | `cfg/spec_cfg/` | ❌ 已删除，不存在 |
| 旧版 CRE CLI 脚本 | `scripts/run_*` 系列 | ❌ 已删除，不存在 |

---

## 立即下一步（Phase 1 起步）

1. **阅读 `doc/CRE_v4.pdf`** — 理解 CRE 对 reward/constraint/policy spec 的格式要求，核对上方 Phase 总览是否准确
2. **设计 `reward_spec_v1.yaml` 字段** — 字段名、类型、单位、必填项，在 DECISIONS.md 记录设计依据
3. **设计 `constraint_spec_v1.yaml` 字段** — 约束名、类型、阈值、严重等级
4. **设计 `policy_spec_v1.yaml` 字段** — 动作空间、观测空间、执行频率
5. **建立 Spec 校验器** — schema 验证脚本，能对三份 spec 做格式和基础一致性检查
6. **更新 STATUS.md** — 逐条勾选 Phase 1 DoD，全部满足后将 Phase 1 标记为 ✅
