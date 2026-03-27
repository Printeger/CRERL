import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analyzers.report_contract import INTEGRATION_AUDIT_MODE
from envs.runtime.scene_family_bridge import build_scene_family_runtime_profile
from pipeline.integration_bundle import run_integration_audit_bundle


def _write_preview(path: Path) -> Path:
    payload = {
        "preview_type": "phase9_validation_context_preview.v1",
        "preview_mode": "non_destructive_validation_context",
        "source_mutation_performed": False,
        "repair_bundle_name": "repair_fixture",
        "phase9_entrypoint": "run_repair_audit.py",
        "preferred_execution_modes": ["baseline", "eval", "train"],
        "scene_family_scope": ["nominal", "shifted"],
        "validation_targets": ["nominal_vs_shifted_success_gap"],
        "target_file_count": 1,
        "file_previews": [
            {
                "target_file": "isaac-training/training/cfg/spec_cfg/reward_spec_v0.yaml",
                "resolved_target_file": "isaac-training/training/cfg/spec_cfg/reward_spec_v0.yaml",
                "document_type": "yaml",
                "operation_count": 1,
                "operations": [
                    {
                        "target_file": "isaac-training/training/cfg/spec_cfg/reward_spec_v0.yaml",
                        "target_path": "components.reward_progress.weight",
                        "before": 1.0,
                        "after": 0.8,
                    }
                ],
            }
        ],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _write_accepted_run(run_dir: Path, *, run_name: str, source: str, execution_mode: str, repair_preview_bound: bool) -> Path:
    run_path = run_dir / run_name
    run_path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_id": run_name,
        "source": source,
        "run_metadata": {
            "run_metadata_type": "phase10_native_execution_run_metadata.v1",
            "source": source,
            "execution_mode": execution_mode,
            "scenario_type": "nominal",
            "scene_family": "nominal",
            "scene_cfg_name": "scene_cfg_nominal.yaml",
            "scene_id_prefix": f"{execution_mode}_nominal",
            "native_repair_preview_consumption": bool(repair_preview_bound),
            "integration_binding_type": "phase10_env_runtime_binding.v1",
            "repair_preview_binding": {
                "binding_type": "phase10_repair_preview_binding.v1",
                "preview_bound": bool(repair_preview_bound),
            },
            "effective_scene_binding": {
                "binding_type": "phase10_effective_scene_binding.v1",
                "scene_cfg_name": "scene_cfg_nominal.yaml",
            },
            "effective_spec_binding": {
                "binding_type": "phase10_effective_spec_binding.v1",
                "repair_preview_bound": bool(repair_preview_bound),
            },
        },
    }
    summary = {
        "run_id": run_name,
        "run_metadata": manifest["run_metadata"],
        "episode_count": 1,
        "success_rate": 0.0,
        "collision_rate": 0.0,
        "min_distance": 0.8,
        "average_return": 4.0,
        "near_violation_ratio": 0.0,
    }
    acceptance = {"passed": True}
    (run_path / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (run_path / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (run_path / "acceptance.json").write_text(json.dumps(acceptance, indent=2, sort_keys=True), encoding="utf-8")
    (run_path / "steps.jsonl").write_text("", encoding="utf-8")
    (run_path / "episodes.jsonl").write_text("", encoding="utf-8")
    return run_path


def _write_dynamic_bundle(bundle_dir: Path, *, bundle_name: str, primary_run_id: str, comparison_run_id: str) -> Path:
    target = bundle_dir / bundle_name
    target.mkdir(parents=True, exist_ok=True)
    report = {
        "report_type": "phase5_dynamic_report.v1",
        "passed": True,
        "max_severity": "warning",
        "primary_run_ids": [primary_run_id],
        "comparison_run_ids": [comparison_run_id],
        "witnesses": [
            {"witness_id": "W_CR", "score": 0.0},
            {"witness_id": "W_EC", "score": 0.25},
            {"witness_id": "W_ER", "score": 0.1},
        ],
    }
    (target / "dynamic_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    (target / "manifest.json").write_text(
        json.dumps({"bundle_type": "phase5_dynamic_analysis_bundle.v1"}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (target / "summary.json").write_text(
        json.dumps({"passed": True, "max_severity": "warning"}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def test_scene_family_profile_binds_repair_preview_context(tmp_path: Path):
    preview_path = _write_preview(tmp_path / "validation_context_preview.json")
    profile = build_scene_family_runtime_profile(
        {
            "enabled": True,
            "family": "nominal",
            "difficulty": 0.5,
            "gravity_tilt_enabled": False,
        },
        seed=17,
        repair_context={"validation_context_preview": str(preview_path)},
    )

    assert profile["repair_preview_binding"]["preview_bound"] is True
    assert profile["repair_preview_binding"]["repair_bundle_name"] == "repair_fixture"
    assert profile["effective_scene_binding"]["repair_preview_bound"] is True
    assert profile["effective_spec_binding"]["target_file_count"] == 1
    assert "components.reward_progress.weight" in profile["effective_spec_binding"]["target_paths"]


def test_run_integration_audit_bundle_writes_namespaced_bundle(tmp_path: Path):
    preview_path = _write_preview(tmp_path / "validation_context_preview.json")
    audit, bundle_paths = run_integration_audit_bundle(
        scene_family="nominal",
        repair_preview_path=str(preview_path),
        reports_root=tmp_path,
        bundle_name="integration_fixture",
    )

    assert audit.integration_acceptance["passed"] is True
    assert bundle_paths["integration_dir"].exists()
    assert bundle_paths["namespace_manifest_path"].exists()
    assert bundle_paths["namespace_contract_path"].exists()

    execution_matrix = json.loads(bundle_paths["execution_matrix_path"].read_text(encoding="utf-8"))
    assert {item["execution_mode"] for item in execution_matrix["execution_modes"]} == {"baseline", "eval", "train"}
    assert all(item["scene_family_backend_direct"] for item in execution_matrix["execution_modes"])
    assert all(item["repair_preview_bound"] for item in execution_matrix["execution_modes"])
    assert all(item["comparison_ready_direct"] for item in execution_matrix["execution_modes"])

    run_binding = json.loads(bundle_paths["run_binding_path"].read_text(encoding="utf-8"))
    assert run_binding["bindings_by_mode"]["train"]["effective_scene_binding"]["scene_cfg_name"] == "scene_cfg_nominal.yaml"
    assert run_binding["bindings_by_mode"]["baseline"]["repair_preview_binding"]["preview_bound"] is True


def test_run_integration_audit_bundle_attaches_native_execution_consumer(tmp_path: Path):
    preview_path = _write_preview(tmp_path / "validation_context_preview.json")
    native_logs_root = tmp_path / "logs"
    baseline_original = _write_accepted_run(
        native_logs_root,
        run_name="phase10_baseline_original",
        source="baseline_greedy",
        execution_mode="baseline",
        repair_preview_bound=False,
    )
    baseline_repaired = _write_accepted_run(
        native_logs_root,
        run_name="phase10_baseline_repaired",
        source="baseline_greedy",
        execution_mode="baseline",
        repair_preview_bound=True,
    )
    eval_repaired = _write_accepted_run(
        native_logs_root,
        run_name="phase10_eval_repaired",
        source="eval",
        execution_mode="eval",
        repair_preview_bound=True,
    )
    train_repaired = _write_accepted_run(
        native_logs_root,
        run_name="phase10_train_repaired",
        source="train",
        execution_mode="train",
        repair_preview_bound=True,
    )
    dynamic_bundle = _write_dynamic_bundle(
        tmp_path / "analysis" / "dynamic",
        bundle_name="dynamic_phase10_native_original_vs_repaired",
        primary_run_id="phase10_baseline_original",
        comparison_run_id="phase10_baseline_repaired",
    )

    audit, bundle_paths = run_integration_audit_bundle(
        scene_family="nominal",
        repair_preview_path=str(preview_path),
        reports_root=tmp_path,
        bundle_name="integration_native_fixture",
        native_run_dirs=[baseline_original, baseline_repaired, eval_repaired, train_repaired],
        comparison_bundle_dirs=[dynamic_bundle],
    )

    consumer = json.loads(bundle_paths["native_execution_consumer_path"].read_text(encoding="utf-8"))
    assert consumer["consumer_type"] == "phase10_native_execution_consumer.v1"
    assert sorted(consumer["native_ready_modes"]) == ["baseline", "eval", "train"]
    assert consumer["comparison_proven_modes"] == ["baseline"]
    assert audit.integration_summary["native_ready_modes"] == ["baseline", "eval", "train"]
    assert audit.integration_acceptance["passed"] is True


def test_run_integration_audit_cli_smoke(tmp_path: Path):
    preview_path = _write_preview(tmp_path / "validation_context_preview.json")
    output_path = tmp_path / "integration_summary_copy.json"
    script_path = ROOT / "scripts" / "run_integration_audit.py"

    completed = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--scene-family",
            "nominal",
            "--repair-preview-path",
            str(preview_path),
            "--reports-root",
            str(tmp_path),
            "--bundle-name",
            "integration_cli",
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["passed"] is True
    assert payload["scene_family"] == "nominal"
    assert Path(payload["integration_dir"]).exists()
    assert output_path.exists()

    namespace_contract = json.loads(Path(payload["namespace_contract_path"]).read_text(encoding="utf-8"))
    assert namespace_contract["report_namespaces"][INTEGRATION_AUDIT_MODE] == "analysis/integration"
