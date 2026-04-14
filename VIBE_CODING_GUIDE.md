# Vibe Coding 使用指南 — CRE Framework

> 面向 vibe coding 新手。本文档告诉你：每次开新会话时读什么、怎么说、怎么推进，以及哪些坑要避开。

---

## 什么是 Vibe Coding？

Vibe coding 是指你不直接写代码，而是用自然语言描述意图，让 AI（Codex / Claude）来生成和修改代码。你的角色是**决策者和审查者**，AI 是执行者。

这套工作流能跑起来的前提是：**AI 每次开新会话时都能快速理解项目背景**，不需要你重新解释。这就是 `AGENTS.md`、`DECISIONS.md`、`INTERFACES.md`、`STATUS.md` 这 4 个文件存在的原因。

---

## 四个核心文件是什么

| 文件 | 作用 | 你什么时候改它 |
|------|------|---------------|
| `AGENTS.md` | 项目简介 + 目录结构 + 编码规则 + 当前 Phase + 必读清单 | Phase 切换时、规则变化时 |
| `DECISIONS.md` | 所有架构决策（为什么这样设计） | 做了新的架构决策时 |
| `INTERFACES.md` | 模块间接口契约（谁调用谁、传什么数据） | 接口新增/变更/实现完成时 |
| `STATUS.md` | 每个 Phase/模块的完成状态 + 下一步行动 | 每次完成一个任务后 |
| `REFACTOR_ROADMAP.md` | ⚠️ CRE 重构路线图（2026-04-12 起）：14 处偏差清单、Phase 0–8 执行计划 | 每次重构 Phase 完成时 |
| `TRACEABILITY.md` | PDF 条款 → 代码追溯表（每个函数实现后填写） | 每个函数完成后 |
| `HANDBOOK.md` | CRE 开发强制规范手册（防偏差 6 条规则，不可绕过） | 规则变更时（须在 DECISIONS.md 记录） |

---

## 标准工作流：每次新会话怎么开始

### 第一步：粘贴启动 Prompt

每次开新会话，**第一条消息**固定用这个模板：

```
你现在是 vibe coding 的指挥官，你不直接修改代码，而是给其他 agent 发布命令（prompt），
review 他们的修改，监督他们不要走偏，并避免上下文过长带来的遗忘。请先阅读以下文件，
然后等待我的指令：
1. AGENTS.md
2. HANDBOOK.md（⚠️ 必读：防偏差强制规范，优先级最高）
3. REFACTOR_ROADMAP.md（⚠️ 必读：重构路线图，当前重构阶段）
4. DECISIONS.md
5. INTERFACES.md
6. STATUS.md
7. TRACEABILITY.md（了解哪些函数已实现，哪些待实现）
8. doc/CRE_v4.pdf（先读与当前 Phase 相关的章节）

读完后告诉我：
- 你理解的当前重构 Phase 是什么（参考 REFACTOR_ROADMAP.md）
- 当前最紧迫的下一步是什么
- TRACEABILITY.md 中有哪些 ❌ 待实现的函数
- 有没有发现任何文件间的矛盾
- 本次任务开始前必须先满足哪些前置条件（HANDBOOK.md 第三章）
```

> **为什么新增 HANDBOOK.md 和 REFACTOR_ROADMAP.md**：2026-04-12 审计发现 14 处严重偏差，根因是历史 agent 未读 PDF 就编码。这两个文件是防止重演的核心机制，必须在每次新会话开始时阅读。

---

### 第二步：确认 AI 理解正确

AI 回复后，检查它说的 Phase 和下一步是否和你 `STATUS.md` 里写的一致。

如果不一致，直接纠正：
```
不对，当前 Phase 是 1，下一步是先根据 CRE_v4.pdf 设计新版 spec 格式，
旧版 spec_cfg/ 已删除，需要从头定义。
```

---

### 第三步：下达任务

确认理解一致后，给出具体任务。任务要**一次一个**，不要一次给 5 件事。

好的任务描述示例：
```
请阅读 doc/CRE_v4.pdf 第 X 章，总结 CRE 对 reward spec 格式的要求，
然后提案新版 reward_spec_v1.yaml 的字段结构。
```

不好的任务描述（太模糊）：
```
帮我完成 Phase 1
```

---

### 第四步：审查 AI 的输出

AI 生成代码或文件后，你需要检查：

