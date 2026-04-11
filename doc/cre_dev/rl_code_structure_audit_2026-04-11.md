# UAV 强化学习代码结构审计（2026-04-11）

> 范围：主训练链路（`isaac-training/training`）优先；补充 baseline 执行路径。

## 1) Policy / Agent 类

### 1.1 主训练策略：PPO
- 文件路径：`isaac-training/training/scripts/ppo.py`
- 类名：`PPO`
- 继承：`TensorDictModuleBase`（PyTorch `nn.Module` 体系）
- action 获取方式：`__call__` 内通过 `self.actor(tensordict)` 采样，再写入 `("agents", "action")`
- 梯度访问：支持（`loss.backward()` + optimizers + grad clip）

签名片段：
```python
class PPO(TensorDictModuleBase):
    def __init__(self, cfg, observation_spec, action_spec, device):
    def __call__(self, tensordict):
    def train(self, tensordict):
    def _update(self, tensordict):
```

### 1.2 baseline 策略接口（非学习型）
- 文件路径：`isaac-training/training/execution/baseline_policies.py`
- 类名：`BaselinePolicy`（以及 `RandomPolicy/GreedyPolicy/ConservativePolicy`）
- 继承：`dataclass` 普通类（不继承 `nn.Module`）
- action 获取方式：`__call__` -> `compute_action` -> 写 `("agents", "action")`
- 梯度访问：不支持训练梯度（`@torch.no_grad()`）

签名片段：
```python
@dataclass
class BaselinePolicy:
    def reset_seed(self, seed: int) -> None:
    def compute_action(self, observation: Mapping[str, torch.Tensor]) -> torch.Tensor:
    @torch.no_grad()
    def __call__(self, tensordict: Any) -> Any:
```

### 1.3 Actor 子网络（PPO 内部）
- 文件路径：`isaac-training/training/scripts/utils.py`
- 类名：`Actor`, `BetaActor`
- 继承：`nn.Module`
- action 参数输出：`forward(features)` 输出分布参数（`loc/scale` 或 `alpha/beta`）

签名片段：
```python
class Actor(nn.Module):
    def forward(self, features: torch.Tensor):

class BetaActor(nn.Module):
    def forward(self, features: torch.Tensor):
```

## 2) Episode / Trajectory / Buffer

### 2.1 rollout 数据存储位置
1. 在线采样批：`SyncDataCollector` 返回 `TensorDict`（训练循环变量 `data`）
   - 文件：`isaac-training/third_party/OmniDrones/omni_drones/utils/torchrl/collector.py`
   - 文件：`isaac-training/training/scripts/train.py`
2. 评估/基线轨迹：`env.rollout(...)` 返回 `TensorDict`（变量 `trajs`）
   - 文件：`isaac-training/training/scripts/utils.py`
   - 文件：`isaac-training/training/execution/baseline_runner.py`
3. CRE 日志缓冲：`TrainingRolloutLogger` 的 `_EpisodeBuffer.steps: list[StepLog]`，最终写入 `steps.jsonl` / `episodes.jsonl`
   - 文件：`isaac-training/training/runtime_logging/training_log_adapter.py`
   - 文件：`isaac-training/training/envs/cre_logging.py`

签名片段：
```python
class SyncDataCollector(_SyncDataCollector):
    def rollout(self) -> TensorDictBase:
    def iterator(self) -> Iterator[TensorDictBase]:

@dataclass
class _EpisodeBuffer:
    episode_index: int
    step_index: int = 0
    sim_time: float = 0.0
    steps: list[StepLog] = field(default_factory=list)

class TrainingRolloutLogger:
    def process_tensordict_batch(self, data: Mapping[str, Any], *, ...):
    def process_batch(self, data: Mapping[str, Any], **kwargs: Any) -> list[TrainingLogRecord]:
    def flush_open_episodes(self, done_type: str = "manual_exit") -> None:
```

### 2.2 observation 数据格式
- 主格式：`TensorDict` + `torch.Tensor`（不是 ndarray/dict-only）
- 定义位置：`NavigationEnv._set_specs()`
- 关键 observation 字段：
  - `("agents", "observation", "state")`: `UnboundedContinuousTensorSpec((8,))`
  - `("agents", "observation", "lidar")`: `UnboundedContinuousTensorSpec((1, lidar_hbeams, lidar_vbeams))`
  - `("agents", "observation", "dynamic_obstacle")`: `UnboundedContinuousTensorSpec((1, dyn_obs_num, 10))`

签名片段：
```python
def _set_specs(self):
    self.observation_spec = CompositeSpec({...})
```

### 2.3 reward 格式
- 格式：`TensorDict["agents"]["reward"]`，`torch.Tensor`
- spec：`UnboundedContinuousTensorSpec((1,))`
- 返回位置：`_compute_reward_and_done()`

签名片段：
```python
def _compute_reward_and_done(self):
    return TensorDict({
        "agents": {"reward": reward},
        "done": terminated | truncated,
        "terminated": terminated,
        "truncated": truncated,
    }, self.batch_size)
```

