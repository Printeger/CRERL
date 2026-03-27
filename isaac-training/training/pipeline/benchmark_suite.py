"""Phase 11 benchmark suite bundle builder."""

from __future__ import annotations

import ast
import copy
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from analyzers.report_contract import (
    BENCHMARK_SUITE_MODE,
    DEFAULT_REPORT_MODE_ARTIFACTS,
    DEFAULT_REPORT_NAMESPACES,
    resolve_report_namespace_root,
    write_namespace_manifest,
    write_report_namespace_contract,
)
from analyzers.spec_ir import load_policy_spec

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal envs
    class _YamlCompat:
        @staticmethod
        def _strip_comment(line: str) -> str:
            return line.split("#", 1)[0].rstrip()

        @staticmethod
        def _parse_scalar(value: str):
            lowered = value.lower()
            if lowered in {"true", "false"}:
                return lowered == "true"
            if lowered in {"null", "none", "~"}:
                return None
            if value.startswith(("'", '"')) and value.endswith(("'", '"')):
                return value[1:-1]
            if value.startswith(("[", "{", "(", "-")) or value[:1].isdigit():
                try:
                    normalized = (
                        value.replace("true", "True")
                        .replace("false", "False")
                        .replace("null", "None")
                    )
                    return ast.literal_eval(normalized)
                except Exception:
                    pass
            try:
                if "." in value or "e" in lowered:
                    return float(value)
                return int(value)
            except Exception:
                return value

        @classmethod
        def _parse_block(cls, lines, start_idx: int, indent: int):
            if start_idx >= len(lines):
                return {}, start_idx

            _, content = lines[start_idx]
            if content.startswith("- "):
                items = []
                idx = start_idx
                while idx < len(lines):
                    current_indent, current = lines[idx]
                    if current_indent < indent or not current.startswith("- ") or current_indent != indent:
                        break
                    payload = current[2:].strip()
                    idx += 1
                    if payload == "":
                        child, idx = cls._parse_block(lines, idx, indent + 2)
                        items.append(child)
                    else:
                        items.append(cls._parse_scalar(payload))
                return items, idx

            mapping = {}
            idx = start_idx
            while idx < len(lines):
                current_indent, current = lines[idx]
                if current_indent < indent or current_indent != indent:
                    break
                key, sep, raw_value = current.partition(":")
                if not sep:
                    raise ValueError(f"Invalid YAML line: {current}")
                key = key.strip()
                value = raw_value.strip()
                idx += 1
                if value == "":
                    if idx < len(lines) and lines[idx][0] > current_indent:
                        child, idx = cls._parse_block(lines, idx, current_indent + 2)
                        mapping[key] = child
                    else:
                        mapping[key] = {}
                else:
                    mapping[key] = cls._parse_scalar(value)
            return mapping, idx

        @classmethod
        def safe_load(cls, text):
            lines = []
            for raw_line in text.splitlines():
                stripped = cls._strip_comment(raw_line)
                if not stripped.strip():
                    continue
                indent = len(stripped) - len(stripped.lstrip(" "))
                lines.append((indent, stripped.lstrip(" ")))
            if not lines:
                return {}
            parsed, _ = cls._parse_block(lines, 0, lines[0][0])
            return parsed

    yaml = _YamlCompat()


TRAINING_ROOT = Path(__file__).resolve().parents[1]
CFG_ROOT = TRAINING_ROOT / "cfg"
DEFAULT_SPEC_CFG_DIR = CFG_ROOT / "spec_cfg"
DEFAULT_ENV_CFG_DIR = CFG_ROOT / "env_cfg"
DEFAULT_BENCHMARK_CFG_DIR = CFG_ROOT / "benchmark_cfg"
BENCHMARK_NAMESPACE = DEFAULT_REPORT_NAMESPACES[BENCHMARK_SUITE_MODE]
ANALYSIS_MODE_NAMESPACE_KEYS = {
    "static": "static_audit_namespace",
    "dynamic": "dynamic_analysis_namespace",
    "semantic": "semantic_analysis_namespace",
    "report": "report_generation_namespace",
    "repair": "repair_generation_namespace",
    "validation": "validation_generation_namespace",
    "integration": "integration_audit_namespace",
}
EXECUTION_MODE_ENTRYPOINTS = {
    "baseline": "isaac-training/training/scripts/run_baseline.py",
    "eval": "isaac-training/training/scripts/eval.py",
    "train": "isaac-training/training/scripts/train.py",
}


