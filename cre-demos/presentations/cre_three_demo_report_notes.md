# CRE 三个 Demo 汇报讲稿

这份讲稿与 `cre_three_demo_report.html` 一一对应，共 12 页。
建议用法：浏览器打开 HTML deck，讲稿面板可以同步查看；如果需要打印讲稿或发给讲解人，直接使用本文件。

## Slide 01 · 总览：为什么要用三个 Demo 讲同一套 CRE 方法

- 建议时长：1 分钟
- 讲稿：
  这一页先给汇报结论。我们不是拿三个彼此孤立的小例子来凑数，而是用三个受控实验把 CRE 的三类典型根因分别钉住：C-R 讲 reward 设计如何诱导危险行为，E-C 讲环境覆盖不足如何造成 critical family 失守，E-R 讲环境 shift 下 reward 与真实任务效用如何脱钩。三组实验都遵守同一套 Clean、Injected、Repaired 三联结构，所以可以横向比较，也可以顺着同一条证据链往下讲。
  第二个要点是，这三个 Demo 的角色分工非常明确。Demo 1 说明不能把高回报直接当成好策略；Demo 2 说明 nominal 看着能飞，不代表训练覆盖到真正关键的约束场景；Demo 3 说明 deployment shift 下，reward proxy 和任务 utility 不是一回事。三者合起来，正好把 CRE 的诊断、修复和验证闭环补齐。
- 过渡：
  接下来先把三组实验为什么可比讲清楚，再分别展开每个 Demo 的设计与结果。

## Slide 02 · 方法：三组实验共享的控制变量和证据链

- 建议时长：1 分钟
- 讲稿：
  为了让结论具有说服力，我们给三组 Demo 统一了实验语法。每一组都只有一个主导因子可以变化，并且都输出同一套 machine-readable evidence：verification summary、root-cause report、repair plan 和 validation decision。这样汇报时不是靠口头解释说服别人，而是每一步都有结构化证据可回查。
  另外，三组 witness 其实分别回答不同问题。W_CR 问的是 reward 有没有把策略往危险边界拉；W_EC 问的是训练环境有没有把关键危险区域覆盖进去；W_ER 问的是 reward proxy 在环境 shift 下还能不能代表真实任务效用。把这三个问题拆开，才能避免误诊断。
- 过渡：
  有了共同实验语法之后，我们就可以先横向给结论，再回到每个 Demo 的局部细节。

## Slide 03 · 横向矩阵：三类 failure 现象相似，但根因与修法完全不同

- 建议时长：1 分钟
- 讲稿：
  这一页建议当作听众的导航页。表格里最重要的是三列：被隔离的单一变量、主导 witness、以及 repair 怎么做。Demo 1 只改 reward，所以修法也应该回到 reward 侧；Demo 2 是训练覆盖问题，所以修法必须补 critical family；Demo 3 是 utility 解耦问题，所以修法要把 shifted robustness 拉回来，而不是一味继续堆 reward。
  横向看数字也能发现规律。Injected 版本的 witness 都明显升高，但它们恶化的方式不同：Demo 1 是 risky route rate 直接拉满，Demo 2 是 nominal 还能飞但 critical gap 撕开，Demo 3 则是 reward retention 还高、utility retention 却掉穿。正是这种模式差异，让 CRE 的分类诊断有意义。
- 过渡：
  下面先看 Demo 1，它回答的是 reward 本身会不会把策略诱导到危险边界上。

## Slide 04 · Demo 1 设计：只改 reward，不改场景

- 建议时长：1 分钟
- 讲稿：
  Demo 1 的设计重点是把环境完全固定住。图里可以看到同一个起点、终点和双通道布局，其中内侧通道更短但净空更小，外侧通道更长但更安全。我们要求三组版本的几何、seed 和训练预算都不变，只允许 reward 平衡改变，这样一旦轨迹选择发生系统性转移，就可以把根因指向 reward 设计，而不是别的因素。
  另一张轨迹图是这个实验最直观的证据。健康策略会更多选择外侧安全通道；Injected 版本则开始贴着内侧边界飞，说明它被 progress-style reward 推向了短而险的捷径。这里真正想说明的是偏好发生了结构性变化，而不是单次偶然失误。
