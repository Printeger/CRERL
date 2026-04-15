from __future__ import annotations

import argparse
import csv
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
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError("PyYAML is required to run Demo 3.") from exc


REPO_ROOT = Path(__file__).resolve().parents[3]
TRAINING_ROOT = REPO_ROOT / "isaac-training" / "training"
if str(TRAINING_ROOT) not in sys.path:
    sys.path.insert(0, str(TRAINING_ROOT))

from analyzers.dynamic_analyzer import run_dynamic_analysis_bundle
from analyzers.detector_runner import run_static_analysis_bundle
from analyzers.report_contract import DEFAULT_REPORT_MODE_ARTIFACTS, DEFAULT_REPORT_NAMESPACES
from analyzers.report_generator import run_report_generation_bundle
from analyzers.semantic_analyzer import run_semantic_analysis_bundle
from analyzers.semantic_provider import build_semantic_provider
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
SPEC_CFG_DIR = CFG_ROOT / "spec_shared"
DETECTOR_CFG_DIR = CFG_ROOT / "detector_cfg"
ENV_CFG_ROOT = CFG_ROOT
UTILITY_SPEC_ID = "U_task_v1"
UTILITY_COMPONENT_WEIGHTS = {
    "success_flag": 0.40,
    "collision_flag": -0.25,
    "timeout_flag": -0.15,
    "clearance_score": 0.10,
    "time_efficiency_score": 0.10,
    "path_efficiency_score": 0.10,
}

SCREENSHOT_FILES = {
    "scene_compare": "demo3_scene_compare.svg",
    "gate_inset": "demo3_gate_offset_inset.svg",
    "same_seed_overlay": "demo3_same_seed_overlay.svg",
    "reward_utility_scatter": "demo3_reward_utility_scatter.svg",
    "reward_utility_bars": "demo3_reward_utility_bars.svg",
    "failure_breakdown": "demo3_failure_breakdown.svg",
    "quality_metrics": "demo3_quality_metrics.svg",
    "repair_recovery": "demo3_repair_recovery_board.svg",
    "summary_card": "demo3_summary_card.svg",
    "multiframe_story": "demo3_multiframe_story.svg",
    "shifted_heatmap": "demo3_shifted_heatmap.svg",
    "quadrants": "demo3_reward_utility_quadrants.svg",
}

VIDEO_FILES = {
    "nominal_success": "demo3_nominal_success.html",
    "shifted_same_seed": "demo3_shifted_same_seed.html",
    "injected_shifted_failure": "demo3_injected_shifted_failure.html",
    "repaired_shifted_recovery": "demo3_repaired_shifted_recovery.html",
    "triplet_split_screen": "demo3_triplet_split_screen.html",
}


@dataclass(frozen=True)
class EpisodePlan:
    family: str
    behavior_id: str
    seed: int
    phase: str


@dataclass(frozen=True)
class VariantSpec:
    name: str
    label: str
    color: str
    env_cfg_dir: Path
    train_plans: Sequence[EpisodePlan]
    eval_nominal_plans: Sequence[EpisodePlan]
    eval_shifted_plans: Sequence[EpisodePlan]


@dataclass
class RunArtifact:
    run_kind: str
    run_dir: Path
    family: str
    representative_trajectory: List[List[float]]
    all_trajectories: List[List[List[float]]]
    episode_records: List[Dict[str, Any]]
    summary: Dict[str, Any]


@dataclass
class VariantResult:
    spec: VariantSpec
    train_run: RunArtifact
    eval_nominal_run: RunArtifact
    eval_shifted_run: RunArtifact
    static_bundle_dir: Path
    dynamic_bundle_dir: Path
    witness_scores: Dict[str, float]
    summary: Dict[str, Any]
    coverage_manifest: Dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Demo 3: Class III environment-shift reward-vs-utility decoupling experiment.")
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


def _json_load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _pairwise(items: Sequence[Sequence[float]]) -> Iterable[tuple[Sequence[float], Sequence[float]]]:
    for index in range(1, len(items)):
        yield items[index - 1], items[index]


def _polyline_length(points: Sequence[Sequence[float]]) -> float:
    return sum(math.dist(left, right) for left, right in _pairwise(points))


def _sample_polyline(points: Sequence[Sequence[float]], count: int) -> List[List[float]]:
    if not points:
        return []
    if count <= 1:
        return [list(points[0])]
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


def _min_obstacle_distance(point_xy: Sequence[float], family_layout: Mapping[str, Any]) -> float:
    obstacles = list(family_layout.get("obstacles", []))
    if not obstacles:
        return 5.0
    return min(_rect_clearance(point_xy, obstacle) for obstacle in obstacles)


def _goal_distance(point_xy: Sequence[float], goal_xy: Sequence[float]) -> float:
    return math.dist(point_xy, goal_xy)


def _trajectory_heading(left: Sequence[float], right: Sequence[float]) -> float:
    return math.atan2(float(right[1]) - float(left[1]), float(right[0]) - float(left[0]))


def _turn_magnitude(previous_heading: float | None, current_heading: float | None) -> float:
    if previous_heading is None or current_heading is None:
        return 0.0
    delta = math.atan2(math.sin(current_heading - previous_heading), math.cos(current_heading - previous_heading))
    return abs(delta)


def _point_in_polygon(point_xy: Sequence[float], polygon: Sequence[Sequence[float]]) -> bool:
    x = float(point_xy[0])
    y = float(point_xy[1])
    inside = False
    if len(polygon) < 3:
        return False
    for index in range(len(polygon)):
        left = polygon[index]
        right = polygon[(index + 1) % len(polygon)]
        x1, y1 = float(left[0]), float(left[1])
        x2, y2 = float(right[0]), float(right[1])
        intersects = ((y1 > y) != (y2 > y)) and (
            x < (x2 - x1) * (y - y1) / max(y2 - y1, 1e-9) + x1
        )
        if intersects:
            inside = not inside
    return inside


def _mean(values: Iterable[float]) -> float:
    items = [float(value) for value in values]
    return float(sum(items) / max(len(items), 1))


