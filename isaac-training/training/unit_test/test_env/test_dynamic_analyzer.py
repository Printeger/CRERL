import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analyzers.detector_runner import run_static_analysis_bundle
from analyzers.dynamic_analyzer import load_static_bundle_context, run_dynamic_analysis
from runtime_logging.episode_writer import (
    discover_accepted_run_directories,
    load_accepted_run_directory,
)
from runtime_logging.logger import create_run_logger, run_acceptance_check


def _reward_components(progress=0.0, manual=0.0):
    return {
        "reward_progress": float(progress),
        "reward_safety_static": 0.0,
        "reward_safety_dynamic": 0.0,
        "penalty_smooth": 0.0,
        "penalty_height": 0.0,
        "manual_control": float(manual),
    }


def _write_episode(
    logger,
    *,
    episode_index: int,
    scene_id: str,
    scenario_type: str,
    scene_cfg_name: str,
    distances,
    rewards,
    done_type: str,
    collision: bool = False,
    out_of_bounds: bool = False,
    dynamic_tags=None,
):
    logger.reset(
        episode_index=episode_index,
        seed=episode_index,
        scene_id=scene_id,
        scenario_type=scenario_type,
        scene_cfg_name=scene_cfg_name,
        scene_tags=dict(dynamic_tags or {}),
    )
    position_x = 0.0
    for step_idx, (distance, reward_total) in enumerate(zip(distances, rewards)):
        position_x += 0.1
        logger.log_step(
            step_idx=step_idx,
            sim_time=0.1 * step_idx,
            position=(position_x, 0.0, 1.5),
            velocity=(1.0, 0.0, 0.0),
            yaw_rate=0.0,
            goal_distance=max(0.0, 5.0 - position_x),
            reward_total=reward_total,
            reward_components=_reward_components(progress=reward_total),
            collision_flag=collision and step_idx == len(distances) - 1,
            min_obstacle_distance=distance,
            near_violation_flag=distance < 0.6,
            out_of_bounds_flag=out_of_bounds and step_idx == len(distances) - 1,
            done_type="running" if step_idx < len(distances) - 1 else done_type,
            scene_id=scene_id,
            scenario_type=scenario_type,
            scene_cfg_name=scene_cfg_name,
            scene_tags=dict(dynamic_tags or {}),
        )
    logger.finalize_episode(done_type=done_type)


def _create_run(
    tmp_path: Path,
    *,
    run_name: str,
    source: str,
    episodes,
) -> Path:
    logger = create_run_logger(
        source=source,
        run_name=run_name,
        base_dir=tmp_path,
        use_timestamp=False,
        near_violation_distance=0.6,
    )
    for episode_index, episode in enumerate(episodes):
        _write_episode(logger, episode_index=episode_index, **episode)

    # The first pass writes acceptance.json; the second pass verifies the full artifact set.
    first = run_acceptance_check(logger.run_dir, write_report=True)
    second = run_acceptance_check(logger.run_dir, write_report=True)
    assert first["passed"] is False
    assert second["passed"] is True
    return Path(logger.run_dir)


def _witness_by_id(report, witness_id: str):
    for witness in report.witnesses:
        if witness["witness_id"] == witness_id:
            return witness
    raise AssertionError(f"Missing witness {witness_id}")


def test_dynamic_analysis_detects_reward_violation_coupling(tmp_path):
    run_dir = _create_run(
        tmp_path,
        run_name="reward_violation_run",
        source="baseline_greedy",
        episodes=[
            {
                "scene_id": "scene_reward_violation",
                "scenario_type": "nominal",
                "scene_cfg_name": "scene_cfg_nominal.yaml",
                "distances": [0.35, 0.32, 0.28, 0.30, 0.40, 0.45, 0.55, 0.58],
                "rewards": [1.2, 1.1, 1.1, 1.0, 0.9, 0.8, 0.7, 0.6],
                "done_type": "collision",
                "collision": True,
            }
        ],
    )

    report = run_dynamic_analysis(run_dirs=[run_dir])
    witness = _witness_by_id(report, "W_CR")

    assert report.report_type == "dynamic_analyzer_report.v1"
    assert witness["score"] >= 0.5
    assert witness["severity"] in {"medium", "high"}


def test_dynamic_analysis_detects_critical_state_undercoverage(tmp_path):
    run_dir = _create_run(
        tmp_path,
        run_name="undercoverage_run",
        source="baseline_conservative",
        episodes=[
            {
                "scene_id": "scene_undercoverage",
                "scenario_type": "nominal",
                "scene_cfg_name": "scene_cfg_nominal.yaml",
                "distances": [1.8, 1.9, 1.7, 1.6, 1.8, 1.9],
                "rewards": [0.6, 0.6, 0.5, 0.5, 0.4, 0.4],
                "done_type": "success",
            }
        ],
    )

    report = run_dynamic_analysis(run_dirs=[run_dir])
    witness = _witness_by_id(report, "W_EC")

    assert witness["score"] >= 0.5
    assert witness["severity"] in {"medium", "high"}


