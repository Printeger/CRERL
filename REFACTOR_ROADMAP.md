# REFACTOR_ROADMAP.md — CRE PDF 对齐重构路线图

> 建立日期：2026-04-12  
> 权威来源：`doc/CRE_v4.pdf` v1.0（April 10, 2026）  
> 触发原因：2026-04-12 审计发现历史实现存在 14 处严重偏差，根本原因是 vibe coding agent 未充分阅读 PDF 即开始编码。  
> **本文件是所有 CRE 分析模块重构的唯一路线图，优先级高于 STATUS.md 中的旧 Phase 记录。**

---

## 一、已发现的偏差清单（14 处）

| 编号 | 偏差名称 | 严重程度 | 受影响文件 | 改动大小 |
|------|---------|---------|-----------|---------|
| DEV-01 | φ²_CR 计算错误（用 issue 计数代替边界距离比） | 🔴 严重 | `analyzers/semantic_analyzer.py` | 大 |
| DEV-02 | φ̄¹_EC 计算错误（用 issue 计数代替 KD 树覆盖率） | 🔴 严重 | `analyzers/semantic_analyzer.py` | 大 |
| DEV-03 | φ³_ER 永远为 None，完全缺失 | 🔴 严重 | `analyzers/semantic_analyzer.py` | 大 |
| DEV-04 | Ψ_CRE 权重错误（2 维 0.5/0.5，非 3 维 0.333/0.333/0.334） | 🔴 严重 | `analyzers/semantic_analyzer.py` | 小 |
| DEV-05 | M2 模块整体缺失（9 个估计器函数均未实现） | 🔴 严重 | 缺少 `analyzers/m2.py` | 大 |
| DEV-06 | M3 模块整体缺失（κ_CR、γ_EC、δ_ER 均未实现） | 🔴 严重 | 缺少 `analyzers/m3.py` | 大 |
| DEV-07 | Stage III Discrepancy Protocol 整体缺失 | 🔴 严重 | 缺少 `analyzers/discrepancy_protocol.py` | 大 |
| DEV-08 | Bootstrap CI（不确定性量化）完全缺失 | 🟡 中等 | `analyzers/semantic_analyzer.py` | 中 |
| DEV-09 | M4 语义分析用自创 Issue 结构替代 failure_hypothesis | 🟡 中等 | `analyzers/semantic_analyzer.py` | 中 |
| DEV-10 | M7 修复生成无候选集/过滤/排名/d_spec 计算 | 🔴 严重 | `repair/repair_generator.py` | 大 |
| DEV-11 | M8 验收只比较 issue 数，缺 C1–C4 完整检查 | 🟡 中等 | `repair/validator.py` | 大 |
| DEV-12 | DiagReport 核心数据结构缺失，各模块自创替代 | 🔴 严重 | 所有 analyzers/ + repair/ | 大 |
| DEV-13 | Pipeline Orchestrator（PO）完全缺失 | 🟡 中等 | 缺少 `pipeline/orchestrator.py` | 中 |
| DEV-14 | SpecS 不可变性原则未执行（in-place 修改 dict） | 🟢 轻微 | `repair/validator.py` | 小 |

**连锁关系**：DEV-01/02/03/05/06/07/12 均由同一根源引发——跳过 LLM-α（D-LLM-α 决策）后，agent 没有意识到这同时意味着需要设计轨迹驱动的替代估计器，而是用 issue 计数近似了事。

---

## 二、修正前的治理前置条件（不可跳过）

> 以下三个前置条件在开始任何 Phase 的编码之前均必须满足。违反则视为 Phase 未开始。

### 前置条件 FC-1：PDF 条款追溯表先行

在 `TRACEABILITY.md` 中，每个待实现函数必须先填写一行追溯记录（状态为 ❌），**再开始实现**。实现完成后将状态改为 ✅。

格式：
```
| PDF 章节         | 公式/函数名              | 实现文件              | 实现函数           | 合约测试文件                      | 状态 |
| Part II §3.2.2  | M2.compute_phi_cr2, Eq.11 | analyzers/m2.py  | compute_phi_cr2() | test_m2_contract.py::test_phi_cr2_* | ❌  |
```

### 前置条件 FC-2：核心数据结构先于算法冻结

Phase 0 必须先完成以下三个文件，**才能开始任何算法实现**：
- `analyzers/diag_report.py` — `DiagReport`、`SpecS`、`RewardDAG`、`Constraint`、`AmbiguityFlag`、`RepairProposal`、`AcceptanceVerdict`（全部 `@dataclass(frozen=True)`）
- `analyzers/cfg.py` — `CFG` 全局配置对象（按 PDF Table 4 完整字段）
- `analyzers/errors.py` — `CREError` 基类及全部错误码（按 PDF §11 Error Registry）

