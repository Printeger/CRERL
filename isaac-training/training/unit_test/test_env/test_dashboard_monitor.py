import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.state import build_dashboard_state


def _write_json(path: Path, payload) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _write_run(root: Path, *, name: str, source: str, execution_mode: str, scenario_type: str, avg_return: float) -> Path:
    run_dir = root / name
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_id": name,
        "source": source,
        "run_metadata": {
            "execution_mode": execution_mode,
            "scene_family": scenario_type,
            "scenario_type": scenario_type,
        },
    }
    summary = {
        "run_id": name,
        "average_return": avg_return,
        "success_rate": 0.5,
        "collision_rate": 0.1,
        "out_of_bounds_rate": 0.0,
        "min_distance": 0.75,
        "near_violation_ratio": 0.2,
        "episode_count": 2,
        "done_type_counts": {"success": 1, "collision": 1},
        "run_metadata": manifest["run_metadata"],
    }
    acceptance = {"passed": True, "max_severity": "info"}
    episodes = [
        {
            "episode_index": 0,
            "scenario_type": scenario_type,
            "scene_cfg_name": f"scene_cfg_{scenario_type}.yaml",
            "source": source,
            "scene_tags": {
                "scene_family": scenario_type,
                "execution_mode": execution_mode,
                "source": source,
                "scenario_type": scenario_type,
                "scene_cfg_name": f"scene_cfg_{scenario_type}.yaml",
            },
            "reward_components_total": {
                "reward_progress": 1.0,
                "reward_safety_static": 0.5,
                "reward_safety_dynamic": 0.2,
                "penalty_smooth": -0.1,
                "penalty_height": -0.05,
            },
        }
    ]
    _write_json(run_dir / "manifest.json", manifest)
    _write_json(run_dir / "summary.json", summary)
    _write_json(run_dir / "acceptance.json", acceptance)
    (run_dir / "steps.jsonl").write_text("", encoding="utf-8")
    (run_dir / "episodes.jsonl").write_text("\n".join(json.dumps(row) for row in episodes) + "\n", encoding="utf-8")
    return run_dir


def _write_bundle(root: Path, namespace: str, bundle_name: str, primary_payload, summary_payload, *, extra_files=None) -> Path:
    primary_name = {
        "static": "static_report.json",
        "dynamic": "dynamic_report.json",
        "semantic": "semantic_report.json",
        "report": "report.json",
        "repair": "repair_plan.json",
        "validation": "validation_decision.json",
        "integration": "integration_summary.json",
        "benchmark": "benchmark_summary.json",
        "release": "release_summary.json",
    }[namespace]
    summary_name = {
        "static": "summary.json",
        "dynamic": "summary.json",
        "semantic": "summary.json",
        "report": "summary.json",
        "repair": "repair_summary.json",
        "validation": "validation_summary.json",
        "integration": "integration_summary.json",
        "benchmark": "benchmark_summary.json",
        "release": "release_summary.json",
    }[namespace]
    bundle_dir = root / "analysis" / namespace / bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    _write_json(bundle_dir / "manifest.json", {"bundle_name": bundle_name, "namespace": namespace})
    _write_json(bundle_dir / primary_name, primary_payload)
    _write_json(bundle_dir / summary_name, summary_payload)
    for relative, payload in dict(extra_files or {}).items():
        _write_json(bundle_dir / relative, payload)
    return bundle_dir


def _write_workspace_summaries(root: Path) -> None:
    _write_json(
        root / "full_smoke_summary.json",
        {
            "summary_type": "phase11_full_smoke_summary.v1",
            "steps": {
                "semantic": {
                    "supported_claims": 3,
                    "weak_claims": 0,
                    "most_likely_claim_type": "E-C",
                    "provider_mode": "azure_gateway",
                },
                "validation": {"decision_status": "inconclusive", "repaired_run_count": 4},
            },
        },
    )
    _write_json(
        root / "native_execution_summary.json",
        {
            "summary_type": "phase11_native_execution_summary.v1",
            "analysis": {
                "semantic": {"supported_claims": 3, "weak_claims": 0, "primary_claim_type": "E-C"},
                "report": {"primary_claim_type": "C-R"},
                "validation": {"decision_status": "rejected", "repaired_run_count": 2},
            },
            "runs": {"baseline": {}, "train": {}, "eval": {}},
        },
    )