### 2.4 done / truncated 标记
- spec 中显式定义：`done`, `terminated`, `truncated`（bool）
- 运行时生成：
  - `self.terminated = out_of_bounds_flag | collision`
  - `self.truncated = progress_buf >= max_episode_length`
  - `done = terminated | truncated`
- 额外 done 类型编码：`done_type`（0 running / 1 success / 2 collision / 3 out_of_bounds / 4 truncated）

签名片段：
```python
self.done_spec = CompositeSpec({
    "done": DiscreteTensorSpec(2, (1,), dtype=torch.bool),
    "terminated": DiscreteTensorSpec(2, (1,), dtype=torch.bool),
    "truncated": DiscreteTensorSpec(2, (1,), dtype=torch.bool),
})
```

## 3) Environment 类

### 3.1 主训练环境
- 文件路径：`isaac-training/training/scripts/env.py`
- 类名：`NavigationEnv`
- 继承：`IsaacEnv`（来自 OmniDrones）
- 是否继承 `gym.Env`：否（继承链是 `NavigationEnv -> IsaacEnv -> torchrl.envs.EnvBase`）

签名片段：
```python
class NavigationEnv(IsaacEnv):
    def __init__(self, cfg):
    def _set_specs(self):
    def _compute_reward_and_done(self):
```

### 3.2 reset()/step() 签名
`NavigationEnv` 本身实现的是 `_reset/_step` 所需子钩子（由父类驱动），公共接口来自 `EnvBase`。

- `EnvBase`（公共 API）
  - 文件：`isaac-training/third_party/rl/torchrl/envs/common.py`
- `IsaacEnv`（子类实现入口）
  - 文件：`isaac-training/third_party/OmniDrones/omni_drones/envs/isaac_env.py`

签名片段：
```python
# EnvBase
def step(self, tensordict: TensorDictBase) -> TensorDictBase:
def reset(self, tensordict: Optional[TensorDictBase] = None, **kwargs) -> TensorDictBase:
def set_seed(self, seed: Optional[int] = None, static_seed: bool = False) -> Optional[int]:
def rollout(self, max_steps: int, policy: Optional[Callable[[TensorDictBase], TensorDictBase]] = None, ...):

# IsaacEnv
def _reset(self, tensordict: TensorDictBase, **kwargs) -> TensorDictBase:
def _step(self, tensordict: TensorDictBase) -> TensorDictBase:
def _set_seed(self, seed: Optional[int] = -1):
```

### 3.3 observation space / action space 定义
- 文件：`isaac-training/training/scripts/env.py`
- 在 `_set_specs()` 中定义：
  - `self.observation_spec = CompositeSpec({...})`
  - `self.action_spec = CompositeSpec({"agents": {"action": self.drone.action_spec}})`
  - `self.reward_spec` / `self.done_spec` 也同处定义

### 3.4 seed 控制
- 支持：是
- 用法：`env.set_seed(cfg.seed)`（训练/评估/baseline 中都有调用）
- 最终落到：`IsaacEnv._set_seed()`，设置 replicator 和 torch seed

## 4) 任务完成评估逻辑（success_rate / task_completion）

### 4.1 success_rate 计算函数

A. 基线统计聚合：
- 文件：`isaac-training/training/execution/baseline_runner.py`
- 函数：`summarize_rollout_metrics(rollout_metrics)`

签名片段：
```python
def summarize_rollout_metrics(rollout_metrics: Sequence[Mapping[str, float]]) -> Dict[str, Any]:
```
说明：从 `stats.reach_goal`（或 `reach_goal`）提取并平均为 `success_rate`。

B. CRE 运行日志聚合：
- 文件：`isaac-training/training/envs/cre_logging.py`
- 函数：`aggregate_episode_records(records)`

签名片段：
```python
def aggregate_episode_records(records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
```
说明：`success_rate = sum(success_flag)/episode_count`。

### 4.2 是否有 task_completion 函数
- 全仓（主训练路径）未发现名为 `task_completion` / `task_complete` / `completion_rate` 的函数。

### 4.3 基于最终状态还是全轨迹
- `baseline_runner.summarize_rollout_stats()`：基于“每个 env 第一个 done 时刻”的统计值（偏终态/终止时刻）。
- `cre_logging.build_episode_log()`：`success_flag = any(step.done_type == "success")`，并在 `_resolve_done_type()` 中也会检查“轨迹任一步 `goal_distance < 0.5`”，属于全轨迹判定。

签名片段：
```python
def summarize_rollout_stats(trajs: Any, *, prefix: str) -> Dict[str, float]:
def _take_first_episode(tensor: torch.Tensor, done: torch.Tensor) -> torch.Tensor:

def _resolve_done_type(self, requested_done_type: Optional[str]) -> str:
def build_episode_log(self, done_type: Optional[str] = None) -> Dict[str, Any]:
```

---

## 结论（简版）
- 主策略是 TensorDict 风格 PPO（可训练、可梯度）。
- rollout 主体是 `TensorDict`，训练批与评估轨迹统一格式。
- 环境不是 gym.Env，而是 TorchRL EnvBase 链路；支持 `set_seed`。
- success_rate 同时存在“终止时刻统计”与“全轨迹 episode 聚合”两套口径；`task_completion` 命名函数不存在。