def test_dynamic_analysis_detects_transfer_fragility(tmp_path):
    nominal_run = _create_run(
        tmp_path,
        run_name="nominal_reference_run",
        source="eval",
        episodes=[
            {
                "scene_id": "scene_nominal_ref",
                "scenario_type": "nominal",
                "scene_cfg_name": "scene_cfg_nominal.yaml",
                "distances": [1.2, 1.1, 1.0, 0.95, 0.92, 0.90],
                "rewards": [0.9, 0.9, 0.8, 0.8, 0.7, 0.7],
                "done_type": "success",
            }
        ],
    )
    shifted_run = _create_run(
        tmp_path,
        run_name="shifted_fragile_run",
        source="eval",
        episodes=[
            {
                "scene_id": "scene_shifted_fragile",
                "scenario_type": "shifted",
                "scene_cfg_name": "scene_cfg_shifted.yaml",
                "distances": [0.7, 0.55, 0.48, 0.42, 0.35, 0.28],
                "rewards": [0.5, 0.4, 0.3, 0.2, 0.2, 0.1],
                "done_type": "collision",
                "collision": True,
                "dynamic_tags": {
                    "dynamic_obstacles_enabled": True,
                    "dynamic_obstacle_count": 2,
                },
            }
        ],
    )

    report = run_dynamic_analysis(
        run_dirs=[nominal_run],
        compare_run_dirs=[shifted_run],
    )
    witness = _witness_by_id(report, "W_ER")

    assert witness["score"] >= 0.4
    assert witness["severity"] in {"warning", "medium", "high"}


def test_discover_accepted_run_directories_filters_by_source_and_scene(tmp_path):
    nominal_run = _create_run(
        tmp_path,
        run_name="discover_nominal_run",
        source="eval",
        episodes=[
            {
                "scene_id": "scene_discover_nominal",
                "scenario_type": "nominal",
                "scene_cfg_name": "scene_cfg_nominal.yaml",
                "distances": [1.0, 0.95, 0.92],
                "rewards": [0.7, 0.7, 0.6],
                "done_type": "success",
            }
        ],
    )
    shifted_run = _create_run(
        tmp_path,
        run_name="discover_shifted_run",
        source="baseline_greedy",
        episodes=[
            {
                "scene_id": "scene_discover_shifted",
                "scenario_type": "shifted",
                "scene_cfg_name": "scene_cfg_shifted.yaml",
                "distances": [0.6, 0.5, 0.4],
                "rewards": [0.4, 0.3, 0.2],
                "done_type": "collision",
                "collision": True,
            }
        ],
    )

    by_source = discover_accepted_run_directories(tmp_path, sources=["baseline_greedy"])
    by_scene = discover_accepted_run_directories(tmp_path, scenario_types=["shifted"])
    by_cfg = discover_accepted_run_directories(tmp_path, scene_cfg_names=["scene_cfg_nominal.yaml"])

    assert by_source == [shifted_run]
    assert by_scene == [shifted_run]
    assert by_cfg == [nominal_run]


def test_dynamic_analysis_loads_static_bundle_context(tmp_path):
    nominal_run = _create_run(
        tmp_path,
        run_name="static_context_nominal_run",
        source="eval",
        episodes=[
            {
                "scene_id": "scene_static_context_nominal",
                "scenario_type": "nominal",
                "scene_cfg_name": "scene_cfg_nominal.yaml",
                "distances": [1.0, 0.95, 0.92],
                "rewards": [0.7, 0.7, 0.6],
                "done_type": "success",
            }
        ],
    )
    reports_root = tmp_path / "reports_root"
    static_report, bundle_paths = run_static_analysis_bundle(
        reports_root=reports_root,
        bundle_name="static_context_bundle",
    )
    assert static_report.passed is True

    report = run_dynamic_analysis(
        run_dirs=[nominal_run],
        reports_root=reports_root,
        static_bundle_name="static_context_bundle",
    )
    static_context = report.metadata["static_context"]

    assert static_context["bundle_name"] == "static_context_bundle"
    assert static_context["spec_version"] == "v0"
    assert static_context["report_path"].endswith("static_report.json")
    assert static_context["namespace_contract"]["contract_type"] == "report_namespace_contract.v1"

    loaded_context = load_static_bundle_context(
        reports_root=reports_root,
        static_bundle_name="static_context_bundle",
    )
    assert loaded_context["bundle_name"] == "static_context_bundle"


