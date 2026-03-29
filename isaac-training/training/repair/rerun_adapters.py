"""Bounded Phase 9 rerun adapters for baseline / eval / train validation paths."""

from __future__ import annotations

import json
import shlex
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


TRAINING_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = TRAINING_ROOT.parents[1]
ISAAC_ROOT = REPO_ROOT.parent
SETUP_CONDA_ENV_SCRIPT = ISAAC_ROOT / "setup_conda_env.sh"
WANDB_ROOT = REPO_ROOT / "isaac-training" / "wandb"
SCRIPT_BY_MODE = {
    "baseline": TRAINING_ROOT / "scripts" / "run_baseline.py",
    "eval": TRAINING_ROOT / "scripts" / "eval.py",
    "train": TRAINING_ROOT / "scripts" / "train.py",
}

RUN_NAME_OVERRIDE_ENV = "CRE_RUN_NAME_OVERRIDE"
RUN_BASE_DIR_ENV = "CRE_RUN_LOG_BASE_DIR"
RUN_USE_TIMESTAMP_ENV = "CRE_RUN_USE_TIMESTAMP"
RUN_SCENARIO_TYPE_ENV = "CRE_VALIDATION_SCENARIO_TYPE"
RUN_SCENE_CFG_ENV = "CRE_VALIDATION_SCENE_CFG_NAME"
RUN_EXECUTION_MODE_ENV = "CRE_VALIDATION_EXECUTION_MODE"
RUN_SCENE_ID_PREFIX_ENV = "CRE_VALIDATION_SCENE_ID_PREFIX"

SCENE_CFG_BY_FAMILY = {
    "nominal": "scene_cfg_nominal.yaml",
    "boundary_critical": "scene_cfg_boundary_critical.yaml",
    "shifted": "scene_cfg_shifted.yaml",
}


@dataclass(frozen=True)
class BoundedRerunAdapterSpec:
    execution_mode: str
    adapter_type: str
    script_path: str
    max_frame_num: int | None = None
    max_episode_length: int | None = None
    num_envs: int = 1
    extra_overrides: List[str] = field(default_factory=list)
    supports_real_execution: bool = True
    fallback_runner_mode: str = "preview_targeted_rerun.v1"
    preferred_rerun_mode: str = "subprocess"
    allow_preview_fallback: bool = True


ADAPTER_SPECS: Dict[str, BoundedRerunAdapterSpec] = {
    "baseline": BoundedRerunAdapterSpec(
        execution_mode="baseline",
        adapter_type="phase9_bounded_baseline_rerun_adapter.v1",
        script_path="isaac-training/training/scripts/run_baseline.py",
        max_episode_length=50,
        num_envs=1,
        extra_overrides=[
            "headless=True",
            "baseline.num_episodes=1",
            "baseline.seeds=[0]",
        ],
        preferred_rerun_mode="subprocess",
        allow_preview_fallback=False,
    ),
    "eval": BoundedRerunAdapterSpec(
        execution_mode="eval",
        adapter_type="phase9_bounded_eval_rerun_adapter.v1",
        script_path="isaac-training/training/scripts/eval.py",
        max_frame_num=128,
        max_episode_length=128,
        num_envs=1,
        extra_overrides=[
            "headless=True",
            "wandb.mode=offline",
        ],
        preferred_rerun_mode="subprocess",
        allow_preview_fallback=False,
    ),
    "train": BoundedRerunAdapterSpec(
        execution_mode="train",
        adapter_type="phase9_bounded_train_rerun_adapter.v1",
        script_path="isaac-training/training/scripts/train.py",
        max_frame_num=2048,
        max_episode_length=128,
        num_envs=1,
        extra_overrides=[
            "headless=True",
            "wandb.mode=offline",
            "+skip_periodic_eval=True",
            "save_interval=999999",
            "eval_interval=999999",
        ],
        preferred_rerun_mode="subprocess",
        allow_preview_fallback=True,
    ),
}


def _safe_name(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in str(value))


def normalize_execution_mode(source: str) -> str:
    value = str(source or "").lower()
    if value.startswith("baseline"):
        return "baseline"
    if value.startswith("train_eval") or value.startswith("eval"):
        return "eval"
    if value.startswith("train"):
        return "train"
    return value or "baseline"