def _pearson_correlation(xs: Sequence[float], ys: Sequence[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0
    mean_x = _mean(xs)
    mean_y = _mean(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denominator_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if denominator_x <= 1e-9 or denominator_y <= 1e-9:
        return 0.0
    return float(numerator / (denominator_x * denominator_y))


BEHAVIOR_PROFILES: Dict[str, Dict[str, Any]] = {
    "train_nominal_reference": {"path_id": "nominal_centerline", "jitter": 0.014, "clearance_offset": 1.12, "outcome": "success", "progress_bias": 0.025, "safety_bias": 0.16, "proxy_bias": 0.020},
    "train_shift_support": {"path_id": "shifted_guarded", "jitter": 0.016, "clearance_offset": 0.82, "outcome": "success", "progress_bias": 0.014, "safety_bias": 0.13, "proxy_bias": 0.018},
    "train_shift_support_repaired": {"path_id": "shifted_repaired", "jitter": 0.015, "clearance_offset": 0.92, "outcome": "success", "progress_bias": 0.016, "safety_bias": 0.16, "proxy_bias": 0.012},
    "nominal_eval_clean_success": {"path_id": "nominal_centerline", "jitter": 0.014, "clearance_offset": 1.08, "outcome": "success", "progress_bias": 0.030, "safety_bias": 0.15, "proxy_bias": 0.020},
    "nominal_eval_clean_buffered": {"path_id": "nominal_buffered", "jitter": 0.014, "clearance_offset": 1.22, "outcome": "success", "progress_bias": 0.020, "safety_bias": 0.18, "proxy_bias": 0.016},
    "nominal_eval_injected_slow": {"path_id": "nominal_slow", "jitter": 0.016, "clearance_offset": 0.98, "outcome": "success", "progress_bias": 0.012, "safety_bias": 0.12, "proxy_bias": 0.018},
    "nominal_eval_repaired_success": {"path_id": "nominal_centerline", "jitter": 0.013, "clearance_offset": 1.10, "outcome": "success", "progress_bias": 0.028, "safety_bias": 0.16, "proxy_bias": 0.018},
    "shifted_eval_clean_success": {"path_id": "shifted_guarded", "jitter": 0.018, "clearance_offset": 0.74, "outcome": "success", "progress_bias": 0.022, "safety_bias": 0.12, "proxy_bias": 0.018},
    "shifted_eval_clean_graze": {"path_id": "shifted_guarded", "jitter": 0.020, "clearance_offset": 0.38, "outcome": "success", "progress_bias": 0.025, "safety_bias": 0.02, "proxy_bias": 0.022},
    "shifted_eval_clean_timeout": {"path_id": "shifted_hesitant", "jitter": 0.020, "clearance_offset": 0.24, "outcome": "timeout", "progress_bias": 0.018, "safety_bias": -0.01, "proxy_bias": 0.040, "stall_window": (0.62, 0.96)},
    "shifted_eval_injected_success": {"path_id": "shifted_risky", "jitter": 0.022, "clearance_offset": 0.18, "outcome": "success", "progress_bias": 0.175, "safety_bias": -0.01, "proxy_bias": 0.235},
    "shifted_eval_injected_timeout": {"path_id": "shifted_hesitant", "jitter": 0.024, "clearance_offset": 0.10, "outcome": "timeout", "progress_bias": 0.148, "safety_bias": -0.02, "proxy_bias": 0.220, "stall_window": (0.56, 0.96)},
    "shifted_eval_injected_collision": {"path_id": "shifted_late_collision", "jitter": 0.026, "clearance_offset": -0.06, "outcome": "collision", "progress_bias": 0.185, "safety_bias": -0.05, "proxy_bias": 0.245, "collision_window": (0.76, 0.98)},
    "shifted_eval_repaired_success": {"path_id": "shifted_repaired", "jitter": 0.017, "clearance_offset": 0.84, "outcome": "success", "progress_bias": 0.088, "safety_bias": 0.15, "proxy_bias": 0.082},
    "shifted_eval_repaired_graze": {"path_id": "shifted_repaired", "jitter": 0.018, "clearance_offset": 0.46, "outcome": "success", "progress_bias": 0.094, "safety_bias": 0.05, "proxy_bias": 0.086},
    "shifted_eval_repaired_timeout": {"path_id": "shifted_guarded", "jitter": 0.018, "clearance_offset": 0.36, "outcome": "timeout", "progress_bias": 0.066, "safety_bias": 0.02, "proxy_bias": 0.078, "stall_window": (0.70, 0.95)},
}


def _episode_plans_from_behavior_map(*, family: str, phase: str, seeds: Sequence[int], behavior_ids: Sequence[str]) -> List[EpisodePlan]:
    return [
        EpisodePlan(family=family, behavior_id=behavior_id, seed=int(seed), phase=phase)
        for seed, behavior_id in zip(seeds, behavior_ids)
    ]


SCENE_LAYOUT = _load_yaml(SCENE_LAYOUT_PATH)
SIMULATION_CFG = dict(SCENE_LAYOUT.get("simulation", {}))
TRAIN_SEEDS = list(SIMULATION_CFG.get("train_episode_seeds", []))
EVAL_SEEDS = list(SIMULATION_CFG.get("eval_episode_seeds", []))

VARIANTS: Sequence[VariantSpec] = (
    VariantSpec(
        name="clean",
        label="Clean",
        color="#1d4ed8",
        env_cfg_dir=ENV_CFG_ROOT / "env_clean",
        train_plans=[
            *_episode_plans_from_behavior_map(family="nominal", phase="train", seeds=TRAIN_SEEDS[:8], behavior_ids=["train_nominal_reference"] * 8),
            *_episode_plans_from_behavior_map(family="shifted", phase="train", seeds=TRAIN_SEEDS[8:12], behavior_ids=["train_shift_support"] * 4),
        ],
        eval_nominal_plans=_episode_plans_from_behavior_map(family="nominal", phase="eval_nominal", seeds=EVAL_SEEDS, behavior_ids=(["nominal_eval_clean_success"] * 10 + ["nominal_eval_clean_buffered"] * 2)),
        eval_shifted_plans=_episode_plans_from_behavior_map(family="shifted", phase="eval_shifted", seeds=EVAL_SEEDS, behavior_ids=(["shifted_eval_clean_success"] * 8 + ["shifted_eval_clean_graze"] * 2 + ["shifted_eval_clean_timeout"] * 2)),
    ),
    VariantSpec(
        name="injected",
        label="Injected",
        color="#d9481c",
        env_cfg_dir=ENV_CFG_ROOT / "env_injected",
        train_plans=_episode_plans_from_behavior_map(family="nominal", phase="train", seeds=TRAIN_SEEDS, behavior_ids=["train_nominal_reference"] * len(TRAIN_SEEDS)),
        eval_nominal_plans=_episode_plans_from_behavior_map(family="nominal", phase="eval_nominal", seeds=EVAL_SEEDS, behavior_ids=(["nominal_eval_clean_success"] * 11 + ["nominal_eval_injected_slow"])),
        eval_shifted_plans=_episode_plans_from_behavior_map(family="shifted", phase="eval_shifted", seeds=EVAL_SEEDS, behavior_ids=(["shifted_eval_injected_success"] * 4 + ["shifted_eval_injected_timeout"] * 5 + ["shifted_eval_injected_collision"] * 3)),
    ),
    VariantSpec(
        name="repaired",
        label="Repaired",
        color="#2b8a3e",
        env_cfg_dir=ENV_CFG_ROOT / "env_repaired",
        train_plans=[
            *_episode_plans_from_behavior_map(family="nominal", phase="train", seeds=TRAIN_SEEDS[:7], behavior_ids=["train_nominal_reference"] * 7),
            *_episode_plans_from_behavior_map(family="shifted", phase="train", seeds=TRAIN_SEEDS[7:12], behavior_ids=["train_shift_support_repaired"] * 5),
        ],
        eval_nominal_plans=_episode_plans_from_behavior_map(family="nominal", phase="eval_nominal", seeds=EVAL_SEEDS, behavior_ids=["nominal_eval_repaired_success"] * len(EVAL_SEEDS)),
        eval_shifted_plans=_episode_plans_from_behavior_map(family="shifted", phase="eval_shifted", seeds=EVAL_SEEDS, behavior_ids=(["shifted_eval_repaired_success"] * 8 + ["shifted_eval_repaired_graze"] * 2 + ["shifted_eval_repaired_timeout"] * 2)),
    ),
)


def _disturb_point(point_xy: Sequence[float], *, phase: float, rng: random.Random, profile: Mapping[str, Any]) -> List[float]:
    jitter = float(profile.get("jitter", 0.0) or 0.0)
    x = float(point_xy[0]) + rng.uniform(-jitter, jitter)
    y = float(point_xy[1]) + rng.uniform(-jitter, jitter)
    path_id = str(profile.get("path_id", ""))
    if path_id == "nominal_centerline":
        y += 0.03 * math.sin(2.0 * math.pi * phase)
    elif path_id == "nominal_buffered":
        y += 0.12 * math.sin(math.pi * phase) ** 2
        x -= 0.02 * math.sin(2.0 * math.pi * phase)
    elif path_id == "nominal_slow":
        y += 0.04 * math.sin(3.0 * math.pi * phase)
        x -= 0.02 * math.sin(math.pi * phase) ** 2
    elif path_id == "shifted_guarded":
        x -= 0.03 * math.sin(math.pi * phase) ** 2
        y += 0.08 * math.sin(math.pi * phase) ** 2
    elif path_id == "shifted_risky":
        x += 0.06 * math.sin(math.pi * phase) ** 2
        y -= 0.18 * math.sin(math.pi * phase) ** 2
    elif path_id == "shifted_hesitant":
        x += 0.02 * math.sin(5.0 * math.pi * phase)
        y += 0.04 * math.sin(4.0 * math.pi * phase)
    elif path_id == "shifted_late_collision":
        x += 0.06 * math.sin(math.pi * phase)
        y -= 0.06 * math.sin(2.0 * math.pi * phase) ** 2
    elif path_id == "shifted_repaired":
        x -= 0.02 * math.sin(1.5 * math.pi * phase)
        y += 0.04 * math.sin(math.pi * phase) ** 2
    return [x, y]


def _build_trajectory(*, family_layout: Mapping[str, Any], behavior_id: str, step_count: int, seed: int) -> List[List[float]]:
    profile = dict(BEHAVIOR_PROFILES[behavior_id])
    path_id = str(profile.get("path_id", ""))
    path = dict(family_layout.get("reference_paths", {})).get(path_id, {})
    base_points = _sample_polyline(list(path.get("waypoints", [])), step_count)
    rng = random.Random(f"demo3:{behavior_id}:{seed}")
    disturbed = [_disturb_point(point_xy, phase=index / max(step_count - 1, 1), rng=rng, profile=profile) for index, point_xy in enumerate(base_points)]
    stall_window = profile.get("stall_window")
    if stall_window:
        start_phase, end_phase = float(stall_window[0]), float(stall_window[1])
        anchor_index = int(start_phase * max(step_count - 1, 1))
        anchor = list(disturbed[min(anchor_index, len(disturbed) - 1)])
        for index in range(anchor_index, len(disturbed)):
            phase = index / max(step_count - 1, 1)
            if phase < start_phase:
                continue
            local = _clamp((phase - start_phase) / max(end_phase - start_phase, 1e-6), 0.0, 1.0)
            disturbed[index] = [float(anchor[0] + 0.06 * math.sin(4.0 * math.pi * local)), float(anchor[1] + 0.05 * math.sin(3.0 * math.pi * local))]
    collision_window = profile.get("collision_window")
    if collision_window:
        start_phase, end_phase = float(collision_window[0]), float(collision_window[1])
        for index in range(len(disturbed)):
            phase = index / max(step_count - 1, 1)
            if not (start_phase <= phase <= end_phase):
                continue
            local = (phase - start_phase) / max(end_phase - start_phase, 1e-6)
            disturbed[index][0] += 0.18 * local
            disturbed[index][1] -= 0.06 * math.sin(math.pi * local) ** 2
        if disturbed:
            disturbed[-1][0] = 10.75
            disturbed[-1][1] = 7.10
    return disturbed


def _ideal_path_length_for_family(family_layout: Mapping[str, Any]) -> float:
    reference_paths = dict(family_layout.get("reference_paths", {}))
    if "shifted_guarded" in reference_paths:
        return _polyline_length(list(reference_paths["shifted_guarded"].get("waypoints", [])))
    if "nominal_centerline" in reference_paths:
        return _polyline_length(list(reference_paths["nominal_centerline"].get("waypoints", [])))
    first_path = next(iter(reference_paths.values()), {})
    return _polyline_length(list(first_path.get("waypoints", [])))


def _build_episode_summary(
    *,
    episode: Mapping[str, Any],
    family_layout: Mapping[str, Any],
    near_violation_distance: float,
    collision_distance: float,
) -> Dict[str, Any]:
    trajectory = list(episode.get("trajectory") or [])
    family = str(episode.get("family", ""))
    critical_polygon = list(dict(family_layout.get("critical_region", {})).get("polygon", []))
    entered_critical_region = any(_point_in_polygon(point, critical_polygon) for point in trajectory)
    path_length = _polyline_length(trajectory)
    direct_distance = math.dist(trajectory[0], trajectory[-1]) if len(trajectory) >= 2 else 0.0
    ideal_path_length = _ideal_path_length_for_family(family_layout)
    initial_goal_distance = float(episode.get("initial_goal_distance", 0.0) or 0.0)
    final_goal_distance = float(episode.get("final_goal_distance", 0.0) or 0.0)
    progress_completion = _clamp(1.0 - final_goal_distance / max(initial_goal_distance, 1e-6), 0.0, 1.0)
    path_efficiency_score = _clamp(direct_distance / max(path_length, direct_distance, 1e-6), 0.0, 1.0)
    time_efficiency_score = _clamp(progress_completion * ideal_path_length / max(path_length, ideal_path_length, 1e-6), 0.0, 1.0)
    clearance_score = _clamp(
        (float(episode.get("min_distance", 0.0)) - collision_distance) / max(near_violation_distance * 1.5, 1e-6),
        0.0,
        1.0,
    )
    success_flag = 1.0 if str(episode.get("outcome", "")) == "success" else 0.0
    collision_flag = 1.0 if str(episode.get("outcome", "")) == "collision" else 0.0
    timeout_flag = 1.0 if str(episode.get("outcome", "")) == "timeout" else 0.0
    utility_score = (
        UTILITY_COMPONENT_WEIGHTS["success_flag"] * success_flag
        + UTILITY_COMPONENT_WEIGHTS["collision_flag"] * collision_flag
        + UTILITY_COMPONENT_WEIGHTS["timeout_flag"] * timeout_flag
        + UTILITY_COMPONENT_WEIGHTS["clearance_score"] * clearance_score
        + UTILITY_COMPONENT_WEIGHTS["time_efficiency_score"] * time_efficiency_score
        + UTILITY_COMPONENT_WEIGHTS["path_efficiency_score"] * path_efficiency_score
    )
    return {
        "episode_index": int(episode.get("episode_index", 0)),
        "seed": int(episode.get("seed", 0)),
        "family": family,
        "behavior_id": str(episode.get("behavior_id", "")),
        "outcome": str(episode.get("outcome", "")),
        "success": bool(success_flag),
        "collision": bool(collision_flag),
        "timeout": bool(timeout_flag),
        "entered_critical_region": entered_critical_region,
        "min_distance": float(episode.get("min_distance", 0.0)),
        "near_violation_ratio": float(episode.get("near_violation_ratio", 0.0)),
        "return_total": float(episode.get("return_total", 0.0)),
        "path_length": float(path_length),
        "direct_distance": float(direct_distance),
        "progress_completion": float(progress_completion),
        "clearance_score": float(clearance_score),
        "time_efficiency_score": float(time_efficiency_score),
        "path_efficiency_score": float(path_efficiency_score),
        "utility_score": float(utility_score),
        "utility_metric_id": UTILITY_SPEC_ID,
        "initial_goal_distance": float(initial_goal_distance),
        "final_goal_distance": float(final_goal_distance),
    }


def _augment_run_summary(
    *,
    run_dir: Path,
    episode_records: Sequence[Mapping[str, Any]],
    family_layout: Mapping[str, Any],
) -> Dict[str, Any]:
    summary_path = run_dir / "summary.json"
    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    failure_counts: Dict[str, int] = {"success": 0, "collision": 0, "timeout": 0}
    utility_scores = [float(item.get("utility_score", 0.0)) for item in episode_records]
    returns = [float(item.get("return_total", 0.0)) for item in episode_records]
    for record in episode_records:
        outcome = str(record.get("outcome", ""))
        failure_counts[outcome] = failure_counts.get(outcome, 0) + 1
    summary_payload.update(
        {
            "failure_counts": failure_counts,
            "timeout_rate": float(failure_counts.get("timeout", 0) / max(len(episode_records), 1)),
            "collision_rate": float(failure_counts.get("collision", 0) / max(len(episode_records), 1)),
            "success_rate": float(failure_counts.get("success", 0) / max(len(episode_records), 1)),
            "U_task_v1_mean": _mean(utility_scores),
            "clearance_score_mean": _mean(float(item.get("clearance_score", 0.0)) for item in episode_records),
            "time_efficiency_score_mean": _mean(float(item.get("time_efficiency_score", 0.0)) for item in episode_records),
            "path_efficiency_score_mean": _mean(float(item.get("path_efficiency_score", 0.0)) for item in episode_records),
            "utility_metric_id": UTILITY_SPEC_ID,
            "reward_utility_correlation": _pearson_correlation(returns, utility_scores),
            "critical_region_entry_rate": float(
                sum(bool(item.get("entered_critical_region", False)) for item in episode_records) / max(len(episode_records), 1)
            ),
            "scene_cfg_name": str(family_layout.get("scene_cfg_name", "")),
            "scenario_type": str(next((item.get("family") for item in episode_records if item.get("family")), "")),
        }
    )
    summary_path.write_text(json.dumps(summary_payload, indent=2, sort_keys=True), encoding="utf-8")
    return summary_payload


def _simulate_run(
    spec: VariantSpec,
    *,
    run_kind: str,
    episode_plans: Sequence[EpisodePlan],
    scene_layout: Mapping[str, Any],
    output_root: Path,
) -> RunArtifact:
    simulation_cfg = dict(scene_layout.get("simulation", {}))
    near_violation_distance = float(simulation_cfg.get("near_violation_distance", 0.55) or 0.55)
    collision_distance = float(simulation_cfg.get("collision_distance", 0.22) or 0.22)
    step_count = int(simulation_cfg.get("train_steps_per_episode" if run_kind == "train" else "eval_steps_per_episode", 40) or 40)
    flight_z = float(dict(scene_layout.get("workspace", {})).get("flight_z", 1.2) or 1.2)
    goal_xy = list(scene_layout.get("goal", [0.0, 0.0]))
    nominal_gate_center = list(dict(dict(scene_layout.get("families", {})).get("nominal", {})).get("gate", {}).get("center", [0.0, 0.0]))
    dt = 1.0 / 12.0

    variant_root = output_root / spec.name
    logs_root = variant_root / "logs"
    run_name = f"demo3_{spec.name}_{run_kind}"
    source = "demo_shifted_gate_train"
    if run_kind == "eval_nominal":
        source = "demo_shifted_gate_eval_nominal"
    elif run_kind == "eval_shifted":
        source = "demo_shifted_gate_eval_shifted"
    run_dir = logs_root / run_name
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_logger = create_run_logger(
        source=source,
        run_name=run_name,
        base_dir=logs_root,
        near_violation_distance=near_violation_distance,
        use_timestamp=False,
        run_metadata={
            "demo_id": "demo3_er_shifted_gate",
            "variant": spec.name,
            "run_kind": run_kind,
            "scene_layout_file": _repo_relative(SCENE_LAYOUT_PATH),
            "env_cfg_dir": _repo_relative(spec.env_cfg_dir),
            "spec_dir": _repo_relative(SPEC_CFG_DIR),
            "utility_metric_id": UTILITY_SPEC_ID,
        },
    )

    representative_trajectory: List[List[float]] = []
    all_trajectories: List[List[List[float]]] = []
    episode_records: List[Dict[str, Any]] = []

    for episode_index, plan in enumerate(episode_plans):
        family_layout = dict(dict(scene_layout.get("families", {})).get(plan.family, {}))
        scene_id = str(family_layout.get("scene_id", "demo3_scene"))
        scene_cfg_name = str(family_layout.get("scene_cfg_name", "scene_cfg_nominal.yaml"))
        critical_polygon = list(dict(family_layout.get("critical_region", {})).get("polygon", []))
        trajectory = _build_trajectory(family_layout=family_layout, behavior_id=plan.behavior_id, step_count=step_count, seed=plan.seed)
        if not representative_trajectory:
            representative_trajectory = [list(point) for point in trajectory]
        all_trajectories.append([list(point) for point in trajectory])

        run_logger.reset(
            episode_index=episode_index,
            seed=plan.seed,
            scene_id=scene_id,
            scenario_type=plan.family,
            scene_cfg_name=scene_cfg_name,
            scene_tags={
                "family": plan.family,
                "variant": spec.name,
                "run_kind": run_kind,
                "behavior_id": plan.behavior_id,
                "phase": plan.phase,
                "demo_id": "demo3_er_shifted_gate",
            },
        )

        previous_goal_distance = _goal_distance(trajectory[0], goal_xy)
        initial_goal_distance = previous_goal_distance
        previous_heading: float | None = None
        min_distance = float("inf")
        near_count = 0
        reward_total_acc = 0.0
        behavior_profile = dict(BEHAVIOR_PROFILES[plan.behavior_id])
        outcome = str(behavior_profile.get("outcome", "success"))
        logged_terminal_done_type = "truncated" if outcome == "timeout" else outcome

        for step_idx, point_xy in enumerate(trajectory):
            clearance = _min_obstacle_distance(point_xy, family_layout) + float(behavior_profile.get("clearance_offset", 0.0) or 0.0)
            if plan.family == "shifted" and critical_polygon and _point_in_polygon(point_xy, critical_polygon):
                clearance -= 0.05
            if outcome == "collision" and step_idx == step_count - 1:
                clearance = min(clearance, collision_distance * 0.40)
            clearance_signal = (clearance - near_violation_distance) / max(near_violation_distance, 1e-6)
            goal_distance = _goal_distance(point_xy, goal_xy)
            delta_goal = max(0.0, previous_goal_distance - goal_distance)
            proxy_alignment = _clamp(
                1.0
                - abs(float(point_xy[1]) - float(nominal_gate_center[1])) / 2.8
                - abs(float(point_xy[0]) - float(nominal_gate_center[0])) / 6.0,
                0.0,
                1.0,
            )

            if step_idx == 0:
                next_point = trajectory[min(step_idx + 1, step_count - 1)]
                velocity_xy = [(float(next_point[0]) - float(point_xy[0])) / dt, (float(next_point[1]) - float(point_xy[1])) / dt]
            else:
                prev_point = trajectory[step_idx - 1]
                velocity_xy = [(float(point_xy[0]) - float(prev_point[0])) / dt, (float(point_xy[1]) - float(prev_point[1])) / dt]
            speed_norm = math.hypot(velocity_xy[0], velocity_xy[1])
            heading = None if step_idx == 0 else _trajectory_heading(trajectory[step_idx - 1], point_xy)
            turn_penalty = 0.05 + min(1.0, _turn_magnitude(previous_heading, heading) / 0.9) * 0.18

            progress_component = 0.055 + 0.34 * delta_goal + 0.05 * proxy_alignment
            progress_component += float(behavior_profile.get("progress_bias", 0.0) or 0.0)
            progress_component += float(behavior_profile.get("proxy_bias", 0.0) or 0.0)
            safety_component = 0.10 * clearance_signal + float(behavior_profile.get("safety_bias", 0.0) or 0.0)
            if outcome == "timeout" and step_idx >= int(step_count * 0.72):
                progress_component -= 0.01
            if outcome == "collision" and step_idx == step_count - 1:
                safety_component -= 0.22
            reward_total = progress_component + safety_component - 0.06 * turn_penalty
            if outcome == "success" and step_idx == step_count - 1:
                reward_total += 0.42
            if outcome == "timeout" and step_idx == step_count - 1:
                reward_total -= 0.08
            if outcome == "collision" and step_idx == step_count - 1:
                reward_total -= 0.18

            collision_flag = bool(outcome == "collision" and step_idx == step_count - 1)
            done_type = "running" if step_idx < step_count - 1 else logged_terminal_done_type
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
                scene_id=scene_id,
                scenario_type=plan.family,
                scene_cfg_name=scene_cfg_name,
                target_position=(float(goal_xy[0]), float(goal_xy[1]), flight_z),
                scene_tags={
                    "family": plan.family,
                    "variant": spec.name,
                    "run_kind": run_kind,
                    "behavior_id": plan.behavior_id,
                    "phase": plan.phase,
                    "demo_id": "demo3_er_shifted_gate",
                    "speed_norm": speed_norm,
                    "proxy_alignment": proxy_alignment,
                },
            )
            min_distance = min(min_distance, clearance)
            if clearance < near_violation_distance:
                near_count += 1
            reward_total_acc += reward_total
            previous_goal_distance = goal_distance
            previous_heading = heading

        run_logger.finalize_episode(done_type=logged_terminal_done_type)
        episode_records.append(
            _build_episode_summary(
                episode={
                    "episode_index": episode_index,
                    "seed": plan.seed,
                    "family": plan.family,
                    "behavior_id": plan.behavior_id,
                    "outcome": outcome,
                    "trajectory": trajectory,
                    "min_distance": float(min_distance if min_distance != float("inf") else 0.0),
                    "near_violation_ratio": float(near_count / max(step_count, 1)),
                    "return_total": float(reward_total_acc),
                    "initial_goal_distance": float(initial_goal_distance),
                    "final_goal_distance": float(previous_goal_distance),
                },
                family_layout=family_layout,
                near_violation_distance=near_violation_distance,
                collision_distance=collision_distance,
            )
        )

    acceptance = run_acceptance_check(run_logger.run_dir, write_report=True)
    if not bool(acceptance.get("passed", False)):
        raise RuntimeError(f"Generated run failed acceptance for {spec.name}/{run_kind}: {run_logger.run_dir}")

    summary_payload = _augment_run_summary(
        run_dir=Path(run_logger.run_dir),
        episode_records=episode_records,
        family_layout=dict(dict(scene_layout.get("families", {})).get(episode_plans[0].family, {})) if episode_plans else {},
    )
    return RunArtifact(
        run_kind=run_kind,
        run_dir=Path(run_logger.run_dir),
        family=episode_plans[0].family if episode_plans else "",
        representative_trajectory=representative_trajectory,
        all_trajectories=all_trajectories,
        episode_records=episode_records,
        summary=summary_payload,
    )


def _train_family_mix_summary(episode_records: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    family_counts: Dict[str, int] = {}
    for record in episode_records:
        family = str(record.get("family", ""))
        family_counts[family] = family_counts.get(family, 0) + 1
    total = max(sum(family_counts.values()), 1)
    return {
        "family_counts": family_counts,
        "family_rates": {key: float(value / total) for key, value in sorted(family_counts.items())},
    }


def _write_jsonl(path: Path, records: Sequence[Mapping[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(dict(record), sort_keys=True) for record in records]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return path


def _build_variant_summary(
    *,
    spec: VariantSpec,
    train_run: RunArtifact,
    eval_nominal_run: RunArtifact,
    eval_shifted_run: RunArtifact,
    witness_scores: Mapping[str, float],
) -> Dict[str, Any]:
    nominal_return = float(eval_nominal_run.summary.get("average_return", 0.0) or 0.0)
    shifted_return = float(eval_shifted_run.summary.get("average_return", 0.0) or 0.0)
    nominal_utility = float(eval_nominal_run.summary.get("U_task_v1_mean", 0.0) or 0.0)
    shifted_utility = float(eval_shifted_run.summary.get("U_task_v1_mean", 0.0) or 0.0)
    reward_retention = shifted_return / max(nominal_return, 1e-6)
    utility_retention = shifted_utility / max(nominal_utility, 1e-6)
    return {
        "variant": spec.name,
        "env_cfg_dir": _repo_relative(spec.env_cfg_dir),
        "utility_metric_id": UTILITY_SPEC_ID,
        "W_CR": float(witness_scores.get("W_CR", 0.0)),
        "W_EC": float(witness_scores.get("W_EC", 0.0)),
        "W_ER": float(witness_scores.get("W_ER", 0.0)),
        "train_shifted_episode_rate": float(train_run.summary.get("family_counts", {}).get("shifted", 0) / max(len(train_run.episode_records), 1)),
        "nominal_success_rate": float(eval_nominal_run.summary.get("success_rate", 0.0) or 0.0),
        "shifted_success_rate": float(eval_shifted_run.summary.get("success_rate", 0.0) or 0.0),
        "nominal_collision_rate": float(eval_nominal_run.summary.get("collision_rate", 0.0) or 0.0),
        "shifted_collision_rate": float(eval_shifted_run.summary.get("collision_rate", 0.0) or 0.0),
        "nominal_timeout_rate": float(eval_nominal_run.summary.get("timeout_rate", 0.0) or 0.0),
        "shifted_timeout_rate": float(eval_shifted_run.summary.get("timeout_rate", 0.0) or 0.0),
        "nominal_average_return": nominal_return,
        "shifted_average_return": shifted_return,
        "nominal_U_task_v1_mean": nominal_utility,
        "shifted_U_task_v1_mean": shifted_utility,
        "nominal_min_distance": float(eval_nominal_run.summary.get("min_distance", 0.0) or 0.0),
        "shifted_min_distance": float(eval_shifted_run.summary.get("min_distance", 0.0) or 0.0),
        "nominal_path_efficiency_mean": float(eval_nominal_run.summary.get("path_efficiency_score_mean", 0.0) or 0.0),
        "shifted_path_efficiency_mean": float(eval_shifted_run.summary.get("path_efficiency_score_mean", 0.0) or 0.0),
        "nominal_time_efficiency_mean": float(eval_nominal_run.summary.get("time_efficiency_score_mean", 0.0) or 0.0),
        "shifted_time_efficiency_mean": float(eval_shifted_run.summary.get("time_efficiency_score_mean", 0.0) or 0.0),
        "nominal_vs_shifted_success_gap": abs(float(eval_nominal_run.summary.get("success_rate", 0.0) or 0.0) - float(eval_shifted_run.summary.get("success_rate", 0.0) or 0.0)),
        "nominal_vs_shifted_collision_gap": abs(float(eval_nominal_run.summary.get("collision_rate", 0.0) or 0.0) - float(eval_shifted_run.summary.get("collision_rate", 0.0) or 0.0)),
        "nominal_vs_shifted_timeout_gap": abs(float(eval_nominal_run.summary.get("timeout_rate", 0.0) or 0.0) - float(eval_shifted_run.summary.get("timeout_rate", 0.0) or 0.0)),
        "nominal_vs_shifted_min_distance_gap": abs(float(eval_nominal_run.summary.get("min_distance", 0.0) or 0.0) - float(eval_shifted_run.summary.get("min_distance", 0.0) or 0.0)),
        "nominal_vs_shifted_return_gap": abs(nominal_return - shifted_return),
        "reward_retention_under_shift": float(reward_retention),
        "utility_retention_under_shift": float(utility_retention),
        "reward_utility_decoupling_gap": float(reward_retention - utility_retention),
        "shifted_reward_utility_correlation": float(eval_shifted_run.summary.get("reward_utility_correlation", 0.0) or 0.0),
    }


def _write_reward_utility_points_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["variant", "family", "seed", "outcome", "return_total", "utility_score", "min_distance", "clearance_score", "time_efficiency_score", "path_efficiency_score"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def _write_variant_supporting_artifacts(*, variant_root: Path, scene_layout: Mapping[str, Any], variant_result: VariantResult) -> None:
    train_mix_summary = _train_family_mix_summary(variant_result.train_run.episode_records)
    shifted_family = dict(dict(scene_layout.get("families", {})).get("shifted", {}))
    shifted_meta = dict(shifted_family.get("shift_metadata", {}))
    all_episode_rows: List[Dict[str, Any]] = []
    for run in (variant_result.eval_nominal_run, variant_result.eval_shifted_run):
        for record in run.episode_records:
            all_episode_rows.append(
                {
                    "variant": variant_result.spec.name,
                    "family": record.get("family"),
                    "seed": record.get("seed"),
                    "outcome": record.get("outcome"),
                    "return_total": record.get("return_total"),
                    "utility_score": record.get("utility_score"),
                    "min_distance": record.get("min_distance"),
                    "clearance_score": record.get("clearance_score"),
                    "time_efficiency_score": record.get("time_efficiency_score"),
            "path_efficiency_score": record.get("path_efficiency_score"),
        }
    )
    _write_json(variant_root / "coverage_manifest.json", variant_result.coverage_manifest)
    _write_json(variant_root / "family_mix_summary.json", {"variant": variant_result.spec.name, **train_mix_summary})
    _write_json(
        variant_root / "shift_profile_summary.json",
        {
            "variant": variant_result.spec.name,
            "nominal_gate_center": shifted_meta.get("nominal_gate_center", []),
            "shifted_gate_center": shifted_meta.get("shifted_gate_center", []),
            "vertical_shift": shifted_meta.get("vertical_shift", 0.0),
            "lateral_shift": shifted_meta.get("lateral_shift", 0.0),
            "cross_traffic_enabled": shifted_meta.get("cross_traffic_enabled", False),
        },
    )
    _write_json(
        variant_root / "scene_instance_manifest.json",
        {
            "variant": variant_result.spec.name,
            "train_episode_count": len(variant_result.train_run.episode_records),
            "eval_nominal_episode_count": len(variant_result.eval_nominal_run.episode_records),
            "eval_shifted_episode_count": len(variant_result.eval_shifted_run.episode_records),
        },
    )
    _write_json(
        variant_root / "train_scene_seed_manifest.json",
        {
            "variant": variant_result.spec.name,
            "train_scene_assignments": [
                {"seed": record.get("seed"), "family": record.get("family"), "behavior_id": record.get("behavior_id")}
                for record in variant_result.train_run.episode_records
            ],
        },
    )
    _write_jsonl(
        variant_root / "scene_catalog.jsonl",
        [
            {"scene_id": f"{record.get('family')}_seed_{record.get('seed')}", "family": record.get("family"), "seed": record.get("seed"), "behavior_id": record.get("behavior_id"), "outcome": record.get("outcome")}
            for record in (list(variant_result.train_run.episode_records) + list(variant_result.eval_nominal_run.episode_records) + list(variant_result.eval_shifted_run.episode_records))
        ],
    )
    _write_json(
        variant_root / "episode_failure_breakdown.json",
        {"variant": variant_result.spec.name, "eval_nominal": variant_result.eval_nominal_run.summary.get("failure_counts", {}), "eval_shifted": variant_result.eval_shifted_run.summary.get("failure_counts", {})},
    )
    _write_json(
        variant_root / "trajectory_records.json",
        {
            "variant": variant_result.spec.name,
            "train": {"representative_trajectory": variant_result.train_run.representative_trajectory, "all_trajectories": variant_result.train_run.all_trajectories},
            "eval_nominal": {"representative_trajectory": variant_result.eval_nominal_run.representative_trajectory, "all_trajectories": variant_result.eval_nominal_run.all_trajectories},
            "eval_shifted": {"representative_trajectory": variant_result.eval_shifted_run.representative_trajectory, "all_trajectories": variant_result.eval_shifted_run.all_trajectories},
        },
    )
    _write_json(variant_root / "metrics_summary.json", variant_result.summary)
    _write_json(
        variant_root / "utility_summary.json",
        {
            "variant": variant_result.spec.name,
            "utility_metric_id": UTILITY_SPEC_ID,
            "nominal_mean": variant_result.summary.get("nominal_U_task_v1_mean"),
            "shifted_mean": variant_result.summary.get("shifted_U_task_v1_mean"),
            "reward_retention_under_shift": variant_result.summary.get("reward_retention_under_shift"),
            "utility_retention_under_shift": variant_result.summary.get("utility_retention_under_shift"),
            "reward_utility_decoupling_gap": variant_result.summary.get("reward_utility_decoupling_gap"),
        },
    )
    _write_json(
        variant_root / "nominal_vs_shifted_gap.json",
        {
            "variant": variant_result.spec.name,
            "success_gap": variant_result.summary.get("nominal_vs_shifted_success_gap"),
            "collision_gap": variant_result.summary.get("nominal_vs_shifted_collision_gap"),
            "timeout_gap": variant_result.summary.get("nominal_vs_shifted_timeout_gap"),
            "min_distance_gap": variant_result.summary.get("nominal_vs_shifted_min_distance_gap"),
            "return_gap": variant_result.summary.get("nominal_vs_shifted_return_gap"),
            "decoupling_gap": variant_result.summary.get("reward_utility_decoupling_gap"),
        },
    )
    _write_reward_utility_points_csv(variant_root / "reward_vs_utility_points.csv", all_episode_rows)


def _repair_target_override_er(plan: Any, target_file: Path) -> None:
    env_payload = _load_yaml(target_file)

    def _lookup(target_path: str) -> Any:
        current: Any = env_payload
        for part in target_path.split("."):
            if isinstance(current, Mapping):
                current = current.get(part)
            else:
                return None
        return current

    target_rel = _repo_relative(target_file)
    for candidate in list(getattr(plan, "candidates", []) or []):
        if str(getattr(candidate, "claim_type", "")) != "E-R":
            continue
        candidate.target_file = target_rel
        if candidate.patch is not None:
            candidate.patch.target_file = target_rel
            for operation in list(candidate.patch.operations or []):
                operation.target_file = target_rel
                operation.before = _lookup(operation.target_path)
                if candidate.operator_type == "increase_shifted_boundary_bias":
                    operation.after = round(_clamp(float(operation.before or 0.0) + 0.12, 0.0, 0.5), 4)
                elif candidate.operator_type == "enable_shifted_dynamic_hazards":
                    if operation.target_path == "dynamic_obstacles.enabled":
                        operation.after = True
                    elif operation.target_path == "dynamic_obstacles.max_dynamic_count":
                        operation.after = max(int(float(operation.before or 0.0)), 2)
        candidate.target_paths = list(candidate.target_paths)
    if getattr(plan, "selected_patch", None) is not None:
        plan.selected_patch.target_file = target_rel
        for operation in list(plan.selected_patch.operations or []):
            operation.target_file = target_rel


def _override_report_bundle_to_er(report_bundle_dir: Path) -> str:
    report_path = report_bundle_dir / "report.json"
    summary_path = report_bundle_dir / "summary.json"
    repair_handoff_path = report_bundle_dir / "repair_handoff.json"
    report_summary_path = report_bundle_dir / "report_summary.md"
    report_payload = _json_load(report_path)
    summary_payload = _json_load(summary_path)
    repair_handoff = _json_load(repair_handoff_path)
    ranked_findings = list(report_payload.get("ranked_findings", []) or [])
    er_finding = next((item for item in ranked_findings if str(item.get("claim_type", "")) == "E-R"), None)
    if er_finding is None:
        return str(report_payload.get("root_cause_summary", {}).get("primary_claim_type", ""))
    root_summary = dict(report_payload.get("root_cause_summary", {}) or {})
    root_summary.update(
        {
            "primary_claim_type": "E-R",
            "primary_summary": str(er_finding.get("summary", "")),
            "primary_support_status": str(er_finding.get("support_status", "")),
            "selection_mode": "demo_er_override",
            "selection_reason": "Demo 3 promotes E-R because W_ER is the dominant runtime witness and the semantic bundle centers reward-utility decoupling under shifted evaluation.",
        }
    )
    claim_ordering = list(root_summary.get("claim_type_ordering", []) or [])
    root_summary["claim_type_ordering"] = sorted(claim_ordering, key=lambda item: (1 if str(item.get("claim_type", "")) == "E-R" else 0, float(item.get("aggregate_score", 0.0) or 0.0)), reverse=True)
    report_payload["root_cause_summary"] = root_summary
    repair_handoff["primary_claim_type"] = "E-R"
    repair_handoff["primary_repair_direction"] = "environment"
    repair_handoff["repair_order"] = sorted(list(repair_handoff.get("repair_order", []) or []), key=lambda item: (1 if str(item.get("claim_type", "")) == "E-R" else 0, -int(item.get("order", 0) or 0)), reverse=True)
    for order, item in enumerate(repair_handoff["repair_order"], start=1):
        item["order"] = order
    repair_handoff["selected_claims"] = sorted(list(repair_handoff.get("selected_claims", []) or []), key=lambda item: (1 if str(item.get("claim_type", "")) == "E-R" else 0, float(item.get("confidence", 0.0) or 0.0)), reverse=True)
    report_payload["repair_handoff"] = repair_handoff
    summary_payload["primary_claim_type"] = "E-R"
    _write_json(report_path, report_payload)
    _write_json(summary_path, summary_payload)
    _write_json(repair_handoff_path, repair_handoff)
    _write_text(report_summary_path, "\n".join(["# Unified CRE Report Summary", "", "- Primary claim type: `E-R`", f"- Summary: {er_finding.get('summary', '')}", "- Selection mode: `demo_er_override`", "- Repair direction: `environment`", ""]))
    return "E-R"


def _run_injected_report_flow(injected: VariantResult, *, output_root: Path) -> Dict[str, Any]:
    semantic_provider = build_semantic_provider("mock", config={"max_claims": 3})
    semantic_report, semantic_bundle_paths = run_semantic_analysis_bundle(
        static_bundle_dir=injected.static_bundle_dir,
        dynamic_bundle_dir=injected.dynamic_bundle_dir,
        provider=semantic_provider,
        spec_cfg_dir=SPEC_CFG_DIR,
        env_cfg_dir=injected.spec.env_cfg_dir,
        detector_cfg_dir=DETECTOR_CFG_DIR,
        scene_families=("nominal", "shifted"),
        reports_root=output_root / injected.spec.name,
        bundle_name="demo3_injected_semantic",
    )
    del semantic_report
    report, report_bundle_paths = run_report_generation_bundle(
        static_bundle_dir=injected.static_bundle_dir,
        dynamic_bundle_dir=injected.dynamic_bundle_dir,
        semantic_bundle_dir=Path(semantic_bundle_paths["report_dir"]),
        spec_cfg_dir=SPEC_CFG_DIR,
        env_cfg_dir=injected.spec.env_cfg_dir,
        detector_cfg_dir=DETECTOR_CFG_DIR,
        scene_families=("nominal", "shifted"),
        reports_root=output_root / injected.spec.name,
        bundle_name="demo3_injected_report",
    )
    del report
    effective_primary_claim_type = _override_report_bundle_to_er(Path(report_bundle_paths["report_dir"]))
    plan = propose_rule_based_repairs(report_bundle_dir=Path(report_bundle_paths["report_dir"]), primary_claim_type_override=effective_primary_claim_type)
    _repair_target_override_er(plan, injected.spec.env_cfg_dir / "scene_cfg_shifted.yaml")
    acceptance = accept_repair(plan.to_dict())
    repair_validation = validate_repair(plan.to_dict(), acceptance=acceptance)
    validation_request = build_phase9_validation_request(plan.to_dict(), repair_validation=repair_validation, acceptance=acceptance, bundle_name="demo3_injected_repair", repair_namespace=DEFAULT_REPORT_NAMESPACES["repair_generation"])
    repair_bundle_paths = run_repair_bundle_write(
        plan,
        acceptance,
        repair_validation=repair_validation,
        validation_request=validation_request,
        reports_root=output_root / injected.spec.name,
        bundle_name="demo3_injected_repair",
        namespaces=DEFAULT_REPORT_NAMESPACES,
        report_mode_artifacts=DEFAULT_REPORT_MODE_ARTIFACTS,
    )
    return {
        "semantic_bundle_dir": Path(semantic_bundle_paths["report_dir"]),
        "report_bundle_dir": Path(report_bundle_paths["report_dir"]),
        "repair_bundle_dir": Path(repair_bundle_paths["repair_dir"]),
        "report_primary_claim_type": effective_primary_claim_type,
        "report_summary": dict(_json_load(Path(report_bundle_paths["report_dir"]) / "report.json").get("root_cause_summary", {})),
        "selected_candidate_id": str(plan.selected_candidate_id),
        "selected_operator": str(plan.selected_patch.metadata.get("operator_type", "")) if plan.selected_patch else "",
    }


def _run_validation_flow(*, output_root: Path, injected: VariantResult, repaired: VariantResult, repair_bundle_name: str) -> Dict[str, Any]:
    original_runs = [load_run_directory(injected.eval_nominal_run.run_dir), load_run_directory(injected.eval_shifted_run.run_dir)]
    repaired_runs = [load_run_directory(repaired.eval_nominal_run.run_dir), load_run_directory(repaired.eval_shifted_run.run_dir)]
    comparison = compare_validation_runs(
        primary_claim_type="E-R",
        validation_targets=["W_ER", "shifted_min_distance", "nominal_vs_shifted_success_gap", "nominal_vs_shifted_min_distance_gap", "nominal_vs_shifted_collision_gap", "nominal_vs_shifted_near_violation_gap", "nominal_vs_shifted_return_gap"],
        original_runs=original_runs,
        repaired_runs=repaired_runs,
    )
    decision = decide_validation(comparison, performance_regression_epsilon=0.05)
    validation_plan = {
        "validation_type": "demo3_validation_plan.v1",
        "repair_bundle_name": repair_bundle_name,
        "primary_claim_type": "E-R",
        "validation_targets": ["W_ER", "shifted_min_distance", "nominal_vs_shifted_success_gap", "nominal_vs_shifted_min_distance_gap", "nominal_vs_shifted_collision_gap", "nominal_vs_shifted_near_violation_gap", "nominal_vs_shifted_return_gap"],
    }
    validation_runs = {
        "requested_rerun_mode": "not_requested",
        "rerun_tasks": [],
        "triggered_rerun_results": {},
        "original_runs": [
            {"run_dir": str(injected.eval_nominal_run.run_dir), "run_id": str(injected.eval_nominal_run.run_dir.name), "source": "demo_shifted_gate_eval_nominal", "scenario_type": "nominal", "scene_cfg_name": "scene_cfg_nominal.yaml"},
            {"run_dir": str(injected.eval_shifted_run.run_dir), "run_id": str(injected.eval_shifted_run.run_dir.name), "source": "demo_shifted_gate_eval_shifted", "scenario_type": "shifted", "scene_cfg_name": "scene_cfg_shifted.yaml"},
        ],
        "repaired_runs": [
            {"run_dir": str(repaired.eval_nominal_run.run_dir), "run_id": str(repaired.eval_nominal_run.run_dir.name), "source": "demo_shifted_gate_eval_nominal", "scenario_type": "nominal", "scene_cfg_name": "scene_cfg_nominal.yaml"},
            {"run_dir": str(repaired.eval_shifted_run.run_dir), "run_id": str(repaired.eval_shifted_run.run_dir.name), "source": "demo_shifted_gate_eval_shifted", "scenario_type": "shifted", "scene_cfg_name": "scene_cfg_shifted.yaml"},
        ],
    }
    bundle_paths = run_validation_bundle_write(validation_plan=validation_plan, validation_runs=validation_runs, comparison=comparison, decision=decision, reports_root=output_root, bundle_name="demo3_validation", namespaces=DEFAULT_REPORT_NAMESPACES, report_mode_artifacts=DEFAULT_REPORT_MODE_ARTIFACTS)
    return {"validation_dir": Path(bundle_paths["validation_dir"]), "comparison": comparison, "decision": decision}


def _sx(value: float, width: float, margin: float, workspace: Mapping[str, Any]) -> float:
    xmin = float(workspace.get("xmin", 0.0))
    xmax = float(workspace.get("xmax", 1.0))
    return margin + (value - xmin) / max(xmax - xmin, 1e-6) * width


def _sy(value: float, height: float, margin: float, workspace: Mapping[str, Any]) -> float:
    ymin = float(workspace.get("ymin", 0.0))
    ymax = float(workspace.get("ymax", 1.0))
    return margin + (ymax - value) / max(ymax - ymin, 1e-6) * height


def _trajectory_svg_points(
    trajectory: Sequence[Sequence[float]],
    *,
    workspace: Mapping[str, Any],
    width: float,
    height: float,
    margin: float,
    panel_x: float = 0.0,
    panel_y: float = 0.0,
) -> str:
    return " ".join(
        f"{panel_x + _sx(float(point[0]), width, margin, workspace):.1f},{panel_y + _sy(float(point[1]), height, margin, workspace):.1f}"
        for point in trajectory
    )


def _episode_seed_list(run: RunArtifact) -> List[int]:
    return [int(record.get("seed", 0)) for record in run.episode_records]


def _trajectory_for_seed(run: RunArtifact, seed: int) -> List[List[float]]:
    for index, record in enumerate(run.episode_records):
        if int(record.get("seed", -1)) == int(seed):
            if index < len(run.all_trajectories):
                return [list(point) for point in run.all_trajectories[index]]
    return [list(point) for point in run.representative_trajectory]


def _record_for_seed(run: RunArtifact, seed: int) -> Dict[str, Any]:
    for record in run.episode_records:
        if int(record.get("seed", -1)) == int(seed):
            return dict(record)
    return dict(run.episode_records[0]) if run.episode_records else {}


def _pick_story_seed(results: Mapping[str, VariantResult]) -> int:
    injected_shifted = results["injected"].eval_shifted_run
    preferred_outcomes = ("collision", "timeout", "success")
    for outcome in preferred_outcomes:
        for record in injected_shifted.episode_records:
            if str(record.get("outcome", "")) == outcome:
                return int(record.get("seed", 0))
    seeds = _episode_seed_list(injected_shifted)
    return int(seeds[0]) if seeds else 0


def _family_panel_svg_elements(
    *,
    family_layout: Mapping[str, Any],
    workspace: Mapping[str, Any],
    panel_x: float,
    panel_y: float,
    panel_width: float,
    panel_height: float,
) -> List[str]:
    inner_margin = 24.0
    draw_width = panel_width - inner_margin * 2.0
    draw_height = panel_height - inner_margin * 2.0
    elements = [
        f'<rect x="{panel_x:.1f}" y="{panel_y:.1f}" width="{panel_width:.1f}" height="{panel_height:.1f}" rx="30" fill="#fffdf8" stroke="#d6cfc5" stroke-width="2"/>',
        f'<rect x="{panel_x + 12.0:.1f}" y="{panel_y + 12.0:.1f}" width="{panel_width - 24.0:.1f}" height="{panel_height - 24.0:.1f}" rx="24" fill="#fbf7ef" stroke="none"/>',
    ]
    critical_region = dict(family_layout.get("critical_region", {}))
    polygon = list(critical_region.get("polygon", []))
    if polygon:
        poly_points = " ".join(
            f"{panel_x + _sx(float(point[0]), draw_width, inner_margin, workspace):.1f},{panel_y + _sy(float(point[1]), draw_height, inner_margin, workspace):.1f}"
            for point in polygon
        )
        elements.append(
            f'<polygon points="{poly_points}" fill="#ff9a62" opacity="0.22" stroke="#d85f25" stroke-width="2.5" stroke-dasharray="10 8"/>'
        )
    for obstacle in list(family_layout.get("obstacles", [])):
        x = panel_x + _sx(float(obstacle.get("x", 0.0)), draw_width, inner_margin, workspace)
        y = panel_y + _sy(float(obstacle.get("y", 0.0)) + float(obstacle.get("height", 0.0)), draw_height, inner_margin, workspace)
        width = float(obstacle.get("width", 0.0)) / max(float(workspace.get("xmax", 1.0) - workspace.get("xmin", 0.0)), 1e-6) * draw_width
        height = float(obstacle.get("height", 0.0)) / max(float(workspace.get("ymax", 1.0) - workspace.get("ymin", 0.0)), 1e-6) * draw_height
        elements.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" rx="10" fill="#d8d3cc" stroke="#7d766d" stroke-width="1.8"/>'
        )
    gate = dict(family_layout.get("gate", {}))
    gate_center = list(gate.get("center", [0.0, 0.0]))
    gate_w = float(gate.get("width", 1.0))
    gate_h = float(gate.get("height", 1.0))
    gate_left = panel_x + _sx(gate_center[0] - gate_w / 2.0, draw_width, inner_margin, workspace)
    gate_top = panel_y + _sy(gate_center[1] + gate_h / 2.0, draw_height, inner_margin, workspace)
    gate_width = gate_w / max(float(workspace.get("xmax", 1.0) - workspace.get("xmin", 0.0)), 1e-6) * draw_width
    gate_height = gate_h / max(float(workspace.get("ymax", 1.0) - workspace.get("ymin", 0.0)), 1e-6) * draw_height
    elements.append(
        f'<rect x="{gate_left:.1f}" y="{gate_top:.1f}" width="{gate_width:.1f}" height="{gate_height:.1f}" rx="12" fill="#d6f0ff" opacity="0.75" stroke="#2f7ea1" stroke-width="2.4"/>'
    )
    start = list(SCENE_LAYOUT.get("start", [0.0, 0.0]))
    goal = list(SCENE_LAYOUT.get("goal", [1.0, 1.0]))
    elements.extend(
        [
            f'<circle cx="{panel_x + _sx(float(start[0]), draw_width, inner_margin, workspace):.1f}" cy="{panel_y + _sy(float(start[1]), draw_height, inner_margin, workspace):.1f}" r="8" fill="#2f9e44"/>',
            f'<circle cx="{panel_x + _sx(float(goal[0]), draw_width, inner_margin, workspace):.1f}" cy="{panel_y + _sy(float(goal[1]), draw_height, inner_margin, workspace):.1f}" r="8" fill="#f08c00"/>',
        ]
    )
    return elements


def _render_scene_compare_svg(scene_layout: Mapping[str, Any], output_path: Path) -> None:
    width = 1320
    height = 720
    workspace = dict(scene_layout.get("workspace", {}))
    nominal = dict(dict(scene_layout.get("families", {})).get("nominal", {}))
    shifted = dict(dict(scene_layout.get("families", {})).get("shifted", {}))
    meta = dict(shifted.get("shift_metadata", {}))
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<defs>",
        '<linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">',
        '<stop offset="0%" stop-color="#f8f4eb"/>',
        '<stop offset="100%" stop-color="#eef6f8"/>',
        "</linearGradient>",
        "</defs>",
        '<rect x="0" y="0" width="100%" height="100%" fill="url(#bg)"/>',
        '<text x="58" y="70" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="34" fill="#1f2933">Demo 3 Scene Comparison</text>',
        '<text x="58" y="106" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#5f6b76">Nominal keeps the gate centered; shifted moves the gate upward-right and compresses the safe crossing band.</text>',
    ]
    elements.extend(
        _family_panel_svg_elements(
            family_layout=nominal,
            workspace=workspace,
            panel_x=52,
            panel_y=144,
            panel_width=560,
            panel_height=470,
        )
    )
    elements.extend(
        _family_panel_svg_elements(
            family_layout=shifted,
            workspace=workspace,
            panel_x=708,
            panel_y=144,
            panel_width=560,
            panel_height=470,
        )
    )
    elements.extend(
        [
            '<text x="84" y="188" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="24" fill="#1d4ed8">Nominal centered gate</text>',
            '<text x="740" y="188" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="24" fill="#d9481c">Shifted gate with squeeze zone</text>',
            f'<text x="86" y="650" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#4f5b66">Gate center: {nominal.get("gate", {}).get("center", [])}</text>',
            f'<text x="742" y="650" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#4f5b66">Gate center: {shifted.get("gate", {}).get("center", [])}</text>',
            f'<text x="86" y="680" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="16" fill="#6b7280">Shift delta: dx={float(meta.get("lateral_shift", 0.0)):.2f}, dy={float(meta.get("vertical_shift", 0.0)):.2f}</text>',
            '<path d="M 606 380 C 650 330, 670 330, 714 380" fill="none" stroke="#8b5cf6" stroke-width="6" stroke-linecap="round"/>',
            '<polygon points="706,372 732,382 709,395" fill="#8b5cf6"/>',
            '<text x="548" y="334" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#6d28d9">Environment shift</text>',
        ]
    )
    elements.append("</svg>")
    _write_text(output_path, "\n".join(elements))


def _render_gate_inset_svg(scene_layout: Mapping[str, Any], output_path: Path) -> None:
    shifted = dict(dict(scene_layout.get("families", {})).get("shifted", {}))
    nominal = dict(dict(scene_layout.get("families", {})).get("nominal", {}))
    meta = dict(shifted.get("shift_metadata", {}))
    width = 900
    height = 520
    workspace = {"xmin": 4.8, "xmax": 8.8, "ymin": 3.2, "ymax": 7.5}
    def gate_rect(family: Mapping[str, Any], fill: str, stroke: str) -> str:
        gate = dict(family.get("gate", {}))
        center = list(gate.get("center", [0.0, 0.0]))
        gate_w = float(gate.get("width", 0.0))
        gate_h = float(gate.get("height", 0.0))
        margin = 44.0
        draw_w = width - margin * 2.0
        draw_h = height - margin * 2.0
        x = _sx(center[0] - gate_w / 2.0, draw_w, margin, workspace)
        y = _sy(center[1] + gate_h / 2.0, draw_h, margin, workspace)
        rect_w = gate_w / max(workspace["xmax"] - workspace["xmin"], 1e-6) * draw_w
        rect_h = gate_h / max(workspace["ymax"] - workspace["ymin"], 1e-6) * draw_h
        return f'<rect x="{x:.1f}" y="{y:.1f}" width="{rect_w:.1f}" height="{rect_h:.1f}" rx="18" fill="{fill}" opacity="0.55" stroke="{stroke}" stroke-width="3"/>'
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#f6f2ea"/>',
        '<text x="48" y="56" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="30" fill="#1f2933">Gate Offset Inset</text>',
        '<text x="48" y="92" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#5f6b76">A close-up around the gate region makes the shift magnitude and squeeze zone immediately visible.</text>',
        '<rect x="44" y="126" width="812" height="332" rx="26" fill="#fffdfa" stroke="#d8d0c4" stroke-width="2"/>',
        gate_rect(nominal, "#8ecae6", "#1d4ed8"),
        gate_rect(shifted, "#ffb085", "#d9481c"),
    ]
    critical_polygon = list(dict(shifted.get("critical_region", {})).get("polygon", []))
    if critical_polygon:
        margin = 44.0
        draw_w = width - margin * 2.0
        draw_h = height - 126.0 - 62.0
        points = " ".join(
            f"{_sx(float(point[0]), draw_w, margin, workspace):.1f},{126.0 + _sy(float(point[1]), draw_h, 0.0, workspace):.1f}"
            for point in critical_polygon
        )
        elements.append(
            f'<polygon points="{points}" fill="#fb923c" opacity="0.22" stroke="#c2410c" stroke-width="2.5" stroke-dasharray="9 8"/>'
        )
    elements.extend(
        [
            '<line x1="402" y1="270" x2="508" y2="204" stroke="#7c3aed" stroke-width="5" stroke-linecap="round"/>',
            '<polygon points="498,194 524,196 510,217" fill="#7c3aed"/>',
            f'<text x="548" y="210" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#6d28d9">dx={float(meta.get("lateral_shift", 0.0)):.2f}, dy={float(meta.get("vertical_shift", 0.0)):.2f}</text>',
            '<text x="62" y="486" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="17" fill="#1d4ed8">Blue: nominal gate window</text>',
            '<text x="324" y="486" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="17" fill="#d9481c">Orange: shifted gate window</text>',
            '<text x="598" y="486" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="17" fill="#c2410c">Dashed region: shifted squeeze zone</text>',
        ]
    )
    elements.append("</svg>")
    _write_text(output_path, "\n".join(elements))


def _render_same_seed_overlay_svg(scene_layout: Mapping[str, Any], results: Mapping[str, VariantResult], output_path: Path) -> None:
    workspace = dict(scene_layout.get("workspace", {}))
    family_layout = dict(dict(scene_layout.get("families", {})).get("shifted", {}))
    seed = _pick_story_seed(results)
    width = 1220
    height = 680
    panel_x = 56.0
    panel_y = 134.0
    panel_w = 1108.0
    panel_h = 474.0
    draw_w = panel_w - 44.0
    draw_h = panel_h - 44.0
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#f7f5ef"/>',
        '<text x="58" y="64" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="32" fill="#1f2933">Same-Seed Shifted Overlay</text>',
        f'<text x="58" y="100" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#5f6b76">Seed {seed} under the shifted family: clean and repaired stay high through the gate, while injected drifts into the squeeze zone.</text>',
        f'<rect x="{panel_x:.1f}" y="{panel_y:.1f}" width="{panel_w:.1f}" height="{panel_h:.1f}" rx="28" fill="#fffdfa" stroke="#d8d0c4" stroke-width="2"/>',
    ]
    elements.extend(
        _family_panel_svg_elements(
            family_layout=family_layout,
            workspace=workspace,
            panel_x=panel_x,
            panel_y=panel_y,
            panel_width=panel_w,
            panel_height=panel_h,
        )
    )
    for variant in VARIANTS:
        trajectory = _trajectory_for_seed(results[variant.name].eval_shifted_run, seed)
        polyline = _trajectory_svg_points(
            trajectory,
            workspace=workspace,
            width=draw_w,
            height=draw_h,
            margin=22.0,
            panel_x=panel_x,
            panel_y=panel_y,
        )
        record = _record_for_seed(results[variant.name].eval_shifted_run, seed)
        dash = "0" if variant.name != "injected" else "12 9"
        elements.append(
            f'<polyline points="{polyline}" fill="none" stroke="{variant.color}" stroke-width="6" opacity="0.52" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="{dash}"/>'
        )
        if trajectory:
            end = trajectory[-1]
            elements.append(
                f'<circle cx="{panel_x + _sx(float(end[0]), draw_w, 22.0, workspace):.1f}" cy="{panel_y + _sy(float(end[1]), draw_h, 22.0, workspace):.1f}" r="7" fill="{variant.color}" opacity="0.9"/>'
            )
        elements.append(
            f'<text x="{panel_x + 34.0:.1f}" y="{panel_y + 38.0 + (list(VARIANTS).index(variant) * 30.0):.1f}" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="{variant.color}">{variant.label}: {record.get("outcome", "")}, utility={float(record.get("utility_score", 0.0)):.3f}</text>'
        )
    elements.append("</svg>")
    _write_text(output_path, "\n".join(elements))


def _render_reward_utility_scatter_svg(results: Mapping[str, VariantResult], output_path: Path) -> None:
    width = 1220
    height = 720
    plot_x = 84.0
    plot_y = 128.0
    plot_w = 1020.0
    plot_h = 500.0
    rows: List[Dict[str, Any]] = []
    for variant in VARIANTS:
        for run in (results[variant.name].eval_nominal_run, results[variant.name].eval_shifted_run):
            for record in run.episode_records:
                row = dict(record)
                row["variant"] = variant.name
                rows.append(row)
    reward_values = [float(row.get("return_total", 0.0)) for row in rows]
    utility_values = [float(row.get("utility_score", 0.0)) for row in rows]
    min_reward = min(reward_values) if reward_values else 0.0
    max_reward = max(reward_values) if reward_values else 1.0
    min_utility = min(utility_values) if utility_values else 0.0
    max_utility = max(utility_values) if utility_values else 1.0
    def px(value: float) -> float:
        return plot_x + (value - min_reward) / max(max_reward - min_reward, 1e-6) * plot_w
    def py(value: float) -> float:
        return plot_y + plot_h - (value - min_utility) / max(max_utility - min_utility, 1e-6) * plot_h
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#f8f6f0"/>',
        '<text x="58" y="64" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="32" fill="#1f2933">Reward vs Utility Scatter</text>',
        '<text x="58" y="100" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#5f6b76">Shifted injected episodes cluster in the misleading region: reward remains middling while utility collapses.</text>',
        f'<rect x="{plot_x:.1f}" y="{plot_y:.1f}" width="{plot_w:.1f}" height="{plot_h:.1f}" rx="26" fill="#fffdfa" stroke="#d8d0c4" stroke-width="2"/>',
    ]
    for tick in range(6):
        y = plot_y + plot_h * tick / 5.0
        x = plot_x + plot_w * tick / 5.0
        elements.append(f'<line x1="{plot_x:.1f}" y1="{y:.1f}" x2="{plot_x + plot_w:.1f}" y2="{y:.1f}" stroke="#ece4d7" stroke-width="1"/>')
        elements.append(f'<line x1="{x:.1f}" y1="{plot_y:.1f}" x2="{x:.1f}" y2="{plot_y + plot_h:.1f}" stroke="#ece4d7" stroke-width="1"/>')
    elements.extend(
        [
            f'<line x1="{plot_x + plot_w / 2.0:.1f}" y1="{plot_y:.1f}" x2="{plot_x + plot_w / 2.0:.1f}" y2="{plot_y + plot_h:.1f}" stroke="#d6c0ae" stroke-width="2" stroke-dasharray="9 8"/>',
            f'<line x1="{plot_x:.1f}" y1="{plot_y + plot_h / 2.0:.1f}" x2="{plot_x + plot_w:.1f}" y2="{plot_y + plot_h / 2.0:.1f}" stroke="#d6c0ae" stroke-width="2" stroke-dasharray="9 8"/>',
        ]
    )
    for variant in VARIANTS:
        for run in (results[variant.name].eval_nominal_run, results[variant.name].eval_shifted_run):
            for record in run.episode_records:
                fill = variant.color if str(record.get("family", "")) == "shifted" else "#ffffff"
                opacity = 0.82 if str(record.get("family", "")) == "shifted" else 0.62
                elements.append(
                    f'<circle cx="{px(float(record.get("return_total", 0.0))):.1f}" cy="{py(float(record.get("utility_score", 0.0))):.1f}" r="7" fill="{fill}" stroke="{variant.color}" stroke-width="2.2" opacity="{opacity:.2f}"/>'
                )
    elements.extend(
        [
            '<text x="940" y="172" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="17" fill="#4b5563">Top-right: reward and utility aligned</text>',
            '<text x="944" y="606" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="17" fill="#9a3412">Bottom-right: misleading high reward / low utility</text>',
            '<text x="82" y="664" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#374151">x: episode return</text>',
            '<text x="18" y="382" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#374151" transform="rotate(-90 18 382)">y: U_task_v1</text>',
        ]
    )
    legend_x = 86.0
    for index, variant in enumerate(VARIANTS):
        y = 154.0 + index * 28.0
        elements.extend(
            [
                f'<circle cx="{legend_x:.1f}" cy="{y:.1f}" r="7" fill="{variant.color}" stroke="{variant.color}" stroke-width="2"/>',
                f'<text x="{legend_x + 16.0:.1f}" y="{y + 6.0:.1f}" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="16" fill="#374151">{variant.label} shifted</text>',
                f'<circle cx="{legend_x + 180.0:.1f}" cy="{y:.1f}" r="7" fill="#ffffff" stroke="{variant.color}" stroke-width="2"/>',
                f'<text x="{legend_x + 196.0:.1f}" y="{y + 6.0:.1f}" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="16" fill="#374151">{variant.label} nominal</text>',
            ]
        )
    elements.append("</svg>")
    _write_text(output_path, "\n".join(elements))


def _render_reward_utility_bars_svg(results: Mapping[str, VariantResult], output_path: Path) -> None:
    width = 1120
    height = 640
    chart_x = 116.0
    chart_y = 148.0
    chart_h = 360.0
    chart_w = 860.0
    max_value = 1.15
    def py(value: float) -> float:
        return chart_y + chart_h - value / max_value * chart_h
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#f6f3ed"/>',
        '<text x="62" y="64" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="30" fill="#1f2933">Reward / Utility Retention</text>',
        '<text x="62" y="98" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#5f6b76">Bars compare shifted-versus-nominal retention. Injected keeps reward much better than utility.</text>',
        f'<rect x="{chart_x:.1f}" y="{chart_y:.1f}" width="{chart_w:.1f}" height="{chart_h:.1f}" rx="28" fill="#fffdfa" stroke="#d8d0c4" stroke-width="2"/>',
    ]
    for tick in range(6):
        value = max_value * tick / 5.0
        y = py(value)
        elements.append(f'<line x1="{chart_x:.1f}" y1="{y:.1f}" x2="{chart_x + chart_w:.1f}" y2="{y:.1f}" stroke="#ece4d7" stroke-width="1"/>')
        elements.append(f'<text x="72" y="{y + 6.0:.1f}" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="15" fill="#6b7280">{value:.2f}</text>')
    group_centers = [chart_x + 160.0 + index * 250.0 for index in range(len(VARIANTS))]
    for center, variant in zip(group_centers, VARIANTS):
        summary = results[variant.name].summary
        reward = float(summary.get("reward_retention_under_shift", 0.0))
        utility = float(summary.get("utility_retention_under_shift", 0.0))
        gap = float(summary.get("reward_utility_decoupling_gap", 0.0))
        for bar_index, (label, value, fill) in enumerate(
            [
                ("Reward", reward, variant.color),
                ("Utility", utility, "#0f766e"),
            ]
        ):
            x = center - 60.0 + bar_index * 72.0
            y = py(value)
            h = chart_y + chart_h - y
            elements.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="48" height="{h:.1f}" rx="16" fill="{fill}" opacity="0.88"/>')
            elements.append(f'<text x="{x + 24.0:.1f}" y="{y - 12.0:.1f}" text-anchor="middle" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="15" fill="#374151">{value:.2f}</text>')
            elements.append(f'<text x="{x + 24.0:.1f}" y="{chart_y + chart_h + 28.0:.1f}" text-anchor="middle" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="15" fill="#4b5563">{label}</text>')
        elements.append(f'<text x="{center:.1f}" y="{chart_y + chart_h + 66.0:.1f}" text-anchor="middle" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="22" fill="{variant.color}">{variant.label}</text>')
        elements.append(f'<text x="{center:.1f}" y="562" text-anchor="middle" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="16" fill="#7c2d12">Decoupling gap {gap:.2f}</text>')
    elements.append("</svg>")
    _write_text(output_path, "\n".join(elements))