1. **它有没有违反 `DECISIONS.md` 里的决策？** 比如用了 `gym.Env` 而不是 `TensorDict`
2. **它有没有照搬旧版 spec 格式？** 旧版 `spec_cfg/` 已删除，新版 spec 格式需根据 CRE_v4.pdf 重新定义
3. **接口是否和 `INTERFACES.md` 一致？** 比如函数签名、返回类型

发现问题时，直接指出：
```
你照搬了旧版 reward_spec_v0.yaml 的字段结构，但旧版 spec_cfg/ 已删除，
新版 spec 格式需要根据 CRE_v4.pdf 重新设计，请先读 CRE_v4.pdf 再定义格式。
```

---

### 第五步：完成任务后更新 STATUS.md

每完成一个任务，让 AI 更新 `STATUS.md`：

```
任务完成。请更新 STATUS.md：
- 把 [具体 Phase 或条目] 的状态改为 ✅
- 确认 DoD（完成判定）中所有产物已存在
- 把"立即下一步"的第一条删除（已完成）
- 如果有新发现的问题，加到待办列表
```

> **这一步很多人会跳过，但它是整个工作流的核心。** 如果 STATUS.md 不更新，下次新会话的 AI 会重复做已经做过的事。

---

## 完成 CRE Framework 的完整流程

当前项目在 **Phase 1（Spec 设计）**，从零开始。下面是从现在到完成的路线图：

### Phase 1：Spec 设计（当前起点）

```
任务 1：读 CRE_v4.pdf，理解 spec 格式要求
  → 让 AI 读 doc/CRE_v4.pdf（重点看 spec 定义相关章节）
  → 让 AI 总结三份 spec 各自需要哪些字段、类型、单位
  → 核对 STATUS.md 中 Phase 总览是否准确，必要时更新

任务 2：逐份设计并创建 spec 文件
  → reward_spec_v1.yaml：字段名、权重范围、单位、必填项
  → constraint_spec_v1.yaml：约束名、类型、阈值、严重等级
  → policy_spec_v1.yaml：动作/观测空间、执行频率
  → 每份文件在 DECISIONS.md 记录格式设计依据

任务 3：建立 Spec 校验器
  → 创建 analyzers/spec_validator.py
  → 能对三份 spec 做 schema 验证与基础一致性检查
  → 编写单元测试，输入合法 spec 通过、输入缺字段报错

完成判定（DoD）：
  → STATUS.md Phase 1 DoD 列表全部勾选 ✅
  → 三份 spec 文件存在，校验器可通过
```

### Phase 2：Static Analysis

```
任务 4：设计分析模块接口
  → 让 AI 读 CRE_v4.pdf 中关于静态分析的章节
  → 确定输入（三份 spec）和输出（结构化报告）格式
  → 在 INTERFACES.md 补充接口签名
  → 在 DECISIONS.md 记录设计决策

任务 5：实现 analyzers/static_analyzer.py
  → 基于 spec_validator.py 的输出，检测 C-R/E-C/E-R 三类冲突
  → 输出结构化报告（JSON/YAML）

任务 6：编写单元测试
  → 阳性测试：输入有 C-R 冲突的 spec，期望报告含对应问题
  → 阴性测试：输入合法 spec，期望报告无问题
  → 测试全部通过后更新 STATUS.md，将 Phase 2 标记为 ✅
```

### Phase 3 及后续

```
每个 Phase 开始前：
  1. 读 CRE_v4.pdf 对应章节，确认该 Phase 的输入/输出
  2. 确认上一 Phase 的 DoD 全部满足
  3. 在 INTERFACES.md 补充新接口定义
  4. 在 DECISIONS.md 记录关键设计决策

每个 Phase 结束时：
  1. 逐条检查 STATUS.md 中该 Phase 的 DoD
  2. 所有产物存在 + 单元测试通过 → 将该 Phase 标记为 ✅
  3. 更新"立即下一步"为下一 Phase 的第一个任务
```

---

## 注意事项

### 关于 AI 的记忆

- AI **没有跨会话记忆**。每次新会话都是全新的，它不记得上次做了什么。
- `STATUS.md` 就是它的"记忆替代品"。保持它最新是你的责任。
- 如果你忘了更新 STATUS.md，下次会话开始时先问 AI："请对比 STATUS.md 和代码库的实际状态，找出不一致的地方。"

### 关于决策

- `DECISIONS.md` 里的 FINAL 决策**不要轻易推翻**。每一条都有原因。
- 如果你觉得某个决策需要改变，先问 AI："如果我改变 D001（TensorDict 改为 gym.Env），会影响哪些模块？"让它做影响分析，再决定。
- 做了新决策后，立刻让 AI 把它加到 `DECISIONS.md`。

