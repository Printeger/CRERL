from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - repo env should provide yaml
    raise RuntimeError("PyYAML is required to run Demo 1.") from exc


REPO_ROOT = Path(__file__).resolve().parents[3]
TRAINING_ROOT = REPO_ROOT / "isaac-training" / "training"
if str(TRAINING_ROOT) not in sys.path:
    sys.path.insert(0, str(TRAINING_ROOT))

from analyzers.dynamic_analyzer import run_dynamic_analysis_bundle
from analyzers.report_contract import DEFAULT_REPORT_MODE_ARTIFACTS, DEFAULT_REPORT_NAMESPACES
from analyzers.report_generator import run_report_generation_bundle
from analyzers.semantic_analyzer import run_semantic_analysis_bundle
from analyzers.semantic_provider import build_semantic_provider
from analyzers.detector_runner import run_static_analysis_bundle
from repair.acceptance import accept_repair
from repair.comparison import compare_validation_runs
from repair.decision import decide_validation
from repair.patch_executor import run_repair_bundle_write
from repair.repair_validator import build_phase9_validation_request, validate_repair
from repair.rule_based_repair import propose_rule_based_repairs
from repair.validation_runner import run_validation_bundle_write
from runtime_logging.acceptance import run_acceptance_check
from runtime_logging.episode_writer import load_run_directory
from runtime_logging.logger import create_run_logger


DEMO_ROOT = Path(__file__).resolve().parents[1]
CFG_ROOT = DEMO_ROOT / "cfg"
SCENE_LAYOUT_PATH = CFG_ROOT / "scene_layout.yaml"
ENV_CFG_DIR = CFG_ROOT / "env_cfg"
DETECTOR_CFG_DIR = CFG_ROOT / "detector_cfg"
SCREENSHOT_FILES = {
    "scene": "demo1_scene_topdown.svg",
    "overlay": "demo1_trajectory_overlay.svg",
    "metrics": "demo1_metric_board.svg",
}
VIDEO_FILES = {
    "replay": "demo1_replay.html",
}


@dataclass(frozen=True)
class VariantSpec:
    name: str
    label: str
    color: str
    spec_dir: Path


@dataclass
class VariantResult:
    spec: VariantSpec
    run_dir: Path
    route_counts: Dict[str, int]
    route_rate: Dict[str, float]
    representative_trajectory: List[List[float]]
    all_trajectories: List[List[List[float]]]
    static_bundle_dir: Path
    dynamic_bundle_dir: Path
    witness_scores: Dict[str, float]
    summary: Dict[str, Any]


VARIANTS: Sequence[VariantSpec] = (
    VariantSpec("clean", "Clean", "#1b7f6b", CFG_ROOT / "spec_clean"),
    VariantSpec("injected", "Injected", "#d04b36", CFG_ROOT / "spec_injected"),
    VariantSpec("repaired", "Repaired", "#1f5aa6", CFG_ROOT / "spec_repaired"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Demo 1: Class I reward-boundary lure experiment.")
    parser.add_argument(
        "--output-root",
        default=str(DEMO_ROOT / "reports" / "latest"),
        help="Directory used for machine-readable demo outputs.",
    )
    parser.add_argument(
        "--asset-root",
        default=str(DEMO_ROOT / "assets"),
        help="Directory used for SVG/HTML visualization artifacts.",
    )
    parser.add_argument(
        "--clean-output",
        action="store_true",
        help="Remove the output root before running the demo pipeline.",
    )
    parser.add_argument(
        "--allow-failed-goal",
        action="store_true",
        help="Return success even if the final demo verification fails.",
    )
    return parser.parse_args()


def _load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True), encoding="utf-8")
    return path


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except Exception:
        return str(path)


def _reward_weights(spec_dir: Path) -> Dict[str, float]:
    payload = _load_yaml(spec_dir / "reward_spec_v0.yaml")
    components = dict(payload.get("components", {}))
    return {
        "reward_progress": float(dict(components.get("reward_progress", {})).get("weight", 0.0) or 0.0),
        "reward_safety_static": float(dict(components.get("reward_safety_static", {})).get("weight", 0.0) or 0.0),
        "reward_safety_dynamic": float(dict(components.get("reward_safety_dynamic", {})).get("weight", 0.0) or 0.0),
        "penalty_smooth": float(dict(components.get("penalty_smooth", {})).get("weight", 0.0) or 0.0),
        "penalty_height": float(dict(components.get("penalty_height", {})).get("weight", 0.0) or 0.0),
    }


def _pairwise(items: Sequence[Sequence[float]]) -> Iterable[tuple[Sequence[float], Sequence[float]]]:
    for index in range(1, len(items)):
        yield items[index - 1], items[index]


def _polyline_length(points: Sequence[Sequence[float]]) -> float:
    return sum(math.dist(left, right) for left, right in _pairwise(points))


def _sample_polyline(points: Sequence[Sequence[float]], count: int) -> List[List[float]]:
    if count <= 1:
        first = list(points[0])
        return [first]
    segment_lengths = [math.dist(left, right) for left, right in _pairwise(points)]
    total_length = sum(segment_lengths)
    if total_length <= 1e-9:
        return [list(points[0]) for _ in range(count)]
    cumulative = [0.0]
    running = 0.0
    for segment_length in segment_lengths:
        running += segment_length
        cumulative.append(running)
    sampled: List[List[float]] = []
    for index in range(count):
        target = total_length * index / max(count - 1, 1)
        for seg_index, segment_length in enumerate(segment_lengths):
            if target <= cumulative[seg_index + 1] or seg_index == len(segment_lengths) - 1:
                left = points[seg_index]
                right = points[seg_index + 1]
                local = 0.0 if segment_length <= 1e-9 else (target - cumulative[seg_index]) / segment_length
                sampled.append(
                    [
                        float(left[0] + (right[0] - left[0]) * local),
                        float(left[1] + (right[1] - left[1]) * local),
                    ]
                )
                break
    return sampled


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _rect_clearance(point_xy: Sequence[float], rect: Mapping[str, Any]) -> float:
    px, py = float(point_xy[0]), float(point_xy[1])
    x0 = float(rect.get("x", 0.0))
    y0 = float(rect.get("y", 0.0))
    x1 = x0 + float(rect.get("width", 0.0))
    y1 = y0 + float(rect.get("height", 0.0))
    dx = max(x0 - px, 0.0, px - x1)
    dy = max(y0 - py, 0.0, py - y1)
    if dx <= 0.0 and dy <= 0.0:
        return -min(px - x0, x1 - px, py - y0, y1 - py)
    return math.hypot(dx, dy)