- 过渡：
  设计讲清楚之后，我们就看结果页，重点看 injected 为什么不是简单地变差，而是变得更危险。

## Slide 05 · Demo 1 结果：回报更高，但安全裕度和路线选择同时恶化

- 建议时长：1 分 30 秒
- 讲稿：
  这里要特别强调一个反直觉现象：Injected 版本的 average return 从 17.66 上升到 20.33，看上去像是学得更好了，但 success rate 从 100% 掉到 66.7%，collision rate 从 0 提升到 33.3%，min distance 从 0.368 缩到 0.067。也就是说，回报提高并没有代表真实行为变好，反而是在奖励函数牵引下更频繁地压着危险边界走。
  再看结构性指标，risky route rate 从 0 直接拉到 1，near violation ratio 从 5.6% 提高到 57.9%，W_CR 飙到 0.718。Repair 后这些值基本回到 clean 水平，而且 success rate 恢复到 100%。所以这不是策略能力不够，而是 reward 目标和安全意图发生了冲突，修 reward 才是对症下药。
- 过渡：
  第二组 Demo 会把 reward 固定住，说明另一类问题其实来自训练环境覆盖不足。

## Slide 06 · Demo 2 设计：reward 固定，只让训练覆盖率出问题

- 建议时长：1 分钟
- 讲稿：
  Demo 2 的关键是把 reward 彻底冻结，然后人为制造训练分布偏置。左侧的场景对比图展示了 nominal family 和 boundary-critical family 的几何差异，右侧覆盖热图展示了 injected 训练样本主要堆在宽通道和开阔区域，真正危险的楔形区几乎没被充分访问。
  这个实验要证明的不是策略全面变差，而是策略在它熟悉的 nominal family 里还能维持表面可接受的表现，但一旦到了真正考验约束的 critical geometry，问题就暴露出来。所以这里的核心不是 reward 调错了，而是训练集没有把该见的关键场景见全。
- 过渡：
  接下来我们看结果页，重点关注 nominal 和 critical 之间的性能裂口。

## Slide 07 · Demo 2 结果：nominal 还能飞，但 critical family 明显掉穿

- 建议时长：1 分 30 秒
- 讲稿：
  这一页最关键的证据是 success gap。Injected 版本 nominal success 还有 91.7%，如果只看常规演示回放，很容易误判为模型还算稳定；但 critical success rate 只剩 16.7%，boundary-critical versus nominal success gap 扩大到 0.75，critical collision rate 上升到 41.7%，critical region failure rate 也达到 71.4%。
  这组结果非常适合说明 E-C 与 C-R 的区别。这里 reward 没有变化，却依然出现明显失败，说明根因不在 reward。Repair 的方式也因此不同，我们不是去改奖励，而是把 critical route bias 和关键几何重新注回训练流程。修复后 critical success 回到 66.7%，collision 和 region failure 都降回 0，验证结果也被接受。
- 过渡：
  第三组 Demo 会再往前走一步，讨论 deployment shift 下 reward 为什么会和真实任务 utility 脱钩。

## Slide 08 · Demo 3 设计：只改评估环境，并把 utility 单独冻结出来

- 建议时长：1 分钟
- 讲稿：
  Demo 3 的设计思想是：先把 nominal 训练和 reward 定义全部冻结，然后只在评估侧引入轻中度环境 shift。图里可以看到门洞发生了横向位移，通行区也变窄，但任务并没有被设计成不可能完成。这样做的目的是制造一种最容易误判的情况，也就是 reward 还在给正反馈，可真正的任务效用已经下降。
  因此这个 Demo 不是直接拿 reward 当结果，而是额外冻结了一个独立的 utility 聚合指标 U_task_v1，把 success、collision、timeout、clearance 和效率组合进来。只有把 utility 从 reward 里分离出来，我们才能严格证明 E-R 的解耦，而不是把问题重新说成 reward 写错了。
