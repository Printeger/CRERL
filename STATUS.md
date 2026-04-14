# STATUS.md — Phase & 模块完成状态

最后更新：2026-04-15

---

## 重构优先快照（2026-04-15）

- 当前重构 Phase：Phase 0 — 基础设施
- 当前 Step：Step 0.4 — 将历史实现移入 `legacy/` 目录（已完成）
- [x] `SpecS` 已在 `isaac-training/training/analyzers/diag_report.py` 实现为 `@dataclass(frozen=True)`，并完成只读容器归一化（禁止 in-place mutation）；对应合约测试已通过，`TRACEABILITY.md` 已更新
- [x] `NLInput` 已按 `doc/CRE_v4.pdf` Part II §1.2 p.21 完成：`isaac-training/training/analyzers/diag_report.py` 已实现 frozen passive schema、`isaac-training/training/unit_test/test_diag_report_contract.py` 的 `test_nlinput_contract_*` 合约测试已通过，`TRACEABILITY.md` 已更新为 `✅`
- [x] `Constraint` 已按 `doc/CRE_v4.pdf` Part II §1.2 p.22 完成：`isaac-training/training/analyzers/diag_report.py` 已实现 frozen canonical schema 校验，`isaac-training/training/unit_test/test_diag_report_contract.py` 的 `test_constraint_contract_*` 合约测试已通过，`TRACEABILITY.md` 已更新为 `✅`
- [x] `RewardDAG` 已按 `doc/CRE_v4.pdf` Part II §1.2 p.22 完成：`isaac-training/training/analyzers/diag_report.py` 已实现 frozen canonical schema、节点/边容器只读归一化与 PDF 锚点注释，`isaac-training/training/unit_test/test_diag_report_contract.py` 的 `test_reward_dag_contract_*` 合约测试已通过，`TRACEABILITY.md` 已更新为 `✅`
- [x] `AmbiguityFlag` 已按 `doc/CRE_v4.pdf` Part II §1.2 p.22 完成：`isaac-training/training/analyzers/diag_report.py` 已实现 frozen passive schema、canonical flag_type 枚举 / dot-separated JSON path `location` / `impact_score` 校验与 PDF 锚点注释，`isaac-training/training/unit_test/test_diag_report_contract.py` 的 `test_ambiguity_flag_contract_*` 合约测试已通过，`TRACEABILITY.md` 已更新为 `✅`
- [x] `DiagReport` 已按 `doc/CRE_v4.pdf` Part II §1.2 pp.22–23 完成：`isaac-training/training/analyzers/diag_report.py` 已实现 frozen canonical report schema、`spec_id/timestamp` 校验、canonical reporters 与 `psi_cre` 的 `[0,1]` 约束、`ci_95`/`flags`/`discrepancy`/`failure_hypothesis`/`repair_targets` 字段校验与 PDF 锚点注释，`isaac-training/training/unit_test/test_diag_report_contract.py` 的 `test_diag_report_contract_*` 合约测试已通过，`TRACEABILITY.md` 已更新为 `✅`
- [x] `RepairProposal` 已按 `doc/CRE_v4.pdf` Part II §1.2 p.23 完成：`isaac-training/training/analyzers/diag_report.py` 已实现 frozen canonical repair proposal schema、`proposal_id/spec_prime/operator_class/declared_side_effects/semantic_justification/predicted_delta_psi/rough_delta_psi` 字段校验、只读 side-effects 归一化与 PDF 锚点注释，`isaac-training/training/unit_test/test_diag_report_contract.py` 的 `test_repair_proposal_contract_*` 合约测试已通过，`TRACEABILITY.md` 已更新为 `✅`
- [x] `AcceptanceVerdict` 已按 `doc/CRE_v4.pdf` Part II §1.2 p.23 完成：`isaac-training/training/analyzers/diag_report.py` 已实现 frozen canonical acceptance verdict schema、`accepted/c1_pass/c2_pass/c3_pass/c4_pass/s_sem/intent_preserved/rejection_feedback` 字段校验与 PDF 锚点注释，`isaac-training/training/unit_test/test_diag_report_contract.py` 的 `test_acceptance_verdict_contract_*` 合约测试已通过，`TRACEABILITY.md` 已更新为 `✅`
- [x] `CFG` 已按 `doc/CRE_v4.pdf` Part II §1.3 Table 4 pp.23–24 完成：`isaac-training/training/analyzers/cfg.py` 已实现 frozen `CFGSchema` + module-level `CFG` singleton、Table 4 默认值、字段级类型/值域校验、`ec_aggregation_mode` 枚举约束、`w_cr + w_ec + w_er = 1.0` 与严格正权重校验，并已通过 `ConfigWeightSumError` 接入正式错误体系；`isaac-training/training/unit_test/test_diag_report_contract.py` 的 `T-CFG-*` 合约测试已通过，`TRACEABILITY.md` 已更新为 `✅`
- [x] `CREError` 已按 `doc/CRE_v4.pdf` Part II §11 pp.49–51 完成：`isaac-training/training/analyzers/errors.py` 已实现 `CREError` 统一基类、`CREErrorCode` 62 个 Table 5 字符串常量、`ErrorDescriptor` + `ERROR_REGISTRY` canonical registry、全部错误码对应的正式子类注册，以及 `ConfigWeightSumError` 对 `cfg.py` 的正式接线；`isaac-training/training/unit_test/test_diag_report_contract.py` 的 `T-ERR-*` 合约测试已覆盖 Table 5 全部 62 行的逐条 `severity/module/description` 对齐，并显式验证 `CONFIG_WEIGHT_SUM_ERROR` 的 `< 1e-9` / `>= 1e-9` 容差边界；`pytest -q` 全量测试 `60 passed, 0 failed`，`TRACEABILITY.md` 第 22 行已更新为 `✅`
- [x] `parse_yaml_input()` 已保留为 compatibility YAML adapter：`isaac-training/training/analyzers/m1.py` 现可将四份结构化 spec 解析为 frozen `SpecS`，为 reward/constraint/policy/environment 执行结构校验，并使用正式 `CREError` 错误码映射 `SPEC_PARSE_FAILURE` / `NULL_REWARD` / `EMPTY_ENV_SET`；但它**不再**被视为 `doc/CRE_v4.pdf` Part II §2.1.1 的 canonical `M1.parse_nl_input` 完成项，`TRACEABILITY.md` 第 30 行已回退为 `parse_nl_input() -> ❌`
- [x] strict PDF LLM architecture correction 的主文档收口已完成：`DECISIONS.md` 已通过 `D-I21` / `D-I22` / `D-I23` 恢复 M1/LLM-α、M4/LLM-β、M7/LLM-δ、M8/LLM-ε 为 canonical 主链路，并将 `CREReport` / `RepairPatch` / `RepairResult` / `ValidationResult` 旧路径降级为 historical artifacts；`INTERFACES.md`、`REFACTOR_ROADMAP.md`、`isaac-training/training/README.md`、`doc/API_KEY.md`、Hydra `cfg/llm/comp_openai.yaml` 与 `analyzers/llm_gateway.py` 已同步修正，且 README 中旧 `semantic_analyzer.py` / `repair_result.json` / `validation_passed` 主教程已迁入 historical/legacy 语境；`parse_yaml_input()` 明确降级为 compatibility only，不再冒充 canonical M1
- [x] Step 0.4 legacy 清场已完成：`static_analyzer.py`、`dynamic_analyzer.py`、`semantic_analyzer.py`、`report_generator.py`、`repair_generator.py`、`validator.py` 已物理迁入 `isaac-training/training/analyzers/legacy/` 与 `isaac-training/training/repair/legacy/`；历史脚本、测试与文档引用已同步改为 legacy 路径，不再冒充 strict PDF canonical 主链
- 立即下一步：进入 canonical Phase 1 / Step 1.1，按 contract-first 实现 `M1.parse_nl_input()`；`parse_yaml_input()` 仅保留 compatibility adapter
- 说明：下方旧版“Phase 1–10 已完成”记录为历史状态，不再代表当前 CRE PDF 对齐重构进度；当前应以 `REFACTOR_ROADMAP.md`、`TRACEABILITY.md` 和本节为准

