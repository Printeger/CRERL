import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analyzers.report_contract import REPORT_GENERATION_MODE
from analyzers.report_generator import run_report_generation, run_report_generation_bundle
from analyzers.semantic_analyzer import run_semantic_analysis_bundle

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "report_cases"


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _make_static_bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "analysis" / "static" / "static_fixture"
    _write_json(
        bundle / "static_report.json",
        {
            "report_type": "static_analyzer_report.v1",
            "spec_version": "v0",
            "passed": False,
            "max_severity": "high",
            "num_findings": 2,
            "findings": [
                {
                    "finding_id": "static:1",
                    "check_id": "reward_constraint_conflicts",
                    "severity": "high",
                    "summary": "Reward shaping under-supports the declared safety constraint.",
                    "passed": False,
                    "details": {},
                    "affected_paths": ["reward.components.reward_safety_static"],
                    "recommended_action": "Strengthen safety reward support.",
                },
                {
                    "finding_id": "static:2",
                    "check_id": "scene_family_coverage",
                    "severity": "warning",
                    "summary": "Critical scenario family coverage is weaker than declared.",
                    "passed": False,
                    "details": {},
                    "affected_paths": ["env_cfg/scene_cfg_boundary_critical.yaml"],
                    "recommended_action": "Increase critical-family coverage.",
                },
            ],
            "metadata": {},
            "scene_family_set": ["nominal", "shifted"],
        },
    )
    _write_json(
        bundle / "summary.json",
        {
            "report_type": "static_analyzer_report.v1",
            "spec_version": "v0",
            "passed": False,
            "max_severity": "high",
            "num_findings": 2,
            "scene_family_set": ["nominal", "shifted"],
        },
    )
    _write_json(
        bundle / "manifest.json",
        {
            "bundle_name": "static_fixture",
            "report_mode": "static_audit",
        },
    )
    return bundle