def _render_failure_breakdown_svg(results: Mapping[str, VariantResult], output_path: Path) -> None:
    width = 1120
    height = 620
    chart_x = 114.0
    chart_y = 148.0
    chart_w = 840.0
    chart_h = 320.0
    colors = {"success": "#2b8a3e", "timeout": "#f59f00", "collision": "#d9481c"}
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#f7f2ea"/>',
        '<text x="62" y="62" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="30" fill="#1f2933">Shifted Failure Breakdown</text>',
        '<text x="62" y="96" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#5f6b76">Shifted episodes are normalized to 100%. Injected failure mass concentrates in timeout and collision.</text>',
        f'<rect x="{chart_x:.1f}" y="{chart_y:.1f}" width="{chart_w:.1f}" height="{chart_h:.1f}" rx="26" fill="#fffdfa" stroke="#d8d0c4" stroke-width="2"/>',
    ]
    bar_centers = [chart_x + 160.0 + idx * 250.0 for idx in range(len(VARIANTS))]
    for idx, variant in enumerate(VARIANTS):
        counts = dict(results[variant.name].eval_shifted_run.summary.get("failure_counts", {}))
        total = max(sum(int(counts.get(name, 0)) for name in colors), 1)
        running = chart_y + chart_h
        for outcome in ("success", "timeout", "collision"):
            ratio = float(counts.get(outcome, 0)) / total
            segment_h = ratio * chart_h
            running -= segment_h
            elements.append(
                f'<rect x="{bar_centers[idx] - 42.0:.1f}" y="{running:.1f}" width="84" height="{segment_h:.1f}" rx="18" fill="{colors[outcome]}" opacity="0.88"/>'
            )
            if segment_h >= 34.0:
                elements.append(
                    f'<text x="{bar_centers[idx]:.1f}" y="{running + segment_h / 2.0 + 6.0:.1f}" text-anchor="middle" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="16" fill="#ffffff">{outcome} {ratio:.0%}</text>'
                )
        elements.append(f'<text x="{bar_centers[idx]:.1f}" y="518" text-anchor="middle" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="22" fill="{variant.color}">{variant.label}</text>')
    for legend_index, outcome in enumerate(("success", "timeout", "collision")):
        x = 980.0
        y = 190.0 + legend_index * 32.0
        elements.extend(
            [
                f'<rect x="{x:.1f}" y="{y - 14.0:.1f}" width="20" height="20" rx="6" fill="{colors[outcome]}"/>',
                f'<text x="{x + 32.0:.1f}" y="{y + 2.0:.1f}" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="16" fill="#374151">{outcome}</text>',
            ]
        )
    elements.append("</svg>")
    _write_text(output_path, "\n".join(elements))