### 关于旧版代码

- 代码库中存在旧版 CRE 实现（`envs/cre_logging.py`、`runtime_logging/`、`scripts/train.py` 中的 CRE hooks、`logs/` 下的日志），**全部标记为参考材料，不应直接依赖**。
- 开发新模块前，先让 AI 读旧版对应代码，了解设计思路，然后根据新版需求决定沿用、重构还是重写。
- 标准提问方式：「请先读旧版的 [文件]，总结它的设计思路，然后根据 CRE_v4.pdf 中 Phase X 的要求，告诉我哪些可以复用，哪些需要重写。」

### 关于接口

- `INTERFACES.md` 里标 ❌ 的接口是需要新建的，标 🔶 的是旧版参考。
- 实现一个新接口后，让 AI 把 `INTERFACES.md` 里对应条目从 ❌ 改为 ✅（新版）。
- **不要把 🔶 直接改为 ✅**，旧版接口变为新版需要经过验证，在 DECISIONS.md 中记录验证结论后才能升格。

### 关于 spec 文件

- 旧版 `cfg/spec_cfg/`（`reward_spec_v0.yaml` 等）**已删除，不存在于代码库中，不要读、不要引用**。
- 新版 spec 格式需要根据 `doc/CRE_v4.pdf` 重新设计，从 `*_v1.yaml` 开始命名。
- 创建新 spec 文件时，在 `DECISIONS.md` 记录格式设计的依据。
- 新 spec 文件创建后，同样遵守不原地修改的规则：变更时创建更高版本（`*_v2.yaml`）。

### 关于 DoD（Definition of Done）

每个 Phase 的完成标准在 `STATUS.md` 的 Phase 详情里有明确列出。完成一个 Phase 的前提是：**DoD 列表中的所有产物都真实存在于代码库中，且单元测试通过**。不能只是"代码写了"，必须产物可验证。

让 AI 验证 DoD 的方式：
```
请检查 STATUS.md 中 Phase 1 的 DoD 列表，
逐条确认每个产物是否已存在于代码库中，给我一个 ✅/❌ 的清单。
```

---

## 常用 Prompt 模板

**开始新会话：**
```
请阅读 AGENTS.md、DECISIONS.md、INTERFACES.md、STATUS.md，
然后告诉我当前 Phase 和最紧迫的下一步。
```

**让 AI 读代码再修改：**
```
请先读 [文件路径]，理解现有实现，然后在其中添加 [功能描述]。
不要修改文件中与本次任务无关的部分。
```

**发现 AI 违反规则时：**
```
这违反了 DECISIONS.md 中的 [D编号]，原因是 [规则内容]。
请撤销这个改动，改用 [正确方式]。
```

**任务完成后更新状态：**
```
任务完成。请更新 STATUS.md：
- 把 [具体条目] 的状态改为 ✅
- 把"下一步行动"的第一条删除（已完成）
- 如果有新发现的问题，加到待办列表
```

**让 AI 做影响分析（改动前）：**
```
我想修改 [文件/接口/决策]，请先分析这会影响哪些模块，
列出所有需要同步修改的地方，然后等我确认再动手。
```

---

## 一句话总结

> 每次新会话：读 4 个文件 → 确认理解 → 一次一个任务 → 审查输出 → 更新 STATUS.md。
> 这个循环就是 vibe coding 的全部。

---

## 【新】单 Agent 标准工作流（CRE 重构专用）

> **适用范围**：CRE 分析模块重构期间（REFACTOR_ROADMAP.md Phase 0–8）。
> **核心设计**：链式自动生成——每个 Prompt 执行完后自动输出下一个可直接使用的 Prompt，你只需复制粘贴，不需要手动查找或填写模板。

---

### 你只需要做 3 件事

| 你做什么 | Agent 自动生成什么 |
|---------|-----------------|
| ① 粘贴 **Prompt A**（固定不改） | 诊断报告 + **Prompt B**（已填好具体值） |
| ② 复制粘贴 **Prompt B** | 核验结果 + **Prompt C**（有 ❌ 时）或 **Prompt D**（全 ✅ 时）；Prompt C 末尾附 Prompt D |
| ③ 粘贴 **Prompt E**（将完成汇报粘入） | Review 结论 + **修正指令**（有问题）或 **Prompt F**（通过）；Prompt F 末尾附下一个 Prompt B |