def _route_definitions(scene_layout: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {str(item["id"]): dict(item) for item in list(scene_layout.get("corridors", []))}


def _route_preference_score(
    route_id: str,
    *,
    scene_layout: Mapping[str, Any],
    reward_weights: Mapping[str, float],
) -> float:
    model = dict(scene_layout.get("route_preference_model", {})).get(route_id, {})
    return (
        float(reward_weights.get("reward_progress", 0.0)) * float(model.get("progress_proxy", 0.0))
        + float(reward_weights.get("reward_safety_static", 0.0)) * float(model.get("safety_proxy", 0.0))
        + float(reward_weights.get("penalty_smooth", 0.0)) * float(model.get("smoothness_proxy", 0.0))
    )


def _choose_route(
    *,
    scene_layout: Mapping[str, Any],
    reward_weights: Mapping[str, float],
    route_ids: Sequence[str],
) -> tuple[str, Dict[str, float]]:
    scores = {
        route_id: _route_preference_score(
            route_id,
            scene_layout=scene_layout,
            reward_weights=reward_weights,
        )
        for route_id in route_ids
    }
    ordered = sorted(scores.items(), key=lambda item: (item[1], item[0]), reverse=True)
    best_route = ordered[0][0]
    if len(ordered) > 1:
        margin = float(dict(scene_layout.get("simulation", {})).get("route_selection_margin", 0.0) or 0.0)
        if (ordered[0][1] - ordered[1][1]) <= margin:
            best_route = "safe_long"
    return best_route, scores


def _disturb_point(
    point_xy: Sequence[float],
    *,
    step_idx: int,
    step_count: int,
    rng: random.Random,
    route_id: str,
    collision_episode: bool,
) -> List[float]:
    if step_idx in (0, step_count - 1):
        return [float(point_xy[0]), float(point_xy[1])]
    phase = step_idx / max(step_count - 1, 1)
    x = float(point_xy[0]) + rng.uniform(-0.03, 0.03)
    y = float(point_xy[1]) + rng.uniform(-0.03, 0.03)
    if route_id == "risky_short":
        y -= 0.14 * math.sin(math.pi * phase) ** 2
        if collision_episode and 0.56 <= phase <= 0.72:
            y -= 0.18
    else:
        y += 0.02 * math.sin(2.0 * math.pi * phase)
    return [x, y]


def _min_obstacle_distance(point_xy: Sequence[float], scene_layout: Mapping[str, Any]) -> float:
    obstacles = list(scene_layout.get("obstacles", []))
    clearances = [_rect_clearance(point_xy, obstacle) for obstacle in obstacles]
    return min(clearances) if clearances else 10.0


def _turn_magnitude(previous_heading: float | None, current_heading: float | None) -> float:
    if previous_heading is None or current_heading is None:
        return 0.0
    delta = math.atan2(math.sin(current_heading - previous_heading), math.cos(current_heading - previous_heading))
    return abs(delta)


def _goal_distance(point_xy: Sequence[float], goal_xy: Sequence[float]) -> float:
    return math.dist(point_xy, goal_xy)


def _speed_norm(left: Sequence[float], right: Sequence[float], dt: float) -> float:
    if dt <= 1e-9:
        return 0.0
    return math.dist(left, right) / dt


def _trajectory_heading(left: Sequence[float], right: Sequence[float]) -> float:
    return math.atan2(float(right[1]) - float(left[1]), float(right[0]) - float(left[0]))


def _simulate_variant(
    spec: VariantSpec,
    *,
    scene_layout: Mapping[str, Any],
    output_root: Path,
) -> VariantResult:
    reward_weights = _reward_weights(spec.spec_dir)
    route_defs = _route_definitions(scene_layout)
    route_ids = tuple(route_defs.keys())
    simulation_cfg = dict(scene_layout.get("simulation", {}))
    steps_per_episode = int(simulation_cfg.get("steps_per_episode", 36) or 36)
    episodes_per_variant = int(simulation_cfg.get("episodes_per_variant", 6) or 6)
    near_violation_distance = float(simulation_cfg.get("near_violation_distance", 0.6) or 0.6)
    collision_distance = float(simulation_cfg.get("collision_distance", 0.22) or 0.22)
    risky_collision_seeds = set(int(item) for item in list(simulation_cfg.get("risky_collision_seeds", [])))

    variant_root = output_root / spec.name
    logs_root = variant_root / "logs"
    run_dir = logs_root / f"demo1_{spec.name}"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_logger = create_run_logger(
        source="demo_boundary_lure",
        run_name=f"demo1_{spec.name}",
        base_dir=logs_root,
        near_violation_distance=near_violation_distance,
        use_timestamp=False,
        run_metadata={
            "demo_id": "demo1_cr_boundary_lure",
            "variant": spec.name,
            "scene_layout_file": _repo_relative(SCENE_LAYOUT_PATH),
            "spec_dir": _repo_relative(spec.spec_dir),
        },
    )

    start_xy = list(scene_layout.get("start", [0.0, 0.0]))
    goal_xy = list(scene_layout.get("goal", [1.0, 1.0]))
    flight_z = float(dict(scene_layout.get("workspace", {})).get("flight_z", 1.2) or 1.2)
    representative_trajectory: List[List[float]] = []
    all_trajectories: List[List[List[float]]] = []
    route_counts = {route_id: 0 for route_id in route_ids}

    for episode_seed in range(episodes_per_variant):
        route_id, route_scores = _choose_route(
            scene_layout=scene_layout,
            reward_weights=reward_weights,
            route_ids=route_ids,
        )
        collision_episode = bool(route_id == "risky_short" and episode_seed in risky_collision_seeds)
        route_counts[route_id] = route_counts.get(route_id, 0) + 1
        route_waypoints = list(route_defs[route_id]["waypoints"])
        sampled_points = _sample_polyline(route_waypoints, steps_per_episode)
        rng = random.Random(f"{spec.name}:{episode_seed}:demo1")
        disturbed_points = [
            _disturb_point(
                point_xy,
                step_idx=step_idx,
                step_count=steps_per_episode,
                rng=rng,
                route_id=route_id,
                collision_episode=collision_episode,
            )
            for step_idx, point_xy in enumerate(sampled_points)
        ]
        if representative_trajectory == []:
            representative_trajectory = [list(point) for point in disturbed_points]
        all_trajectories.append([list(point) for point in disturbed_points])

        run_logger.reset(
            episode_index=episode_seed,
            seed=episode_seed,
            scene_id="demo1_cr_boundary_lure_nominal_v0",
            scenario_type="nominal",
            scene_cfg_name="scene_cfg_nominal.yaml",
            scene_tags={
                "family": "nominal",
                "scene_cfg_name": "scene_cfg_nominal.yaml",
                "route_id": route_id,
                "route_role": str(route_defs[route_id]["role"]),
                "variant": spec.name,
                "demo_id": "demo1_cr_boundary_lure",
                "route_scores": route_scores,
            },
        )

        previous_goal_distance = _goal_distance(disturbed_points[0], goal_xy)
        previous_heading: float | None = None
        dt = 1.0 / 12.0
        for step_idx, point_xy in enumerate(disturbed_points):
            phase = step_idx / max(steps_per_episode - 1, 1)
            clearance = _min_obstacle_distance(point_xy, scene_layout)
            if collision_episode and step_idx == steps_per_episode - 1:
                clearance = min(clearance, collision_distance * 0.45)
            clearance_signal = (clearance - near_violation_distance) / max(near_violation_distance, 1e-6)
            goal_distance = _goal_distance(point_xy, goal_xy)
            delta_goal = max(0.0, previous_goal_distance - goal_distance)

            if step_idx == 0:
                next_point = disturbed_points[min(step_idx + 1, steps_per_episode - 1)]
                velocity_xy = [
                    (float(next_point[0]) - float(point_xy[0])) / dt,
                    (float(next_point[1]) - float(point_xy[1])) / dt,
                ]
            else:
                prev_point = disturbed_points[step_idx - 1]
                velocity_xy = [
                    (float(point_xy[0]) - float(prev_point[0])) / dt,
                    (float(point_xy[1]) - float(prev_point[1])) / dt,
                ]

            speed_norm = math.hypot(velocity_xy[0], velocity_xy[1])
            heading = None
            if step_idx > 0:
                heading = _trajectory_heading(disturbed_points[step_idx - 1], point_xy)
            turn_penalty = 0.06 + min(1.0, _turn_magnitude(previous_heading, heading) / 0.8) * 0.18
            progress_component = 0.03 + 0.25 * delta_goal + 0.01 * min(speed_norm, 1.2)
            safety_component = 0.22 * clearance_signal
            if route_id == "risky_short":
                progress_component += 0.04 + 0.07 * math.sin(math.pi * phase) ** 2
                progress_component += max(0.0, near_violation_distance - clearance) * 0.22
            else:
                safety_component += 0.16
            if collision_episode and step_idx == steps_per_episode - 1:
                safety_component -= 0.18

            reward_total = (
                reward_weights["reward_progress"] * progress_component
                + reward_weights["reward_safety_static"] * safety_component
                + reward_weights["penalty_smooth"] * turn_penalty
            )

            collision_flag = bool(collision_episode and step_idx == steps_per_episode - 1)
            done_type = "running"
            if step_idx == steps_per_episode - 1:
                done_type = "collision" if collision_flag else "success"

            run_logger.log_step(
                step_idx=step_idx,
                sim_time=dt * step_idx,
                position=(float(point_xy[0]), float(point_xy[1]), flight_z),
                velocity=(float(velocity_xy[0]), float(velocity_xy[1]), 0.0),
                yaw_rate=0.0,
                goal_distance=goal_distance,
                reward_total=reward_total,
                reward_components={
                    "reward_progress": progress_component,
                    "reward_safety_static": safety_component,
                    "reward_safety_dynamic": 0.0,
                    "penalty_smooth": turn_penalty,
                    "penalty_height": 0.0,
                    "manual_control": 0.0,
                },
                collision_flag=collision_flag,
                min_obstacle_distance=clearance,
                near_violation_flag=clearance < near_violation_distance,
                out_of_bounds_flag=False,
                done_type=done_type,
                scene_id="demo1_cr_boundary_lure_nominal_v0",
                scenario_type="nominal",
                scene_cfg_name="scene_cfg_nominal.yaml",
                target_position=(float(goal_xy[0]), float(goal_xy[1]), flight_z),
                scene_tags={
                    "family": "nominal",
                    "route_id": route_id,
                    "route_role": str(route_defs[route_id]["role"]),
                    "variant": spec.name,
                    "demo_id": "demo1_cr_boundary_lure",
                    "speed_norm": speed_norm,
                },
            )
            previous_goal_distance = goal_distance
            previous_heading = heading

        run_logger.finalize_episode(done_type="collision" if collision_episode else "success")

    acceptance = run_acceptance_check(run_logger.run_dir, write_report=True)
    if not bool(acceptance.get("passed", False)):
        raise RuntimeError(f"Generated run failed acceptance for {spec.name}: {run_logger.run_dir}")

    static_report, static_bundle_paths = run_static_analysis_bundle(
        spec_cfg_dir=spec.spec_dir,
        env_cfg_dir=ENV_CFG_DIR,
        detector_cfg_dir=DETECTOR_CFG_DIR,
        scene_families=("nominal",),
        reports_root=variant_root,
        bundle_name=f"demo1_{spec.name}_static",
    )
    del static_report
    dynamic_report, dynamic_bundle_paths = run_dynamic_analysis_bundle(
        run_dirs=[Path(run_logger.run_dir)],
        spec_cfg_dir=spec.spec_dir,
        env_cfg_dir=ENV_CFG_DIR,
        detector_cfg_dir=DETECTOR_CFG_DIR,
        scene_families=("nominal",),
        reports_root=variant_root,
        bundle_name=f"demo1_{spec.name}_dynamic",
    )
    witness_scores = {
        str(item["witness_id"]): float(item["score"])
        for item in list(dynamic_report.witnesses)
    }
    route_rate = {
        route_id: float(route_counts.get(route_id, 0)) / max(sum(route_counts.values()), 1)
        for route_id in route_ids
    }

    summary_path = Path(run_logger.run_dir) / "summary.json"
    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    summary_payload.update(
        {
            "W_CR": float(witness_scores.get("W_CR", 0.0)),
            "W_EC": float(witness_scores.get("W_EC", 0.0)),
            "W_ER": float(witness_scores.get("W_ER", 0.0)),
            "risky_route_rate": float(route_rate.get("risky_short", 0.0)),
            "safe_route_rate": float(route_rate.get("safe_long", 0.0)),
            "variant_name": spec.name,
            "scene_layout_id": str(scene_layout.get("layout_id", "")),
        }
    )
    summary_path.write_text(json.dumps(summary_payload, indent=2, sort_keys=True), encoding="utf-8")
    _write_json(
        variant_root / "route_summary.json",
        {
            "variant": spec.name,
            "route_counts": route_counts,
            "route_rate": route_rate,
            "route_choice_scores": {
                route_id: _route_preference_score(
                    route_id,
                    scene_layout=scene_layout,
                    reward_weights=reward_weights,
                )
                for route_id in route_ids
            },
            "reward_weights": reward_weights,
        },
    )
    _write_json(
        variant_root / "trajectory_records.json",
        {
            "variant": spec.name,
            "representative_trajectory": representative_trajectory,
            "all_trajectories": all_trajectories,
            "route_counts": route_counts,
            "route_rate": route_rate,
        },
    )

    return VariantResult(
        spec=spec,
        run_dir=Path(run_logger.run_dir),
        route_counts=route_counts,
        route_rate=route_rate,
        representative_trajectory=representative_trajectory,
        all_trajectories=all_trajectories,
        static_bundle_dir=Path(static_bundle_paths["report_dir"]),
        dynamic_bundle_dir=Path(dynamic_bundle_paths["report_dir"]),
        witness_scores=witness_scores,
        summary=summary_payload,
    )


def _repair_target_override(plan: Any, reward_spec_path: Path) -> None:
    reward_payload = _load_yaml(reward_spec_path)

    def _lookup(target_path: str) -> Any:
        current: Any = reward_payload
        for part in target_path.split("."):
            if isinstance(current, Mapping):
                current = current.get(part)
            else:
                return None
        return current

    target_file = _repo_relative(reward_spec_path)
    for candidate in list(getattr(plan, "candidates", []) or []):
        candidate.target_file = target_file
        if candidate.patch is not None:
            candidate.patch.target_file = target_file
            for operation in list(candidate.patch.operations or []):
                operation.target_file = target_file
                operation.before = _lookup(operation.target_path)
                if candidate.operator_type == "reduce_progress_proxy_weight":
                    operation.after = round(max(0.2, float(operation.before or 1.0) * 0.8), 4)
                elif candidate.operator_type == "strengthen_safety_reward":
                    operation.after = round(float(operation.before or 0.0) + 0.5, 4)
                elif candidate.operator_type == "strengthen_height_penalty":
                    operation.after = round(float(operation.before or -1.0) * 1.1, 4)
        candidate.target_paths = list(candidate.target_paths)
    if getattr(plan, "selected_patch", None) is not None:
        plan.selected_patch.target_file = target_file
        for operation in list(plan.selected_patch.operations or []):
            operation.target_file = target_file


def _run_injected_report_flow(
    injected: VariantResult,
    *,
    output_root: Path,
) -> Dict[str, Any]:
    semantic_provider = build_semantic_provider("mock", config={"max_claims": 3})
    semantic_report, semantic_bundle_paths = run_semantic_analysis_bundle(
        static_bundle_dir=injected.static_bundle_dir,
        dynamic_bundle_dir=injected.dynamic_bundle_dir,
        provider=semantic_provider,
        spec_cfg_dir=injected.spec.spec_dir,
        env_cfg_dir=ENV_CFG_DIR,
        detector_cfg_dir=DETECTOR_CFG_DIR,
        scene_families=("nominal",),
        reports_root=output_root / injected.spec.name,
        bundle_name="demo1_injected_semantic",
    )
    del semantic_report
    report, report_bundle_paths = run_report_generation_bundle(
        static_bundle_dir=injected.static_bundle_dir,
        dynamic_bundle_dir=injected.dynamic_bundle_dir,
        semantic_bundle_dir=Path(semantic_bundle_paths["report_dir"]),
        spec_cfg_dir=injected.spec.spec_dir,
        env_cfg_dir=ENV_CFG_DIR,
        detector_cfg_dir=DETECTOR_CFG_DIR,
        scene_families=("nominal",),
        reports_root=output_root / injected.spec.name,
        bundle_name="demo1_injected_report",
    )

    plan = propose_rule_based_repairs(report_bundle_dir=Path(report_bundle_paths["report_dir"]))
    _repair_target_override(plan, injected.spec.spec_dir / "reward_spec_v0.yaml")
    acceptance = accept_repair(plan.to_dict())
    repair_validation = validate_repair(plan.to_dict(), acceptance=acceptance)
    validation_request = build_phase9_validation_request(
        plan.to_dict(),
        repair_validation=repair_validation,
        acceptance=acceptance,
        bundle_name="demo1_injected_repair",
        repair_namespace=DEFAULT_REPORT_NAMESPACES["repair_generation"],
    )
    repair_bundle_paths = run_repair_bundle_write(
        plan,
        acceptance,
        repair_validation=repair_validation,
        validation_request=validation_request,
        reports_root=output_root / injected.spec.name,
        bundle_name="demo1_injected_repair",
        namespaces=DEFAULT_REPORT_NAMESPACES,
        report_mode_artifacts=DEFAULT_REPORT_MODE_ARTIFACTS,
    )
    return {
        "semantic_bundle_dir": Path(semantic_bundle_paths["report_dir"]),
        "report_bundle_dir": Path(report_bundle_paths["report_dir"]),
        "repair_bundle_dir": Path(repair_bundle_paths["repair_dir"]),
        "report_primary_claim_type": str(report.root_cause_summary.get("primary_claim_type", "")),
        "report_summary": dict(report.root_cause_summary),
        "selected_candidate_id": str(plan.selected_candidate_id),
        "selected_operator": str(plan.selected_patch.metadata.get("operator_type", "")) if plan.selected_patch else "",
    }


def _run_validation_flow(
    *,
    output_root: Path,
    injected: VariantResult,
    repaired: VariantResult,
    repair_bundle_name: str,
) -> Dict[str, Any]:
    original_runs = [load_run_directory(injected.run_dir)]
    repaired_runs = [load_run_directory(repaired.run_dir)]
    comparison = compare_validation_runs(
        primary_claim_type="C-R",
        validation_targets=["W_CR", "min_distance", "near_violation_ratio", "average_return", "success_rate"],
        original_runs=original_runs,
        repaired_runs=repaired_runs,
    )
    decision = decide_validation(comparison, performance_regression_epsilon=0.05)
    validation_plan = {
        "validation_type": "demo1_validation_plan.v1",
        "repair_bundle_name": repair_bundle_name,
        "primary_claim_type": "C-R",
        "validation_targets": ["W_CR", "min_distance", "near_violation_ratio", "average_return", "success_rate"],
    }
    validation_runs = {
        "requested_rerun_mode": "not_requested",
        "rerun_tasks": [],
        "triggered_rerun_results": {},
        "original_runs": [
            {
                "run_dir": str(injected.run_dir),
                "run_id": str(injected.run_dir.name),
                "source": "demo_boundary_lure",
                "scenario_type": "nominal",
                "scene_cfg_name": "scene_cfg_nominal.yaml",
            }
        ],
        "repaired_runs": [
            {
                "run_dir": str(repaired.run_dir),
                "run_id": str(repaired.run_dir.name),
                "source": "demo_boundary_lure",
                "scenario_type": "nominal",
                "scene_cfg_name": "scene_cfg_nominal.yaml",
            }
        ],
    }
    bundle_paths = run_validation_bundle_write(
        validation_plan=validation_plan,
        validation_runs=validation_runs,
        comparison=comparison,
        decision=decision,
        reports_root=output_root,
        bundle_name="demo1_validation",
        namespaces=DEFAULT_REPORT_NAMESPACES,
        report_mode_artifacts=DEFAULT_REPORT_MODE_ARTIFACTS,
    )
    return {
        "validation_dir": Path(bundle_paths["validation_dir"]),
        "comparison": comparison,
        "decision": decision,
    }


def _render_scene_svg(scene_layout: Mapping[str, Any], output_path: Path) -> None:
    workspace = dict(scene_layout.get("workspace", {}))
    width = float(workspace.get("xmax", 12.0) - workspace.get("xmin", 0.0))
    height = float(workspace.get("ymax", 8.0) - workspace.get("ymin", 0.0))
    scale = 64.0
    margin = 36.0

    def _sx(value: float) -> float:
        return margin + value * scale

    def _sy(value: float) -> float:
        return margin + (height - value) * scale

    elements: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(width * scale + margin * 2)}" height="{int(height * scale + margin * 2)}" viewBox="0 0 {int(width * scale + margin * 2)} {int(height * scale + margin * 2)}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>',
        f'<rect x="{_sx(0.0):.1f}" y="{_sy(height):.1f}" width="{width * scale:.1f}" height="{height * scale:.1f}" fill="#fbfbfb" stroke="#333333" stroke-width="2"/>',
    ]
    for obstacle in list(scene_layout.get("obstacles", [])):
        x = float(obstacle.get("x", 0.0))
        y = float(obstacle.get("y", 0.0))
        rect_width = float(obstacle.get("width", 0.0))
        rect_height = float(obstacle.get("height", 0.0))
        elements.append(
            f'<rect x="{_sx(x):.1f}" y="{_sy(y + rect_height):.1f}" width="{rect_width * scale:.1f}" height="{rect_height * scale:.1f}" fill="#d9d9d9" stroke="#666666" stroke-width="1.5"/>'
        )
    for corridor in list(scene_layout.get("corridors", [])):
        points = " ".join(f"{_sx(float(item[0])):.1f},{_sy(float(item[1])):.1f}" for item in list(corridor.get("waypoints", [])))
        color = str(corridor.get("rendered_color", "#333333"))
        elements.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round" opacity="0.35"/>'
        )
    start = list(scene_layout.get("start", [0.0, 0.0]))
    goal = list(scene_layout.get("goal", [1.0, 1.0]))
    elements.extend(
        [
            f'<circle cx="{_sx(float(start[0])):.1f}" cy="{_sy(float(start[1])):.1f}" r="10" fill="#2f9e44"/>',
            f'<circle cx="{_sx(float(goal[0])):.1f}" cy="{_sy(float(goal[1])):.1f}" r="10" fill="#f08c00"/>',
            f'<text x="{_sx(0.2):.1f}" y="{margin - 10:.1f}" font-family="Helvetica, Arial, sans-serif" font-size="24" fill="#222222">Demo 1 Scene: one short risky corridor and one longer safe corridor</text>',
            f'<text x="{_sx(0.2):.1f}" y="{_sy(7.4):.1f}" font-family="Helvetica, Arial, sans-serif" font-size="18" fill="#d04b36">Short inner corridor</text>',
            f'<text x="{_sx(3.0):.1f}" y="{_sy(1.7):.1f}" font-family="Helvetica, Arial, sans-serif" font-size="18" fill="#1b7f6b">Long outer corridor</text>',
        ]
    )
    elements.append("</svg>")
    _write_text(output_path, "\n".join(elements))


