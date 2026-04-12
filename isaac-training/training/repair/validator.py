from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import tempfile
from typing import Any
import warnings

import yaml

from analyzers.static_analyzer import StaticReport, run_static_analysis
from repair.repair_generator import RepairPatch, RepairResult


_PATH_SEGMENT_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*)(?:\[(?P<index>\*|\d+)\])?$")


@dataclass
class PatchValidationResult:
    report_id: str
    patches_applied: int
    issues_before: list[str]
    issues_after: list[str]
    issues_resolved: list[str]
    issues_introduced: list[str]
    passed: bool
    summary: dict[str, Any]
    output_path: str | None


def _load_yaml_file(path: str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a top-level mapping")
    return payload


def _parse_path(path: str) -> list[tuple[str, str | int | None]]:
    segments: list[tuple[str, str | int | None]] = []
    for raw_segment in path.split("."):
        match = _PATH_SEGMENT_RE.match(raw_segment)
        if match is None:
            raise ValueError(f"Unsupported patch path segment: {raw_segment}")
        key = match.group("key")
        index = match.group("index")
        if index is None:
            parsed_index: str | int | None = None
        elif index == "*":
            parsed_index = "*"
        else:
            parsed_index = int(index)
        segments.append((key, parsed_index))
    return segments


def _apply_set(node: Any, segments: list[tuple[str, str | int | None]], value: Any) -> int:
    if not segments or not isinstance(node, dict):
        return 0
    key, index = segments[0]
    if key not in node:
        return 0

    if len(segments) == 1:
        if index is None:
            node[key] = value
            return 1
        target_list = node.get(key)
        if not isinstance(target_list, list):
            return 0
        if index == "*":
            for idx in range(len(target_list)):
                target_list[idx] = value
            return len(target_list)
        if 0 <= index < len(target_list):
            target_list[index] = value
            return 1
        return 0

    child = node[key]
    remaining = segments[1:]
    if index is None:
        return _apply_set(child, remaining, value)
    if not isinstance(child, list):
        return 0
    if index == "*":
        applied = 0
        for item in child:
            if isinstance(item, dict):
                applied += _apply_set(item, remaining, value)
        return applied
    if 0 <= index < len(child) and isinstance(child[index], dict):
        return _apply_set(child[index], remaining, value)
    return 0


def _resolve_list(node: Any, segments: list[tuple[str, str | int | None]]) -> list[Any] | None:
    current = node
    for key, index in segments:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
        if index is None:
            continue
        if not isinstance(current, list):
            return None
        if index == "*":
            return current
        if not (0 <= index < len(current)):
            return None
        current = current[index]
    return current if isinstance(current, list) else None


def _apply_patch(target_spec: dict[str, Any], patch: RepairPatch) -> bool:
    try:
        segments = _parse_path(patch.target_field)
    except ValueError as exc:
        warnings.warn(str(exc), RuntimeWarning)
        return False

    if patch.operation == "set":
        applied = _apply_set(target_spec, segments, patch.new_value)
        if applied == 0:
            warnings.warn(f"Failed to apply patch {patch.patch_id} to {patch.target_field}", RuntimeWarning)
            return False
        return True

    target_list = _resolve_list(target_spec, segments)
    if target_list is None:
        warnings.warn(f"Failed to resolve list path for patch {patch.patch_id}: {patch.target_field}", RuntimeWarning)
        return False
    if patch.operation == "add":
        target_list.append(patch.new_value)
        return True
    if patch.operation == "remove":
        original_len = len(target_list)
        target_list[:] = [item for item in target_list if item != patch.new_value]
        if len(target_list) == original_len:
            warnings.warn(f"Failed to remove value for patch {patch.patch_id}: {patch.target_field}", RuntimeWarning)
            return False
        return True

    warnings.warn(f"Unsupported patch operation for {patch.patch_id}: {patch.operation}", RuntimeWarning)
    return False


def _write_yaml_temp(payload: dict[str, Any]) -> str:
    handle = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8")
    try:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=False)
        return handle.name
    finally:
        handle.close()


def _build_summary(
    *,
    passed: bool,
    patches_applied: int,
    resolved_count: int,
    introduced_count: int,
) -> dict[str, Any]:
    return {
        "passed": passed,
        "patches_applied": patches_applied,
        "resolved_count": resolved_count,
        "introduced_count": introduced_count,
    }


def _write_result(result: PatchValidationResult, output_dir: str | None) -> PatchValidationResult:
    if output_dir is None:
        return result
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / "validation_result.json"
    result.output_path = str(output_path)
    output_path.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
    return result


def validate_repair(
    repair_result: RepairResult,
    static_report: StaticReport,
    reward_spec_path: str,
    constraint_spec_path: str,
    policy_spec_path: str,
    env_spec_path: str,
    output_dir: str | None = None,
) -> PatchValidationResult:
    reward_spec = _load_yaml_file(reward_spec_path)
    constraint_spec = _load_yaml_file(constraint_spec_path)
    policy_spec = _load_yaml_file(policy_spec_path)
    env_spec = _load_yaml_file(env_spec_path)

    target_specs = {
        "reward": reward_spec,
        "constraint": constraint_spec,
        "env": env_spec,
    }
    patches_applied = 0
    for patch in repair_result.patches:
        target_spec = target_specs.get(patch.target_spec)
        if target_spec is None:
            warnings.warn(f"Unsupported target_spec for patch {patch.patch_id}: {patch.target_spec}", RuntimeWarning)
            continue
        if _apply_patch(target_spec, patch):
            patches_applied += 1

    temp_paths: list[str] = []
    try:
        temp_paths.append(_write_yaml_temp(reward_spec))
        temp_paths.append(_write_yaml_temp(constraint_spec))
        temp_paths.append(_write_yaml_temp(policy_spec))
        temp_paths.append(_write_yaml_temp(env_spec))

        after_report = run_static_analysis(
            temp_paths[0],
            temp_paths[1],
            temp_paths[2],
            temp_paths[3],
        )
    finally:
        for temp_path in temp_paths:
            Path(temp_path).unlink(missing_ok=True)

    issues_before = [issue.issue_id for issue in static_report.issues]
    issues_after = [issue.issue_id for issue in after_report.issues]
    issues_resolved = [issue_id for issue_id in issues_before if issue_id not in issues_after]
    issues_introduced = [issue_id for issue_id in issues_after if issue_id not in issues_before]
    passed = issues_introduced == [] and (issues_resolved != [] or issues_before == [])

    result = PatchValidationResult(
        report_id=repair_result.report_id,
        patches_applied=patches_applied,
        issues_before=issues_before,
        issues_after=issues_after,
        issues_resolved=issues_resolved,
        issues_introduced=issues_introduced,
        passed=passed,
        summary=_build_summary(
            passed=passed,
            patches_applied=patches_applied,
            resolved_count=len(issues_resolved),
            introduced_count=len(issues_introduced),
        ),
        output_path=None,
    )
    return _write_result(result, output_dir)
