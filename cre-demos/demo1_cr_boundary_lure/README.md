# Demo 1 开发计划

## 1. 文档定位

本文档是 **Demo 1：Class I（C-R）构造实验** 的中文开发计划。

它的用途不是介绍 CRE 理论，而是把 Demo 1 的开发边界、执行顺序、
实验留存物、视频采集物和验收标准写死，避免后续实现时跑偏。

对应的总规划来源：

- [cre-demos/README.md](../README.md)

本 Demo 的唯一主张是：

> 在环境固定的前提下，仅通过 reward 偏置，就能把策略推向危险边界。

如果实现后的现象不能支持这句话，就说明 Demo 1 做偏了。

---

## 2. 实验目标

### 2.1 主目标

证明：

- reward 设计本身会诱导策略偏向高风险边界区域
- 不是因为环境没覆盖
- 也不是因为分布迁移

### 2.2 对外展示目标

这个 demo 对外要让观众一眼看懂三件事：

1. 同一个场景里有两条路：
   - 一条更短但更危险
   - 一条更长但更安全
2. 注入后的 reward 会把策略推向危险通道
3. repair 后策略会重新回到更安全的路径选择

### 2.3 非目标

本 Demo **不**追求：

- 复杂环境泛化能力
- 多种 failure mode 同时出现
- OOD shift 证明
- critical coverage 证明

如果这些内容变成主角，这个 demo 就不是 `C-R` 了。

---

## 3. 核心因果假设

### 3.1 因果结构

固定：

- 环境
- 起终点
- 训练预算
- policy 结构
- seed 集

只改变：

- reward 权重
- reward 组成平衡

希望观察到：

`reward progress 偏置增强 -> 更偏好短而险的内侧通道 -> 更小 min_distance -> 更高 near_violation_ratio -> W_CR 上升`

### 3.2 不能接受的混因果

以下情况都算失败或跑偏：

1. clean 和 injected 的场景几何不一样
2. injected 其实主要是因为环境变难了
3. policy 在 injected 里全面崩掉，而不是“有选择地偏向危险边界”
4. repair 后只是整体变保守停住，不再完成任务

---

## 4. 场景设计方案

### 4.1 场景名称

建议正式命名：

- `demo1_cr_boundary_lure`

### 4.2 场景结构

场景必须满足：

- 一个起点
- 一个终点
- 两条都可通行的候选路径

路径 A：危险近路

- 路程短
- 靠墙 / 靠障碍边界
- 净空小
- reward 很容易给出“前进快、离目标近”的正反馈

路径 B：安全远路

- 路程略长
- 转弯更平缓
- 离障碍更远
- 从任务意图上更合理

### 4.3 推荐几何外观

推荐采用：

- “双通道”布局
- 通过一组静态障碍围出：
  - 内侧窄通道
  - 外侧宽通道

建议第一版先不要加入：

- 动态障碍
- 风扰动
- 复杂噪声

原因：

- 第一版最重要的是把 `reward -> boundary hugging` 的因果做干净

### 4.4 可视化要求

该场景必须能从俯视图一眼看出：

1. 哪条路更短
2. 哪条路更危险
3. clean / injected / repaired 三种轨迹分别偏向哪里

如果俯视图不直观，这个场景应该重做。

---

## 5. 版本划分

Demo 1 固定只做三个版本：

### 5.1 Clean

目标：

- 作为健康对照组

要求：

- progress reward 和 safety penalty 基本平衡
- policy 大多数时候走外侧更安全通道

### 5.2 Injected

目标：

- 制造明确的 `C-R` 矛盾

建议注入方式：

- 提高 `reward_progress.weight`
- 降低 `reward_safety_static.weight`

要求：

- 场景不变
- 训练设置不变
- 只改变 reward 偏置

预期现象：

- 更频繁走内侧窄通道
- 贴边飞行更明显
- min distance 下降
- near violation 增加

### 5.3 Repaired

目标：

- 证明 repair 能逆转这个 reward 引导问题

建议修复方式：

- 恢复 safety 权重
- 或增加 boundary-aware penalty

预期现象：

- 路径偏好回到安全通道
- `W_CR` 明显回落
- `min_distance` 恢复

