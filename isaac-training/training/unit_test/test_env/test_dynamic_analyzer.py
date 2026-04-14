import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Historical / legacy pipeline imports.
from analyzers.legacy.dynamic_analyzer import DynamicReport, run_dynamic_analysis
from analyzers.legacy.static_analyzer import StaticReport, run_static_analysis


SPEC_DIR = ROOT / "cfg" / "spec_cfg"
REAL_EVAL_LOG_DIR = ROOT / "logs" / "train_eval_rollout_20260411_215734"


def _real_static_report() -> StaticReport:
    return run_static_analysis(
        str(SPEC_DIR / "reward_spec_v1.yaml"),
        str(SPEC_DIR / "constraint_spec_v1.yaml"),
        str(SPEC_DIR / "policy_spec_v1.yaml"),
        str(SPEC_DIR / "env_spec_v1.yaml"),
    )


def _step(
    *,
    step_idx: int,
    reward_total: float = 1.0,
    min_obstacle_distance: float = 1.5,
    collision_flag: bool = False,
    out_of_bounds_flag: bool = False,
    done_type: str = "running",
    velocity=(1.0, 0.0, 0.0),
    yaw_rate: float = 0.0,
    position=(0.0, 0.0, 1.5),
):
    return {
        "episode_index": 0,
        "step_idx": step_idx,
        "sim_time": float(step_idx) * 0.1,
        "scene_id": "scene_000",
        "scenario_type": "nominal",
        "position": list(position),
        "velocity": list(velocity),
        "yaw_rate": yaw_rate,
        "goal_distance": max(0.0, 5.0 - step_idx),
        "reward_total": reward_total,
        "reward_components": {
            "reward_progress": reward_total,
            "reward_safety_static": 0.0,
            "reward_safety_dynamic": 0.0,
            "penalty_smooth": 0.0,
            "penalty_height": 0.0,
            "manual_control": 0.0,
        },
        "collision_flag": collision_flag,
        "min_obstacle_distance": min_obstacle_distance,
        "near_violation_flag": min_obstacle_distance < 0.5,
        "out_of_bounds_flag": out_of_bounds_flag,
        "done_type": done_type,
        "source": "eval",
        "scene_cfg_name": "scene_cfg_nominal.yaml",
        "target_position": [1.0, 1.0, 1.5],
        "scene_tags": {},
    }


def _episode_payload(steps):
    total_reward = sum(float(step.get("reward_total", 0.0) or 0.0) for step in steps)
    min_distance = min(
        float(step["min_obstacle_distance"])
        for step in steps
        if step.get("min_obstacle_distance") is not None
    )
    collision_flag = any(bool(step.get("collision_flag")) for step in steps)
    out_of_bounds_flag = any(bool(step.get("out_of_bounds_flag")) for step in steps)
    done_type = steps[-1].get("done_type", "running")
    return {
        "summary": {
            "episode_index": 0,
            "seed": 0,
            "scene_id": "scene_000",
            "scenario_type": "nominal",
            "num_steps": len(steps),
            "trajectory_length": 0.0,
            "return_total": total_reward,
            "reward_components_total": {
                "reward_progress": total_reward,
                "reward_safety_static": 0.0,
                "reward_safety_dynamic": 0.0,
                "penalty_smooth": 0.0,
                "penalty_height": 0.0,
                "manual_control": 0.0,
            },
            "success_flag": False,
            "collision_flag": collision_flag,
            "out_of_bounds_flag": out_of_bounds_flag,
            "min_obstacle_distance": min_distance,
            "near_violation_steps": sum(int(step.get("near_violation_flag", False)) for step in steps),
            "near_violation_ratio": (
                sum(int(step.get("near_violation_flag", False)) for step in steps) / len(steps)
                if steps else 0.0
            ),
            "final_goal_distance": steps[-1].get("goal_distance"),
            "done_type": done_type,
            "source": "eval",
            "scene_cfg_name": "scene_cfg_nominal.yaml",
            "scene_tags": {},
        },
        "steps": steps,
    }