后续所有模块只能 **import** 这三个文件中的类，不得自创替代结构。

### 前置条件 FC-3：合约测试先于实现

每个函数实现前，必须先写对应的 PDF Test Standards（T1–Tn）为 pytest 用例（预期 fail）。
实现完成后，所有合约测试通过，才能在 TRACEABILITY.md 将状态改为 ✅。

---

## 三、防止新偏差的具体机制

| 风险类型 | 防护机制 | 触发时机 |
|---------|---------|---------|
| Agent 未读 PDF 直接编码 | 代码注释必须标注 PDF 公式编号，否则 review 拒绝 | 每次 PR/任务审查 |
| Agent 用近似替代精确公式 | 合约测试含数值精度断言（如 `assert abs(x - 0.0) < 1e-9`） | 合约测试阶段 |
| Agent 自创数据结构 | Phase 0 冻结所有 dataclass，后续只能 import | Phase 0 完成后即锁定 |
| 模块间接口漂移 | 每 Phase 结束前更新 INTERFACES.md，下一 Phase 必须先读 | Phase 交接时 |
| 破坏已有功能 | 每 Phase 结束后必须跑全量 pytest，新 test 不得让旧 test fail | Phase 结束时 |
| Ψ_CRE 权重不为 1 | CFG 对象启动时做权重检验，违反抛 CONFIG_WEIGHT_SUM_ERROR | 管线启动时 |
| Enhanced estimator 写入 canonical slot | `@supplementary_only` 装饰器 + 运行时检查，违反抛 CANONICAL_VIOLATION_ERROR | M3/M5 执行时 |

---

## 四、重构路线图（严格串行，不可跳步）

> 每个 Step 完成后，commander 必须 review 后才能推进下一步。

### Phase 0 — 基础设施（无算法，只有结构）

**目标**：冻结所有核心数据结构和配置，为后续所有 Phase 提供统一基础。

| Step | 任务 | PDF 依据 | 产物 |
|------|------|---------|------|
| 0.1 | 定义 `DiagReport`、`SpecS`、`RewardDAG`、`Constraint`、`AmbiguityFlag`、`RepairProposal`、`AcceptanceVerdict` | Part II §1.2 Core Data Schemas (pp.21–23) | `analyzers/diag_report.py` |
| 0.2 | 定义 `CFG` 全局配置对象（Table 4 全部字段） | Part II §1.3 (p.23–24) | `analyzers/cfg.py` |
| 0.3 | 定义 `CREError` 基类及全部错误码 | Part II §11 Error Code Registry (pp.49–51) | `analyzers/errors.py` |
| 0.4 | 将历史实现移入 legacy/ 目录 | — | `analyzers/legacy/`、`repair/legacy/` |
| 0.5 | 填写 TRACEABILITY.md 追溯表骨架（所有函数 ❌） | Part II Table 3 Module Registry | `TRACEABILITY.md` |

**DoD**：`analyzers/diag_report.py` 中所有 dataclass 均为 `frozen=True`；`CFG` 中 `w_cr + w_ec + w_er` 默认值之和 = 1.0；`CREError` 涵盖 PDF §11 全部错误码。

---

### Phase 1 — M1 Specification Parsing（canonical LLM-α + compatibility YAML adapter）

**目标**：恢复 Stage I 的 canonical `LLM-α` 解析链路——将 `NLInput` 解析为 `SpecS`，执行 ambiguity escalation 与 §2.1.3 的 symbolic pre-check；仓库现有 YAML 资产仅通过 compatibility adapter 复用，不得替代 canonical M1。

| Step | 任务 | PDF 依据 | 产物 |
|------|------|---------|------|
| 1.1 | 实现 `M1.parse_nl_input`（`NLInput -> SpecS`，canonical LLM-α） | Part II §2.1.1 (p.25) | `analyzers/m1.py` |
| 1.2 | 实现 `M1.detect_and_escalate_ambiguities`（ambiguity flags + escalation） | Part II §2.1.2 (p.26) | `analyzers/m1.py` |
| 1.3 | 实现 `M1.run_symbolic_precheck`（3 条 fatal 检查） | Part II §2.1.3 (p.26–27) | `analyzers/m1.py` |
| 1.4 | 保留 `parse_yaml_input` 作为 compatibility YAML adapter（不计入 canonical M1 完成） | Compatibility only；canonical 仍以 Part II §2.1 为准 | `analyzers/m1.py` |
| 1.5 | 写合约测试（T1–T4，含 ambiguity / escalation / precheck） | Part II §2.1 Test Standards | `unit_test/test_m1_contract.py` |

