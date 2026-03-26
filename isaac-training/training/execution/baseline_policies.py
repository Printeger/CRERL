"""Hand-crafted baseline policies for Phase 3 comparison runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

import torch


def _vec_to_new_frame(vec: torch.Tensor, goal_direction: torch.Tensor) -> torch.Tensor:
    if vec.ndim == 1:
        vec = vec.unsqueeze(0)
    if goal_direction.ndim == 1:
        goal_direction = goal_direction.unsqueeze(0)

    goal_direction_x = goal_direction / goal_direction.norm(dim=-1, keepdim=True).clamp_min(1e-6)
    z_direction = torch.tensor([0.0, 0.0, 1.0], device=vec.device, dtype=vec.dtype).expand_as(goal_direction_x)
    goal_direction_y = torch.cross(z_direction, goal_direction_x, dim=-1)
    goal_direction_y = goal_direction_y / goal_direction_y.norm(dim=-1, keepdim=True).clamp_min(1e-6)
    goal_direction_z = torch.cross(goal_direction_x, goal_direction_y, dim=-1)
    goal_direction_z = goal_direction_z / goal_direction_z.norm(dim=-1, keepdim=True).clamp_min(1e-6)

    if vec.ndim == 3:
        n = vec.size(0)
        vec_x_new = torch.bmm(vec.view(n, vec.shape[1], 3), goal_direction_x.view(n, 3, 1))
        vec_y_new = torch.bmm(vec.view(n, vec.shape[1], 3), goal_direction_y.view(n, 3, 1))
        vec_z_new = torch.bmm(vec.view(n, vec.shape[1], 3), goal_direction_z.view(n, 3, 1))
    else:
        n = vec.size(0)
        vec_x_new = torch.bmm(vec.view(n, 1, 3), goal_direction_x.view(n, 3, 1))
        vec_y_new = torch.bmm(vec.view(n, 1, 3), goal_direction_y.view(n, 3, 1))
        vec_z_new = torch.bmm(vec.view(n, 1, 3), goal_direction_z.view(n, 3, 1))

    return torch.cat((vec_x_new, vec_y_new, vec_z_new), dim=-1)


def vec_to_world(vec: torch.Tensor, goal_direction: torch.Tensor) -> torch.Tensor:
    world_dir = torch.tensor([1.0, 0.0, 0.0], device=vec.device, dtype=vec.dtype).expand_as(goal_direction)
    world_frame_new = _vec_to_new_frame(world_dir, goal_direction)
    world_frame_vel = _vec_to_new_frame(vec, world_frame_new)
    return world_frame_vel


def _squeeze_direction(direction: torch.Tensor) -> torch.Tensor:
    if direction.ndim == 3 and direction.shape[1] == 1:
        return direction[:, 0]
    return direction


def _extract_observation(tensordict: Any) -> Dict[str, torch.Tensor]:
    return {
        "state": tensordict["agents", "observation", "state"],
        "direction": _squeeze_direction(tensordict["agents", "observation", "direction"]),
        "lidar": tensordict["agents", "observation", "lidar"],
        "dynamic_obstacle": tensordict["agents", "observation", "dynamic_obstacle"],
    }


@dataclass
class BaselinePolicy:
    """Base interface for hand-crafted high-level velocity policies."""

    action_limit: float = 2.0
    seed: int = 0

    def __post_init__(self) -> None:
        self._generator = torch.Generator(device="cpu")
        self._generator.manual_seed(int(self.seed))

    def reset_seed(self, seed: int) -> None:
        self.seed = int(seed)
        self._generator.manual_seed(self.seed)

    def compute_action(self, observation: Mapping[str, torch.Tensor]) -> torch.Tensor:
        raise NotImplementedError

    @torch.no_grad()
    def __call__(self, tensordict: Any) -> Any:
        observation = _extract_observation(tensordict)
        actions_world = self.compute_action(observation)
        tensordict["agents", "action"] = actions_world
        return tensordict


@dataclass
class RandomPolicy(BaselinePolicy):
    """Uniform random velocity sampler in the goal-aligned control space."""

    random_scale: float = 1.0

    def compute_action(self, observation: Mapping[str, torch.Tensor]) -> torch.Tensor:
        direction = observation["direction"]
        action_shape = direction.shape[:-1] + (3,)
        local_action = torch.rand(action_shape, generator=self._generator, dtype=direction.dtype)
        local_action = (2.0 * local_action - 1.0) * (self.action_limit * self.random_scale)
        local_action = local_action.to(direction.device)
        return vec_to_world(local_action, direction)


@dataclass
class GreedyPolicy(BaselinePolicy):
    """Goal-seeking policy with no explicit obstacle avoidance."""

    forward_speed: float = 1.5
    vertical_gain: float = 0.8

    def compute_action(self, observation: Mapping[str, torch.Tensor]) -> torch.Tensor:
        state = observation["state"]
        direction = observation["direction"]
        distance_2d = state[..., 3]
        distance_z = state[..., 4]

        forward = torch.clamp(distance_2d * 0.25 + self.forward_speed * 0.5, min=0.0, max=self.forward_speed)
        vertical = torch.clamp(distance_z * self.vertical_gain, min=-self.action_limit, max=self.action_limit)
        lateral = torch.zeros_like(forward)

        local_action = torch.stack((forward, lateral, vertical), dim=-1)
        local_action = torch.clamp(local_action, min=-self.action_limit, max=self.action_limit)
        return vec_to_world(local_action, direction)


@dataclass
class ConservativePolicy(BaselinePolicy):
    """Safety-biased potential-field policy with slower forward motion."""

    forward_speed: float = 0.8
    vertical_gain: float = 0.6
    safety_distance: float = 1.5
    stop_distance: float = 0.6
    lateral_gain: float = 1.2
    dynamic_avoidance_gain: float = 0.8

    def compute_action(self, observation: Mapping[str, torch.Tensor]) -> torch.Tensor:
        state = observation["state"]
        direction = observation["direction"]
        lidar = observation["lidar"]
        dynamic_obstacle = observation["dynamic_obstacle"]

        distance_z = state[..., 4]
        lidar_range = 40.0

        # Recover approximate clearance from the stored "range - hit_distance" representation.
        static_clearance = torch.clamp(lidar_range - lidar, min=0.0, max=lidar_range)
        min_clearance = static_clearance.amin(dim=(-1, -2, -3))
        proximity_per_beam = lidar.squeeze(1).amax(dim=-1)
        half = proximity_per_beam.shape[-1] // 2
        left_proximity = proximity_per_beam[..., :half].mean(dim=-1)
        right_proximity = proximity_per_beam[..., half:].mean(dim=-1)

        clearance_scale = torch.clamp(
            (min_clearance - self.stop_distance)
            / max(self.safety_distance - self.stop_distance, 1e-6),
            min=0.0,
            max=1.0,
        )
        forward = self.forward_speed * clearance_scale
        lateral = torch.tanh((right_proximity - left_proximity) / max(lidar_range, 1.0)) * self.lateral_gain
        vertical = torch.clamp(distance_z * self.vertical_gain, min=-self.action_limit, max=self.action_limit)

        if dynamic_obstacle.numel() > 0:
            dyn = dynamic_obstacle.squeeze(1)
            dyn_rpos = dyn[..., :3]
            dyn_distance_2d = dyn[..., 3].clamp_min(1e-3)
            active = dyn_distance_2d < (self.safety_distance * 2.0)
            ahead = torch.clamp(dyn_rpos[..., 0], min=0.0)
            lateral = lateral + (
                (-dyn_rpos[..., 1] / dyn_distance_2d.square()) * active
            ).sum(dim=-1) * self.dynamic_avoidance_gain
            vertical = vertical + (
                (-dyn_rpos[..., 2] / dyn_distance_2d.square()) * active
            ).sum(dim=-1) * (0.5 * self.dynamic_avoidance_gain)
            forward = forward - (
                (ahead / dyn_distance_2d.square()) * active
            ).sum(dim=-1) * (0.35 * self.dynamic_avoidance_gain)

        local_action = torch.stack((forward, lateral, vertical), dim=-1)
        local_action = torch.clamp(local_action, min=-self.action_limit, max=self.action_limit)
        return vec_to_world(local_action, direction)


def build_baseline_policy(
    name: str,
    *,
    action_limit: float,
    seed: int,
    policy_cfg: Optional[Mapping[str, Any]] = None,
) -> BaselinePolicy:
    cfg = dict(policy_cfg or {})
    normalized = str(name).strip().lower()
    if normalized == "random":
        return RandomPolicy(
            action_limit=action_limit,
            seed=seed,
            random_scale=float(cfg.get("random_scale", 1.0)),
        )
    if normalized == "greedy":
        return GreedyPolicy(
            action_limit=action_limit,
            seed=seed,
            forward_speed=float(cfg.get("greedy_forward_speed", 1.5)),
            vertical_gain=float(cfg.get("greedy_vertical_gain", 0.8)),
        )
    if normalized == "conservative":
        return ConservativePolicy(
            action_limit=action_limit,
            seed=seed,
            forward_speed=float(cfg.get("conservative_forward_speed", 0.8)),
            vertical_gain=float(cfg.get("conservative_vertical_gain", 0.6)),
            safety_distance=float(cfg.get("safety_distance", 1.5)),
            stop_distance=float(cfg.get("stop_distance", 0.6)),
            lateral_gain=float(cfg.get("lateral_gain", 1.2)),
            dynamic_avoidance_gain=float(cfg.get("dynamic_avoidance_gain", 0.8)),
        )
    raise ValueError(f"Unsupported baseline policy: {name}")


__all__ = [
    "BaselinePolicy",
    "RandomPolicy",
    "GreedyPolicy",
    "ConservativePolicy",
    "build_baseline_policy",
    "vec_to_world",
]
