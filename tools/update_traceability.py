#!/usr/bin/env python3
"""Refresh the auto-generated summary section in Traceability.md from git state."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Sequence, Tuple


AUTO_START = "<!-- TRACEABILITY:BEGIN -->"
AUTO_END = "<!-- TRACEABILITY:END -->"
TRACEABILITY_FILE = "Traceability.md"


def run_git(args: Sequence[str], repo_root: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def get_repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def parse_name_status(raw: str) -> List[Tuple[str, str]]:
    entries: List[Tuple[str, str]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1]
        if path == TRACEABILITY_FILE:
            continue
        entries.append((status, path))
    return entries


def module_label(path: str) -> str:
    if path.startswith("doc/roadmap/"):
        return "Spec / Roadmap"
    if path.startswith("doc/"):
        return "Project Docs"
    if path.startswith("isaac-training/training/analyzers/"):
        return "Analyzers"
    if path.startswith("isaac-training/training/runtime_logging/"):
        return "Runtime Logging"
    if path.startswith("isaac-training/training/execution/"):
        return "Execution / Baselines"
    if path.startswith("isaac-training/training/cfg/spec_cfg/"):
        return "Specification Config"
    if path.startswith("isaac-training/training/envs/"):
        return "Procedural Env / Sensors"
    if path.startswith("isaac-training/training/scripts/env.py"):
        return "Isaac Env Core"
    if path.startswith("isaac-training/training/scripts/command_generator.py"):
        return "Baselines / Adversarial Probes"
    if path.startswith("isaac-training/training/scripts/"):
        return "Training Pipeline"
    if path.startswith("isaac-training/training/cfg/"):
        return "Training Config"
    if path.startswith("isaac-training/training/unit_test/"):
        return "Training Tests"
    if path.startswith("isaac-training/third_party/OmniDrones/"):
        return "UAV Platform Assets"
    if path.startswith("ros1/") or path.startswith("ros2/"):
        return "Deployment Stack"
    if path.startswith("tools/") or path.startswith(".githooks/"):
        return "Developer Workflow"
    return path.split("/", 1)[0] if "/" in path else "Repo Root"


def detect_phases(paths: Sequence[str]) -> List[str]:
    phases = set()
    for path in paths:
        roadmap_match = re.match(r"doc/roadmap/phase(\d+)\.md$", path)
        dev_log_match = re.match(r"doc/dev_log/p(\d+)_dev_status\.md$", path)
        if roadmap_match:
            phases.add(f"Phase {roadmap_match.group(1)}")
        if dev_log_match:
            phases.add(f"Phase {dev_log_match.group(1)}")
        if path in {"doc/roadmap.md", "doc/roadmap/roadmap.md"} or path.startswith("doc/specs/"):
            phases.add("Phase 0")
        if path.startswith("isaac-training/training/analyzers/"):
            name = Path(path).name
            if name.startswith("semantic") or name == "llm_analyzer.py":
                phases.add("Phase 6")
            elif name.startswith("dynamic"):
                phases.add("Phase 5")
            else:
                phases.add("Phase 4")
        if path.startswith("isaac-training/training/cfg/spec_cfg/"):
            phases.add("Phase 4")
        if (
            path.startswith("isaac-training/training/execution/")
            or "baseline" in path
        ):
            phases.add("Phase 3")
        if path.startswith("isaac-training/training/runtime_logging/"):
            phases.update({"Phase 2", "Phase 3"})
        if (
            path.startswith("isaac-training/training/scripts/env.py")
            or path.startswith("isaac-training/training/envs/")
            or path.startswith("isaac-training/training/cfg/")
        ):
            phases.update({"Phase 1", "Phase 4", "Phase 7"})
        if path.endswith("run_static_audit.py"):
            phases.add("Phase 4")
        if path.endswith("run_dynamic_audit.py"):
            phases.add("Phase 5")
        if path.endswith("run_semantic_audit.py"):
            phases.add("Phase 6")
        if "command_generator.py" in path:
            phases.update({"Phase 2", "Phase 3"})
        if path.startswith("ros1/") or path.startswith("ros2/"):
            phases.add("Phase 7")
    return sorted(phases)


def shortstat(repo_root: Path, staged_only: bool) -> str:
    args = ["diff", "--shortstat"]
    if staged_only:
        args.insert(1, "--cached")
    text = run_git(args, repo_root).strip()
    return text or "No diff stat available."


def get_branch(repo_root: Path) -> str:
    return run_git(["branch", "--show-current"], repo_root).strip() or "DETACHED"


def render_summary(repo_root: Path, staged_only: bool) -> str:
    status_args = ["diff", "--name-status", "--find-renames"]
    if staged_only:
        status_args.insert(1, "--cached")
    entries = parse_name_status(run_git(status_args, repo_root))

    timestamp = dt.datetime.now().isoformat(timespec="seconds")
    branch = get_branch(repo_root)

    lines = [
        f"_Updated: `{timestamp}`_",
        "",
        f"- Scope: `{repo_root}`",
        f"- Branch: `{branch}`",
        f"- Source: `{'staged diff' if staged_only else 'working tree diff'}`",
    ]

    if not entries:
        lines.extend(
            [
                "- Impacted phases: none",
                "- Diff stat: no staged changes detected",
                "",
                "No staged changes were found when the summary was generated.",
            ]
        )
        return "\n".join(lines)

    paths = [path for _, path in entries]
    phases = detect_phases(paths)
    lines.append(f"- Impacted phases: `{', '.join(phases) if phases else 'unclassified'}`")
    lines.append(f"- Diff stat: {shortstat(repo_root, staged_only)}")
    lines.append("")
    lines.append("### Changed Files")
    for status, path in entries:
        lines.append(f"- `{status}` [{path}]({path}) [{module_label(path)}]")

    return "\n".join(lines)


def update_traceability(repo_root: Path, staged_only: bool) -> int:
    traceability_path = repo_root / TRACEABILITY_FILE
    if not traceability_path.exists():
        raise FileNotFoundError(f"{TRACEABILITY_FILE} not found at repo root")

    original = traceability_path.read_text()
    if AUTO_START not in original or AUTO_END not in original:
        raise ValueError("Traceability.md is missing auto-summary markers")

    start = original.index(AUTO_START) + len(AUTO_START)
    end = original.index(AUTO_END)
    rendered = "\n" + render_summary(repo_root, staged_only) + "\n"
    updated = original[:start] + rendered + original[end:]

    if updated != original:
        traceability_path.write_text(updated)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--working-tree",
        action="store_true",
        help="Summarize the working tree diff instead of the staged diff.",
    )
    args = parser.parse_args()

    repo_root = get_repo_root()
    update_traceability(repo_root, staged_only=not args.working_tree)
    return 0


if __name__ == "__main__":
    sys.exit(main())
