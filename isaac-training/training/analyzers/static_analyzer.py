from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any

import yaml

from analyzers.spec_validator import validate_spec_set


ISSUE_TYPE_PREFIX = {
    "C-R": "CR",
    "E-C": "EC",
    "E-R": "ER",
}

SEVERITIES = ("error", "warning", "info")
ISSUE_TYPES = tuple(ISSUE_TYPE_PREFIX.keys())


@dataclass
class StaticIssue:
    issue_id: str
    issue_type: str
    severity: str
    rule_id: str
    description: str
    traceable_fields: list[str]
    evidence: dict[str, Any]


@dataclass
class StaticReport:
    spec_versions: dict[str, str]
    issues: list[StaticIssue]
    summary: dict[str, Any]
    output_path: str | None


def _load_yaml_file(path: str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a top-level mapping")
    return data


def _normalize_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, ensure_ascii=True)


def _extract_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for raw_token in re.split(r"[_\s()]+", text.lower()):
        normalized = re.sub(r"[^a-z0-9]", "", raw_token)
        if len(normalized) >= 3:
            tokens.add(normalized)
    return tokens


def _make_issue_factory() -> tuple[dict[str, int], Any]:
    counters: dict[str, int] = defaultdict(int)

    def create_issue(
        issue_type: str,
        severity: str,
        rule_id: str,
        description: str,
        traceable_fields: list[str],
        evidence: dict[str, Any] | None = None,
    ) -> StaticIssue:
        prefix = ISSUE_TYPE_PREFIX[issue_type]
        counters[prefix] += 1
        return StaticIssue(
            issue_id=f"{prefix}-{counters[prefix]:03d}",
            issue_type=issue_type,
            severity=severity,
            rule_id=rule_id,
            description=description,
            traceable_fields=traceable_fields,
            evidence=evidence or {},
        )

    return counters, create_issue


