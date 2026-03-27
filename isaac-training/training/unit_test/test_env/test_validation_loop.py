import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from repair.acceptance import accept_repair
from repair.patch_executor import build_validation_context_preview, run_repair_bundle_write
from repair.comparison import compare_validation_runs
from repair.decision import decide_validation
import repair.validation_runner as validation_runner_module
from runtime_logging.logger import create_run_logger
from repair.repair_validator import build_phase9_validation_request, validate_repair
from repair.rule_based_repair import propose_rule_based_repairs
from repair.validation_request_loader import load_validation_request_bundle
from repair.validation_runner import (
    build_validation_rerun_tasks,
    prepare_validation_runs,
    run_validation_bundle_write,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
REWARD_SPEC = REPO_ROOT / "isaac-training" / "training" / "cfg" / "spec_cfg" / "reward_spec_v0.yaml"
BOUNDARY_CFG = REPO_ROOT / "isaac-training" / "training" / "cfg" / "env_cfg" / "scene_cfg_boundary_critical.yaml"
SHIFTED_CFG = REPO_ROOT / "isaac-training" / "training" / "cfg" / "env_cfg" / "scene_cfg_shifted.yaml"


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _get_path_value(payload, dotted_path: str):
    current = payload
    for part in dotted_path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            current = current[index] if index < len(current) else None
        else:
            return None
    return current


def _make_report_bundle(tmp_path: Path, *, claim_type: str, summary: str, target_ref: Path) -> Path:
    bundle = tmp_path / "analysis" / "report" / f"report_{claim_type.lower().replace('-', '_')}"
    primary_direction = {
        "C-R": "reward",
        "E-C": "environment",
        "E-R": "mixed",
    }[claim_type]
    impacted_components = {
        "C-R": ["C", "R"],
        "E-C": ["C", "E"],
        "E-R": ["E", "R"],
    }[claim_type]
    handoff_id = f"repair_handoff:{claim_type}:primary"
    selected_claim = {
        "handoff_id": handoff_id,
        "claim_type": claim_type,
        "selected_from": "analysis/static" if claim_type != "E-R" else "analysis/semantic",
        "selected_from_rank": 1,
        "severity": "high",
        "confidence": 0.9,
        "support_status": "machine_direct" if claim_type != "E-R" else "semantic_supported",
        "summary": summary,
        "impacted_components": impacted_components,
        "suggested_repair_direction": primary_direction,
        "required_evidence_refs": [str(target_ref)],
        "source_record_ids": [handoff_id.replace("repair_handoff:", "source:")],
        "selection_basis": "phase9_test_fixture",
    }
    _write_json(
        bundle / "report.json",
        {
            "report_type": "phase7_unified_report.v1",
            "spec_version": "v0",
            "passed": False,
            "max_severity": "high",
            "num_ranked_findings": 1,
            "input_bundles": {},
            "ranked_findings": [],
            "root_cause_summary": {
                "primary_claim_type": claim_type,
                "primary_summary": summary,
            },
            "repair_handoff": {},
            "metadata": {"bundle_name": bundle.name},
        },
    )
    _write_json(
        bundle / "repair_handoff.json",
        {
            "handoff_type": "phase8_repair_handoff.v1",
            "primary_claim_type": claim_type,
            "primary_repair_direction": primary_direction,
            "claim_record_schema": "phase7_repair_ready_claim.v1",
            "selection_policy": "phase7_ranked_claim_selection.v3",
            "impacted_components_union": impacted_components,
            "selected_claims": [selected_claim],
            "repair_order": [
                {
                    "order": 1,
                    "handoff_id": handoff_id,
                    "claim_type": claim_type,
                    "selected_from": selected_claim["selected_from"],
                    "suggested_repair_direction": primary_direction,
                    "selection_basis": "phase9_test_fixture",
                }
            ],
            "required_evidence_contract": {},
            "selection_summary": {
                "primary_claim_type": claim_type,
                "selection_focus_order": [claim_type],
                "selected_claim_count": 1,
            },
            "metadata": {"phase8_ready": True},
        },
    )
    _write_json(
        bundle / "summary.json",
        {
            "report_type": "phase7_unified_report.v1",
            "spec_version": "v0",
            "passed": False,
            "max_severity": "high",
            "num_ranked_findings": 1,
            "primary_claim_type": claim_type,
            "repair_ready_claims": 1,
        },
    )
    _write_json(
        bundle / "manifest.json",
        {
            "bundle_type": "report_generation_bundle.v1",
            "metadata": {"bundle_name": bundle.name},
        },
    )
    return bundle


def _make_repair_bundle(tmp_path: Path, *, claim_type: str, summary: str, target_ref: Path) -> Path:
    report_bundle = _make_report_bundle(tmp_path, claim_type=claim_type, summary=summary, target_ref=target_ref)
    plan = propose_rule_based_repairs(report_bundle_dir=report_bundle)
    acceptance = accept_repair(plan.to_dict())
    repair_validation = validate_repair(plan.to_dict(), acceptance=acceptance)
    validation_request = build_phase9_validation_request(
        plan.to_dict(),
        repair_validation=repair_validation,
        acceptance=acceptance,
        bundle_name=f"repair_{claim_type.lower().replace('-', '_')}",
    )
    bundle_paths = run_repair_bundle_write(
        plan,
        acceptance,
        repair_validation=repair_validation,
        validation_request=validation_request,
        reports_root=tmp_path,
        bundle_name=f"repair_{claim_type.lower().replace('-', '_')}",
    )
    return bundle_paths["repair_dir"]


def _make_accepted_run_dir(
    base_dir: Path,
    *,
    name: str,
    source: str,
    scenario_type: str,
    scene_cfg_name: str,
    metrics: dict,
) -> Path:
    run_dir = base_dir / name
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "episodes").mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_text(
        json.dumps({"run_id": name, "source": source}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    summary = {
        "episode_count": 1,
        "success_rate": 0.0,
        "collision_rate": 0.0,
        "min_distance": 0.0,
        "average_return": 0.0,
        "near_violation_ratio": 0.0,
        **metrics,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (run_dir / "acceptance.json").write_text(
        json.dumps({"passed": True, "max_severity": "info"}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    episode_row = {
        "episode_index": 0,
        "seed": 0,
        "scene_id": f"{name}:scene0",
        "scenario_type": scenario_type,
        "scene_cfg_name": scene_cfg_name,
        "num_steps": 1,
        "trajectory_length": 1.0,
        "return_total": float(summary.get("average_return", 0.0)),
        "reward_components_total": {},
        "success_flag": bool(summary.get("success_rate", 0.0) > 0.0),
        "collision_flag": bool(summary.get("collision_rate", 0.0) > 0.0),
        "out_of_bounds_flag": False,
        "min_obstacle_distance": float(summary.get("min_distance", 0.0)),
        "near_violation_steps": 0,
        "near_violation_ratio": float(summary.get("near_violation_ratio", 0.0)),
        "final_goal_distance": 0.0,
        "done_type": "success" if summary.get("success_rate", 0.0) > 0 else "unknown",
        "source": source,
    }
    (run_dir / "episodes.jsonl").write_text(json.dumps(episode_row) + "\n", encoding="utf-8")
    (run_dir / "steps.jsonl").write_text("", encoding="utf-8")
    (run_dir / "episodes" / "episode_0000.json").write_text(
        json.dumps({"summary": episode_row}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return run_dir


def test_validation_request_loader_reads_repair_bundle(tmp_path):
    repair_bundle_dir = _make_repair_bundle(
        tmp_path,
        claim_type="E-R",
        summary="Shifted-family robustness is too weak under distribution shift.",
        target_ref=SHIFTED_CFG,
    )
    loaded = load_validation_request_bundle(repair_bundle_dir, require_phase9_ready=True)

    assert loaded["loader_type"] == "phase9_validation_request_loader.v1"
    assert loaded["request_valid"] is True
    assert loaded["phase9_ready"] is True
    assert loaded["primary_claim_type"] == "E-R"
    assert loaded["preferred_execution_modes"] == ["baseline", "eval"]
    assert loaded["scene_family_scope"] == ["nominal", "shifted"]
    assert loaded["resolved_paths"]["validation_context_preview.json"].endswith("validation_context_preview.json")


def test_validation_context_preview_builds_patched_yaml_state(tmp_path):
    repair_bundle_dir = _make_repair_bundle(
        tmp_path,
        claim_type="E-C",
        summary="Boundary-critical family undercovers critical states near the route corridor.",
        target_ref=BOUNDARY_CFG,
    )
    loaded = load_validation_request_bundle(repair_bundle_dir, require_phase9_ready=True)
    preview = build_validation_context_preview(
        loaded["repair_plan"],
        validation_request=loaded["validation_request"],
    )

    assert preview["preview_type"] == "phase9_validation_context_preview.v1"
    assert preview["source_mutation_performed"] is False
    assert preview["preferred_execution_modes"] == ["baseline", "eval"]
    file_preview = preview["file_previews"][0]
    operation = file_preview["operations"][0]
    assert _get_path_value(file_preview["original_document"], operation["target_path"]) == operation["before"]
    assert _get_path_value(file_preview["patched_document"], operation["target_path"]) == operation["after"]


def test_validation_context_preview_is_written_into_repair_bundle(tmp_path):
    repair_bundle_dir = _make_repair_bundle(
        tmp_path,
        claim_type="C-R",
        summary="Reward progress proxy dominates safety shaping near boundary states.",
        target_ref=REWARD_SPEC,
    )
    loaded = load_validation_request_bundle(repair_bundle_dir, require_phase9_ready=True)

    preview = loaded["validation_context_preview"]
    assert preview["preview_type"] == "phase9_validation_context_preview.v1"
    assert preview["preview_mode"] == "non_destructive_validation_context"
    assert preview["validation_targets"] == loaded["validation_targets"]
    assert preview["target_file_count"] >= 1


def test_prepare_validation_runs_and_decision_accepts_improving_repair(tmp_path):
    repair_bundle_dir = _make_repair_bundle(
        tmp_path,
        claim_type="E-R",
        summary="Shifted-family robustness is too weak under distribution shift.",
        target_ref=SHIFTED_CFG,
    )
    logs_root = tmp_path / "logs"
    original_run = _make_accepted_run_dir(
        logs_root,
        name="baseline_nominal_original",
        source="baseline",
        scenario_type="shifted",
        scene_cfg_name="scene_cfg_shifted.yaml",
        metrics={
            "W_ER": 0.40,
            "min_distance": 0.60,
            "collision_rate": 0.10,
            "near_violation_ratio": 0.20,
            "average_return": 3.00,
            "success_rate": 0.50,
        },
    )
    repaired_run = _make_accepted_run_dir(
        logs_root,
        name="baseline_nominal_repaired",
        source="baseline",
        scenario_type="shifted",
        scene_cfg_name="scene_cfg_shifted.yaml",
        metrics={
            "W_ER": 0.15,
            "min_distance": 0.82,
            "collision_rate": 0.04,
            "near_violation_ratio": 0.10,
            "average_return": 2.98,
            "success_rate": 0.52,
        },
    )

    prepared = prepare_validation_runs(
        repair_bundle_dir=repair_bundle_dir,
        logs_root=logs_root,
        original_run_dirs=[original_run],
        repaired_run_dirs=[repaired_run],
    )
    comparison = compare_validation_runs(
        primary_claim_type=prepared["validation_input"]["primary_claim_type"],
        validation_targets=prepared["validation_input"]["validation_targets"],
        original_runs=prepared["original_runs"],
        repaired_runs=prepared["repaired_runs"],
    )
    decision = decide_validation(comparison, performance_regression_epsilon=0.05)

    assert prepared["validation_plan"]["primary_claim_type"] == "E-R"
    assert comparison["metric_deltas"]["W_ER"]["improvement"] > 0.0
    assert decision["decision_status"] == "accepted"
    assert decision["accepted"] is True


def test_compare_validation_runs_derives_nominal_vs_shifted_success_gap(tmp_path):
    repair_bundle_dir = _make_repair_bundle(
        tmp_path,
        claim_type="E-R",
        summary="Shifted-family robustness is too weak under distribution shift.",
        target_ref=SHIFTED_CFG,
    )
    logs_root = tmp_path / "logs"
    original_nominal = _make_accepted_run_dir(
        logs_root,
        name="baseline_nominal_original",
        source="baseline",
        scenario_type="nominal",
        scene_cfg_name="scene_cfg_nominal.yaml",
        metrics={
            "W_ER": 0.40,
            "min_distance": 0.72,
            "collision_rate": 0.04,
            "near_violation_ratio": 0.10,
            "average_return": 3.20,
            "success_rate": 0.82,
        },
    )
    original_shifted = _make_accepted_run_dir(
        logs_root,
        name="baseline_shifted_original",
        source="baseline",
        scenario_type="shifted",
        scene_cfg_name="scene_cfg_shifted.yaml",
        metrics={
            "W_ER": 0.44,
            "min_distance": 0.55,
            "collision_rate": 0.10,
            "near_violation_ratio": 0.22,
            "average_return": 2.85,
            "success_rate": 0.46,
        },
    )
    repaired_nominal = _make_accepted_run_dir(
        logs_root,
        name="baseline_nominal_repaired",
        source="baseline",
        scenario_type="nominal",
        scene_cfg_name="scene_cfg_nominal.yaml",
        metrics={
            "W_ER": 0.24,
            "min_distance": 0.78,
            "collision_rate": 0.03,
            "near_violation_ratio": 0.08,
            "average_return": 3.22,
            "success_rate": 0.84,
        },
    )
    repaired_shifted = _make_accepted_run_dir(
        logs_root,
        name="baseline_shifted_repaired",
        source="baseline",
        scenario_type="shifted",
        scene_cfg_name="scene_cfg_shifted.yaml",
        metrics={
            "W_ER": 0.20,
            "min_distance": 0.71,
            "collision_rate": 0.05,
            "near_violation_ratio": 0.11,
            "average_return": 3.00,
            "success_rate": 0.70,
        },
    )

    prepared = prepare_validation_runs(
        repair_bundle_dir=repair_bundle_dir,
        logs_root=logs_root,
        original_run_dirs=[original_nominal, original_shifted],
        repaired_run_dirs=[repaired_nominal, repaired_shifted],
    )
    comparison = compare_validation_runs(
        primary_claim_type=prepared["validation_input"]["primary_claim_type"],
        validation_targets=prepared["validation_input"]["validation_targets"],
        original_runs=prepared["original_runs"],
        repaired_runs=prepared["repaired_runs"],
    )

    gap_payload = comparison["metric_deltas"]["nominal_vs_shifted_success_gap"]
    assert round(gap_payload["original"], 4) == 0.36
    assert round(gap_payload["repaired"], 4) == 0.14
    assert gap_payload["improvement"] > 0.0
    assert "nominal" in comparison["original_by_scenario"]
    assert "shifted" in comparison["original_by_scenario"]


def test_validation_decision_rejects_large_performance_regression(tmp_path):
    repair_bundle_dir = _make_repair_bundle(
        tmp_path,
        claim_type="C-R",
        summary="Reward progress proxy dominates safety shaping near boundary states.",
        target_ref=REWARD_SPEC,
    )
    logs_root = tmp_path / "logs"
    original_run = _make_accepted_run_dir(
        logs_root,
        name="eval_nominal_original",
        source="eval",
        scenario_type="nominal",
        scene_cfg_name="scene_cfg_nominal.yaml",
        metrics={
            "W_CR": 0.35,
            "min_distance": 0.55,
            "collision_rate": 0.08,
            "near_violation_ratio": 0.21,
            "average_return": 4.20,
            "success_rate": 0.70,
        },
    )
    repaired_run = _make_accepted_run_dir(
        logs_root,
        name="eval_nominal_repaired",
        source="eval",
        scenario_type="nominal",
        scene_cfg_name="scene_cfg_nominal.yaml",
        metrics={
            "W_CR": 0.20,
            "min_distance": 0.68,
            "collision_rate": 0.03,
            "near_violation_ratio": 0.09,
            "average_return": 3.70,
            "success_rate": 0.60,
        },
    )
    prepared = prepare_validation_runs(
        repair_bundle_dir=repair_bundle_dir,
        logs_root=logs_root,
        original_run_dirs=[original_run],
        repaired_run_dirs=[repaired_run],
    )
    comparison = compare_validation_runs(
        primary_claim_type=prepared["validation_input"]["primary_claim_type"],
        validation_targets=prepared["validation_input"]["validation_targets"],
        original_runs=prepared["original_runs"],
        repaired_runs=prepared["repaired_runs"],
    )
    decision = decide_validation(comparison, performance_regression_epsilon=0.05)

    assert comparison["metric_deltas"]["W_CR"]["improvement"] > 0.0
    assert comparison["metric_deltas"]["average_return"]["improvement"] < -0.05
    assert decision["decision_status"] == "rejected"
    assert decision["accepted"] is False


def test_prepare_validation_runs_trigger_rerun_creates_preview_repaired_runs(tmp_path):
    repair_bundle_dir = _make_repair_bundle(
        tmp_path,
        claim_type="E-R",
        summary="Shifted-family robustness is too weak under distribution shift.",
        target_ref=SHIFTED_CFG,
    )
    logs_root = tmp_path / "logs"
    original_nominal = _make_accepted_run_dir(
        logs_root,
        name="baseline_nominal_original",
        source="baseline",
        scenario_type="nominal",
        scene_cfg_name="scene_cfg_nominal.yaml",
        metrics={
            "W_ER": 0.34,
            "min_distance": 0.74,
            "collision_rate": 0.04,
            "near_violation_ratio": 0.10,
            "average_return": 3.25,
            "success_rate": 0.80,
        },
    )
    original_shifted = _make_accepted_run_dir(
        logs_root,
        name="baseline_shifted_original",
        source="baseline",
        scenario_type="shifted",
        scene_cfg_name="scene_cfg_shifted.yaml",
        metrics={
            "W_ER": 0.46,
            "min_distance": 0.52,
            "collision_rate": 0.12,
            "near_violation_ratio": 0.25,
            "average_return": 2.70,
            "success_rate": 0.42,
        },
    )

    prepared = prepare_validation_runs(
        repair_bundle_dir=repair_bundle_dir,
        logs_root=logs_root,
        original_run_dirs=[original_nominal, original_shifted],
        trigger_rerun=True,
        repaired_logs_root=tmp_path / "repaired_logs",
    )
    comparison = compare_validation_runs(
        primary_claim_type=prepared["validation_input"]["primary_claim_type"],
        validation_targets=prepared["validation_input"]["validation_targets"],
        original_runs=prepared["original_runs"],
        repaired_runs=prepared["repaired_runs"],
    )

    assert prepared["validation_runs"]["trigger_rerun"] is True
    assert len(prepared["validation_runs"]["rerun_tasks"]) == 2
    assert len(prepared["repaired_runs"]) == 2
    assert all(Path(item["run_dir"]).exists() for item in prepared["validation_runs"]["repaired_runs"])
    assert "nominal_vs_shifted_success_gap" in comparison["metric_deltas"]
    assert comparison["metric_deltas"]["nominal_vs_shifted_success_gap"]["improvement"] > 0.0


def test_build_validation_rerun_tasks_emit_bounded_adapter_metadata(tmp_path):
    repair_bundle_dir = _make_repair_bundle(
        tmp_path,
        claim_type="E-R",
        summary="Shifted-family robustness is too weak under distribution shift.",
        target_ref=SHIFTED_CFG,
    )
    loaded = load_validation_request_bundle(repair_bundle_dir, require_phase9_ready=True)

    baseline_task = build_validation_rerun_tasks(
        validation_input={**loaded, "preferred_execution_modes": ["baseline"], "scene_family_scope": ["nominal"]},
        original_runs=[],
        repaired_logs_root=tmp_path / "repaired_logs",
    )[0]
    eval_task = build_validation_rerun_tasks(
        validation_input={**loaded, "preferred_execution_modes": ["eval"], "scene_family_scope": ["shifted"]},
        original_runs=[],
        repaired_logs_root=tmp_path / "repaired_logs",
    )[0]
    train_task = build_validation_rerun_tasks(
        validation_input={**loaded, "preferred_execution_modes": ["train"], "scene_family_scope": ["nominal"]},
        original_runs=[],
        repaired_logs_root=tmp_path / "repaired_logs",
    )[0]

    assert baseline_task["adapter_type"] == "phase9_bounded_baseline_rerun_adapter.v1"
    assert baseline_task["supports_real_execution"] is True
    assert baseline_task["script_path"].endswith("run_baseline.py")
    assert "baseline.num_episodes=1" in baseline_task["hydra_overrides"]

    assert eval_task["adapter_type"] == "phase9_bounded_eval_rerun_adapter.v1"
    assert eval_task["script_path"].endswith("eval.py")
    assert "wandb.mode=offline" in eval_task["hydra_overrides"]
    assert any(item.startswith("max_frame_num=") for item in eval_task["hydra_overrides"])

    assert train_task["adapter_type"] == "phase9_bounded_train_rerun_adapter.v1"
    assert train_task["script_path"].endswith("train.py")
    assert "skip_periodic_eval=True" in train_task["hydra_overrides"]
    assert train_task["bounded_limits"]["max_frame_num"] == 2048
    assert train_task["command_preview"][0] == "python3"
    assert train_task["env_overrides"]["CRE_RUN_USE_TIMESTAMP"] == "0"
    assert train_task["expected_run_dir"].endswith(train_task["output_run_name"])


def test_create_run_logger_honors_bounded_rerun_env_overrides(tmp_path, monkeypatch):
    monkeypatch.setenv("CRE_RUN_NAME_OVERRIDE", "validation_real_eval_00")
    monkeypatch.setenv("CRE_RUN_LOG_BASE_DIR", str(tmp_path / "bounded_logs"))
    monkeypatch.setenv("CRE_RUN_USE_TIMESTAMP", "0")

    logger = create_run_logger(
        source="eval",
        run_name="eval_rollout",
        base_dir=tmp_path / "ignored_logs",
        use_timestamp=True,
    )

    assert logger.run_id == "validation_real_eval_00"
    assert logger.run_dir == (tmp_path / "bounded_logs" / "validation_real_eval_00")
    assert logger.run_dir.exists()


def test_prepare_validation_runs_subprocess_mode_uses_bounded_execution_adapter(tmp_path, monkeypatch):
    repair_bundle_dir = _make_repair_bundle(
        tmp_path,
        claim_type="E-R",
        summary="Shifted-family robustness is too weak under distribution shift.",
        target_ref=SHIFTED_CFG,
    )
    logs_root = tmp_path / "logs"
    original_run = _make_accepted_run_dir(
        logs_root,
        name="baseline_shifted_original",
        source="baseline",
        scenario_type="shifted",
        scene_cfg_name="scene_cfg_shifted.yaml",
        metrics={
            "W_ER": 0.46,
            "min_distance": 0.52,
            "collision_rate": 0.12,
            "near_violation_ratio": 0.25,
            "average_return": 2.70,
            "success_rate": 0.42,
        },
    )

    def _fake_invoke(command, *, cwd, env, timeout_sec=600):
        run_dir = _make_accepted_run_dir(
            Path(env["CRE_RUN_LOG_BASE_DIR"]),
            name=env["CRE_RUN_NAME_OVERRIDE"],
            source=env["CRE_VALIDATION_EXECUTION_MODE"],
            scenario_type=env["CRE_VALIDATION_SCENARIO_TYPE"],
            scene_cfg_name=env["CRE_VALIDATION_SCENE_CFG_NAME"],
            metrics={
                "W_ER": 0.18,
                "min_distance": 0.74,
                "collision_rate": 0.04,
                "near_violation_ratio": 0.10,
                "average_return": 2.96,
                "success_rate": 0.68,
            },
        )
        assert run_dir.exists()

        class _Result:
            returncode = 0
            stdout = "subprocess adapter smoke"
            stderr = ""

        return _Result()

    monkeypatch.setattr(validation_runner_module, "_invoke_subprocess_command", _fake_invoke)

    prepared = prepare_validation_runs(
        repair_bundle_dir=repair_bundle_dir,
        logs_root=logs_root,
        original_run_dirs=[original_run],
        trigger_rerun=True,
        rerun_mode="subprocess",
        repaired_logs_root=tmp_path / "repaired_logs",
    )

    task = prepared["validation_runs"]["rerun_tasks"][0]
    result = prepared["validation_runs"]["triggered_rerun_results"]["task_results"][0]
    assert prepared["validation_runs"]["requested_rerun_mode"] == "subprocess"
    assert task["adapter_type"] == "phase9_bounded_baseline_rerun_adapter.v1"
    assert result["runner_mode"] == "bounded_subprocess_rerun.v1"
    assert result["status"] == "completed"
    assert result["fallback_used"] is False
    assert Path(result["run_dir"]).exists()
    assert result["subprocess_returncode"] == 0


def test_post_repair_evidence_contract_exposes_phase10_consumer_requirements(tmp_path):
    repair_bundle_dir = _make_repair_bundle(
        tmp_path,
        claim_type="E-R",
        summary="Shifted-family robustness is too weak under distribution shift.",
        target_ref=SHIFTED_CFG,
    )
    logs_root = tmp_path / "logs"
    original_nominal = _make_accepted_run_dir(
        logs_root,
        name="eval_nominal_original",
        source="eval",
        scenario_type="nominal",
        scene_cfg_name="scene_cfg_nominal.yaml",
        metrics={
            "W_ER": 0.33,
            "min_distance": 0.73,
            "collision_rate": 0.04,
            "near_violation_ratio": 0.11,
            "average_return": 3.10,
            "success_rate": 0.76,
        },
    )
    original_shifted = _make_accepted_run_dir(
        logs_root,
        name="eval_shifted_original",
        source="eval",
        scenario_type="shifted",
        scene_cfg_name="scene_cfg_shifted.yaml",
        metrics={
            "W_ER": 0.46,
            "min_distance": 0.54,
            "collision_rate": 0.09,
            "near_violation_ratio": 0.22,
            "average_return": 2.82,
            "success_rate": 0.44,
        },
    )

    prepared = prepare_validation_runs(
        repair_bundle_dir=repair_bundle_dir,
        logs_root=logs_root,
        original_run_dirs=[original_nominal, original_shifted],
        trigger_rerun=True,
        repaired_logs_root=tmp_path / "repaired_logs",
    )
    comparison = compare_validation_runs(
        primary_claim_type=prepared["validation_input"]["primary_claim_type"],
        validation_targets=prepared["validation_input"]["validation_targets"],
        original_runs=prepared["original_runs"],
        repaired_runs=prepared["repaired_runs"],
    )
    decision = decide_validation(comparison, performance_regression_epsilon=0.05)
    bundle_paths = run_validation_bundle_write(
        validation_plan=prepared["validation_plan"],
        validation_runs=prepared["validation_runs"],
        comparison=comparison,
        decision=decision,
        reports_root=tmp_path,
        bundle_name="validation_contract_fixture",
    )

    evidence = json.loads(bundle_paths["post_repair_evidence_path"].read_text(encoding="utf-8"))
    contract = evidence["consumer_contract"]

    assert evidence["evidence_schema_version"] == "phase10_post_repair_evidence.v2"
    assert evidence["requested_rerun_mode"] == "preview"
    assert contract["contract_type"] == "phase10_post_repair_evidence_consumer.v2"
    assert "required_rerun_task_fields" in contract
    assert "required_triggered_result_fields" in contract
    assert "adapter_type" in contract["required_rerun_task_fields"]
    assert "hydra_overrides" in contract["required_rerun_task_fields"]
    assert "run_dir" in contract["required_triggered_result_fields"]
    assert contract["consumer_expectations"]["bounded_rerun_adapter_metadata_required"] is True


def test_run_validation_audit_cli_smoke(tmp_path):
    repair_bundle_dir = _make_repair_bundle(
        tmp_path,
        claim_type="E-C",
        summary="Boundary-critical family undercovers critical states near the route corridor.",
        target_ref=BOUNDARY_CFG,
    )
    logs_root = tmp_path / "logs"
    original_run = _make_accepted_run_dir(
        logs_root,
        name="baseline_boundary_original",
        source="baseline",
        scenario_type="boundary_critical",
        scene_cfg_name="scene_cfg_boundary_critical.yaml",
        metrics={
            "W_EC": 0.42,
            "min_distance": 0.48,
            "collision_rate": 0.12,
            "near_violation_ratio": 0.24,
            "average_return": 2.80,
            "success_rate": 0.42,
        },
    )
    repaired_run = _make_accepted_run_dir(
        logs_root,
        name="baseline_boundary_repaired",
        source="baseline",
        scenario_type="boundary_critical",
        scene_cfg_name="scene_cfg_boundary_critical.yaml",
        metrics={
            "W_EC": 0.18,
            "min_distance": 0.66,
            "collision_rate": 0.04,
            "near_violation_ratio": 0.10,
            "average_return": 2.82,
            "success_rate": 0.48,
        },
    )

    output_path = tmp_path / "validation_decision_copy.json"
    script_path = ROOT / "scripts" / "run_validation_audit.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--repair-bundle-dir",
            str(repair_bundle_dir),
            "--logs-root",
            str(logs_root),
            "--original-run-dir",
            str(original_run),
            "--trigger-rerun",
            "--rerun-mode",
            "preview",
            "--repaired-logs-root",
            str(tmp_path / "repaired_logs"),
            "--reports-root",
            str(tmp_path),
            "--bundle-name",
            "validation_cli_fixture",
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["accepted"] is True
    assert payload["decision_status"] == "accepted"
    assert payload["primary_claim_type"] == "E-C"
    assert payload["original_run_count"] == 1
    assert payload["repaired_run_count"] == 1
    assert payload["trigger_rerun"] is True
    assert Path(payload["validation_plan_path"]).exists()
    assert Path(payload["validation_runs_path"]).exists()
    assert Path(payload["comparison_path"]).exists()
    assert Path(payload["validation_decision_path"]).exists()
    assert Path(payload["post_repair_evidence_path"]).exists()
    assert Path(payload["validation_summary_md_path"]).exists()
    assert output_path.exists()