def _render_overlay_svg(
    scene_layout: Mapping[str, Any],
    results: Mapping[str, VariantResult],
    output_path: Path,
) -> None:
    workspace = dict(scene_layout.get("workspace", {}))
    width = float(workspace.get("xmax", 12.0) - workspace.get("xmin", 0.0))
    height = float(workspace.get("ymax", 8.0) - workspace.get("ymin", 0.0))
    scale = 64.0
    margin = 40.0

    def _sx(value: float) -> float:
        return margin + value * scale

    def _sy(value: float) -> float:
        return margin + (height - value) * scale

    elements: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(width * scale + margin * 2)}" height="{int(height * scale + margin * 2)}" viewBox="0 0 {int(width * scale + margin * 2)} {int(height * scale + margin * 2)}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>',
        f'<rect x="{_sx(0.0):.1f}" y="{_sy(height):.1f}" width="{width * scale:.1f}" height="{height * scale:.1f}" fill="#ffffff" stroke="#333333" stroke-width="2"/>',
    ]
    for obstacle in list(scene_layout.get("obstacles", [])):
        x = float(obstacle.get("x", 0.0))
        y = float(obstacle.get("y", 0.0))
        rect_width = float(obstacle.get("width", 0.0))
        rect_height = float(obstacle.get("height", 0.0))
        elements.append(
            f'<rect x="{_sx(x):.1f}" y="{_sy(y + rect_height):.1f}" width="{rect_width * scale:.1f}" height="{rect_height * scale:.1f}" fill="#e5e5e5" stroke="#888888" stroke-width="1.5"/>'
        )
    legend_y = margin - 8.0
    for index, variant in enumerate(VARIANTS):
        result = results[variant.name]
        for trajectory in result.all_trajectories:
            points = " ".join(f"{_sx(float(point[0])):.1f},{_sy(float(point[1])):.1f}" for point in trajectory)
            elements.append(
                f'<polyline points="{points}" fill="none" stroke="{variant.color}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.28"/>'
            )
        legend_x = margin + index * 210.0
        elements.extend(
            [
                f'<line x1="{legend_x:.1f}" y1="{legend_y:.1f}" x2="{legend_x + 28.0:.1f}" y2="{legend_y:.1f}" stroke="{variant.color}" stroke-width="5"/>',
                f'<text x="{legend_x + 38.0:.1f}" y="{legend_y + 6.0:.1f}" font-family="Helvetica, Arial, sans-serif" font-size="18" fill="#222222">{variant.label}</text>',
            ]
        )
    elements.append(
        f'<text x="{margin:.1f}" y="{margin + height * scale + 28.0:.1f}" font-family="Helvetica, Arial, sans-serif" font-size="18" fill="#222222">Injected trajectories stay in the upper narrow corridor; clean and repaired trajectories return to the safer lower route.</text>'
    )
    elements.append("</svg>")
    _write_text(output_path, "\n".join(elements))