def _make_dynamic_bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "analysis" / "dynamic" / "dynamic_fixture"
    _write_json(
        bundle / "dynamic_report.json",
        {
            "report_type": "dynamic_analyzer_report.v1",
            "spec_version": "v0",
            "passed": True,
            "max_severity": "warning",
            "num_findings": 2,
            "primary_run_ids": ["nominal_run_001"],
            "comparison_run_ids": ["shifted_run_001"],
            "witnesses": [
                {
                    "witness_id": "W_ER",
                    "severity": "warning",
                    "score": 0.62,
                    "summary": "Shifted family shows measurable degradation.",
                    "metrics": [],
                    "details": {
                        "primary_run_ids": ["nominal_run_001"],
                        "comparison_run_ids": ["shifted_run_001"],
                    },
                },
                {
                    "witness_id": "W_CR",
                    "severity": "medium",
                    "score": 0.71,
                    "summary": "Policy earns reward near boundary states.",
                    "metrics": [],
                    "details": {
                        "primary_run_ids": ["nominal_run_001"],
                        "comparison_run_ids": ["shifted_run_001"],
                    },
                },
            ],
            "findings": [
                {
                    "finding_id": "dynamic:1",
                    "witness_id": "W_ER",
                    "severity": "warning",
                    "summary": "Shifted degradation detected.",
                    "score": 0.62,
                    "details": {},
                    "evidence_refs": ["nominal_run_001", "shifted_run_001"],
                },
                {
                    "finding_id": "dynamic:2",
                    "witness_id": "W_CR",
                    "severity": "medium",
                    "summary": "Reward-constraint coupling detected.",
                    "score": 0.71,
                    "details": {},
                    "evidence_refs": ["nominal_run_001"],
                },
            ],
            "group_summaries": {
                "by_source": {"eval": {"run_count": 1}},
                "by_scenario_type": {"shifted": {"run_count": 1}},
            },
            "failure_summaries": {
                "by_scenario_type": {"shifted": {"failure_pressure": 0.5}},
            },
            "static_context": {"bundle_name": "static_fixture"},
            "evidence_objects": [
                {
                    "evidence_id": "failure:comparison:scenario_type:shifted",
                    "evidence_type": "failure_hotspot",
                    "scope": "comparison",
                    "title": "comparison failure hotspot",
                    "summary": "Shifted hotspot",
                    "severity": "warning",
                    "score": 0.5,
                    "witness_id": "W_ER",
                    "grouping_key": "scenario_type",
                    "group_name": "shifted",
                    "sources": ["eval"],
                    "scenario_types": ["shifted"],
                    "scene_cfg_names": ["scene_cfg_shifted.yaml"],
                    "evidence_refs": ["shifted_run_001"],
                    "semantic_tags": ["failure_hotspot"],
                    "metrics": {"failure_pressure": 0.5},
                    "payload": {},
                }
            ],
            "semantic_inputs": {
                "semantic_input_type": "dynamic_semantic_input.v1",
                "semantic_contract_type": "phase6_dynamic_semantic_contract.v1",
                "report_summary": {"passed": True, "max_severity": "medium", "num_findings": 2},
                "declared_families": ["nominal", "shifted"],
                "constraint_ids": ["collision_avoidance"],
                "reward_components": ["reward_progress", "reward_safety_static"],
                "witness_overview": [],
                "attribution_candidates": [
                    {
                        "candidate_id": "failure:comparison:scenario_type:shifted",
                        "summary": "Shifted hotspot",
                    }
                ],
                "failure_hotspots": [
                    {
                        "evidence_id": "failure:comparison:scenario_type:shifted",
                        "summary": "Shifted hotspot",
                    }
                ],
                "prompt_sections": {"runtime_summary": {"primary_run_ids": ["nominal_run_001"]}},
                "cross_validation_contract": {
                    "contract_type": "phase6_cross_validation_contract.v1",
                    "required_supported_claim_types": ["C-R", "E-C", "E-R"],
                },
                "prompt_seeds": ["Which witness is strongest?"],
                "primary_run_ids": ["nominal_run_001"],
                "comparison_run_ids": ["shifted_run_001"],
                "spec_version": "v0",
                "static_context": {"bundle_name": "static_fixture"},
            },
            "metadata": {},
        },
    )
    _write_json(bundle / "dynamic_evidence.json", {"evidence_type": "dynamic_evidence_bundle.v1"})
    _write_json(
        bundle / "semantic_inputs.json",
        {
            "semantic_input_type": "dynamic_semantic_input.v1",
            "semantic_contract_type": "phase6_dynamic_semantic_contract.v1",
            "declared_families": ["nominal", "shifted"],
            "constraint_ids": ["collision_avoidance"],
            "reward_components": ["reward_progress", "reward_safety_static"],
            "witness_overview": [],
            "attribution_candidates": [{"candidate_id": "cand-1"}],
            "failure_hotspots": [{"evidence_id": "failure:comparison:scenario_type:shifted"}],
            "prompt_sections": {"runtime_summary": {"primary_run_ids": ["nominal_run_001"]}},
            "cross_validation_contract": {
                "contract_type": "phase6_cross_validation_contract.v1",
                "required_supported_claim_types": ["C-R", "E-C", "E-R"],
            },
            "prompt_seeds": ["Which witness is strongest?"],
            "primary_run_ids": ["nominal_run_001"],
            "comparison_run_ids": ["shifted_run_001"],
            "spec_version": "v0",
            "static_context": {"bundle_name": "static_fixture"},
        },
    )
    _write_json(
        bundle / "summary.json",
        {
            "report_type": "dynamic_analyzer_report.v1",
            "passed": True,
            "max_severity": "medium",
            "num_findings": 2,
        },
    )
    _write_json(
        bundle / "manifest.json",
        {
            "bundle_name": "dynamic_fixture",
            "report_mode": "dynamic_analysis",
        },
    )
    return bundle


def _make_semantic_bundle(tmp_path: Path, static_bundle: Path, dynamic_bundle: Path) -> Path:
    report_dir = tmp_path / "analysis" / "semantic" / "semantic_fixture"
    _, bundle_paths = run_semantic_analysis_bundle(
        static_bundle_dir=static_bundle,
        dynamic_bundle_dir=dynamic_bundle,
        reports_root=tmp_path,
        bundle_name="semantic_fixture",
        report_dir=report_dir,
    )
    return bundle_paths["report_dir"]


def _materialize_report_case(tmp_path: Path, fixture_name: str):
    payload = json.loads((FIXTURE_ROOT / fixture_name).read_text(encoding="utf-8"))
    static_bundle = tmp_path / "analysis" / "static" / payload["static"]["manifest.json"]["bundle_name"]
    dynamic_bundle = tmp_path / "analysis" / "dynamic" / payload["dynamic"]["manifest.json"]["bundle_name"]
    semantic_bundle = tmp_path / "analysis" / "semantic" / payload["semantic"]["manifest.json"]["bundle_name"]
    for relative_name, value in payload["static"].items():
        _write_json(static_bundle / relative_name, value)
    for relative_name, value in payload["dynamic"].items():
        _write_json(dynamic_bundle / relative_name, value)
    for relative_name, value in payload["semantic"].items():
        _write_json(semantic_bundle / relative_name, value)
    return static_bundle, dynamic_bundle, semantic_bundle