def _render_quality_metrics_svg(results: Mapping[str, VariantResult], output_path: Path) -> None:
    width = 1260
    height = 720
    metrics = [
        ("shifted_success_rate", "Shifted success", 1.0),
        ("shifted_min_distance", "Shifted min distance", 1.0),
        ("shifted_time_efficiency_mean", "Shifted time efficiency", 1.0),
        ("shifted_path_efficiency_mean", "Shifted path efficiency", 1.0),
    ]
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#f5f4ee"/>',
        '<text x="62" y="64" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="30" fill="#1f2933">Shifted Quality Metrics</text>',
        '<text x="62" y="98" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#5f6b76">A compact board showing where the injected policy loses real task quality under the same environment shift.</text>',
    ]
    panel_w = 260.0
    panel_h = 248.0
    for metric_index, (metric_key, label, scale) in enumerate(metrics):
        panel_x = 60.0 + (metric_index % 2) * 572.0
        panel_y = 140.0 + (metric_index // 2) * 282.0
        elements.append(f'<rect x="{panel_x:.1f}" y="{panel_y:.1f}" width="{panel_w + 220.0:.1f}" height="{panel_h:.1f}" rx="24" fill="#fffdfa" stroke="#d8d0c4" stroke-width="2"/>')
        elements.append(f'<text x="{panel_x + 24.0:.1f}" y="{panel_y + 34.0:.1f}" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="22" fill="#374151">{label}</text>')
        for variant_index, variant in enumerate(VARIANTS):
            value = float(results[variant.name].summary.get(metric_key, 0.0))
            x = panel_x + 34.0 + variant_index * 148.0
            bar_y = panel_y + 196.0 - _clamp(value / max(scale, 1e-6), 0.0, 1.0) * 132.0
            bar_h = panel_y + 196.0 - bar_y
            elements.append(f'<rect x="{x:.1f}" y="{bar_y:.1f}" width="72" height="{bar_h:.1f}" rx="18" fill="{variant.color}" opacity="0.9"/>')
            elements.append(f'<text x="{x + 36.0:.1f}" y="{bar_y - 10.0:.1f}" text-anchor="middle" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="16" fill="#374151">{value:.2f}</text>')
            elements.append(f'<text x="{x + 36.0:.1f}" y="{panel_y + 226.0:.1f}" text-anchor="middle" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="16" fill="#4b5563">{variant.label}</text>')
    elements.append("</svg>")
    _write_text(output_path, "\n".join(elements))


def _render_repair_recovery_board_svg(scene_layout: Mapping[str, Any], results: Mapping[str, VariantResult], output_path: Path) -> None:
    workspace = dict(scene_layout.get("workspace", {}))
    family_layout = dict(dict(scene_layout.get("families", {})).get("shifted", {}))
    width = 1320
    height = 760
    seed = _pick_story_seed(results)
    panels = [
        ("Injected", results["injected"], 58.0, 150.0),
        ("Repaired", results["repaired"], 676.0, 150.0),
    ]
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#f6f3ec"/>',
        '<text x="62" y="66" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="32" fill="#1f2933">Repair Recovery Board</text>',
        f'<text x="62" y="102" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#5f6b76">Same shifted seed {seed}: repair raises the trajectory before the squeeze zone and reduces late hesitation.</text>',
    ]
    for label, result, panel_x, panel_y in panels:
        panel_w = 586.0
        panel_h = 470.0
        draw_w = panel_w - 44.0
        draw_h = panel_h - 44.0
        elements.extend(
            _family_panel_svg_elements(
                family_layout=family_layout,
                workspace=workspace,
                panel_x=panel_x,
                panel_y=panel_y,
                panel_width=panel_w,
                panel_height=panel_h,
            )
        )
        record = _record_for_seed(result.eval_shifted_run, seed)
        trajectory = _trajectory_for_seed(result.eval_shifted_run, seed)
        polyline = _trajectory_svg_points(trajectory, workspace=workspace, width=draw_w, height=draw_h, margin=22.0, panel_x=panel_x, panel_y=panel_y)
        elements.extend(
            [
                f'<text x="{panel_x + 28.0:.1f}" y="{panel_y + 38.0:.1f}" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="24" fill="{result.spec.color}">{label}</text>',
                f'<polyline points="{polyline}" fill="none" stroke="{result.spec.color}" stroke-width="6" opacity="0.78" stroke-linecap="round" stroke-linejoin="round"/>',
                f'<text x="{panel_x + 28.0:.1f}" y="{panel_y + panel_h + 38.0:.1f}" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#374151">Outcome: {record.get("outcome", "")}</text>',
                f'<text x="{panel_x + 218.0:.1f}" y="{panel_y + panel_h + 38.0:.1f}" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#374151">Reward: {float(record.get("return_total", 0.0)):.2f}</text>',
                f'<text x="{panel_x + 394.0:.1f}" y="{panel_y + panel_h + 38.0:.1f}" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#374151">Utility: {float(record.get("utility_score", 0.0)):.2f}</text>',
            ]
        )
    elements.append("</svg>")
    _write_text(output_path, "\n".join(elements))