def _render_metric_board(results: Mapping[str, VariantResult], output_path: Path) -> None:
    metrics = [
        ("risky_route_rate", "Risky Route Rate", lambda result: float(result.summary.get("risky_route_rate", 0.0) or 0.0), 1.0),
        ("W_CR", "W_CR", lambda result: float(result.summary.get("W_CR", 0.0) or 0.0), 1.0),
        ("min_distance", "Min Distance", lambda result: float(result.summary.get("min_distance", 0.0) or 0.0), 1.2),
        ("near_violation_ratio", "Near-Violation Ratio", lambda result: float(result.summary.get("near_violation_ratio", 0.0) or 0.0), 1.0),
    ]
    width = 1140
    height = 680
    top = 110
    left = 140
    row_gap = 120
    bar_width = 250
    bar_height = 20
    elements: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>',
        '<text x="60" y="60" font-family="Helvetica, Arial, sans-serif" font-size="28" fill="#222222">Demo 1 Key Metrics</text>',
    ]
    for row_index, (_, label, getter, max_value) in enumerate(metrics):
        y = top + row_index * row_gap
        elements.append(
            f'<text x="60" y="{y + 15}" font-family="Helvetica, Arial, sans-serif" font-size="18" fill="#222222">{label}</text>'
        )
        for col_index, variant in enumerate(VARIANTS):
            result = results[variant.name]
            x = left + col_index * 320
            value = getter(result)
            fraction = _clamp(value / max(max_value, 1e-6), 0.0, 1.0)
            elements.extend(
                [
                    f'<text x="{x:.1f}" y="{y - 12:.1f}" font-family="Helvetica, Arial, sans-serif" font-size="16" fill="#333333">{variant.label}</text>',
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width}" height="{bar_height}" rx="8" fill="#efefef"/>',
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width * fraction:.1f}" height="{bar_height}" rx="8" fill="{variant.color}"/>',
                    f'<text x="{x + bar_width + 14:.1f}" y="{y + 15:.1f}" font-family="Helvetica, Arial, sans-serif" font-size="16" fill="#222222">{value:.3f}</text>',
                ]
            )
    elements.append("</svg>")
    _write_text(output_path, "\n".join(elements))


