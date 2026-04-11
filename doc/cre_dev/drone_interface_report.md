## Policy
- 类型: PPO（TensorDictModuleBase，策略梯度训练）
- 文件: isaac-training/training/scripts/ppo.py
- 获取action方式: 通过 __call__(tensordict) 内部调用 self.actor(tensordict) 采样动作，再写入 ("agents", "action")
- 是否支持梯度: 是

## Trajectory
- 类型: TensorDict 轨迹批（训练由 SyncDataCollector 输出，评估由 env.rollout 输出）
- states格式: torch.Tensor，主要位于 ("agents", "observation", "state"/"lidar"/"dynamic_obstacle")
- actions格式: torch.Tensor，位于 ("agents", "action")
- rewards格式: torch.Tensor，位于 ("agents", "reward")，shape 对应 spec 为 (1,)

## Environment
- 继承: NavigationEnv -> IsaacEnv -> torchrl.envs.EnvBase（非 gym.Env）
- reset签名: def reset(self, tensordict: Optional[TensorDictBase] = None, **kwargs) -> TensorDictBase
- step签名: def step(self, tensordict: TensorDictBase) -> TensorDictBase
- 支持seed: 是

## UtilityOracle候选
- 函数名: summarize_rollout_metrics
- 评估方式: 对 rollout 的 stats 字段做 episode 级聚合，提取并平均 success_rate / collision_rate / return 等指标

- 函数名: aggregate_episode_records
- 评估方式: 对 episodes.jsonl 做运行级聚合，按 success_flag 计算 success_rate，并统计 done_type 分布与安全相关指标

## 潜在适配难点
- 接口范式差异: 该项目主交互是 TensorDict，不是常见 Gym 的 (obs, reward, done, info) tuple，需要适配层做键映射。
- action语义差异: Policy 输出/写入的是嵌套键 ("agents", "action")，部分模块还存在 action_normalized，需要统一到底层执行动作语义。
- done语义多通道: 同时有 done、terminated、truncated、done_type（编码+标签），若外部只支持单 done 标志会丢失终止原因。
- success口径不唯一: baseline 侧更偏“首个 done 时刻统计”，CRE 聚合侧是 episode 全轨迹 success_flag 聚合，跨模块对齐时需固定口径。
- 环境继承差异: NavigationEnv 非 gym.Env，reset/step 来自 TorchRL EnvBase 体系，依赖 TensorSpec/CompositeSpec。
- 轨迹持久化差异: 内存轨迹是 TensorDict，但落盘证据是 steps.jsonl/episodes.jsonl；在线评估与离线分析需要双向字段对齐。