---

## 旧版历史状态（待整体重写，不再代表当前重构进度）

Phase 1 的四份 v1 spec、`analyzers/spec_validator.py`、历史 Phase 2 的 `analyzers/legacy/static_analyzer.py` 与历史 Phase 3 的 `analyzers/legacy/dynamic_analyzer.py` 已完成，并已补齐对应单元测试。  
历史 Phase 4 的 `analyzers/legacy/semantic_analyzer.py` 与 `unit_test/test_env/test_semantic_analyzer.py`、历史 Phase 5 的 `analyzers/legacy/report_generator.py` 与 `unit_test/test_env/test_report_generator.py`、历史 Phase 6 的 `repair/legacy/repair_generator.py` 与 `unit_test/test_env/test_repair_generator.py`、历史 Phase 7 的 `repair/legacy/validator.py` 与 `unit_test/test_env/test_validator.py`、历史 Phase 8 的 `train.py` / `train.yaml` 集成改动与 `unit_test/test_env/test_integration_pipeline.py`、Phase 9 的 benchmark suite（`cfg/benchmark_cfg/`、`scripts/run_benchmark.py`、`unit_test/test_env/test_benchmark.py`），以及 Phase 10 的发布文档与打包脚本（`TRACEABILITY.md`、`README.md`、`scripts/build_release.sh`）均已完成；发布包 `release/cre_suite_v1.0.0.tar.gz` 已成功生成并验包。

