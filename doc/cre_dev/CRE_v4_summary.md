# CRE_v4.pdf 核心结论摘要

> 生成日期：2026-04-12 | 来源：`doc/CRE_v4.pdf` v1.0（April 10, 2026）  
> 覆盖范围：Part I §1–8 全文（NeurIPS-Standard Method Section，共 20 页）  
> **本文件是阅读 PDF 的替代品；新 Agent 会话若时间紧可先读本文件，但仍以 PDF 为权威来源。**

---

## 一、框架定位

CRE（Constraint–Reward–Environment）是一个**预训练诊断框架**，在 RL 训练启动前（或训练期间）检测 spec 层面的三类结构性不一致，而非训练后审计策略行为。

核心论点：reward hacking、安全失效、分布偏移失败的根本原因都可追溯到 spec 层面（R / C / E 三者之间的矛盾），而任何事后检查 *已学策略行为* 的诊断方法都无法在源头发现这些问题。CRE 在 spec 层面操作，检测并修复这些矛盾。

---

## 二、核心数据结构：Specification Triple

$$\mathcal{S} = (\mathcal{E}_\text{tr},\ \mathcal{E}_\text{dep},\ R,\ \mathcal{C},\ \Pi)$$

| 字段 | 含义 | 表示方式 |
|------|------|---------|
| `E_tr` | 训练环境分布（MDP 集合） | 场景描述符族 + shift 算子 |
| `E_dep` | 部署环境集合 `{e_0,...,e_n}`（`e_0` = nominal） | 同上 |
| `R` | Reward 函数 `S×A → ℝ` | 加权有向无环图（DAG）`G_R`，节点=reward term，边=shaping 依赖 |
| `C` | 约束集合 `{(K_j, σ_j, h_j)}` | 每条约束 = 违约区域谓词 + 严重等级 + 时间范围 |
| `Π` | Policy 类 | 动作空间 + 观测空间 + 执行频率 |

**约束表示（Def 1.2）**：
- `K_j ⊆ S×A`：违约状态-动作对，编码为一阶谓词 `O_j: S×A → {0,1}`
- `σ_j ∈ {hard, soft, info}`：严重等级
- `h_j ∈ {instantaneous, episodic, cumulative}`：时间范围

**不可变性原则**：`S` 在整个诊断管线中不可修改；只有 Stage V–VI 验证通过后才用 `S'` 替换。

---

## 三、三类不一致分类（Three-Class Taxonomy）

### Class I — C-R 不一致（Constraint–Reward）

**定义（Def 1.3）**：存在策略 π，使得 `J(π) > J(π*) - ε_J`（近最优），同时 `P_π[∃t: (s_t,a_t)∈K_j] > 0`（违反某个 hard 约束）。

两种失效模式：
1. **边界趋近（boundary-seeking）**：策略在约束边界附近操作
2. **梯度对立（gradient opposition）**：`cos(∇_θ J_R, ∇_θ J_C) < -δ_opp`，reward 梯度与约束满足梯度反向

**重要限制（Remark 1.4）**：规范检测器 φ²_CR 是 *充分但不必要* 条件，以下情形**无法可靠检测**：
- 稀疏违约但不持续趋近边界
- soft constraint 累积冲突
- 定义在动作空间（而非状态几何边界）上的约束

---

### Class II — E-C 不一致（Environment–Constraint）

**定义（Def 1.5）**：

$$\text{Cov}(K_j, \mathcal{E}_\text{tr}) := \frac{|\{s \in K_j \mid \exists\tau \sim \pi_\text{ref} \text{ in } \mathcal{E}_\text{tr}: s\in\tau\}|}{|K_j|} < \delta_j$$

训练环境对约束关键区域 `K_j` 覆盖不足，策略无法获得足够的约束满足学习信号。

**连续状态空间实现**：`|K_j|` 解释为 Lebesgue 测度，用 KD 树近邻查找（半径 `r_j = critical_region_radius`）近似，会引入随 `r_j` 增大的估计偏差——高维场景需做敏感性分析。

---

### Class III — E-R 不一致（Environment–Reward）

**定义（Def 1.7）**：

$$\phi^{(3)}_{ER}(\mathcal{S}) := \frac{1 - \rho_{RU}(\pi^*; \mathcal{E}_\text{dep})}{2} > \theta_{ER}$$