**DoD**：合约测试全部通过；`TRACEABILITY.md` M1 行状态改为 ✅。

---

### Phase 2 — M2 主估计器（需要轨迹数据）

**目标**：实现所有行为级估计器，包括 3 个 canonical reporter 和 5 个 supplementary estimator。

| Step | 任务 | PDF 依据 | 产物 |
|------|------|---------|------|
| 2.1 | 定义 `Trajectory` 数据结构 | Part II §3.1 (p.27) | `analyzers/m2.py` |
| 2.2 | 实现 `compute_phi_cr2`（Boundary-Seeking Score，**canonical**） | Part II §3.2.2, Eq.(11) (p.28) | `analyzers/m2.py` |
| 2.3 | 实现 `compute_phi_ec_j`（per-constraint KD 树覆盖率） | Part II §3.3.1, Eq.(12) (p.29) | `analyzers/m2.py` |
| 2.4 | 实现 `compute_phi_ec_bar`（mean/min 聚合，**canonical**） | Part II §3.3.2, Eq.(13) (p.30) | `analyzers/m2.py` |
| 2.5 | 实现 `compute_phi_er3`（reward-utility decoupling，**canonical**，用 done_type==1 作 oracle） | Part II §3.4.3, Eq.(18) (p.32–33) | `analyzers/m2.py` |
| 2.6 | 实现 5 个 supplementary 估计器（phi_cr1, phi_ec2, phi_ec3, phi_er1, phi_er2） | Part II §3.2.1, §3.3.3/4, §3.4.1/2 | `analyzers/m2.py` |
| 2.7 | 实现 `@supplementary_only` 装饰器（防止写入 canonical slot） | Part II §3.1 (p.27) | `analyzers/m2.py` |
| 2.8 | 写合约测试（所有函数的 T1–T6） | Part II §3.2–§3.4 Test Standards | `unit_test/test_m2_contract.py` |

**DoD**：合约测试全部通过，含数值精度验证；TRACEABILITY.md M2 全行 ✅。

---

### Phase 3 — M5 Ψ_CRE 综合评分

**目标**：实现正确的 3 维 Ψ_CRE 计算，含 Bootstrap CI 和双阈值标定。

| Step | 任务 | PDF 依据 | 产物 |
|------|------|---------|------|
| 3.1 | 实现 `M5.monotone_transform f(·)` | Part II §6.1.1, Eq.(27) (p.38) | `analyzers/m5.py` |
| 3.2 | 实现 `M5.compute_psi_cre`（3 维，w=0.333/0.333/0.334，权重检验） | Part II §6.1.2, Eq.(26) (p.38) | `analyzers/m5.py` |
| 3.3 | 实现 `M5.compute_bootstrap_ci`（BCa，B=1000） | Part II §6.1.3, Eq.(28) (p.39) | `analyzers/m5.py` |
| 3.4 | 实现 `M5.calibrate_thresholds`（τ_detect, τ_alarm） | Part II §6.1.4 (p.40) | `analyzers/m5.py` |
| 3.5 | 写合约测试 | Part II §6 Test Standards | `unit_test/test_m5_contract.py` |

**DoD**：合约测试通过；`w_cr + w_ec + w_er = 1.0` 启动检验生效；TRACEABILITY.md M5 ✅。

---

### Phase 4 — M4 语义分析（canonical LLM-β）

**目标**：恢复 `LLM-β` canonical 主链路，生成 `failure_hypothesis`（str）和 `repair_targets`（list[str]），并填入 `DiagReport` 的对应 canonical 字段。

| Step | 任务 | PDF 依据 | 产物 |
|------|------|---------|------|
| 4.1 | 实现 `M4.generate_failure_hypothesis`（LLM-β） | Part II §7.1, p.41 | `analyzers/m4.py` |
| 4.2 | 实现 `repair_targets` 优先级排序 | Part II §7.1 | `analyzers/m4.py` |
| 4.3 | 写合约测试（含 `SemanticOverwriteError` 守护测试） | Part II §7 Test Standards | `unit_test/test_m4_contract.py` |

**DoD**：合约测试通过；M4 不修改任何数值字段（守护测试验证）；TRACEABILITY.md M4 ✅。

---