---

### 工作流全景图

```
新会话开始
  ↓
① 你：粘贴 Prompt A（固定不改）
  ↓
  Agent 输出：诊断报告 + Prompt B（已填好）
  ↓
  你：Review 诊断报告（1 分钟）
    有误 → 直接说出纠正内容 → Agent 重新输出诊断报告 + 新 Prompt B
    正确 → 复制 Prompt B
  ↓
② 你：粘贴 Prompt B
  ↓
  Agent 输出：前置条件 ✅/❌ 清单
    全部 ✅ → 直接输出 Prompt D（已填好）
    有  ❌ → 输出 Prompt C（针对缺失项的补充操作）
              Prompt C 末尾自动附 Prompt D
  ↓
  你：执行 Prompt C 中的操作（如有），然后复制 Prompt D
  ↓
  Agent 执行：读 PDF → 合约测试 → 实现 → 测试 → 更新追溯表
  Agent 输出：结构化完成汇报
  ↓
③ 你：复制完成汇报，粘贴进 Prompt E 发出
  ↓
  Agent 输出：Review 结论
    有问题 → 输出针对性修正指令（修正完成后重新汇报，再回到 ③）
    全部通过 → 输出 Prompt F（已填好）+ 下一个 Prompt B
  ↓
  你：复制 Prompt F 发出
  ↓
  Agent 收尾：更新 STATUS.md + INTERFACES.md
  ↓
  同一会话继续 → 复制 Prompt F 末尾的 Prompt B，回到 ②
  上下文过长   → 开新会话，粘贴 Prompt A
```

---

### Prompt A：开局诊断（每次新会话第一条消息，固定不改）

```
你现在是 CRE 框架开发的执行者，同时兼任本次会话的状态诊断者。

## 阶段一：读文档（按序完成，不可跳过）

请按以下顺序阅读文件，全部读完再输出：

1. HANDBOOK.md        — 记录 6 条强制规则（Rule 1–6）核心要点
2. REFACTOR_ROADMAP.md — 记录当前重构 Phase 编号和下一个未完成的 Step
3. TRACEABILITY.md    — 统计 ❌ 条目总数，找出第一个 ❌ 条目（函数名 + PDF 章节）
4. STATUS.md          — 记录当前 Phase DoD 第一个未勾选的条目
5. INTERFACES.md      — 记录下一个待实现函数的接口状态（[FROZEN]/[DRAFT]/[PENDING]）
6. DECISIONS.md       — 记录有无与下一步任务相关的 FINAL 决策

## 阶段二：输出诊断报告（格式固定，不允许省略任何字段）

---
### 诊断报告

当前重构 Phase：Phase [N] — [名称]
当前 Step：Step [N.M] — [任务名]
TRACEABILITY 进度：已完成 [X]/43，下一个待实现：[函数名/结构名]（[PDF 章节 + 页码]）
下一步接口状态：[FROZEN / DRAFT / PENDING]
相关 FINAL 决策：[决策 ID + 核心内容，或"无"]
文件间矛盾：[列出，或"无"]
判断：[当前最紧迫任务一句话] / 前置条件预判：[是否满足]

---

## 阶段三：生成 Prompt B（将以下方括号替换为具体值后输出）

注意：Phase 0 数据结构步骤去掉 [P6]；M5 相关步骤保留 [P6]。

---PROMPT-B-START---
请核验以下前置条件，每条输出 ✅（满足）或 ❌（不满足 + 原因）：

[FC-1] TRACEABILITY.md 中，[函数名/结构名] 已有登记行（状态为 ❌）
[FC-2] [实现文件路径] 存在，且 [函数名] 所需依赖类型已在其中定义
[FC-3] unit_test/test_[模块名]_contract.py 已存在（即使全部 fail）
[P2 ] [函数名] 的接口签名已在 INTERFACES.md 中标记为 [FROZEN]
[P6 ] （仅 M5 步骤保留）CFG 中 w_cr + w_ec + w_er = 1.0 已可验证

核验完成后：
- 全部 ✅ → 直接输出 Prompt D（已填好具体值）
- 有  ❌ → 对每个 ❌ 生成具体的 Prompt C 补充步骤，Prompt C 末尾附 Prompt D
- prompt C和prompt D的格式和内容参考@VIBE_CODING_GUIDE.md 中的示例，确保具体、可执行、且直接指向代码库中的文件/行。
---PROMPT-B-END---

等待你确认诊断正确后，复制上方 PROMPT-B 内容发出。
```