def _write_episode_json(log_dir: Path, steps, *, episode_index: int = 0) -> None:
    episodes_dir = log_dir / "episodes"
    episodes_dir.mkdir(parents=True, exist_ok=True)
    payload = _episode_payload(steps)
    payload["summary"]["episode_index"] = episode_index
    for step in payload["steps"]:
        step["episode_index"] = episode_index
    episode_path = episodes_dir / f"episode_{episode_index:04d}.json"
    episode_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_empty_log_dir(tmp_path):
    report = run_dynamic_analysis(
        _real_static_report(),
        str(tmp_path),
        str(SPEC_DIR / "reward_spec_v1.yaml"),
        str(SPEC_DIR / "constraint_spec_v1.yaml"),
    )

    assert isinstance(report, DynamicReport)
    assert report.episode_count == 0
    assert report.summary["no_episodes"] is True


def test_d1_collision_violation_fires(tmp_path):
    _write_episode_json(
        tmp_path,
        [
            _step(step_idx=0, min_obstacle_distance=0.7),
            _step(step_idx=1, min_obstacle_distance=0.4, collision_flag=True, done_type="collision"),
        ],
    )

    report = run_dynamic_analysis(
        _real_static_report(),
        str(tmp_path),
        str(SPEC_DIR / "reward_spec_v1.yaml"),
        str(SPEC_DIR / "constraint_spec_v1.yaml"),
    )

    assert any(
        issue.rule_id == "hard_constraint_violation_rate" and issue.issue_type == "C-R"
        for issue in report.issues
    )


def test_d2_soft_exceedance_fires(tmp_path):
    _write_episode_json(
        tmp_path,
        [
            _step(step_idx=0, min_obstacle_distance=0.45),
            _step(step_idx=1, min_obstacle_distance=0.40),
        ],
    )

    report = run_dynamic_analysis(
        _real_static_report(),
        str(tmp_path),
        str(SPEC_DIR / "reward_spec_v1.yaml"),
        str(SPEC_DIR / "constraint_spec_v1.yaml"),
    )

    assert any(
        issue.rule_id == "soft_constraint_exceedance_rate" and issue.issue_type == "C-R"
        for issue in report.issues
    )


def test_d3_low_coverage_fires(tmp_path):
    _write_episode_json(
        tmp_path,
        [
            _step(step_idx=0, min_obstacle_distance=2.5),
            _step(step_idx=1, min_obstacle_distance=2.2),
            _step(step_idx=2, min_obstacle_distance=2.1),
        ],
    )

    report = run_dynamic_analysis(
        _real_static_report(),
        str(tmp_path),
        str(SPEC_DIR / "reward_spec_v1.yaml"),
        str(SPEC_DIR / "constraint_spec_v1.yaml"),
    )

    assert any(
        issue.rule_id == "critical_region_proximity" and issue.issue_type == "E-C"
        for issue in report.issues
    )


def test_d5_missing_field_reported(tmp_path):
    _write_episode_json(
        tmp_path,
        [
            _step(step_idx=0, min_obstacle_distance=1.0),
            _step(step_idx=1, min_obstacle_distance=0.8),
        ],
    )

    report = run_dynamic_analysis(
        _real_static_report(),
        str(tmp_path),
        str(SPEC_DIR / "reward_spec_v1.yaml"),
        str(SPEC_DIR / "constraint_spec_v1.yaml"),
    )

    assert any(
        issue.rule_id == "missing_field_coverage" and issue.severity == "info"
        for issue in report.issues
    )


def test_real_log_smoke():
    report = run_dynamic_analysis(
        _real_static_report(),
        str(REAL_EVAL_LOG_DIR),
        str(SPEC_DIR / "reward_spec_v1.yaml"),
        str(SPEC_DIR / "constraint_spec_v1.yaml"),
    )

    assert isinstance(report, DynamicReport)
    assert report.episode_count > 0
    assert isinstance(report.issues, list)
