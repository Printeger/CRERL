import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from repair.acceptance import accept_repair
from repair.patch_executor import run_repair_bundle_write
from repair.repair_validator import build_phase9_validation_request, validate_repair
from repair.rule_based_repair import propose_rule_based_repairs


REPO_ROOT = Path(__file__).resolve().parents[4]
REWARD_SPEC = REPO_ROOT / "isaac-training" / "training" / "cfg" / "spec_cfg" / "reward_spec_v0.yaml"
BOUNDARY_CFG = REPO_ROOT / "isaac-training" / "training" / "cfg" / "env_cfg" / "scene_cfg_boundary_critical.yaml"
SHIFTED_CFG = REPO_ROOT / "isaac-training" / "training" / "cfg" / "env_cfg" / "scene_cfg_shifted.yaml"


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


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
        "selection_basis": "phase7_test_fixture",
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
            "metadata": {
                "bundle_name": bundle.name,
            },
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
                    "selection_basis": "phase7_test_fixture",
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
            "metadata": {
                "bundle_name": bundle.name,
            },
        },
    )
    return bundle


def test_rule_based_repair_generates_cr_candidate_from_report_bundle(tmp_path):
    bundle = _make_report_bundle(
        tmp_path,
        claim_type="C-R",
        summary="Reward progress proxy dominates safety shaping near boundary states.",
        target_ref=REWARD_SPEC,
    )
    plan = propose_rule_based_repairs(report_bundle_dir=bundle)

    assert plan.plan_type == "phase8_repair_plan.v1"
    assert plan.primary_claim_type == "C-R"
    assert plan.selected_candidate_id
    assert plan.selected_patch is not None
    assert plan.candidates
    assert plan.candidates[0].operator_type == "reduce_progress_proxy_weight"
    assert plan.candidates[0].target_file.endswith("reward_spec_v0.yaml")
    assert plan.selected_patch.operations[0].before == 1.0
    assert plan.selected_patch.operations[0].after == 0.8


def test_rule_based_repair_generates_ec_candidate_from_report_bundle(tmp_path):
    bundle = _make_report_bundle(
        tmp_path,
        claim_type="E-C",
        summary="Boundary-critical family undercovers critical states near the route corridor.",
        target_ref=BOUNDARY_CFG,
    )
    plan = propose_rule_based_repairs(report_bundle_dir=bundle)

    assert plan.primary_claim_type == "E-C"
    assert plan.candidates[0].operator_type == "increase_critical_route_bias"
    assert plan.candidates[0].target_file.endswith("scene_cfg_boundary_critical.yaml")
    assert plan.selected_patch is not None
    assert plan.selected_patch.operations[0].after > plan.selected_patch.operations[0].before


def test_rule_based_repair_generates_er_candidate_from_report_bundle(tmp_path):
    bundle = _make_report_bundle(
        tmp_path,
        claim_type="E-R",
        summary="Shifted-family robustness is too weak under distribution shift.",
        target_ref=SHIFTED_CFG,
    )
    plan = propose_rule_based_repairs(report_bundle_dir=bundle)

    assert plan.primary_claim_type == "E-R"
    assert plan.candidates[0].operator_type == "increase_shifted_boundary_bias"
    assert plan.candidates[0].target_file.endswith("scene_cfg_shifted.yaml")
    assert plan.selected_patch is not None
    assert plan.selected_patch.operations[0].target_path == "distribution_modes.boundary_adjacent_bias"


def test_rule_based_repair_generation_is_deterministic(tmp_path):
    bundle = _make_report_bundle(
        tmp_path,
        claim_type="C-R",
        summary="Reward progress proxy dominates safety shaping near boundary states.",
        target_ref=REWARD_SPEC,
    )
    first = propose_rule_based_repairs(report_bundle_dir=bundle).to_dict()
    second = propose_rule_based_repairs(report_bundle_dir=bundle).to_dict()

    assert first == second


def test_rule_based_repair_can_override_primary_claim_type(tmp_path):
    bundle = _make_report_bundle(
        tmp_path,
        claim_type="C-R",
        summary="Reward progress proxy dominates safety shaping near boundary states.",
        target_ref=REWARD_SPEC,
    )
    handoff_path = bundle / "repair_handoff.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    handoff["selected_claims"].append(
        {
            "handoff_id": "repair_handoff:E-R:secondary",
            "claim_type": "E-R",
            "selected_from": "analysis/semantic",
            "selected_from_rank": 2,
            "severity": "high",
            "confidence": 0.9,
            "support_status": "semantic_supported",
            "summary": "Shifted-family robustness is too weak under distribution shift.",
            "impacted_components": ["E", "R"],
            "suggested_repair_direction": "mixed",
            "required_evidence_refs": [str(SHIFTED_CFG)],
            "source_record_ids": ["source:E-R:secondary"],
            "selection_basis": "phase7_test_fixture",
        }
    )
    handoff["repair_order"].append(
        {
            "order": 2,
            "handoff_id": "repair_handoff:E-R:secondary",
            "claim_type": "E-R",
            "selected_from": "analysis/semantic",
            "suggested_repair_direction": "mixed",
            "selection_basis": "phase7_test_fixture",
        }
    )
    handoff["selection_summary"]["selection_focus_order"].append("E-R")
    handoff_path.write_text(json.dumps(handoff, indent=2, sort_keys=True), encoding="utf-8")

    plan = propose_rule_based_repairs(
        report_bundle_dir=bundle,
        primary_claim_type_override="E-R",
    )

    assert plan.primary_claim_type == "E-R"
    assert plan.candidates[0].claim_type == "E-R"
    assert plan.candidates[0].operator_type == "increase_shifted_boundary_bias"
    assert plan.metadata["primary_claim_type_override"] == "E-R"


