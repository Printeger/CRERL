"""Episode writing and run-directory loading helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

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
    "load_accepted_run_directory",
    "load_run_directories",
    "load_run_directory",
]
