"""Artifact scanning and view-model helpers for the local CRE dashboard."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Mapping, Sequence


TRAINING_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOGS_ROOT = TRAINING_ROOT / "logs"
DEFAULT_REPORTS_ROOT = TRAINING_ROOT / "reports"
TMP_ROOT = Path("/tmp")

FLOW_ORDER = [
    "spec",
    "scene",
    "execution",
    "logs",
    "static",
    "dynamic",
    "semantic",
    "report",
    "repair",
    "validation",
    "integration",
    "benchmark",
    "release",
]

FLOW_LABELS = {
    "spec": "Spec",
    "scene": "Scene",
    "execution": "Execution",
    "logs": "Logs",
    "static": "Static",
    "dynamic": "Dynamic",
    "semantic": "Semantic",
    "report": "Report",
    "repair": "Repair",
    "validation": "Validation",
    "integration": "Integration",
    "benchmark": "Benchmark",
    "release": "Release",
}

FLOW_PHASES = {
    "spec": "Phase 0",
    "scene": "Phase 1",
    "execution": "Phase 3",
    "logs": "Phase 2",
    "static": "Phase 4",
    "dynamic": "Phase 5",
    "semantic": "Phase 6",
    "report": "Phase 7",
    "repair": "Phase 8",
    "validation": "Phase 9",
    "integration": "Phase 10",
    "benchmark": "Phase 11",
    "release": "Phase 11",
}

STATUS_PRIORITY = {
    "failed": 5,
    "warning": 4,
    "running": 3,
    "passed": 2,
    "idle": 1,
}

ANALYSIS_PRIMARY_FILES = {
    "static": "static_report.json",
    "dynamic": "dynamic_report.json",
    "semantic": "semantic_report.json",
    "report": "report.json",
    "repair": "repair_plan.json",
    "validation": "validation_decision.json",
    "integration": "integration_summary.json",
    "benchmark": "benchmark_summary.json",
    "release": "release_summary.json",
}

ANALYSIS_SUMMARY_FILES = {
    "static": "summary.json",
    "dynamic": "summary.json",
    "semantic": "summary.json",
    "report": "summary.json",
    "repair": "repair_summary.json",
    "validation": "validation_summary.json",
    "integration": "integration_summary.json",
    "benchmark": "benchmark_summary.json",
    "release": "release_summary.json",
}

FULL_SMOKE_STEP_FILES = [
    ("static", "static_cli_output.json"),
    ("dynamic", "dynamic_cli_output.json"),
    ("semantic", "semantic_cli_output.json"),
    ("report", "report_cli_output.json"),
    ("repair", "repair_cli_output.json"),
    ("validation", "validation_cli_output.json"),
    ("integration", "integration_cli_output.json"),
    ("benchmark", "benchmark_cli_output.json"),
    ("release", "release_cli_output.json"),
]

NATIVE_STEP_FILES = [
    ("static", "static_report_copy.json"),
    ("dynamic", "dynamic_report_copy.json"),
    ("semantic", "semantic_report_copy.json"),
    ("report", "report_copy.json"),
    ("repair", "repair_plan_copy.json"),
    ("validation", "validation_decision_copy.json"),
]

WITNESS_COLOR = {
    "W_CR": "#d97706",
    "W_EC": "#2563eb",
    "W_ER": "#7c3aed",
}

REWARD_COMPONENT_KEYS = [
    "reward_progress",
    "reward_safety_static",
    "reward_safety_dynamic",
    "penalty_smooth",
    "penalty_height",
    "manual_control",
]

WANDB_METRIC_ALIASES = {
    "policy_loss": ["policy_loss", "loss/policy", "train/policy_loss"],
    "value_loss": ["value_loss", "loss/value", "train/value_loss"],
    "entropy": ["entropy", "train/entropy"],
    "kl": ["kl", "train/kl", "approx_kl"],
    "learning_rate": ["learning_rate", "lr", "train/lr"],
    "fps": ["fps", "frames_per_second", "train/fps"],
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_or_empty(value: float | None) -> str:
    if value is None:
        return ""
    return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()


def _safe_read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _safe_read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def _existing_paths(paths: Iterable[Path]) -> List[Path]:
    unique = []
    seen = set()
    for path in paths:
        try:
            resolved = path.resolve()
        except FileNotFoundError:
            resolved = path
        key = str(resolved)
        if key in seen or not path.exists():
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _max_mtime(paths: Iterable[Path]) -> float | None:
    mtimes = [path.stat().st_mtime for path in paths if path.exists()]
    return max(mtimes) if mtimes else None


def _status_from_passed(*, passed: bool, severity: str | None = None) -> str:
    if not passed:
        return "failed"
    if severity in {"warning", "medium", "high", "critical"}:
        return "warning"
    return "passed"


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        cast = float(value)
    except Exception:
        return None
    if math.isnan(cast) or math.isinf(cast):
        return None
    return cast


def _mean_or_none(values: Iterable[Any]) -> float | None:
    cleaned = [float(item) for item in values if _to_float(item) is not None]
    return mean(cleaned) if cleaned else None


def _first_episode_metadata(episodes: Sequence[Mapping[str, Any]]) -> Dict[str, str]:
    if not episodes:
        return {"scenario_type": "", "scene_cfg_name": "", "source": "", "scene_family": ""}
    first = dict(episodes[0])
    scene_tags = dict(first.get("scene_tags") or {})
    return {
        "scenario_type": str(first.get("scenario_type", scene_tags.get("scenario_type", ""))),
        "scene_cfg_name": str(first.get("scene_cfg_name", scene_tags.get("scene_cfg_name", ""))),
        "source": str(first.get("source", "")),
        "scene_family": str(scene_tags.get("scene_family", first.get("scenario_type", ""))),
    }


def _aggregate_reward_components(episodes: Sequence[Mapping[str, Any]]) -> Dict[str, float]:
    totals: Dict[str, float] = {key: 0.0 for key in REWARD_COMPONENT_KEYS}
    for episode in episodes:
        reward_totals = dict(episode.get("reward_components_total") or {})
        for key in REWARD_COMPONENT_KEYS:
            totals[key] += float(reward_totals.get(key, 0.0) or 0.0)
    if not any(abs(value) > 0 for value in totals.values()):
        return {}
    return totals


def _discover_default_watch_roots(
    extra_watch_roots: Sequence[str | Path] | None = None,
    *,
    include_defaults: bool = True,
) -> List[Path]:
    candidates: List[Path] = []
    if include_defaults:
        candidates.append(TRAINING_ROOT)
        if TMP_ROOT.exists():
            tmp_candidates = sorted(TMP_ROOT.glob("crerl_*"))
            candidates.extend(path for path in tmp_candidates if path.is_dir())
    if extra_watch_roots:
        candidates.extend(Path(path) for path in extra_watch_roots)
    return _existing_paths(candidates)


def _iter_log_roots(logs_root: str | Path, watch_roots: Sequence[Path]) -> List[Path]:
    candidates: List[Path] = [Path(logs_root)]
    for root in watch_roots:
        if (root / "logs").exists():
            candidates.append(root / "logs")
    return _existing_paths(candidates)


def _iter_analysis_roots(reports_root: str | Path, watch_roots: Sequence[Path]) -> List[Path]:
    candidates: List[Path] = []
    reports_root = Path(reports_root)
    if (reports_root / "analysis").exists():
        candidates.append(reports_root / "analysis")
    if reports_root.name == "analysis" and reports_root.exists():
        candidates.append(reports_root)
    for root in watch_roots:
        if (root / "analysis").exists():
            candidates.append(root / "analysis")
        if (root / "reports" / "analysis").exists():
            candidates.append(root / "reports" / "analysis")
    return _existing_paths(candidates)


def discover_run_snapshots(logs_root: str | Path, watch_roots: Sequence[Path]) -> List[Dict[str, Any]]:
    snapshots: List[Dict[str, Any]] = []
    for root in _iter_log_roots(logs_root, watch_roots):
        for run_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            manifest_path = run_dir / "manifest.json"
            summary_path = run_dir / "summary.json"
            acceptance_path = run_dir / "acceptance.json"
            steps_path = run_dir / "steps.jsonl"
            episodes_path = run_dir / "episodes.jsonl"
            if not any(path.exists() for path in [manifest_path, summary_path, acceptance_path, episodes_path]):
                continue

            manifest = _safe_read_json(manifest_path)
            summary = _safe_read_json(summary_path)
            acceptance = _safe_read_json(acceptance_path)
            episodes = _safe_read_jsonl(episodes_path)
            episode_meta = _first_episode_metadata(episodes)
            reward_components = _aggregate_reward_components(episodes)
            run_metadata = dict(summary.get("run_metadata") or manifest.get("run_metadata") or {})

            status = "idle"
            if steps_path.exists() and not acceptance_path.exists():
                status = "running"
            elif acceptance:
                status = _status_from_passed(
                    passed=bool(acceptance.get("passed", False)),
                    severity=str(acceptance.get("max_severity", "") or ""),
                )
            elif summary:
                status = "warning"

            execution_mode = str(
                run_metadata.get("execution_mode")
                or episode_meta.get("source")
                or manifest.get("source", "")
            )
            if execution_mode == "test_flight":
                execution_mode = "manual"

            snapshots.append(
                {
                    "kind": "run",
                    "module": "logs" if status != "running" else "execution",
                    "run_id": str(summary.get("run_id", manifest.get("run_id", run_dir.name))),
                    "name": run_dir.name,
                    "path": str(run_dir),
                    "mtime": _max_mtime([manifest_path, summary_path, acceptance_path, steps_path, episodes_path]),
                    "status": status,
                    "source": str(manifest.get("source", episode_meta.get("source", ""))),
                    "execution_mode": execution_mode,
                    "scenario_type": str(episode_meta.get("scenario_type", "")),
                    "scene_cfg_name": str(episode_meta.get("scene_cfg_name", "")),
                    "scene_family": str(episode_meta.get("scene_family", "")),
                    "run_metadata": run_metadata,
                    "summary": summary,
                    "acceptance": acceptance,
                    "episode_count": int(summary.get("episode_count", len(episodes) or 0)),
                    "reward_components": reward_components,
                    "done_type_counts": dict(summary.get("done_type_counts") or {}),
                    "manifest_path": str(manifest_path) if manifest_path.exists() else "",
                    "summary_path": str(summary_path) if summary_path.exists() else "",
                    "acceptance_path": str(acceptance_path) if acceptance_path.exists() else "",
                    "scene_tags": dict((episodes[0] if episodes else {}).get("scene_tags") or {}),
                }
            )
    return sorted(snapshots, key=lambda item: (item.get("mtime") or 0.0, item["name"]))


def _bundle_status(namespace: str, primary: Mapping[str, Any], summary: Mapping[str, Any], bundle_dir: Path) -> str:
    if not (bundle_dir / ANALYSIS_PRIMARY_FILES[namespace]).exists() or not (bundle_dir / ANALYSIS_SUMMARY_FILES[namespace]).exists():
        return "running"

    if namespace in {"static", "dynamic", "semantic", "report", "integration"}:
        return _status_from_passed(
            passed=bool(primary.get("passed", False)),
            severity=str(primary.get("max_severity", summary.get("max_severity", "")) or ""),
        )
    if namespace == "repair":
        acceptance = _safe_read_json(bundle_dir / "acceptance.json")
        if acceptance:
            return _status_from_passed(
                passed=bool(acceptance.get("passed", False)),
                severity=str(acceptance.get("max_severity", summary.get("max_severity", "")) or ""),
            )
        return "passed" if bool(summary.get("phase9_ready", False)) else "warning"
    if namespace == "validation":
        decision = str(primary.get("decision_status", ""))
        if decision == "accepted":
            return "passed"
        if decision in {"rejected", "inconclusive"}:
            return "warning"
        return "failed"
    if namespace == "benchmark":
        case_count = int(summary.get("case_count", 0) or 0)
        ready_count = int(summary.get("ready_case_count", 0) or 0)
        return "passed" if case_count > 0 and ready_count >= case_count else "warning"
    if namespace == "release":
        return "passed" if bool(summary.get("phase11_exit_ready", False)) else "warning"
    return "idle"


def discover_bundle_snapshots(reports_root: str | Path, watch_roots: Sequence[Path]) -> List[Dict[str, Any]]:
    snapshots: List[Dict[str, Any]] = []
    for analysis_root in _iter_analysis_roots(reports_root, watch_roots):
        for namespace in ANALYSIS_PRIMARY_FILES:
            namespace_root = analysis_root / namespace
            if not namespace_root.exists():
                continue
            for bundle_dir in sorted(path for path in namespace_root.iterdir() if path.is_dir()):
                manifest_path = bundle_dir / "manifest.json"
                primary_path = bundle_dir / ANALYSIS_PRIMARY_FILES[namespace]
                summary_path = bundle_dir / ANALYSIS_SUMMARY_FILES[namespace]
                if not any(path.exists() for path in [manifest_path, primary_path, summary_path]):
                    continue
                manifest = _safe_read_json(manifest_path)
                primary = _safe_read_json(primary_path)
                summary = _safe_read_json(summary_path)
                snapshots.append(
                    {
                        "kind": "bundle",
                        "module": namespace,
                        "name": bundle_dir.name,
                        "path": str(bundle_dir),
                        "namespace": namespace,
                        "mtime": _max_mtime([manifest_path, primary_path, summary_path]),
                        "status": _bundle_status(namespace, primary, summary, bundle_dir),
                        "manifest": manifest,
                        "primary": primary,
                        "summary": summary,
                        "manifest_path": str(manifest_path) if manifest_path.exists() else "",
                        "primary_path": str(primary_path) if primary_path.exists() else "",
                        "summary_path": str(summary_path) if summary_path.exists() else "",
                    }
                )
    return sorted(snapshots, key=lambda item: (item.get("mtime") or 0.0, item["name"]))


def discover_workspace_snapshots(watch_roots: Sequence[Path]) -> List[Dict[str, Any]]:
    workspaces: List[Dict[str, Any]] = []
    for root in watch_roots:
        full_summary = root / "full_smoke_summary.json"
        native_summary = root / "native_execution_summary.json"
        if full_summary.exists():
            summary = _safe_read_json(full_summary)
            workspaces.append(
                {
                    "kind": "workspace",
                    "workspace_type": "analysis-only-smoke",
                    "name": root.name,
                    "path": str(root),
                    "mtime": full_summary.stat().st_mtime,
                    "status": "passed",
                    "summary": summary,
                    "summary_path": str(full_summary),
                    "module": "release",
                }
            )
        elif any((root / filename).exists() for _, filename in FULL_SMOKE_STEP_FILES):
            existing = [(module, root / filename) for module, filename in FULL_SMOKE_STEP_FILES if (root / filename).exists()]
            module, last_path = sorted(existing, key=lambda item: item[1].stat().st_mtime)[-1]
            workspaces.append(
                {
                    "kind": "workspace",
                    "workspace_type": "analysis-only-smoke",
                    "name": root.name,
                    "path": str(root),
                    "mtime": last_path.stat().st_mtime,
                    "status": "running",
                    "summary": {},
                    "summary_path": "",
                    "module": module,
                }
            )

        if native_summary.exists():
            summary = _safe_read_json(native_summary)
            workspaces.append(
                {
                    "kind": "workspace",
                    "workspace_type": "native-execution-smoke",
                    "name": root.name,
                    "path": str(root),
                    "mtime": native_summary.stat().st_mtime,
                    "status": "passed",
                    "summary": summary,
                    "summary_path": str(native_summary),
                    "module": "validation",
                }
            )
        elif any((root / filename).exists() for _, filename in NATIVE_STEP_FILES):
            existing = [(module, root / filename) for module, filename in NATIVE_STEP_FILES if (root / filename).exists()]
            module, last_path = sorted(existing, key=lambda item: item[1].stat().st_mtime)[-1]
            workspaces.append(
                {
                    "kind": "workspace",
                    "workspace_type": "native-execution-smoke",
                    "name": root.name,
                    "path": str(root),
                    "mtime": last_path.stat().st_mtime,
                    "status": "running",
                    "summary": {},
                    "summary_path": "",
                    "module": module,
                }
            )
    return sorted(workspaces, key=lambda item: (item.get("mtime") or 0.0, item["name"]))


def _latest_by_module(module: str, runs: Sequence[Mapping[str, Any]], bundles: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    candidates = [item for item in [*runs, *bundles] if item.get("module") == module]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.get("mtime") or 0.0)


def _infer_active_context(
    runs: Sequence[Mapping[str, Any]],
    bundles: Sequence[Mapping[str, Any]],
    workspaces: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    running_bundles = [item for item in bundles if item.get("status") == "running"]
    if running_bundles:
        active = max(running_bundles, key=lambda item: item.get("mtime") or 0.0)
        return {
            "source_kind": "bundle",
            "module": active["module"],
            "phase": FLOW_PHASES.get(active["module"], ""),
            "title": f"{FLOW_LABELS.get(active['module'], active['module']).title()} bundle is running",
            "path": active["path"],
            "input_name": active["name"],
            "status": active["status"],
            "mtime": active.get("mtime"),
            "details": active,
        }

    running_runs = [item for item in runs if item.get("status") == "running"]
    if running_runs:
        active = max(running_runs, key=lambda item: item.get("mtime") or 0.0)
        module = "execution"
        return {
            "source_kind": "run",
            "module": module,
            "phase": FLOW_PHASES.get(module, ""),
            "title": f"{active.get('execution_mode', active.get('source', 'run'))} execution is running",
            "path": active["path"],
            "input_name": active["run_id"],
            "status": active["status"],
            "mtime": active.get("mtime"),
            "details": active,
        }

    running_workspaces = [item for item in workspaces if item.get("status") == "running"]
    if running_workspaces:
        active = max(running_workspaces, key=lambda item: item.get("mtime") or 0.0)
        return {
            "source_kind": "workspace",
            "module": active["module"],
            "phase": FLOW_PHASES.get(active["module"], ""),
            "title": f"{active.get('workspace_type', 'workspace')} is progressing",
            "path": active["path"],
            "input_name": active["name"],
            "status": active["status"],
            "mtime": active.get("mtime"),
            "details": active,
        }

    completed = [*bundles, *runs, *workspaces]
    if completed:
        active = max(completed, key=lambda item: item.get("mtime") or 0.0)
        module = str(active.get("module", "release"))
        title = (
            f"Latest completed {FLOW_LABELS.get(module, module).title()} artifact"
            if active.get("kind") != "run"
            else f"Latest completed {active.get('execution_mode', active.get('source', 'run'))} run"
        )
        return {
            "source_kind": str(active.get("kind", "artifact")),
            "module": module,
            "phase": FLOW_PHASES.get(module, ""),
            "title": title,
            "path": active["path"],
            "input_name": str(active.get("name", active.get("run_id", ""))),
            "status": str(active.get("status", "idle")),
            "mtime": active.get("mtime"),
            "details": active,
        }

    return {
        "source_kind": "none",
        "module": "spec",
        "phase": FLOW_PHASES["spec"],
        "title": "No live artifacts found yet",
        "path": "",
        "input_name": "",
        "status": "idle",
        "mtime": None,
        "details": {},
    }


def _spec_node() -> Dict[str, Any]:
    spec_dir = TRAINING_ROOT / "cfg" / "spec_cfg"
    env_dir = TRAINING_ROOT / "cfg" / "env_cfg"
    passed = spec_dir.exists() and env_dir.exists()
    return {
        "module": "spec",
        "label": FLOW_LABELS["spec"],
        "phase": FLOW_PHASES["spec"],
        "status": "passed" if passed else "failed",
        "headline": "Spec and env cfg roots",
        "current_object": f"{len(list(spec_dir.glob('*.yaml')))} spec cfgs / {len(list(env_dir.glob('*.yaml')))} env cfgs",
        "last_update": _iso_or_empty(_max_mtime([spec_dir, env_dir])),
        "path": str(spec_dir),
        "details": {
            "spec_cfg_dir": str(spec_dir),
            "env_cfg_dir": str(env_dir),
        },
    }


def _scene_node() -> Dict[str, Any]:
    env_gen = TRAINING_ROOT / "envs" / "env_gen.py"
    bridge = TRAINING_ROOT / "envs" / "runtime" / "scene_family_bridge.py"
    passed = env_gen.exists() and bridge.exists()
    return {
        "module": "scene",
        "label": FLOW_LABELS["scene"],
        "phase": FLOW_PHASES["scene"],
        "status": "passed" if passed else "failed",
        "headline": "Scene backend availability",
        "current_object": "env_gen + scene_family_bridge",
        "last_update": _iso_or_empty(_max_mtime([env_gen, bridge])),
        "path": str(bridge),
        "details": {
            "env_gen_path": str(env_gen),
            "scene_family_bridge_path": str(bridge),
        },
    }


def _flow_node_from_artifact(module: str, artifact: Mapping[str, Any] | None) -> Dict[str, Any]:
    if artifact is None:
        return {
            "module": module,
            "label": FLOW_LABELS[module],
            "phase": FLOW_PHASES[module],
            "status": "idle",
            "headline": "No artifact yet",
            "current_object": "",
            "last_update": "",
            "path": "",
            "details": {},
        }
    summary = dict(artifact.get("summary") or artifact.get("primary") or {})
    headline = artifact.get("name", "")
    if module in {"execution", "logs"}:
        headline = str(artifact.get("run_id", artifact.get("name", "")))
    current_object = ""
    if module in {"execution", "logs"}:
        current_object = f"{artifact.get('execution_mode', artifact.get('source', 'run'))} · {artifact.get('scenario_type', '')}"
    elif module == "validation":
        current_object = str(summary.get("decision_status", ""))
    elif module == "release":
        current_object = f"exit_ready={summary.get('phase11_exit_ready', False)}"
    elif module == "benchmark":
        current_object = f"{summary.get('ready_case_count', 0)}/{summary.get('case_count', 0)} cases ready"
    elif module == "repair":
        current_object = str(summary.get("selected_candidate_id", ""))
    elif module == "report":
        current_object = str(summary.get("primary_claim_type", ""))
    elif module == "semantic":
        current_object = str(summary.get("most_likely_claim_type", summary.get("primary_claim_type", "")))
    elif module == "dynamic":
        witness_scores = dict(summary.get("witness_scores") or {})
        if witness_scores:
            current_object = ", ".join(f"{key}={value:.3f}" for key, value in witness_scores.items() if _to_float(value) is not None)
    return {
        "module": module,
        "label": FLOW_LABELS[module],
        "phase": FLOW_PHASES[module],
        "status": str(artifact.get("status", "idle")),
        "headline": headline,
        "current_object": current_object,
        "last_update": _iso_or_empty(artifact.get("mtime")),
        "path": str(artifact.get("path", "")),
        "details": dict(artifact),
    }


def build_flow_nodes(
    runs: Sequence[Mapping[str, Any]],
    bundles: Sequence[Mapping[str, Any]],
    workspaces: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    nodes: List[Dict[str, Any]] = [_spec_node(), _scene_node()]

    latest_execution = None
    if runs:
        latest_execution = max(runs, key=lambda item: item.get("mtime") or 0.0)
    nodes.append(_flow_node_from_artifact("execution", latest_execution))
    nodes.append(_flow_node_from_artifact("logs", latest_execution))

    for module in ["static", "dynamic", "semantic", "report", "repair", "validation", "integration", "benchmark", "release"]:
        nodes.append(_flow_node_from_artifact(module, _latest_by_module(module, runs, bundles)))

    if workspaces:
        latest_workspace = max(workspaces, key=lambda item: item.get("mtime") or 0.0)
        latest_module = latest_workspace.get("module")
        for node in nodes:
            if node["module"] == latest_module and node["status"] == "idle":
                node["status"] = latest_workspace.get("status", "idle")
                node["headline"] = latest_workspace.get("workspace_type", "")
                node["current_object"] = latest_workspace.get("name", "")
                node["last_update"] = _iso_or_empty(latest_workspace.get("mtime"))
                node["path"] = latest_workspace.get("path", "")
    return nodes


def build_recent_events(
    runs: Sequence[Mapping[str, Any]],
    bundles: Sequence[Mapping[str, Any]],
    workspaces: Sequence[Mapping[str, Any]],
    *,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for run in runs:
        events.append(
            {
                "timestamp": _iso_or_empty(run.get("mtime")),
                "module": run.get("module", "logs"),
                "status": run.get("status", "idle"),
                "title": f"Run {run.get('run_id', run.get('name', ''))}",
                "summary": f"{run.get('execution_mode', run.get('source', 'run'))} · {run.get('scenario_type', '')}",
                "path": run.get("path", ""),
            }
        )
    for bundle in bundles:
        events.append(
            {
                "timestamp": _iso_or_empty(bundle.get("mtime")),
                "module": bundle.get("module", ""),
                "status": bundle.get("status", "idle"),
                "title": f"{bundle.get('module', '').title()} bundle {bundle.get('name', '')}",
                "summary": str(bundle.get("primary", {}).get("primary_claim_type", bundle.get("summary", {}).get("max_severity", ""))),
                "path": bundle.get("path", ""),
            }
        )
    for workspace in workspaces:
        events.append(
            {
                "timestamp": _iso_or_empty(workspace.get("mtime")),
                "module": workspace.get("module", ""),
                "status": workspace.get("status", "idle"),
                "title": str(workspace.get("workspace_type", "")),
                "summary": str(workspace.get("name", "")),
                "path": workspace.get("path", ""),
            }
        )
    events.sort(key=lambda item: item["timestamp"], reverse=True)
    return events[:limit]


def _status_badge(status: str) -> str:
    return {
        "passed": "completed",
        "warning": "warning",
        "failed": "failed",
        "running": "running",
        "idle": "idle",
    }.get(status, status)


def build_overview(
    active: Mapping[str, Any],
    flow_nodes: Sequence[Mapping[str, Any]],
    runs: Sequence[Mapping[str, Any]],
    bundles: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    latest_semantic = _latest_by_module("semantic", runs, bundles) or {}
    semantic_metadata = dict(dict(latest_semantic.get("primary") or {}).get("metadata") or {})
    provider_mode = str(
        semantic_metadata.get("provider_mode")
        or semantic_metadata.get("provider_name")
        or dict(latest_semantic.get("summary") or {}).get("provider_mode", "")
    )
    if provider_mode == "custom":
        provider_name = str(semantic_metadata.get("provider_name", ""))
        if "azure_gateway" in provider_name:
            provider_mode = "azure_gateway"
        elif "mock" in provider_name:
            provider_mode = "mock"
    # analysis-only smoke summaries carry provider_mode in step outputs, but bundle does not;
    # keep a stable fallback if a semantic bundle lacks the provider field.
    if not provider_mode:
        provider_mode = str(dict(latest_semantic.get("summary") or {}).get("provider_mode", "")) or "artifact-only"

    latest_mtime = max(
        [item.get("mtime") or 0.0 for item in [*runs, *bundles] if item.get("mtime")],
        default=None,
    )
    overall_status = "idle"
    if any(node["status"] == "failed" for node in flow_nodes):
        overall_status = "failed"
    elif any(node["status"] == "warning" for node in flow_nodes):
        overall_status = "warning"
    elif any(node["status"] == "running" for node in flow_nodes):
        overall_status = "running"
    elif any(node["status"] == "passed" for node in flow_nodes):
        overall_status = "completed"

    details = dict(active.get("details") or {})
    run_or_bundle = ""
    if active.get("source_kind") == "run":
        run_or_bundle = str(details.get("run_id", details.get("name", "")))
    else:
        run_or_bundle = str(details.get("name", active.get("input_name", "")))
    execution_mode = str(details.get("execution_mode", details.get("source", "")))
    scene_family = str(details.get("scene_family", details.get("scenario_type", "")))
    return {
        "current_phase": str(active.get("phase", "")),
        "active_module": FLOW_LABELS.get(str(active.get("module", "")), str(active.get("module", ""))),
        "current_object": run_or_bundle,
        "execution_mode": execution_mode or "-",
        "scene_family": scene_family or "-",
        "provider_mode": provider_mode or "-",
        "overall_health": overall_status,
        "overall_health_label": _status_badge(overall_status),
        "last_update": _iso_or_empty(latest_mtime),
    }


def build_kpis(
    runs: Sequence[Mapping[str, Any]],
    bundles: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    latest_run = max(runs, key=lambda item: item.get("mtime") or 0.0) if runs else {}
    latest_dynamic = _latest_by_module("dynamic", runs, bundles) or {}
    latest_semantic = _latest_by_module("semantic", runs, bundles) or {}
    latest_report = _latest_by_module("report", runs, bundles) or {}
    latest_validation = _latest_by_module("validation", runs, bundles) or {}
    latest_release = _latest_by_module("release", runs, bundles) or {}

    summary = dict(latest_run.get("summary") or {})
    dynamic_primary = dict(latest_dynamic.get("primary") or {})
    witness_scores = dict(dynamic_primary.get("witness_scores") or {})
    if not witness_scores:
        for witness in list(dynamic_primary.get("witnesses") or []):
            if not isinstance(witness, dict):
                continue
            witness_id = str(witness.get("witness_id", ""))
            score = _to_float(witness.get("score"))
            if witness_id and score is not None:
                witness_scores[witness_id] = score

    semantic_primary = dict(latest_semantic.get("primary") or {})
    semantic_summary = dict(latest_report.get("primary", {}).get("semantic_claim_summary") or {})
    validation_primary = dict(latest_validation.get("primary") or {})
    release_summary = dict(latest_release.get("summary") or latest_release.get("primary") or {})

    return [
        {"label": "success_rate", "value": summary.get("success_rate", "-"), "status": latest_run.get("status", "idle")},
        {"label": "collision_rate", "value": summary.get("collision_rate", "-"), "status": latest_run.get("status", "idle")},
        {"label": "out_of_bounds_rate", "value": summary.get("out_of_bounds_rate", "-"), "status": latest_run.get("status", "idle")},
        {"label": "min_distance", "value": summary.get("min_distance", "-"), "status": latest_run.get("status", "idle")},
        {"label": "near_violation_ratio", "value": summary.get("near_violation_ratio", "-"), "status": latest_run.get("status", "idle")},
        {"label": "average_return", "value": summary.get("average_return", "-"), "status": latest_run.get("status", "idle")},
        {"label": "W_CR", "value": witness_scores.get("W_CR", "-"), "status": latest_dynamic.get("status", "idle")},
        {"label": "W_EC", "value": witness_scores.get("W_EC", "-"), "status": latest_dynamic.get("status", "idle")},
        {"label": "W_ER", "value": witness_scores.get("W_ER", "-"), "status": latest_dynamic.get("status", "idle")},
        {
            "label": "semantic_primary_claim_type",
            "value": semantic_summary.get("most_likely_claim_type", semantic_primary.get("primary_claim_type", "-")),
            "status": latest_semantic.get("status", "idle"),
        },
        {
            "label": "report_primary_claim_type",
            "value": dict(latest_report.get("primary") or {}).get("root_cause_summary", {}).get("primary_claim_type", dict(latest_report.get("primary") or {}).get("primary_claim_type", "-")),
            "status": latest_report.get("status", "idle"),
        },
        {
            "label": "validation_decision_status",
            "value": validation_primary.get("decision_status", "-"),
            "status": latest_validation.get("status", "idle"),
        },
        {
            "label": "release_readiness",
            "value": release_summary.get("phase11_exit_ready", "-"),
            "status": latest_release.get("status", "idle"),
        },
    ]


def _build_series_chart(title: str, x: Sequence[Any], traces: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "title": title,
        "data": [dict(trace, x=list(x)) for trace in traces],
        "layout": {
            "title": {"text": title, "font": {"size": 14}},
            "paper_bgcolor": "#f8fafc",
            "plot_bgcolor": "#ffffff",
            "margin": {"l": 42, "r": 18, "t": 42, "b": 56},
            "legend": {"orientation": "h"},
            "xaxis": {"tickangle": -20, "automargin": True},
        },
    }


def _build_bar_chart(title: str, x: Sequence[Any], traces: Sequence[Dict[str, Any]], *, barmode: str = "group") -> Dict[str, Any]:
    chart = _build_series_chart(title, x, traces)
    chart["layout"]["barmode"] = barmode
    return chart


def _wandb_chart_specs(watch_roots: Sequence[Path]) -> List[Dict[str, Any]]:
    histories: List[Path] = []
    for root in watch_roots:
        histories.extend(root.rglob("wandb-history.jsonl"))
    histories = sorted({path for path in histories if path.exists()}, key=lambda p: p.stat().st_mtime)
    if not histories:
        return []
    latest = histories[-1]
    rows = _safe_read_jsonl(latest)
    if not rows:
        return []
    chart_specs: List[Dict[str, Any]] = []
    step_axis = list(range(len(rows)))
    for metric_name, aliases in WANDB_METRIC_ALIASES.items():
        values = []
        for row in rows:
            value = None
            for alias in aliases:
                if alias in row and _to_float(row.get(alias)) is not None:
                    value = float(row[alias])
                    break
            values.append(value)
        if not any(value is not None for value in values):
            continue
        chart_specs.append(
            _build_series_chart(
                f"WandB {metric_name}",
                step_axis,
                [
                    {
                        "type": "scatter",
                        "mode": "lines+markers",
                        "name": metric_name,
                        "y": values,
                        "line": {"width": 2},
                    }
                ],
            )
        )
    return chart_specs


def build_chart_specs(
    runs: Sequence[Mapping[str, Any]],
    bundles: Sequence[Mapping[str, Any]],
    watch_roots: Sequence[Path],
) -> List[Dict[str, Any]]:
    charts: List[Dict[str, Any]] = []

    sorted_runs = sorted(runs, key=lambda item: item.get("mtime") or 0.0)[-12:]
    run_labels = [item.get("run_id", item.get("name", "")) for item in sorted_runs]
    if sorted_runs:
        charts.append(
            _build_series_chart(
                "Average Return Trend",
                run_labels,
                [
                    {
                        "type": "scatter",
                        "mode": "lines+markers",
                        "name": "average_return",
                        "y": [item.get("summary", {}).get("average_return") for item in sorted_runs],
                        "line": {"color": "#2563eb", "width": 3},
                    }
                ],
            )
        )
        charts.append(
            _build_series_chart(
                "Safety Outcome Trend",
                run_labels,
                [
                    {
                        "type": "scatter",
                        "mode": "lines+markers",
                        "name": "success_rate",
                        "y": [item.get("summary", {}).get("success_rate") for item in sorted_runs],
                        "line": {"color": "#16a34a"},
                    },
                    {
                        "type": "scatter",
                        "mode": "lines+markers",
                        "name": "collision_rate",
                        "y": [item.get("summary", {}).get("collision_rate") for item in sorted_runs],
                        "line": {"color": "#dc2626"},
                    },
                    {
                        "type": "scatter",
                        "mode": "lines+markers",
                        "name": "out_of_bounds_rate",
                        "y": [item.get("summary", {}).get("out_of_bounds_rate") for item in sorted_runs],
                        "line": {"color": "#f59e0b"},
                    },
                ],
            )
        )
        charts.append(
            _build_series_chart(
                "Minimum Distance Trend",
                run_labels,
                [
                    {
                        "type": "scatter",
                        "mode": "lines+markers",
                        "name": "min_distance",
                        "y": [item.get("summary", {}).get("min_distance") for item in sorted_runs],
                        "line": {"color": "#7c3aed", "width": 3},
                    }
                ],
            )
        )
        charts.append(
            _build_series_chart(
                "Near-Violation Ratio Trend",
                run_labels,
                [
                    {
                        "type": "scatter",
                        "mode": "lines+markers",
                        "name": "near_violation_ratio",
                        "y": [item.get("summary", {}).get("near_violation_ratio") for item in sorted_runs],
                        "line": {"color": "#ea580c", "width": 3},
                    }
                ],
            )
        )

        done_type_keys = sorted({key for run in sorted_runs for key in dict(run.get("done_type_counts") or {}).keys()})
        if done_type_keys:
            charts.append(
                _build_bar_chart(
                    "Done Type Distribution",
                    run_labels,
                    [
                        {
                            "type": "bar",
                            "name": done_type,
                            "y": [dict(run.get("done_type_counts") or {}).get(done_type, 0) for run in sorted_runs],
                        }
                        for done_type in done_type_keys
                    ],
                    barmode="stack",
                )
            )

        if any(run.get("reward_components") for run in sorted_runs):
            charts.append(
                _build_bar_chart(
                    "Reward Components Breakdown",
                    run_labels,
                    [
                        {
                            "type": "bar",
                            "name": key,
                            "y": [dict(run.get("reward_components") or {}).get(key, 0.0) for run in sorted_runs],
                        }
                        for key in REWARD_COMPONENT_KEYS
                    ],
                    barmode="stack",
                )
            )

        family_groups: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
        for run in runs:
            family = str(run.get("scene_family") or run.get("scenario_type") or "unknown")
            family_groups[family].append(run)
        family_labels = sorted(family_groups.keys())
        if family_labels:
            charts.append(
                _build_bar_chart(
                    "Family Comparison",
                    family_labels,
                    [
                        {
                            "type": "bar",
                            "name": "success_rate",
                            "y": [_mean_or_none(item.get("summary", {}).get("success_rate") for item in family_groups[label]) for label in family_labels],
                        },
                        {
                            "type": "bar",
                            "name": "min_distance",
                            "y": [_mean_or_none(item.get("summary", {}).get("min_distance") for item in family_groups[label]) for label in family_labels],
                        },
                        {
                            "type": "bar",
                            "name": "near_violation_ratio",
                            "y": [_mean_or_none(item.get("summary", {}).get("near_violation_ratio") for item in family_groups[label]) for label in family_labels],
                        },
                    ],
                )
            )

    dynamic_bundles = [item for item in bundles if item.get("module") == "dynamic"]
    if dynamic_bundles:
        dynamic_bundles = sorted(dynamic_bundles, key=lambda item: item.get("mtime") or 0.0)[-12:]
        labels = [item.get("name", "") for item in dynamic_bundles]
        score_map: Dict[str, List[float | None]] = {key: [] for key in WITNESS_COLOR}
        for bundle in dynamic_bundles:
            primary = dict(bundle.get("primary") or {})
            witnesses = list(primary.get("witnesses") or [])
            bundle_scores = {}
            for witness in witnesses:
                if not isinstance(witness, dict):
                    continue
                witness_id = str(witness.get("witness_id", ""))
                bundle_scores[witness_id] = _to_float(witness.get("score"))
            for witness_id in score_map:
                score_map[witness_id].append(bundle_scores.get(witness_id))
        charts.append(
            _build_series_chart(
                "Witness Trend",
                labels,
                [
                    {
                        "type": "scatter",
                        "mode": "lines+markers",
                        "name": witness_id,
                        "y": score_map[witness_id],
                        "line": {"color": WITNESS_COLOR[witness_id], "width": 3},
                    }
                    for witness_id in score_map
                ],
            )
        )

    validation_bundles = [item for item in bundles if item.get("module") == "validation"]
    if validation_bundles:
        latest_validation = max(validation_bundles, key=lambda item: item.get("mtime") or 0.0)
        metric_deltas = dict(latest_validation.get("primary", {}).get("metric_deltas") or {})
        metric_keys = [key for key, value in metric_deltas.items() if _to_float(value) is not None]
        if metric_keys:
            charts.append(
                _build_bar_chart(
                    "Before/After Repair Delta",
                    metric_keys,
                    [
                        {
                            "type": "bar",
                            "name": latest_validation.get("name", "validation"),
                            "y": [metric_deltas[key] for key in metric_keys],
                            "marker": {"color": ["#16a34a" if float(metric_deltas[key]) >= 0 else "#dc2626" for key in metric_keys]},
                        }
                    ],
                )
            )

    charts.extend(_wandb_chart_specs(watch_roots))
    return charts


def build_dashboard_state(
    *,
    logs_root: str | Path = DEFAULT_LOGS_ROOT,
    reports_root: str | Path = DEFAULT_REPORTS_ROOT,
    watch_roots: Sequence[str | Path] | None = None,
    include_default_watch_roots: bool = True,
) -> Dict[str, Any]:
    resolved_watch_roots = _discover_default_watch_roots(
        watch_roots,
        include_defaults=include_default_watch_roots,
    )
    runs = discover_run_snapshots(logs_root, resolved_watch_roots)
    bundles = discover_bundle_snapshots(reports_root, resolved_watch_roots)
    workspaces = discover_workspace_snapshots(resolved_watch_roots)
    active = _infer_active_context(runs, bundles, workspaces)
    flow_nodes = build_flow_nodes(runs, bundles, workspaces)
    return {
        "generated_at": _utc_now().isoformat(),
        "overview": build_overview(active, flow_nodes, runs, bundles),
        "active": active,
        "flow_nodes": flow_nodes,
        "kpis": build_kpis(runs, bundles),
        "events": build_recent_events(runs, bundles, workspaces),
        "charts": build_chart_specs(runs, bundles, resolved_watch_roots),
        "runs": list(reversed(sorted(runs, key=lambda item: item.get("mtime") or 0.0)[-10:])),
        "bundles": list(reversed(sorted(bundles, key=lambda item: item.get("mtime") or 0.0)[-10:])),
        "workspaces": list(reversed(sorted(workspaces, key=lambda item: item.get("mtime") or 0.0)[-10:])),
        "watch_roots": [str(path) for path in resolved_watch_roots],
    }


__all__ = [
    "build_dashboard_state",
    "DEFAULT_LOGS_ROOT",
    "DEFAULT_REPORTS_ROOT",
    "FLOW_ORDER",
    "FLOW_LABELS",
    "FLOW_PHASES",
]