---

### Step 0.4 特例：legacy 清场专用 Prompt B / D / E

> **适用场景**：当 Prompt A 的诊断结果显示当前 Step 为 `Step 0.4 — 将历史实现移入 legacy/ 目录` 时，**不要直接使用通用函数实现版 Prompt B/D/E**，改用下面这一组。
>
> **目标**：把旧实现迁入 `analyzers/legacy/`、`repair/legacy/`，并同步清理引用与文档表述；这一步不是 PDF 函数实现任务，因此不应要求“先写合约测试再改 TRACEABILITY”。

#### Step 0.4 专用 Prompt B：前置条件核验

```
请核验 Step 0.4（legacy 清场）的前置条件，每条输出 ✅（满足）或 ❌（不满足 + 原因）：

[LC-1] STATUS.md 当前 Step 明确为 `Step 0.4 — 将历史实现移入 legacy/ 目录`
[LC-2] REFACTOR_ROADMAP.md 已把 Step 0.4 的目标写明为产出 `analyzers/legacy/`、`repair/legacy/`
[LC-3] 以下历史实现文件当前仍位于非 legacy 路径，且需迁移：
       - isaac-training/training/analyzers/static_analyzer.py
       - isaac-training/training/analyzers/dynamic_analyzer.py
       - isaac-training/training/analyzers/semantic_analyzer.py
       - isaac-training/training/analyzers/report_generator.py
       - isaac-training/training/repair/repair_generator.py
       - isaac-training/training/repair/validator.py
[LC-4] `isaac-training/training/analyzers/legacy/`、`isaac-training/training/repair/legacy/` 若不存在，可安全创建
[LC-5] 代码库中不存在必须继续从 canonical 路径直接 import 上述历史模块的强依赖；若有，已能列出所有引用位置
[LC-6] README / STATUS / 其他文档中与上述历史实现相关的表述，可同步降级为 historical/legacy，不会误伤 canonical M1/M4/M7/M8 主链路

核验完成后：
- 全部 ✅ → 直接输出 Step 0.4 专用 Prompt D（已填好具体值）
- 有 ❌ → 对每个 ❌ 生成具体的 Prompt C 补充步骤，Prompt C 末尾附 Step 0.4 专用 Prompt D
- Prompt C 必须直接指向具体文件/行或具体命令，避免抽象建议
```

#### Step 0.4 专用 Prompt D：执行 legacy 清场