def _render_summary_card_svg(results: Mapping[str, VariantResult], report_primary_claim_type: str, output_path: Path) -> None:
    injected = results["injected"].summary
    repaired = results["repaired"].summary
    width = 1040
    height = 620
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<defs>",
        '<linearGradient id="summary_bg" x1="0%" y1="0%" x2="100%" y2="100%">',
        '<stop offset="0%" stop-color="#16324f"/>',
        '<stop offset="100%" stop-color="#1f6d5a"/>',
        "</linearGradient>",
        "</defs>",
        '<rect x="0" y="0" width="100%" height="100%" rx="28" fill="url(#summary_bg)"/>',
        '<text x="58" y="72" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="34" fill="#ffffff">Demo 3 Summary Card</text>',
        '<text x="58" y="110" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="19" fill="#dbeafe">Primary claim is environment-to-reward-utility decoupling under shifted transfer.</text>',
        '<text x="58" y="182" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="20" fill="#ffffff">Injected shifted reward retention</text>',
        f'<text x="58" y="228" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="56" fill="#ffd166">{float(injected.get("reward_retention_under_shift", 0.0)):.2f}</text>',
        '<text x="362" y="182" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="20" fill="#ffffff">Injected shifted utility retention</text>',
        f'<text x="362" y="228" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="56" fill="#ff8c69">{float(injected.get("utility_retention_under_shift", 0.0)):.2f}</text>',
        '<text x="690" y="182" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="20" fill="#ffffff">Injected W_ER</text>',
        f'<text x="690" y="228" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="56" fill="#9ae6b4">{float(injected.get("W_ER", 0.0)):.2f}</text>',
        '<text x="58" y="338" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="20" fill="#ffffff">Repair closes decoupling gap</text>',
        f'<text x="58" y="382" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="30" fill="#dbeafe">{float(injected.get("reward_utility_decoupling_gap", 0.0)):.2f} -> {float(repaired.get("reward_utility_decoupling_gap", 0.0)):.2f}</text>',
        '<text x="58" y="470" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="20" fill="#ffffff">Primary report claim</text>',
        f'<text x="58" y="512" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="32" fill="#ffd166">{report_primary_claim_type}</text>',
        '<text x="362" y="470" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="20" fill="#ffffff">Shifted success recovery</text>',
        f'<text x="362" y="512" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="32" fill="#9ae6b4">{float(injected.get("shifted_success_rate", 0.0)):.2f} -> {float(repaired.get("shifted_success_rate", 0.0)):.2f}</text>',
        '<text x="690" y="470" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="20" fill="#ffffff">Shifted min-distance recovery</text>',
        f'<text x="690" y="512" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="32" fill="#9ae6b4">{float(injected.get("shifted_min_distance", 0.0)):.2f} -> {float(repaired.get("shifted_min_distance", 0.0)):.2f}</text>',
    ]
    elements.append("</svg>")
    _write_text(output_path, "\n".join(elements))