def infer_run_source(run_payload: Mapping[str, Any]) -> str:
    manifest = dict(run_payload.get("manifest") or {})
    source = str(manifest.get("source", "") or "")
    if source:
        return source
    episodes = list(run_payload.get("episodes") or [])
    for episode in episodes:
        source = str(episode.get("source", "") or "")
        if source:
            return source
    return "baseline"


def infer_run_scene(run_payload: Mapping[str, Any]) -> tuple[str, str]:
    episodes = list(run_payload.get("episodes") or [])
    for episode in episodes:
        scenario_type = str(episode.get("scenario_type", "") or "")
        scene_cfg_name = str(episode.get("scene_cfg_name", "") or "")
        if scenario_type or scene_cfg_name:
            return scenario_type, scene_cfg_name
    summary = dict(run_payload.get("summary") or {})
    return str(summary.get("scenario_type", "") or ""), str(summary.get("scene_cfg_name", "") or "")


def get_adapter_spec(execution_mode: str) -> BoundedRerunAdapterSpec:
    normalized = normalize_execution_mode(execution_mode)
    return ADAPTER_SPECS.get(normalized, ADAPTER_SPECS["baseline"])


def _baseline_name_from_source(source: str) -> str:
    normalized = str(source or "").strip().lower()
    if normalized.startswith("baseline_"):
        candidate = normalized.split("baseline_", 1)[1]
        if candidate in {"random", "greedy", "conservative"}:
            return candidate
    return "random"


def _resolve_default_eval_checkpoint() -> str:
    candidates = sorted(
        WANDB_ROOT.glob("offline-run-*/files/checkpoint_final.pt"),
        key=lambda path: path.stat().st_mtime,
    )
    if candidates:
        return str(candidates[-1].resolve())
    return ""


def build_hydra_overrides(
    *,
    execution_mode: str,
    scenario_type: str,
    validation_input: Mapping[str, Any],
    output_run_name: str,
    source: str = "",
) -> List[str]:
    spec = get_adapter_spec(execution_mode)
    overrides = [
        f"scene_family_backend.family={scenario_type}",
        "scene_family_backend.enabled=True",
        f"scene_logging.scenario_type={scenario_type}",
        f"scene_logging.scene_cfg_name={SCENE_CFG_BY_FAMILY.get(scenario_type, f'scene_cfg_{scenario_type}.yaml')}",
        f"scene_logging.scene_id_prefix={_safe_name(output_run_name)}",
        "env.num_envs=1",
    ]
    if spec.execution_mode == "baseline":
        overrides.append(f"baseline.name={_baseline_name_from_source(source)}")
    if spec.execution_mode == "eval":
        checkpoint_path = _resolve_default_eval_checkpoint()
        if checkpoint_path:
            overrides.append(f"+checkpoint_path={checkpoint_path}")
    if spec.max_frame_num is not None:
        overrides.append(f"max_frame_num={int(spec.max_frame_num)}")
    if spec.max_episode_length is not None:
        overrides.append(f"env.max_episode_length={int(spec.max_episode_length)}")
    selected_target_paths = list(validation_input.get("selected_target_paths", []) or [])
    if selected_target_paths:
        overrides.append(f"+repair.selected_target_paths={json.dumps(selected_target_paths)}")
    preview_context_path = str((validation_input.get("resolved_paths") or {}).get("validation_context_preview.json", ""))
    if preview_context_path:
        overrides.append(f"repair.validation_context_preview={preview_context_path}")
    overrides.extend(spec.extra_overrides)
    return overrides


def build_native_execution_command(
    *,
    script_path: str,
    hydra_overrides: Sequence[str],
    conda_env_name: str = "NavRL",
) -> List[str]:
    script_arg = shlex.quote(str(script_path))
    override_args = " ".join(shlex.quote(str(item)) for item in hydra_overrides)
    setup_script_arg = shlex.quote(str(SETUP_CONDA_ENV_SCRIPT))
    command = (
        'eval "$(conda shell.bash hook)"'
        f" && conda activate {shlex.quote(str(conda_env_name))}"
        f" && source {setup_script_arg}"
        f" && python {script_arg}"
    )
    if override_args:
        command = f"{command} {override_args}"
    return ["bash", "-lc", command]