---

## 6. 开发计划

建议按 6 个阶段推进，不要跳步。

### 阶段 A：设计冻结

目标：

- 冻结 Demo 1 的因果边界

要完成的事情：

1. 确认场景草图
2. 确认 clean / injected / repaired 的 reward 差异
3. 确认固定 seed 列表
4. 确认必须输出的图和视频

交付物：

- 本文档
- 一张简单场景草图

### 阶段 B：场景实现

目标：

- 把双通道场景做成可复现环境

要完成的事情：

1. 在 demo 专用目录下加入场景配置
2. 固定 start / goal
3. 固定障碍布局或固定 seed 对应布局
4. 确保 clean / injected / repaired 用的是同一场景

验收标准：

- 三个版本加载出的场景几何一致
- 俯视图可清楚看出双通道结构

### 阶段 C：reward 注入与修复配置

目标：

- 准备三套 reward 版本

要完成的事情：

1. clean reward config
2. injected reward config
3. repaired reward config

要求：

- 只改 reward
- 每次改动都必须记录 diff

验收标准：

- 三套 config 的差异只落在 reward 相关字段

### 阶段 D：训练与评估

目标：

- 生成 clean / injected / repaired 三组可比较结果

建议流程：

1. 训练 clean
2. 训练 injected
3. 训练 repaired
4. 用同一组 eval seed 评估三者

要求：

- 每个版本都保留：
  - train 日志
  - eval 日志
  - 模型 checkpoint

验收标准：

- 三组结果都可重放
- 三组评估都可比

### 阶段 E：可视化与证据整理

目标：

- 把现象变成一眼能懂的图

必须完成：

1. 场景截图
2. 轨迹叠加图
3. 核心指标图
4. 一页 take-away 摘要

验收标准：

- 不看代码，只看图也能说出：
  - injected 更贴边
  - repaired 更安全

### 阶段 F：对外演示打包

目标：

- 让这个 demo 能直接进入 HTML deck / 组会展示

要完成的事情：

1. 整理视频片段
2. 整理最终图表
3. 写简短中文/英文 take-away
4. 准备和总 deck 对应的最终素材路径

---

## 7. 建议目录结构

建议未来所有 Demo 1 专属文件都放在：

```text
cre-demos/demo1_cr_boundary_lure/
  README.md
  cfg/
    env_cfg/
    spec_cfg/
  scripts/
  assets/
    screenshots/
    videos/
  reports/
    clean/
    injected/
    repaired/
```

### 7.1 推荐文件职责

`cfg/env_cfg/`

- Demo 1 专用场景配置

`cfg/spec_cfg/`

- Demo 1 clean / injected / repaired reward 配置

`scripts/`

- 训练、评估、截图、轨迹叠加、视频生成脚本

`assets/screenshots/`

- 原始截图和精选截图

`assets/videos/`

- 原始录像和压缩版演示视频

`reports/clean|injected|repaired/`

- 每个版本独立保存运行和分析结果

---

## 8. 必须保存的实验数据

这一节是 Demo 1 最容易被忽略、但实际最重要的部分。

原则：

- 任何最终展示图，都必须能追溯到原始实验数据

### 8.1 必须保存的配置类数据

每个版本都必须保存：

1. 环境配置快照
2. reward 配置快照
3. policy / train 配置快照
4. seed 列表
5. clean / injected / repaired 的差异说明

建议文件：

- `config_snapshot.yaml`
- `seed_manifest.json`
- `reward_diff.md`

### 8.2 必须保存的训练输出

每个版本都必须保存：

1. 最终 checkpoint
2. 训练日志
3. 评估日志
4. acceptance / summary 类文件

建议文件：

- `checkpoint_final.pt`
- `train_manifest.json`
- `eval_manifest.json`
- `summary.json`

### 8.3 必须保存的轨迹类数据

这是 Demo 1 的核心证据，必须留。

至少保存：

1. step-level trajectory
2. episode-level summary
3. route choice 标记
4. 每个 episode 的最小障碍距离

建议文件：

- `steps.jsonl`
- `episodes.jsonl`
- `route_choice.json`
- `trajectory_summary.json`

