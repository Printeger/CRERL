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