其中 `ρ_RU` 是跨部署环境的 reward 排名与 utility 排名之间的 Pearson 相关系数。

`φ³_ER = 0`：reward 与 utility 完全对齐；`φ³_ER = 0.5`：零相关；`φ³_ER = 1`：最大反相关。

---

## 四、六阶段管线总览

```
Stage I   M1   NL 解析 + 歧义检测 → 结构化 S
                LLM-α：抽取 reward DAG、约束谓词、环境族；检测歧义 flag
                内部一致性预检：类型兼容 / 域边界 / Coverage 预界

Stage II  M2   三维主估计器（Behavioral Level，算法无关）
                C-R：φ¹_CR（Reward-Risk 相关）、φ²_CR（边界趋近，canonical）
                E-C：φ^(1,j)_EC（每约束覆盖率，canonical=平均/最小聚合）
                     φ²_EC（约束激活频率）、φ³_EC（约束多样性）
                E-R：φ¹_ER（Deployment Utility Gap）、φ²_ER（Deployment Reward Gap）
                     φ³_ER（reward-utility 去耦，canonical）

          M3   增强估计器（Mechanistic Level，补充诊断深度）
                κ̃_CR：梯度冲突评分（B/M, Ag）
                γ̃_EC：双模拟软覆盖（M, Ag）
                δ̃_ER：梯度漂移评分（M, Cd，需 critic）
                ⚠️ 增强估计器只进差异协议，绝不进 Ψ_CRE 计算

Stage III DP   差异协议（仅在 M2+M3 同时可用时激活）
                触发条件：Δ_d = |φ̂_d - κ̂_d| > η_disc（默认 0.15）
                Case A LATENT_INCONSISTENCY：φ̂_d<τ_low，κ̂_d>τ_high → 扩展不确定区间
                Case B CRITIC_QUALITY_WARN ：φ̂_d>τ_high，κ̂_d<τ_low → 主估计器主导，安排复查

Stage IV  M5   Ψ_CRE 综合评分
                见公式 § 五；Bootstrap CI（BCa，B=1000 轨迹重采样）
          M4   LLM-β 语义分析：生成自然语言失效机制假说 + 修复优先级列表
                ⚠️ LLM-β 不修改任何数值字段（post-processing diff guard 强制）

Stage V   M7   修复生成（LLM-δ）
                操作词汇表分三类：Reward-space / Environment-space / Constraint-adjacent
                最小编辑原则：d_spec(S, S') ≤ η_edit（默认 0.20）
                生成 K'=2K 候选（默认 K=3），粗排后提交 M8

Stage VI  M8   验收与验证
                C1 诊断改善：Ψ_CRE(S') > Ψ_CRE(S)
                C2 安全不退化：max_j P_π*(S')[(s,a)∈K_j] ≤ max_j P_π*(S)[(s,a)∈K_j]
                C3 效用不退化：U_nom(S') ≥ U_nom(S) - ε_perf
                C4 最小编辑：d_spec(S, S') ≤ η_edit
                LLM-ε 语义一致性验证：s_sem ≥ 0.80 且 intent_preserved = true
                最多 N_max=5 轮循环；超限 → HARD_REJECT + 人工升级
```

---

## 五、Ψ_CRE 综合评分

$$\Psi_\text{CRE}(\mathcal{S}) = 1 - \left[w_{CR}\,f\!\left(\varphi^{(2)}_{CR}\right) + w_{EC}\,f\!\left(1-\bar\varphi^{(1)}_{EC}\right) + w_{ER}\,f\!\left(\varphi^{(3)}_{ER}\right)\right]$$

其中 `w_CR + w_EC + w_ER = 1`，`f(·)` 为 sigmoid 单调变换（steepness k=8.0，inflection x_0=0.5）：

$$f(x) = \frac{\sigma(k(x-x_0)) - \sigma(-kx_0)}{\sigma(k(1-x_0)) - \sigma(-kx_0)},\quad \sigma(z) = \frac{1}{1+e^{-z}}$$

| 值 | 含义 |
|----|------|
| `Ψ_CRE = 1` | spec 完全一致 |
| `Ψ_CRE = 0` | 三维全部最大不一致 |
| `Ψ_CRE < τ_alarm`（默认 0.75） | 触发修复循环 |
| `Ψ_CRE < τ_detect`（默认 μ₀ - 1.5σ₀） | 检测到不一致（但未必需要立即行动） |

