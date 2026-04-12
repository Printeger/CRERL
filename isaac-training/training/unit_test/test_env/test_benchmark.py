import json
import sys
from pathlib import Path

import pytest

ISAAC_TRAINING_ROOT = Path(__file__).resolve().parents[3]
TRAINING_ROOT = ISAAC_TRAINING_ROOT / "training"
if str(TRAINING_ROOT) not in sys.path:
    sys.path.insert(0, str(TRAINING_ROOT))

from scripts.run_benchmark import run_benchmark


BENCHMARK_DIR = TRAINING_ROOT / "cfg" / "benchmark_cfg"
EXPECTED_CASES = {"clean_nominal", "injected_cr", "injected_ec", "injected_er"}


@pytest.fixture(scope="module")
def benchmark_results():
    return run_benchmark(str(BENCHMARK_DIR))


def test_clean_nominal_no_alarm(benchmark_results):
    assert benchmark_results["clean_nominal"]["alarm"] is False


def test_injected_cr_detected(benchmark_results):
    assert benchmark_results["injected_cr"]["alarm"] is True


def test_injected_ec_detected(benchmark_results):
    assert benchmark_results["injected_ec"]["alarm"] is True


def test_injected_er_detected(benchmark_results):
    assert benchmark_results["injected_er"]["total_issues"] > 0


def test_all_cases_present(benchmark_results):
    assert EXPECTED_CASES.issubset(benchmark_results.keys())


def test_output_json_written(tmp_path):
    results = run_benchmark(str(BENCHMARK_DIR), output_dir=str(tmp_path))
    output_path = tmp_path / "benchmark_results.json"

    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == results


def test_psi_cre_range(benchmark_results):
    for case_result in benchmark_results.values():
        assert 0.0 <= case_result["psi_cre"] <= 1.0