### Phase 5 — M7 修复生成（含 d_spec 和最小编辑过滤）

**目标**：恢复 `LLM-δ` canonical 修复候选生成，并实现符合 PDF 的 minimality 过滤和两阶段排名。

| Step | 任务 | PDF 依据 | 产物 |
|------|------|---------|------|
| 5.1 | 实现 `M7.compute_spec_edit_distance`（Def 6.2, Eq.29） | Part II §8.1.1, p.42 | `repair/m7.py` |
| 5.2 | 实现 `M7.generate_repair_proposals`（LLM-δ；K'=2K 候选，使用 V_R 词汇表） | Part II §8.1.2, p.42–43 | `repair/m7.py` |
| 5.3 | 实现 `M7.filter_by_minimality`（d_spec ≤ η_edit=0.20） | Part II §8.1.3, p.43 | `repair/m7.py` |
| 5.4 | 实现 `M7.rank_proposals`（Stage 1: rollout 估算；Stage 2: predicted_delta_psi） | Part II §8.1.4, p.43–44 | `repair/m7.py` |
| 5.5 | 写合约测试 | Part II §8 Test Standards | `unit_test/test_m7_contract.py` |

**DoD**：合约测试通过；每个提案携带 `semantic_justification`（≤200 tokens）；TRACEABILITY.md M7 ✅。

---

> 注：PDF Part II §11 的 Error Registry 含 `M6_HYPOTHESIS_UNAVAILABLE`。当前路线图尚未把 M6 单独展开为独立 Phase/Step，这表示文档仍有不完整处；后续必须补齐其归属，不得继续忽略该模块存在性。

### Phase 6 — M8 验收（C1–C4 完整检查；canonical LLM-ε）

**目标**：实现四条验收标准和修复循环控制（最多 N_max=5 轮）。