### 8.4 必须保存的分析结果

至少保存：

1. `W_CR`
2. `min_distance`
3. `near_violation_ratio`
4. `collision_rate`
5. demo 自定义的 `short_corridor_choice_ratio`

建议文件：

- `metrics_summary.json`
- `dynamic_report.json`
- `validation_summary.json`

### 8.5 必须保存的可视化中间产物

不要只留最终图。

还要保存：

1. 场景俯视图原图
2. 轨迹叠加原图
3. 图表源数据
4. 最终导出版 PNG / SVG

建议文件：

- `scene_topdown_raw.png`
- `trajectory_overlay_raw.png`
- `chart_source.csv`
- `metrics_comparison.png`

---

## 9. 必须保存的视频或动画素材

Demo 1 非常适合视频化，因为“偏向危险边界”比静态图更容易说服人。

### 9.1 最低视频集

至少保存以下 4 类视频：

1. **场景介绍视频**
   - 展示双通道结构
   - 说明哪条是危险近路，哪条是安全远路

2. **clean 评估视频**
   - 展示 clean policy 倾向走安全路径

3. **injected 评估视频**
   - 展示 injected policy 更频繁贴边走近路

4. **repaired 评估视频**
   - 展示 repaired policy 回到较安全路径

### 9.2 推荐扩展视频

如果时间允许，再加：

1. **三联对比视频**
   - clean / injected / repaired 同屏对比

2. **俯视轨迹动画**
   - 多 seed 叠加播放

3. **指标变化动画**
   - `W_CR`
   - `min_distance`
   - `near_violation_ratio`

### 9.3 每类视频建议保存两个版本

每条视频建议保留：

1. 原始版本
   - 分辨率高
   - 不压字幕

2. 展示版本
   - 有标题
   - 有箭头 / 标签
   - 文件更小

建议文件命名：

- `scene_intro_raw.mp4`
- `scene_intro_captioned.mp4`
- `clean_eval_raw.mp4`
- `clean_eval_captioned.mp4`
- `injected_eval_raw.mp4`
- `injected_eval_captioned.mp4`
- `repaired_eval_raw.mp4`
- `repaired_eval_captioned.mp4`

### 9.4 视频拍摄重点

录视频时必须保证能看出来：

1. UAV 位置
2. 障碍边界
3. 目标点
4. 通道差异
5. 是否贴边飞行

建议加上：

- 起点标记
- 终点标记
- 危险通道红色框
- 安全通道绿色框

---

## 10. 必做图表清单

这个 demo 至少要产出下面 5 张图。

### 图 1：场景结构图

内容：

- 双通道静态俯视图
- 标出 start / goal
- 标出危险近路和安全远路

### 图 2：轨迹叠加图

内容：

- clean 多条轨迹
- injected 多条轨迹
- repaired 多条轨迹

目的：

- 直观看路径偏好变化

### 图 3：核心指标分组柱状图

指标：

- `W_CR`
- `min_distance`
- `near_violation_ratio`

### 图 4：通道选择比例图

指标：

- `short_corridor_choice_ratio`
- `safe_corridor_choice_ratio`

### 图 5：repair 前后恢复图

指标：

- injected vs repaired
- 显示：
  - `W_CR` 回落
  - `min_distance` 恢复

---

## 11. 最终交付建议

Demo 1 最终建议交付成以下内容：

### 11.1 面向内部研发

- 完整实验目录
- 原始日志
- 原始截图
- 原始视频
- 指标 JSON

### 11.2 面向组会 / 汇报

- 1 页实验摘要 markdown
- 3~5 张图
- 1 个三联对比视频

### 11.3 面向后续 HTML deck

至少准备：

1. 一张最清晰场景图
2. 一张 trajectory overlay
3. 一张核心指标对比图
4. 一句中文结论
5. 一句英文结论

---

## 12. 验收标准

Demo 1 只有同时满足以下条件，才算完成：

### 12.1 因果验收

1. clean / injected / repaired 场景一致
2. injected 只改 reward
3. repaired 只做 reward 侧修复

### 12.2 现象验收

