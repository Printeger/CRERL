"""Phase 9 validation runner and namespaced validation bundle writer."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Sequence

from analyzers.report_contract import (
    DEFAULT_REPORT_NAMESPACES,
    VALIDATION_GENERATION_MODE,
    resolve_report_namespace_root,
    write_namespace_manifest,
    write_report_namespace_contract,
)
from runtime_logging.episode_writer import (
    discover_accepted_run_directories,
    load_run_directories,
)

from repair.rerun_adapters import (
    REPO_ROOT,
    SCENE_CFG_BY_FAMILY,
    adjust_summary_for_bounded_rerun,
    build_bounded_rerun_task,
    infer_run_scene,
    infer_run_source,
    normalize_execution_mode,
)
from repair.validation_request_loader import load_validation_request_bundle


VALIDATION_NAMESPACE = DEFAULT_REPORT_NAMESPACES[VALIDATION_GENERATION_MODE]


def _invoke_subprocess_command(
    command: Sequence[str],
    *,
    cwd: str | Path,
    env: Mapping[str, str],
    timeout_sec: int = 600,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=str(cwd),
        env=dict(env),
        text=True,
        capture_output=True,
        timeout=int(timeout_sec),
        check=False,
    )


def build_validation_rerun_tasks(
    *,
    validation_input: Mapping[str, Any],
    original_runs: Sequence[Mapping[str, Any]],
    repaired_logs_root: str | Path | None = None,
) -> list[Dict[str, Any]]:
    """Build deterministic Phase 9 rerun tasks from original evidence."""

    repair_bundle_name = str(validation_input.get("repair_bundle_name", "repair_latest"))
    tasks: list[Dict[str, Any]] = []

    if original_runs:
        for index, run_payload in enumerate(original_runs):
            source = infer_run_source(run_payload)
            execution_mode = normalize_execution_mode(source)
            scenario_type, scene_cfg_name = infer_run_scene(run_payload)
            if not scenario_type:
                scenario_type = str((validation_input.get("scene_family_scope") or ["nominal"])[0])
            if not scene_cfg_name:
                scene_cfg_name = SCENE_CFG_BY_FAMILY.get(scenario_type, f"scene_cfg_{scenario_type}.yaml")
            output_run_name = f"{repair_bundle_name}_{execution_mode}_{scenario_type}_{index:02d}"
            tasks.append(
                build_bounded_rerun_task(
                    validation_input=validation_input,
                    original_run_payload=run_payload,
                    execution_mode=execution_mode,
                    scenario_type=scenario_type,
                    scene_cfg_name=scene_cfg_name,
                    output_run_name=output_run_name,
                    repaired_logs_root=repaired_logs_root,
                    index=index,
                )
            )
        return tasks

    for execution_mode in validation_input.get("preferred_execution_modes", []) or ["baseline"]:
        for index, scenario_type in enumerate(validation_input.get("scene_family_scope", []) or ["nominal"]):
            tasks.append(
                build_bounded_rerun_task(
                    validation_input=validation_input,
                    original_run_payload=None,
                    execution_mode=str(execution_mode),
                    scenario_type=str(scenario_type),
                    scene_cfg_name=SCENE_CFG_BY_FAMILY.get(str(scenario_type), f"scene_cfg_{scenario_type}.yaml"),
                    output_run_name=f"{repair_bundle_name}_{execution_mode}_{scenario_type}_{index:02d}",
                    repaired_logs_root=repaired_logs_root,
                    index=index,
                )
            )
    return tasks


def _write_preview_repaired_run(
    run_dir: Path,
    *,
    run_name: str,
    source: str,
    scenario_type: str,
    scene_cfg_name: str,
    summary: Mapping[str, Any],
) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "episodes").mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_id": run_name,
        "source": source,
        "generated_by": "phase9_preview_targeted_rerun.v1",
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (run_dir / "summary.json").write_text(json.dumps(dict(summary), indent=2, sort_keys=True), encoding="utf-8")
    (run_dir / "acceptance.json").write_text(
        json.dumps({"passed": True, "max_severity": "info"}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    episode_row = {
        "episode_index": 0,
        "seed": 0,
        "scene_id": f"{run_name}:scene0",
        "scenario_type": scenario_type,
        "scene_cfg_name": scene_cfg_name,
        "num_steps": 1,
        "trajectory_length": 1.0,
        "return_total": float(dict(summary).get("average_return", 0.0)),
        "reward_components_total": {},
        "success_flag": bool(dict(summary).get("success_rate", 0.0) > 0.0),
        "collision_flag": bool(dict(summary).get("collision_rate", 0.0) > 0.0),
        "out_of_bounds_flag": False,
        "min_obstacle_distance": float(dict(summary).get("min_distance", 0.0)),
        "near_violation_steps": 0,
        "near_violation_ratio": float(dict(summary).get("near_violation_ratio", 0.0)),
        "final_goal_distance": 0.0,
        "done_type": "success" if dict(summary).get("success_rate", 0.0) > 0 else "unknown",
        "source": source,
    }
    (run_dir / "episodes.jsonl").write_text(json.dumps(episode_row) + "\n", encoding="utf-8")
    (run_dir / "steps.jsonl").write_text("", encoding="utf-8")
    (run_dir / "episodes" / "episode_0000.json").write_text(
        json.dumps({"summary": episode_row}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return run_dir


def preview_rerun_runner(
    task: Mapping[str, Any],
    *,
    validation_input: Mapping[str, Any],
    original_run_payload: Mapping[str, Any] | None,
    rerun_logs_root: str | Path,
) -> Dict[str, Any]:
    """Deterministic preview-mode targeted rerun used for bounded Phase 9 tests.

    This does not mutate source files or invoke Isaac. It materializes a repaired
    accepted-run directory derived from the original accepted evidence and the
    repair request scope, giving Phase 9 a stable post-repair evidence object.
    """

    run_root = Path(rerun_logs_root)
    run_root.mkdir(parents=True, exist_ok=True)
    output_run_name = str(task.get("output_run_name", "validation_rerun"))
    scenario_type = str(task.get("scenario_type", "nominal"))
    source = str(task.get("source", task.get("execution_mode", "baseline")))
    scene_cfg_name = str(task.get("scene_cfg_name", SCENE_CFG_BY_FAMILY.get(scenario_type, "")))
    original_summary = dict((original_run_payload or {}).get("summary") or {})
    adjusted_summary = adjust_summary_for_bounded_rerun(
        original_summary,
        validation_input=validation_input,
        execution_mode=normalize_execution_mode(str(task.get("execution_mode", source))),
        scenario_type=scenario_type,
    )
    run_dir = _write_preview_repaired_run(
        run_root / output_run_name,
        run_name=output_run_name,
        source=source,
        scenario_type=scenario_type,
        scene_cfg_name=scene_cfg_name,
        summary=adjusted_summary,
    )
    return {
        "task_id": str(task.get("task_id", "")),
        "runner_mode": "preview_targeted_rerun.v1",
        "status": "completed",
        "run_dir": str(run_dir),
        "run_id": output_run_name,
        "scenario_type": scenario_type,
        "scene_cfg_name": scene_cfg_name,
        "source": source,
    }


def bounded_subprocess_rerun_runner(
    task: Mapping[str, Any],
    *,
    validation_input: Mapping[str, Any],
    original_run_payload: Mapping[str, Any] | None,
    rerun_logs_root: str | Path,
    allow_fallback: bool = False,
) -> Dict[str, Any]:
    """Attempt a bounded real execution subprocess rerun for Phase 9."""

    command = [str(item) for item in list(task.get("command_preview", []) or [])]
    if not command:
        if allow_fallback:
            fallback = preview_rerun_runner(
                task,
                validation_input=validation_input,
                original_run_payload=original_run_payload,
                rerun_logs_root=rerun_logs_root,
            )
            return {
                **fallback,
                "runner_mode": "bounded_subprocess_rerun.v1",
                "fallback_used": True,
                "fallback_runner_mode": "preview_targeted_rerun.v1",
                "status": "completed_with_preview_fallback",
                "subprocess_returncode": None,
            }
        return {
            "task_id": str(task.get("task_id", "")),
            "runner_mode": "bounded_subprocess_rerun.v1",
            "status": "failed_no_command",
            "fallback_used": False,
        }

    subprocess_env = dict(os.environ)
    subprocess_env.update({str(k): str(v) for k, v in dict(task.get("env_overrides") or {}).items()})
    cwd = Path(str(task.get("repo_root", REPO_ROOT)))
    expected_run_dir = Path(str(task.get("expected_run_dir", ""))) if str(task.get("expected_run_dir", "")) else None

    result = _invoke_subprocess_command(
        command,
        cwd=cwd,
        env=subprocess_env,
    )
    if result.returncode == 0 and expected_run_dir is not None and expected_run_dir.exists():
        return {
            "task_id": str(task.get("task_id", "")),
            "runner_mode": "bounded_subprocess_rerun.v1",
            "status": "completed",
            "run_dir": str(expected_run_dir),
            "run_id": str(task.get("output_run_name", expected_run_dir.name)),
            "scenario_type": str(task.get("scenario_type", "")),
            "scene_cfg_name": str(task.get("scene_cfg_name", "")),
            "source": str(task.get("source", task.get("execution_mode", ""))),
            "fallback_used": False,
            "subprocess_returncode": int(result.returncode),
            "stdout_tail": result.stdout[-1000:],
            "stderr_tail": result.stderr[-1000:],
        }

    if allow_fallback:
        fallback = preview_rerun_runner(
            task,
            validation_input=validation_input,
            original_run_payload=original_run_payload,
            rerun_logs_root=rerun_logs_root,
        )
        return {
            **fallback,
            "runner_mode": "bounded_subprocess_rerun.v1",
            "fallback_used": True,
            "fallback_runner_mode": "preview_targeted_rerun.v1",
            "status": "completed_with_preview_fallback",
            "subprocess_returncode": int(result.returncode),
            "stdout_tail": result.stdout[-1000:],
            "stderr_tail": result.stderr[-1000:],
        }

    return {
        "task_id": str(task.get("task_id", "")),
        "runner_mode": "bounded_subprocess_rerun.v1",
        "status": "failed_subprocess",
        "run_dir": str(expected_run_dir) if expected_run_dir is not None else "",
        "run_id": str(task.get("output_run_name", "")),
        "scenario_type": str(task.get("scenario_type", "")),
        "scene_cfg_name": str(task.get("scene_cfg_name", "")),
        "source": str(task.get("source", task.get("execution_mode", ""))),
        "fallback_used": False,
        "subprocess_returncode": int(result.returncode),
        "stdout_tail": result.stdout[-1000:],
        "stderr_tail": result.stderr[-1000:],
    }


def _resolve_rerun_runner(
    rerun_mode: str,
    rerun_runner: Callable[..., Mapping[str, Any]] | None = None,
) -> Callable[..., Mapping[str, Any]]:
    if rerun_runner is not None:
        return rerun_runner
    normalized = str(rerun_mode or "preview").lower()
    if normalized == "preview":
        return preview_rerun_runner
    if normalized == "subprocess":
        return lambda task, **kwargs: bounded_subprocess_rerun_runner(
            task,
            allow_fallback=False,
            **kwargs,
        )
    if normalized == "auto":
        return lambda task, **kwargs: bounded_subprocess_rerun_runner(
            task,
            allow_fallback=True,
            **kwargs,
        )
    raise ValueError(f"Unsupported rerun_mode '{rerun_mode}'.")


def trigger_targeted_reruns(
    *,
    validation_input: Mapping[str, Any],
    rerun_tasks: Sequence[Mapping[str, Any]],
    original_runs: Sequence[Mapping[str, Any]],
    rerun_logs_root: str | Path,
    rerun_mode: str = "preview",
    rerun_runner: Callable[..., Mapping[str, Any]] | None = None,
) -> Dict[str, Any]:
    """Execute targeted rerun tasks and return repaired run references."""

    runner = _resolve_rerun_runner(rerun_mode, rerun_runner)
    original_by_dir = {str(item.get("run_dir", "")): item for item in original_runs}
    task_results: list[Dict[str, Any]] = []
    repaired_run_dirs: list[str] = []

    for task in rerun_tasks:
        original_payload = original_by_dir.get(str(task.get("original_run_dir", "")))
        result = dict(
            runner(
                task,
                validation_input=validation_input,
                original_run_payload=original_payload,
                rerun_logs_root=rerun_logs_root,
            )
            or {}
        )
        task_results.append(result)
        run_dir = str(result.get("run_dir", "") or "")
        if run_dir:
            repaired_run_dirs.append(str(Path(run_dir)))

    return {
        "rerun_type": "phase9_targeted_rerun_results.v1",
        "requested_rerun_mode": str(rerun_mode),
        "rerun_logs_root": str(rerun_logs_root),
        "task_results": task_results,
        "repaired_run_dirs": repaired_run_dirs,
    }


def _build_validation_plan(
    validation_input: Mapping[str, Any],
    *,
    logs_root: str | Path | None = None,
    original_run_dirs: Sequence[str | Path] = (),
    repaired_run_dirs: Sequence[str | Path] = (),
) -> Dict[str, Any]:
    return {
        "plan_type": "phase9_validation_plan.v1",
        "repair_bundle_name": str(validation_input.get("repair_bundle_name", "")),
        "repair_bundle_dir": str(validation_input.get("repair_bundle_dir", "")),
        "phase9_entrypoint": str(validation_input.get("phase9_entrypoint", "")),
        "primary_claim_type": str(validation_input.get("primary_claim_type", "")),
        "preferred_execution_modes": list(validation_input.get("preferred_execution_modes", []) or []),
        "scene_family_scope": list(validation_input.get("scene_family_scope", []) or []),
        "validation_targets": list(validation_input.get("validation_targets", []) or []),
        "comparison_mode": str(validation_input.get("validation_request", {}).get("comparison_mode", "")),
        "logs_root": str(logs_root) if logs_root is not None else "",
        "original_run_dirs": [str(item) for item in original_run_dirs],
        "repaired_run_dirs": [str(item) for item in repaired_run_dirs],
    }


def prepare_validation_runs(
    *,
    repair_bundle_dir: str | Path,
    logs_root: str | Path | None = None,
    original_run_dirs: Sequence[str | Path] = (),
    repaired_run_dirs: Sequence[str | Path] = (),
    trigger_rerun: bool = False,
    rerun_mode: str = "preview",
    rerun_runner: Callable[..., Mapping[str, Any]] | None = None,
    repaired_logs_root: str | Path | None = None,
) -> Dict[str, Any]:
    """Prepare Phase 9 validation inputs and accepted-run references."""

    validation_input = load_validation_request_bundle(repair_bundle_dir, require_phase9_ready=False)
    resolved_original_dirs = [Path(item) for item in original_run_dirs]
    resolved_repaired_dirs = [Path(item) for item in repaired_run_dirs]

    discovery_used = False
    if not resolved_original_dirs and logs_root is not None:
        discovery_used = True
        discovered_original_dirs = discover_accepted_run_directories(
            logs_root,
            scenario_types=validation_input.get("scene_family_scope", []),
            require_passed=True,
        )
        discovered_original_runs = (
            load_run_directories(discovered_original_dirs, require_passed=True)
            if discovered_original_dirs
            else []
        )
        preferred_modes = {
            str(item)
            for item in (validation_input.get("preferred_execution_modes", []) or [])
            if str(item)
        }
        if preferred_modes:
            discovered_original_runs = [
                item
                for item in discovered_original_runs
                if normalize_execution_mode(infer_run_source(item)) in preferred_modes
            ]
        resolved_original_dirs = [Path(item.get("run_dir", "")) for item in discovered_original_runs]

    original_runs = load_run_directories(resolved_original_dirs, require_passed=True) if resolved_original_dirs else []
    rerun_tasks: list[Dict[str, Any]] = []
    triggered_rerun_results: Dict[str, Any] | None = None
    if trigger_rerun and not resolved_repaired_dirs:
        rerun_root = Path(repaired_logs_root) if repaired_logs_root is not None else (Path(logs_root) if logs_root is not None else Path(repair_bundle_dir).parent / "repaired_runs")
        rerun_tasks = build_validation_rerun_tasks(
            validation_input=validation_input,
            original_runs=original_runs,
            repaired_logs_root=rerun_root,
        )
        triggered_rerun_results = trigger_targeted_reruns(
            validation_input=validation_input,
            rerun_tasks=rerun_tasks,
            original_runs=original_runs,
            rerun_logs_root=rerun_root,
            rerun_mode=rerun_mode,
            rerun_runner=rerun_runner,
        )
        resolved_repaired_dirs = list(triggered_rerun_results.get("repaired_run_dirs", []) or [])

    repaired_runs = load_run_directories(resolved_repaired_dirs, require_passed=True) if resolved_repaired_dirs else []

    validation_plan = _build_validation_plan(
        validation_input,
        logs_root=logs_root,
        original_run_dirs=resolved_original_dirs,
        repaired_run_dirs=resolved_repaired_dirs,
    )
    validation_runs = {
        "runs_type": "phase9_validation_runs.v1",
        "discovery_used": discovery_used,
        "trigger_rerun": bool(trigger_rerun),
        "requested_rerun_mode": str(rerun_mode),
        "rerun_tasks": rerun_tasks,
        "triggered_rerun_results": dict(triggered_rerun_results or {}),
        "original_runs": [
            {
                "run_dir": str(item.get("run_dir", "")),
                "run_id": str(item.get("run_id", "")),
                "source": str((item.get("manifest") or {}).get("source", "")),
                "scenario_type": infer_run_scene(item)[0],
                "scene_cfg_name": infer_run_scene(item)[1],
                "summary": dict(item.get("summary") or {}),
                "acceptance": dict(item.get("acceptance") or {}),
            }
            for item in original_runs
        ],
        "repaired_runs": [
            {
                "run_dir": str(item.get("run_dir", "")),
                "run_id": str(item.get("run_id", "")),
                "source": str((item.get("manifest") or {}).get("source", "")),
                "scenario_type": infer_run_scene(item)[0],
                "scene_cfg_name": infer_run_scene(item)[1],
                "summary": dict(item.get("summary") or {}),
                "acceptance": dict(item.get("acceptance") or {}),
            }
            for item in repaired_runs
        ],
    }
    return {
        "validation_input": validation_input,
        "validation_plan": validation_plan,
        "validation_runs": validation_runs,
        "original_runs": original_runs,
        "repaired_runs": repaired_runs,
    }


def _build_validation_summary_payload(
    *,
    validation_plan: Mapping[str, Any],
    comparison: Mapping[str, Any],
    decision: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "bundle_type": "validation_bundle.v1",
        "validation_plan_type": str(validation_plan.get("plan_type", "")),
        "primary_claim_type": str(validation_plan.get("primary_claim_type", "")),
        "decision_status": str(decision.get("decision_status", "")),
        "accepted": bool(decision.get("accepted", False)),
        "original_run_count": int(comparison.get("original_run_count", 0) or 0),
        "repaired_run_count": int(comparison.get("repaired_run_count", 0) or 0),
        "blocked_by": list(decision.get("blocked_by", []) or []),
    }


def _build_post_repair_evidence(
    *,
    validation_plan: Mapping[str, Any],
    validation_runs: Mapping[str, Any],
    comparison: Mapping[str, Any],
    decision: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "evidence_type": "phase10_post_repair_evidence.v1",
        "repair_bundle_name": str(validation_plan.get("repair_bundle_name", "")),
        "primary_claim_type": str(validation_plan.get("primary_claim_type", "")),
        "comparison_mode": str(validation_plan.get("comparison_mode", "")),
        "validation_targets": list(validation_plan.get("validation_targets", []) or []),
        "decision_status": str(decision.get("decision_status", "")),
        "accepted": bool(decision.get("accepted", False)),
        "phase10_ready": bool(decision.get("decision_status", "")) in {"accepted", "rejected"},
        "evidence_schema_version": "phase10_post_repair_evidence.v2",
        "original_run_refs": [
            {
                "run_dir": str(item.get("run_dir", "")),
                "run_id": str(item.get("run_id", "")),
                "source": str(item.get("source", "")),
                "scenario_type": str(item.get("scenario_type", "")),
                "scene_cfg_name": str(item.get("scene_cfg_name", "")),
            }
            for item in list(validation_runs.get("original_runs", []) or [])
        ],
        "repaired_run_refs": [
            {
                "run_dir": str(item.get("run_dir", "")),
                "run_id": str(item.get("run_id", "")),
                "source": str(item.get("source", "")),
                "scenario_type": str(item.get("scenario_type", "")),
                "scene_cfg_name": str(item.get("scene_cfg_name", "")),
            }
            for item in list(validation_runs.get("repaired_runs", []) or [])
        ],
        "rerun_tasks": list(validation_runs.get("rerun_tasks", []) or []),
        "triggered_rerun_results": dict(validation_runs.get("triggered_rerun_results", {}) or {}),
        "metric_deltas": dict(comparison.get("metric_deltas", {}) or {}),
        "original_by_scenario": dict(comparison.get("original_by_scenario", {}) or {}),
        "repaired_by_scenario": dict(comparison.get("repaired_by_scenario", {}) or {}),
        "blocked_by": list(decision.get("blocked_by", []) or []),
        "requested_rerun_mode": str(validation_runs.get("requested_rerun_mode", "")),
        "consumer_contract": {
            "contract_type": "phase10_post_repair_evidence_consumer.v2",
            "phase10_entrypoint": "post_repair_validation_consumer.v1",
            "required_top_level_fields": [
                "primary_claim_type",
                "decision_status",
                "accepted",
                "metric_deltas",
                "original_run_refs",
                "repaired_run_refs",
                "rerun_tasks",
                "triggered_rerun_results",
            ],
            "required_metric_delta_fields": [
                "metric_name",
                "category",
                "direction",
                "original",
                "repaired",
                "delta_raw",
                "improvement",
            ],
            "required_run_ref_fields": [
                "run_dir",
                "run_id",
                "source",
                "scenario_type",
                "scene_cfg_name",
            ],
            "required_rerun_task_fields": [
                "task_id",
                "execution_mode",
                "adapter_type",
                "supports_real_execution",
                "fallback_runner_mode",
                "script_path",
                "hydra_overrides",
                "command_preview",
                "bounded_limits",
            ],
            "required_triggered_result_fields": [
                "task_id",
                "runner_mode",
                "status",
                "run_dir",
                "run_id",
                "scenario_type",
                "scene_cfg_name",
                "source",
            ],
            "consumer_expectations": {
                "post_repair_bundle_is_namespaced": True,
                "decision_must_be_machine_readable": True,
                "scenario_conditioned_summaries_required": True,
                "bounded_rerun_adapter_metadata_required": True,
            },
        },
    }


def _build_validation_summary_markdown(
    *,
    validation_plan: Mapping[str, Any],
    comparison: Mapping[str, Any],
    decision: Mapping[str, Any],
) -> str:
    lines = [
        "# Validation Summary",
        "",
        f"- Repair bundle: `{validation_plan.get('repair_bundle_name', '')}`",
        f"- Primary claim type: `{validation_plan.get('primary_claim_type', '')}`",
        f"- Decision: `{decision.get('decision_status', '')}`",
        f"- Accepted: `{bool(decision.get('accepted', False))}`",
        f"- Original runs: `{comparison.get('original_run_count', 0)}`",
        f"- Repaired runs: `{comparison.get('repaired_run_count', 0)}`",
        "",
        "## Metric Deltas",
        "",
    ]
    metric_deltas = dict(comparison.get("metric_deltas") or {})
    if metric_deltas:
        for metric_name, payload in metric_deltas.items():
            lines.append(
                f"- `{metric_name}`:"
                f" original=`{payload.get('original', '')}`"
                f" repaired=`{payload.get('repaired', '')}`"
                f" improvement=`{payload.get('improvement', '')}`"
            )
    else:
        lines.append("- No metric deltas available.")
    lines.extend(
        [
            "",
            "## Decision Rationale",
            "",
            str(decision.get("decision_rationale", "")) or "No rationale recorded.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def write_validation_bundle(
    *,
    validation_plan: Mapping[str, Any],
    validation_runs: Mapping[str, Any],
    comparison: Mapping[str, Any],
    decision: Mapping[str, Any],
    validation_dir: str | Path,
    namespace_root: str | Path | None = None,
    bundle_name: str = "validation_latest",
    namespace: str = VALIDATION_NAMESPACE,
) -> Dict[str, Path]:
    validation_path = Path(validation_dir)
    validation_path.mkdir(parents=True, exist_ok=True)

    validation_plan_path = validation_path / "validation_plan.json"
    validation_runs_path = validation_path / "validation_runs.json"
    comparison_path = validation_path / "comparison.json"
    validation_decision_path = validation_path / "validation_decision.json"
    validation_summary_path = validation_path / "validation_summary.json"
    validation_summary_md_path = validation_path / "validation_summary.md"
    post_repair_evidence_path = validation_path / "post_repair_evidence.json"
    manifest_path = validation_path / "manifest.json"

    validation_plan_path.write_text(json.dumps(dict(validation_plan), indent=2, sort_keys=True), encoding="utf-8")
    validation_runs_path.write_text(json.dumps(dict(validation_runs), indent=2, sort_keys=True), encoding="utf-8")
    comparison_path.write_text(json.dumps(dict(comparison), indent=2, sort_keys=True), encoding="utf-8")
    validation_decision_path.write_text(json.dumps(dict(decision), indent=2, sort_keys=True), encoding="utf-8")
    summary_payload = _build_validation_summary_payload(
        validation_plan=validation_plan,
        comparison=comparison,
        decision=decision,
    )
    validation_summary_path.write_text(json.dumps(summary_payload, indent=2, sort_keys=True), encoding="utf-8")
    post_repair_evidence_payload = _build_post_repair_evidence(
        validation_plan=validation_plan,
        validation_runs=validation_runs,
        comparison=comparison,
        decision=decision,
    )
    post_repair_evidence_path.write_text(
        json.dumps(post_repair_evidence_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    validation_summary_md_path.write_text(
        _build_validation_summary_markdown(
            validation_plan=validation_plan,
            comparison=comparison,
            decision=decision,
        ),
        encoding="utf-8",
    )
    manifest_payload = {
        "bundle_type": "validation_bundle.v1",
        "namespace": namespace,
        "repair_bundle_name": str(validation_plan.get("repair_bundle_name", "")),
        "validation_plan_path": validation_plan_path.name,
        "validation_runs_path": validation_runs_path.name,
        "comparison_path": comparison_path.name,
        "validation_decision_path": validation_decision_path.name,
        "validation_summary_path": validation_summary_path.name,
        "validation_summary_md_path": validation_summary_md_path.name,
        "post_repair_evidence_path": post_repair_evidence_path.name,
        "accepted": bool(decision.get("accepted", False)),
        "decision_status": str(decision.get("decision_status", "")),
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True), encoding="utf-8")

    bundle_paths: Dict[str, Path] = {
        "report_dir": validation_path,
        "validation_dir": validation_path,
        "validation_plan_path": validation_plan_path,
        "validation_runs_path": validation_runs_path,
        "comparison_path": comparison_path,
        "validation_decision_path": validation_decision_path,
        "validation_summary_path": validation_summary_path,
        "validation_summary_md_path": validation_summary_md_path,
        "post_repair_evidence_path": post_repair_evidence_path,
        "manifest_path": manifest_path,
        "summary_path": validation_summary_path,
    }
    if namespace_root is not None:
        bundle_paths["namespace_manifest_path"] = write_namespace_manifest(
            namespace_root,
            bundle_name=bundle_name,
            report_mode=VALIDATION_GENERATION_MODE,
            namespace=namespace,
            bundle_paths=bundle_paths,
            report_summary={
                "accepted": bool(decision.get("accepted", False)),
                "decision_status": str(decision.get("decision_status", "")),
                "primary_claim_type": str(validation_plan.get("primary_claim_type", "")),
            },
        )
    return bundle_paths


def run_validation_bundle_write(
    *,
    validation_plan: Mapping[str, Any],
    validation_runs: Mapping[str, Any],
    comparison: Mapping[str, Any],
    decision: Mapping[str, Any],
    reports_root: str | Path | None = None,
    bundle_name: str = "validation_latest",
    validation_dir: str | Path | None = None,
    namespaces: Mapping[str, str] | None = None,
    report_mode_artifacts: Mapping[str, Any] | None = None,
) -> Dict[str, Path]:
    namespace = str((namespaces or DEFAULT_REPORT_NAMESPACES).get(VALIDATION_GENERATION_MODE, VALIDATION_NAMESPACE))
    namespace_root = None
    if validation_dir is None:
        if reports_root is None:
            reports_root = Path(__file__).resolve().parents[1] / "reports"
        namespace_root = resolve_report_namespace_root(reports_root, VALIDATION_GENERATION_MODE, namespaces=namespaces)
        validation_dir = namespace_root / str(bundle_name)
    bundle_paths = write_validation_bundle(
        validation_plan=validation_plan,
        validation_runs=validation_runs,
        comparison=comparison,
        decision=decision,
        validation_dir=validation_dir,
        namespace_root=namespace_root,
        bundle_name=str(bundle_name),
        namespace=namespace,
    )
    if reports_root is not None:
        bundle_paths["namespace_contract_path"] = write_report_namespace_contract(
            reports_root,
            namespaces=namespaces,
            report_mode_artifacts=report_mode_artifacts,
        )
    return bundle_paths


__all__ = [
    "VALIDATION_NAMESPACE",
    "build_validation_rerun_tasks",
    "bounded_subprocess_rerun_runner",
    "prepare_validation_runs",
    "preview_rerun_runner",
    "run_validation_bundle_write",
    "trigger_targeted_reruns",
    "write_validation_bundle",
]
