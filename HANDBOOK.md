# HANDBOOK.md — CRE 开发强制规范手册

> **定位**：本文件是所有 CRE 开发 agent 和 commander 的强制行为规范。  
> **权威性**：本文件规则优先级高于 AGENTS.md 中的通用规则，且高于任何口头/会话内指令。  
> **不可变性**：本文件内容变更须在 DECISIONS.md 中记录决策编号和变更原因。

---

## 第一章：为什么这份手册存在

2026-04-12，对 CRE 历史实现做了完整审计，发现 **14 处严重偏差**，所有偏差追溯到同一根因：

> **vibe coding agent 在未充分阅读 `doc/CRE_v4.pdf` 的情况下开始编码，用"看起来合理的近似"替代了 PDF 规定的精确算法。**

具体表现：
- φ²_CR（边界趋近分）用"issue 计数 / reward term 数量"替代
- Ψ_CRE 只计算 2 维（丢失了 E-R 维度）
- M2、M3、Stage III DP、Pipeline Orchestrator 完全缺失
- 核心数据结构 `DiagReport` 被四个自创结构替代

这份手册的每一条规则都对应一个已发生的偏差。**遵守规则 = 防止重蹈覆辙。**

---

## 第二章：六条不可绕过的强制规则

### Rule 1：先读 PDF，后动代码

**触发时机**：任何涉及 CRE 分析模块（M1–M8、DP、M5、PO）的编码任务开始前。

**要求**：
1. 读 `doc/CRE_v4.pdf` 中该模块对应的章节（见 `REFACTOR_ROADMAP.md` 各 Phase 的"PDF 依据"列）
2. 实现的每个函数，代码注释中**必须标注 PDF 公式编号**，格式：`# CRE_v4 Eq.(11) Part I §3.3`
3. 未标注 PDF 公式编号的函数 = 未完成

**违反后果**：commander 拒绝接受该产物，任务重做。

---

### Rule 2：先定数据结构，后写算法

**触发时机**：Phase 0 完成之前，任何算法函数不得创建。

**要求**：
1. 所有模块间传递的数据结构必须来自 `analyzers/diag_report.py`（Phase 0 产物）
2. 禁止创建替代数据结构（如自定义 `StaticReport`、`SemanticReport` 等）
3. 如需在 `DiagReport` 上扩展字段，必须先在 INTERFACES.md 声明，经 commander 冻结后再修改 `diag_report.py`

**违反后果**：`analyzers/legacy/` 中已有 4 个自创结构的教训——它们导致了整个 M5（Ψ_CRE）计算的系统性错误。

---

### Rule 3：先写合约测试（Contract Tests），后写实现

**触发时机**：每个函数实现前。

**要求**：
1. 把 PDF Part II 对应函数的 Test Standards（T1–Tn）转写为 pytest 用例
2. 合约测试文件路径：`unit_test/test_[模块名]_contract.py`
3. 测试必须包含**数值精度断言**（如 `assert abs(result - 0.0) < 1e-9`），不允许只做"不崩溃"检查
4. 实现完成后，所有合约测试必须通过

**合约测试的核心价值**：PDF 给出的 T1/T2/T3 等测试用例是从理论推导出的必要条件，只要实现通过这些测试，就能保证公式实现正确。跳过这步的代价是"代码能运行但结果完全错误"——这正是历史偏差的模式。

---

### Rule 4：TRACEABILITY.md 是完成的充要条件

**触发时机**：每个函数实现完成后，在标记 STATUS.md 之前。

**要求**：
```
必须完成：TRACEABILITY.md 对应行 ❌ → ✅
才能执行：STATUS.md 勾选对应 DoD 条目
```

**TRACEABILITY.md 填写格式**：
```markdown
| Part II §X.Y.Z | M?.function_name, Eq.(N) | analyzers/mN.py | function_name() | test_mN_contract.py::test_* | ✅ |
```

**违反后果**：STATUS.md 勾选无效，下一个 agent 将无法判断该函数是否真正按 PDF 实现。

---

### Rule 5：旧版实现只读，不修改，不调用

**触发时机**：任何时候。

**旧版文件列表**（全部在 `legacy/` 目录）：
- `analyzers/legacy/static_analyzer.py`
- `analyzers/legacy/dynamic_analyzer.py`
- `analyzers/legacy/semantic_analyzer.py`
- `analyzers/legacy/report_generator.py`
- `repair/legacy/repair_generator.py`
- `repair/legacy/validator.py`

**要求**：
- 允许：`Read` 这些文件，学习设计思路
- 禁止：在这些文件上做任何修改
- 禁止：在新代码中 `from analyzers.legacy.xxx import yyy`
- 禁止：把旧版文件当作"已完成"的实现引用

---

### Rule 6：Ψ_CRE 是三维评分，权重检验是硬约束

**触发时机**：任何调用 Ψ_CRE 计算的代码。