def _iter_hard_constraints(constraint_spec: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    constraints = constraint_spec.get("constraints", [])
    if not isinstance(constraints, list):
        return []
    return [
        (index, constraint)
        for index, constraint in enumerate(constraints)
        if isinstance(constraint, dict) and constraint.get("severity") == "hard"
    ]


def _iter_soft_constraints(constraint_spec: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    constraints = constraint_spec.get("constraints", [])
    if not isinstance(constraints, list):
        return []
    return [
        (index, constraint)
        for index, constraint in enumerate(constraints)
        if isinstance(constraint, dict) and constraint.get("severity") == "soft"
    ]


def _rule_type_compatibility(
    reward_spec: dict[str, Any],
    constraint_spec: dict[str, Any],
    create_issue: Any,
) -> tuple[list[StaticIssue], set[tuple[str, str]]]:
    issues: list[StaticIssue] = []
    reported_pairs: set[tuple[str, str]] = set()
    reward_terms = reward_spec.get("reward_terms", [])
    if not isinstance(reward_terms, list):
        return issues, reported_pairs

    # This rule is a Class I C-R inconsistency (Def 1.3) token approximation,
    # not a direct implementation of §2.3 type_compatibility.
    for reward_index, reward_term in enumerate(reward_terms):
        if not isinstance(reward_term, dict):
            continue
        weight = reward_term.get("weight")
        if not isinstance(weight, (int, float)) or weight <= 0:
            continue
        reward_tokens = _extract_tokens(_normalize_text(reward_term.get("term_expr", "")))
        if not reward_tokens:
            continue
        reward_term_id = str(reward_term.get("term_id", f"reward_terms[{reward_index}]"))
        for constraint_index, constraint in _iter_hard_constraints(constraint_spec):
            predicate_tokens = _extract_tokens(
                _normalize_text(constraint.get("indicator_predicate", ""))
            )
            shared_tokens = sorted(reward_tokens & predicate_tokens)
            if not shared_tokens:
                continue
            constraint_id = str(constraint.get("constraint_id", f"constraint[{constraint_index}]"))
            reported_pairs.add((reward_term_id, constraint_id))
            issues.append(
                create_issue(
                    issue_type="C-R",
                    severity="warning",
                    rule_id="type_compatibility",
                    description=(
                        f"Reward term '{reward_term_id}' shares state-variable tokens with hard "
                        f"constraint '{constraint_id}', which may create boundary-seeking pressure."
                    ),
                    traceable_fields=[
                        f"reward.reward_terms[{reward_index}].term_expr",
                        f"constraint.constraints[{constraint_index}].indicator_predicate",
                    ],
                    evidence={
                        "reward_term_id": reward_term_id,
                        "constraint_id": constraint_id,
                        "shared_tokens": shared_tokens,
                    },
                )
            )
    return issues, reported_pairs


def _rule_domain_boundary(
    reward_spec: dict[str, Any],
    constraint_spec: dict[str, Any],
    already_reported_pairs: set[tuple[str, str]],
    create_issue: Any,
) -> list[StaticIssue]:
    issues: list[StaticIssue] = []
    reward_terms = reward_spec.get("reward_terms", [])
    if not isinstance(reward_terms, list):
        return issues

    # This rule is a coarse approximation of §2.3 domain_boundary.
    for reward_index, reward_term in enumerate(reward_terms):
        if not isinstance(reward_term, dict):
            continue
        weight = reward_term.get("weight")
        if not isinstance(weight, (int, float)) or weight <= 0:
            continue
        clip_bounds = reward_term.get("clip_bounds", {})
        if not isinstance(clip_bounds, dict):
            continue
        clip_min = clip_bounds.get("min")
        if not isinstance(clip_min, (int, float)) or clip_min < 0:
            continue
        reward_tokens = _extract_tokens(_normalize_text(reward_term.get("term_expr", "")))
        if not reward_tokens:
            continue
        reward_term_id = str(reward_term.get("term_id", f"reward_terms[{reward_index}]"))
        for constraint_index, constraint in _iter_hard_constraints(constraint_spec):
            constraint_id = str(constraint.get("constraint_id", f"constraint[{constraint_index}]"))
            if (reward_term_id, constraint_id) in already_reported_pairs:
                continue
            predicate_tokens = _extract_tokens(
                _normalize_text(constraint.get("indicator_predicate", ""))
            )
            shared_tokens = sorted(reward_tokens & predicate_tokens)
            if not shared_tokens:
                continue
            issues.append(
                create_issue(
                    issue_type="C-R",
                    severity="warning",
                    rule_id="domain_boundary",
                    description=(
                        f"Reward term '{reward_term_id}' has non-negative support and overlaps "
                        f"token-wise with hard constraint '{constraint_id}', suggesting reward "
                        "support may extend toward a constrained boundary."
                    ),
                    traceable_fields=[
                        f"reward.reward_terms[{reward_index}].clip_bounds.min",
                        f"reward.reward_terms[{reward_index}].term_expr",
                        f"constraint.constraints[{constraint_index}].indicator_predicate",
                    ],
                    evidence={
                        "reward_term_id": reward_term_id,
                        "constraint_id": constraint_id,
                        "clip_bounds_min": clip_min,
                        "shared_tokens": shared_tokens,
                    },
                )
            )
    return issues


def _rule_coverage_prebound(
    constraint_spec: dict[str, Any],
    env_spec: dict[str, Any],
    create_issue: Any,
) -> list[StaticIssue]:
    issues: list[StaticIssue] = []
    e_tr = env_spec.get("E_tr", {})
    scene_families = e_tr.get("scene_families", []) if isinstance(e_tr, dict) else []
    top_level_shifts = env_spec.get("shift_operators", [])
    family_count = len(scene_families) if isinstance(scene_families, list) else 0

    family_sources = scene_families if isinstance(scene_families, list) else []
    shift_sources: list[str] = []
    if isinstance(top_level_shifts, list):
        for shift in top_level_shifts:
            if not isinstance(shift, dict):
                continue
            shift_sources.append(str(shift.get("shift_id", "")))
            shift_sources.append(str(shift.get("description", "")))
    coverage_tokens = set()
    for source in [*family_sources, *shift_sources]:
        coverage_tokens |= _extract_tokens(_normalize_text(source))

    for constraint_index, constraint in _iter_hard_constraints(constraint_spec):
        constraint_id = str(constraint.get("constraint_id", f"constraint[{constraint_index}]"))
        constraint_tokens = _extract_tokens(constraint_id)
        keyword_match = bool(constraint_tokens & coverage_tokens)
        if keyword_match:
            continue
        evidence = {
            "constraint_id": constraint_id,
            "constraint_tokens": sorted(constraint_tokens),
            "keyword_match": keyword_match,
            "matched_tokens": [],
        }
        if family_count > 0:
            evidence["e_tr_family_count"] = family_count
            evidence["note"] = f"keyword match failed; E_tr has {family_count} scene families"
        issues.append(
            create_issue(
                issue_type="E-C",
                severity="warning",
                rule_id="coverage_prebound",
                description=(
                    f"Hard constraint '{constraint_id}' has no keyword-level match against "
                    "E_tr scene families or declared shift operators, so static coverage "
                    "pre-bound support is unclear."
                ),
                traceable_fields=[
                    f"constraint.constraints[{constraint_index}].constraint_id",
                    "environment.E_tr.scene_families",
                    "environment.shift_operators",
                ],
                evidence=evidence,
            )
        )
    return issues


def _rule_deployment_shift_coverage(
    env_spec: dict[str, Any],
    create_issue: Any,
) -> list[StaticIssue]:
    issues: list[StaticIssue] = []
    e_tr = env_spec.get("E_tr", {})
    if not isinstance(e_tr, dict):
        return issues
    e_tr_shift_operators = e_tr.get("shift_operators", [])
    if not isinstance(e_tr_shift_operators, list) or e_tr_shift_operators:
        return issues

    e_dep = env_spec.get("E_dep", {})
    if not isinstance(e_dep, dict):
        return issues
    deployment_envs = e_dep.get("deployment_envs", [])
    if not isinstance(deployment_envs, list):
        return issues

    # Derived from Def 1.7 E-R + §2.2 environment representation.
    for env_index, deployment_env in enumerate(deployment_envs):
        if not isinstance(deployment_env, dict):
            continue
        applied_shifts = deployment_env.get("applied_shift_operators", [])
        if not isinstance(applied_shifts, list) or not applied_shifts:
            continue
        env_id = str(deployment_env.get("env_id", f"deployment_env[{env_index}]"))
        issues.append(
            create_issue(
                issue_type="E-R",
                severity="warning",
                rule_id="deployment_shift_coverage",
                description=(
                    f"Deployment environment '{env_id}' applies shift operators, but "
                    "E_tr declares no training-time shift coverage."
                ),
                traceable_fields=[
                    "environment.E_tr.shift_operators",
                    f"environment.E_dep.deployment_envs[{env_index}].applied_shift_operators",
                ],
                evidence={
                    "env_id": env_id,
                    "applied_shift_operators": list(applied_shifts),
                    "e_tr_shift_operators": [],
                },
            )
        )
    return issues


def _rule_soft_constraint_penalty_alignment(
    reward_spec: dict[str, Any],
    constraint_spec: dict[str, Any],
    create_issue: Any,
) -> list[StaticIssue]:
    issues: list[StaticIssue] = []
    reward_terms = reward_spec.get("reward_terms", [])
    if not isinstance(reward_terms, list):
        return issues

    # Derived from Def 1.3 Class I C-R.
    for constraint_index, constraint in _iter_soft_constraints(constraint_spec):
        penalty_weight = constraint.get("penalty_weight")
        if not isinstance(penalty_weight, (int, float)) or penalty_weight <= 0:
            continue
        predicate_tokens = _extract_tokens(_normalize_text(constraint.get("indicator_predicate", "")))
        if not predicate_tokens:
            continue
        constraint_id = str(constraint.get("constraint_id", f"constraint[{constraint_index}]"))
        for reward_index, reward_term in enumerate(reward_terms):
            if not isinstance(reward_term, dict):
                continue
            reward_weight = reward_term.get("weight")
            if not isinstance(reward_weight, (int, float)) or reward_weight <= 0:
                continue
            reward_tokens = _extract_tokens(_normalize_text(reward_term.get("term_expr", "")))
            shared_tokens = sorted(reward_tokens & predicate_tokens)
            if not shared_tokens:
                continue
            reward_term_id = str(reward_term.get("term_id", f"reward_terms[{reward_index}]"))
            issues.append(
                create_issue(
                    issue_type="C-R",
                    severity="info",
                    rule_id="soft_constraint_penalty_alignment",
                    description=(
                        f"Reward term '{reward_term_id}' and soft constraint '{constraint_id}' "
                        "share variable tokens while the reward is positive and the penalty "
                        "weight is active; this may indicate competing incentives."
                    ),
                    traceable_fields=[
                        f"reward.reward_terms[{reward_index}].weight",
                        f"reward.reward_terms[{reward_index}].term_expr",
                        f"constraint.constraints[{constraint_index}].penalty_weight",
                        f"constraint.constraints[{constraint_index}].indicator_predicate",
                    ],
                    evidence={
                        "reward_term_id": reward_term_id,
                        "constraint_id": constraint_id,
                        "reward_weight": reward_weight,
                        "penalty_weight": penalty_weight,
                        "shared_tokens": shared_tokens,
                    },
                )
            )
    return issues


def _build_summary(issues: list[StaticIssue], validation_failed: bool = False) -> dict[str, Any]:
    by_type = {issue_type: 0 for issue_type in ISSUE_TYPES}
    by_severity = {severity: 0 for severity in SEVERITIES}
    for issue in issues:
        by_type[issue.issue_type] = by_type.get(issue.issue_type, 0) + 1
        by_severity[issue.severity] = by_severity.get(issue.severity, 0) + 1
    return {
        "total": len(issues),
        "by_type": by_type,
        "by_severity": by_severity,
        "validation_failed": validation_failed,
    }


def _write_report(report: StaticReport, output_dir: str | None) -> StaticReport:
    if output_dir is None:
        return report
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / "static_report.json"
    report.output_path = str(output_path)
    payload = asdict(report)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return report


def run_static_analysis(
    reward_spec_path: str,
    constraint_spec_path: str,
    policy_spec_path: str,
    env_spec_path: str,
    output_dir: str | None = None,
) -> StaticReport:
    validation = validate_spec_set(
        reward_spec_path,
        constraint_spec_path,
        policy_spec_path,
        env_spec_path,
    )
    if not validation.valid:
        report = StaticReport(
            spec_versions={},
            issues=[],
            summary=_build_summary([], validation_failed=True)
            | {
                "validation_errors": list(validation.errors),
                "validation_warnings": list(validation.warnings),
            },
            output_path=None,
        )
        return _write_report(report, output_dir)

    reward_spec = _load_yaml_file(reward_spec_path)
    constraint_spec = _load_yaml_file(constraint_spec_path)
    policy_spec = _load_yaml_file(policy_spec_path)
    env_spec = _load_yaml_file(env_spec_path)

    _, create_issue = _make_issue_factory()
    issues: list[StaticIssue] = []

    type_compatibility_issues, reported_pairs = _rule_type_compatibility(
        reward_spec,
        constraint_spec,
        create_issue,
    )
    issues.extend(type_compatibility_issues)
    issues.extend(
        _rule_domain_boundary(
            reward_spec,
            constraint_spec,
            reported_pairs,
            create_issue,
        )
    )
    issues.extend(_rule_coverage_prebound(constraint_spec, env_spec, create_issue))
    issues.extend(_rule_deployment_shift_coverage(env_spec, create_issue))
    issues.extend(
        _rule_soft_constraint_penalty_alignment(
            reward_spec,
            constraint_spec,
            create_issue,
        )
    )

    report = StaticReport(
        spec_versions={
            "reward": str(reward_spec.get("spec_version", "")),
            "constraint": str(constraint_spec.get("spec_version", "")),
            "policy": str(policy_spec.get("spec_version", "")),
            "environment": str(env_spec.get("spec_version", "")),
        },
        issues=issues,
        summary=_build_summary(issues, validation_failed=False),
        output_path=None,
    )
    return _write_report(report, output_dir)