> **Phase 定义权威来源**：`doc/CRE_v4.pdf`。下方 Phase 总览是基于 CRE_v4.pdf 的初步规划，**开发前必须先读 PDF 核对，如有出入以 PDF 为准并更新本文件**。

---

## Phase 总览与 DoD

### Phase 1 — Spec 设计 ✅ 已完成

**目标**：定义四份 YAML spec 文件的完整格式，作为后续所有分析的输入合约。

**DoD（以下全部满足才算完成）：**
- [x] `cfg/spec_cfg/reward_spec_v1.yaml` 存在，包含：字段名、类型、单位、必填项、版本号
- [x] `cfg/spec_cfg/constraint_spec_v1.yaml` 存在，包含：约束名、类型、阈值、严重等级
- [x] `cfg/spec_cfg/policy_spec_v1.yaml` 存在，包含：动作空间、观测空间、执行频率
- [x] `cfg/spec_cfg/env_spec_v1.yaml` 存在，包含：`E_tr`/`E_dep` 声明、`scene_families`、`shift_operators`、`generator_seeds`、`env_cfg_refs`
- [x] 四份文件有 JSON Schema 或等效的 schema 校验器可通过
- [x] `DECISIONS.md` 中有关于 spec 格式设计依据的记录

> 注：阻塞性决策 `D-S1` / `D-S2` / `D-S3` 已于 2026-04-12 记录；environment spec 处理见 `D-S4-env`，跳过 LLM-α 解析层的偏差记录见 `D-LLM-α`。

**可验证产物**：
```
cfg/spec_cfg/reward_spec_v1.yaml
cfg/spec_cfg/constraint_spec_v1.yaml
cfg/spec_cfg/policy_spec_v1.yaml
cfg/spec_cfg/env_spec_v1.yaml
isaac-training/training/analyzers/__init__.py
isaac-training/training/analyzers/spec_validator.py
```

---

### Phase 2 — Spec 校验与静态分析 ✅ 已完成

**目标**：基于 Phase 1 的四份 spec，检测静态矛盾（C-R 冲突、E-C 不匹配、E-R 不匹配）。

**依赖**：Phase 1 全部 DoD 已满足。

**DoD：**
- [x] `analyzers/` 包存在，可 `import analyzers`
- [x] 输入：四份 spec v1 文件；输出：结构化静态分析报告（JSON/YAML）
- [x] 能检测至少以下三类问题：C-R 冲突、E-C 不匹配、E-R 不匹配
- [x] `INTERFACES.md` 中有 Phase 2 分析函数的签名记录
- [x] 单元测试通过（含至少一个阳性案例：输入有冲突的 spec，期望报告含对应问题）

**可验证产物**：
```
analyzers/__init__.py
analyzers/spec_validator.py
analyzers/legacy/static_analyzer.py
unit_test/test_env/test_static_analyzer.py  （通过）
analysis/static/<bundle>/  （运行一次后产生）
```

---

### Phase 3 — Dynamic Analysis ✅ 已完成

**目标**：从真实运行日志中检测动态行为与 spec 的不一致。

**依赖**：Phase 2 DoD 已满足。

**DoD：**
- [x] 输入：静态分析 bundle + 运行日志目录；输出：动态分析报告
- [x] 能读取 `logs/` 下的旧版日志（或新版日志），字段映射决策已在 `DECISIONS.md` 记录
- [x] 单元测试通过

**可验证产物**：
```
analyzers/legacy/dynamic_analyzer.py
unit_test/test_env/test_dynamic_analyzer.py  （通过）
```

---

### Phase 4 — Semantic Analysis ✅ 已完成

**目标**：跨模态语义不一致检测（结合静态+动态结果做语义推断）。

**依赖**：Phase 3 DoD 已满足。

**DoD：**
- [x] 输入：静态 bundle + 动态 bundle；输出：语义分析报告
- [x] 单元测试通过

**可验证产物**：
```
analyzers/legacy/semantic_analyzer.py
unit_test/test_env/test_semantic_analyzer.py  （通过）
```

---

### Phase 5 — Report Generation ✅ 已完成

**目标**：将前三阶段分析结果汇总为结构化 CRE 报告。

**依赖**：Phase 4 DoD 已满足。