def test_dynamic_report_promotes_group_and_failure_summaries(tmp_path):
    nominal_run = _create_run(
        tmp_path,
        run_name="summary_nominal_run",
        source="baseline_greedy",
        episodes=[
            {
                "scene_id": "scene_summary_nominal",
                "scenario_type": "nominal",
                "scene_cfg_name": "scene_cfg_nominal.yaml",
                "distances": [1.1, 0.95, 0.88],
                "rewards": [0.8, 0.7, 0.6],
                "done_type": "success",
            }
        ],
    )
    shifted_run = _create_run(
        tmp_path,
        run_name="summary_shifted_run",
        source="baseline_greedy",
        episodes=[
            {
                "scene_id": "scene_summary_shifted",
                "scenario_type": "shifted",
                "scene_cfg_name": "scene_cfg_shifted.yaml",
                "distances": [0.62, 0.48, 0.35],
                "rewards": [0.5, 0.4, 0.2],
                "done_type": "collision",
                "collision": True,
                "dynamic_tags": {
                    "dynamic_obstacles_enabled": True,
                    "dynamic_obstacle_count": 1,
                },
            }
        ],
    )

    report = run_dynamic_analysis(
        run_dirs=[nominal_run],
        compare_run_dirs=[shifted_run],
    )

    assert "primary" in report.group_summaries
    assert "comparison" in report.group_summaries
    assert "by_source" in report.group_summaries["primary"]
    assert "baseline_greedy" in report.group_summaries["primary"]["by_source"]
    assert "primary" in report.failure_summaries
    assert "comparison" in report.failure_summaries
    assert "by_scenario_type" in report.failure_summaries["comparison"]
    assert "shifted" in report.failure_summaries["comparison"]["by_scenario_type"]
    assert (
        report.failure_summaries["comparison"]["by_scenario_type"]["shifted"]["failure_pressure"] > 0.0
    )
    assert report.static_context["bundle_name"] == ""
    assert report.static_context["namespace_contract"] == {}


def test_run_dynamic_audit_cli_writes_machine_readable_bundle(tmp_path):
    nominal_run = _create_run(
        tmp_path,
        run_name="cli_nominal_run",
        source="eval",
        episodes=[
            {
                "scene_id": "scene_cli_nominal",
                "scenario_type": "nominal",
                "scene_cfg_name": "scene_cfg_nominal.yaml",
                "distances": [1.1, 1.0, 0.95, 0.92],
                "rewards": [0.8, 0.8, 0.7, 0.7],
                "done_type": "success",
            }
        ],
    )
    shifted_run = _create_run(
        tmp_path,
        run_name="cli_shifted_run",
        source="eval",
        episodes=[
            {
                "scene_id": "scene_cli_shifted",
                "scenario_type": "shifted",
                "scene_cfg_name": "scene_cfg_shifted.yaml",
                "distances": [0.65, 0.5, 0.4, 0.3],
                "rewards": [0.5, 0.4, 0.2, 0.1],
                "done_type": "collision",
                "collision": True,
                "dynamic_tags": {
                    "dynamic_obstacles_enabled": True,
                    "dynamic_obstacle_count": 1,
                },
            }
        ],
    )

    reports_root = tmp_path / "reports_root"
    report_dir = reports_root / "analysis" / "dynamic" / "cli_dynamic_bundle"
    namespace_manifest_path = reports_root / "analysis" / "dynamic" / "namespace_manifest.json"
    namespace_contract_path = reports_root / "analysis" / "report_namespace_contract.json"
    output_path = tmp_path / "cli_dynamic_report.json"
    static_report, _bundle_paths = run_static_analysis_bundle(
        reports_root=reports_root,
        bundle_name="cli_static_bundle",
    )
    assert static_report.passed is True
    command = [
        sys.executable,
        str(ROOT / "scripts" / "run_dynamic_audit.py"),
        "--logs-root",
        str(tmp_path),
        "--source",
        "eval",
        "--compare-source",
        "eval",
        "--compare-scenario-type",
        "shifted",
        "--scenario-type",
        "nominal",
        "--reports-root",
        str(reports_root),
        "--bundle-name",
        "cli_dynamic_bundle",
        "--static-bundle-name",
        "cli_static_bundle",
        "--output",
        str(output_path),
    ]
    result = subprocess.run(
        command,
        cwd=ROOT.parent,
        capture_output=True,
        text=True,
        check=True,
    )

    assert output_path.exists()
    assert (report_dir / "dynamic_report.json").exists()
    assert (report_dir / "summary.json").exists()
    assert (report_dir / "manifest.json").exists()
    assert namespace_manifest_path.exists()
    assert namespace_contract_path.exists()

    stdout_payload = json.loads(result.stdout)
    report_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert stdout_payload["report_dir"] == str(report_dir)
    assert stdout_payload["namespace_manifest_path"] == str(namespace_manifest_path)
    assert stdout_payload["namespace_contract_path"] == str(namespace_contract_path)
    assert report_payload["report_type"] == "dynamic_analyzer_report.v1"
    assert sorted(report_payload["primary_run_ids"]) == ["cli_nominal_run"]
    assert sorted(report_payload["comparison_run_ids"]) == ["cli_shifted_run"]
    assert report_payload["metadata"]["static_context"]["bundle_name"] == "cli_static_bundle"

    loaded = load_accepted_run_directory(nominal_run)
    assert loaded["acceptance"]["passed"] is True
