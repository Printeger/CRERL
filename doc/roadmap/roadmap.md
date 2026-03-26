Phase 0：冻结问题定义与成功标准
目标
先把项目研究对象锁死，避免后面边做边改题。
你要做什么
写一份 SPEC-v0.md，明确：
546. 任务
  -  室内无人机自主避障，到达目标点 
547. 状态
  -  例如：激光雷达距离、速度、姿态、目标相对方向、上一步动作 
548. 动作
  -  速度指令 / 角速度指令 / 连续控制 
549. 约束 CCC
  -  碰撞禁止 
  -  障碍安全距离下限 
  -  最大速度 / 最大姿态角 
550. 奖励 RRR
  -  goal progress 
  -  success bonus 
  -  time penalty 
  -  smoothness penalty 
551. 环境族 D\mathcal DD
  -  宽走廊 
  -  窄走廊 
  -  障碍密集 
  -  传感噪声增大 
552. CRE 总定义
  -  存在策略，能在部署环境族上同时满足任务、约束、稳定性 
553. 三类诊断
  -  C--R, E--C, E--R 
554. 修复空间
  -  reward reweighting 
  -  critical scenario injection 
  -  domain randomization 
这个阶段的理论只需要完成什么
只完成这 4 个对象：
F(S),ρ(S),WCR,WEC,WER,dspec\mathcal F(\mathcal S), \quad \rho(\mathcal S), \quad W_{CR},W_{EC},W_{ER}, \quad d_{\mathrm{spec}}F(S),ρ(S),WCR,WEC,WER,dspec
也就是：
-  可行集 
-  一致性边际 
-  三类 witness 
-  specification 改动距离 
验收指标
满足以下就过关：
-  有一份不超过 3 页的正式问题定义文档 
-  所有变量都能落到代码中 
-  团队内部或你自己看一遍，不再出现“这个奖励到底算不算正式定义的一部分”这种模糊点 
-  能明确写出“什么算成功、什么算失败” 
在无人机场景里的含义
这一步相当于先回答：
“我们训练的到底是不是室内避障到点任务？碰撞、安全边界、窄走廊这些算不算 deployment concern？”

---
Phase 1：先搭“可测环境”，不是完整训练环境
目标
让环境先服务“检测”，不是一上来服务“最优训练”。
你要做什么
搭一个 Gymnasium 风格的环境，至少支持：
-  固定随机种子 
-  参数化地图生成 
-  参数化障碍密度 
-  参数化走廊宽度 
-  参数化传感噪声 
-  每一步记录： 
  -  reward 总值 
  -  reward 各分量 
  -  是否碰撞 
  -  最小障碍距离 
  -  是否到达目标 
  -  当前速度/姿态 
  -  当前场景标签 
这一阶段不需要什么
不需要：
-  大规模训练 
-  最优 reward 
-  复杂 curriculum 
-  多算法比较 
验收指标
必须满足：
1784.  给定相同 seed，地图和轨迹可复现 
1785.  随机策略可以跑通 100 个 episode 不崩 
1786.  日志中能导出： 
  -  success rate 
  -  collision rate 
  -  min obstacle distance 
  -  trajectory length 
1787.  可以生成三类场景： 
  -  宽松场景 
  -  窄走廊场景 
  -  高噪声场景 
在无人机场景里的含义
这一步不是训练无人机变聪明，而是先保证：
你能系统地制造“宽走廊、窄走廊、障碍密集、传感器变差”这些情境。

---
Phase 2：用非 RL 策略先验证理论量是不是“会动”
目标
先验证你的理论量和检测指标不是死的。
你要做什么
先不用 RL。
 先做 3 类简单策略：
-  随机策略 
-  贪婪朝目标飞的策略 
-  保守避障规则策略 
然后计算：
- WCRW_{CR}WCR：高奖励是否靠近边界 
- WECW_{EC}WEC：critical states 覆盖率 
- WERW_{ER}WER：环境变化后的 performance gap 
为什么先不用 RL
因为如果一上来就 RL 训练失败，你会分不清是：
-  理论错了 
-  检测器错了 
-  环境有 bug 
-  训练没收敛 
验收指标
至少达到：
-  保守策略的碰撞率显著低于贪婪策略 
-  贪婪策略在窄走廊中 WCRW_{CR}WCR 更高 
-  仅在宽走廊训练出的策略，在窄走廊测试中 WECW_{EC}WEC / 违约率明显变差 
-  改变环境 proxy 后，某些策略的 WERW_{ER}WER 变大 
在无人机场景里的含义
比如：
-  一个“只看目标方向”的策略会更容易擦边飞 
-  一个“优先避障”的策略虽然慢，但安全
 如果你的指标连这种差异都反映不出来，理论就还不能往后推进。 