**DoD：**
- [x] 输出报告格式在 `INTERFACES.md` 中有定义
- [x] 报告含问题列表、严重等级、可追溯到 spec 字段
- [x] 单元测试通过

**可验证产物**：
```
analyzers/legacy/report_generator.py
unit_test/test_env/test_report_generator.py  （通过）
```

---

### Phase 6 — Repair ✅ 已完成

**目标**：基于 Phase 5 报告，生成规则驱动的自动修复建议（patch）。

**依赖**：Phase 5 DoD 已满足。

**DoD：**
- [x] 输入：CRE 报告；输出：修复补丁列表（可应用到 spec 文件）
- [x] 单元测试通过

**可验证产物**：
```
repair/__init__.py
repair/legacy/repair_generator.py
unit_test/test_env/test_repair_generator.py  （通过）
```

---

### Phase 7 — Validation ✅ 已完成

**目标**：验证修复后的 spec 是否消除了原有问题。

**依赖**：Phase 6 DoD 已满足。

**DoD：**
- [x] 输入：修复后 spec；输出：验证报告（对比修复前后）
- [x] 修复后的 spec 通过 Phase 2 静态分析（无原问题）
- [x] 单元测试通过

**可验证产物**：
```
repair/legacy/validator.py
unit_test/test_env/test_validator.py  （通过）
```

---

### Phase 8 — Integration ✅ 已完成

**目标**：将 CRE 分析流程接入训练主循环（`train.py`），实现运行时自动记录和 acceptance check。

**依赖**：Phase 7 DoD 已满足。

**DoD：**
- [x] `train.py` 中集成新版 CRE logging（接口设计符合 `INTERFACES.md`）
- [x] 训练结束后自动生成 CRE 报告并写入 WandB
- [x] acceptance check 通过后训练才视为合格运行
- [x] 集成测试通过

**可验证产物**：
```
cfg/train.yaml
scripts/train.py
unit_test/test_env/test_integration_pipeline.py  （通过）
```

---

### Phase 9 — Benchmark Suite ✅ 已完成

**目标**：通过注入已知缺陷的 spec 验证检测器的有效性。

**依赖**：Phase 8 DoD 已满足。

**DoD：**
- [x] `cfg/benchmark_cfg/` 存在，含 `clean_nominal` 和三类注入 case
- [x] `clean_nominal` 基准 case 可稳定运行，并在当前实现下得到 `alarm=False`
- [x] `injected_cr` / `injected_ec` 在当前 benchmark 中已验证 `alarm=True`
- [x] `injected_er` → 检测到 issues（`total_issues > 0`）；`alarm` 受 `phi_er=None` 限制，偏差已记录于 `D-BM1`
- [x] 结果可复现，且 benchmark 单元测试通过

> 注：当前 legacy `semantic_analyzer.py` 已将 `phi_cr` 计算扩展为 `static + dynamic` 的 C-R issues，并使用 reward term 数量归一化；`phi_er` 仍固定为 `None`，因此 `injected_er` 当前的验收标准仍是“可检出 semantic issue”，而非 `alarm=True`。

**可验证产物**：
```
cfg/benchmark_cfg/
scripts/run_benchmark.py
unit_test/test_env/test_benchmark.py  （通过）
```

---

### Phase 10 — Release Packaging ✅ 已完成

**目标**：打包所有产物，产出可发布的 CRE 分析套件。

**依赖**：Phase 9 DoD 已满足。

**DoD：**
- [x] `TRACEABILITY.md` 填写完整（spec 字段 → 实现代码的映射）
- [x] `README.md` 填写完整
- [x] 发布包（tarball/zip）可生成

**可验证产物**：
```
TRACEABILITY.md
README.md
scripts/build_release.sh
release/cre_suite_v1.0.0.tar.gz
```

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

## 开发出现以下偏差：

### CRE 实现偏差审计报告

  对照来源：CRE_v4.pdf Part I §1–8 + Part II §1–4（已读完）

  ---
####  偏差 1：φ²_CR 计算方式完全错误【严重】

  PDF 要求（Part I §3.3，Eq.11；Part II §3.2.2 M2.compute_phi_cr2）：
  φ²_CR = max(0, 1 − D*/D^unif)
  需要两组轨迹：traj_pistar（π* 下的轨迹）和 traj_unif（随机基准策略 π_unif
  的轨迹），计算两者到 hard constraint 边界 ∂K_j
  的最小欧氏距离期望值之比。这是一个轨迹级几何量。

  当前实现（analyzers/legacy/semantic_analyzer.py line 162）：
  phi_cr = _clamp01(min(len(cr_issues) / total_terms, 1.0))
  用issue 计数除以 reward term 数量近似。这是纯粹的启发式指标，与 PDF
  公式没有任何数学关系。

  受影响文件：analyzers/legacy/semantic_analyzer.py（run_semantic_analysis）
  改动大小：大——需要引入轨迹数据作为输入，实现边界距离计算
  连锁偏差：φ²_CR 输入 Ψ_CRE，Ψ_CRE 计算结果因此不可信

  ---
