import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analyzers.semantic_claims import (
    SemanticClaim,
    SemanticClaimSet,
    normalize_claim_type,
)
from analyzers.semantic_inputs import (
    build_semantic_analysis_input,
    load_dynamic_bundle,
    load_static_bundle,
)
from analyzers.spec_ir import load_spec_ir


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
            "passed": True,
            "max_severity": "warning",
            "num_findings": 1,
            "findings": [
                {
                    "finding_id": "static:1",
                    "check_id": "check_reward_proxy_suspicion",
                    "severity": "warning",
                    "summary": "Clearance shaping may behave like a proxy reward.",
                    "passed": False,
                    "details": {},
                    "affected_paths": ["reward.components.safety_static"],
                    "recommended_action": "Review safety shaping intent.",
                }
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
            "passed": True,
            "max_severity": "warning",
            "num_findings": 1,
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
                    "score": 0.25,
                    "summary": "Shifted family shows measurable degradation.",
                    "metrics": [],
                    "details": {
                        "primary_run_ids": ["nominal_run_001"],
                        "comparison_run_ids": ["shifted_run_001"],
                    },
                }
            ],
            "findings": [
                {
                    "finding_id": "dynamic:1",
                    "witness_id": "W_ER",
                    "severity": "warning",
                    "summary": "Shifted degradation detected.",
                    "score": 0.25,
                    "details": {},
                    "evidence_refs": ["nominal_run_001", "shifted_run_001"],
                }
            ],
            "group_summaries": {
                "primary": {"by_source": {"eval": {"run_count": 1}}},
                "comparison": {"by_source": {"eval": {"run_count": 1}}},
            },
            "failure_summaries": {},
            "static_context": {"bundle_name": "static_fixture"},
            "evidence_objects": [
                {
                    "evidence_id": "failure:comparison:scenario_type:shifted",
                    "evidence_type": "failure_hotspot",
                    "scope": "comparison",
                    "title": "comparison failure hotspot",
                    "summary": "Shifted hotspot",
                    "severity": "warning",
                    "score": 0.4,
                    "witness_id": "",
                    "grouping_key": "scenario_type",
                    "group_name": "shifted",
                    "sources": ["eval"],
                    "scenario_types": ["shifted"],
                    "scene_cfg_names": ["scene_cfg_shifted.yaml"],
                    "evidence_refs": ["shifted_run_001"],
                    "semantic_tags": ["failure_hotspot"],
                    "metrics": {"failure_pressure": 0.4},
                    "payload": {},
                }
            ],
            "semantic_inputs": {
                "semantic_input_type": "dynamic_semantic_input.v1",
                "semantic_contract_type": "phase6_dynamic_semantic_contract.v1",
                "report_summary": {"passed": True, "max_severity": "warning", "num_findings": 2},
                "declared_families": ["nominal", "shifted"],
                "constraint_ids": ["collision_avoidance"],
                "reward_components": ["progress", "safety_static"],
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
            "reward_components": ["progress", "safety_static"],
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
            "max_severity": "warning",
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


def test_semantic_claim_normalization_and_roundtrip():
    claim = SemanticClaim(
        claim_id="claim-1",
        claim_type="cr",
        confidence=1.2,
        severity="HIGH",
        summary="Reward encourages boundary seeking.",
        status="SUPPORTED",
        supporting_evidence_ids=["ev-1", "ev-1", ""],
        affected_families=["shifted", "shifted"],
    )
    assert claim.claim_type == "C-R"
    assert claim.status == "supported"
    assert claim.severity == "high"
    assert claim.confidence == 1.0
    assert claim.supporting_evidence_ids == ["ev-1"]
    assert claim.affected_families == ["shifted"]

    payload = claim.to_dict()
    reconstructed = SemanticClaim.from_dict(payload)
    assert reconstructed.to_dict() == payload


def test_semantic_claim_set_roundtrip():
    payload = {
        "claim_set_type": "semantic_claim_set.v1",
        "supported_claims": [
            {
                "claim_id": "claim-1",
                "claim_type": "E-R",
                "confidence": 0.7,
                "severity": "warning",
                "summary": "Shifted degradation is consistent with environment-reward mismatch.",
            }
        ],
        "weak_claims": [],
        "rejected_claims": [],
        "cross_checks": [
            {
                "claim_id": "claim-1",
                "passed": True,
                "support_status": "supported",
                "messages": ["Claim is supported by W_ER evidence."],
                "matched_evidence_ids": ["evidence:1"],
                "matched_witness_ids": ["W_ER"],
            }
        ],
        "metadata": {"provider_mode": "mock"},
    }
    claim_set = SemanticClaimSet.from_dict(payload)
    assert claim_set.supported_claims[0].claim_type == "E-R"
    assert claim_set.cross_checks[0].support_status == "supported"
    assert claim_set.to_dict()["metadata"]["provider_mode"] == "mock"


def test_semantic_input_builder_reuses_dynamic_semantic_handoff(tmp_path):
    static_dir = _make_static_bundle(tmp_path)
    dynamic_dir = _make_dynamic_bundle(tmp_path)
    spec_ir = load_spec_ir()

    static_bundle = load_static_bundle(static_dir)
    dynamic_bundle = load_dynamic_bundle(dynamic_dir)
    semantic_input = build_semantic_analysis_input(
        spec_ir=spec_ir,
        static_bundle=static_bundle,
        dynamic_bundle=dynamic_bundle,
    )

    payload = semantic_input.to_dict()
    assert payload["input_type"] == "semantic_analysis_input.v1"
    assert payload["spec_version"] == "v0"
    assert "collision_avoidance" in payload["spec_summary"]["constraint_ids"]
    assert payload["dynamic_context"]["bundle_name"] == "dynamic_fixture"
    assert payload["static_context"]["bundle_name"] == "static_fixture"
    assert payload["cross_validation_requirements"]["semantic_contract_type"] == "phase6_dynamic_semantic_contract.v1"
    assert payload["cross_validation_requirements"]["cross_validation_contract"]["contract_type"] == "phase6_cross_validation_contract.v1"
    assert payload["evidence_context"]["dynamic_bundle_refs"]["primary_run_ids"] == ["nominal_run_001"]
    assert payload["prompt_sections"]["semantic_handoff"]["semantic_contract_type"] == "phase6_dynamic_semantic_contract.v1"


def test_normalize_claim_type_aliases():
    assert normalize_claim_type("cr") == "C-R"
    assert normalize_claim_type("e_c") == "E-C"
    assert normalize_claim_type("er") == "E-R"
    assert normalize_claim_type("mystery") == "unknown"
