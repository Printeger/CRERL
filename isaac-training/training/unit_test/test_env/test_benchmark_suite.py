import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analyzers.report_contract import BENCHMARK_SUITE_MODE
from pipeline.benchmark_suite import build_benchmark_suite_audit, run_benchmark_suite_bundle


def test_build_benchmark_suite_audit_loads_real_cases():
    audit = build_benchmark_suite_audit()

    assert audit.suite_name == "cre_v1_minimal_benchmark"
    assert audit.suite_version == "v1"
    assert audit.benchmark_summary["case_count"] == 4
    assert audit.benchmark_summary["clean_case_count"] == 1
    assert audit.benchmark_summary["injected_case_count"] == 3
    assert audit.benchmark_summary["ready_case_count"] == 4

    case_ids = {case["case_id"] for case in audit.benchmark_cases["cases"]}
    assert case_ids == {
        "clean_nominal_v1",
        "injected_cr_v1",
        "injected_ec_v1",
        "injected_er_v1",
    }

    claim_types = {
        case["case_id"]: case["expected_primary_claim_type"]
        for case in audit.benchmark_cases["cases"]
    }
    assert claim_types["clean_nominal_v1"] == ""
    assert claim_types["injected_cr_v1"] == "C-R"
    assert claim_types["injected_ec_v1"] == "E-C"
    assert claim_types["injected_er_v1"] == "E-R"


def test_run_benchmark_suite_bundle_writes_namespaced_bundle(tmp_path: Path):
    audit, bundle_paths = run_benchmark_suite_bundle(
        reports_root=tmp_path,
        bundle_name="benchmark_fixture",
    )

    assert audit.benchmark_summary["case_count"] == 4
    assert bundle_paths["benchmark_dir"].exists()
    assert bundle_paths["benchmark_manifest_path"].exists()
    assert bundle_paths["benchmark_cases_path"].exists()
    assert bundle_paths["benchmark_matrix_path"].exists()
    assert bundle_paths["benchmark_summary_path"].exists()
    assert bundle_paths["benchmark_summary_md_path"].exists()
    assert bundle_paths["namespace_manifest_path"].exists()
    assert bundle_paths["namespace_contract_path"].exists()

    summary = json.loads(bundle_paths["benchmark_summary_path"].read_text(encoding="utf-8"))
    assert summary["ready_case_count"] == 4
    assert summary["phase10_native_ready_case_count"] == 4

    matrix = json.loads(bundle_paths["benchmark_matrix_path"].read_text(encoding="utf-8"))
    assert len(matrix["rows"]) == 4
    assert len(matrix["execution_rows"]) == 12
    assert len(matrix["comparison_rows"]) == 8
    assert all(row["case_ready"] for row in matrix["rows"])
    assert all(row["replay_ready"] for row in matrix["execution_rows"])
    assert all(row["entrypoint"] for row in matrix["execution_rows"])

    summary_md = bundle_paths["benchmark_summary_md_path"].read_text(encoding="utf-8")
    assert "## Replay Matrix" in summary_md
    assert "clean_nominal_v1::baseline" in summary_md


def test_run_benchmark_suite_cli_smoke(tmp_path: Path):
    output_path = tmp_path / "benchmark_summary_copy.json"
    script_path = ROOT / "scripts" / "run_benchmark_suite.py"

    completed = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--reports-root",
            str(tmp_path),
            "--bundle-name",
            "benchmark_cli",
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["suite_name"] == "cre_v1_minimal_benchmark"
    assert payload["case_count"] == 4
    assert payload["ready_case_count"] == 4
    assert payload["phase10_native_ready_case_count"] == 4
    assert Path(payload["benchmark_dir"]).exists()
    assert output_path.exists()

    namespace_contract = json.loads(Path(payload["namespace_contract_path"]).read_text(encoding="utf-8"))
    assert namespace_contract["report_namespaces"][BENCHMARK_SUITE_MODE] == "analysis/benchmark"