####  偏差 2：φ̄¹_EC 计算方式完全错误【严重】

  PDF 要求（Part I §3.4，Eq.12–13；Part II §3.3.1 M2.compute_phi_ec_j）：
  φ^(1,j)_EC = |{s∈K_j | ∃τ∼π_ref in D_{E_tr} : s∈τ}| / |K_j|
  需要参考策略 π_ref 的轨迹数据集（D_{E_tr}），用 KD 树近邻查找（半径
  critical_region_radius=0.10）对每个 hard constraint 做蒙特卡洛覆盖率估计，|K_j|
  通过 MC 采样（n_mc_kj=1000 次）估计。然后用 mean/min 模式聚合。

  当前实现（analyzers/legacy/semantic_analyzer.py line 169）：
  phi_ec = _clamp01(1.0 - min(len(ec_issues) / max(total_constraints, 1), 1.0))
  用 issue 计数除以约束总数近似。与 PDF 公式毫无关系。

  受影响文件：analyzers/legacy/semantic_analyzer.py
  改动大小：大——需要轨迹数据、KD 树、MC 采样、per-constraint 覆盖率计算
  连锁偏差：同偏差 1

  ---
#### 偏差 3：φ³_ER 永远为 None，完全缺失【严重】

  PDF 要求（Part I §3.5，Eq.18；Part II §3.4.3 M2.compute_phi_er3）：
  φ³_ER = ½(1 − ρ_RU(π*; E_dep))
  需要：
  1. 跨 E_dep 各部署环境的归一化累积 reward R_norm(π*; e_i)
  2. 独立于 R 的 utility oracle U(π; e)（task-completion flag 或其他）
  3. 计算 Pearson 相关系数 ρ_RU 后代入公式

  当前实现（analyzers/legacy/semantic_analyzer.py line 170）：
  phi_er = None  # 永远跳过
  以"无 utility oracle"为由完全跳过。但 PDF §3.6 明确说明可用 done_type==1（success
  flag）作为 oracle（§CRE_v4_summary.md 也已记录这个替代方案）。done_type==1 独立于
  reward，满足 Assumption 3.2。

  受影响文件：analyzers/legacy/semantic_analyzer.py
  改动大小：大——需要实现 utility oracle（done_type==1 作为 U），并从 E_dep
  各环境收集 reward/utility score
  连锁偏差：Ψ_CRE 公式中 w_ER 项永远为 0，benchmark 中 injected_er 无法触发 alarm

  ---
#### 偏差 4：Ψ_CRE 权重错误（2 维而非 3 维）【严重】

  PDF 要求（Part I §5.2，Eq.26；CFG Table 4）：
  Ψ_CRE = 1 − [w_CR·f(φ²_CR) + w_EC·f(1−φ̄¹_EC) + w_ER·f(φ³_ER)]
  w_CR = w_EC = 0.333, w_ER = 0.334（和为 1.0）
  三维等权重，且 PDF Part II §1.3 要求启动时验证 w_cr + w_ec + w_er = 1.0（误差 <
  10⁻⁹），否则 CONFIG_WEIGHT_SUM_ERROR。

  当前实现（analyzers/legacy/semantic_analyzer.py line 172–174）：
  w_cr = 0.5
  w_ec = 0.5
  psi_cre = _clamp01(1.0 - (w_cr * _f(phi_cr) + w_ec * _f(1.0 - phi_ec)))
  只有 2 维，权重 0.5+0.5=1.0，phi_er 项被丢弃，没有权重检验。

  受影响文件：analyzers/legacy/semantic_analyzer.py
  改动大小：小（权重改值）；依赖偏差 3 先修复
  连锁偏差：Ψ_CRE 数值偏低（因为少算一项），alarm 触发条件失真

  ---