def test_run_report_generation_bundle_writes_namespaced_report(tmp_path):
    static_bundle = _make_static_bundle(tmp_path)
    dynamic_bundle = _make_dynamic_bundle(tmp_path)
    semantic_bundle = _make_semantic_bundle(tmp_path, static_bundle, dynamic_bundle)

    report, bundle_paths = run_report_generation_bundle(
        static_bundle_dir=static_bundle,
        dynamic_bundle_dir=dynamic_bundle,
        semantic_bundle_dir=semantic_bundle,
        reports_root=tmp_path,
        bundle_name="report_fixture",
    )

    assert report.report_type == "phase7_unified_report.v1"
    assert report.num_ranked_findings >= 4
    assert report.root_cause_summary["primary_claim_type"] in {"C-R", "E-C", "E-R"}
    assert bundle_paths["report_json_path"].exists()
    assert bundle_paths["ranked_findings_path"].exists()
    assert bundle_paths["repair_handoff_path"].exists()
    assert bundle_paths["report_summary_path"].exists()
    assert bundle_paths["namespace_contract_path"].exists()

    contract = json.loads(bundle_paths["namespace_contract_path"].read_text(encoding="utf-8"))
    assert contract["report_namespaces"][REPORT_GENERATION_MODE] == "analysis/report"


def test_run_report_generation_builds_repair_handoff(tmp_path):
    static_bundle = _make_static_bundle(tmp_path)
    dynamic_bundle = _make_dynamic_bundle(tmp_path)
    semantic_bundle = _make_semantic_bundle(tmp_path, static_bundle, dynamic_bundle)

    report = run_report_generation(
        static_bundle_dir=static_bundle,
        dynamic_bundle_dir=dynamic_bundle,
        semantic_bundle_dir=semantic_bundle,
    )

    assert report.repair_handoff
    assert report.repair_handoff["handoff_type"] == "phase8_repair_handoff.v1"
    assert report.repair_handoff["claim_record_schema"] == "phase7_repair_ready_claim.v1"
    assert report.repair_handoff["selection_policy"] == "phase7_ranked_claim_selection.v2"
    assert report.repair_handoff["selected_claims"]
    first = report.repair_handoff["selected_claims"][0]
    assert first["claim_type"] in {"C-R", "E-C", "E-R"}
    assert first["suggested_repair_direction"] in {"reward", "environment", "constraint", "mixed"}
    assert "required_evidence_refs" in first
    assert "selection_basis" in first


def test_report_generator_cli_smoke(tmp_path):
    static_bundle = _make_static_bundle(tmp_path)
    dynamic_bundle = _make_dynamic_bundle(tmp_path)
    semantic_bundle = _make_semantic_bundle(tmp_path, static_bundle, dynamic_bundle)
    output_path = tmp_path / "report_copy.json"
    script_path = ROOT / "scripts" / "run_report_audit.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--static-bundle-dir",
            str(static_bundle),
            "--dynamic-bundle-dir",
            str(dynamic_bundle),
            "--semantic-bundle-dir",
            str(semantic_bundle),
            "--reports-root",
            str(tmp_path),
            "--bundle-name",
            "report_cli_fixture",
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["passed"] in {True, False}
    assert payload["report_dir"].endswith("report_cli_fixture")
    assert Path(payload["report_json_path"]).exists()
    assert Path(payload["ranked_findings_path"]).exists()
    assert Path(payload["repair_handoff_path"]).exists()
    assert output_path.exists()


def test_root_cause_prefers_static_blocker_over_conflicting_semantic_claim(tmp_path):
    static_bundle, dynamic_bundle, semantic_bundle = _materialize_report_case(
        tmp_path,
        "static_semantic_conflict_case.json",
    )
    report = run_report_generation(
        static_bundle_dir=static_bundle,
        dynamic_bundle_dir=dynamic_bundle,
        semantic_bundle_dir=semantic_bundle,
    )

    assert report.root_cause_summary["primary_claim_type"] == "C-R"
    conflict_kinds = {item["kind"] for item in report.root_cause_summary["conflicts"]}
    assert "static_semantic_claim_type_conflict" in conflict_kinds
    assert report.repair_handoff["primary_repair_direction"] == "reward"


def test_root_cause_can_prefer_supported_semantic_claim_over_static_warning(tmp_path):
    static_bundle, dynamic_bundle, semantic_bundle = _materialize_report_case(
        tmp_path,
        "semantic_supported_over_static_warning_case.json",
    )
    report = run_report_generation(
        static_bundle_dir=static_bundle,
        dynamic_bundle_dir=dynamic_bundle,
        semantic_bundle_dir=semantic_bundle,
    )

    assert report.root_cause_summary["primary_claim_type"] == "E-R"
    assert report.repair_handoff["primary_repair_direction"] == "mixed"
    assert report.repair_handoff["selected_claims"][0]["claim_type"] == "E-R"