def _load_yaml_file(path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML file at {path} must load to a dict.")
    return data


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if str(item)]
    if str(value):
        return [str(value)]
    return []


def _deep_copy_dict(mapping: Mapping[str, Any]) -> Dict[str, Any]:
    return copy.deepcopy(dict(mapping))


def _resolve_yaml_reference(root: Path, ref: str) -> Path:
    path = Path(ref)
    if not path.is_absolute():
        path = root / path
    return path


def _default_case_path(benchmark_cfg_dir: Path, suite_name: str) -> Path:
    path = Path(suite_name)
    if path.suffix:
        return path if path.is_absolute() else benchmark_cfg_dir / path
    return benchmark_cfg_dir / f"{suite_name}.yaml"


def _resolve_required_namespaces(
    analysis_modes: Sequence[str],
    policy_runtime_expectations: Mapping[str, Any],
) -> Dict[str, str]:
    resolved: Dict[str, str] = {}
    for mode in analysis_modes:
        namespace_key = ANALYSIS_MODE_NAMESPACE_KEYS.get(str(mode))
        if not namespace_key:
            continue
        namespace = str(policy_runtime_expectations.get(namespace_key, "")).strip()
        if namespace:
            resolved[str(mode)] = namespace
    return resolved


def load_benchmark_suite_manifest(
    *,
    benchmark_cfg_dir: str | Path = DEFAULT_BENCHMARK_CFG_DIR,
    suite_name: str = "benchmark_suite_v1",
) -> Dict[str, Any]:
    benchmark_cfg_dir = Path(benchmark_cfg_dir)
    suite_path = _default_case_path(benchmark_cfg_dir, suite_name)
    payload = _load_yaml_file(suite_path)
    payload["suite_path"] = str(suite_path)
    return payload


def _build_case_record(
    case_payload: Mapping[str, Any],
    *,
    case_path: Path,
    spec_cfg_dir: Path,
    env_cfg_dir: Path,
    suite_defaults: Mapping[str, Any],
    policy_runtime_expectations: Mapping[str, Any],
) -> Dict[str, Any]:
    spec_refs = _deep_copy_dict(case_payload.get("spec_refs", {}))
    env_refs = _deep_copy_dict(case_payload.get("env_refs", {}))

    resolved_spec_refs = {
        str(key): str(_resolve_yaml_reference(spec_cfg_dir, str(value)))
        for key, value in spec_refs.items()
    }
    resolved_env_refs = {
        str(key): (
            [str(_resolve_yaml_reference(env_cfg_dir, item)) for item in value]
            if isinstance(value, (list, tuple))
            else str(_resolve_yaml_reference(env_cfg_dir, str(value)))
        )
        for key, value in env_refs.items()
    }

    spec_refs_ok = all(Path(path).exists() for path in resolved_spec_refs.values())
    env_refs_ok = all(
        Path(item).exists()
        for value in resolved_env_refs.values()
        for item in (value if isinstance(value, list) else [value])
    )

    execution_modes = _as_str_list(case_payload.get("execution_modes")) or _as_str_list(
        suite_defaults.get("default_execution_modes")
    )
    analysis_modes = _as_str_list(case_payload.get("analysis_modes")) or _as_str_list(
        suite_defaults.get("default_analysis_modes")
    )
    supported_modes = {
        str(item)
        for item in _as_str_list(policy_runtime_expectations.get("supported_execution_modes"))
    }
    integration_modes = {
        str(item)
        for item in _as_str_list(policy_runtime_expectations.get("integration_required_execution_modes"))
    }

    expected_signals = _deep_copy_dict(case_payload.get("expected_signals", {}))
    expected_primary_claim_type = str(expected_signals.get("expected_primary_claim_type", "")).strip()
    expected_validation_targets = _as_str_list(expected_signals.get("expected_validation_targets"))
    expected_analyzer_focus = _as_str_list(expected_signals.get("expected_analyzer_focus"))
    required_namespaces = _resolve_required_namespaces(analysis_modes, policy_runtime_expectations)

    case_record = {
        "schema_type": str(case_payload.get("schema_type", "phase11_benchmark_case.v1")),
        "case_id": str(case_payload.get("case_id", case_path.stem)),
        "title": str(case_payload.get("title", case_path.stem)),
        "description": str(case_payload.get("description", "")),
        "case_path": str(case_path),
        "benchmark_class": str(case_payload.get("benchmark_class", "injected")),
        "inconsistency_type": str(case_payload.get("inconsistency_type", "clean")),
        "scene_family": str(case_payload.get("scene_family", "nominal")),
        "scene_cfg_name": str(case_payload.get("scene_cfg_name", "")),
        "execution_modes": execution_modes,
        "analysis_modes": analysis_modes,
        "spec_refs": spec_refs,
        "env_refs": env_refs,
        "resolved_spec_refs": resolved_spec_refs,
        "resolved_env_refs": resolved_env_refs,
        "spec_refs_ok": bool(spec_refs_ok),
        "env_refs_ok": bool(env_refs_ok),
        "supported_execution_modes": sorted(mode for mode in execution_modes if mode in supported_modes),
        "unsupported_execution_modes": sorted(mode for mode in execution_modes if mode not in supported_modes),
        "native_phase10_ready": all(mode in integration_modes for mode in execution_modes),
        "expected_primary_claim_type": expected_primary_claim_type,
        "expected_validation_targets": expected_validation_targets,
        "expected_analyzer_focus": expected_analyzer_focus,
        "required_namespaces": required_namespaces,
        "injection": _deep_copy_dict(case_payload.get("injection", {})),
        "release": _deep_copy_dict(case_payload.get("release", {})),
    }
    case_record["case_ready"] = bool(
        case_record["spec_refs_ok"]
        and case_record["env_refs_ok"]
        and not case_record["unsupported_execution_modes"]
        and case_record["native_phase10_ready"]
    )
    return case_record