#### 偏差 5：M2 模块完全缺失（所有一次估计器均未实现）【严重】

  PDF 要求（Part II §3）：M2 是独立模块，包含 9 个函数：
  - compute_phi_cr1（Reward-Risk 相关，supplementary）
  - compute_phi_cr2（Boundary-Seeking Score，canonical）
  - compute_phi_ec_j（per-constraint 覆盖率）
  - compute_phi_ec_bar（聚合，mean/min 两种模式）
  - compute_phi_ec2（constraint activation frequency，supplementary）
  - compute_phi_ec3（constraint diversity entropy，supplementary）
  - compute_phi_er1（deployment utility gap，supplementary）
  - compute_phi_er2（deployment reward gap，supplementary）
  - compute_phi_er3（reward-utility decoupling，canonical）

  输入均为轨迹数据（list[Trajectory]），输出为 float。

  当前实现：analyzers/ 下完全没有 primary_estimators.py 或等效模块。偏差 1–4
  中的近似计算被混入 analyzers/legacy/semantic_analyzer.py。

  受影响文件：缺少 analyzers/primary_estimators.py（或 m2.py）
  改动大小：大——需新建模块，实现全部 9 个函数

  ---
#### 偏差 6：M3（Enhanced Estimators）完全缺失【严重】

  PDF 要求（Part II §4）：M3 实现三个机制层估计器：
  - compute_kappa_cr（梯度冲突分 κ̃_CR，需要可微策略）
  - compute_gamma_ec（双模拟软覆盖 γ̃_EC，需要 BisimulationModel）
  - compute_delta_er（梯度漂移 δ̃_ER，需要 critic）

  关键约束：M3 输出只能路由到 Stage III Discrepancy Protocol，不得写入 DiagReport 的
   canonical slots（phi_cr2/phi_ec_bar/phi_er3），否则 CANONICAL_VIOLATION_ERROR。

  当前实现：完全缺失。无 enhanced_estimators.py 或等效模块。

  受影响文件：缺少 analyzers/enhanced_estimators.py（或 m3.py）
  改动大小：大——但 κ_CR 需要可微策略（PyTorch 梯度），γ_EC 需要
  BisimulationModel，δ_ER 需要 critic；这三个在本项目中优先级最低

  ---
#### 偏差 7：Stage III Discrepancy Protocol 完全缺失【严重】

  PDF 要求（Part I §4；Part II §5 DP.*）：包含四个函数：
  - DP.compute_discrepancy：计算 Δ_d = |φ̂_d − κ̂_d|
  - DP.case_a_handler：LATENT_INCONSISTENCY — 扩展不确定区间 σ_d
  - DP.case_b_handler：CRITIC_QUALITY_WARN — 保持 canonical 值，安排复查
  - DP.run_protocol：主入口，仅在 M2+M3 均可用时激活

  触发条件：Δ_d > η_disc（默认 0.15）。Case A/B 分别处理不同方向的偏差。

  当前实现：完全缺失。analyzers/legacy/semantic_analyzer.py 跳过了整个 Stage III。

  受影响文件：缺少 analyzers/discrepancy_protocol.py（或 dp.py）
  改动大小：大（但依赖 M3 完成后才能完整测试）

  ---
#### 偏差 8：Bootstrap CI（不确定性量化）完全缺失【中等】

  PDF 要求（Part I §5.3，Eq.28；Part II §6.1.3 M5.compute_bootstrap_ci）：
  CI_95(φ̂_d) = [φ̂_d^(α₁), φ̂_d^(α₂)]
  B=1000 次轨迹重采样，BCa（Bias-Corrected accelerated）方法。结果存入
  DiagReport.ci_95，Stage III Case A 的不确定区间扩展依赖此 CI。

  当前实现：无任何 bootstrap 实现。SemanticReport 无 ci_95 字段。

  受影响文件：analyzers/legacy/semantic_analyzer.py（缺失 ci_95 字段）；缺少独立的
  bootstrap 函数
  改动大小：中——bootstrap 本身不难，但需要有轨迹数据才能重采样

  ---
#### 偏差 9：M4（LLM-β 语义分析）用规则代替，但规则设计不符 PDF【中等】

  PDF 要求（Part I §5.4；Part II §7 M4.generate_failure_hypothesis）：
  LLM-β 的唯一职责是生成：(1) 自然语言失效假说 failure_hypothesis: str；(2)
  修复优先级列表 repair_targets: list[str]。它不修改任何数值字段，结果存入
  DiagReport.failure_hypothesis 和 DiagReport.repair_targets，供 M7 使用。

  当前实现（analyzers/legacy/semantic_analyzer.py）：
  - 用规则驱动生成 SemanticIssue 列表（SEM-CR-COMPOSITE、SEM-EC-COVERAGE
  等），这是额外创造的数据结构，PDF 中不存在
  - SemanticReport 无 failure_hypothesis 和 repair_targets 字段
  - 规则触发的 SemanticIssue 被传递给 repair/legacy/repair_generator.py 作为修复依据——PDF 中修复由
   M7(LLM-δ) 根据 DiagReport 生成，不由 Issue 列表触发

  受影响文件：analyzers/legacy/semantic_analyzer.py；analyzers/legacy/report_generator.py（CRERepo
  rt 结构与 DiagReport 不符）
  改动大小：中——若不引入 LLM，需设计替代的 failure_hypothesis 文本生成机制

  ---
