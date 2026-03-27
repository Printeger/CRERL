import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analyzers.report_contract import RELEASE_PACKAGING_MODE
from pipeline.benchmark_suite import run_benchmark_suite_bundle
from pipeline.release_bundle import build_release_bundle_audit, run_release_packaging_bundle


def _write_fake_integration_bundle(root: Path, bundle_name: str = "integration_fixture") -> Path:
    bundle_dir = root / "analysis" / "integration" / bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "manifest.json").write_text(
        json.dumps({"bundle_type": "phase10_integration_bundle.v1"}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (bundle_dir / "integration_acceptance.json").write_text(
        json.dumps(
            {
                "acceptance_type": "phase10_integration_acceptance.v1",
                "passed": True,
                "comparison_ready_modes": ["baseline", "eval", "train"],
                "native_ready_modes": ["baseline", "eval", "train"],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (bundle_dir / "native_execution_consumer.json").write_text(
        json.dumps(
            {
                "consumer_type": "phase10_native_execution_consumer.v1",
                "consumer_contract": "phase10_post_repair_evidence_consumer.v2",
                "comparison_proven_modes": ["baseline", "eval", "train"],
                "native_ready_modes": ["baseline", "eval", "train"],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return bundle_dir


def test_build_release_bundle_audit_reads_benchmark_bundle(tmp_path: Path):
    _, benchmark_paths = run_benchmark_suite_bundle(
        reports_root=tmp_path,
        bundle_name="benchmark_fixture",
    )

    audit = build_release_bundle_audit(
        benchmark_bundle_dir=benchmark_paths["benchmark_dir"],
    )

    assert audit.suite_name == "cre_v1_minimal_benchmark"
    assert audit.suite_version == "v1"
    assert audit.release_summary["demo_case_count"] == 4
    assert audit.release_summary["release_ready_case_count"] == 4
    assert audit.release_summary["api_key_required_by_default"] is False
    assert audit.release_summary["phase11_exit_ready"] is False
    assert len(audit.demo_matrix["rows"]) == 4
    assert all(row["release_demo_ready"] for row in audit.demo_matrix["rows"])
    assert audit.demo_consumer["consumer_type"] == "phase11_clean_vs_injected_demo_consumer.v1"
    assert len(audit.demo_consumer["demo_pairs"]) == 3
    assert audit.release_acceptance["acceptance_type"] == "phase11_release_acceptance.v1"


def test_run_release_packaging_bundle_writes_namespaced_bundle(tmp_path: Path):
    _, bundle_paths = run_release_packaging_bundle(
        reports_root=tmp_path,
        bundle_name="release_fixture",
    )

    assert bundle_paths["release_dir"].exists()
    assert bundle_paths["release_plan_path"].exists()
    assert bundle_paths["release_artifacts_path"].exists()
    assert bundle_paths["demo_matrix_path"].exists()
    assert bundle_paths["demo_consumer_path"].exists()
    assert bundle_paths["release_acceptance_path"].exists()
    assert bundle_paths["release_summary_path"].exists()
    assert bundle_paths["release_summary_md_path"].exists()
    assert bundle_paths["namespace_manifest_path"].exists()
    assert bundle_paths["namespace_contract_path"].exists()

    summary = json.loads(bundle_paths["release_summary_path"].read_text(encoding="utf-8"))
    assert summary["demo_case_count"] == 4
    assert summary["release_ready_case_count"] == 4
    assert summary["api_key_required_by_default"] is False
    assert summary["phase11_exit_ready"] is False

    demo_matrix = json.loads(bundle_paths["demo_matrix_path"].read_text(encoding="utf-8"))
    assert len(demo_matrix["rows"]) == 4
    assert all(row["native_phase10_ready"] for row in demo_matrix["rows"])

    demo_consumer = json.loads(bundle_paths["demo_consumer_path"].read_text(encoding="utf-8"))
    assert demo_consumer["clean_case_id"] == "clean_nominal_v1"
    assert len(demo_consumer["demo_pairs"]) == 3

    acceptance = json.loads(bundle_paths["release_acceptance_path"].read_text(encoding="utf-8"))
    assert acceptance["phase11_exit_ready"] is False

    summary_md = bundle_paths["release_summary_md_path"].read_text(encoding="utf-8")
    assert "## Demo Matrix" in summary_md
    assert "## Clean-vs-Injected Demo Consumer" in summary_md
    assert "## Phase 11 Close-Out" in summary_md
    assert "clean_nominal_v1" in summary_md


def test_run_release_packaging_cli_smoke(tmp_path: Path):
    output_path = tmp_path / "release_summary_copy.json"
    script_path = ROOT / "scripts" / "run_release_packaging.py"

    completed = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--reports-root",
            str(tmp_path),
            "--bundle-name",
            "release_cli",
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["suite_name"] == "cre_v1_minimal_benchmark"
    assert payload["demo_case_count"] == 4
    assert payload["release_ready_case_count"] == 4
    assert payload["phase11_exit_ready"] is False
    assert payload["api_key_required_by_default"] is False
    assert Path(payload["release_dir"]).exists()
    assert output_path.exists()

    namespace_contract = json.loads(Path(payload["namespace_contract_path"]).read_text(encoding="utf-8"))
    assert namespace_contract["report_namespaces"][RELEASE_PACKAGING_MODE] == "analysis/release"


def test_release_bundle_phase11_closeout_passes_with_integration_proof(tmp_path: Path):
    _, benchmark_paths = run_benchmark_suite_bundle(
        reports_root=tmp_path,
        bundle_name="benchmark_fixture",
    )
    integration_dir = _write_fake_integration_bundle(tmp_path)

    audit, bundle_paths = run_release_packaging_bundle(
        benchmark_bundle_dir=benchmark_paths["benchmark_dir"],
        reports_root=tmp_path,
        bundle_name="release_closeout",
        integration_bundle_dirs=[integration_dir],
    )

    assert audit.release_summary["phase11_exit_ready"] is True
    assert audit.release_summary["integration_proof_available"] is True
    assert audit.release_acceptance["passed"] is True

    acceptance = json.loads(bundle_paths["release_acceptance_path"].read_text(encoding="utf-8"))
    assert acceptance["phase11_exit_ready"] is True