def _build_benchmark_matrix(case_records: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    rows = []
    execution_rows = []
    comparison_rows = []
    for case in case_records:
        case_id = str(case.get("case_id", ""))
        execution_modes = list(case.get("execution_modes", []) or [])
        required_namespaces = dict(case.get("required_namespaces", {}) or {})
        expected_validation_targets = list(case.get("expected_validation_targets", []) or [])
        scene_family = str(case.get("scene_family", ""))
        scene_cfg_name = str(case.get("scene_cfg_name", ""))
        case_ready = bool(case.get("case_ready", False))
        rows.append(
            {
                "case_id": case_id,
                "benchmark_class": str(case.get("benchmark_class", "")),
                "inconsistency_type": str(case.get("inconsistency_type", "")),
                "scene_family": scene_family,
                "scene_cfg_name": scene_cfg_name,
                "execution_modes": execution_modes,
                "analysis_modes": list(case.get("analysis_modes", []) or []),
                "case_ready": case_ready,
                "native_phase10_ready": bool(case.get("native_phase10_ready", False)),
                "expected_primary_claim_type": str(case.get("expected_primary_claim_type", "")),
                "expected_validation_targets": expected_validation_targets,
                "required_namespaces": required_namespaces,
            }
        )
        for execution_mode in execution_modes:
            execution_rows.append(
                {
                    "task_id": f"{case_id}::{execution_mode}",
                    "case_id": case_id,
                    "execution_mode": execution_mode,
                    "entrypoint": EXECUTION_MODE_ENTRYPOINTS.get(execution_mode, ""),
                    "scene_family": scene_family,
                    "scene_cfg_name": scene_cfg_name,
                    "benchmark_class": str(case.get("benchmark_class", "")),
                    "inconsistency_type": str(case.get("inconsistency_type", "")),
                    "required_namespaces": required_namespaces,
                    "expected_validation_targets": expected_validation_targets,
                    "replay_ready": bool(case_ready and execution_mode in EXECUTION_MODE_ENTRYPOINTS),
                    "phase10_native_ready": bool(case.get("native_phase10_ready", False)),
                }
            )
        for target in expected_validation_targets:
            comparison_rows.append(
                {
                    "comparison_id": f"{case_id}::{target}",
                    "case_id": case_id,
                    "target_metric": target,
                    "scene_family": scene_family,
                    "inconsistency_type": str(case.get("inconsistency_type", "")),
                    "comparison_ready": bool(case_ready),
                }
            )
    return {
        "matrix_type": "phase11_benchmark_execution_matrix.v2",
        "rows": rows,
        "execution_rows": execution_rows,
        "comparison_rows": comparison_rows,
    }


def _build_benchmark_summary(
    *,
    suite_name: str,
    suite_version: str,
    case_records: Sequence[Mapping[str, Any]],
    benchmark_matrix: Mapping[str, Any],
) -> Dict[str, Any]:
    cases = list(case_records)
    injected_cases = [case for case in cases if str(case.get("benchmark_class", "")) == "injected"]
    clean_cases = [case for case in cases if str(case.get("benchmark_class", "")) == "clean"]
    inconsistency_counts: Dict[str, int] = {}
    for case in cases:
        inconsistency_type = str(case.get("inconsistency_type", ""))
        inconsistency_counts[inconsistency_type] = inconsistency_counts.get(inconsistency_type, 0) + 1
    ready_cases = [case for case in cases if bool(case.get("case_ready", False))]

    return {
        "summary_type": "phase11_benchmark_summary.v1",
        "suite_name": suite_name,
        "suite_version": suite_version,
        "case_count": len(cases),
        "clean_case_count": len(clean_cases),
        "injected_case_count": len(injected_cases),
        "ready_case_count": len(ready_cases),
        "phase10_native_ready_case_count": sum(bool(case.get("native_phase10_ready", False)) for case in cases),
        "execution_task_count": len(list(benchmark_matrix.get("execution_rows", []) or [])),
        "comparison_task_count": len(list(benchmark_matrix.get("comparison_rows", []) or [])),
        "replay_ready_task_count": sum(
            bool(row.get("replay_ready", False))
            for row in list(benchmark_matrix.get("execution_rows", []) or [])
        ),
        "inconsistency_counts": inconsistency_counts,
        "analysis_mode_union": sorted(
            {
                str(mode)
                for case in cases
                for mode in list(case.get("analysis_modes", []) or [])
            }
        ),
        "execution_mode_union": sorted(
            {
                str(mode)
                for case in cases
                for mode in list(case.get("execution_modes", []) or [])
            }
        ),
        "matrix_ready": all(bool(row.get("case_ready", False)) for row in benchmark_matrix.get("rows", [])),
    }


def _build_summary_markdown(
    *,
    benchmark_manifest: Mapping[str, Any],
    benchmark_summary: Mapping[str, Any],
    benchmark_matrix: Mapping[str, Any],
) -> str:
    lines = [
        "# Phase 11 Benchmark Summary",
        "",
        f"- Suite: `{benchmark_manifest['suite_name']}`",
        f"- Version: `{benchmark_manifest['suite_version']}`",
        f"- Cases: `{benchmark_summary['case_count']}`",
        f"- Clean cases: `{benchmark_summary['clean_case_count']}`",
        f"- Injected cases: `{benchmark_summary['injected_case_count']}`",
        f"- Ready cases: `{benchmark_summary['ready_case_count']}`",
        f"- Phase-10-native-ready cases: `{benchmark_summary['phase10_native_ready_case_count']}`",
        f"- Execution tasks: `{benchmark_summary['execution_task_count']}`",
        f"- Replay-ready tasks: `{benchmark_summary['replay_ready_task_count']}`",
        f"- Comparison tasks: `{benchmark_summary['comparison_task_count']}`",
        "",
        "## Benchmark Cases",
        "",
    ]
    for row in benchmark_matrix.get("rows", []):
        lines.extend(
            [
                f"### {row['case_id']}",
                f"- class: `{row['benchmark_class']}`",
                f"- inconsistency: `{row['inconsistency_type']}`",
                f"- family: `{row['scene_family']}`",
                f"- execution modes: `{', '.join(row['execution_modes'])}`",
                f"- ready: `{row['case_ready']}`",
                f"- expected primary claim: `{row['expected_primary_claim_type'] or 'none'}`",
            ]
        )
        if row.get("expected_validation_targets"):
            lines.append(
                f"- expected validation targets: `{', '.join(row['expected_validation_targets'])}`"
            )
        lines.append("")
    lines.extend(["## Replay Matrix", ""])
    for row in benchmark_matrix.get("execution_rows", []):
        lines.extend(
            [
                f"- `{row['task_id']}` -> entrypoint `{row['entrypoint']}` | replay ready `{row['replay_ready']}`",
            ]
        )
    lines.append("")
    return "\n".join(lines).strip() + "\n"


@dataclass
class BenchmarkSuiteAudit:
    suite_name: str
    suite_version: str
    benchmark_manifest: Dict[str, Any]
    benchmark_cases: Dict[str, Any]
    benchmark_matrix: Dict[str, Any]
    benchmark_summary: Dict[str, Any]


def write_benchmark_bundle(
    audit: BenchmarkSuiteAudit,
    *,
    report_dir: str | Path,
    namespaces: Mapping[str, str] | None = None,
    report_mode_artifacts: Mapping[str, Sequence[str]] | None = None,
) -> Dict[str, Path]:
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    benchmark_manifest_path = report_dir / "benchmark_manifest.json"
    benchmark_cases_path = report_dir / "benchmark_cases.json"
    benchmark_matrix_path = report_dir / "benchmark_matrix.json"
    benchmark_summary_path = report_dir / "benchmark_summary.json"
    benchmark_summary_md_path = report_dir / "benchmark_summary.md"
    manifest_path = report_dir / "manifest.json"

    benchmark_manifest_path.write_text(
        json.dumps(audit.benchmark_manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    benchmark_cases_path.write_text(
        json.dumps(audit.benchmark_cases, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    benchmark_matrix_path.write_text(
        json.dumps(audit.benchmark_matrix, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    benchmark_summary_path.write_text(
        json.dumps(audit.benchmark_summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    benchmark_summary_md_path.write_text(
        _build_summary_markdown(
            benchmark_manifest=audit.benchmark_manifest,
            benchmark_summary=audit.benchmark_summary,
            benchmark_matrix=audit.benchmark_matrix,
        ),
        encoding="utf-8",
    )

    bundle_paths = {
        "report_dir": report_dir,
        "benchmark_manifest_path": benchmark_manifest_path,
        "benchmark_cases_path": benchmark_cases_path,
        "benchmark_matrix_path": benchmark_matrix_path,
        "benchmark_summary_path": benchmark_summary_path,
        "benchmark_summary_md_path": benchmark_summary_md_path,
        "manifest_path": manifest_path,
    }

    namespace_root = resolve_report_namespace_root(
        report_dir.parents[2],
        BENCHMARK_SUITE_MODE,
        namespaces=namespaces,
    )
    namespace_manifest_path = write_namespace_manifest(
        namespace_root,
        bundle_name=report_dir.name,
        report_mode=BENCHMARK_SUITE_MODE,
        namespace=(namespaces or DEFAULT_REPORT_NAMESPACES)[BENCHMARK_SUITE_MODE],
        bundle_paths=bundle_paths,
        report_summary=audit.benchmark_summary,
    )
    namespace_contract_path = write_report_namespace_contract(
        report_dir.parents[2],
        namespaces=namespaces,
        report_mode_artifacts=report_mode_artifacts,
    )

    manifest_payload = {
        "bundle_type": "phase11_benchmark_bundle.v1",
        "suite_name": audit.suite_name,
        "suite_version": audit.suite_version,
        "benchmark_manifest_path": str(benchmark_manifest_path),
        "benchmark_cases_path": str(benchmark_cases_path),
        "benchmark_matrix_path": str(benchmark_matrix_path),
        "benchmark_summary_path": str(benchmark_summary_path),
        "benchmark_summary_md_path": str(benchmark_summary_md_path),
        "namespace_manifest_path": str(namespace_manifest_path),
        "namespace_contract_path": str(namespace_contract_path),
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True), encoding="utf-8")

    bundle_paths["namespace_manifest_path"] = namespace_manifest_path
    bundle_paths["namespace_contract_path"] = namespace_contract_path
    return bundle_paths


def build_benchmark_suite_audit(
    *,
    benchmark_cfg_dir: str | Path = DEFAULT_BENCHMARK_CFG_DIR,
    suite_name: str = "benchmark_suite_v1",
    spec_cfg_dir: str | Path = DEFAULT_SPEC_CFG_DIR,
    env_cfg_dir: str | Path = DEFAULT_ENV_CFG_DIR,
) -> BenchmarkSuiteAudit:
    benchmark_cfg_dir = Path(benchmark_cfg_dir)
    spec_cfg_dir = Path(spec_cfg_dir)
    env_cfg_dir = Path(env_cfg_dir)
    suite_payload = load_benchmark_suite_manifest(
        benchmark_cfg_dir=benchmark_cfg_dir,
        suite_name=suite_name,
    )
    policy_spec = load_policy_spec(spec_cfg_dir=spec_cfg_dir)
    policy_runtime_expectations = dict(policy_spec.raw.get("runtime_expectations", {}) or {})

    case_files = _as_str_list(suite_payload.get("case_files"))
    case_records = []
    for case_file in case_files:
        case_path = _resolve_yaml_reference(benchmark_cfg_dir, case_file)
        case_payload = _load_yaml_file(case_path)
        case_records.append(
            _build_case_record(
                case_payload,
                case_path=case_path,
                spec_cfg_dir=spec_cfg_dir,
                env_cfg_dir=env_cfg_dir,
                suite_defaults=suite_payload,
                policy_runtime_expectations=policy_runtime_expectations,
            )
        )

    benchmark_matrix = _build_benchmark_matrix(case_records)
    benchmark_manifest = {
        "manifest_type": "phase11_benchmark_manifest.v1",
        "suite_name": str(suite_payload.get("suite_name", suite_name)),
        "suite_version": str(suite_payload.get("suite_version", "v1")),
        "description": str(suite_payload.get("description", "")),
        "suite_path": str(suite_payload.get("suite_path", "")),
        "case_files": case_files,
        "default_execution_modes": _as_str_list(suite_payload.get("default_execution_modes")),
        "default_analysis_modes": _as_str_list(suite_payload.get("default_analysis_modes")),
        "case_ids": [str(case.get("case_id", "")) for case in case_records],
        "execution_task_count": len(list(benchmark_matrix.get("execution_rows", []) or [])),
        "comparison_task_count": len(list(benchmark_matrix.get("comparison_rows", []) or [])),
    }
    benchmark_summary = _build_benchmark_summary(
        suite_name=benchmark_manifest["suite_name"],
        suite_version=benchmark_manifest["suite_version"],
        case_records=case_records,
        benchmark_matrix=benchmark_matrix,
    )
    benchmark_cases = {
        "cases_type": "phase11_benchmark_cases.v1",
        "suite_name": benchmark_manifest["suite_name"],
        "cases": case_records,
    }

    return BenchmarkSuiteAudit(
        suite_name=benchmark_manifest["suite_name"],
        suite_version=benchmark_manifest["suite_version"],
        benchmark_manifest=benchmark_manifest,
        benchmark_cases=benchmark_cases,
        benchmark_matrix=benchmark_matrix,
        benchmark_summary=benchmark_summary,
    )


def run_benchmark_suite_bundle(
    *,
    benchmark_cfg_dir: str | Path = DEFAULT_BENCHMARK_CFG_DIR,
    suite_name: str = "benchmark_suite_v1",
    reports_root: str | Path = TRAINING_ROOT / "reports",
    bundle_name: Optional[str] = None,
    benchmark_dir: str | Path | None = None,
    namespaces: Mapping[str, str] | None = None,
    report_mode_artifacts: Mapping[str, Sequence[str]] | None = None,
    spec_cfg_dir: str | Path = DEFAULT_SPEC_CFG_DIR,
    env_cfg_dir: str | Path = DEFAULT_ENV_CFG_DIR,
) -> tuple[BenchmarkSuiteAudit, Dict[str, Path]]:
    audit = build_benchmark_suite_audit(
        benchmark_cfg_dir=benchmark_cfg_dir,
        suite_name=suite_name,
        spec_cfg_dir=spec_cfg_dir,
        env_cfg_dir=env_cfg_dir,
    )
    if benchmark_dir is None:
        namespace_root = resolve_report_namespace_root(
            reports_root,
            BENCHMARK_SUITE_MODE,
            namespaces=namespaces,
        )
        target_bundle_name = bundle_name or audit.suite_name
        benchmark_dir = namespace_root / target_bundle_name
    bundle_paths = write_benchmark_bundle(
        audit,
        report_dir=benchmark_dir,
        namespaces=namespaces,
        report_mode_artifacts=report_mode_artifacts,
    )
    bundle_paths["benchmark_dir"] = bundle_paths["report_dir"]
    return audit, bundle_paths


__all__ = [
    "BENCHMARK_NAMESPACE",
    "BenchmarkSuiteAudit",
    "build_benchmark_suite_audit",
    "load_benchmark_suite_manifest",
    "run_benchmark_suite_bundle",
    "write_benchmark_bundle",
]