#### 偏差 10：M7 修复生成机制严重简化【严重】

  PDF 要求（Part I §6；Part II §8）：
  - M7 生成 K'=2K（默认 K=3，即 6 个）候选修复提案，每个为 RepairProposal
  - 每个提案包含完整的 SpecS'（新 spec），operator_class（来自 V_R
  词汇表），declared_side_effects，semantic_justification（≤200
  tokens），predicted_delta_psi
  - 使用 M7.compute_spec_edit_distance 计算 d_spec(S, S')，超过 η_edit=0.20 的提案被
   M7.filter_by_minimality 过滤
  - M7.rank_proposals：两阶段排名（Stage 1：N_rank=50 轮 rollout 估算
  ΔΨ_rough；Stage 2：LLM predicted_delta_psi 作 tiebreaker）

  当前实现（repair/legacy/repair_generator.py）：
  - 每个 issue 一对一生成一个 RepairPatch（issue 数 = patch 数），没有"候选集 → 过滤
   → 排名"流程
  - RepairPatch 结构远比 RepairProposal 简单，缺少
  operator_class、declared_side_effects、semantic_justification、predicted_delta_psi
  - d_spec 和 η_edit 完全未实现（DECISIONS.md 的 D-S4 schema 也没有此字段）
  - 没有 rollout 排名（更本没有与 RL 训练环境交互的能力）

  受影响文件：repair/legacy/repair_generator.py（整体需重构）
  改动大小：大

  ---
#### 偏差 11：M8 验收协议缺少 C1–C4 完整检查【中等】

  PDF 要求（Part I §7；Part II §9 M8.*）：四个验收标准：
  - C1（诊断改善）：Ψ_CRE(S') > Ψ_CRE(S)
  - C2（安全不退化）：max_j P_π*(S')[(s,a)∈K_j] ≤ max_j P_π*(S)[(s,a)∈K_j]
  - C3（效用不退化）：U_nom(S') ≥ U_nom(S) − ε_perf（默认 0.05）
  - C4（最小编辑）：d_spec(S, S') ≤ η_edit（默认 0.20）

  另需 LLM-ε 语义一致性验证（s_sem ≥ 0.80，intent_preserved=true）。最多 N_max=5
  轮循环，超限 → HARD_REJECT。

  当前实现（repair/legacy/validator.py）：
  - 只检查静态分析 issue 数量变化（issue_ids before/after），无任何 Ψ_CRE 比较
  - C2（policy safety rollout）完全缺失
  - C3（utility non-regression）完全缺失
  - C4 依赖 d_spec，而 d_spec 未实现（偏差 10）
  - 无 LLM-ε 语义验证
  - 无循环控制（N_max=5 轮）

  受影响文件：repair/legacy/validator.py（validate_repair）
  改动大小：大

  ---
#### 偏差 12：DiagReport 核心数据结构缺失，各模块用自定义结构替代【严重】

  PDF 要求（Part II §1.2）：所有模块间数据交换用统一的 DiagReport 数据类，包含：
  spec_id, phi_cr2, phi_ec_bar, phi_er3（canonical），phi_cr1, phi_ec2, phi_ec3,
  phi_er1, phi_er2（supplementary），kappa_cr, gamma_ec,
  delta_er（enhanced），psi_cre, ci_95, flags, discrepancy, failure_hypothesis,
  repair_targets（M4 填写），以及 phi_ec_per_j（per-constraint 覆盖率列表）。

  当前实现：不存在 DiagReport 类。各模块分别使用：
  - StaticReport（analyzers/legacy/static_analyzer.py）
  - DynamicReport（analyzers/legacy/dynamic_analyzer.py）
  - SemanticReport（analyzers/legacy/semantic_analyzer.py）
  - CREReport（analyzers/legacy/report_generator.py）

  这四个类不构成 PDF 规定的数据流。CREReport 对应 PDF 的
  DiagReport，但字段完全不同。

  受影响文件：所有 analyzers/ 文件；repair/ 文件
  改动大小：大——连锁影响所有模块接口

  ---
#### 偏差 13：Pipeline Orchestrator（PO）完全缺失【中等】

  PDF 要求（Part II §10 PO.run_cre_pipeline）：Pipeline Orchestrator 负责：
  - 按 M1→M2→M3→[DP]→M5→M4→[loop: M7→M8] 的顺序调度
  - 验证 w_cr + w_ec + w_er = 1.0（CONFIG_WEIGHT_SUM_ERROR）
  - 管理 enhanced_estimators_enabled 开关（控制 M3/DP 是否运行）
  - 维护 AuditTrail（每个函数调用追加带类型的记录）
  - 执行修复循环（最多 N_max 轮）并输出 AcceptanceVerdict

  当前实现：scripts/run_benchmark.py 中有手写的顺序调用，但没有正式的 Orchestrator
  模块。train.py 集成代码也是简单的线性调用，无循环控制、无 AuditTrail、无权重验证。

  受影响文件：缺少 pipeline/orchestrator.py（或 po.py）；scripts/run_benchmark.py
  改动大小：中

  ---
#### 偏差 14：SpecS 不可变性原则未执行【轻微】

  PDF 要求（Part II §1.2）：SpecS 必须是 @dataclass(frozen=True)，repair
  时创建新对象 S'，原始 S 从不 in-place 修改。spec.version 每次修复后递增。违反触发
  FrozenInstanceError。

  当前实现：4 份 YAML spec 文件是普通文件，repair/legacy/validator.py 中用 _write_yaml_temp
  创建临时文件时会 in-place 修改加载到内存的 Python dict（_apply_patch 直接改
  target_spec dict）。虽然原始文件未被写入，但内存对象可变，不符合 frozen 原则。

  受影响文件：repair/legacy/validator.py（_apply_patch，_apply_set）
  改动大小：小

  ---
  连锁偏差汇总
```
  D-LLM-α（跳过 LLM-α）
      ├─→ 偏差 1: φ²_CR 无轨迹数据，改用 issue 计数近似
      ├─→ 偏差 2: φ̄¹_EC 无轨迹数据，改用 issue 计数近似
      ├─→ 偏差 5: M2 整模块缺失（依赖轨迹输入）
      ├─→ 偏差 6: M3 整模块缺失（依赖可微策略/critic）
      ├─→ 偏差 7: Stage III DP 缺失（依赖 M2+M3）
      └─→ 偏差 12: DiagReport 结构被碎片化替代

  D-LLM-α（跳过 LLM-β/δ/ε）
      ├─→ 偏差 9: M4 语义分析改为规则驱动（结构不符）
      ├─→ 偏差 10: M7 修复改为 1:1 规则模板（无候选集/排名/minimality）
      └─→ 偏差 11: M8 验收改为 issue 数量比较（缺 C2/C3/C4/LLM-ε）

  phi_er = None（偏差 3）
      └─→ 偏差 4: Ψ_CRE 只有 2 维（benchmark injected_er 无法 alarm）
```
  ---
  优先级建议（按实现可行性排序）

  ┌────────┬──────────────────────────────┬──────────────────────────────┐
  │ 优先级 │             偏差             │             原因             │
  ├────────┼──────────────────────────────┼──────────────────────────────┤
  │ 🔴 P0  │ 4（Ψ_CRE 权重修正）          │ 改 3 行，立即可做            │
  ├────────┼──────────────────────────────┼──────────────────────────────┤
  │ 🔴 P0  │ 3（φ³_ER 用 done_type==1）   │ 有现成日志字段，可做         │
  ├────────┼──────────────────────────────┼──────────────────────────────┤
  │ 🔴 P0  │ 12（DiagReport 结构）        │ 基础数据流，所有后续依赖它   │
  ├────────┼──────────────────────────────┼──────────────────────────────┤
  │ 🟡 P1  │ 1+2（φ²_CR、φ̄¹_EC 轨迹计算） │ 依赖有轨迹数据可访问         │
  ├────────┼──────────────────────────────┼──────────────────────────────┤
  │ 🟡 P1  │ 5（M2 模块）                 │ 依赖轨迹接口                 │
  ├────────┼──────────────────────────────┼──────────────────────────────┤
  │ 🟠 P2  │ 10+11（M7/M8 修复循环）      │ 依赖 Ψ_CRE 正确后才有意义    │
  ├────────┼──────────────────────────────┼──────────────────────────────┤
  │ 🟠 P2  │ 13（Pipeline Orchestrator）  │ 结构性重构                   │
  ├────────┼──────────────────────────────┼──────────────────────────────┤
  │ ⚪ P3  │ 6+7（M3+DP）                 │ 依赖可微策略，Isaac Sim 环境 │
  ├────────┼──────────────────────────────┼──────────────────────────────┤
  │ ⚪ P3  │ 8（Bootstrap CI）            │ 依赖 M2 完成                 │
  └────────┴──────────────────────────────┴──────────────────────────────┘
