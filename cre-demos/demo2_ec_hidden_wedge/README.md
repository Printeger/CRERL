# Demo 2 开发计划

## 1. 文档定位

本文档是 **Demo 2：Class II（E-C）覆盖不足实验** 的中文开发计划。

它的用途不是重复 CRE 总体理论，而是把 Demo 2 的因果边界、开发顺序、
实验留存物、视频采集物和验收标准明确写死，避免后续实现时把它做成
reward 问题、迁移问题，或者只是一个泛泛的“难场景失败”示例。

对应的总规划来源：

- [cre-demos/README.md](../README.md)

本 Demo 的唯一主张是：

> 在 reward 不变的前提下，只因为训练环境对关键危险几何覆盖不足，
> 策略就可能在 nominal 场景看起来还行，却在 boundary-critical 场景明显失效。

如果最终现象不能支持这句话，就说明 Demo 2 做偏了。

---

## 2. 实验目标

### 2.1 主目标

证明：

- 主要问题不在 reward
- 主要问题在训练环境没有充分覆盖真正检验约束的危险区域
- `W_EC` 应该成为主导 witness

### 2.2 对外展示目标

这个 demo 对外要让观众一眼看懂三件事：

1. 训练时大多数场景太开阔、太顺，几乎没逼策略进入关键风险几何
2. 同一 reward 下，policy 在 nominal 回放里看起来还能完成任务
3. 一旦切到 boundary-critical 场景，失败会明显暴露出来；修复后又能收敛回来

### 2.3 非目标

本 Demo **不**追求：

- reward 误设证明
- 分布迁移鲁棒性证明
- 多个 failure mode 同时叠加
- “所有场景都变差”的弱策略展示

如果这些内容变成主角，这个 demo 就不是 `E-C` 了。

---

## 3. 核心因果假设

### 3.1 因果结构

固定：

- reward 定义与权重
- policy 结构
- 训练预算
- eval seed 集
- 任务语义

只改变：

- 训练场景族采样分布
- critical template 覆盖率
- repair 侧的环境注入策略

希望观察到：

`critical coverage 降低 -> 训练阶段几乎不遇到危险楔形/边界窄口 -> nominal 结果仍可接受 -> critical 场景 success/min_distance 明显恶化 -> W_EC 上升`

### 3.2 不能接受的混因果

以下情况都算失败或跑偏：

1. clean / injected / repaired 的 reward 不一致
2. eval family 在三版本之间偷偷变化
3. injected 结果其实是因为训练预算或 policy 结构变了
4. nominal 和 critical 全都同样差，无法说明“覆盖不足”
5. repair 后只是整体变保守或停住，而不是缩小 critical gap

---

## 4. 场景设计方案

### 4.1 场景族命名

建议正式命名：

- Demo 目录：
  - `demo2_ec_hidden_wedge`
- 训练 family：
  - `demo2_ec_open_bias_train`
- 评估 family：
  - `demo2_ec_hidden_wedge_eval`

### 4.2 训练场景族外观

训练族应当明显偏向：

- 宽通道
- 平缓转向
- 障碍间距较大
- 靠墙危险区较少

目的：

- 让策略在训练中很少接触真正危险的边界关键区

### 4.3 关键评估场景族外观

评估族应当明显包含：

- 窄 L 型拐角
- 贴墙 choke point
- 盲拐角或局部 clutter pocket
- 一块视觉上非常明确的危险楔形区

目的：

- 让观众一眼看出：
  - 这就是训练中几乎没见过、但真正检验约束的 critical geometry

### 4.4 可视化要求

该 demo 至少要能直观看出：

1. 训练样本主要覆盖了哪些区域
2. critical danger mask 落在什么位置
3. nominal scene 和 critical scene 的几何差异
4. clean / injected / repaired 在 critical 区的轨迹差异

如果看图看不出“训练没覆盖到关键危险区”，这个场景设计应该重做。

---

## 5. 版本划分

Demo 2 固定只做三个版本：

### 5.1 Clean

目标：

- 作为健康对照组

要求：

- reward 完全冻结
- 训练分布包含足够的 critical 几何
- nominal 和 critical 的性能差距应当可控

### 5.2 Injected

目标：

- 制造明确的 `E-C` 覆盖不足问题

建议注入方式：

- 降低 critical template 采样比例
- 让训练样本更偏向 open / easy scenes
- 仍然保持 reward、policy、budget 不变

要求：

- nominal eval 不能全面崩
- critical eval 要出现明显掉点

预期现象：

- nominal success 只轻度下降或基本稳定
- critical success 明显下降
- critical `min_distance` 明显更差
- `W_EC` 成为主方向

