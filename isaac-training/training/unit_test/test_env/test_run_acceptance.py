import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENVS_PATH = ROOT / "envs"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ENVS_PATH) not in sys.path:
    sys.path.insert(0, str(ENVS_PATH))

from cre_logging import FlightEpisodeLogger
from runtime_logging.acceptance import run_acceptance_check


def _build_valid_run_dir(tmp_path: Path) -> Path:
    logger = FlightEpisodeLogger(
        run_name="acceptance_run",
        base_dir=tmp_path,
        near_violation_distance=0.5,
        use_timestamp=False,
        source="test_flight",
    )
    logger.reset(
        episode_index=0,
        seed=11,
        scene_id="scene_nominal_000",
        scenario_type="nominal",
        scene_cfg_name="scene_cfg_nominal.yaml",
        scene_tags={
            "scene_id": "scene_nominal_000",
            "family": "nominal",
            "scene_cfg_name": "scene_cfg_nominal.yaml",
        },
    )
    logger.log_step(
        step_idx=0,
        sim_time=0.0,
        scene_id="scene_nominal_000",
        scenario_type="nominal",
        position=(0.0, 0.0, 1.0),
        velocity=(0.1, 0.0, 0.0),
        yaw_rate=0.0,
        goal_distance=1.0,
        reward_total=0.5,
        reward_components={"manual_control": 0.0},
        collision_flag=False,
        min_obstacle_distance=0.8,
        near_violation_flag=False,
        out_of_bounds_flag=False,
        done_type="running",
        scene_cfg_name="scene_cfg_nominal.yaml",
    )
    logger.log_step(
        step_idx=1,
        sim_time=0.1,
        scene_id="scene_nominal_000",
        scenario_type="nominal",
        position=(0.1, 0.0, 1.0),
        velocity=(0.1, 0.0, 0.0),
        yaw_rate=0.0,
        goal_distance=0.2,
        reward_total=1.0,
        reward_components={"manual_control": 0.0},
        collision_flag=False,
        min_obstacle_distance=0.7,
        near_violation_flag=False,
        out_of_bounds_flag=False,
        done_type="success",
        scene_cfg_name="scene_cfg_nominal.yaml",
    )
    logger.finalize_episode(done_type="success")
    return tmp_path / "acceptance_run"


def _rewrite_jsonl_record(path: Path, index: int, mutator):
    records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    records[index] = mutator(records[index])
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )


def test_valid_run_directory_passes_acceptance_and_writes_report(tmp_path):
    run_dir = _build_valid_run_dir(tmp_path)

    result = run_acceptance_check(run_dir, write_report=True)

    assert result["passed"] is True
    assert (run_dir / "acceptance.json").exists()
    report = json.loads((run_dir / "acceptance.json").read_text(encoding="utf-8"))
    assert report["passed"] is True
    assert report["metrics"]["success_rate"] == 1.0


def test_missing_manifest_fails_acceptance(tmp_path):
    run_dir = _build_valid_run_dir(tmp_path)
    (run_dir / "manifest.json").unlink()

    result = run_acceptance_check(run_dir, write_report=False)

    assert result["passed"] is False
    assert any("missing artifact: manifest.json" in error for error in result["errors"])


def test_missing_required_step_field_fails_acceptance(tmp_path):
    run_dir = _build_valid_run_dir(tmp_path)

    def mutate(step):
        step.pop("yaw_rate", None)
        return step

    _rewrite_jsonl_record(run_dir / "steps.jsonl", 0, mutate)

    result = run_acceptance_check(run_dir, write_report=False)

    assert result["passed"] is False
    assert any("missing step fields: yaw_rate" in error for error in result["errors"])


def test_inconsistent_summary_fails_acceptance(tmp_path):
    run_dir = _build_valid_run_dir(tmp_path)
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    summary["average_return"] = 999.0
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    result = run_acceptance_check(run_dir, write_report=False)

    assert result["passed"] is False
    assert any("summary.json mismatch for average_return" in error for error in result["errors"])


def test_missing_standard_reward_component_keys_fail_acceptance(tmp_path):
    run_dir = _build_valid_run_dir(tmp_path)

    def mutate(step):
        step["reward_components"].pop("reward_progress", None)
        return step

    _rewrite_jsonl_record(run_dir / "steps.jsonl", 0, mutate)

    result = run_acceptance_check(run_dir, write_report=False)

    assert result["passed"] is False
    assert any("step reward_components missing standard keys" in error for error in result["errors"])


def test_invalid_done_type_fails_acceptance(tmp_path):
    run_dir = _build_valid_run_dir(tmp_path)

    def mutate(step):
        step["done_type"] = "teleport"
        return step

    _rewrite_jsonl_record(run_dir / "steps.jsonl", 0, mutate)

    result = run_acceptance_check(run_dir, write_report=False)

    assert result["passed"] is False
    assert any("invalid step done_type: teleport" in error for error in result["errors"])
