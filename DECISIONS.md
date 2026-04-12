# DECISIONS.md — 架构决策记录

所有标记为 FINAL 的决策不得在不更新本文件的前提下推翻。

> ⚠️ **关于旧版实现**：部分决策（D010–D019）引用了旧版代码中的具体实现或 spec 内容，这些旧版代码均已删除或标记为参考材料，不保证与新版 CRE 需求兼容。标注"旧版参考"的决策需在新版开发时重新验证后才能升格为 FINAL。

---

| ID | 范围 | 决策 | 原因 | 状态 |
|----|------|------|------|------|
| D001 | 数据格式 | 使用 TorchRL `TensorDict` 作为 env/policy/collector 边界的统一数据容器 | Isaac Sim 集成要求 TorchRL；`gym.Env` 范式与向量化 Isaac 环境不兼容 | FINAL |
| D002 | Policy | PPO 实现为 `TensorDictModuleBase` 子类 | 直接支持 TensorDict I/O，无需手动提取张量；`SyncDataCollector` 兼容性要求 | FINAL |
| D003 | Done 编码 | `done_type` 为多通道整数：0=running, 1=success, 2=collision, 3=out_of_bounds, 4=truncated | 单 bool `done` 丢失终止原因；CRE 分析需要分类统计 | FINAL |
| D004 | 安全阈值 | `near_violation_distance = 0.5m` 用于近距违规检测 | 匹配无人机物理尺寸 + 安全余量；新版 spec 定义后需重新确认是否沿用 | 旧版参考，待确认 |
| D005 | 成功判定 | episode 成功 = 终止时 `goal_distance < 0.5m`（即 `done_type == 1`） | 与物理停靠容差匹配；新版 spec 定义后需重新确认 | 旧版参考，待确认 |
| D006 | 配置管理 | 所有训练/eval/audit 配置走 Hydra（`cfg/`） | 可组合配置、支持 sweep、保证可复现性 | FINAL |
| D007 | 实验跟踪 | WandB 记录训练指标；CRE 分析结果另行决定如何记录 | 集中可见性；CRE 结果记录方式待 Phase 8（Integration）设计时决定 | FINAL（WandB 部分）；CRE 记录方式待定 |
| D008 | Spec 版本控制 | 新版 spec 文件从 `*_v1.yaml` 开始命名（旧版 v0 已删除）；后续变更创建更高版本，禁止原地修改 | 旧版 `cfg/spec_cfg/` 已删除；新版需根据 CRE_v4.pdf 重新设计格式 | FINAL |
| D009 | 新包位置 | `analyzers/`、`repair/`、`pipeline/` 等新包均在 `isaac-training/training/` 下创建，与 `envs/`、`runtime_logging/` 同级 | 与现有包结构保持一致；具体包结构待阅读 CRE_v4.pdf 后确定 | FINAL |
| D010 | Reward 组件 | 旧版记录 6 个组件：`reward_progress`、`reward_safety_static`、`reward_safety_dynamic`、`penalty_smooth`、`penalty_height`、`manual_control` | 旧版 spec 已删除；新版组件定义需根据 CRE_v4.pdf 重新确定 | 旧版参考，待重新定义 |
| D011 | Constraint 定义 | 旧版记录 5 个约束：`collision_avoidance`、`safety_margin`、`workspace_boundary`、`speed_bound`、`attitude_turn_rate` | 旧版 spec 已删除；新版约束定义需根据 CRE_v4.pdf 重新确定 | 旧版参考，待重新定义 |
| D012 | CRE 日志单元 | 旧版用 `FlightEpisodeLogger` 作为 per-episode 日志写入器 | 旧版设计思路；新版日志架构需根据 CRE_v4.pdf 重新设计 | 旧版参考，待重新设计 |
| D013 | TensorDict 适配器 | 旧版用 `TrainingRolloutLogger` 桥接 TensorDict batch 到日志器 | 旧版设计思路；新版适配器需与新版 CRE 日志格式对齐 | 旧版参考，待重新设计 |
| D014 | 日志聚合 | 旧版用 `aggregate_log_directory(run_dir)` 计算运行级指标 | 旧版设计思路；新版聚合逻辑待定 | 旧版参考，待重新设计 |
| D015 | Acceptance Check | 旧版用 `run_acceptance_check(run_dir)` 作为 Phase 门控 | 旧版设计思路；新版 acceptance 规则需与新版分析结果对齐 | 旧版参考，待重新设计 |
| D016 | Success rate | 旧版 `cre_logging.py::aggregate_episode_records()` 比 `baseline_runner.py::summarize_rollout_metrics()` 更接近真值 | 两者均为旧版；新版需根据新 spec 重新定义 success 判定 | 旧版参考，待重新定义 |