**双阈值语义**：
- `τ_detect`：统计显著性阈值（基于 null 分布标定）
- `τ_alarm`：行动阈值（基于运营成本 c_fp / c_fn 标定）
- 关系：`τ_alarm ≤ τ_detect`（actionable ⊆ detectable）

---

## 六、规范检测器（Canonical Reporters）对照表

| 维度 | 规范检测器 | 含义 | 增强对应器 |
|------|-----------|------|-----------|
| C-R | φ²_CR 边界趋近评分 | π* 趋近 hard 约束边界的程度（相对随机基准） | κ̃_CR 梯度冲突 |
| E-C | φ̄¹_EC 均值关键态覆盖率 | 训练轨迹覆盖 hard 约束关键区域的比例 | γ̃_EC 双模拟软覆盖 |
| E-R | φ³_ER reward-utility 去耦 | 跨环境 reward 排名与 utility 排名的相关性（反向归一化） | δ̃_ER 梯度漂移 |

**E-C 聚合模式**（关键配置！）：
- `ec_aggregation_mode: "mean"`（默认）：可能因均值掩盖最坏单约束失效
- `ec_aggregation_mode: "min"`：**安全关键场景必须使用**，`safety_level: critical` 自动切换
- 建议：无论哪种模式，都应单独检查每个 φ^(1,j)_EC

---

## 七、三条核心定理

| 定理 | 结论 | 限制 |
|------|------|------|
| **Thm 8.3** 框架内一致性 | 在理想 oracle 条件下，Ψ_CRE < 1 ⟺ 至少一个规范检测器激活 | 是充分非必要：不覆盖所有真实不一致模式 |
| **Thm 8.5** 算法无关性 | Ψ_CRE 与 RL 优化器和 critic 架构无关，仅依赖轨迹统计 | π* 本身依赖优化器，不同优化器得不同 Ψ_CRE |
| **Thm 8.7** 修复收敛 | LLM 以 p_min>0 概率覆盖每个候选时，N≤⌈log δ/log(1-p_min)⌉ 轮内以 1-δ 概率收敛 | 要求编辑球内存在可接受修复 |

---

## 八、必须遵守的架构约束

1. **增强估计器隔离**：κ̃_CR、γ̃_EC、δ̃_ER 只能路由到差异协议（Stage III）；写入 Ψ_CRE 规范槽位触发 `CanonicalViolationError`，管线强制停止。

2. **E-C 聚合必须显式选择**：安全关键场景必须在配置中设置 `ec_aggregation_mode: "min"`；不能依赖默认值。

3. **Utility Oracle 独立性（Assumptions 3.2–3.4）**：
   - U(π;e) 必须在 R 设计之前确定，且与 R 的构造统计独立
   - 任何由 R 单调变换、共享标注来源导出的 U 都会使 φ³_ER 失效
   - 若无法保证完全独立，需在报告中标注相关度，作为 E-R 结果的限制说明

4. **spec 不可变性**：`S` 在 Stage I–IV 全程不可修改；任何临时修改都违反框架基本假设。

5. **LLM-β 数值只读**：LLM-β 只生成自然语言假说，不能修改 DiagReport 中的任何数值字段；违反触发 `SemanticOverwriteError`。

---

## 九、对本项目实现的直接影响

| CRE 框架要求 | 本项目（无人机避障 RL）对应 |
|-------------|--------------------------|
| 约束谓词 `O_j: S×A → {0,1}` | `done_type` 编码（2=collision, 3=out_of_bounds）可直接复用 |
| hard 约束边界距离 `d(s, ∂K_j)` | 已有 `near_violation_distance=0.5m`（D004，需在新版 spec 中确认） |
| 关键区域覆盖 Cov(K_j, E_tr) | 现有 env_cfg/shifted/boundary_critical.yaml 是实现此覆盖的环境配置 |
| Utility oracle U(π;e) | 需要独立于 reward 定义；候选：task-completion flag（`done_type==1`）+ safety monitor |
| spec → 结构化 S | Phase 1 的三份 YAML 就是 spec；格式须满足 CRE_v4.pdf §2.2 的表示要求 |
| 部署环境 E_dep | 已有 scene_cfg_base/nominal/shifted/boundary_critical.yaml，对应 e_0…e_n |
