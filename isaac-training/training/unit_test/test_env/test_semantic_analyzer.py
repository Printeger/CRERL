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
from analyzers.semantic_analyzer import (
    SEMANTIC_ANALYSIS_NAMESPACE,
    build_semantic_summary_markdown,
    run_semantic_analysis,
    run_semantic_analysis_with_provider_mode,
    run_semantic_analysis_bundle,
)
from analyzers.semantic_merge import (
    build_phase7_claim_consumer,
    build_semantic_report_merge_input,
)
from analyzers.semantic_crosscheck import validate_semantic_claims
from analyzers.semantic_inputs import (
    build_semantic_analysis_input,
    load_dynamic_bundle,
    load_static_bundle,
)
from analyzers.semantic_provider import MockSemanticProvider
from analyzers.semantic_provider import (
    AzureGatewaySemanticProvider,
    build_provider_messages,
    build_semantic_provider,
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


def test_mock_provider_generates_grounded_er_claim(tmp_path):
    static_dir = _make_static_bundle(tmp_path)
    dynamic_dir = _make_dynamic_bundle(tmp_path)
    semantic_input = build_semantic_analysis_input(
        static_bundle_dir=static_dir,
        dynamic_bundle_dir=dynamic_dir,
    )

    provider = MockSemanticProvider()
    claims = provider.generate_claims(semantic_input)

    assert claims
    first = claims[0]
    assert first.claim_type == "E-R"
    assert first.supporting_witness_ids == ["W_ER"]
    assert first.supporting_evidence_ids
    assert first.affected_families == ["shifted"]
    assert first.repair_direction_hint == "review shifted-family robustness and environment-reward alignment"


def test_semantic_crosscheck_supports_grounded_mock_claim(tmp_path):
    static_dir = _make_static_bundle(tmp_path)
    dynamic_dir = _make_dynamic_bundle(tmp_path)
    semantic_input = build_semantic_analysis_input(
        static_bundle_dir=static_dir,
        dynamic_bundle_dir=dynamic_dir,
    )

    provider = MockSemanticProvider()
    claim_set = validate_semantic_claims(
        provider.generate_claims(semantic_input),
        semantic_input=semantic_input,
    )

    assert len(claim_set.supported_claims) == 1
    assert claim_set.supported_claims[0].claim_type == "E-R"
    assert claim_set.cross_checks[0].passed is True
    assert claim_set.cross_checks[0].support_status == "supported"


def test_semantic_crosscheck_rejects_unsupported_overclaim(tmp_path):
    static_dir = _make_static_bundle(tmp_path)
    dynamic_dir = _make_dynamic_bundle(tmp_path)
    semantic_input = build_semantic_analysis_input(
        static_bundle_dir=static_dir,
        dynamic_bundle_dir=dynamic_dir,
    )

    overclaim = SemanticClaim(
        claim_id="claim-over",
        claim_type="C-R",
        confidence=0.9,
        severity="high",
        summary="Unsupported C-R overclaim.",
        supporting_evidence_ids=["missing-evidence"],
        supporting_witness_ids=["W_CR"],
        affected_families=["shifted"],
    )

    claim_set = validate_semantic_claims([overclaim], semantic_input=semantic_input)

    assert not claim_set.supported_claims
    assert len(claim_set.rejected_claims) == 1
    assert claim_set.rejected_claims[0].claim_type == "C-R"
    assert claim_set.cross_checks[0].passed is False
    assert claim_set.cross_checks[0].support_status == "rejected"


def test_run_semantic_analysis_builds_supported_er_report(tmp_path):
    static_dir = _make_static_bundle(tmp_path)
    dynamic_dir = _make_dynamic_bundle(tmp_path)

    report = run_semantic_analysis(
        static_bundle_dir=static_dir,
        dynamic_bundle_dir=dynamic_dir,
    )

    assert report.report_type == "semantic_analyzer_report.v1"
    assert report.spec_version == "v0"
    assert report.static_bundle_name == "static_fixture"
    assert report.dynamic_bundle_name == "dynamic_fixture"
    assert report.passed is True
    assert report.supported_claims
    assert report.supported_claims[0]["claim_type"] == "E-R"
    assert report.semantic_input["input_type"] == "semantic_analysis_input.v1"
    assert report.metadata["provider_mode"] == "mock"


def test_write_semantic_bundle_outputs_namespaced_artifacts(tmp_path):
    static_dir = _make_static_bundle(tmp_path)
    dynamic_dir = _make_dynamic_bundle(tmp_path)
    reports_root = tmp_path / "reports"

    report, bundle_paths = run_semantic_analysis_bundle(
        static_bundle_dir=static_dir,
        dynamic_bundle_dir=dynamic_dir,
        reports_root=reports_root,
        bundle_name="semantic_fixture",
    )

    report_dir = reports_root / "analysis" / "semantic" / "semantic_fixture"
    assert bundle_paths["report_dir"] == report_dir
    assert report_dir.exists()
    assert (report_dir / "semantic_report.json").exists()
    assert (report_dir / "semantic_claims.json").exists()
    assert (report_dir / "semantic_input.json").exists()
    assert (report_dir / "semantic_summary.md").exists()
    assert (report_dir / "summary.json").exists()
    assert (report_dir / "manifest.json").exists()
    assert (reports_root / "analysis" / "semantic" / "namespace_manifest.json").exists()
    assert (reports_root / "analysis" / "report_namespace_contract.json").exists()

    manifest = json.loads((report_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["namespace"] == SEMANTIC_ANALYSIS_NAMESPACE
    assert manifest["bundle_type"] == "semantic_analysis_bundle.v1"

    summary = json.loads((report_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["supported_claims"] >= 1
    assert summary["rejected_claims"] == len(report.rejected_claims)

    markdown = (report_dir / "semantic_summary.md").read_text(encoding="utf-8")
    assert "# Semantic Diagnosis Summary" in markdown
    assert "`E-R`" in markdown


def test_semantic_summary_markdown_contains_top_claim(tmp_path):
    static_dir = _make_static_bundle(tmp_path)
    dynamic_dir = _make_dynamic_bundle(tmp_path)
    report = run_semantic_analysis(
        static_bundle_dir=static_dir,
        dynamic_bundle_dir=dynamic_dir,
    )

    markdown = build_semantic_summary_markdown(report)
    assert "## Top Diagnosis" in markdown
    assert report.human_summary["most_likely_claim_type"] in markdown


def test_semantic_merge_and_claim_consumer_are_phase7_ready(tmp_path):
    static_dir = _make_static_bundle(tmp_path)
    dynamic_dir = _make_dynamic_bundle(tmp_path)
    report, _ = run_semantic_analysis_bundle(
        static_bundle_dir=static_dir,
        dynamic_bundle_dir=dynamic_dir,
        reports_root=tmp_path / "reports",
        bundle_name="semantic_fixture",
    )

    consumer = build_phase7_claim_consumer(report.to_dict(), semantic_bundle_name="semantic_fixture")
    merge_input = build_semantic_report_merge_input(
        report.to_dict(),
        semantic_bundle_name="semantic_fixture",
        claim_consumer_bundle=consumer.to_dict(),
    )

    assert consumer.consumer_type == "phase7_claim_consumer.v1"
    assert consumer.primary_claim_type == "E-R"
    assert consumer.repair_ready_claims
    assert consumer.repair_ready_claims[0].supporting_evidence_ids
    assert merge_input.merge_input_type == "phase7_semantic_report_merge_input.v1"
    assert merge_input.consumer_contract["claim_consumer_type"] == "phase7_claim_consumer.v1"
    assert merge_input.top_claim["claim_type"] == "E-R"


def test_semantic_bundle_writes_merge_and_consumer_artifacts(tmp_path):
    static_dir = _make_static_bundle(tmp_path)
    dynamic_dir = _make_dynamic_bundle(tmp_path)
    report_dir = tmp_path / "reports" / "analysis" / "semantic" / "semantic_fixture"

    _, bundle_paths = run_semantic_analysis_bundle(
        static_bundle_dir=static_dir,
        dynamic_bundle_dir=dynamic_dir,
        report_dir=report_dir,
        bundle_name="semantic_fixture",
    )

    assert bundle_paths["semantic_merge_input_path"].exists()
    assert bundle_paths["claim_consumer_path"].exists()

    consumer_payload = json.loads(bundle_paths["claim_consumer_path"].read_text(encoding="utf-8"))
    merge_payload = json.loads(bundle_paths["semantic_merge_input_path"].read_text(encoding="utf-8"))
    assert consumer_payload["consumer_type"] == "phase7_claim_consumer.v1"
    assert merge_payload["merge_input_type"] == "phase7_semantic_report_merge_input.v1"


def test_build_provider_messages_is_evidence_first(tmp_path):
    static_dir = _make_static_bundle(tmp_path)
    dynamic_dir = _make_dynamic_bundle(tmp_path)
    semantic_input = build_semantic_analysis_input(
        static_bundle_dir=static_dir,
        dynamic_bundle_dir=dynamic_dir,
    )

    messages = build_provider_messages(semantic_input)
    assert len(messages) == 2
    assert "evidence-first" in messages[0]["content"]
    assert "cross_validation_requirements" in messages[1]["content"]


def test_build_semantic_provider_supports_mock_and_gateway_modes():
    mock_provider = build_semantic_provider("mock", config={"max_claims": 2})
    assert isinstance(mock_provider, MockSemanticProvider)
    assert mock_provider.max_claims == 2

    gateway_provider = build_semantic_provider(
        "azure_gateway",
        config={"deployment_name": "gpt4o", "api_key_env_var": "TEST_COMP_OPENAI_API_KEY"},
    )
    assert isinstance(gateway_provider, AzureGatewaySemanticProvider)
    assert gateway_provider.config.deployment_name == "gpt4o"
    assert gateway_provider.config.api_key_env_var == "TEST_COMP_OPENAI_API_KEY"


def test_gateway_provider_requires_api_key():
    provider = AzureGatewaySemanticProvider()
    provider.config.api_key = ""
    provider.config.api_key_env_var = "THIS_ENV_SHOULD_NOT_EXIST_FOR_TEST"
    try:
        provider._resolve_api_key()
    except RuntimeError as exc:
        assert "Missing API key" in str(exc)
    else:
        raise AssertionError("Expected provider to require an API key.")


def test_run_semantic_analysis_with_provider_mode_uses_mock_by_default(tmp_path):
    static_dir = _make_static_bundle(tmp_path)
    dynamic_dir = _make_dynamic_bundle(tmp_path)

    report = run_semantic_analysis_with_provider_mode(
        static_bundle_dir=static_dir,
        dynamic_bundle_dir=dynamic_dir,
        provider_mode="mock",
        provider_config={"max_claims": 2},
    )

    assert report.metadata["provider_mode"] == "mock"
    assert report.supported_claims