```
前置条件已全部满足。现在开始执行 Step 0.4 legacy 清场。

任务：将历史实现迁入 legacy/ 目录，并清理对 canonical 主链路的误导性暴露

目标文件：
- isaac-training/training/analyzers/static_analyzer.py
- isaac-training/training/analyzers/dynamic_analyzer.py
- isaac-training/training/analyzers/semantic_analyzer.py
- isaac-training/training/analyzers/report_generator.py
- isaac-training/training/repair/repair_generator.py
- isaac-training/training/repair/validator.py

目标目录：
- isaac-training/training/analyzers/legacy/
- isaac-training/training/repair/legacy/

执行步骤（按序完成，不可跳步）：

Step 1 读文档上下文，输出迁移计划：
  - 读取 REFACTOR_ROADMAP.md Step 0.4、STATUS.md、DECISIONS.md 中与 `D-I23` 相关段落
  - 列出需要迁移的历史文件、需要同步修正的 import / README / 测试引用
  - 明确哪些文件属于 canonical 主链路，声明“不得移动/改写”

Step 2 搜索引用并建立清单：
  - 搜索上述历史实现文件在代码库中的 import、脚本入口、README、测试引用
  - 将结果分成：
    1. 必须改路径的代码引用
    2. 必须降级为 legacy/historical 的文档表述
    3. 可保留但需加注释的历史测试/附录引用

Step 3 执行迁移：
  - 创建 `analyzers/legacy/`、`repair/legacy/`（若尚不存在）
  - 将历史实现文件移入对应 legacy 目录
  - 保证这些文件迁移后语义不变，不把旧逻辑“顺手修成 canonical”
  - 若需要 `__init__.py` 或最小注释文件，补齐但保持只读参考定位

Step 4 修正引用与文档：
  - 修复所有仍指向旧路径的 import / 测试 / README 路径
  - README、STATUS、其他文档中若提及这些模块，必须明确标注为 `historical` / `legacy`
  - 不得把 legacy 模块重新包装成 canonical fallback、compatibility adapter 或当前主实现

Step 5 运行验证：
  - 运行与本次迁移直接相关的搜索命令，确认非 legacy 路径不再暴露这些历史模块
  - 运行 `pytest -q`，确认无新增 fail
  - 如存在必须保留的 legacy 测试入口，需在汇报中说明原因

Step 6 更新状态文档：
  - 更新 STATUS.md：将 Step 0.4 标记完成，刷新“立即下一步”为 canonical `M1.parse_nl_input()` contract-first
  - 如 REFACTOR_ROADMAP.md / README / DECISIONS.md / INTERFACES.md 因迁移发生必要同步，保持表述一致
  - 注意：Step 0.4 不对应新的 PDF 函数实现，因此此任务默认不改 TRACEABILITY.md，除非你能证明某一行追溯状态必须因“路径迁移”而调整

完成后输出以下汇报（格式固定）：

---REPORT-START---
任务：Step 0.4 legacy 清场
迁移文件：[
  "analyzers/static_analyzer.py -> analyzers/legacy/static_analyzer.py",
  "analyzers/dynamic_analyzer.py -> analyzers/legacy/dynamic_analyzer.py",
  "analyzers/semantic_analyzer.py -> analyzers/legacy/semantic_analyzer.py",
  "analyzers/report_generator.py -> analyzers/legacy/report_generator.py",
  "repair/repair_generator.py -> repair/legacy/repair_generator.py",
  "repair/validator.py -> repair/legacy/validator.py"
]
引用修正：[
  "文件路径: 修正内容",
  "..."
]
文档同步：[
  "STATUS.md: ...",
  "README.md: ...",
  "REFACTOR_ROADMAP.md: ...",
  "DECISIONS.md/INTERFACES.md: 无或具体内容"
]
验证：
  - 搜索检查：[命令/结果摘要]
  - pytest -q：[X] passed, 0 failed
TRACEABILITY.md：未改动 / 说明原因
下一步：Step [N.M] — [下一任务，通常为 canonical M1.parse_nl_input contract tests]
风险或遗留问题：[列出或"无"]
---REPORT-END---

禁止事项（触碰则整个任务重做）：
❌ 修改 canonical M1/M4/M7/M8 的接口定义来迁就 legacy 文件
❌ 把 legacy 模块继续放在原路径，同时再复制一份到 legacy/（双轨并存）
❌ 借“迁移”之名修改历史实现逻辑，导致行为变化
❌ 把 `parse_yaml_input()`、offline fallback、旧 patch/result 路线重新包装成 canonical 主链路
❌ 未验证引用就移动文件，导致 import 断裂
❌ 在未完成清场前，把 STATUS.md 写成“下一步直接实现 M1”而不说明 Step 0.4 已完成
```

#### Step 0.4 专用 Prompt E：Review legacy 清场汇报

```
请 Review 以下 Step 0.4 legacy 清场完成汇报：

---REPORT-START---
[将 Agent 输出的完成汇报粘贴在此处]
---REPORT-END---

Review 要点（逐条检查）：
[ ] 目标历史文件已全部迁入 `analyzers/legacy/` 或 `repair/legacy/`
[ ] 非 legacy 路径下不再保留同名历史实现主文件（避免双轨并存）
[ ] 所有 import / 测试 / README 引用已同步到新路径或明确降级为 historical/legacy
[ ] canonical M1/M4/M7/M8、`DiagReport` / `RepairProposal` / `AcceptanceVerdict` 主链路未被改坏
[ ] `pytest -q` 无新增 fail
[ ] STATUS.md 已将 Step 0.4 收尾，并把“立即下一步”切到 canonical `M1.parse_nl_input()` 的 contract-first 开发
[ ] 未把 YAML adapter、offline fallback、`RepairPatch` / `RepairResult` 路线重新包装成 canonical

根据 Review 结果输出（二选一）：

情况 A：发现问题
  输出 Review 诊断报告（每个问题一条）：
  - 问题编号：LGC-[N]
  - 检查项：[对应的 Review 要点]
  - 问题描述：[具体说明 + 文件路径/行号]
  - 根因：[为什么这仍然偏离 Step 0.4 目标]

  然后生成修正 Prompt：

  ---PROMPT-LGC-FIX-START---
  Review 未通过，需要修正以下 Step 0.4 偏差：

  [对每个问题 LGC-N 输出：]
  问题 LGC-[N]：[问题描述]
  位置：[文件路径 + 行号/模块名]
  修正要求：[具体修改动作]
  验证方式：[如何确认修正完成]

  修正完成后，重新输出以下格式：
  ---REPORT-START---
  任务：Step 0.4 legacy 清场
  迁移文件：[...]
  引用修正：[...]
  文档同步：[...]
  验证：
    - 搜索检查：[命令/结果摘要]
    - pytest -q：[X] passed, 0 failed
  TRACEABILITY.md：未改动 / 说明原因
  下一步：Step [N.M] — [下一任务]
  风险或遗留问题：[列出或"无"]
  修正说明：[本次修正了哪些问题 LGC-N，如何修正的]
  ---REPORT-END---
  ---PROMPT-LGC-FIX-END---

情况 B：全部通过
  输出：
  - “Step 0.4 legacy 清场通过”
  - 然后给出下一步建议：
    - 开始为 `M1.parse_nl_input()` 补 canonical contract tests
    - 再进入 `M1` 的 LLM-α 实现
    - 新会话可回到通用 Prompt A → Prompt B 链路
```

