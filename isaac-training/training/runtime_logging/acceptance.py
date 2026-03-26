"""Run-level acceptance checks for CRE runtime log directories."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from envs.cre_logging import (
    STANDARD_REWARD_COMPONENT_KEYS,
    aggregate_episode_records,
)


CANONICAL_DONE_TYPES = {
    "running",
    "success",
    "collision",
    "out_of_bounds",
    "truncated",
    "manual_regen",
    "manual_exit",
    "unknown",
}

REQUIRED_STEP_FIELDS = {
    "scene_id",
    "scenario_type",
    "scene_cfg_name",
    "position",
    "velocity",
    "yaw_rate",
    "goal_distance",
    "reward_total",
    "reward_components",
    "collision_flag",
    "min_obstacle_distance",
    "near_violation_flag",
    "out_of_bounds_flag",
    "done_type",
    "source",
}

REQUIRED_EPISODE_FIELDS = {
    "episode_index",
    "seed",
    "scene_id",
    "scenario_type",
    "scene_cfg_name",
    "num_steps",
    "trajectory_length",
    "return_total",
    "reward_components_total",
    "success_flag",
    "collision_flag",
    "out_of_bounds_flag",
    "min_obstacle_distance",
    "near_violation_steps",
    "near_violation_ratio",
    "final_goal_distance",
    "done_type",
    "source",
}

SUMMARY_METRIC_KEYS = {
    "success_rate",
    "collision_rate",
    "min_distance",
    "average_return",
    "near_violation_ratio",
}


def _json_load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl_load(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _float_close(left: Any, right: Any, tol: float = 1e-6) -> bool:
    if left is None or right is None:
        return left is None and right is None
    return abs(float(left) - float(right)) <= tol


def _episode_artifact_paths(run_dir: Path) -> List[Path]:
    episodes_dir = run_dir / "episodes"
    if not episodes_dir.exists():
        return []
    return sorted(episodes_dir.glob("episode_*.json"))


def load_run_summary(run_dir: str | Path) -> Dict[str, Any]:
    run_path = Path(run_dir)
    summary_path = run_path / "summary.json"
    if summary_path.exists():
        return _json_load(summary_path)
    episode_records = _jsonl_load(run_path / "episodes.jsonl")
    summary = aggregate_episode_records(episode_records)
    summary["run_dir"] = str(run_path)
    return summary


def validate_step_schema(step_record: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []

    missing = sorted(REQUIRED_STEP_FIELDS - set(step_record.keys()))
    if missing:
        errors.append(f"missing step fields: {', '.join(missing)}")

    done_type = str(step_record.get("done_type", ""))
    if done_type and done_type not in CANONICAL_DONE_TYPES:
        errors.append(f"invalid step done_type: {done_type}")

    reward_components = step_record.get("reward_components")
    if not isinstance(reward_components, Mapping):
        errors.append("step reward_components must be a mapping")
    else:
        missing_reward_keys = sorted(
            set(STANDARD_REWARD_COMPONENT_KEYS) - set(reward_components.keys())
        )
        if missing_reward_keys:
            errors.append(
                "step reward_components missing standard keys: "
                + ", ".join(missing_reward_keys)
            )

    scene_cfg_name = step_record.get("scene_cfg_name")
    if scene_cfg_name in (None, ""):
        errors.append("step scene_cfg_name is missing")

    source = step_record.get("source")
    if source in (None, ""):
        errors.append("step source is missing")

    return errors


def validate_episode_schema(episode_record: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []

    missing = sorted(REQUIRED_EPISODE_FIELDS - set(episode_record.keys()))
    if missing:
        errors.append(f"missing episode fields: {', '.join(missing)}")

    done_type = str(episode_record.get("done_type", ""))
    if done_type and done_type not in CANONICAL_DONE_TYPES:
        errors.append(f"invalid episode done_type: {done_type}")

    reward_components_total = episode_record.get("reward_components_total")
    if not isinstance(reward_components_total, Mapping):
        errors.append("episode reward_components_total must be a mapping")
    else:
        missing_reward_keys = sorted(
            set(STANDARD_REWARD_COMPONENT_KEYS) - set(reward_components_total.keys())
        )
        if missing_reward_keys:
            errors.append(
                "episode reward_components_total missing standard keys: "
                + ", ".join(missing_reward_keys)
            )

    num_steps = int(episode_record.get("num_steps", 0) or 0)
    near_violation_steps = int(episode_record.get("near_violation_steps", 0) or 0)
    expected_ratio = (near_violation_steps / num_steps) if num_steps > 0 else 0.0
    actual_ratio = float(episode_record.get("near_violation_ratio", 0.0) or 0.0)
    if not _float_close(expected_ratio, actual_ratio):
        errors.append(
            "episode near_violation_ratio does not match near_violation_steps / num_steps"
        )

    scene_cfg_name = episode_record.get("scene_cfg_name")
    if scene_cfg_name in (None, ""):
        errors.append("episode scene_cfg_name is missing")

    source = episode_record.get("source")
    if source in (None, ""):
        errors.append("episode source is missing")

    collision_flag = bool(episode_record.get("collision_flag"))
    out_of_bounds_flag = bool(episode_record.get("out_of_bounds_flag"))
    success_flag = bool(episode_record.get("success_flag"))
    if collision_flag and done_type != "collision":
        errors.append("episode collision_flag is true but done_type is not collision")
    if out_of_bounds_flag and done_type != "out_of_bounds":
        errors.append("episode out_of_bounds_flag is true but done_type is not out_of_bounds")
    if success_flag and done_type != "success":
        errors.append("episode success_flag is true but done_type is not success")

    return errors


def compare_summary_against_episodes(run_dir: str | Path) -> Tuple[List[str], Dict[str, Any]]:
    run_path = Path(run_dir)
    errors: List[str] = []
    summary_path = run_path / "summary.json"
    if not summary_path.exists():
        return ["summary.json is missing"], {}

    summary = _json_load(summary_path)
    episode_records = _jsonl_load(run_path / "episodes.jsonl")
    recomputed = aggregate_episode_records(episode_records)

    for key in ("episode_count", *sorted(SUMMARY_METRIC_KEYS)):
        if key not in summary:
            errors.append(f"summary.json missing key: {key}")
            continue
        if not _float_close(summary.get(key), recomputed.get(key)):
            errors.append(
                f"summary.json mismatch for {key}: "
                f"{summary.get(key)} != {recomputed.get(key)}"
            )

    return errors, recomputed


def _validate_artifact_completeness(run_dir: Path) -> List[str]:
    required_paths = [
        run_dir / "manifest.json",
        run_dir / "steps.jsonl",
        run_dir / "episodes.jsonl",
        run_dir / "summary.json",
        run_dir / "episodes",
    ]
    errors = [f"missing artifact: {path.name}" for path in required_paths if not path.exists()]
    if not _episode_artifact_paths(run_dir):
        errors.append("missing episode artifacts under episodes/")
    return errors


def _validate_cross_file_consistency(
    run_dir: Path,
    steps: Sequence[Dict[str, Any]],
    episodes: Sequence[Dict[str, Any]],
    manifest: Optional[Dict[str, Any]],
    summary: Optional[Dict[str, Any]],
) -> List[str]:
    errors: List[str] = []

    episode_rows = {
        int(record["episode_index"]): record
        for record in episodes
        if "episode_index" in record
    }

    for artifact_path in _episode_artifact_paths(run_dir):
        payload = _json_load(artifact_path)
        artifact_summary = payload.get("summary", {})
        episode_index = artifact_summary.get("episode_index")
        if episode_index not in episode_rows:
            errors.append(
                f"episode artifact {artifact_path.name} has no matching episodes.jsonl row"
            )
            continue
        episode_row = episode_rows[int(episode_index)]
        for key in ("scene_id", "scenario_type", "scene_cfg_name", "done_type", "source"):
            if artifact_summary.get(key) != episode_row.get(key):
                errors.append(
                    f"episode artifact {artifact_path.name} mismatches episodes.jsonl on {key}"
                )

    source_values = set()
    if manifest and manifest.get("source"):
        source_values.add(str(manifest["source"]))
    if summary and summary.get("source"):
        source_values.add(str(summary["source"]))
    source_values.update(str(step.get("source")) for step in steps if step.get("source"))
    source_values.update(str(ep.get("source")) for ep in episodes if ep.get("source"))
    if len(source_values) > 1:
        errors.append(f"run source is inconsistent across artifacts: {sorted(source_values)}")

    steps_by_episode: Dict[int, List[Dict[str, Any]]] = {}
    for step in steps:
        episode_index = int(step.get("episode_index", -1))
        steps_by_episode.setdefault(episode_index, []).append(step)

    for episode_index, episode_record in episode_rows.items():
        expected_scene_cfg = episode_record.get("scene_cfg_name")
        episode_steps = steps_by_episode.get(episode_index, [])
        if not episode_steps:
            errors.append(f"episode {episode_index} has no corresponding step records")
            continue
        step_scene_cfg_values = {
            str(step.get("scene_cfg_name"))
            for step in episode_steps
            if step.get("scene_cfg_name") not in (None, "")
        }
        if not step_scene_cfg_values:
            errors.append(f"episode {episode_index} step records are missing scene_cfg_name")
        elif len(step_scene_cfg_values) > 1:
            errors.append(
                f"episode {episode_index} has inconsistent step-level scene_cfg_name values"
            )
        elif expected_scene_cfg not in step_scene_cfg_values:
            errors.append(
                f"episode {episode_index} scene_cfg_name mismatches between steps and episode summary"
            )

    return errors


def validate_run_directory(run_dir: str | Path) -> Dict[str, Any]:
    run_path = Path(run_dir)
    checks: Dict[str, Dict[str, Any]] = {}
    errors: List[str] = []

    artifact_errors = _validate_artifact_completeness(run_path)
    checks["artifact_completeness"] = {
        "passed": not artifact_errors,
        "errors": artifact_errors,
    }
    errors.extend(artifact_errors)

    manifest = _json_load(run_path / "manifest.json") if (run_path / "manifest.json").exists() else None
    summary = _json_load(run_path / "summary.json") if (run_path / "summary.json").exists() else None
    steps = _jsonl_load(run_path / "steps.jsonl")
    episodes = _jsonl_load(run_path / "episodes.jsonl")

    step_errors: List[str] = []
    for index, step in enumerate(steps):
        for error in validate_step_schema(step):
            step_errors.append(f"step[{index}]: {error}")
    checks["step_schema"] = {
        "passed": not step_errors,
        "errors": step_errors,
    }
    errors.extend(step_errors)

    episode_errors: List[str] = []
    for index, episode in enumerate(episodes):
        for error in validate_episode_schema(episode):
            episode_errors.append(f"episode[{index}]: {error}")
    checks["episode_schema"] = {
        "passed": not episode_errors,
        "errors": episode_errors,
    }
    errors.extend(episode_errors)

    summary_errors, recomputed_metrics = compare_summary_against_episodes(run_path)
    checks["summary_consistency"] = {
        "passed": not summary_errors,
        "errors": summary_errors,
    }
    errors.extend(summary_errors)

    cross_file_errors = _validate_cross_file_consistency(
        run_path,
        steps=steps,
        episodes=episodes,
        manifest=manifest,
        summary=summary,
    )
    checks["cross_file_consistency"] = {
        "passed": not cross_file_errors,
        "errors": cross_file_errors,
    }
    errors.extend(cross_file_errors)

    metric_errors: List[str] = []
    for key in sorted(SUMMARY_METRIC_KEYS):
        if key not in recomputed_metrics:
            metric_errors.append(f"recomputed metrics missing key: {key}")
    checks["run_metric_sufficiency"] = {
        "passed": not metric_errors,
        "errors": metric_errors,
    }
    errors.extend(metric_errors)

    result = {
        "passed": not errors,
        "run_dir": str(run_path),
        "source": (
            (manifest or {}).get("source")
            or (summary or {}).get("source")
            or next((step.get("source") for step in steps if step.get("source")), "unknown")
        ),
        "metrics": recomputed_metrics,
        "checks": checks,
        "errors": errors,
    }
    return result


def write_acceptance_report(run_dir: str | Path, result: Mapping[str, Any]) -> Path:
    run_path = Path(run_dir)
    report_path = run_path / "acceptance.json"
    report_path.write_text(
        json.dumps(dict(result), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report_path


def run_acceptance_check(
    run_dir: str | Path,
    *,
    write_report: bool = True,
) -> Dict[str, Any]:
    result = validate_run_directory(run_dir)
    if write_report:
        write_acceptance_report(run_dir, result)
    return result


__all__ = [
    "CANONICAL_DONE_TYPES",
    "REQUIRED_EPISODE_FIELDS",
    "REQUIRED_STEP_FIELDS",
    "SUMMARY_METRIC_KEYS",
    "compare_summary_against_episodes",
    "load_run_summary",
    "run_acceptance_check",
    "validate_episode_schema",
    "validate_run_directory",
    "validate_step_schema",
    "write_acceptance_report",
]