1. injected 明显更偏向危险近路
2. injected `min_distance` 明显更小
3. injected `near_violation_ratio` 明显更高
4. `W_CR` 是主方向
5. repaired 能明显逆转趋势

### 12.3 展示验收

1. 有场景图
2. 有轨迹图
3. 有指标图
4. 有视频
5. 不看代码也能看懂

---

## 13. 一页防跑偏清单

开始实现前，先逐条检查。

### 必须满足

- 环境固定
- reward 才是唯一主变量
- 双通道结构可视化明显
- 结果体现“更危险但更诱人”
- repair 能逆转

### 一旦出现就暂停

- 场景也变了
- injected 全面崩掉
- 主要现象变成 coverage 不足
- 主要现象变成分布迁移
- 没有视频或轨迹证据

---

## 14. 下一步建议

按下面顺序做最稳：

1. 先实现场景和俯视截图
2. 再冻结 reward 三版本
3. 再跑少量 seed 验证现象是否明显
4. 现象明显后再补全训练预算
5. 最后再做视频和对外展示打包

如果第一轮少量 seed 结果看不出“危险近路偏好”，不要急着扩训练，
先回到场景几何和 reward 差异上重调。

---

## 15. 当前实现状态

截至当前仓库状态，Demo 1 已经有一套可直接运行的隔离实现：

- 配置目录：`cre-demos/demo1_cr_boundary_lure/cfg/`
- 主脚本：`cre-demos/demo1_cr_boundary_lure/scripts/run_demo1.py`
- 轻量回归测试：`cre-demos/demo1_cr_boundary_lure/test_demo1_pipeline.py`
- 最新实验输出：`cre-demos/demo1_cr_boundary_lure/reports/latest/`
- 最新展示素材：
  - `assets/screenshots/demo1_scene_topdown.svg`
  - `assets/screenshots/demo1_trajectory_overlay.svg`
  - `assets/screenshots/demo1_metric_board.svg`
  - `assets/videos/demo1_replay.html`

### 15.1 当前实现的实验版本

当前实现不是把 PPO 训练链强行拉进来，而是先做了一个：

- 场景隔离
- reward 隔离
- 运行日志结构化
- CRE 分析链可复用
- 可视化可直接展示

的 demo substrate。

它的作用是先把 Demo 1 最重要的因果关系做干净：

> 同一几何场景下，只改 reward，策略就会从安全通道转向危险通道；
> 然后通过 reward 侧修复，再回到安全通道。

### 15.2 一键复现实验

```bash
python3 cre-demos/demo1_cr_boundary_lure/scripts/run_demo1.py --clean-output
```

### 15.3 当前验证结论

最新 `verification_summary.json` 已经给出：

- `goal_achieved = true`
- `report_primary_claim_is_cr = true`
- `repair_validation_accepted = true`

关键结果如下：

- Clean:
  - `risky_route_rate = 0.0`
  - `min_distance = 0.3685`
  - `near_violation_ratio = 0.0556`
  - `W_CR = 0.0103`
- Injected:
  - `risky_route_rate = 1.0`
  - `min_distance = 0.0673`
  - `near_violation_ratio = 0.5787`
  - `W_CR = 0.7180`
- Repaired:
  - `risky_route_rate = 0.0`
  - `min_distance = 0.3644`
  - `near_violation_ratio = 0.0556`
  - `W_CR = 0.0118`

### 15.4 当前 repair 叙事

当前 report / repair / validation 路径选择的修复算子是：

- `strengthen_safety_reward`

因此当前 repaired 版本采用的是：

- 保留较强 progress shaping
- 通过提升 `reward_safety_static.weight`
- 把路线偏好从危险近路拉回安全远路

这和 Demo 1 原计划中的“恢复 safety 权重”是一致的。

### 15.5 后续如果要升级成真实训练版

当前 demo 已经足够支撑展示与因果验证。

如果后续要升级成更重的 native 训练版，推荐顺序是：

1. 保留当前双通道几何不动
2. 把同样的 clean / injected / repaired reward 配置接到真实训练入口
3. 让训练结果继续输出同样的 step / episode / analysis 证据
4. 用当前 demo 的指标和图作为 native 版本的验收模板