---

### Prompt B 执行后 Agent 的两种输出

**情况一：全部 ✅**

Agent 直接输出 Prompt D，你复制粘贴发出即可（见下方 Prompt D 结构）。

**情况二：有 ❌**

Agent 针对每个 ❌ 输出补充操作，结尾自动附 Prompt D：

```
❌ 前置条件未满足：

[FC-X] [具体缺失内容]
补充操作：[Agent 根据缺失类型生成的具体操作步骤]
完成标志：[如何判断这一项已满足]

---
所有补充完成后，复制以下 Prompt D 发出：

---PROMPT-D-START---
[已填好具体值的完整 Prompt D]
---PROMPT-D-END---
```

---

### Prompt D 结构（由 Agent 自动填写后输出，此处仅供参考）

```
前置条件已全部满足。现在开始执行编码任务。

任务：实现 [函数名]
文件：[实现文件路径]
PDF：doc/CRE_v4.pdf [章节 + 页码]
合约测试：unit_test/test_[模块名]_contract.py

执行步骤（按序完成，不可跳步）：

Step 1 读 PDF [章节 + 页码]，输出：
  - 完整函数签名（参数类型、返回类型）
  - 输入合约（约束条件）、输出合约（值域）
  - 公式编号（如 Eq.(11)）
  - Test Standards T1–TN 逐条原文
  - 错误码及触发条件

Step 2 填充合约测试：
  替换框架用例为真实测试逻辑。要求：
  对应 PDF T1/T2... 原文；含数值精度断言（如 assert abs(x-y) < 1e-9）；
  不只做"不崩溃"检查。运行确认全部 fail（pytest [合约测试文件] -v）。

Step 3 实现函数：
  注释格式 # CRE_v4 Eq.(N) Part I/II §X.Y；严格按 PDF 公式；
  输出超范围时 clamp；不用 legacy/ 代码；不建新数据结构。

Step 4 运行合约测试：pytest [合约测试文件] -v → 必须全部通过。

Step 5 运行全量测试：pytest -q → 不允许新增 fail。

Step 6 更新 TRACEABILITY.md：[函数名] 对应行 ❌ → ✅。

完成后输出以下汇报（格式固定）：

---REPORT-START---
实现函数：[文件路径]::[函数名]
PDF 公式：Eq.([N]) [章节]
合约测试：T1 [描述] ✅ | T2 [描述] ✅ | ...（逐条）
全量测试：[X] passed, 0 failed
TRACEABILITY.md：已更新 ✅
注释示例：# CRE_v4 Eq.([N]) [章节]
PDF 矛盾或问题：[列出或"无"]
---REPORT-END---

禁止事项（触碰则整个任务重做）：
❌ 用 len()/计数替代 PDF 公式
❌ 注释缺 PDF 公式编号
❌ 修改 legacy/ 目录下任何文件
❌ 合约测试通过前改 TRACEABILITY.md
❌ 创建 diag_report.py 以外的新数据结构
❌ 硬编码超参数（引用 CFG 字段）
```

---

### Prompt E：Review 汇报（将完成汇报粘入后发出，固定格式）