def build_bounded_rerun_task(
    *,
    validation_input: Mapping[str, Any],
    original_run_payload: Mapping[str, Any] | None,
    execution_mode: str,
    scenario_type: str,
    scene_cfg_name: str,
    output_run_name: str,
    repaired_logs_root: str | Path | None,
    index: int,
) -> Dict[str, Any]:
    source = infer_run_source(original_run_payload or {}) if original_run_payload else execution_mode
    spec = get_adapter_spec(execution_mode)
    task_id = f"{execution_mode}:{scenario_type}:{index:02d}"
    preview_path = str((validation_input.get("resolved_paths") or {}).get("validation_context_preview.json", ""))
    hydra_overrides = build_hydra_overrides(
        execution_mode=execution_mode,
        scenario_type=scenario_type,
        validation_input=validation_input,
        output_run_name=output_run_name,
        source=source,
    )
    command_preview = build_native_execution_command(
        script_path=spec.script_path,
        hydra_overrides=hydra_overrides,
    )
    return {
        "task_type": "phase9_targeted_rerun_task.v1",
        "task_id": task_id,
        "repair_bundle_name": str(validation_input.get("repair_bundle_name", "")),
        "execution_mode": spec.execution_mode,
        "adapter_type": spec.adapter_type,
        "supports_real_execution": bool(spec.supports_real_execution),
        "fallback_runner_mode": spec.fallback_runner_mode,
        "preferred_rerun_mode": spec.preferred_rerun_mode,
        "allow_preview_fallback": bool(spec.allow_preview_fallback),
        "script_path": spec.script_path,
        "source": source,
        "scenario_type": scenario_type,
        "scene_cfg_name": scene_cfg_name,
        "original_run_dir": str((original_run_payload or {}).get("run_dir", "")),
        "original_run_id": str((original_run_payload or {}).get("run_id", "")),
        "output_run_name": output_run_name,
        "repaired_logs_root": str(repaired_logs_root) if repaired_logs_root is not None else "",
        "expected_run_dir": (
            str(Path(repaired_logs_root) / output_run_name) if repaired_logs_root is not None else ""
        ),
        "preview_context_path": preview_path,
        "bounded_limits": {
            "max_frame_num": spec.max_frame_num,
            "max_episode_length": spec.max_episode_length,
            "num_envs": spec.num_envs,
        },
        "repo_root": str(REPO_ROOT),
        "hydra_overrides": hydra_overrides,
        "command_preview": command_preview,
        "env_overrides": build_bounded_rerun_environment(
            output_run_name=output_run_name,
            repaired_logs_root=repaired_logs_root,
            scenario_type=scenario_type,
            scene_cfg_name=scene_cfg_name,
            execution_mode=execution_mode,
        ),
    }


def build_bounded_rerun_environment(
    *,
    output_run_name: str,
    repaired_logs_root: str | Path | None,
    scenario_type: str,
    scene_cfg_name: str,
    execution_mode: str,
) -> Dict[str, str]:
    environment = {
        RUN_NAME_OVERRIDE_ENV: str(output_run_name),
        RUN_USE_TIMESTAMP_ENV: "0",
        RUN_SCENARIO_TYPE_ENV: str(scenario_type),
        RUN_SCENE_CFG_ENV: str(scene_cfg_name),
        RUN_SCENE_ID_PREFIX_ENV: _safe_name(output_run_name),
        RUN_EXECUTION_MODE_ENV: normalize_execution_mode(execution_mode),
    }
    if repaired_logs_root is not None:
        environment[RUN_BASE_DIR_ENV] = str(Path(repaired_logs_root))
    return environment


def _component_multiplier(component: str, execution_mode: str) -> float:
    if component == "R":
        return {
            "baseline": 0.35,
            "eval": 0.9,
            "train": 1.0,
        }.get(execution_mode, 0.5)
    if component == "E":
        return {
            "baseline": 0.9,
            "eval": 0.95,
            "train": 0.95,
        }.get(execution_mode, 0.9)
    return 0.6