def test_build_dashboard_state_aggregates_runs_bundles_and_charts(tmp_path: Path):
    logs_root = tmp_path / "logs"
    _write_run(logs_root, name="train_nominal_001", source="train", execution_mode="train", scenario_type="nominal", avg_return=3.2)
    _write_run(logs_root, name="eval_shifted_001", source="eval", execution_mode="eval", scenario_type="shifted", avg_return=2.1)

    _write_bundle(
        tmp_path,
        "dynamic",
        "dynamic_fixture",
        {
            "passed": True,
            "max_severity": "warning",
            "witnesses": [
                {"witness_id": "W_CR", "score": 0.2},
                {"witness_id": "W_EC", "score": 0.4},
                {"witness_id": "W_ER", "score": 0.6},
            ],
        },
        {"passed": True, "max_severity": "warning", "witness_scores": {"W_CR": 0.2, "W_EC": 0.4, "W_ER": 0.6}},
    )
    _write_bundle(
        tmp_path,
        "semantic",
        "semantic_fixture",
        {
            "passed": True,
            "max_severity": "warning",
            "metadata": {"provider_mode": "azure_gateway"},
            "supported_claims": 3,
            "weak_claims": 0,
            "primary_claim_type": "E-C",
        },
        {"passed": True, "max_severity": "warning", "provider_mode": "azure_gateway"},
    )
    _write_bundle(
        tmp_path,
        "report",
        "report_fixture",
        {
            "passed": True,
            "max_severity": "warning",
            "root_cause_summary": {"primary_claim_type": "C-R"},
            "semantic_claim_summary": {"most_likely_claim_type": "E-C"},
        },
        {"passed": True, "max_severity": "warning"},
    )
    _write_bundle(
        tmp_path,
        "validation",
        "validation_fixture",
        {
            "decision_status": "rejected",
            "accepted": False,
            "blocked_by": [],
            "metric_deltas": {"consistency_improvement": -0.2, "safety_improvement": 0.1},
        },
        {"decision_status": "rejected"},
    )
    _write_bundle(
        tmp_path,
        "release",
        "release_fixture",
        {"phase11_exit_ready": True},
        {"phase11_exit_ready": True},
    )
    _write_workspace_summaries(tmp_path)

    state = build_dashboard_state(
        logs_root=logs_root,
        reports_root=tmp_path,
        watch_roots=[tmp_path],
        include_default_watch_roots=False,
    )

    assert state["overview"]["active_module"] in {"Release", "Validation", "Report", "Semantic", "Dynamic", "Logs"}
    assert any(card["label"] == "W_ER" and card["value"] == 0.6 for card in state["kpis"])
    assert any(chart["title"] == "Average Return Trend" for chart in state["charts"])
    assert any(chart["title"] == "Witness Trend" for chart in state["charts"])
    assert any(chart["title"] == "Before/After Repair Delta" for chart in state["charts"])
    assert any(event["title"].startswith("Run") for event in state["events"])


def test_build_dashboard_state_marks_incomplete_bundle_as_running(tmp_path: Path):
    semantic_dir = tmp_path / "analysis" / "semantic" / "semantic_running"
    semantic_dir.mkdir(parents=True, exist_ok=True)
    _write_json(semantic_dir / "manifest.json", {"bundle_name": "semantic_running"})

    state = build_dashboard_state(
        logs_root=tmp_path / "logs",
        reports_root=tmp_path,
        watch_roots=[tmp_path],
        include_default_watch_roots=False,
    )

    active = state["active"]
    assert active["module"] == "semantic"
    assert active["status"] == "running"


def test_dashboard_app_serves_html_and_json(tmp_path: Path):
    pytest.importorskip("starlette")
    pytest.importorskip("httpx")
    from starlette.testclient import TestClient

    from dashboard.app import create_dashboard_app

    logs_root = tmp_path / "logs"
    _write_run(logs_root, name="baseline_nominal_001", source="baseline_greedy", execution_mode="baseline", scenario_type="nominal", avg_return=4.0)
    _write_bundle(
        tmp_path,
        "release",
        "release_fixture",
        {"phase11_exit_ready": True},
        {"phase11_exit_ready": True},
    )

    app = create_dashboard_app(
        logs_root=logs_root,
        reports_root=tmp_path,
        watch_roots=[tmp_path],
        include_default_watch_roots=False,
    )
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200
    assert "CRE Local Monitoring Dashboard" in response.text
    assert "Global Overview" in response.text

    api_response = client.get("/api/state")
    assert api_response.status_code == 200
    payload = api_response.json()
    assert "overview" in payload
    assert "flow_nodes" in payload