```
请 Review 以下编码任务完成汇报：

---REPORT-START---
[将 Agent 输出的完成汇报粘贴在此处]
---REPORT-END---

Review 要点（逐条检查）：
[ ] T1–TN 全部 pass，每条对应 PDF 原文描述，含数值精度断言
[ ] pytest -q 结果为 X passed, 0 failed（无新增 fail）
[ ] TRACEABILITY.md 对应行已改为 ✅
[ ] 注释含 PDF 公式编号（格式：# CRE_v4 Eq.(N) §X.Y）
[ ] 无禁止事项触碰

根据 Review 结果输出（二选一）：

情况 A：发现问题
  输出 Review 诊断报告（每个问题一条）：
  - 问题编号：G-[N]
  - 检查项：[对应的 Review 要点]
  - 问题描述：[具体说明，引用 PDF 章节或合约测试编号]
  - 根因：[判断为什么会出现这个问题]

  然后生成 Prompt G（可直接发给 coding agent 执行修正）：

  ---PROMPT-G-START---
  Review 未通过，需要修正以下问题：

  [对每个问题 G-N 输出：]
  问题 G-[N]：[问题描述]
  位置：[文件路径 + 函数名/行号]
  修正要求：[具体的修改操作，引用 PDF 章节或公式编号]
  验证方式：[修正后如何确认已解决，如运行哪个测试/检查哪个文件]

  修正完成后，重新输出以下格式的汇报，等待再次粘入 Prompt E：

  ---REPORT-START---
  实现函数：[文件路径]::[函数名]
  PDF 公式：Eq.([N]) [章节]
  合约测试：T1 [描述] ✅ | T2 [描述] ✅ | ...（逐条）
  全量测试：[X] passed, 0 failed
  TRACEABILITY.md：已更新 ✅
  注释示例：# CRE_v4 Eq.([N]) [章节]
  PDF 矛盾或问题：[列出或"无"]
  修正说明：[本次修正了哪些问题 G-N，如何修正的]
  ---REPORT-END---

  禁止事项（修正时同样适用）：
  ❌ 用 len()/计数替代 PDF 公式
  ❌ 注释缺 PDF 公式编号
  ❌ 修改 legacy/ 目录下任何文件
  ❌ 合约测试通过前改 TRACEABILITY.md
  ❌ 创建 diag_report.py 以外的新数据结构
  ❌ 硬编码超参数（引用 CFG 字段）
  ---PROMPT-G-END---

情况 B：全部通过
  输出"Review 通过"，然后生成 Prompt F 和下一个 Prompt B：

  ---PROMPT-F-START---
  Review 通过。请完成收尾：
  1. STATUS.md：勾选 [DoD 条目]（[ ] → [x]），更新"最后更新"日期，更新"立即下一步"
  2. INTERFACES.md（如有变更）：[函数名] 状态 [DRAFT] → [FROZEN]，
     DECISIONS.md 追加 D-I[N] 冻结记录
  3. 输出进度摘要：完成了什么 / TRACEABILITY 进度（X/43）/ 下一个 Step
  4. 生成下一个 Step 的 Prompt B（格式同 Prompt A 输出的 Prompt B，已填好具体值）
  ---PROMPT-F-END---
```

---

### 何时开新会话

| 情况 | 判断标准 | 处理方式 |
|------|---------|---------|
| 上下文过长 | Agent 重复内容或遗忘早期约束 | 等当前 Prompt F 收尾后开新会话 |
| 连续 2 次同类偏差 | 同一类型错误第二次出现 | 立即结束，从 Prompt A 重新开始 |
| 完成超过 3 个 Step | 同一会话 Step 数 > 3 | 建议开新会话 |

**开新会话不是失败，几分钟就能重建上下文。**

---

### 快速参考卡

```
你做什么                          Agent 自动输出什么
─────────────────────────────────────────────────────
① 粘贴 Prompt A（固定不改）  →  诊断报告 + Prompt B
② 粘贴 Prompt B              →  全部 ✅：Prompt D
                                 有  ❌：Prompt C（含 Prompt D）
   粘贴 Prompt D             →  执行编码 → 完成汇报
③ 将汇报粘入 Prompt E 发出  →  通过：Prompt F + 下一个 Prompt B
                                 不通过：Review 诊断 + Prompt G
   粘贴 Prompt G             →  修正执行 → 新完成汇报 → 再回到 ③
   粘贴 Prompt F             →  STATUS/INTERFACES 更新完成

每次 Prompt E Review 必须核查：
  ✅ 合约测试 T1–TN 全部 pass（含数值精度断言）
  ✅ pytest -q：X passed, 0 failed
  ✅ TRACEABILITY.md 对应行 ❌ → ✅
  ✅ 代码注释含 PDF 公式编号
  ✅ 无禁止事项触碰
```