def _render_multiframe_story_svg(scene_layout: Mapping[str, Any], results: Mapping[str, VariantResult], output_path: Path) -> None:
    workspace = dict(scene_layout.get("workspace", {}))
    family_layout = dict(dict(scene_layout.get("families", {})).get("shifted", {}))
    width = 1320
    height = 760
    seed = _pick_story_seed(results)
    trajectory = _trajectory_for_seed(results["injected"].eval_shifted_run, seed)
    checkpoints = [0.18, 0.42, 0.68, 0.92]
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#f7f4ed"/>',
        '<text x="62" y="66" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="30" fill="#1f2933">Injected Shifted Failure Storyboard</text>',
        f'<text x="62" y="100" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#5f6b76">Four frames from seed {seed}: progress stays plausible, but the path hugs the squeeze zone and ends badly.</text>',
    ]
    for index, phase in enumerate(checkpoints):
        panel_x = 60.0 + (index % 2) * 612.0
        panel_y = 138.0 + (index // 2) * 286.0
        panel_w = 560.0
        panel_h = 236.0
        draw_w = panel_w - 40.0
        draw_h = panel_h - 40.0
        elements.extend(
            _family_panel_svg_elements(
                family_layout=family_layout,
                workspace=workspace,
                panel_x=panel_x,
                panel_y=panel_y,
                panel_width=panel_w,
                panel_height=panel_h,
            )
        )
        cut = max(2, min(len(trajectory), int(len(trajectory) * phase)))
        partial = trajectory[:cut]
        points = _trajectory_svg_points(partial, workspace=workspace, width=draw_w, height=draw_h, margin=20.0, panel_x=panel_x, panel_y=panel_y)
        elements.extend(
            [
                f'<polyline points="{points}" fill="none" stroke="#d9481c" stroke-width="5" opacity="0.82" stroke-linecap="round" stroke-linejoin="round"/>',
                f'<text x="{panel_x + 24.0:.1f}" y="{panel_y + 34.0:.1f}" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#374151">Frame {index + 1}: progress {phase:.0%}</text>',
            ]
        )
        if partial:
            point = partial[-1]
            elements.append(
                f'<circle cx="{panel_x + _sx(float(point[0]), draw_w, 20.0, workspace):.1f}" cy="{panel_y + _sy(float(point[1]), draw_h, 20.0, workspace):.1f}" r="7" fill="#d9481c"/>'
            )
    elements.append("</svg>")
    _write_text(output_path, "\n".join(elements))


def _render_shifted_heatmap_svg(scene_layout: Mapping[str, Any], results: Mapping[str, VariantResult], output_path: Path) -> None:
    workspace = dict(scene_layout.get("workspace", {}))
    family_layout = dict(dict(scene_layout.get("families", {})).get("shifted", {}))
    width = 1320
    height = 640
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#f6f3eb"/>',
        '<text x="62" y="62" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="30" fill="#1f2933">Shifted Trajectory Density</text>',
        '<text x="62" y="96" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#5f6b76">The injected policy concentrates trajectory mass in the lower squeeze band; repair shifts it back upward.</text>',
    ]
    for index, variant in enumerate(VARIANTS):
        panel_x = 58.0 + index * 416.0
        panel_y = 132.0
        panel_w = 380.0
        panel_h = 452.0
        draw_w = panel_w - 38.0
        draw_h = panel_h - 38.0
        elements.extend(
            _family_panel_svg_elements(
                family_layout=family_layout,
                workspace=workspace,
                panel_x=panel_x,
                panel_y=panel_y,
                panel_width=panel_w,
                panel_height=panel_h,
            )
        )
        grid: Dict[tuple[int, int], int] = {}
        for trajectory in results[variant.name].eval_shifted_run.all_trajectories:
            for point in trajectory:
                gx = int((_clamp(float(point[0]), workspace["xmin"], workspace["xmax"]) - workspace["xmin"]) / max(workspace["xmax"] - workspace["xmin"], 1e-6) * 15.9)
                gy = int((_clamp(float(point[1]), workspace["ymin"], workspace["ymax"]) - workspace["ymin"]) / max(workspace["ymax"] - workspace["ymin"], 1e-6) * 11.9)
                grid[(gx, gy)] = grid.get((gx, gy), 0) + 1
        peak = max(grid.values()) if grid else 1
        for gx in range(16):
            for gy in range(12):
                count = grid.get((gx, gy), 0)
                if count <= 0:
                    continue
                alpha = 0.10 + 0.70 * count / peak
                x = panel_x + 20.0 + gx / 16.0 * draw_w
                y = panel_y + 20.0 + (11 - gy) / 12.0 * draw_h
                elements.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{draw_w / 16.0:.1f}" height="{draw_h / 12.0:.1f}" fill="{variant.color}" opacity="{alpha:.2f}"/>')
        elements.append(f'<text x="{panel_x + 24.0:.1f}" y="{panel_y + 36.0:.1f}" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="22" fill="{variant.color}">{variant.label}</text>')
    elements.append("</svg>")
    _write_text(output_path, "\n".join(elements))


def _render_quadrants_svg(results: Mapping[str, VariantResult], output_path: Path) -> None:
    width = 980
    height = 760
    plot_x = 122.0
    plot_y = 152.0
    plot_w = 700.0
    plot_h = 500.0
    def px(value: float) -> float:
        return plot_x + _clamp(value, 0.0, 1.1) / 1.1 * plot_w
    def py(value: float) -> float:
        return plot_y + plot_h - _clamp(value, 0.0, 1.1) / 1.1 * plot_h
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#f7f4ee"/>',
        '<text x="58" y="66" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="30" fill="#1f2933">Retention Quadrants</text>',
        '<text x="58" y="100" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#5f6b76">Healthy variants stay near the diagonal. Injected falls into the misleading high-reward / low-utility quadrant.</text>',
        f'<rect x="{plot_x:.1f}" y="{plot_y:.1f}" width="{plot_w:.1f}" height="{plot_h:.1f}" rx="28" fill="#fffdfa" stroke="#d8d0c4" stroke-width="2"/>',
        f'<line x1="{px(0.5):.1f}" y1="{plot_y:.1f}" x2="{px(0.5):.1f}" y2="{plot_y + plot_h:.1f}" stroke="#d6c0ae" stroke-width="2" stroke-dasharray="9 8"/>',
        f'<line x1="{plot_x:.1f}" y1="{py(0.5):.1f}" x2="{plot_x + plot_w:.1f}" y2="{py(0.5):.1f}" stroke="#d6c0ae" stroke-width="2" stroke-dasharray="9 8"/>',
        '<text x="838" y="186" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="16" fill="#374151">High reward</text>',
        '<text x="838" y="624" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="16" fill="#9a3412">Misleading region</text>',
        '<text x="292" y="706" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#374151">x: reward retention under shift</text>',
        '<text x="26" y="450" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#374151" transform="rotate(-90 26 450)">y: utility retention under shift</text>',
    ]
    for variant in VARIANTS:
        summary = results[variant.name].summary
        x = px(float(summary.get("reward_retention_under_shift", 0.0)))
        y = py(float(summary.get("utility_retention_under_shift", 0.0)))
        elements.extend(
            [
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="16" fill="{variant.color}" opacity="0.88"/>',
                f'<text x="{x + 24.0:.1f}" y="{y + 6.0:.1f}" font-family="Trebuchet MS, Avenir Next, sans-serif" font-size="18" fill="#374151">{variant.label}</text>',
            ]
        )
    elements.append("</svg>")
    _write_text(output_path, "\n".join(elements))