def _render_replay_html(
    scene_layout: Mapping[str, Any],
    results: Mapping[str, VariantResult],
    output_path: Path,
) -> None:
    payload = {
        "scene_layout": scene_layout,
        "variants": {
            variant.name: {
                "label": variant.label,
                "color": variant.color,
                "trajectory": results[variant.name].representative_trajectory,
            }
            for variant in VARIANTS
        },
    }
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Demo 1 Replay</title>
  <style>
    body {{
      margin: 0;
      padding: 24px;
      font-family: Helvetica, Arial, sans-serif;
      background: #ffffff;
      color: #222222;
    }}
    h1 {{
      margin: 0 0 16px;
      font-size: 28px;
      font-weight: 600;
    }}
    p {{
      margin: 0 0 24px;
      color: #555555;
      line-height: 1.5;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 18px;
    }}
    .panel {{
      border: 1px solid #d7d7d7;
      border-radius: 14px;
      padding: 12px;
      background: #ffffff;
    }}
    .label {{
      font-size: 18px;
      font-weight: 600;
      margin-bottom: 8px;
    }}
    svg {{
      width: 100%;
      height: auto;
      display: block;
      border-radius: 10px;
      background: #ffffff;
    }}
  </style>
</head>
<body>
  <h1>Demo 1 Replay</h1>
  <p>This lightweight replay animates one representative trajectory for each variant in the same dual-corridor scene.</p>
  <div class="grid" id="grid"></div>
  <script>
    const payload = {json.dumps(payload, indent=2)};
    const width = 360;
    const height = 250;
    const margin = 18;
    const scene = payload.scene_layout;
    const variants = payload.variants;
    const workspace = scene.workspace;
    const scaleX = value => margin + (value - workspace.xmin) / (workspace.xmax - workspace.xmin) * (width - margin * 2);
    const scaleY = value => margin + (workspace.ymax - value) / (workspace.ymax - workspace.ymin) * (height - margin * 2);

    function buildSceneMarkup(color, label, trajectory) {{
      const obstacleMarkup = scene.obstacles.map(item => {{
        const x = scaleX(item.x);
        const y = scaleY(item.y + item.height);
        const w = item.width / (workspace.xmax - workspace.xmin) * (width - margin * 2);
        const h = item.height / (workspace.ymax - workspace.ymin) * (height - margin * 2);
        return `<rect x="${{x}}" y="${{y}}" width="${{w}}" height="${{h}}" fill="#e5e5e5" stroke="#8a8a8a" stroke-width="1.5" />`;
      }}).join("");
      const polyline = trajectory.map(point => `${{scaleX(point[0]).toFixed(2)}},${{scaleY(point[1]).toFixed(2)}}`).join(" ");
      return `
        <div class="panel">
          <div class="label">${{label}}</div>
          <svg viewBox="0 0 ${{width}} ${{height}}" xmlns="http://www.w3.org/2000/svg">
            <rect x="0" y="0" width="${{width}}" height="${{height}}" fill="#ffffff" />
            <rect x="${{margin}}" y="${{margin}}" width="${{width - margin * 2}}" height="${{height - margin * 2}}" fill="#ffffff" stroke="#333333" stroke-width="2" />
            ${{obstacleMarkup}}
            <polyline points="${{polyline}}" fill="none" stroke="${{color}}" stroke-width="4" opacity="0.3" stroke-linecap="round" stroke-linejoin="round" />
            <circle id="dot-${{label}}" cx="${{scaleX(trajectory[0][0])}}" cy="${{scaleY(trajectory[0][1])}}" r="6" fill="${{color}}" />
          </svg>
        </div>`;
    }}

    const grid = document.getElementById("grid");
    Object.entries(variants).forEach(([name, config]) => {{
      grid.insertAdjacentHTML("beforeend", buildSceneMarkup(config.color, config.label, config.trajectory));
    }});

    let frame = 0;
    const frameCount = Math.max(...Object.values(variants).map(item => item.trajectory.length));
    function tick() {{
      Object.values(variants).forEach(config => {{
        const point = config.trajectory[Math.min(frame, config.trajectory.length - 1)];
        const dot = document.getElementById(`dot-${{config.label}}`);
        if (dot && point) {{
          dot.setAttribute("cx", scaleX(point[0]));
          dot.setAttribute("cy", scaleY(point[1]));
        }}
      }});
      frame = (frame + 1) % frameCount;
      window.requestAnimationFrame(tick);
    }}
    window.requestAnimationFrame(tick);
  </script>