### 5.3 Repaired

目标：

- 证明环境侧 repair 能缩小 coverage gap

建议修复方式：

- 把 critical scene 注回训练集
- 提高 boundary-critical family 的采样权重
- 增加 curriculum 中的 high-risk template 占比

预期现象：

- nominal 指标不需要大幅提升
- critical gap 明显收窄
- `W_EC` 明显回落

---

## 6. 开发计划

建议按 7 个阶段推进，不要跳步。

### 阶段 A：设计冻结

目标：

- 冻结 Demo 2 的因果边界和场景族角色

要完成的事情：

1. 明确 train family 和 eval family 的命名
2. 明确危险楔形区 / critical region 的几何定义
3. 明确 clean / injected / repaired 的环境侧差异
4. 明确必须输出的图和视频

交付物：

- 本文档
- 一张 nominal vs critical 场景草图
- 一份 critical region 标注说明

### 阶段 B：训练族与评估族实现

目标：

- 把 open-bias train family 和 hidden-wedge eval family 做成可复现环境

要完成的事情：

1. 在 demo 专用目录下加入训练/评估场景配置
2. 固定 nominal 与 critical 的 family 元数据
3. 为 critical region 准备机器可读的 mask 或 annotation
4. 确保三版本共享同一 reward 和同一 eval 方案

验收标准：

- nominal / critical 场景截图差异清楚
- critical region 可被稳定标注
- eval family 在三版本之间完全一致

### 阶段 C：coverage 注入与修复配置

目标：

- 准备 clean / injected / repaired 三套环境覆盖版本

要完成的事情：

1. clean 训练分布配置
2. injected 训练分布配置
3. repaired 训练分布配置
4. coverage diff 记录

要求：

- reward 文件保持不变
- 每次只改环境采样或 template 配额
- 每次改动都必须记录 diff

验收标准：

- 三套配置差异只落在环境覆盖相关字段
- reward 快照完全一致

### 阶段 D：训练与评估

目标：

- 生成 clean / injected / repaired 三组可比较结果

建议流程：

1. 用各自 train family 训练三版 policy
2. 用同一组 nominal eval seed 评估三者
3. 用同一组 critical eval seed 评估三者
4. 保证输出能回溯到具体 scene family 与 seed

要求：

- 每个版本都保留：
  - train 日志
  - nominal eval 日志
  - critical eval 日志
  - 模型 checkpoint

验收标准：

- 三组结果可重放
- nominal / critical 对比可追溯
- family 标签完整进入日志

### 阶段 E：动态分析与证据整理

目标：

- 把 coverage gap 变成清晰的 machine-readable 证据

必须完成：

1. 计算 `W_EC`
2. 计算 nominal vs critical success gap
3. 计算 nominal vs critical min-distance gap
4. 计算 `critical_region_entry_rate`
5. 计算 `critical_region_failure_rate`

验收标准：

- 能从 JSON 直接读出关键 gap
- 能从 report 看出主方向是 `E-C`

### 阶段 F：可视化与证据打包

目标：

- 让“训练没覆盖到关键危险区”变成一眼能懂的图

必须完成：

1. 训练覆盖图
2. critical danger mask 图
3. nominal vs critical 场景对比图
4. 指标对比图
5. 一页 take-away 摘要

验收标准：

- 不看代码，只看图也能说出：
  - injected 训练阶段没覆盖到关键区
  - 所以 critical eval 掉得更厉害
  - repair 后 gap 缩小

### 阶段 G：对外演示打包

目标：

- 让这个 demo 能直接进入 HTML deck / 组会展示

要完成的事情：

1. 整理视频片段
2. 整理最终图表
3. 写简短中文/英文 take-away
4. 准备和总 deck 对应的最终素材路径

---

## 7. 建议目录结构

建议未来所有 Demo 2 专属文件都放在：