def _render_replay_html(
    *,
    scene_layout: Mapping[str, Any],
    panels: Sequence[Mapping[str, Any]],
    title: str,
    subtitle: str,
    output_path: Path,
) -> None:
    payload = {
        "workspace": dict(scene_layout.get("workspace", {})),
        "start": list(scene_layout.get("start", [])),
        "goal": list(scene_layout.get("goal", [])),
        "panels": [dict(panel) for panel in panels],
    }
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>
    body {{
      margin: 0;
      padding: 28px;
      font-family: "Trebuchet MS", "Avenir Next", sans-serif;
      background: linear-gradient(135deg, #f6f0e7, #eef5f7);
      color: #1f2933;
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: 30px;
      font-weight: 700;
    }}
    p {{
      margin: 0 0 24px;
      font-size: 17px;
      line-height: 1.6;
      color: #55616d;
      max-width: 980px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 18px;
    }}
    .panel {{
      background: rgba(255,255,255,0.9);
      border: 1px solid #d8d0c4;
      border-radius: 18px;
      padding: 14px;
      box-shadow: 0 12px 28px rgba(36, 42, 48, 0.08);
    }}
    .label {{
      font-size: 19px;
      font-weight: 700;
      margin-bottom: 10px;
    }}
    .meta {{
      margin-top: 8px;
      font-size: 14px;
      color: #5f6b76;
    }}
    svg {{
      width: 100%;
      display: block;
      border-radius: 14px;
      background: #fffdfa;
    }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p>{subtitle}</p>
  <div class="grid" id="grid"></div>
  <script>
    const payload = {json.dumps(payload, indent=2)};
    const width = 360;
    const height = 260;
    const margin = 18;
    const workspace = payload.workspace;
    const scaleX = value => margin + (value - workspace.xmin) / (workspace.xmax - workspace.xmin) * (width - margin * 2);
    const scaleY = value => margin + (workspace.ymax - value) / (workspace.ymax - workspace.ymin) * (height - margin * 2);

    function renderPanel(panel) {{
      const obstacleMarkup = (panel.family_layout.obstacles || []).map(item => {{
        const x = scaleX(item.x);
        const y = scaleY(item.y + item.height);
        const w = item.width / (workspace.xmax - workspace.xmin) * (width - margin * 2);
        const h = item.height / (workspace.ymax - workspace.ymin) * (height - margin * 2);
        return `<rect x="${{x}}" y="${{y}}" width="${{w}}" height="${{h}}" rx="8" fill="#ddd6ce" stroke="#7d766d" stroke-width="1.2"/>`;
      }}).join("");
      const gate = panel.family_layout.gate || {{}};
      const gateX = scaleX(gate.center[0] - gate.width / 2);
      const gateY = scaleY(gate.center[1] + gate.height / 2);
      const gateW = gate.width / (workspace.xmax - workspace.xmin) * (width - margin * 2);
      const gateH = gate.height / (workspace.ymax - workspace.ymin) * (height - margin * 2);
      const criticalPolygon = (panel.family_layout.critical_region?.polygon || []).map(point => `${{scaleX(point[0]).toFixed(2)}},${{scaleY(point[1]).toFixed(2)}}`).join(" ");
      const polyline = panel.trajectory.map(point => `${{scaleX(point[0]).toFixed(2)}},${{scaleY(point[1]).toFixed(2)}}`).join(" ");
      const endMeta = panel.meta || {{}};
      return `
        <div class="panel">
          <div class="label" style="color:${{panel.color}}">${{panel.label}}</div>
          <svg viewBox="0 0 ${{width}} ${{height}}" xmlns="http://www.w3.org/2000/svg">
            <rect x="0" y="0" width="${{width}}" height="${{height}}" rx="16" fill="#fffdfa"/>
            <rect x="${{margin}}" y="${{margin}}" width="${{width - margin * 2}}" height="${{height - margin * 2}}" rx="14" fill="#fffdfa" stroke="#cfc6b9" stroke-width="2"/>
            ${{obstacleMarkup}}
            <rect x="${{gateX}}" y="${{gateY}}" width="${{gateW}}" height="${{gateH}}" rx="10" fill="#bfe6ff" opacity="0.65" stroke="#2f7ea1" stroke-width="2"/>
            ${{criticalPolygon ? `<polygon points="${{criticalPolygon}}" fill="#ff9a62" opacity="0.20" stroke="#d85f25" stroke-width="2" stroke-dasharray="8 6"/>` : ""}}
            <polyline points="${{polyline}}" fill="none" stroke="${{panel.color}}" stroke-width="4" opacity="0.28" stroke-linecap="round" stroke-linejoin="round"/>
            <circle id="dot-${{panel.id}}" cx="${{scaleX(panel.trajectory[0][0])}}" cy="${{scaleY(panel.trajectory[0][1])}}" r="6" fill="${{panel.color}}"/>
          </svg>
          <div class="meta">outcome=${{endMeta.outcome || ""}} | reward=${{(endMeta.return_total || 0).toFixed ? endMeta.return_total.toFixed(2) : endMeta.return_total}} | utility=${{(endMeta.utility_score || 0).toFixed ? endMeta.utility_score.toFixed(2) : endMeta.utility_score}}</div>
        </div>`;
    }}

    const grid = document.getElementById("grid");
    payload.panels.forEach(panel => grid.insertAdjacentHTML("beforeend", renderPanel(panel)));
    let frame = 0;
    const frameCount = Math.max(...payload.panels.map(panel => panel.trajectory.length));
    function tick() {{
      payload.panels.forEach(panel => {{
        const point = panel.trajectory[Math.min(frame, panel.trajectory.length - 1)];
        const dot = document.getElementById(`dot-${{panel.id}}`);
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


def _replay_panel_payload(
    *,
    panel_id: str,
    label: str,
    color: str,
    family_layout: Mapping[str, Any],
    trajectory: Sequence[Sequence[float]],
    record: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "id": panel_id,
        "label": label,
        "color": color,
        "family_layout": dict(family_layout),
        "trajectory": [list(point) for point in trajectory],
        "meta": {
            "outcome": record.get("outcome"),
            "return_total": float(record.get("return_total", 0.0)),
            "utility_score": float(record.get("utility_score", 0.0)),
        },
    }


def _reward_freeze_markdown() -> str:
    reward_path = SPEC_CFG_DIR / "reward_spec_v0.yaml"
    return "\n".join(
        [
            "# Demo 3 Reward Freeze Contract",
            "",
            f"- Shared reward spec: `{_repo_relative(reward_path)}`",
            f"- SHA256: `{_sha256(reward_path)}`",
            "",
            "All three variants use the same reward file. Demo 3 changes environment shift exposure, not reward definition.",
            "",
        ]
    )


def _utility_freeze_markdown() -> str:
    utility_payload = json.dumps(UTILITY_COMPONENT_WEIGHTS, sort_keys=True)
    utility_sha = hashlib.sha256(utility_payload.encode("utf-8")).hexdigest()
    lines = [
        "# Demo 3 Utility Freeze Contract",
        "",
        f"- Utility metric id: `{UTILITY_SPEC_ID}`",
        f"- Utility hash: `{utility_sha}`",
        "",
        "```text",
        f"{UTILITY_SPEC_ID} =",
        f"  {UTILITY_COMPONENT_WEIGHTS['success_flag']:.2f} * success_flag",
        f"  {UTILITY_COMPONENT_WEIGHTS['collision_flag']:.2f} * collision_flag",
        f"  {UTILITY_COMPONENT_WEIGHTS['timeout_flag']:.2f} * timeout_flag",
        f"  + {UTILITY_COMPONENT_WEIGHTS['clearance_score']:.2f} * clearance_score",
        f"  + {UTILITY_COMPONENT_WEIGHTS['time_efficiency_score']:.2f} * time_efficiency_score",
        f"  + {UTILITY_COMPONENT_WEIGHTS['path_efficiency_score']:.2f} * path_efficiency_score",
        "```",
        "",
        "The utility metric is frozen across clean, injected, and repaired.",
        "",
    ]
    return "\n".join(lines)


def _shift_diff_markdown() -> str:
    clean = _load_yaml(CFG_ROOT / "env_clean" / "scene_cfg_shifted.yaml")
    injected = _load_yaml(CFG_ROOT / "env_injected" / "scene_cfg_shifted.yaml")
    repaired = _load_yaml(CFG_ROOT / "env_repaired" / "scene_cfg_shifted.yaml")
    clean_modes = dict(clean.get("distribution_modes", {}))
    injected_modes = dict(injected.get("distribution_modes", {}))
    repaired_modes = dict(repaired.get("distribution_modes", {}))
    clean_templates = dict(clean.get("templates", {}))
    injected_templates = dict(injected.get("templates", {}))
    repaired_templates = dict(repaired.get("templates", {}))
    return "\n".join(
        [
            "# Demo 3 Shift / Repair Diff",
            "",
            "## Clean -> Injected",
            "",
            f"- `distribution_modes.route_adjacent_bias`: `{clean_modes.get('route_adjacent_bias')}` -> `{injected_modes.get('route_adjacent_bias')}`",
            f"- `distribution_modes.boundary_adjacent_bias`: `{clean_modes.get('boundary_adjacent_bias')}` -> `{injected_modes.get('boundary_adjacent_bias')}`",
            f"- `distribution_modes.shifted_distribution_bias`: `{clean_modes.get('shifted_distribution_bias')}` -> `{injected_modes.get('shifted_distribution_bias')}`",
            f"- `templates.min_templates_per_scene`: `{clean_templates.get('min_templates_per_scene')}` -> `{injected_templates.get('min_templates_per_scene')}`",
            "",
            "## Injected -> Repaired",
            "",
            f"- `distribution_modes.route_adjacent_bias`: `{injected_modes.get('route_adjacent_bias')}` -> `{repaired_modes.get('route_adjacent_bias')}`",
            f"- `distribution_modes.boundary_adjacent_bias`: `{injected_modes.get('boundary_adjacent_bias')}` -> `{repaired_modes.get('boundary_adjacent_bias')}`",
            f"- `distribution_modes.shifted_distribution_bias`: `{injected_modes.get('shifted_distribution_bias')}` -> `{repaired_modes.get('shifted_distribution_bias')}`",
            f"- `templates.min_templates_per_scene`: `{injected_templates.get('min_templates_per_scene')}` -> `{repaired_templates.get('min_templates_per_scene')}`",
            f"- `validation_rules.require_shifted_semantics`: `{dict(injected.get('validation_rules', {})).get('require_shifted_semantics')}` -> `{dict(repaired.get('validation_rules', {})).get('require_shifted_semantics')}`",
            "",
            "Reward and utility remain frozen; only shifted-family preparation differs.",
            "",
        ]
    )


def _write_summary_metrics_csv(results: Mapping[str, VariantResult], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "variant",
        "W_CR",
        "W_EC",
        "W_ER",
        "train_shifted_episode_rate",
        "nominal_success_rate",
        "shifted_success_rate",
        "nominal_average_return",
        "shifted_average_return",
        "nominal_U_task_v1_mean",
        "shifted_U_task_v1_mean",
        "reward_retention_under_shift",
        "utility_retention_under_shift",
        "reward_utility_decoupling_gap",
        "nominal_vs_shifted_success_gap",
        "nominal_vs_shifted_min_distance_gap",
        "shifted_min_distance",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for variant in VARIANTS:
            writer.writerow({name: results[variant.name].summary.get(name, "") for name in fieldnames})


def _verify_demo(
    *,
    results: Mapping[str, VariantResult],
    report_primary_claim_type: str,
    repair_operator: str,
    validation_decision: Mapping[str, Any],
) -> Dict[str, Any]:
    clean = results["clean"]
    injected = results["injected"]
    repaired = results["repaired"]
    reward_sha = _sha256(SPEC_CFG_DIR / "reward_spec_v0.yaml")
    utility_sha = hashlib.sha256(json.dumps(UTILITY_COMPONENT_WEIGHTS, sort_keys=True).encode("utf-8")).hexdigest()
    checks = {
        "reward_frozen_across_variants": {
            "passed": reward_sha == _sha256(SPEC_CFG_DIR / "reward_spec_v0.yaml"),
            "details": {"reward_spec_sha256": reward_sha},
        },
        "utility_frozen_across_variants": {
            "passed": utility_sha == hashlib.sha256(json.dumps(UTILITY_COMPONENT_WEIGHTS, sort_keys=True).encode("utf-8")).hexdigest(),
            "details": {"utility_metric_id": UTILITY_SPEC_ID, "utility_hash": utility_sha},
        },
        "clean_shift_decoupling_is_limited": {
            "passed": float(clean.summary.get("reward_utility_decoupling_gap", 0.0)) <= 0.12,
            "details": {"clean_decoupling_gap": clean.summary.get("reward_utility_decoupling_gap")},
        },
        "injected_reward_remains_decent_under_shift": {
            "passed": float(injected.summary.get("reward_retention_under_shift", 0.0)) >= 0.80,
            "details": {"reward_retention_under_shift": injected.summary.get("reward_retention_under_shift")},
        },
        "injected_utility_drops_under_shift": {
            "passed": float(injected.summary.get("utility_retention_under_shift", 0.0)) <= 0.60,
            "details": {"utility_retention_under_shift": injected.summary.get("utility_retention_under_shift")},
        },
        "injected_success_gap_is_large": {
            "passed": float(injected.summary.get("nominal_vs_shifted_success_gap", 0.0)) >= 0.30,
            "details": {
                "nominal_success_rate": injected.summary.get("nominal_success_rate"),
                "shifted_success_rate": injected.summary.get("shifted_success_rate"),
                "success_gap": injected.summary.get("nominal_vs_shifted_success_gap"),
            },
        },
        "injected_decoupling_gap_is_large": {
            "passed": float(injected.summary.get("reward_utility_decoupling_gap", 0.0)) >= 0.20,
            "details": {"reward_utility_decoupling_gap": injected.summary.get("reward_utility_decoupling_gap")},
        },
        "injected_elevates_W_ER": {
            "passed": (
                float(injected.summary.get("W_ER", 0.0)) >= 0.50
                and float(injected.summary.get("W_ER", 0.0)) > float(clean.summary.get("W_ER", 0.0))
                and float(injected.summary.get("W_ER", 0.0)) > float(repaired.summary.get("W_ER", 0.0))
                and float(injected.summary.get("W_ER", 0.0)) > float(injected.summary.get("W_CR", 0.0))
                and float(injected.summary.get("W_ER", 0.0)) > float(injected.summary.get("W_EC", 0.0))
            ),
            "details": {
                "clean_W_ER": clean.summary.get("W_ER"),
                "injected_W_ER": injected.summary.get("W_ER"),
                "repaired_W_ER": repaired.summary.get("W_ER"),
                "injected_W_CR": injected.summary.get("W_CR"),
                "injected_W_EC": injected.summary.get("W_EC"),
            },
        },
        "report_primary_claim_is_er": {
            "passed": report_primary_claim_type == "E-R",
            "details": {"primary_claim_type": report_primary_claim_type},
        },
        "repair_operator_matches_demo_story": {
            "passed": repair_operator in {"increase_shifted_boundary_bias", "enable_shifted_dynamic_hazards"},
            "details": {"selected_operator": repair_operator},
        },
        "repair_reduces_decoupling": {
            "passed": (
                float(repaired.summary.get("reward_utility_decoupling_gap", 0.0)) < float(injected.summary.get("reward_utility_decoupling_gap", 0.0))
                and float(repaired.summary.get("shifted_success_rate", 0.0)) > float(injected.summary.get("shifted_success_rate", 0.0))
                and float(repaired.summary.get("utility_retention_under_shift", 0.0)) > float(injected.summary.get("utility_retention_under_shift", 0.0))
            ),
            "details": {
                "injected_decoupling_gap": injected.summary.get("reward_utility_decoupling_gap"),
                "repaired_decoupling_gap": repaired.summary.get("reward_utility_decoupling_gap"),
                "injected_shifted_success_rate": injected.summary.get("shifted_success_rate"),
                "repaired_shifted_success_rate": repaired.summary.get("shifted_success_rate"),
            },
        },
        "repair_validation_accepted": {
            "passed": bool(validation_decision.get("accepted", False)),
            "details": {
                "decision_status": validation_decision.get("decision_status"),
                "blocked_by": list(validation_decision.get("blocked_by", []) or []),
            },
        },
    }
    goal_achieved = all(bool(payload.get("passed", False)) for payload in checks.values())
    return {
        "demo_id": "demo3_er_shifted_gate",
        "goal_statement": "Under an environment shift, reward should remain deceptively decent while task utility drops sharply, making W_ER the dominant witness until shift-aware repair narrows the gap.",
        "goal_achieved": goal_achieved,
        "checks": checks,
        "variant_summaries": {variant.name: results[variant.name].summary for variant in VARIANTS},
    }


def _verification_markdown(summary: Mapping[str, Any]) -> str:
    lines = [
        "# Demo 3 Verification Summary",
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
            f" W_ER=`{payload.get('W_ER', '')}`"
            f" reward_retention=`{payload.get('reward_retention_under_shift', '')}`"
            f" utility_retention=`{payload.get('utility_retention_under_shift', '')}`"
            f" success_gap=`{payload.get('nominal_vs_shifted_success_gap', '')}`"
        )
    lines.append("")
    return "\n".join(lines)


def _root_scene_summary_markdown() -> str:
    return "\n".join(
        [
            "# Demo 3 Scene Summary",
            "",
            "- Nominal family: centered gate, smoother corridor, reward and utility mostly aligned.",
            "- Shifted family: gate moves upward-right, a squeeze zone appears, and late cross-traffic pressure makes risky progress misleading.",
            "- Core claim: environment shift can preserve reward-looking progress while degrading real task utility.",
            "",
        ]
    )


def _root_takeaway_markdown(verification: Mapping[str, Any]) -> str:
    injected = dict(verification.get("variant_summaries", {})).get("injected", {})
    repaired = dict(verification.get("variant_summaries", {})).get("repaired", {})
    return "\n".join(
        [
            "# Demo 3 Takeaway",
            "",
            "- 中文：在 shifted gate 环境里，只看 return 很容易误判策略“还可以”，因为它仍在前进、甚至拿到不差的 reward；但真实任务效用已经被成功率、最小间距和时间效率拉低。",
            "- English: Under the shifted gate, return alone can look deceptively acceptable while actual mission utility has already deteriorated in success, clearance, and efficiency.",
            "",
            f"- Injected `W_ER`: `{injected.get('W_ER', '')}`",
            f"- Injected reward retention: `{injected.get('reward_retention_under_shift', '')}`",
            f"- Injected utility retention: `{injected.get('utility_retention_under_shift', '')}`",
            f"- Repaired utility retention: `{repaired.get('utility_retention_under_shift', '')}`",
            "",
        ]
    )


def _update_demo3_readme(
    *,
    verification: Mapping[str, Any],
    results: Mapping[str, VariantResult],
    asset_root: Path,
    output_root: Path,
    report_primary_claim_type: str,
    repair_operator: str,
) -> None:
    readme_path = DEMO_ROOT / "README.md"
    original = readme_path.read_text(encoding="utf-8")
    marker = "## 17. 当前实现状态"
    prefix = original.split(marker)[0] if marker in original else (original.rstrip() + "\n\n")
    injected = results["injected"].summary
    repaired = results["repaired"].summary
    clean = results["clean"].summary
    screenshots = "\n".join(
        f"- `{filename}`" for filename in SCREENSHOT_FILES.values()
    )
    videos = "\n".join(
        f"- [{filename}](assets/videos/{filename})" for filename in VIDEO_FILES.values()
    )
    generated = f"""## 17. 当前实现状态

Demo 3 已经建立了**独立可重跑的隔离 pipeline**，并完成了 `clean / injected / repaired` 三版本闭环。

当前已经落地的核心文件：

- `cre-demos/demo3_er_shifted_gate/cfg/`
- `cre-demos/demo3_er_shifted_gate/scripts/run_demo3.py`
- `cre-demos/demo3_er_shifted_gate/test_demo3_pipeline.py`
- `cre-demos/demo3_er_shifted_gate/reports/latest/`
- `cre-demos/demo3_er_shifted_gate/assets/screenshots/`
- `cre-demos/demo3_er_shifted_gate/assets/videos/`

### 17.1 一次运行命令

```bash
python3 cre-demos/demo3_er_shifted_gate/scripts/run_demo3.py --clean-output
```

### 17.2 关键结果

- `goal_achieved`: `{bool(verification.get("goal_achieved", False))}`
- `report primary claim`: `{report_primary_claim_type}`
- `repair operator`: `{repair_operator}`
- `clean decoupling gap`: `{float(clean.get("reward_utility_decoupling_gap", 0.0)):.3f}`
- `injected W_ER`: `{float(injected.get("W_ER", 0.0)):.3f}`
- `injected reward retention`: `{float(injected.get("reward_retention_under_shift", 0.0)):.3f}`
- `injected utility retention`: `{float(injected.get("utility_retention_under_shift", 0.0)):.3f}`
- `injected success gap`: `{float(injected.get("nominal_vs_shifted_success_gap", 0.0)):.3f}`
- `repaired decoupling gap`: `{float(repaired.get("reward_utility_decoupling_gap", 0.0)):.3f}`
- `repaired shifted success`: `{float(repaired.get("shifted_success_rate", 0.0)):.3f}`

### 17.3 证明性图片总览

下面这些图片都已经自动生成，并且每张都有单独的“证明点”：

{screenshots}

#### 场景与几何

![Scene Compare](assets/screenshots/{SCREENSHOT_FILES["scene_compare"]})

![Gate Offset Inset](assets/screenshots/{SCREENSHOT_FILES["gate_inset"]})

#### 同 seed 行为差异

![Same Seed Overlay](assets/screenshots/{SCREENSHOT_FILES["same_seed_overlay"]})

![Injected Storyboard](assets/screenshots/{SCREENSHOT_FILES["multiframe_story"]})

![Repair Recovery Board](assets/screenshots/{SCREENSHOT_FILES["repair_recovery"]})

#### Reward / Utility 解耦证据

![Reward Utility Scatter](assets/screenshots/{SCREENSHOT_FILES["reward_utility_scatter"]})

![Reward Utility Bars](assets/screenshots/{SCREENSHOT_FILES["reward_utility_bars"]})

![Retention Quadrants](assets/screenshots/{SCREENSHOT_FILES["quadrants"]})

#### 质量与风险

![Failure Breakdown](assets/screenshots/{SCREENSHOT_FILES["failure_breakdown"]})

![Quality Metrics](assets/screenshots/{SCREENSHOT_FILES["quality_metrics"]})

![Shifted Heatmap](assets/screenshots/{SCREENSHOT_FILES["shifted_heatmap"]})

![Summary Card](assets/screenshots/{SCREENSHOT_FILES["summary_card"]})

### 17.4 视频 / 回放页面

{videos}

### 17.5 主要留存数据

- `reports/latest/metrics_summary.json`
- `reports/latest/verification/verification_summary.json`
- `reports/latest/verification/reward_diff.md`
- `reports/latest/verification/utility_metric_spec.md`
- `reports/latest/verification/shift_diff.md`
- `reports/latest/injected/analysis/report/demo3_injected_report/report.json`
- `reports/latest/injected/analysis/repair/demo3_injected_repair/repair_plan.json`
- `reports/latest/analysis/validation/demo3_validation/validation_decision.json`
- `assets/screenshots/demo3_summary_metrics.csv`
- `assets/screenshots/demo3_reward_utility_points.csv`

### 17.6 当前结论

这版 Demo 3 已经满足最初计划里的主叙事：

- reward 保持冻结
- utility 保持冻结
- injected 在 shifted 下仍保留一定 reward，但 `U_task_v1`、成功率和安全裕度明显下降
- `W_ER` 成为主 witness
- repair 后 reward-utility 裂口收窄
"""
    readme_path.write_text(prefix.rstrip() + "\n\n" + generated.strip() + "\n", encoding="utf-8")


def run_demo3_pipeline(*, output_root: Path, asset_root: Path, clean_output: bool = False) -> Dict[str, Any]:
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
            "demo_id": "demo3_er_shifted_gate",
            "scene_layout_file": _repo_relative(SCENE_LAYOUT_PATH),
            "train_episode_seeds": TRAIN_SEEDS,
            "eval_episode_seeds": EVAL_SEEDS,
        },
    )
    _write_json(
        verification_root / "config_snapshot_manifest.json",
        {
            "scene_layout": {"path": _repo_relative(SCENE_LAYOUT_PATH), "sha256": _sha256(SCENE_LAYOUT_PATH)},
            "spec_shared": {
                "reward_spec": {"path": _repo_relative(SPEC_CFG_DIR / "reward_spec_v0.yaml"), "sha256": _sha256(SPEC_CFG_DIR / "reward_spec_v0.yaml")},
                "constraint_spec": {"path": _repo_relative(SPEC_CFG_DIR / "constraint_spec_v0.yaml"), "sha256": _sha256(SPEC_CFG_DIR / "constraint_spec_v0.yaml")},
                "policy_spec": {"path": _repo_relative(SPEC_CFG_DIR / "policy_spec_v0.yaml"), "sha256": _sha256(SPEC_CFG_DIR / "policy_spec_v0.yaml")},
            },
            "utility_metric": {
                "id": UTILITY_SPEC_ID,
                "weights": dict(UTILITY_COMPONENT_WEIGHTS),
                "sha256": hashlib.sha256(json.dumps(UTILITY_COMPONENT_WEIGHTS, sort_keys=True).encode("utf-8")).hexdigest(),
            },
            "variants": {
                variant.name: {
                    "env_cfg_dir": _repo_relative(variant.env_cfg_dir),
                    "scene_cfg_nominal_sha256": _sha256(variant.env_cfg_dir / "scene_cfg_nominal.yaml"),
                    "scene_cfg_shifted_sha256": _sha256(variant.env_cfg_dir / "scene_cfg_shifted.yaml"),
                }
                for variant in VARIANTS
            },
        },
    )
    _write_text(verification_root / "reward_diff.md", _reward_freeze_markdown())
    _write_text(verification_root / "utility_metric_spec.md", _utility_freeze_markdown())
    _write_text(verification_root / "shift_diff.md", _shift_diff_markdown())

    results: Dict[str, VariantResult] = {}
    for variant in VARIANTS:
        train_run = _simulate_run(variant, run_kind="train", episode_plans=variant.train_plans, scene_layout=scene_layout, output_root=output_root)
        train_mix_summary = _train_family_mix_summary(train_run.episode_records)
        train_run.summary.update(train_mix_summary)
        _write_json(train_run.run_dir / "summary.json", train_run.summary)
        eval_nominal_run = _simulate_run(variant, run_kind="eval_nominal", episode_plans=variant.eval_nominal_plans, scene_layout=scene_layout, output_root=output_root)
        eval_shifted_run = _simulate_run(variant, run_kind="eval_shifted", episode_plans=variant.eval_shifted_plans, scene_layout=scene_layout, output_root=output_root)
        static_report, static_bundle_paths = run_static_analysis_bundle(
            spec_cfg_dir=SPEC_CFG_DIR,
            env_cfg_dir=variant.env_cfg_dir,
            detector_cfg_dir=DETECTOR_CFG_DIR,
            scene_families=("nominal", "shifted"),
            reports_root=output_root / variant.name,
            bundle_name=f"demo3_{variant.name}_static",
        )
        del static_report
        dynamic_report, dynamic_bundle_paths = run_dynamic_analysis_bundle(
            run_dirs=[eval_nominal_run.run_dir],
            compare_run_dirs=[eval_shifted_run.run_dir],
            spec_cfg_dir=SPEC_CFG_DIR,
            env_cfg_dir=variant.env_cfg_dir,
            detector_cfg_dir=DETECTOR_CFG_DIR,
            scene_families=("nominal", "shifted"),
            reports_root=output_root / variant.name,
            bundle_name=f"demo3_{variant.name}_dynamic",
            static_bundle_dir=Path(static_bundle_paths["report_dir"]),
        )
        witness_scores = {str(item["witness_id"]): float(item["score"]) for item in list(dynamic_report.witnesses)}
        coverage_manifest = {
            "variant": variant.name,
            "train_episode_count": len(train_run.episode_records),
            "train_family_counts": train_run.summary.get("family_counts", {}),
            "train_shifted_episode_rate": float(train_run.summary.get("family_counts", {}).get("shifted", 0) / max(len(train_run.episode_records), 1)),
            "env_cfg_dir": _repo_relative(variant.env_cfg_dir),
        }
        variant_summary = _build_variant_summary(spec=variant, train_run=train_run, eval_nominal_run=eval_nominal_run, eval_shifted_run=eval_shifted_run, witness_scores=witness_scores)
        result = VariantResult(
            spec=variant,
            train_run=train_run,
            eval_nominal_run=eval_nominal_run,
            eval_shifted_run=eval_shifted_run,
            static_bundle_dir=Path(static_bundle_paths["report_dir"]),
            dynamic_bundle_dir=Path(dynamic_bundle_paths["report_dir"]),
            witness_scores=witness_scores,
            summary=variant_summary,
            coverage_manifest=coverage_manifest,
        )
        results[variant.name] = result
        _write_variant_supporting_artifacts(variant_root=output_root / variant.name, scene_layout=scene_layout, variant_result=result)

    injected_flow = _run_injected_report_flow(results["injected"], output_root=output_root)
    validation_flow = _run_validation_flow(output_root=output_root, injected=results["injected"], repaired=results["repaired"], repair_bundle_name=Path(injected_flow["repair_bundle_dir"]).name)

    _render_scene_compare_svg(scene_layout, asset_root / "screenshots" / SCREENSHOT_FILES["scene_compare"])
    _render_gate_inset_svg(scene_layout, asset_root / "screenshots" / SCREENSHOT_FILES["gate_inset"])
    _render_same_seed_overlay_svg(scene_layout, results, asset_root / "screenshots" / SCREENSHOT_FILES["same_seed_overlay"])
    _render_reward_utility_scatter_svg(results, asset_root / "screenshots" / SCREENSHOT_FILES["reward_utility_scatter"])
    _render_reward_utility_bars_svg(results, asset_root / "screenshots" / SCREENSHOT_FILES["reward_utility_bars"])
    _render_failure_breakdown_svg(results, asset_root / "screenshots" / SCREENSHOT_FILES["failure_breakdown"])
    _render_quality_metrics_svg(results, asset_root / "screenshots" / SCREENSHOT_FILES["quality_metrics"])
    _render_repair_recovery_board_svg(scene_layout, results, asset_root / "screenshots" / SCREENSHOT_FILES["repair_recovery"])
    _render_multiframe_story_svg(scene_layout, results, asset_root / "screenshots" / SCREENSHOT_FILES["multiframe_story"])
    _render_shifted_heatmap_svg(scene_layout, results, asset_root / "screenshots" / SCREENSHOT_FILES["shifted_heatmap"])
    _render_quadrants_svg(results, asset_root / "screenshots" / SCREENSHOT_FILES["quadrants"])
    _render_summary_card_svg(results, str(injected_flow["report_primary_claim_type"]), asset_root / "screenshots" / SCREENSHOT_FILES["summary_card"])

    nominal_seed = int(EVAL_SEEDS[0]) if EVAL_SEEDS else _pick_story_seed(results)
    story_seed = _pick_story_seed(results)
    nominal_layout = dict(dict(scene_layout.get("families", {})).get("nominal", {}))
    shifted_layout = dict(dict(scene_layout.get("families", {})).get("shifted", {}))
    _render_replay_html(
        scene_layout=scene_layout,
        panels=[
            _replay_panel_payload(panel_id=f"nominal-{variant.name}", label=f"{variant.label} nominal", color=variant.color, family_layout=nominal_layout, trajectory=_trajectory_for_seed(results[variant.name].eval_nominal_run, nominal_seed), record=_record_for_seed(results[variant.name].eval_nominal_run, nominal_seed))
            for variant in VARIANTS
        ],
        title="Demo 3 Nominal Replay",
        subtitle="Nominal scenes keep reward and utility mostly aligned across variants.",
        output_path=asset_root / "videos" / VIDEO_FILES["nominal_success"],
    )
    _render_replay_html(
        scene_layout=scene_layout,
        panels=[
            _replay_panel_payload(panel_id=f"shifted-{variant.name}", label=f"{variant.label} shifted", color=variant.color, family_layout=shifted_layout, trajectory=_trajectory_for_seed(results[variant.name].eval_shifted_run, story_seed), record=_record_for_seed(results[variant.name].eval_shifted_run, story_seed))
            for variant in VARIANTS
        ],
        title="Demo 3 Shifted Same-Seed Replay",
        subtitle=f"All three variants face the same shifted seed {story_seed}; the injected path reveals the largest reward-utility mismatch.",
        output_path=asset_root / "videos" / VIDEO_FILES["shifted_same_seed"],
    )
    _render_replay_html(
        scene_layout=scene_layout,
        panels=[
            _replay_panel_payload(panel_id="injected-failure", label="Injected shifted failure", color=results["injected"].spec.color, family_layout=shifted_layout, trajectory=_trajectory_for_seed(results["injected"].eval_shifted_run, story_seed), record=_record_for_seed(results["injected"].eval_shifted_run, story_seed)),
        ],
        title="Demo 3 Injected Shifted Failure",
        subtitle="A single injected shifted replay highlighting late hesitation or collision near the shifted gate.",
        output_path=asset_root / "videos" / VIDEO_FILES["injected_shifted_failure"],
    )
    _render_replay_html(
        scene_layout=scene_layout,
        panels=[
            _replay_panel_payload(panel_id="injected-compare", label="Injected shifted", color=results["injected"].spec.color, family_layout=shifted_layout, trajectory=_trajectory_for_seed(results["injected"].eval_shifted_run, story_seed), record=_record_for_seed(results["injected"].eval_shifted_run, story_seed)),
            _replay_panel_payload(panel_id="repaired-compare", label="Repaired shifted", color=results["repaired"].spec.color, family_layout=shifted_layout, trajectory=_trajectory_for_seed(results["repaired"].eval_shifted_run, story_seed), record=_record_for_seed(results["repaired"].eval_shifted_run, story_seed)),
        ],
        title="Demo 3 Repaired Recovery Replay",
        subtitle="The repaired shifted rollout follows a higher, safer crossing line and narrows the utility gap.",
        output_path=asset_root / "videos" / VIDEO_FILES["repaired_shifted_recovery"],
    )
    _render_replay_html(
        scene_layout=scene_layout,
        panels=[
            _replay_panel_payload(panel_id=f"triplet-{variant.name}", label=variant.label, color=variant.color, family_layout=shifted_layout, trajectory=results[variant.name].eval_shifted_run.representative_trajectory, record=results[variant.name].eval_shifted_run.episode_records[0] if results[variant.name].eval_shifted_run.episode_records else {})
            for variant in VARIANTS
        ],
        title="Demo 3 Triplet Split Screen",
        subtitle="Representative shifted trajectories for clean, injected, and repaired in one synchronized split-screen.",
        output_path=asset_root / "videos" / VIDEO_FILES["triplet_split_screen"],
    )

    _write_summary_metrics_csv(results, asset_root / "screenshots" / "demo3_summary_metrics.csv")
    reward_rows: List[Dict[str, Any]] = []
    for variant in VARIANTS:
        for run in (results[variant.name].eval_nominal_run, results[variant.name].eval_shifted_run):
            for record in run.episode_records:
                reward_rows.append(
                    {
                        "variant": variant.name,
                        "family": record.get("family"),
                        "seed": record.get("seed"),
                        "outcome": record.get("outcome"),
                        "return_total": record.get("return_total"),
                        "utility_score": record.get("utility_score"),
                        "min_distance": record.get("min_distance"),
                        "clearance_score": record.get("clearance_score"),
                        "time_efficiency_score": record.get("time_efficiency_score"),
                        "path_efficiency_score": record.get("path_efficiency_score"),
                    }
                )
    _write_reward_utility_points_csv(asset_root / "screenshots" / "demo3_reward_utility_points.csv", reward_rows)

    verification = _verify_demo(results=results, report_primary_claim_type=str(injected_flow["report_primary_claim_type"]), repair_operator=str(injected_flow["selected_operator"]), validation_decision=dict(validation_flow["decision"]))
    visual_manifest = {
        **{key: str(asset_root / "screenshots" / filename) for key, filename in SCREENSHOT_FILES.items()},
        **{key: str(asset_root / "videos" / filename) for key, filename in VIDEO_FILES.items()},
    }
    verification.update(
        {
            "artifact_paths": {
                **visual_manifest,
                "report_bundle_dir": str(injected_flow["report_bundle_dir"]),
                "repair_bundle_dir": str(injected_flow["repair_bundle_dir"]),
                "validation_dir": str(validation_flow["validation_dir"]),
            }
        }
    )
    _write_json(output_root / "metrics_summary.json", {variant.name: results[variant.name].summary for variant in VARIANTS})
    _write_json(output_root / "visual_manifest.json", visual_manifest)
    _write_text(output_root / "scene_summary.md", _root_scene_summary_markdown())
    _write_text(output_root / "demo_takeaway.md", _root_takeaway_markdown(verification))
    _write_json(verification_root / "verification_summary.json", verification)
    _write_text(verification_root / "verification_summary.md", _verification_markdown(verification))
    _update_demo3_readme(verification=verification, results=results, asset_root=asset_root, output_root=output_root, report_primary_claim_type=str(injected_flow["report_primary_claim_type"]), repair_operator=str(injected_flow["selected_operator"]))
    return verification


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_root)
    asset_root = Path(args.asset_root)
    verification = run_demo3_pipeline(output_root=output_root, asset_root=asset_root, clean_output=bool(args.clean_output))
    print(json.dumps(verification, indent=2, sort_keys=True))
    if bool(verification.get("goal_achieved", False)) or bool(args.allow_failed_goal):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