---
Phase 3：构造“可控不一致”基准
目标
故意造出你想检测的问题，检验 detector 是否真能识别。
你要做什么
构造 4 套 specification：
1. Clean spec
合理 reward，合理约束，合理场景分布
2. C--R inconsistent spec
例如：
-  progress reward 权重大 
-  near-obstacle penalty 弱 
-  导致无人机为了更快到目标，贴障碍飞 
3. E--C inconsistent spec
例如：
-  训练地图几乎都是宽走廊 
-  但测试里有窄走廊 
-  训练时几乎从不触发最小安全距离约束 
4. E--R inconsistent spec
例如：
-  奖励中有一个在简单地图里有效的 proxy 
-  例如“自由空间大”与前进方向高度相关 
-  但到复杂地图里这个 proxy 失效 
这一阶段的理论要补什么
把三类 witness 真正写成代码可计算量：
- WCRW_{CR}WCR：boundary-seeking / reward-violation coupling 
- WECW_{EC}WEC：critical region coverage 
- WERW_{ER}WER：transfer fragility / intervention gap 
验收指标
这是关键：
-  在你人为注入的 benchmark 上，正确 inconsistency 类型应排到 top-1 或 top-2 
-  我建议最初验收阈值： 
  -  类型识别命中率 ≥80%\ge 80\%≥80%
  -  severity 排序与人工预期基本一致 
-  三类 injected spec 的指标变化方向要符合预期 
在无人机场景里的含义
这一步等价于：
你自己故意把无人机任务“搞坏”，然后看系统能不能说清楚是哪里坏了。

---
Phase 4：引入简化 RL 训练，而不是完整版大训练
目标
确认你的 CRE 检测在“学出来的策略”上也成立。
你要做什么
选一个最稳的 baseline，例如：
-  PPO-Lagrangian 
-  SAC-Lagrangian 
-  或你当前最熟悉、能稳定跑的 Safe RL 方法 
先只在简化环境中训练。
 不要一开始就上最复杂室内图。
建议先从：
-  2D 或低复杂度 3D 
-  少量障碍 
-  固定目标 
-  有限地图模板 
开始。
你在这里需要完整 RL 环境吗
从这一步开始，需要。
 但仍然是“简化版完整训练环境”，不是终极版环境。
验收指标
clean spec 上至少满足：
-  成功率达到可接受水平，例如 ≥80%\ge 80\%≥80%
-  碰撞率低于一个初步阈值，例如 ≤10%\le 10\%≤10%
-  训练曲线稳定，不出现完全不学 
-  不同 seed 下结果方向一致 
然后对 inconsistent specs 检查：
-  C--R inconsistent spec 下，boundary-seeking 变高 
-  E--C inconsistent spec 下，test collision 在窄走廊明显升高 
-  E--R inconsistent spec 下，shifted env return / success 明显下降 
在无人机场景里的含义
这一步不是要追求最强 UAV policy，
 而是要证明：
当策略真是通过 RL 学出来之后，你的 CRE 框架还能抓到问题。

---
Phase 5：做第一版 Repair，只做 3 类最必要修复
目标
不要追求大而全的修复库，只做最必要、最可验证的修复。
只做这三类
A. C--R repair
-  reward reweighting 
-  boundary-aware penalty injection 
B. E--C repair
-  critical scenario injection 
-  curriculum oversampling 
C. E--R repair
-  structured domain randomization 
不建议现在做的
先不要做太重的：
-  复杂因果去混淆 
-  自动 constraint logic 重写 
-  多轮 LLM 自动生成+自动执行修复 
验收指标
修复要有量化收益。建议至少满足：
-  violation rate 下降至少 20%20\%20%
-  success rate 不下降超过 5%5\%5%
-  OOD gap 明显缩小 
- ΨCRE\Psi_{\mathrm{CRE}}ΨCRE 提升 
你可以把 accept rule 写成：
ΔΨCRE>0,ΔSafety>0,ΔPerf≥−ϵperf.\Delta \Psi_{\mathrm{CRE}} > 0,\quad \Delta \mathrm{Safety} > 0,\quad \Delta \mathrm{Perf} \ge -\epsilon_{\mathrm{perf}}.ΔΨCRE>0,ΔSafety>0,ΔPerf≥−ϵperf.
在无人机场景里的含义
比如：
-  原来无人机为了快到终点，总是在墙边擦飞 
-  你加了 boundary penalty 后，它飞得稍微保守一点 
-  只要碰撞明显减少，而到达率没有明显崩，这个修复就算有效 

