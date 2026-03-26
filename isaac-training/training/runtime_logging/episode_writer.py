"""Episode writing and run-directory loading helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from envs.cre_logging import FlightEpisodeLogger


def create_episode_writer(*args, **kwargs):
    """Return the current episode logger implementation."""

    return FlightEpisodeLogger(*args, **kwargs)


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


def load_run_directory(run_dir: str | Path) -> Dict[str, Any]:
    run_path = Path(run_dir)
    return {
        "run_dir": str(run_path),
        "run_id": run_path.name,
        "manifest": _json_load(run_path / "manifest.json") if (run_path / "manifest.json").exists() else {},
        "summary": _json_load(run_path / "summary.json") if (run_path / "summary.json").exists() else {},
        "acceptance": _json_load(run_path / "acceptance.json") if (run_path / "acceptance.json").exists() else {},
        "steps": _jsonl_load(run_path / "steps.jsonl"),
        "episodes": _jsonl_load(run_path / "episodes.jsonl"),
    }


def _normalize_filter(values: Optional[Sequence[str]]) -> List[str]:
    if not values:
        return []
    return [str(item) for item in values if str(item)]


def _matches_filter(candidate_values: Sequence[str], expected: Sequence[str]) -> bool:
    if not expected:
        return True
    candidate_set = {str(item) for item in candidate_values if str(item)}
    expected_set = {str(item) for item in expected if str(item)}
    return bool(candidate_set & expected_set)


def load_accepted_run_directory(
    run_dir: str | Path,
    *,
    require_passed: bool = True,
) -> Dict[str, Any]:
    payload = load_run_directory(run_dir)
    acceptance = payload.get("acceptance") or {}
    if not acceptance:
        raise FileNotFoundError(f"Missing acceptance.json under run directory: {run_dir}")
    if require_passed and not bool(acceptance.get("passed", False)):
        raise ValueError(f"Run directory did not pass acceptance: {run_dir}")
    return payload


def discover_accepted_run_directories(
    logs_root: str | Path,
    *,
    sources: Optional[Sequence[str]] = None,
    scenario_types: Optional[Sequence[str]] = None,
    scene_cfg_names: Optional[Sequence[str]] = None,
    run_name_contains: Optional[str] = None,
    require_passed: bool = True,
) -> List[Path]:
    logs_root = Path(logs_root)
    expected_sources = _normalize_filter(sources)
    expected_scenarios = _normalize_filter(scenario_types)
    expected_scene_cfgs = _normalize_filter(scene_cfg_names)
    matched: List[Path] = []

    for run_dir in sorted(path for path in logs_root.iterdir() if path.is_dir()):
        acceptance_path = run_dir / "acceptance.json"
        if not acceptance_path.exists():
            continue
        payload = load_run_directory(run_dir)
        acceptance = payload.get("acceptance") or {}
        if require_passed and not bool(acceptance.get("passed", False)):
            continue
        if run_name_contains and run_name_contains not in run_dir.name:
            continue

        manifest = payload.get("manifest") or {}
        episodes = payload.get("episodes") or []
        candidate_sources = [
            str(manifest.get("source", "")),
            *(str(item.get("source", "")) for item in episodes),
        ]
        candidate_scenarios = [str(item.get("scenario_type", "")) for item in episodes]
        candidate_scene_cfgs = [str(item.get("scene_cfg_name", "")) for item in episodes]

        if not _matches_filter(candidate_sources, expected_sources):
            continue
        if not _matches_filter(candidate_scenarios, expected_scenarios):
            continue
        if not _matches_filter(candidate_scene_cfgs, expected_scene_cfgs):
            continue
        matched.append(run_dir)

    return matched


def load_run_directories(
    run_dirs: Sequence[str | Path],
    *,
    require_passed: bool = True,
) -> List[Dict[str, Any]]:
    return [
        load_accepted_run_directory(run_dir, require_passed=require_passed)
        for run_dir in run_dirs
    ]


__all__ = [
    "FlightEpisodeLogger",
    "create_episode_writer",
    "discover_accepted_run_directories",
    "load_accepted_run_directory",
    "load_run_directories",
    "load_run_directory",
]
