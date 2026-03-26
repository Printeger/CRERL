"""Adapters for routing training and evaluation rollouts into CRE logs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Sequence

import torch

from envs.cre_logging import FlightEpisodeLogger, StepLog, normalize_reward_components


DONE_TYPE_CODE_MAP = {
    0: "running",
    1: "success",
    2: "collision",
    3: "out_of_bounds",
    4: "truncated",
}


def done_type_code_to_string(
    value: Any,
    *,
    collision_flag: bool = False,
    out_of_bounds_flag: bool = False,
    success_flag: bool = False,
    truncated_flag: bool = False,
    done_type_labels: Optional[Mapping[Any, Any]] = None,
) -> str:
    if collision_flag:
        return "collision"
    if out_of_bounds_flag:
        return "out_of_bounds"
    if success_flag:
        return "success"
    if truncated_flag:
        return "truncated"

    if value is None:
        return "running"

    if isinstance(value, torch.Tensor):
        if value.numel() == 0:
            return "running"
        value = float(value.detach().cpu().reshape(-1)[0].item())
    elif isinstance(value, (list, tuple)):
        value = float(value[0]) if value else 0.0
    else:
        value = float(value)

    labels = dict(done_type_labels or DONE_TYPE_CODE_MAP)
    return str(labels.get(int(round(value)), "unknown"))


def _as_tensor(value: Any) -> Optional[torch.Tensor]:
    if value is None:
        return None
    if isinstance(value, torch.Tensor):
        return value.detach().cpu()
    return torch.as_tensor(value)


def _get_nested(container: Any, *keys: str) -> Any:
    current = container
    for key in keys:
        if current is None:
            return None
        try:
            if hasattr(current, "keys") and key in current.keys():
                current = current[key]
            else:
                current = current.get(key)
        except Exception:
            return None
    return current


def extract_cre_env_metadata(
    env: Any,
    *,
    fallback_scenario_type: str,
    fallback_scene_cfg_name: str,
    fallback_scene_id_prefix: Optional[str] = None,
) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {}
    runtime_env = env
    for attr_name in ("base_env", "env"):
        if hasattr(runtime_env, attr_name):
            try:
                candidate = getattr(runtime_env, attr_name)
            except Exception:
                candidate = None
            if candidate is not None:
                runtime_env = candidate
                break

    if hasattr(runtime_env, "get_cre_runtime_metadata"):
        try:
            extracted = runtime_env.get_cre_runtime_metadata()
        except Exception:
            extracted = None
        if isinstance(extracted, Mapping):
            metadata.update(extracted)

    scenario_type = str(metadata.get("scenario_type") or fallback_scenario_type)
    scene_cfg_name = str(metadata.get("scene_cfg_name") or fallback_scene_cfg_name)
    scene_id_prefix = str(
        metadata.get("scene_id_prefix")
        or metadata.get("scene_id")
        or fallback_scene_id_prefix
        or f"{scenario_type}_scene"
    )
    done_type_labels = metadata.get("done_type_labels")
    if not isinstance(done_type_labels, Mapping):
        done_type_labels = dict(DONE_TYPE_CODE_MAP)

    return {
        "scenario_type": scenario_type,
        "scene_cfg_name": scene_cfg_name,
        "scene_id_prefix": scene_id_prefix,
        "done_type_labels": dict(done_type_labels),
    }


def _infer_batch_shape(tensor: Optional[torch.Tensor], num_envs: int) -> tuple[int, int]:
    if tensor is None:
        return 1, num_envs
    if tensor.ndim == 0:
        return 1, 1
    if tensor.ndim == 1:
        if tensor.shape[0] == num_envs:
            return 1, num_envs
        if num_envs > 0 and tensor.shape[0] % num_envs == 0:
            return tensor.shape[0] // num_envs, num_envs
        return 1, tensor.shape[0]
    if tensor.shape[0] == num_envs and (tensor.ndim == 2 or tensor.shape[1] != num_envs):
        return 1, num_envs
    if tensor.ndim >= 2:
        return int(tensor.shape[0]), int(tensor.shape[1])
    return 1, num_envs


def _ensure_time_env(tensor: Any, num_envs: int, batch_shape: Optional[tuple[int, int]] = None) -> Optional[torch.Tensor]:
    tensor = _as_tensor(tensor)
    if tensor is None:
        return None

    if batch_shape is None:
        batch_shape = _infer_batch_shape(tensor, num_envs)
    time_dim, env_dim = batch_shape

    if tensor.ndim == 0:
        return tensor.reshape(1, 1)
    if tensor.ndim == 1:
        if tensor.shape[0] == env_dim:
            return tensor.reshape(1, env_dim)
        if env_dim > 0 and tensor.shape[0] == time_dim * env_dim:
            return tensor.reshape(time_dim, env_dim)
        return tensor.reshape(1, tensor.shape[0])
    if tensor.ndim >= 2:
        if tensor.shape[0] == env_dim and (tensor.ndim == 2 or tensor.shape[1] != env_dim):
            return tensor.unsqueeze(0)
        if tensor.shape[0] == time_dim and tensor.shape[1] == env_dim:
            return tensor
        if env_dim > 0 and tensor.shape[0] == time_dim * env_dim:
            return tensor.reshape(time_dim, env_dim, *tensor.shape[1:])
    return tensor


def _scalar(value: Any, default: float = 0.0) -> float:
    tensor = _as_tensor(value)
    if tensor is None or tensor.numel() == 0:
        return float(default)
    return float(tensor.reshape(-1)[0].item())


def _bool_scalar(value: Any, default: bool = False) -> bool:
    tensor = _as_tensor(value)
    if tensor is None or tensor.numel() == 0:
        return bool(default)
    return bool(tensor.reshape(-1)[0].item())


def _select_drone_state(value: Any) -> torch.Tensor:
    tensor = _as_tensor(value)
    if tensor is None:
        return torch.zeros(13)
    while tensor.ndim > 1:
        tensor = tensor[0]
    if tensor.numel() < 13:
        padded = torch.zeros(13, dtype=tensor.dtype)
        padded[: tensor.numel()] = tensor
        return padded
    return tensor[:13]


@dataclass
class TrainingLogRecord:
    """Normalized step record extracted from a training/eval rollout."""

    env_index: int
    episode_index: int
    step_index: int
    sim_time: float
    scene_id: str
    scenario_type: str
    scene_cfg_name: Optional[str]
    position: Sequence[float]
    velocity: Sequence[float]
    yaw_rate: float
    goal_distance: Optional[float]
    reward_total: float
    reward_components: Dict[str, float]
    collision_flag: bool
    min_obstacle_distance: Optional[float]
    near_violation_flag: bool
    out_of_bounds_flag: bool
    done_type: str


@dataclass
class _EpisodeBuffer:
    episode_index: int
    step_index: int = 0
    sim_time: float = 0.0
    steps: list[StepLog] = field(default_factory=list)


class TrainingRolloutLogger:
    """Stateful adapter from batched rollout tensors to CRE log artifacts."""

    def __init__(
        self,
        run_logger: FlightEpisodeLogger,
        *,
        num_envs: int,
        dt: float,
        source: str,
        scenario_type: str,
        scene_cfg_name: Optional[str] = None,
        scene_id_prefix: Optional[str] = None,
        done_type_labels: Optional[Mapping[Any, Any]] = None,
        seed: Optional[int] = None,
    ) -> None:
        self.run_logger = run_logger
        self.num_envs = int(num_envs)
        self.dt = float(dt)
        self.source = str(source)
        self.scenario_type = str(scenario_type)
        self.scene_cfg_name = scene_cfg_name
        self.scene_id_prefix = (
            str(scene_id_prefix)
            if scene_id_prefix is not None
            else f"{self.scenario_type}_scene"
        )
        self.done_type_labels = dict(done_type_labels or DONE_TYPE_CODE_MAP)
        self.seed = seed
        self._next_episode_index = 0
        self._buffers = [self._new_buffer() for _ in range(self.num_envs)]

    def _new_buffer(self) -> _EpisodeBuffer:
        buffer = _EpisodeBuffer(episode_index=self._next_episode_index)
        self._next_episode_index += 1
        return buffer

    def _build_scene_id(self, env_index: int, episode_index: int) -> str:
        return f"{self.scene_id_prefix}_env_{env_index:03d}_episode_{episode_index:05d}"

    def process_tensordict_batch(
        self,
        data: Mapping[str, Any],
        *,
        scenario_type: Optional[str] = None,
        scene_cfg_name: Optional[str] = None,
    ) -> list[TrainingLogRecord]:
        next_td = _get_nested(data, "next")
        if next_td is None:
            next_td = data
        info = _get_nested(next_td, "info")
        if info is None:
            info = {}
        done = _get_nested(next_td, "done")
        truncated = _get_nested(next_td, "truncated")

        batch_anchor = _as_tensor(_get_nested(info, "reward_total"))
        if batch_anchor is None:
            batch_anchor = _as_tensor(done)
        batch_shape = _infer_batch_shape(batch_anchor, self.num_envs)

        drone_state = _ensure_time_env(_get_nested(info, "drone_state"), self.num_envs, batch_shape)
        goal_distance = _ensure_time_env(_get_nested(info, "goal_distance"), self.num_envs, batch_shape)
        min_distance = _ensure_time_env(_get_nested(info, "min_obstacle_distance"), self.num_envs, batch_shape)
        near_violation = _ensure_time_env(_get_nested(info, "near_violation_flag"), self.num_envs, batch_shape)
        out_of_bounds = _ensure_time_env(_get_nested(info, "out_of_bounds_flag"), self.num_envs, batch_shape)
        collision = _ensure_time_env(_get_nested(info, "collision_flag"), self.num_envs, batch_shape)
        yaw_rate = _ensure_time_env(_get_nested(info, "yaw_rate"), self.num_envs, batch_shape)
        reward_total = _ensure_time_env(_get_nested(info, "reward_total"), self.num_envs, batch_shape)
        reward_progress = _ensure_time_env(_get_nested(info, "reward_progress"), self.num_envs, batch_shape)
        reward_safety_static = _ensure_time_env(_get_nested(info, "reward_safety_static"), self.num_envs, batch_shape)
        reward_safety_dynamic = _ensure_time_env(_get_nested(info, "reward_safety_dynamic"), self.num_envs, batch_shape)
        penalty_smooth = _ensure_time_env(_get_nested(info, "penalty_smooth"), self.num_envs, batch_shape)
        penalty_height = _ensure_time_env(_get_nested(info, "penalty_height"), self.num_envs, batch_shape)
        done_type_code = _ensure_time_env(_get_nested(info, "done_type"), self.num_envs, batch_shape)
        done = _ensure_time_env(done, self.num_envs, batch_shape)
        truncated = _ensure_time_env(truncated, self.num_envs, batch_shape)

        time_dim, env_dim = batch_shape
        records: list[TrainingLogRecord] = []
        effective_scenario_type = str(scenario_type or self.scenario_type)
        effective_scene_cfg_name = scene_cfg_name or self.scene_cfg_name

        for time_index in range(time_dim):
            for env_index in range(min(env_dim, self.num_envs)):
                buffer = self._buffers[env_index]
                state = _select_drone_state(
                    None if drone_state is None else drone_state[time_index, env_index]
                )
                position = tuple(float(v) for v in state[:3])
                velocity = tuple(float(v) for v in state[7:10])
                goal_distance_value = None if goal_distance is None else _scalar(goal_distance[time_index, env_index], default=0.0)
                collision_flag = False if collision is None else _bool_scalar(collision[time_index, env_index])
                out_of_bounds_flag = False if out_of_bounds is None else _bool_scalar(out_of_bounds[time_index, env_index])
                success_flag = goal_distance_value is not None and goal_distance_value < 0.5
                truncated_flag = False if truncated is None else _bool_scalar(truncated[time_index, env_index])
                done_type = done_type_code_to_string(
                    None if done_type_code is None else done_type_code[time_index, env_index],
                    collision_flag=collision_flag,
                    out_of_bounds_flag=out_of_bounds_flag,
                    success_flag=success_flag,
                    truncated_flag=truncated_flag,
                    done_type_labels=self.done_type_labels,
                )
                scene_id = self._build_scene_id(env_index, buffer.episode_index)
                reward_components = normalize_reward_components({
                    "reward_progress": 0.0 if reward_progress is None else _scalar(reward_progress[time_index, env_index]),
                    "reward_safety_static": 0.0 if reward_safety_static is None else _scalar(reward_safety_static[time_index, env_index]),
                    "reward_safety_dynamic": 0.0 if reward_safety_dynamic is None else _scalar(reward_safety_dynamic[time_index, env_index]),
                    "penalty_smooth": 0.0 if penalty_smooth is None else _scalar(penalty_smooth[time_index, env_index]),
                    "penalty_height": 0.0 if penalty_height is None else _scalar(penalty_height[time_index, env_index]),
                })
                step_log = StepLog(
                    episode_index=buffer.episode_index,
                    step_idx=buffer.step_index,
                    sim_time=buffer.sim_time,
                    scene_id=scene_id,
                    scenario_type=effective_scenario_type,
                    position=position,
                    velocity=velocity,
                    yaw_rate=0.0 if yaw_rate is None else _scalar(yaw_rate[time_index, env_index]),
                    goal_distance=goal_distance_value,
                    reward_total=0.0 if reward_total is None else _scalar(reward_total[time_index, env_index]),
                    reward_components=reward_components,
                    collision_flag=collision_flag,
                    min_obstacle_distance=None if min_distance is None else _scalar(min_distance[time_index, env_index]),
                    near_violation_flag=False if near_violation is None else _bool_scalar(near_violation[time_index, env_index]),
                    out_of_bounds_flag=out_of_bounds_flag,
                    done_type=done_type,
                    source=self.source,
                    scene_cfg_name=effective_scene_cfg_name,
                    target_position=None,
                    scene_tags={
                        "env_index": env_index,
                        "source": self.source,
                        "scene_cfg_name": effective_scene_cfg_name,
                    },
                )
                buffer.steps.append(step_log)
                buffer.step_index += 1
                buffer.sim_time += self.dt

                records.append(
                    TrainingLogRecord(
                        env_index=env_index,
                        episode_index=buffer.episode_index,
                        step_index=step_log.step_idx,
                        sim_time=step_log.sim_time,
                        scene_id=scene_id,
                        scenario_type=effective_scenario_type,
                        scene_cfg_name=effective_scene_cfg_name,
                        position=position,
                        velocity=velocity,
                        yaw_rate=step_log.yaw_rate,
                        goal_distance=step_log.goal_distance,
                        reward_total=step_log.reward_total,
                        reward_components=dict(step_log.reward_components),
                        collision_flag=step_log.collision_flag,
                        min_obstacle_distance=step_log.min_obstacle_distance,
                        near_violation_flag=step_log.near_violation_flag,
                        out_of_bounds_flag=step_log.out_of_bounds_flag,
                        done_type=done_type,
                    )
                )

                done_flag = False if done is None else _bool_scalar(done[time_index, env_index])
                if done_flag or done_type != "running":
                    self.run_logger.write_episode(
                        episode_index=buffer.episode_index,
                        steps=buffer.steps,
                        seed=self.seed,
                        scene_id=scene_id,
                        scenario_type=effective_scenario_type,
                        scene_cfg_name=effective_scene_cfg_name,
                        scene_tags=dict(step_log.scene_tags),
                        done_type=done_type,
                    )
                    self._buffers[env_index] = self._new_buffer()

        return records

    def process_batch(self, data: Mapping[str, Any], **kwargs: Any) -> list[TrainingLogRecord]:
        return self.process_tensordict_batch(data, **kwargs)

    def flush_open_episodes(self, done_type: str = "manual_exit") -> None:
        for env_index, buffer in enumerate(self._buffers):
            if not buffer.steps:
                continue
            scene_id = self._build_scene_id(env_index, buffer.episode_index)
            self.run_logger.write_episode(
                episode_index=buffer.episode_index,
                steps=buffer.steps,
                seed=self.seed,
                scene_id=scene_id,
                scenario_type=self.scenario_type,
                scene_cfg_name=self.scene_cfg_name,
                scene_tags={
                    "env_index": env_index,
                    "source": self.source,
                    "scene_cfg_name": self.scene_cfg_name,
                },
                done_type=done_type,
            )
            self._buffers[env_index] = self._new_buffer()


__all__ = [
    "DONE_TYPE_CODE_MAP",
    "TrainingLogRecord",
    "TrainingRolloutLogger",
    "done_type_code_to_string",
    "extract_cre_env_metadata",
]