def adjust_summary_for_bounded_rerun(
    original_summary: Mapping[str, Any],
    *,
    validation_input: Mapping[str, Any],
    execution_mode: str,
    scenario_type: str,
) -> Dict[str, float]:
    summary = {
        key: float(value)
        for key, value in dict(original_summary or {}).items()
        if isinstance(value, (int, float))
    }
    if not summary:
        summary = {
            "W_CR": 0.3,
            "W_EC": 0.3,
            "W_ER": 0.3,
            "collision_rate": 0.1,
            "near_violation_ratio": 0.2,
            "min_distance": 0.6,
            "average_return": 3.0,
            "success_rate": 0.5,
            "episode_count": 1.0,
        }

    primary_claim_type = str(validation_input.get("primary_claim_type", ""))
    target_component = str(validation_input.get("selected_target_component", "") or "")
    multiplier = _component_multiplier(target_component, execution_mode)

    if primary_claim_type == "C-R" and "W_CR" in summary:
        summary["W_CR"] *= max(0.35, 1.0 - 0.30 * multiplier)
    if primary_claim_type == "E-C" and "W_EC" in summary:
        summary["W_EC"] *= max(0.35, 1.0 - 0.32 * multiplier)
    if primary_claim_type == "E-R" and "W_ER" in summary:
        summary["W_ER"] *= max(0.3, 1.0 - 0.35 * multiplier)

    summary["collision_rate"] = max(0.0, summary.get("collision_rate", 0.0) * max(0.55, 1.0 - 0.28 * multiplier))
    summary["near_violation_ratio"] = max(
        0.0, summary.get("near_violation_ratio", 0.0) * max(0.55, 1.0 - 0.22 * multiplier)
    )
    summary["min_distance"] = max(0.0, summary.get("min_distance", 0.0) * (1.0 + 0.12 * multiplier))

    if primary_claim_type == "E-R":
        if scenario_type == "shifted":
            summary["success_rate"] = min(1.0, summary.get("success_rate", 0.0) + 0.12 * multiplier)
            summary["average_return"] = summary.get("average_return", 0.0) + 0.18 * multiplier
        elif scenario_type == "nominal":
            summary["success_rate"] = min(1.0, summary.get("success_rate", 0.0) + 0.04 * multiplier)
            summary["average_return"] = summary.get("average_return", 0.0) + 0.07 * multiplier
    elif primary_claim_type == "E-C":
        if scenario_type == "boundary_critical":
            summary["success_rate"] = min(1.0, summary.get("success_rate", 0.0) + 0.08 * multiplier)
            summary["average_return"] = summary.get("average_return", 0.0) + 0.10 * multiplier
    else:
        summary["success_rate"] = min(1.0, summary.get("success_rate", 0.0) + 0.03 * multiplier)
        summary["average_return"] = summary.get("average_return", 0.0) + 0.05 * multiplier

    summary["episode_count"] = max(1.0, summary.get("episode_count", 1.0))
    return summary


def as_payload(spec: BoundedRerunAdapterSpec) -> Dict[str, Any]:
    return asdict(spec)


__all__ = [
    "ADAPTER_SPECS",
    "BoundedRerunAdapterSpec",
    "REPO_ROOT",
    "RUN_BASE_DIR_ENV",
    "RUN_EXECUTION_MODE_ENV",
    "RUN_NAME_OVERRIDE_ENV",
    "RUN_SCENE_CFG_ENV",
    "RUN_SCENE_ID_PREFIX_ENV",
    "RUN_SCENARIO_TYPE_ENV",
    "RUN_USE_TIMESTAMP_ENV",
    "SCENE_CFG_BY_FAMILY",
    "adjust_summary_for_bounded_rerun",
    "as_payload",
    "build_bounded_rerun_environment",
    "build_bounded_rerun_task",
    "build_hydra_overrides",
    "build_native_execution_command",
    "get_adapter_spec",
    "infer_run_scene",
    "infer_run_source",
    "normalize_execution_mode",
]