def test_repair_acceptance_and_bundle_writer(tmp_path):
    bundle = _make_report_bundle(
        tmp_path,
        claim_type="C-R",
        summary="Reward progress proxy dominates safety shaping near boundary states.",
        target_ref=REWARD_SPEC,
    )
    plan = propose_rule_based_repairs(report_bundle_dir=bundle)
    acceptance = accept_repair(plan.to_dict())
    repair_validation = validate_repair(plan.to_dict(), acceptance=acceptance)
    validation_request = build_phase9_validation_request(
        plan.to_dict(),
        repair_validation=repair_validation,
        acceptance=acceptance,
        bundle_name="repair_fixture",
    )
    bundle_paths = run_repair_bundle_write(
        plan,
        acceptance,
        repair_validation=repair_validation,
        validation_request=validation_request,
        reports_root=tmp_path,
        bundle_name="repair_fixture",
    )

    assert acceptance["passed"] is True
    assert repair_validation["passed"] is True
    assert repair_validation["phase9_ready"] is True
    assert bundle_paths["repair_plan_path"].exists()
    assert bundle_paths["repair_candidates_path"].exists()
    assert bundle_paths["spec_patch_path"].exists()
    assert bundle_paths["spec_patch_preview_path"].exists()
    assert bundle_paths["repair_summary_path"].exists()
    assert bundle_paths["repair_summary_md_path"].exists()
    assert bundle_paths["acceptance_path"].exists()
    assert bundle_paths["repair_validation_path"].exists()
    assert bundle_paths["validation_request_path"].exists()
    assert bundle_paths["namespace_contract_path"].exists()

    summary_payload = json.loads(bundle_paths["repair_summary_path"].read_text(encoding="utf-8"))
    assert summary_payload["bundle_type"] == "repair_generation_bundle.v1"
    assert summary_payload["primary_claim_type"] == "C-R"
    validation_payload = json.loads(bundle_paths["repair_validation_path"].read_text(encoding="utf-8"))
    assert validation_payload["validation_type"] == "phase8_repair_validator.v1"
    request_payload = json.loads(bundle_paths["validation_request_path"].read_text(encoding="utf-8"))
    assert request_payload["request_type"] == "phase9_validation_request.v1"
    assert request_payload["phase9_ready"] is True


def test_repair_validator_builds_phase9_request(tmp_path):
    bundle = _make_report_bundle(
        tmp_path,
        claim_type="E-C",
        summary="Boundary-critical family undercovers critical states near the route corridor.",
        target_ref=BOUNDARY_CFG,
    )
    plan = propose_rule_based_repairs(report_bundle_dir=bundle)
    acceptance = accept_repair(plan.to_dict())
    repair_validation = validate_repair(plan.to_dict(), acceptance=acceptance)
    request = build_phase9_validation_request(
        plan.to_dict(),
        repair_validation=repair_validation,
        acceptance=acceptance,
        bundle_name="repair_validation_fixture",
    )

    assert repair_validation["passed"] is True
    assert repair_validation["phase9_ready"] is True
    assert request["request_type"] == "phase9_validation_request.v1"
    assert request["repair_bundle_name"] == "repair_validation_fixture"
    assert request["primary_claim_type"] == "E-C"
    assert request["phase9_ready"] is True
    assert "W_EC" in request["validation_targets"]
    assert request["selected_target_files"]
    assert request["selected_target_paths"]


def test_run_repair_audit_cli_smoke(tmp_path):
    bundle = _make_report_bundle(
        tmp_path,
        claim_type="E-R",
        summary="Shifted-family robustness is too weak under distribution shift.",
        target_ref=SHIFTED_CFG,
    )
    output_path = tmp_path / "repair_plan_copy.json"
    script_path = ROOT / "scripts" / "run_repair_audit.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--report-bundle-dir",
            str(bundle),
            "--reports-root",
            str(tmp_path),
            "--bundle-name",
            "repair_cli_fixture",
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["passed"] is True
    assert payload["phase9_ready"] is True
    assert payload["primary_claim_type"] == "E-R"
    assert payload["candidate_count"] >= 1
    assert Path(payload["repair_plan_path"]).exists()
    assert Path(payload["spec_patch_preview_path"]).exists()
    assert Path(payload["acceptance_path"]).exists()
    assert Path(payload["repair_validation_path"]).exists()
    assert Path(payload["validation_request_path"]).exists()
    assert output_path.exists()
