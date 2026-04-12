from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from analyzers.report_generator import CREReport


TARGET_SPECS = ("reward", "constraint", "env")

RULE_TEMPLATES: dict[str, dict[str, Any]] = {
    "type_compatibility": {
        "target_spec": "reward",
        "target_field": "reward_terms[*].weight",
        "operation": "set",
        "new_value": 0.0,
        "rationale": "将与 hard constraint 共享变量的 reward term weight 置零以消除边界趋近激励",
    },
    "domain_boundary": {
        "target_spec": "reward",
        "target_field": "reward_terms[*].clip_bounds.min",
        "operation": "set",
        "new_value": None,
        "rationale": "移除非负 clip 下界以消除 domain boundary 风险",
    },
    "coverage_prebound": {
        "target_spec": "env",
        "target_field": "shift_operators",
        "operation": "add",
        "new_value": "<constraint_critical_region_operator>",
        "rationale": "补充覆盖约束关键区域的 shift operator",
    },
    "deployment_shift_coverage": {
        "target_spec": "env",
        "target_field": "E_tr.shift_operators",
        "operation": "add",
        "new_value": "<deployment_shift_operator>",
        "rationale": "在训练分布中显式声明部署 shift 覆盖",
    },
    "soft_constraint_penalty_alignment": {
        "target_spec": "constraint",
        "target_field": "constraints[*].penalty_weight",
        "operation": "set",
        "new_value": 0.0,
        "rationale": "将与 reward 方向冲突的 soft constraint penalty_weight 置零",
    },
    "SEM-CR-COMPOSITE": {
        "target_spec": "reward",
        "target_field": "reward_terms[*].weight",
        "operation": "set",
        "new_value": 0.0,
        "rationale": "动态运行确认边界趋近，建议将相关 reward term weight 置零",
    },
    "SEM-EC-COVERAGE": {
        "target_spec": "env",
        "target_field": "shift_operators",
        "operation": "add",
        "new_value": "<coverage_shift_operator>",
        "rationale": "动态分析确认覆盖不足，建议补充 shift operator",
    },
    "SEM-ALARM": {
        "target_spec": "reward",
        "target_field": "reward_terms[*].weight",
        "operation": "set",
        "new_value": 0.0,
        "rationale": "Ψ_CRE 低于告警阈值，建议全面审查 reward term weights",
    },
}


@dataclass
class RepairPatch:
    patch_id: str
    target_spec: str
    target_field: str
    operation: str
    old_value: Any
    new_value: Any
    rationale: str
    source_issue_ids: list[str]


@dataclass
class RepairResult:
    report_id: str
    patches: list[RepairPatch]
    summary: dict[str, Any]
    output_path: str | None


def _make_patch_id(index: int) -> str:
    return f"PATCH-{index:03d}"


def _build_summary(patches: list[RepairPatch], source_issue_count: int) -> dict[str, Any]:
    by_target_spec = {target_spec: 0 for target_spec in TARGET_SPECS}
    for patch in patches:
        by_target_spec[patch.target_spec] = by_target_spec.get(patch.target_spec, 0) + 1
    return {
        "total_patches": len(patches),
        "by_target_spec": by_target_spec,
        "source_issue_count": source_issue_count,
    }


def _write_result(result: RepairResult, output_dir: str | None) -> RepairResult:
    if output_dir is None:
        return result
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / "repair_result.json"
    result.output_path = str(output_path)
    output_path.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
    return result


def generate_repair(
    cre_report: CREReport,
    output_dir: str | None = None,
) -> RepairResult:
    patches: list[RepairPatch] = []
    matched_issue_ids: set[str] = set()
    all_issues = [
        *cre_report.static_issues,
        *cre_report.dynamic_issues,
        *cre_report.semantic_issues,
    ]

    for issue in all_issues:
        template = RULE_TEMPLATES.get(issue.rule_id)
        if template is None:
            continue
        matched_issue_ids.add(issue.issue_id)
        evidence = issue.evidence if isinstance(issue.evidence, dict) else {}
        patches.append(
            RepairPatch(
                patch_id=_make_patch_id(len(patches) + 1),
                target_spec=template["target_spec"],
                target_field=template["target_field"],
                operation=template["operation"],
                old_value=evidence.get("old_value"),
                new_value=template["new_value"],
                rationale=template["rationale"],
                source_issue_ids=[issue.issue_id],
            )
        )

    result = RepairResult(
        report_id=cre_report.report_id,
        patches=patches,
        summary=_build_summary(patches, source_issue_count=len(matched_issue_ids)),
        output_path=None,
    )
    return _write_result(result, output_dir)