| Step | 任务 | PDF 依据 | 产物 |
|------|------|---------|------|
| 6.1 | 实现 C1（Ψ_CRE(S') > Ψ_CRE(S)） | Part II §9.1.1, Eq.(30), p.45 | `repair/m8.py` |
| 6.2 | 实现 C4（d_spec(S, S') ≤ η_edit） | Part II §9.1.1, Eq.(33), p.45 | `repair/m8.py` |
| 6.3 | 实现 C2/C3 stub（标注需要 rollout，当前保守返回 True） | Part II §9.1.1, Eq.(31–32), p.45 | `repair/m8.py` |
| 6.4 | 实现 `M8.verify_semantic_consistency`（LLM-ε，s_sem ≥ 0.80） | Part II §9.1.2, p.46 | `repair/m8.py` |
| 6.5 | 实现 `M8.run_acceptance_loop`（N_max=5 轮，HARD_REJECT） | Part II §9.1.3, p.46–47 | `repair/m8.py` |
| 6.6 | 写合约测试 | Part II §9 Test Standards | `unit_test/test_m8_contract.py` |

**DoD**：合约测试通过；N_max 循环可验证；TRACEABILITY.md M8 ✅。

---

### Phase 7 — Pipeline Orchestrator

**目标**：实现 PO，按 PDF 规定的执行顺序调度所有模块，管理 AuditTrail 和修复循环。

| Step | 任务 | PDF 依据 | 产物 |
|------|------|---------|------|
| 7.1 | 实现 `PO.run_cre_pipeline`（执行顺序：M1→M2→M3→[DP]→M5→M4→[loop:M7→M8]） | Part II §10.1.1, p.48 | `pipeline/orchestrator.py` |
| 7.2 | 实现 `PO.audit_trail_schema` 和 AuditTrail 追加 | Part II §10.1.2, p.49 | `pipeline/orchestrator.py` |
| 7.3 | 实现权重检验（CONFIG_WEIGHT_SUM_ERROR）和 enhanced_estimators_enabled 开关 | Part II §1.3 Table 4 | `pipeline/orchestrator.py` |
| 7.4 | 端到端集成测试（含 benchmark suite 通过） | Part II §12 Integration Test Suite | `unit_test/test_pipeline_e2e.py` |

**DoD**：端到端测试通过；benchmark clean_nominal→alarm=False, injected_cr/ec/er→alarm=True（含 E-R 维度）；TRACEABILITY.md PO ✅。

---

### Phase 8 — M3 + Stage III（可选，依赖 Isaac Sim）

**目标**：实现机制层估计器和 Discrepancy Protocol（需要可微策略和 critic）。

| Step | 任务 | PDF 依据 | 产物 |
|------|------|---------|------|
| 8.1 | 实现 `M3.compute_kappa_cr`（梯度冲突分，需 PyTorch 可微策略） | Part II §4.1.1, Eq.(19), p.33–34 | `analyzers/m3.py` |
| 8.2 | 实现 `M3.compute_gamma_ec`（双模拟软覆盖，需 BisimulationModel） | Part II §4.1.2, Eq.(20), p.34 | `analyzers/m3.py` |
| 8.3 | 实现 `M3.compute_delta_er`（梯度漂移，需 critic） | Part II §4.1.3, Eq.(21), p.34–35 | `analyzers/m3.py` |
| 8.4 | 实现 Stage III Discrepancy Protocol（DP.compute_discrepancy, case_a/b_handler） | Part II §5, p.35–37 | `analyzers/discrepancy_protocol.py` |

> ⚠️ Phase 8 依赖真实训练环境（Isaac Sim + PyTorch 可微策略），在 NavRL 环境中可能无法完整运行。优先级最低，可在其他 Phase 完成后再启动。

---

## 五、每个 Step 的标准执行协议（Commander 发命令模板）

每条 agent 命令必须包含以下五段：

```
【1. 读 PDF】请先读 doc/CRE_v4.pdf [精确章节和页码]
【2. 读现有代码】请读 [具体文件路径]（了解上下文）
【3. 写什么】实现以下函数，签名如下：[精确签名]
【4. 合约测试】实现前先写 PDF Test Standards T1–Tn 为 pytest 用例（预期 fail）；实现后通过
【5. 禁止事项】不得绕过 PDF 公式，不得自创数据结构，代码注释必须标注 PDF 公式编号
```

---

## 六、目录结构变化（重构后）

```
analyzers/
    legacy/              ← 历史实现（只读参考）
        static_analyzer.py
        dynamic_analyzer.py
        semantic_analyzer.py
        report_generator.py
    diag_report.py       ← Phase 0：核心数据结构（frozen dataclasses）
    cfg.py               ← Phase 0：全局配置（CFG singleton）
    errors.py            ← Phase 0：CREError 体系
    m1.py                ← Phase 1：Spec Parsing（`parse_nl_input` / LLM-α canonical；`parse_yaml_input` compatibility-only）
    m2.py                ← Phase 2：Primary Estimators（M2.compute_phi_*）
    m3.py                ← Phase 8：Enhanced Estimators（M3.compute_kappa/gamma/delta）
    m4.py                ← Phase 4：Semantic Analysis（M4.generate_failure_hypothesis）
    m5.py                ← Phase 3：Composite Scoring（M5.compute_psi_cre）
    discrepancy_protocol.py  ← Phase 8：Stage III DP
repair/
    legacy/              ← 历史实现（只读参考）
        repair_generator.py
        validator.py
    m7.py                ← Phase 5：Repair Generation（M7.*）
    m8.py                ← Phase 6：Acceptance & Validation（M8.*）
pipeline/
    orchestrator.py      ← Phase 7：Pipeline Orchestrator（PO.*）
unit_test/
    test_m1_contract.py  ← Phase 1 合约测试
    test_m2_contract.py  ← Phase 2 合约测试
    test_m3_contract.py  ← Phase 8 合约测试
    test_m4_contract.py  ← Phase 4 合约测试
    test_m5_contract.py  ← Phase 3 合约测试
    test_m7_contract.py  ← Phase 5 合约测试
    test_m8_contract.py  ← Phase 6 合约测试
    test_pipeline_e2e.py ← Phase 7 端到端测试
    test_env/            ← 现有测试（保持不变，继续通过）
```

---

## 七、当前状态

| 重构阶段 | 状态 | 说明 |
|---------|------|------|
| 治理前置条件制定 | ✅ 完成 | 本文档 + AGENTS.md + HANDBOOK.md + TRACEABILITY.md 已更新 |
| Phase 0 — 基础设施 | ⏳ 待开始 | 等待 commander 发出 Phase 0 命令 |
| Phase 1 — M1 | ⏳ 待开始 | — |
| Phase 2 — M2 | ⏳ 待开始 | — |
| Phase 3 — M5 | ⏳ 待开始 | — |
| Phase 4 — M4 | ⏳ 待开始 | — |
| Phase 5 — M7 | ⏳ 待开始 | — |
| Phase 6 — M8 | ⏳ 待开始 | — |
| Phase 7 — PO  | ⏳ 待开始 | — |
| Phase 8 — M3+DP | ⏳ 待开始（依赖 Isaac Sim） | — |
