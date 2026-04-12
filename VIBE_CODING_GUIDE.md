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

---

## 标准工作流：每次新会话怎么开始

### 第一步：粘贴启动 Prompt

每次开新会话，**第一条消息**固定用这个模板：

```
请先阅读以下文件，然后等待我的指令：
1. AGENTS.md
2. DECISIONS.md
3. INTERFACES.md
4. STATUS.md
5. doc/CRE_v4.pdf（第1-10页即可，了解理论背景）

读完后告诉我：
- 你理解的当前 Phase 是什么
- 当前最紧迫的下一步是什么
- 有没有发现任何文件间的矛盾
- 本次任务开始前必须先冻结哪些接口或决策
```

> **为什么这样做**：AI 没有跨会话记忆。这个启动 prompt 相当于给新同事的入职材料包。

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