**要求**：
```python
# 在调用 compute_psi_cre 之前必须有：
assert abs(cfg.w_cr + cfg.w_ec + cfg.w_er - 1.0) < 1e-9, "CONFIG_WEIGHT_SUM_ERROR"
# 三个 canonical reporter 全部参与计算：
psi = 1 - (w_cr * f(phi_cr2) + w_ec * f(1 - phi_ec_bar) + w_er * f(phi_er3))
```

**默认值**（PDF Table 4）：`w_cr = 0.333, w_ec = 0.333, w_er = 0.334`

**违反后果**：phi_er3 永远为 0 时，injected_er benchmark 无法触发 alarm，整个 E-R 诊断能力失效（这已发生）。

---

## 第三章：每次 Phase 开始前的检查清单

Commander 发出 Phase N 的第一条命令前，必须确认以下所有项为真：

```
□ Phase N-1 的 TRACEABILITY.md 所有行均为 ✅
□ Phase N-1 的 STATUS.md DoD 全部勾选
□ REFACTOR_ROADMAP.md 中 Phase N 的所有前置依赖已满足
□ 本 Phase 依赖的数据结构已在 diag_report.py 中定义（frozen）
□ 本 Phase 的 INTERFACES.md 接口签名已经 commander 冻结
□ 本 Phase 的合约测试文件已创建（预期 fail 状态）
```

---

## 第四章：每次 Step 完成后的验收清单

Agent 汇报任务完成后，commander 必须验证：

```
□ 代码注释中有 PDF 公式编号（每个实现函数至少一处）
□ 合约测试（T1–Tn）全部通过，含数值精度断言
□ pytest 全量（含旧有测试）无新增 fail
□ TRACEABILITY.md 对应行已改为 ✅
□ 没有在 legacy/ 目录下创建或修改文件
□ 没有创建新的自定义数据结构（只使用 diag_report.py 中的类）
□ 如有新接口，已更新 INTERFACES.md
```

---

## 第五章：Commander 发命令的标准模板

每条命令必须包含以下五段（缺少任何一段，agent 可能产生偏差）：

```
【读 PDF】
请先读 doc/CRE_v4.pdf [精确章节，如：Part II §3.2.2, pp.28–29]。
记录以下内容：函数签名、输入合约、输出合约、公式编号、Test Standards T1–Tn。

【读现有代码】
请读 [具体文件路径]（如：analyzers/diag_report.py），确认可用的数据结构。

【先写合约测试】
在实现函数之前，先把 PDF Test Standards T1–Tn 写成 pytest 用例（文件：unit_test/test_Xn_contract.py）。
此时预期全部 fail。

【实现函数】
实现以下函数：
  文件：analyzers/mN.py
  签名：def function_name(param: Type, ...) -> ReturnType
  要求：每个实现行注明 PDF 公式编号；输出范围必须满足 [0, 1]（或规定范围）。

【完成标准】
- 合约测试 T1–Tn 全部通过（含数值精度）
- TRACEABILITY.md 对应行改为 ✅
- 无新增 pytest fail

【禁止事项】
- 不得用近似替代 PDF 公式
- 不得自创数据结构
- 不得修改 legacy/ 目录下的文件
- 不得在没有 PDF 依据的情况下添加额外功能

【完成判定】
  汇报格式：
  - 实现了哪个函数（文件路径 + 函数名）
  - 合约测试结果（T1–TN 各自 pass/fail）
  - 全量 pytest 结果（X passed, 0 failed）
  - TRACEABILITY.md 已更新（是/否）
  - 遇到的问题或 PDF 与现有代码的矛盾（如有）
```

---

## 第六章：常见偏差模式识别

以下模式是历史偏差的典型表现，一旦发现立即标记并重做：

| 偏差模式 | 识别特征 | 正确做法 |
|---------|---------|---------|
| 用 issue 计数替代估计器 | `phi_cr = len(issues) / total_terms` | 实现 M2.compute_phi_cr2（边界距离比） |
| 权重不为 3 维 | `w_cr = 0.5, w_ec = 0.5`（只有 2 项）| `w_cr=0.333, w_ec=0.333, w_er=0.334` |
| 估计器永远为 None | `phi_er = None` | 实现 M2.compute_phi_er3（done_type==1 作 oracle） |
| 自创中间报告结构 | `class StaticReport`、`class SemanticReport` | 使用 `DiagReport`（diag_report.py） |
| 修复不做候选集 | 每个 issue 直接生成 1 个 patch | 实现 M7：K'=2K 候选 → filter → rank |
| 验收只比较 issue 数 | `passed = len(after) < len(before)` | 实现 C1–C4 + N_max 循环（M8） |
| 无 PDF 公式标注 | 函数体无任何 `# Eq.(N)` 注释 | 每个计算步骤标注 PDF 章节和公式号 |
