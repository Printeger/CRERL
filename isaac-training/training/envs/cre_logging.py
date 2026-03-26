"""
CRE runtime logging utilities for flight tests and environment analysis.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


def _default_logs_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "logs"


def _safe_float(value: Optional[Any], default: Optional[float] = None) -> Optional[float]:
    if value is None:
        return default
    return float(value)


def _sum_reward_components(steps: Sequence["StepLog"]) -> Dict[str, float]:
    totals: Dict[str, float] = {}
    for step in steps:
        for key, value in step.reward_components.items():
            totals[key] = totals.get(key, 0.0) + float(value)
    return totals


def _jsonl_load(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def aggregate_episode_records(records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    if not records:
        return {
            "episode_count": 0,
            "success_rate": 0.0,
            "collision_rate": 0.0,
            "out_of_bounds_rate": 0.0,
            "min_distance": None,
            "average_return": 0.0,
            "near_violation_ratio": 0.0,
            "done_type_counts": {},
        }

    episode_count = len(records)
    success_count = sum(bool(record.get("success_flag")) for record in records)
    collision_count = sum(bool(record.get("collision_flag")) for record in records)
    out_of_bounds_count = sum(bool(record.get("out_of_bounds_flag")) for record in records)
    min_distances = [
        float(record["min_obstacle_distance"])
        for record in records
        if record.get("min_obstacle_distance") is not None
    ]
    returns = [float(record.get("return_total", 0.0)) for record in records]
    near_violation_steps = sum(int(record.get("near_violation_steps", 0)) for record in records)
    total_steps = sum(max(0, int(record.get("num_steps", 0))) for record in records)

    done_type_counts: Dict[str, int] = {}
    for record in records:
        done_type = str(record.get("done_type", "unknown"))
        done_type_counts[done_type] = done_type_counts.get(done_type, 0) + 1

    return {
        "episode_count": episode_count,
        "success_rate": success_count / episode_count,
        "collision_rate": collision_count / episode_count,
        "out_of_bounds_rate": out_of_bounds_count / episode_count,
        "min_distance": min(min_distances) if min_distances else None,
        "average_return": sum(returns) / episode_count,
        "near_violation_ratio": (near_violation_steps / total_steps) if total_steps else 0.0,
        "done_type_counts": done_type_counts,
    }


def aggregate_log_directory(run_dir: str | Path) -> Dict[str, Any]:
    run_path = Path(run_dir)
    episode_records = _jsonl_load(run_path / "episodes.jsonl")
    summary = aggregate_episode_records(episode_records)
    summary["run_dir"] = str(run_path)
    return summary


@dataclass
class StepLog:
    """Per-step runtime metrics collected during a flight episode."""

    episode_index: int
    step_idx: int
    sim_time: float
    scene_id: str
    scenario_type: str
    position: Tuple[float, float, float]
    velocity: Tuple[float, float, float]
    yaw_rate: float
    goal_distance: Optional[float]
    reward_total: float
    reward_components: Dict[str, float]
    collision_flag: bool
    min_obstacle_distance: Optional[float]
    near_violation_flag: bool
    out_of_bounds_flag: bool
    done_type: str
    target_position: Optional[Tuple[float, float, float]] = None
    scene_tags: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EpisodeLog:
    """Episode-level CRE summary."""

    episode_index: int
    seed: Optional[int]
    scene_id: str
    scenario_type: str
    num_steps: int
    trajectory_length: float
    return_total: float
    reward_components_total: Dict[str, float]
    success_flag: bool
    collision_flag: bool
    out_of_bounds_flag: bool
    min_obstacle_distance: Optional[float]
    near_violation_steps: int
    near_violation_ratio: float
    final_goal_distance: Optional[float]
    done_type: str
    scene_tags: Dict[str, Any] = field(default_factory=dict)


class FlightEpisodeLogger:
    """Collects step logs, writes episode artifacts, and maintains run-level summaries."""

    def __init__(
        self,
        *,
        run_name: str = "cre_run",
        base_dir: Optional[str | Path] = None,
        near_violation_distance: float = 0.5,
        use_timestamp: bool = True,
    ):
        self.base_dir = Path(base_dir) if base_dir is not None else _default_logs_dir()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_id = f"{run_name}_{timestamp}" if use_timestamp else run_name
        self.run_dir = self.base_dir / self.run_id
        self.episodes_dir = self.run_dir / "episodes"
        self.episodes_dir.mkdir(parents=True, exist_ok=True)
        self.steps_jsonl_path = self.run_dir / "steps.jsonl"
        self.episodes_jsonl_path = self.run_dir / "episodes.jsonl"
        self.summary_path = self.run_dir / "summary.json"
        self.manifest_path = self.run_dir / "manifest.json"
        self.near_violation_distance = float(near_violation_distance)
        self.completed_episodes: List[Dict[str, Any]] = []
        self._finalized = False
        self._last_episode_summary: Optional[Dict[str, Any]] = None
        self._write_manifest()
        self.reset()

    def _write_manifest(self) -> None:
        manifest = {
            "run_id": self.run_id,
            "base_dir": str(self.base_dir),
            "run_dir": str(self.run_dir),
            "near_violation_distance": self.near_violation_distance,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def reset(
        self,
        *,
        episode_index: int = 0,
        seed: Optional[int] = None,
        scene_id: Optional[str] = None,
        scenario_type: Optional[str] = None,
        scene_tags: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.episode_index = episode_index
        self.seed = seed
        self.scene_id = scene_id or ""
        self.scenario_type = scenario_type or ""
        self.scene_tags = dict(scene_tags or {})
        if not self.scene_id:
            self.scene_id = str(self.scene_tags.get("scene_id", ""))
        if not self.scenario_type:
            self.scenario_type = str(self.scene_tags.get("family", ""))
        self.steps: List[StepLog] = []
        self._trajectory_length = 0.0
        self._last_position: Optional[Tuple[float, float, float]] = None
        self._finalized = False
        self._last_episode_summary = None

    def has_steps(self) -> bool:
        return bool(self.steps)

    def log_step(
        self,
        *,
        step_idx: int,
        sim_time: float,
        position: Sequence[float],
        velocity: Sequence[float],
        yaw_rate: float = 0.0,
        goal_distance: Optional[float] = None,
        reward_total: Optional[float] = 0.0,
        reward_components: Optional[Dict[str, Any]] = None,
        collision_flag: bool = False,
        min_obstacle_distance: Optional[float] = None,
        near_violation_flag: Optional[bool] = None,
        out_of_bounds_flag: bool = False,
        done_type: str = "running",
        scene_id: Optional[str] = None,
        scenario_type: Optional[str] = None,
        target_position: Optional[Sequence[float]] = None,
        scene_tags: Optional[Dict[str, Any]] = None,
        reached_goal: Optional[bool] = None,
        collision_proxy: Optional[bool] = None,
    ) -> None:
        pos = tuple(float(v) for v in position[:3])
        vel = tuple(float(v) for v in velocity[:3])
        target = None if target_position is None else tuple(float(v) for v in target_position[:3])
        reward_component_dict = {
            str(key): float(value)
            for key, value in (reward_components or {}).items()
        }
        if self._last_position is not None:
            self._trajectory_length += math.dist(self._last_position, pos)
        self._last_position = pos

        scene_id_value = scene_id or self.scene_id or str(self.scene_tags.get("scene_id", ""))
        scenario_value = scenario_type or self.scenario_type or str(self.scene_tags.get("family", ""))
        merged_tags = dict(self.scene_tags)
        if scene_tags:
            merged_tags.update(scene_tags)
        if near_violation_flag is None:
            near_violation_flag = (
                min_obstacle_distance is not None and
                float(min_obstacle_distance) < self.near_violation_distance
            )
        if reached_goal:
            done_type = "success" if done_type == "running" else done_type
        collision_flag = bool(collision_flag or collision_proxy)

        self.steps.append(
            StepLog(
                episode_index=self.episode_index,
                step_idx=int(step_idx),
                sim_time=float(sim_time),
                scene_id=str(scene_id_value),
                scenario_type=str(scenario_value),
                position=pos,
                velocity=vel,
                yaw_rate=float(yaw_rate),
                goal_distance=_safe_float(goal_distance),
                reward_total=float(reward_total or 0.0),
                reward_components=reward_component_dict,
                collision_flag=collision_flag,
                min_obstacle_distance=_safe_float(min_obstacle_distance),
                near_violation_flag=bool(near_violation_flag),
                out_of_bounds_flag=bool(out_of_bounds_flag),
                done_type=str(done_type),
                target_position=target,
                scene_tags=merged_tags,
            )
        )

    def _resolve_done_type(self, requested_done_type: Optional[str]) -> str:
        alias_map = {
            None: "unknown",
            "regen": "manual_regen",
            "final": "manual_exit",
            "exit": "manual_exit",
        }
        normalized = alias_map.get(requested_done_type, requested_done_type or "unknown")
        collision_flag = any(step.collision_flag for step in self.steps)
        out_of_bounds_flag = any(step.out_of_bounds_flag for step in self.steps)
        success_flag = any(
            step.done_type == "success" or
            (step.goal_distance is not None and step.goal_distance < 0.5)
            for step in self.steps
        )
        if collision_flag:
            return "collision"
        if out_of_bounds_flag:
            return "out_of_bounds"
        if success_flag:
            return "success"
        return str(normalized)

    def build_episode_log(self, done_type: Optional[str] = None) -> Dict[str, Any]:
        if not self.steps:
            return {}

        resolved_done_type = self._resolve_done_type(done_type)
        last_step = self.steps[-1]
        if last_step.done_type == "running" or done_type is not None:
            last_step.done_type = resolved_done_type

        goal_distances = [step.goal_distance for step in self.steps if step.goal_distance is not None]
        min_distances = [
            step.min_obstacle_distance
            for step in self.steps
            if step.min_obstacle_distance is not None
        ]
        near_violation_steps = sum(int(step.near_violation_flag) for step in self.steps)
        collision_flag = any(step.collision_flag for step in self.steps)
        out_of_bounds_flag = any(step.out_of_bounds_flag for step in self.steps)
        success_flag = any(step.done_type == "success" for step in self.steps)
        episode_log = EpisodeLog(
            episode_index=self.episode_index,
            seed=self.seed,
            scene_id=last_step.scene_id or self.scene_id,
            scenario_type=last_step.scenario_type or self.scenario_type,
            num_steps=len(self.steps),
            trajectory_length=self._trajectory_length,
            return_total=sum(step.reward_total for step in self.steps),
            reward_components_total=_sum_reward_components(self.steps),
            success_flag=success_flag,
            collision_flag=collision_flag,
            out_of_bounds_flag=out_of_bounds_flag,
            min_obstacle_distance=min(min_distances) if min_distances else None,
            near_violation_steps=near_violation_steps,
            near_violation_ratio=near_violation_steps / len(self.steps) if self.steps else 0.0,
            final_goal_distance=goal_distances[-1] if goal_distances else None,
            done_type=resolved_done_type,
            scene_tags=dict(self.scene_tags),
        )
        return asdict(episode_log)

    def summary(self) -> Dict[str, Any]:
        return self.build_episode_log()

    def _append_jsonl(self, path: Path, payloads: Iterable[Dict[str, Any]]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            for payload in payloads:
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def export_json(self, path: str, done_type: Optional[str] = None) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "summary": self.build_episode_log(done_type=done_type),
            "steps": [asdict(step) for step in self.steps],
        }
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def finalize_episode(self, done_type: Optional[str] = None) -> Dict[str, Any]:
        if not self.steps:
            return {}
        if self._finalized and self._last_episode_summary is not None:
            return dict(self._last_episode_summary)

        episode_summary = self.build_episode_log(done_type=done_type)
        episode_path = self.episodes_dir / f"episode_{self.episode_index:04d}.json"
        episode_payload = {
            "summary": episode_summary,
            "steps": [asdict(step) for step in self.steps],
        }
        episode_path.write_text(json.dumps(episode_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        self._append_jsonl(self.steps_jsonl_path, [asdict(step) for step in self.steps])
        self._append_jsonl(self.episodes_jsonl_path, [episode_summary])
        self.completed_episodes.append(episode_summary)
        self._write_run_summary()
        self._finalized = True
        self._last_episode_summary = dict(episode_summary)
        return episode_summary

    def _write_run_summary(self) -> None:
        summary = aggregate_episode_records(self.completed_episodes)
        summary["run_id"] = self.run_id
        summary["run_dir"] = str(self.run_dir)
        summary["near_violation_distance"] = self.near_violation_distance
        self.summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

