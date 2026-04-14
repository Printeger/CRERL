# CRE Diagnostic & Repair Suite — 使用说明

**版本**：v1.0.0 | **环境**：NavRL (Python 3.10) | **更新**：2026-04-12

CRE（Constraint–Reward–Environment）是一个**预训练诊断框架**，在 RL 训练启动前（或训练结束后）检测 spec 层面的三类结构性不一致，并自动生成修复建议：

| 不一致类型 | 含义 | 典型症状 |
|-----------|------|---------|
| **C-R** Constraint–Reward | Reward 激励策略违反约束 | reward hacking、boundary-seeking |
| **E-C** Environment–Constraint | 训练环境未充分覆盖约束关键区域 | 训练中很少触发约束，部署时违规 |
| **E-R** Environment–Reward | 跨部署环境的 reward 排名与真实 utility 排名脱钩 | 分布偏移后性能骤降 |

---

## 目录

1. [环境准备](#1-环境准备)
2. [项目结构](#2-项目结构)
3. [配置参数说明](#3-配置参数说明)
4. [快速启动：完整流水线](#4-快速启动完整流水线)
5. [逐模块使用与验证](#5-逐模块使用与验证)
   - [Phase 1 — Spec 校验器](#phase-1--spec-校验器)
   - [Phase 2 — 静态分析](#phase-2--静态分析)
   - [Phase 3 — 动态分析](#phase-3--动态分析)
   - [Phase 4 — 语义分析与 Ψ_CRE 评分](#phase-4--语义分析与-ψ_cre-评分)
   - [Phase 5 — 汇总报告](#phase-5--汇总报告)
   - [Phase 6 — 修复建议](#phase-6--修复建议)
   - [Phase 7 — 修复验证](#phase-7--修复验证)
   - [Benchmark Suite](#benchmark-suite)
6. [与训练集成（Phase 8）](#6-与训练集成phase-8)
7. [读懂输出报告](#7-读懂输出报告)
8. [常见问题与修复指南](#8-常见问题与修复指南)
9. [运行测试套件](#9-运行测试套件)

---

## 1. 环境准备

### 激活 Conda 环境

```bash
source /home/mint/miniconda3/etc/profile.d/conda.sh
conda activate NavRL
```

所有后续命令默认在 `NavRL` 环境下、`isaac-training/training/` 目录内执行：

```bash
cd /home/mint/rl_dev/CRERL/isaac-training/training
```

### 依赖验证

```bash
python -c "import yaml, analyzers, repair; print('OK')"
# 期望输出：OK
```

如果报错 `ModuleNotFoundError: No module named 'yaml'`：

```bash
conda install -c conda-forge pyyaml
```

### LLM 接入配置（strict PDF mode）

strict PDF mode 下，M1 / M4 / M7 / M8 走 CRE_v4 的 canonical LLM path，不再允许以 YAML parser 或规则引擎替代：
- provider：COMP OpenAI API gateway
- authentication header：`api-key`
- base endpoint：`https://comp.azure-api.net/azure/openai/deployments/{deployment}`
- 环境变量：`COMP_OPENAI_API_KEY`、`COMP_OPENAI_BASE_URL`、`COMP_OPENAI_API_VERSION`、`CRE_LLM_ALPHA_DEPLOYMENT`、`CRE_LLM_BETA_DEPLOYMENT`、`CRE_LLM_DELTA_DEPLOYMENT`、`CRE_LLM_EPSILON_DEPLOYMENT`

仓库中**不得保存真实 API key**。接入说明见 `doc/API_KEY.md` 与 `doc/COMP OpenAI Access Guide v3.11.pdf`。

---

## 2. 项目结构

```
isaac-training/training/
├── cfg/
│   ├── spec_cfg/                   # ★ CRE 核心输入：四份 spec 文件
│   │   ├── reward_spec_v1.yaml     # Reward 函数定义（加权 DAG）
│   │   ├── constraint_spec_v1.yaml # 约束集合（谓词 + 严重等级）
│   │   ├── policy_spec_v1.yaml     # 策略规格（动作/观测/频率）
│   │   └── env_spec_v1.yaml        # 环境规格（E_tr / E_dep）
│   ├── benchmark_cfg/              # Benchmark 注入测试用 spec
│   │   ├── clean_nominal/          # 无缺陷基准
│   │   ├── injected_cr/            # 注入 C-R 冲突
│   │   ├── injected_ec/            # 注入 E-C 不匹配
│   │   └── injected_er/            # 注入 E-R 不匹配
│   ├── llm/comp_openai.yaml        # strict PDF mode：LLM provider 配置
│   ├── cre.yaml                    # strict PDF mode：CRE 主入口配置
│   └── train.yaml                  # 训练配置（含 spec_cfg 路径组）
│
├── analyzers/                      # ★ CRE 分析包
│   ├── diag_report.py              # Phase 0：canonical data schemas
│   ├── cfg.py / errors.py          # Phase 0：global config + CREError registry
│   ├── llm_gateway.py              # strict PDF mode：shared COMP OpenAI gateway
│   ├── m1.py                       # Phase 1：M1（canonical LLM-α；含 YAML compatibility adapter）
│   ├── m2.py / m3.py / m4.py / m5.py
│   └── legacy/                     # 历史实现（只读参考，不是 canonical）
│
├── repair/                         # ★ 修复包
│   ├── m7.py / m8.py               # canonical repair + acceptance modules
│   └── legacy/                     # 历史实现（只读参考，不是 canonical）
│
├── pipeline/
│   └── orchestrator.py             # canonical PO.run_cre_pipeline
│
├── scripts/
│   └── run_benchmark.py            # Benchmark 运行脚本
│
├── logs/                           # 训练日志目录（Phase 3 输入）
│   └── <run_id>/
│       ├── manifest.json
│       ├── episodes.jsonl
│       └── episodes/episode_XXXX.json
│
├── unit_test/test_env/             # 测试套件（9 个文件，60 个测试）
└── pytest.ini                      # pytest 配置
```

---

## 3. 配置参数说明

### 3.1 四份 Spec 文件（最重要的配置）

#### `cfg/spec_cfg/reward_spec_v1.yaml` — Reward 规格

```yaml
spec_type: "reward"
spec_version: "1.0"

reward_terms:
  - term_id: "reward_progress"       # 唯一 ID，必须与日志 reward_components 键名一致
    term_expr: "goal_distance_t_minus_1 - goal_distance_t"  # 人类可读表达式
    weight: 1.00                     # 正数=激励，负数=惩罚
    unit: "m"                        # 物理单位（仅用于文档）
    clip_bounds:
      min: -1.5                      # null 表示不裁剪
      max: 1.5
    shaping_flag: true               # true = potential-based shaping term

dag_edges:                           # reward_progress 是其他 term 的 shaping 父节点
  - from: "reward_progress"
    to: "reward_safety_static"
```

**关键参数**：
- `weight`：控制该 term 对总 reward 的贡献方向和强度
- `clip_bounds.min >= 0`：与 hard constraint 共享变量时会触发 `domain_boundary` 警告
- `dag_edges`：描述 potential-based shaping 依赖关系，空列表合法

#### `cfg/spec_cfg/constraint_spec_v1.yaml` — 约束规格

```yaml
constraints:
  - constraint_id: "collision_avoidance"
    indicator_predicate: "min_obstacle_distance_m <= 0.0 OR done_type == 2"
    severity: "hard"                 # hard / soft / info
    temporal_scope: "instantaneous"  # instantaneous / episodic / cumulative
    coverage_threshold_delta: 0.90   # 训练环境需覆盖此约束的最低比例
    tolerance: null                  # hard/info 约束填 null
    penalty_weight: null             # hard/info 约束填 null

  - constraint_id: "safety_margin"
    severity: "soft"
    tolerance: 0.50                  # soft 约束必须非 null：违规容忍阈值
    penalty_weight: 0.60             # soft 约束必须非 null：惩罚权重
```

**关键参数**：
- `severity: "hard"`：策略绝对不能违反；`soft`：有容忍阈值
- `coverage_threshold_delta`：静态分析的 E-C 检测基准，值越高要求越严
- `soft` 约束的 `tolerance` / `penalty_weight` **必须非 null**，否则校验失败

#### `cfg/spec_cfg/env_spec_v1.yaml` — 环境规格

```yaml
E_tr:                               # 训练环境
  shift_operators: []               # 空列表=训练时无分布偏移

E_dep:                              # 部署环境列表
  deployment_envs:
    - env_id: "e1_shifted"
      applied_shift_operators:      # 部署时施加的偏移
        - "workspace_scale_shift"
```

**关键参数**：
- `E_tr.shift_operators: []` 且 `E_dep` 中有非空 `applied_shift_operators`，会触发 `deployment_shift_coverage` E-R 警告（训练分布未覆盖部署偏移）

#### `cfg/spec_cfg/policy_spec_v1.yaml` — 策略规格

```yaml
action_space:
  tensor_key: ["agents", "action"]  # TorchRL TensorDict 中的 key
  shape: [3]
  bounds:
    min: [-2.0, -2.0, -2.0]
    max: [2.0, 2.0, 2.0]

execution_frequency_hz: 62.5        # 由 sim.yaml: dt=0.016 推导
```

### 3.2 训练配置中的 spec 路径（`train.yaml`）

```yaml
spec_cfg:
  reward: isaac-training/training/cfg/spec_cfg/reward_spec_v1.yaml
  constraint: isaac-training/training/cfg/spec_cfg/constraint_spec_v1.yaml
  policy: isaac-training/training/cfg/spec_cfg/policy_spec_v1.yaml
  env: isaac-training/training/cfg/spec_cfg/env_spec_v1.yaml
```

路径相对于项目根目录 `CRERL/`。若迁移到新机器，只需修改这四行。

### 3.3 strict PDF mode 核心阈值（来自 `CFG`）

| CFG 字段 | 默认值 | 含义 |
|------|--------|------|
| `tau_alarm_psi` | 0.75 | `Ψ_CRE` 低于此值触发告警 |
| `w_cr` | 0.333 | C-R 维度权重 |
| `w_ec` | 0.333 | E-C 维度权重 |
| `w_er` | 0.334 | E-R 维度权重 |
| `tau_sem` | 0.80 | semantic consistency 阈值 |
| `eta_edit` | 0.20 | minimality 阈值 |
| `eps_perf` | 0.05 | utility 容忍边界 |

这些值都应通过 `analyzers/cfg.py::CFG` 与 Hydra 配置管理；strict PDF mode 下不再通过旧两维实现的顶部常量手调。

---

## 4. 快速启动：完整流水线

strict PDF mode 下，canonical 顶层入口不再是 `generate_report -> generate_repair -> validate_repair` 的旧附加链路，而是 `pipeline/orchestrator.py::run_cre_pipeline()`。

推荐入口：

```python
# scripts/run_full_cre.py（strict PDF mode 示例）
import sys
sys.path.insert(0, ".")   # 在 isaac-training/training/ 下运行

from analyzers.diag_report import NLInput
from analyzers.cfg import CFG
from analyzers.llm_gateway import CompOpenAIGateway
from pipeline.orchestrator import run_cre_pipeline

nl = NLInput(
    r_desc="reward natural-language description",
    c_desc="constraint natural-language description",
    e_desc="environment natural-language description",
    metadata={"source": "strict_pdf_mode_demo"},
)

diag_report, verdict = run_cre_pipeline(
    nl_input=nl,
    cfg=CFG,
    llm_client=CompOpenAIGateway(),
)

print(diag_report.psi_cre)
print(verdict.accepted if verdict is not None else None)
```

> 历史说明：`analyzers/legacy/report_generator.py`、`repair/legacy/repair_generator.py`、`repair/legacy/validator.py`
> 的 quickstart 只保留为 legacy 参考，不再代表 strict PDF canonical path。

**当前实现状态**：
- `run_cre_pipeline()` 仍待实现
- `parse_yaml_input()` 只保留为 compatibility adapter
- M1/M4/M7/M8 的 contract 已冻结，但 canonical 业务逻辑尚未落地

```
planned strict-PDF outputs
├── diag_report.json
├── repair_proposals.json
├── acceptance_verdict.json
└── audit_trail.json
```

> strict PDF mode 下，当前主输出围绕 `DiagReport`、`RepairProposal`、`AcceptanceVerdict` 与 `PO.run_cre_pipeline()` 组织；旧 `report.json` / `repair_result.json` / `validation_result.json` 仅保留为 legacy 参考。

---

## 5. 逐模块使用与验证

### Phase 1 — Spec 校验器

**文件**：`analyzers/spec_validator.py`
**作用**：验证四份 YAML spec 的格式合法性与跨文件一致性

```python
from analyzers.spec_validator import validate_spec_file, validate_spec_set

# 单文件校验
result = validate_spec_file("cfg/spec_cfg/reward_spec_v1.yaml")
print(result.valid, result.errors, result.warnings)

# 四文件联合校验（推荐）
result = validate_spec_set(
    "cfg/spec_cfg/reward_spec_v1.yaml",
    "cfg/spec_cfg/constraint_spec_v1.yaml",
    "cfg/spec_cfg/policy_spec_v1.yaml",
    "cfg/spec_cfg/env_spec_v1.yaml",
)
print(result.valid)   # True = 格式合法
print(result.errors)  # [] = 无错误
```

**检验功能是否正常**：

```bash
python -m pytest unit_test/test_env/test_spec_validator.py -v
# 期望：11 passed
```

**常见错误与修复**：

| 错误信息 | 原因 | 修复 |
|---------|------|------|
| `missing required field 'spec_type'` | YAML 顶层缺少 spec_type | 加上 `spec_type: "reward"` |
| `tolerance: soft constraint requires a non-null value` | soft 约束未填 tolerance | 在对应约束下填写 `tolerance: 0.5` |
| `severity: expected one of ['hard', 'info', 'soft']` | severity 拼写错误 | 只能用这三个值 |
| `spec_version mismatch` | 四份文件版本号不一致 | 统一改为 `spec_version: "1.0"` |
| `reward.dag_edges contains a cycle` | DAG 中有循环依赖 | 检查 dag_edges，移除形成环的那条边 |

---

### Historical Phase 2 — 静态分析（legacy）

**文件**：`analyzers/legacy/static_analyzer.py`
**作用**：旧版 legacy 结构性矛盾检测，无需运行时数据；不属于 strict PDF canonical path

```python
from analyzers.legacy.static_analyzer import run_static_analysis

report = run_static_analysis(
    "cfg/spec_cfg/reward_spec_v1.yaml",
    "cfg/spec_cfg/constraint_spec_v1.yaml",
    "cfg/spec_cfg/policy_spec_v1.yaml",
    "cfg/spec_cfg/env_spec_v1.yaml",
    output_dir="/tmp/cre_static",   # 省略则不写盘
)

# 查看检测结果
for issue in report.issues:
    print(f"[{issue.issue_type}][{issue.severity}] {issue.rule_id}: {issue.description}")
    print(f"  涉及字段: {issue.traceable_fields}")
    print(f"  证据: {issue.evidence}")
```

**五条检测规则**：

| rule_id | 维度 | 级别 | 含义 |
|---------|------|------|------|
| `type_compatibility` | C-R | warning | reward term 与 hard constraint 共享状态变量，可能产生 boundary-seeking 激励 |
| `domain_boundary` | C-R | warning | reward term 非负支撑与 hard constraint 共享变量，支撑可能落在约束边界方向 |
| `coverage_prebound` | E-C | warning | hard constraint 无法通过关键词匹配到训练环境的 scene family 或 shift operator |
| `deployment_shift_coverage` | E-R | warning | 部署环境有 shift operator 但训练环境未显式声明对应覆盖 |
| `soft_constraint_penalty_alignment` | C-R | info | soft constraint 惩罚与正权 reward term 共享变量，可能相互牵制 |

**检验功能是否正常**：

```bash
python -m pytest unit_test/test_env/test_static_analyzer.py -v
# 期望：5 passed（含阳性案例：注入冲突 spec → 必须报告对应 issue）
```

**结果解读**：
- 当前 v1 spec 正常产出 **10 条 issue（全部 warning/info，无 error）**
- `coverage_prebound` 对 `collision_avoidance` 报 warning 是**已知假阳性**：scene family 名称（nominal/shifted）不含 "collision" 关键词，但训练环境确实有障碍物。可忽略或在 `env_spec_v1.yaml` 的 `shift_operators[*].description` 中加入 "obstacle" 相关描述改善匹配

---

### Historical Phase 3 — 动态分析（legacy）

**文件**：`analyzers/legacy/dynamic_analyzer.py`
**作用**：旧版 legacy 运行日志分析；不属于 strict PDF canonical path

```python
from analyzers.legacy.static_analyzer  import run_static_analysis
from analyzers.legacy.dynamic_analyzer import run_dynamic_analysis

static = run_static_analysis(...)  # 需要先有 Phase 2 结果

report = run_dynamic_analysis(
    static_report        = static,
    log_dir              = "logs/train_eval_rollout_20260411_215734",
    reward_spec_path     = "cfg/spec_cfg/reward_spec_v1.yaml",
    constraint_spec_path = "cfg/spec_cfg/constraint_spec_v1.yaml",
    output_dir           = "/tmp/cre_dynamic",
)

print(f"分析了 {report.episode_count} 个 episode")
print(f"发现 {len(report.issues)} 条动态 issue")
```

**日志目录格式要求**：

```
logs/<run_id>/
├── episodes/
│   ├── episode_0000.json   # 优先读取（含完整 step 数据）
│   └── episode_0001.json
└── episodes.jsonl           # fallback（仅 episode 摘要）
```

**五条动态规则（D1–D5）**：

| rule_id | 维度 | 触发条件 |
|---------|------|---------|
| `hard_constraint_violation_rate` | C-R | step 级 `collision_flag=True` 或 `out_of_bounds_flag=True` |
| `soft_constraint_exceedance_rate` | C-R | `min_obstacle_distance < 0.50` / `velocity_norm > 2.0` / `yaw_rate > 1.20` |
| `critical_region_proximity` | E-C | `min_obstacle_distance < 1.0m` 的 step 比例低于 `coverage_threshold_delta` |
| `reward_violation_correlation` | C-R | 高 reward episode 同时发生约束违规 |
| `missing_field_coverage` | info | 日志缺失 spec 所需字段（已知：`min_dynamic_obstacle_distance_m` 等） |

**检验功能是否正常**：

```bash
python -m pytest unit_test/test_env/test_dynamic_analyzer.py -v
# 期望：6 passed（含真实日志 smoke test）
```

**日志字段缺失时的处理**：

当前日志缺少以下字段，相关规则会降级或跳过：

| 缺失字段 | 影响 | 处理方式 |
|---------|------|---------|
| `min_dynamic_obstacle_distance_m` | 无法区分静态/动态障碍物距离 | 用 `min_obstacle_distance` 代替，报告 missing_field info |
| `body_roll_rad` / `body_pitch_rad` | `attitude_turn_rate` 只能检测 yaw 分量 | 报告 `partial_coverage=True` |
| `workspace_size_x_m/y_m` | 无法重建几何边界 | 改用 `out_of_bounds_flag` |

---

### Phase 4 — M4 Failure Hypothesis（canonical）

**文件**：`analyzers/m4.py`
**作用**：对已完成的 `DiagReport` 执行单次 LLM-β 调用，返回 `(failure_hypothesis, repair_targets)`，再由 caller 在 diff guard 通过后写回 `DiagReport.failure_hypothesis / repair_targets`

```python
from analyzers.m4 import generate_failure_hypothesis

failure_hypothesis, repair_targets = generate_failure_hypothesis(
    diag_report=diag_report,
    spec=spec,
    cfg=CFG,
    llm_client=CompOpenAIGateway(),
)
```

当前状态：canonical contract 已冻结，业务实现待补。

---

### Phase 5 — M7 修复候选生成（canonical）

**文件**：`repair/m7.py`
**作用**：LLM-δ 生成 `list[RepairProposal]`，再执行 minimality 过滤与两阶段排名

```python
from repair.m7 import generate_repair_proposals, filter_by_minimality, rank_proposals

proposals = generate_repair_proposals(
    spec=spec,
    diag_report=diag_report,
    cfg=CFG,
    llm_client=CompOpenAIGateway(),
)
proposals = filter_by_minimality(proposals, spec=spec, cfg=CFG)
proposals = rank_proposals(proposals, spec=spec, diag_report=diag_report, cfg=CFG)
```

strict PDF mode 下，Phase 5 的 canonical 输出是 `RepairProposal`，不是 legacy `CREReport`、`RepairPatch` 或 `RepairResult`。

### Phase 6 — M8 验收与语义一致性（canonical）

**文件**：`repair/m8.py`
**作用**：
- `evaluate_acceptance_criteria()`：检查 C1–C4
- `verify_semantic_consistency()`：LLM-ε 计算 `(s_sem, intent_preserved)`
- `run_acceptance_loop()`：合并 acceptance criteria 与 semantic gate，输出 `AcceptanceVerdict`

strict PDF mode 下，semantic consistency 是额外 acceptance gate，不等价于旧 `validator.py` 的 patch replay/issue diff 流程。

```python
from repair.m8 import run_acceptance_loop

accepted_spec, verdict, exit_code = run_acceptance_loop(
    nl_orig=nl,
    spec=spec,
    proposals=proposals,
    diag_report=diag_report,
    cfg=CFG,
    llm_client=CompOpenAIGateway(),
)
```

### Phase 7 — PO.run_cre_pipeline（canonical）

**文件**：`pipeline/orchestrator.py`
**作用**：按 PDF Part II §10.1.1 的顺序串联 M1 → M2 → M3 → [DP] → M5 → M4 → [loop: M7 → M8]

```python
from pipeline.orchestrator import run_cre_pipeline

diag_report, verdict = run_cre_pipeline(
    nl_input=nl,
    cfg=CFG,
    llm_client=CompOpenAIGateway(),
)
```

### Historical Appendix — 旧 report / patch / validator 流程

`analyzers/legacy/semantic_analyzer.py`、`analyzers/legacy/report_generator.py`、`repair/legacy/repair_generator.py`、`repair/legacy/validator.py` 及其对应测试只保留为 legacy 参考，用于理解 pre-refactor 代码如何偏离 PDF；它们不再代表当前 canonical phases。

---

### Benchmark Suite

验证检测器灵敏度：注入已知缺陷的 spec，确认是否被正确检出。

```bash
# 命令行运行
python scripts/run_benchmark.py \
  --benchmark_dir cfg/benchmark_cfg \
  --output_dir /tmp/cre_benchmark
```

**期望输出**：

```json
{
  "clean_nominal":  {"alarm": false, "psi_cre": 0.9xxx, "total_issues": N},
  "injected_cr":    {"alarm": true,  "psi_cre": <0.75,  "total_issues": N},
  "injected_ec":    {"alarm": true,  "psi_cre": <0.75,  "total_issues": N},
  "injected_er":    {"alarm": false, "psi_cre": xxx,    "total_issues": >0}
}
```

> Historical note（legacy benchmark snapshot）：
> 当前仓库里留存的 `injected_er -> alarm=false` 说明来自旧 `semantic_analyzer.py` 路线，其中 `phi_er=None` 导致 E-R 维度未参与 `Ψ_CRE`。这不是 strict PDF canonical 目标，待 canonical M2/M5 落地后应被移除。

**检验功能是否正常**：

```bash
python -m pytest unit_test/test_env/test_benchmark.py -v
# 期望：10 passed（含 clean_nominal/injected_cr/ec/er 四个 case）
```

---

## 6. 与训练集成（Phase 8）

CRE 分析以**追加方式**接入 `scripts/train.py`，训练结束后自动运行，失败不影响训练结果。

### 配置步骤

**Step 1**：确认 `train.yaml` 中已有 spec 路径配置（已预置）：

```yaml
spec_cfg:
  reward: isaac-training/training/cfg/spec_cfg/reward_spec_v1.yaml
  constraint: isaac-training/training/cfg/spec_cfg/constraint_spec_v1.yaml
  policy: isaac-training/training/cfg/spec_cfg/policy_spec_v1.yaml
  env: isaac-training/training/cfg/spec_cfg/env_spec_v1.yaml
```

**Step 2**：strict PDF mode 下应以 `pipeline/orchestrator.py::run_cre_pipeline()` 为主入口；旧 `train.py` 收尾区的 `generate_report -> generate_repair -> validate_repair` hook 只保留为 historical integration artifact。

**WandB 中观察的 canonical CRE 指标（orchestrator 落地后）**：

| Key | 含义 | 健康值 |
|-----|------|-------|
| `cre_v2/psi_cre` | 综合一致性评分 | ≥ 0.75 |
| `cre_v2/alarm` | 是否触发告警（0/1） | 0 |
| `cre_v2/repair_targets_count` | M4 输出的 repair targets 数量 | 参考 |
| `cre_v2/accepted` | 本轮提案是否通过 acceptance protocol | 1 |

**Step 3**：启动训练（需要 Isaac Sim 环境）：

```bash
conda activate NavRL
python scripts/train.py --config-name train
```

训练结束后，CRE 报告写入训练日志目录，WandB 同步更新。

---

## 7. 读懂输出报告

### `static_report.json` 结构

```json
{
  "spec_versions": {"reward": "1.0", "constraint": "1.0", ...},
  "issues": [
    {
      "issue_id": "CR-001",
      "issue_type": "C-R",
      "severity": "warning",
      "rule_id": "type_compatibility",
      "description": "Reward term 'reward_progress' shares state-variable tokens...",
      "traceable_fields": ["reward.reward_terms[0].term_expr", "constraint.constraints[0].indicator_predicate"],
      "evidence": {
        "reward_term_id": "reward_progress",
        "constraint_id": "collision_avoidance",
        "shared_tokens": ["distance"]
      }
    }
  ],
  "summary": {
    "total": 10,
    "by_type": {"C-R": 7, "E-C": 1, "E-R": 2},
    "by_severity": {"error": 0, "warning": 8, "info": 2},
    "validation_failed": false
  }
}
```

### `RepairProposal`（canonical 计划输出）

```json
{
  "proposal_id": "RP-001",
  "spec_prime": "<SpecS'>",
  "operator_class": "reward_reweight",
  "declared_side_effects": ["reduced shaping incentive"],
  "semantic_justification": "align reward with safety boundary",
  "predicted_delta_psi": 0.18,
  "rough_delta_psi": 0.12
}
```

### `AcceptanceVerdict`（canonical 计划输出）

```json
{
  "accepted": true,
  "c1_pass": true,
  "c2_pass": true,
  "c3_pass": true,
  "c4_pass": true,
  "s_sem": 0.92,
  "intent_preserved": true,
  "rejection_feedback": []
}
```

### Historical Appendix — `repair_result.json`（legacy only）

旧 `repair_result.json` / patch 手工应用流程只保留为 historical artifact，不代表 strict PDF canonical path。

---

## 8. 常见问题与修复指南

### 问题 1：`validate_spec_set` 返回 `valid=False`

```
错误：spec.constraints[0].tolerance: soft constraint requires a non-null value
修复：在对应约束下补充 tolerance: 0.5（根据物理含义选取合理值）
```

### 问题 2：静态分析产出大量 C-R warning

**原因**：token heuristic 匹配粗糙，`distance` 这类通用词出现在多个 reward term 和 constraint 中。

**判断是否为假阳性**：
- 查看 `evidence.shared_tokens`，若只有 `distance` / `min` 等通用词 → 大概率假阳性
- 若包含 `collision` / `obstacle` / `boundary` 等语义明确的词 → 值得关注

**处理方式**：
- 假阳性：在 `reward_spec_v1.yaml` 中改写 `term_expr` 使其更具体（如将 `goal_distance_t` 改为 `target_goal_dist_t`），减少无意义 token 重叠
- 真阳性：按 Phase 6 修复建议调整 reward weight

### 问题 3：动态分析 `episode_count=0`

**原因**：日志目录路径错误，或目录下没有 `episodes/` 子目录也没有 `episodes.jsonl`

**排查**：

```bash
ls logs/<run_id>/                    # 确认目录存在
ls logs/<run_id>/episodes/ | head -5 # 确认 episode JSON 文件存在
```

### 问题 4：`psi_cre` 持续偏低（< 0.50）

**最常见原因**：`E_tr.shift_operators == []` 但部署环境有多个 shift，导致 C-R 和 E-C 评分双双拉低。

**修复路径**：
1. 在 `env_spec_v1.yaml` 的 `E_tr.shift_operators` 中添加与部署一致的偏移声明
2. 或降低 `coverage_threshold_delta`（从 0.90 调低），但需记录决策依据

### 问题 5：Benchmark `injected_er` 未触发 alarm

这是**已知设计限制**（`D-BM1`），不是 bug。
`phi_er` 计算需要跨多个部署环境的真实运行数据（Pearson 相关），单次训练无法满足。
当前 `injected_er` 仍能检出 `total_issues > 0`（`SEM-ER-DETECTION` 规则），只是不触发 alarm。

### 问题 6：pytest 只运行部分测试

确保在 `isaac-training/training/` 目录下运行，且 pytest.ini 存在：

```bash
cd /home/mint/rl_dev/CRERL/isaac-training/training
python -m pytest -v   # 应收集 60 个测试
```

### 问题 7：修改 spec 后如何重新跑分析

**规则**：spec 文件不得原地修改，每次变更创建更高版本号的文件。

```bash
cp cfg/spec_cfg/reward_spec_v1.yaml cfg/spec_cfg/reward_spec_v2.yaml
# 编辑 reward_spec_v2.yaml
# 在 DECISIONS.md 中记录变更原因
# 重新运行分析，传入 v2 路径
```

---

## 9. 运行测试套件

### 全套测试（推荐日常使用）

```bash
cd /home/mint/rl_dev/CRERL/isaac-training/training
source /home/mint/miniconda3/etc/profile.d/conda.sh && conda activate NavRL
python -m pytest -v
```

**期望输出**：60 passed

### 分模块测试

```bash
# Phase 1
python -m pytest unit_test/test_env/test_spec_validator.py -v      # 11 tests

# Phase 2
python -m pytest unit_test/test_env/test_static_analyzer.py -v     # 5 tests

# Phase 3（含真实日志 smoke test）
python -m pytest unit_test/test_env/test_dynamic_analyzer.py -v    # 6 tests

# Historical appendix tests only
python -m pytest unit_test/test_env/test_semantic_analyzer.py -v  # historical only, imports analyzers.legacy.*
python -m pytest unit_test/test_env/test_report_generator.py -v   # historical only, imports analyzers.legacy.*
python -m pytest unit_test/test_env/test_repair_generator.py -v   # historical only, imports repair.legacy.*
python -m pytest unit_test/test_env/test_validator.py -v          # historical only, imports repair.legacy.*

# 全流程集成（含真实日志）
python -m pytest unit_test/test_env/test_integration_pipeline.py -v  # 3 tests

# Benchmark
python -m pytest unit_test/test_env/test_benchmark.py -v            # 10 tests
```

### 快速健康检查（无需完整测试）

```bash
python -c "
from analyzers.spec_validator import validate_spec_set
r = validate_spec_set(
    'cfg/spec_cfg/reward_spec_v1.yaml',
    'cfg/spec_cfg/constraint_spec_v1.yaml',
    'cfg/spec_cfg/policy_spec_v1.yaml',
    'cfg/spec_cfg/env_spec_v1.yaml',
)
print('OK' if r.valid else 'FAIL: ' + str(r.errors))
"
```

---

## 附录：Ψ_CRE 计算公式

$$\Psi_{CRE} = 1 - \left[ w_{CR} \cdot f(\phi_{CR}) + w_{EC} \cdot f(1 - \phi_{EC}) + w_{ER} \cdot f(\phi_{ER}) \right]$$

其中 $f(x) = \frac{\sigma(8(x-0.5)) - \sigma(-4)}{\sigma(4) - \sigma(-4)}$，$\sigma$ 为 sigmoid 函数。

strict PDF mode 的 canonical 目标是完整三维 $\Psi_{CRE}$；不应把 E-R 维度长期退化为二维评分。