```text
cre-demos/demo2_ec_hidden_wedge/
  README.md
  cfg/
    env_cfg/
    spec_cfg/
    detector_cfg/
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

- Demo 2 专用训练/评估场景配置

`cfg/spec_cfg/`

- 冻结 reward 与任务语义快照，证明 reward 未变化

`cfg/detector_cfg/`

- critical region 与 witness 阈值相关配置

`scripts/`

- 训练、评估、coverage 统计、截图、轨迹叠加、视频生成脚本

`assets/screenshots/`

- 原始截图和精选截图

`assets/videos/`

- 原始录像和压缩版演示视频

`reports/clean|injected|repaired/`

- 每个版本独立保存运行和分析结果

---

## 8. 必须保存的实验数据

这一节是 Demo 2 最容易被忽略、但实际最重要的部分。

原则：

- 任何最终展示图，都必须能追溯到原始实验数据
- 任何“coverage 不足”的说法，都必须有机器可读证据支撑

### 8.1 必须保存的配置类数据

每个版本都必须保存：

1. train family 配置快照
2. eval family 配置快照
3. reward / spec 快照
4. policy / train 配置快照
5. seed 列表
6. clean / injected / repaired 的 coverage 差异说明

建议文件：

- `train_family_snapshot.yaml`
- `eval_family_snapshot.yaml`
- `spec_snapshot.yaml`
- `train_cfg_snapshot.yaml`
- `seed_manifest.json`
- `coverage_diff.md`

### 8.2 必须保存的训练覆盖类数据

这是 Demo 2 的核心证据，必须留。

至少保存：

1. 每轮训练采样到的 scene manifest
2. template 采样计数
3. nominal / boundary-critical family 混合比例
4. critical region 出现频次
5. 训练时用于生成场景的 seed 清单

建议文件：

- `scene_catalog.jsonl`
- `template_counts.json`
- `family_mix_summary.json`
- `coverage_manifest.json`
- `train_scene_seed_manifest.json`

### 8.3 必须保存的训练与评估输出

每个版本都必须保存：

1. 最终 checkpoint
2. 训练日志
3. nominal eval 日志
4. critical eval 日志
5. acceptance / summary 类文件

建议文件：

- `checkpoint_final.pt`
- `train_manifest.json`
- `eval_nominal_manifest.json`
- `eval_critical_manifest.json`
- `summary.json`
- `acceptance.json`

### 8.4 必须保存的轨迹与场景证据

这是 Demo 2 对外说服力的第二层基础。

至少保存：

1. step-level trajectory
2. episode-level summary
3. scene 实例清单
4. critical region mask 或 annotation
5. 每个 episode 的 failure breakdown

建议文件：

- `steps.jsonl`
- `episodes.jsonl`
- `trajectory_records.json`
- `scene_instance_manifest.json`
- `critical_region_mask.json`
- `episode_failure_breakdown.json`

### 8.5 必须保存的分析结果

至少保存：

1. `W_EC`
2. `boundary_critical_vs_nominal_success_gap`
3. `boundary_critical_vs_nominal_min_distance_gap`
4. `critical_region_entry_rate`
5. `critical_region_failure_rate`
6. report / repair / validation 结果

建议文件：

- `metrics_summary.json`
- `dynamic_report.json`
- `report.json`
- `repair_plan.json`
- `validation_summary.json`

### 8.6 必须保存的可视化中间产物

不要只留最终图。

还要保存：

1. nominal 场景俯视图原图
2. critical 场景俯视图原图
3. 训练覆盖热图原图
4. 图表源数据
5. 最终导出版 PNG / SVG

建议文件：

- `nominal_scene_topdown_raw.png`
- `critical_scene_topdown_raw.png`
- `training_coverage_heatmap_raw.png`
- `chart_source.csv`
- `coverage_gap_board.svg`

---

## 9. 必须保存的视频或动画素材

Demo 2 很适合视频化，因为“nominal 看起来还行，但 critical 一下暴露”
用动态回放比静态图更有说服力。

### 9.1 最低视频集

至少保存以下 5 类视频：

1. **训练覆盖介绍视频**
   - 展示训练阶段主要采样到的是 open / easy scenes

2. **critical 场景介绍视频**
   - 展示 hidden wedge / boundary-critical 几何
   - 说明哪块区域是关键危险区

3. **injected nominal 评估视频**
   - 展示 injected 在 nominal 下仍然“看起来还能跑”

4. **injected critical 评估视频**
   - 展示 injected 在 critical 场景明显失败

5. **repaired critical 评估视频**
   - 展示 repair 后 critical 表现回升

### 9.2 推荐扩展视频

如果时间允许，再加：

1. **clean / injected / repaired 三联 critical 对比视频**
2. **训练 coverage 热图动画**
3. **nominal vs critical 同 seed 对比视频**
4. **指标变化动画**
   - `W_EC`
   - success gap
   - min-distance gap

### 9.3 每类视频建议保存两个版本

每条视频建议保留：

1. 原始版本
   - 分辨率高
   - 不压字幕

2. 展示版本
   - 有标题
   - 有场景标签
   - 有 critical 区高亮
   - 文件更小

建议文件命名：

- `train_coverage_intro_raw.mp4`
- `train_coverage_intro_captioned.mp4`
- `critical_scene_intro_raw.mp4`
- `critical_scene_intro_captioned.mp4`
- `injected_nominal_eval_raw.mp4`
- `injected_nominal_eval_captioned.mp4`
- `injected_critical_eval_raw.mp4`
- `injected_critical_eval_captioned.mp4`
- `repaired_critical_eval_raw.mp4`
- `repaired_critical_eval_captioned.mp4`

### 9.4 视频拍摄重点

录视频时必须保证能看出来：

1. UAV 位置
2. 起点和终点
3. nominal / critical family 标签
4. critical 区域边界
5. episode 结果是 success / collision / timeout 哪一种

建议额外叠加：

- seed 编号
- scene id
- 当前 family
- critical wedge 红色框
- `min_distance` 或 failure 标签

---

## 10. 必做图表清单

这个 demo 至少要产出下面 6 张图。

### 图 1：训练覆盖图 vs danger mask

内容：

- 训练覆盖热图
- critical region mask
- 标出训练几乎没覆盖到的关键区

### 图 2：nominal vs critical 场景结构图

内容：

- 同一任务语义下的两类典型几何
- 标出 choke point、盲区、危险楔形区

### 图 3：success rate 分组柱状图

指标：

- nominal success rate
- critical success rate
- clean / injected / repaired 三组对比

### 图 4：min-distance gap 图

指标：

- nominal `min_distance`
- critical `min_distance`
- clean / injected / repaired 三组对比

### 图 5：critical 进入率与失败率图

指标：

- `critical_region_entry_rate`
- `critical_region_failure_rate`

### 图 6：repair 恢复图

指标：

- injected vs repaired
- 显示：
  - `W_EC` 回落
  - critical success gap 缩小
  - critical `min_distance` 回升

---

## 11. 最终交付建议

Demo 2 最终建议交付成以下内容：

### 11.1 面向内部研发

- 完整实验目录
- 原始日志
- coverage 统计 JSON
- 原始截图
- 原始视频
- 指标 JSON

### 11.2 面向组会 / 汇报

- 1 页实验摘要 markdown
- 4~6 张图
- 1 个三联 critical 对比视频

### 11.3 面向后续 HTML deck

至少准备：

1. 一张训练 coverage 图
2. 一张 nominal vs critical 场景对比图
3. 一张关键指标对比图
4. 一句中文结论
5. 一句英文结论

---

## 12. 验收标准

Demo 2 只有同时满足以下条件，才算完成：

### 12.1 因果验收

1. clean / injected / repaired 的 reward 一致
2. eval family 一致
3. injected 只改训练环境覆盖
4. repaired 只做环境侧修复

### 12.2 现象验收

1. injected nominal success 下降应较小
2. injected critical success 明显下降
3. injected critical `min_distance` 明显更差
4. `W_EC` 是主方向
5. repaired 能明显缩小 critical gap

建议量化目标：

- injected nominal success drop 小于 `10 pp`
- injected critical success drop 至少 `30 pp`
- repaired 至少收回一半 clean-to-injected 的 critical gap

### 12.3 展示验收

1. 有训练 coverage 图
2. 有 nominal vs critical 场景图
3. 有指标图
4. 有视频
5. 不看代码也能看懂“覆盖不足导致 critical 失效”

---

## 13. 一页防跑偏清单

开始实现前，先逐条检查。

### 必须满足

- reward 固定
- 环境覆盖才是唯一主变量
- nominal 和 critical 场景差异可视化明显
- 有 coverage 统计证据
- repair 能从环境侧缩小 gap

### 一旦出现就暂停

- reward 也变了
- eval family 也变了
- 所有场景一起崩
- 主要现象变成分布迁移
- 没有 coverage 证据，只有结果图

---

## 14. 下一步建议

按下面顺序做最稳：

1. 先把 nominal / critical 场景草图和 danger mask 冻结
2. 再补训练 coverage 统计接口
3. 再冻结 clean / injected / repaired 的 family 配置
4. 先跑少量 seed 验证是否能稳定出现 nominal-small-drop / critical-big-drop
5. 现象明显后再补全训练预算与视频打包

如果第一轮少量 seed 看不出明显的 critical gap，不要急着加大训练，
先回到 scene family 设计和 coverage 配额上重调。

---

## 15. 当前实现状态

截至当前仓库状态，Demo 2 还处于**规划阶段**，尚未像 Demo 1 那样形成
隔离实现与回归测试。

因此当前最合理的最小实现顺序是：

1. 先在 `cre-demos/demo2_ec_hidden_wedge/` 下冻结配置与文档
2. 再补一个 coverage 统计与可视化脚本
3. 再补一个隔离 runner
4. 最后再补轻量回归测试和 `reports/latest/`

在这四步之前，不建议直接把 Demo 2 混进主 benchmark 路径里实现。
