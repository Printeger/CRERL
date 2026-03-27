"""Baseline rollout orchestration for Phase 3 comparison runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence

import torch

from execution.baseline_policies import BaselinePolicy, build_baseline_policy
from runtime_logging.logger import (
    aggregate_log_directory,
    create_run_logger,
    run_acceptance_check,
)
from runtime_logging.training_log_adapter import (
    TrainingRolloutLogger,
    build_cre_run_metadata,
    build_cre_scene_tags_template,
    extract_cre_env_metadata,
)


@dataclass
class BaselineRunResult:
    baseline_name: str
    run_dir: str
    seeds: List[int]
    rollout_metrics: List[Dict[str, float]]
    summary: Dict[str, Any]
    acceptance: Dict[str, Any]


def resolve_baseline_seeds(
    *,
    base_seed: int,
    num_episodes: int,
    explicit_seeds: Optional[Sequence[int]] = None,
) -> List[int]:
    if explicit_seeds:
        return [int(seed) for seed in explicit_seeds]
    return [int(base_seed) + idx for idx in range(int(num_episodes))]


def _take_first_episode(tensor: torch.Tensor, done: torch.Tensor) -> torch.Tensor:
    first_done = torch.argmax(done.long(), dim=1).cpu()
    indices = first_done.reshape(first_done.shape + (1,) * (tensor.ndim - 2))
    return torch.take_along_dim(tensor.cpu(), indices, dim=1).reshape(-1)


def summarize_rollout_stats(trajs: Any, *, prefix: str) -> Dict[str, float]:
    done = trajs.get(("next", "done"))
    stats = trajs[("next", "stats")]
    info: Dict[str, float] = {}
    for key, value in stats.cpu().items():
        scalar = torch.mean(_take_first_episode(value, done).float()).item()
        info[f"{prefix}/{key}"] = scalar
    return info


@torch.no_grad()
def run_baseline_rollouts(
    *,
    env: Any,
    cfg: Any,
    baseline_name: str,
    policy_cfg: Optional[Mapping[str, Any]] = None,
    explicit_seeds: Optional[Sequence[int]] = None,
) -> BaselineRunResult:
    cre_env_metadata = extract_cre_env_metadata(
        env,
        fallback_scenario_type="legacy_navigation_env",
        fallback_scene_cfg_name="legacy_baseline_env",
        fallback_scene_id_prefix="legacy_baseline_scene",
    )
    seeds = resolve_baseline_seeds(
        base_seed=int(cfg.seed),
        num_episodes=int(cfg.baseline.num_episodes),
        explicit_seeds=explicit_seeds,
    )

    policy: BaselinePolicy = build_baseline_policy(
        baseline_name,
        action_limit=float(cfg.algo.actor.action_limit),
        seed=int(seeds[0]),
        policy_cfg=policy_cfg,
    )
    source = f"baseline_{baseline_name}"
    cre_run_metadata = build_cre_run_metadata(
        cre_env_metadata,
        source=source,
        execution_mode="baseline",
    )
    cre_scene_tags = build_cre_scene_tags_template(
        cre_env_metadata,
        source=source,
        execution_mode="baseline",
    )
    run_logger = create_run_logger(
        source=source,
        run_name=f"baseline_{baseline_name}_rollout",
        near_violation_distance=0.5,
        run_metadata=cre_run_metadata,
    )
    log_adapter = TrainingRolloutLogger(
        run_logger,
        num_envs=int(cfg.env.num_envs),
        dt=float(cfg.sim.dt) * float(cfg.sim.substeps),
        source=source,
        scenario_type=cre_env_metadata["scenario_type"],
        scene_cfg_name=cre_env_metadata["scene_cfg_name"],
        scene_id_prefix=cre_env_metadata["scene_id_prefix"],
        done_type_labels=cre_env_metadata["done_type_labels"],
        seed=int(cfg.seed),
        scene_tags_template=cre_scene_tags,
    )

    rollout_metrics: List[Dict[str, float]] = []
    env.enable_render(False)
    env.eval()

    for episode_seed in seeds:
        env.set_seed(int(episode_seed))
        policy.reset_seed(int(episode_seed))
        trajs = env.rollout(
            max_steps=int(cfg.env.max_episode_length),
            policy=policy,
            auto_reset=True,
            break_when_any_done=False,
            return_contiguous=False,
        )
        log_adapter.process_batch(trajs)
        log_adapter.flush_open_episodes(done_type="truncated")
        rollout_metrics.append(
            summarize_rollout_stats(
                trajs,
                prefix=f"baseline/{baseline_name}",
            )
        )
        env.reset()

    summary = aggregate_log_directory(run_logger.run_dir)
    acceptance = run_acceptance_check(run_logger.run_dir, write_report=True)
    return BaselineRunResult(
        baseline_name=baseline_name,
        run_dir=str(run_logger.run_dir),
        seeds=seeds,
        rollout_metrics=rollout_metrics,
        summary=summary,
        acceptance=acceptance,
    )


__all__ = [
    "BaselineRunResult",
    "resolve_baseline_seeds",
    "run_baseline_rollouts",
    "summarize_rollout_stats",
]