---
Phase 6：把理论和修复收敛到“V1 框架”
目标
在进入复杂室内环境前，先把理论、检测、修复在简化任务上跑顺。
你要做什么
冻结以下内容：
5007.  CRE 总定义 
5008.  三类 witness 
5009.  consistency score 
5010.  repair objective 
5011.  accept / reject 规则 
5012.  诊断报告格式 
验收指标
满足以下才进入下一阶段：
-  对 4 套 specification，系统行为稳定 
-  不同 seed 下 detector 排序大体一致 
-  repair 的收益方向稳定 
-  你已经可以用 2--3 页文档把“理论对象—检测—修复—验证”完整讲清楚 
在无人机场景里的含义
这一步相当于：
你已经有了一个“在简化无人机避障任务上能闭环”的 CRE-v1。

---
Phase 7：扩到完整室内无人机训练环境
目标
从“方法成立”走向“应用成立”。
你要做什么
把环境升级到更真实的室内设置：
-  更复杂地图生成 
-  多种走廊宽度 
-  障碍类型更多 
-  传感噪声 / 失真更真实 
-  更长 episode 
-  更真实的动力学或控制约束 
这里你可以开始逐步贴近你的实际应用场景。
这一阶段要注意
不要一边扩环境一边大改理论。
 理论主干此时应该已经固定。
 这里只是测试理论在更真实场景下是否仍然有效。
验收指标
至少检查：
-  clean spec 下仍能稳定训练 
-  inconsistency 注入仍能被识别 
-  repair 收益在更真实环境中仍保留 
-  不同地图模板下结论方向一致 
在无人机场景里的含义
这一步才是你真正开始回答：
这个 CRE 框架对“室内无人机自主避障 RL 训练”到底有没有实用价值。

---
Phase 8：补理论增强与论文化验证
目标
把前面的工程闭环提炼成论文级理论与证据。
你要做什么
这时再补：
-  pairwise insufficiency 的反例 
-  undercoverage 不可识别性命题 
-  minimal repair 的存在性 / 局部改进命题 
-  有限样本估计误差界 
-  ablation 
-  runtime analysis 
验收指标
你应该能形成完整论文叙事：
-  问题存在 
-  理论定义闭合 
-  检测有效 
-  修复有效 
-  局限明确 

---
三、你到底应不应该先把理论全完善再做实验
答案很明确：
不应该。
最好的方式是：
先冻结“理论核心”
只先完成这几样：
6077.  CRE 总定义 
6078.  consistency margin ρ\rhoρ
6079.  三类 witness 
6080.  repair objective 
6081.  accept rule 的原则形式 
这已经足够支撑前 4 个阶段。
然后立刻测试
因为很多理论对象只有放到环境里，你才知道：
-  是否可计算 
-  是否有区分度 
-  是否会和实际日志脱节 
再迭代
只有当这一层“理论对象 + 指标 + 修复动作”在实验里表现稳定，才继续做更强理论。
所以正确节奏是：
最小理论→最小验证→修订理论→扩大验证\text{最小理论} \rightarrow \text{最小验证} \rightarrow \text{修订理论} \rightarrow \text{扩大验证}最小理论→最小验证→修订理论→扩大验证
而不是：
完整理论→很晚才第一次测试\text{完整理论} \rightarrow \text{很晚才第一次测试}完整理论→很晚才第一次测试
后者风险太大。

---
四、你前期到底需不需要完整 RL 环境
不需要完整训练环境的阶段
Phase 0--3：
-  问题定义 
-  可测环境 
-  非 RL 策略验证 
-  injected inconsistency benchmark 
这些阶段只需要：
-  reset / step 
-  场景参数化 
-  日志记录 
-  可复现种子 
-  简单策略运行 
需要简化版完整 RL 环境的阶段
Phase 4--6：
-  baseline training 
-  detector on learned policy 
-  repair validation 
需要更真实完整 RL 环境的阶段
Phase 7 以后：
-  真正贴近室内无人机场景 
-  更复杂地图与动力学 
-  更真实噪声与 shift 

---
六、最重要的验收总表
下面这张表你可以直接当项目进度表用。