- 过渡：
  有了这个设计前提，下一页的散点图和恢复图就会特别有解释力。

## Slide 09 · Demo 3 结果：reward 仍然像回事，但 utility 已经掉穿

- 建议时长：1 分 30 秒
- 讲稿：
  这一页建议先讲最打人的数字。Injected 版本的 reward retention under shift 还有 93.2%，如果只看 return，很多人会觉得策略并没有显著退化；但 utility retention under shift 只剩 24.4%，reward-utility decoupling gap 扩大到 0.688，shifted success 也从 83.3% 掉到 33.3%。这说明 reward proxy 已经失去了代表真实任务效果的能力。
  Repair 后我们看到的是另一种恢复模式：reward retention 继续保持在 96.7%，utility retention 回升到 78.5%，decoupling gap 收窄到 0.182，shifted success 恢复到 83.3%。这组结果特别适合作为 E-R 的展示，因为它不是简单地让所有指标一起好转，而是准确地缩小了 reward 和 utility 之间的裂口。
- 过渡：
  看完三组局部细节之后，我们回到横向层面总结怎么区分这三类问题。

## Slide 10 · 交叉对比：不要把三类问题混成同一种“飞得不好”

- 建议时长：1 分钟
- 讲稿：
  这一页的目的，是帮助听众把表面相似的失败现象重新拆开。三组 Demo 都可能出现碰撞、贴边、成功率下降，但诊断逻辑不一样。若危险捷径偏好在固定几何下被稳定放大，就是 C-R；若 nominal 还能过、critical 明显掉穿，就是 E-C；若 reward 看着还行但 utility 掉穿，就是 E-R。
  更重要的是修法映射。C-R 应该从 reward 或 safety penalty 下手，E-C 要补训练覆盖，E-R 则要增强 shifted robustness 和 utility 对齐。只有把现象、witness 和 repair 对上，CRE 的修复流程才不会流于经验主义。
- 过渡：
  最后两页我会把这份汇报依赖的支撑材料和推荐收束结论一起给出来。

## Slide 11 · 支撑材料：汇报时每一页都能回到具体证据文件

- 建议时长：1 分钟
- 讲稿：
  这一页主要用来回答一个常见问题：这些图是不是只适合演示，不适合复核？答案是否定的。每个 Demo 我们都保留了截图、回放、verification summary、root-cause report、repair plan 和 validation decision，所以汇报里的每一个判断都能落回机器可读文件。
  汇报时可以根据对象灵活切换证据粒度。面对管理或评审，可以停留在图和关键指标层；面对研发同学，可以直接跳到对应 README、JSON 或 replay 页面，验证 witness、repair operator 和 validation status 是否真的闭环一致。
- 过渡：
  最后一页我会把三组 Demo 串成一句完整的汇报结论，并给出下一步建议。

## Slide 12 · 结论：三组 Demo 已经把 CRE 的诊断、修复、验证故事讲闭环

- 建议时长：1 分钟
- 讲稿：
  如果只用一句话总结这份汇报，那就是：我们已经用三组受控实验把 CRE 的三类核心 failure mechanism 分别钉住，并且每一组都完成了 Injected、Repair、Validation 的闭环。它们共同说明，RL 系统失效不能只看 reward 或单次回放，而必须回到 witness、根因和修复证据链去判断。
  接下来的工作也很自然。对外汇报时，可以用这套 deck 做统一叙事；对内工程推进时，可以把这三组 Demo 当作回归基线，持续检查 reward 侧、coverage 侧和 shift robustness 侧是否再次出现已知问题。这样这份材料就不仅是一次展示，也是一套可复用的审计模板。
- 过渡：
  汇报结束后，可以根据提问深度回跳到任意 Demo 页，或者直接打开对应 artifact 做现场追溯。
