"""Analyzer package for CRE consistency checks."""

from .aggregation import FindingRecord, StaticAnalyzerReport, build_static_report, write_static_report
from .detector_runner import run_detectors, run_static_analysis
from .spec_ir import (
    ConstraintSpec,
    EnvironmentFamilySpec,
    PolicySpec,
    RewardComponentSpec,
    RewardSpec,
    RuntimeSchemaSpec,
    SpecIR,
    build_runtime_schema_spec,
    load_constraint_spec,
    load_environment_spec,
    load_policy_spec,
    load_reward_spec,
    load_spec_ir,
)
from .static_checks import (
    StaticCheckResult,
    check_constraint_runtime_binding,
    check_required_runtime_fields,
    check_reward_constraint_conflicts,
    check_reward_proxy_suspicion,
    check_scene_family_coverage,
    run_static_checks,
)

__all__ = [
    "FindingRecord",
    "StaticAnalyzerReport",
    "build_static_report",
    "write_static_report",
    "run_detectors",
    "run_static_analysis",
    "ConstraintSpec",
    "EnvironmentFamilySpec",
    "PolicySpec",
    "RewardComponentSpec",
    "RewardSpec",
    "RuntimeSchemaSpec",
    "SpecIR",
    "build_runtime_schema_spec",
    "load_constraint_spec",
    "load_environment_spec",
    "load_policy_spec",
    "load_reward_spec",
    "load_spec_ir",
    "StaticCheckResult",
    "check_constraint_runtime_binding",
    "check_required_runtime_fields",
    "check_reward_constraint_conflicts",
    "check_reward_proxy_suspicion",
    "check_scene_family_coverage",
    "run_static_checks",
]