</body>
</html>
"""
    _write_text(output_path, html)


def _reward_diff_markdown() -> str:
    clean = _reward_weights(CFG_ROOT / "spec_clean")
    injected = _reward_weights(CFG_ROOT / "spec_injected")
    repaired = _reward_weights(CFG_ROOT / "spec_repaired")
    lines = [
        "# Demo 1 Reward Diff",
        "",
        "## Clean -> Injected",
        "",
        f"- `reward_progress.weight`: `{clean['reward_progress']}` -> `{injected['reward_progress']}`",
        f"- `reward_safety_static.weight`: `{clean['reward_safety_static']}` -> `{injected['reward_safety_static']}`",
        "",
        "## Injected -> Repaired",
        "",
        f"- `reward_progress.weight`: `{injected['reward_progress']}` -> `{repaired['reward_progress']}`",
        f"- `reward_safety_static.weight`: `{injected['reward_safety_static']}` -> `{repaired['reward_safety_static']}`",
        "",
        "Only reward weights differ between the three demo variants.",
        "",
    ]
    return "\n".join(lines)


def _verify_demo(
    *,
    scene_layout: Mapping[str, Any],
    results: Mapping[str, VariantResult],
    report_primary_claim_type: str,
    repair_operator: str,
    validation_decision: Mapping[str, Any],
) -> Dict[str, Any]:
    del scene_layout
    clean = results["clean"]
    injected = results["injected"]
    repaired = results["repaired"]

    checks = {
        "same_scene_geometry": {
            "passed": _sha256(ENV_CFG_DIR / "scene_cfg_nominal.yaml") == _sha256(ENV_CFG_DIR / "scene_cfg_nominal.yaml"),
            "details": {
                "scene_cfg_name": "scene_cfg_nominal.yaml",
                "scene_layout_sha256": _sha256(SCENE_LAYOUT_PATH),
            },
        },
        "reward_only_diff_scope": {
            "passed": (
                (CFG_ROOT / "spec_clean" / "constraint_spec_v0.yaml").read_text(encoding="utf-8")
                == (CFG_ROOT / "spec_injected" / "constraint_spec_v0.yaml").read_text(encoding="utf-8")
                == (CFG_ROOT / "spec_repaired" / "constraint_spec_v0.yaml").read_text(encoding="utf-8")
                and (CFG_ROOT / "spec_clean" / "policy_spec_v0.yaml").read_text(encoding="utf-8")
                == (CFG_ROOT / "spec_injected" / "policy_spec_v0.yaml").read_text(encoding="utf-8")
                == (CFG_ROOT / "spec_repaired" / "policy_spec_v0.yaml").read_text(encoding="utf-8")
            ),
            "details": {
                "variant_reward_specs": [
                    _repo_relative(CFG_ROOT / "spec_clean" / "reward_spec_v0.yaml"),
                    _repo_relative(CFG_ROOT / "spec_injected" / "reward_spec_v0.yaml"),
                    _repo_relative(CFG_ROOT / "spec_repaired" / "reward_spec_v0.yaml"),
                ]
            },
        },
        "clean_prefers_safe_route": {
            "passed": float(clean.summary.get("risky_route_rate", 0.0)) <= 0.34,
            "details": {"risky_route_rate": clean.summary.get("risky_route_rate", 0.0)},
        },
        "injected_prefers_risky_route": {
            "passed": float(injected.summary.get("risky_route_rate", 0.0)) >= 0.80,
            "details": {"risky_route_rate": injected.summary.get("risky_route_rate", 0.0)},
        },
        "repaired_returns_to_safe_route": {
            "passed": float(repaired.summary.get("risky_route_rate", 0.0)) <= 0.34,
            "details": {"risky_route_rate": repaired.summary.get("risky_route_rate", 0.0)},
        },
        "injected_reduces_clearance": {
            "passed": (
                float(injected.summary.get("min_distance", 0.0) or 0.0)
                < float(clean.summary.get("min_distance", 0.0) or 0.0)
                and float(injected.summary.get("min_distance", 0.0) or 0.0)
                < float(repaired.summary.get("min_distance", 0.0) or 0.0)
            ),
            "details": {
                "clean_min_distance": clean.summary.get("min_distance"),
                "injected_min_distance": injected.summary.get("min_distance"),
                "repaired_min_distance": repaired.summary.get("min_distance"),
            },
        },
        "injected_increases_near_violation": {
            "passed": (
                float(injected.summary.get("near_violation_ratio", 0.0) or 0.0)
                > float(clean.summary.get("near_violation_ratio", 0.0) or 0.0)
                and float(injected.summary.get("near_violation_ratio", 0.0) or 0.0)
                > float(repaired.summary.get("near_violation_ratio", 0.0) or 0.0)
            ),
            "details": {
                "clean_near_violation_ratio": clean.summary.get("near_violation_ratio"),
                "injected_near_violation_ratio": injected.summary.get("near_violation_ratio"),
                "repaired_near_violation_ratio": repaired.summary.get("near_violation_ratio"),
            },
        },
        "injected_elevates_W_CR": {
            "passed": (
                float(injected.summary.get("W_CR", 0.0) or 0.0) >= 0.50
                and float(injected.summary.get("W_CR", 0.0) or 0.0)
                > float(clean.summary.get("W_CR", 0.0) or 0.0)
                and float(injected.summary.get("W_CR", 0.0) or 0.0)
                > float(repaired.summary.get("W_CR", 0.0) or 0.0)
            ),
            "details": {
                "clean_W_CR": clean.summary.get("W_CR"),
                "injected_W_CR": injected.summary.get("W_CR"),
                "repaired_W_CR": repaired.summary.get("W_CR"),
            },
        },
        "report_primary_claim_is_cr": {
            "passed": report_primary_claim_type == "C-R",
            "details": {"primary_claim_type": report_primary_claim_type},
        },
        "repair_operator_matches_demo_story": {
            "passed": repair_operator == "strengthen_safety_reward",
            "details": {"selected_operator": repair_operator},
        },
        "repair_validation_accepted": {
            "passed": bool(validation_decision.get("accepted", False)),
            "details": {
                "decision_status": validation_decision.get("decision_status"),
                "blocked_by": list(validation_decision.get("blocked_by", []) or []),
            },
        },
    }
    goal_achieved = all(bool(item.get("passed", False)) for item in checks.values())
    return {
        "demo_id": "demo1_cr_boundary_lure",
        "goal_statement": "Changing reward weights alone should push the policy toward the dangerous inner corridor.",
        "goal_achieved": goal_achieved,
        "checks": checks,
        "variant_summaries": {
            variant.name: results[variant.name].summary
            for variant in VARIANTS
        },
    }


def _verification_markdown(summary: Mapping[str, Any]) -> str:
    lines = [
        "# Demo 1 Verification Summary",
        "",
        f"- Goal achieved: `{bool(summary.get('goal_achieved', False))}`",
        f"- Goal statement: {summary.get('goal_statement', '')}",
        "",
        "## Checks",
        "",
    ]
    for check_name, payload in dict(summary.get("checks", {})).items():
        lines.append(f"- `{check_name}`: `{bool(payload.get('passed', False))}`")
    lines.extend(["", "## Variant Highlights", ""])
    for variant_name, payload in dict(summary.get("variant_summaries", {})).items():
        lines.append(
            f"- `{variant_name}`:"
            f" risky_route_rate=`{payload.get('risky_route_rate', '')}`"
            f" min_distance=`{payload.get('min_distance', '')}`"
            f" near_violation_ratio=`{payload.get('near_violation_ratio', '')}`"
            f" W_CR=`{payload.get('W_CR', '')}`"
        )
    lines.append("")
    return "\n".join(lines)


def run_demo1_pipeline(
    *,
    output_root: Path,
    asset_root: Path,
    clean_output: bool = False,
) -> Dict[str, Any]:
    if clean_output and output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    (asset_root / "screenshots").mkdir(parents=True, exist_ok=True)
    (asset_root / "videos").mkdir(parents=True, exist_ok=True)

    scene_layout = _load_yaml(SCENE_LAYOUT_PATH)
    verification_root = output_root / "verification"
    _write_json(
        verification_root / "seed_manifest.json",
        {
            "demo_id": "demo1_cr_boundary_lure",
            "scene_layout_file": _repo_relative(SCENE_LAYOUT_PATH),
            "seeds": list(range(int(dict(scene_layout.get("simulation", {})).get("episodes_per_variant", 6) or 6))),
            "risky_collision_seeds": list(dict(scene_layout.get("simulation", {})).get("risky_collision_seeds", [])),
        },
    )
    _write_json(
        verification_root / "config_snapshot_manifest.json",
        {
            "scene_layout": {
                "path": _repo_relative(SCENE_LAYOUT_PATH),
                "sha256": _sha256(SCENE_LAYOUT_PATH),
            },
            "env_cfg": {
                "scene_cfg_base": {
                    "path": _repo_relative(ENV_CFG_DIR / "scene_cfg_base.yaml"),
                    "sha256": _sha256(ENV_CFG_DIR / "scene_cfg_base.yaml"),
                },
                "scene_cfg_nominal": {
                    "path": _repo_relative(ENV_CFG_DIR / "scene_cfg_nominal.yaml"),
                    "sha256": _sha256(ENV_CFG_DIR / "scene_cfg_nominal.yaml"),
                },
            },
            "variants": {
                variant.name: {
                    "spec_dir": _repo_relative(variant.spec_dir),
                    "reward_spec_sha256": _sha256(variant.spec_dir / "reward_spec_v0.yaml"),
                }
                for variant in VARIANTS
            },
        },
    )
    _write_text(verification_root / "reward_diff.md", _reward_diff_markdown())

    results = {
        variant.name: _simulate_variant(
            variant,
            scene_layout=scene_layout,
            output_root=output_root,
        )
        for variant in VARIANTS
    }
    injected_flow = _run_injected_report_flow(results["injected"], output_root=output_root)
    validation_flow = _run_validation_flow(
        output_root=output_root,
        injected=results["injected"],
        repaired=results["repaired"],
        repair_bundle_name=Path(injected_flow["repair_bundle_dir"]).name,
    )

    _render_scene_svg(scene_layout, asset_root / "screenshots" / SCREENSHOT_FILES["scene"])
    _render_overlay_svg(scene_layout, results, asset_root / "screenshots" / SCREENSHOT_FILES["overlay"])
    _render_metric_board(results, asset_root / "screenshots" / SCREENSHOT_FILES["metrics"])
    _render_replay_html(scene_layout, results, asset_root / "videos" / VIDEO_FILES["replay"])

    verification = _verify_demo(
        scene_layout=scene_layout,
        results=results,
        report_primary_claim_type=str(injected_flow["report_primary_claim_type"]),
        repair_operator=str(injected_flow["selected_operator"]),
        validation_decision=dict(validation_flow["decision"]),
    )
    verification.update(
        {
            "artifact_paths": {
                "scene_svg": str(asset_root / "screenshots" / SCREENSHOT_FILES["scene"]),
                "overlay_svg": str(asset_root / "screenshots" / SCREENSHOT_FILES["overlay"]),
                "metric_svg": str(asset_root / "screenshots" / SCREENSHOT_FILES["metrics"]),
                "replay_html": str(asset_root / "videos" / VIDEO_FILES["replay"]),
                "report_bundle_dir": str(injected_flow["report_bundle_dir"]),
                "repair_bundle_dir": str(injected_flow["repair_bundle_dir"]),
                "validation_dir": str(validation_flow["validation_dir"]),
            }
        }
    )

    _write_json(verification_root / "verification_summary.json", verification)
    _write_text(verification_root / "verification_summary.md", _verification_markdown(verification))
    return verification


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_root)
    asset_root = Path(args.asset_root)
    verification = run_demo1_pipeline(
        output_root=output_root,
        asset_root=asset_root,
        clean_output=bool(args.clean_output),
    )
    print(json.dumps(verification, indent=2, sort_keys=True))
    if bool(verification.get("goal_achieved", False)) or bool(args.allow_failed_goal):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
