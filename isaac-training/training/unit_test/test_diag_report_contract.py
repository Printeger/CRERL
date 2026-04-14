"""Contract tests for the CRE_v4 Part II Section 1.2 core schemas."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass
import inspect
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analyzers.diag_report import (
    AcceptanceVerdict,
    AmbiguityFlag,
    Constraint,
    DiagReport,
    DiscrepancyRecord,
    Environment,
    NLInput,
    PolicyClass,
    RepairProposal,
    RewardDAG,
    RewardTerm,
    SpecS,
    TrainingEnvDistribution,
)
from analyzers.cfg import CFG, CFGSchema, CONFIG_WEIGHT_SUM_ERROR
from analyzers.errors import (
    CREError,
    CREErrorCode,
    ERROR_CLASS_REGISTRY,
    ERROR_REGISTRY,
    ConfigWeightSumError,
    ErrorDescriptor,
)


def _build_nlinput() -> NLInput:
    return NLInput(
        r_desc="maximize progress toward the goal",
        c_desc="avoid collisions and stay within workspace limits",
        e_desc="indoor cluttered navigation with dynamic obstacles",
        metadata={"source": "manual-yaml-bootstrap"},
    )


def _build_ambiguity_flag(**overrides: object) -> AmbiguityFlag:
    kwargs: dict[str, object] = {
        "flag_type": "UNDEFINED_THRESHOLD",
        "location": "R.nodes.0.clip_bounds.max",
        "impact_score": 0.5,
    }
    kwargs.update(overrides)
    return AmbiguityFlag(**kwargs)


def _build_constraint(**overrides: object) -> Constraint:
    kwargs: dict[str, object] = {
        "k_id": "C1",
        "predicate": lambda _state, _action: 0,
        "sigma": "hard",
        "scope": "instantaneous",
        "zeta": None,
        "lam": None,
        "delta": 0.1,
    }
    kwargs.update(overrides)
    return Constraint(**kwargs)


def _build_discrepancy_record() -> DiscrepancyRecord:
    return DiscrepancyRecord()


def _build_diag_report(**overrides: object) -> DiagReport:
    kwargs: dict[str, object] = {
        "spec_id": "spec-001",
        "timestamp": "2026-04-14T10:30:00Z",
        "phi_cr2": 0.8,
        "phi_ec_bar": 0.75,
        "phi_er3": 0.7,
        "phi_cr1": None,
        "phi_ec2": None,
        "phi_ec3": None,
        "phi_ec_per_j": None,
        "phi_er1": None,
        "phi_er2": None,
        "kappa_cr": None,
        "gamma_ec": None,
        "delta_er": None,
        "psi_cre": 0.76,
        "ci_95": {"phi_cr2": (0.72, 0.88), "psi_cre": (0.68, 0.84)},
        "flags": ["WARN_REWARD_SPARSE"],
        "discrepancy": [_build_discrepancy_record()],
        "failure_hypothesis": None,
        "repair_targets": None,
    }
    kwargs.update(overrides)
    return DiagReport(**kwargs)


def _build_reward_dag(**overrides: object) -> RewardDAG:
    kwargs: dict[str, object] = {
        "nodes": [RewardTerm()],
        "edges": [("r_goal", "r_progress")],
    }
    kwargs.update(overrides)
    return RewardDAG(**kwargs)


def _build_specs() -> SpecS:
    return SpecS(
        spec_id="spec-001",
        E_tr=TrainingEnvDistribution(),
        E_dep=[Environment()],
        R=RewardDAG(nodes=[RewardTerm()], edges=[]),
        C=[_build_constraint()],
        Pi=PolicyClass(),
    )


def _build_repair_proposal(**overrides: object) -> RepairProposal:
    kwargs: dict[str, object] = {
        "proposal_id": "123e4567-e89b-12d3-a456-426614174000",
        "spec_prime": _build_specs(),
        "operator_class": "ReweightTerms",
        "declared_side_effects": {
            "reward": "May reduce nominal progress while improving safety."
        },
        "semantic_justification": (
            "Increase safety margin emphasis to reduce collision-seeking behavior."
        ),
        "predicted_delta_psi": 0.12,
        "rough_delta_psi": 0.08,
    }
    kwargs.update(overrides)
    return RepairProposal(**kwargs)


def _build_acceptance_verdict(**overrides: object) -> AcceptanceVerdict:
    kwargs: dict[str, object] = {
        "accepted": True,
        "c1_pass": True,
        "c2_pass": True,
        "c3_pass": True,
        "c4_pass": True,
        "s_sem": 0.8,
        "intent_preserved": True,
        "rejection_feedback": None,
    }
    kwargs.update(overrides)
    return AcceptanceVerdict(**kwargs)


def _build_cfg(**overrides: object) -> CFGSchema:
    kwargs: dict[str, object] = {
        "eta_flag": 0.15,
        "llm_retry_limit": 3,
        "delta_j_default": 0.50,
        "n_ref_traj": 500,
        "n_mc_kj": 1000,
        "critical_region_radius": 0.10,
        "ec_aggregation_mode": "mean",
        "eps_stab": 1e-6,
        "enhanced_estimators_enabled": True,
        "eta_disc": 0.15,
        "tau_low": 0.30,
        "tau_high": 0.70,
        "lambda_expand": 0.50,
        "n_rechk": 1,
        "f_steepness": 8.0,
        "f_inflection": 0.50,
        "w_cr": 0.333,
        "w_ec": 0.333,
        "w_er": 0.334,
        "b_bootstrap": 1000,
        "k_detect": 1.5,
        "k_alarm": 3.0,
        "tau_alarm_psi": 0.75,
        "k_proposals": 3,
        "eta_edit": 0.20,
        "n_rank_episodes": 50,
        "eps_rank": 0.02,
        "ranking_mode": "rollout_first",
        "tau_sem": 0.80,
        "eps_perf": 0.05,
        "n_max_iterations": 5,
    }
    kwargs.update(overrides)
    return CFGSchema(**kwargs)


def _error_code_values() -> list[str]:
    return [
        value
        for name, value in vars(CREErrorCode).items()
        if name.isupper() and not name.startswith("_")
    ]


TABLE_5_EXPECTED_ROWS: tuple[ErrorDescriptor, ...] = (
    ErrorDescriptor(
        CREErrorCode.SPEC_PARSE_FAILURE,
        "HALT",
        "M1",
        "LLM failed to produce valid JSON spec after all retries",
    ),
    ErrorDescriptor(
        CREErrorCode.NULL_REWARD,
        "HALT",
        "M1",
        "Reward DAG has no nodes after null-fill",
    ),
    ErrorDescriptor(
        CREErrorCode.EMPTY_CONSTRAINT_SET,
        "WARN",
        "M1",
        "No constraints parsed; downstream runs constraint-free",
    ),
    ErrorDescriptor(
        CREErrorCode.EMPTY_ENV_SET,
        "HALT",
        "M1",
        "No deployment environments; e0 required",
    ),
    ErrorDescriptor(
        CREErrorCode.AMBIGUITY_UNRESOLVABLE,
        "HALT",
        "M1",
        "High-impact ambiguity flag cannot be autoresolved",
    ),
    ErrorDescriptor(
        CREErrorCode.PRECHECK_TYPE_MISMATCH,
        "HALT",
        "M1",
        "Incompatible state/action subspaces",
    ),
    ErrorDescriptor(
        CREErrorCode.PRECHECK_DOMAIN_TRIVIAL,
        "HALT",
        "M1",
        "Entire state space is violating; trivial repair exists",
    ),
    ErrorDescriptor(
        CREErrorCode.PRECHECK_COVERAGE_INSUFFICIENT,
        "HALT",
        "M1",
        "Fewer scene families than hard constraints",
    ),
    ErrorDescriptor(
        CREErrorCode.PRECHECK_SOFT_NO_TOLERANCE,
        "WARN",
        "M1",
        "Soft constraint with zeta=None",
    ),
    ErrorDescriptor(
        CREErrorCode.DEGENERATE_CR1_VAR,
        "WARN",
        "M2",
        "sigma_R = 0 or sigma_C = 0; phi_cr1 set to None",
    ),
    ErrorDescriptor(
        CREErrorCode.BOUNDARY_BASELINE_DEGENERATE,
        "HALT",
        "M2",
        "pi_unif has zero boundary clearance",
    ),
    ErrorDescriptor(
        CREErrorCode.ER_CORRELATION_DEGENERATE,
        "HALT",
        "M2",
        "Zero cross-environment variance in R or U",
    ),
    ErrorDescriptor(
        CREErrorCode.NO_HARD_CONSTRAINTS,
        "HALT",
        "M2",
        "phi_cr2 called with no hard constraints",
    ),
    ErrorDescriptor(
        CREErrorCode.WRONG_SEVERITY,
        "HALT",
        "M2",
        "compute_phi_ec_j called with non-hard constraint",
    ),
    ErrorDescriptor(
        CREErrorCode.EMPTY_KJ_ESTIMATE,
        "WARN",
        "M2",
        "MC sampling yields 0 points in Kj",
    ),
    ErrorDescriptor(
        CREErrorCode.EMPTY_HARD_CONSTRAINTS,
        "HALT",
        "M2",
        "compute_phi_ec_bar called with empty list",
    ),
    ErrorDescriptor(
        CREErrorCode.INSUFFICIENT_TRAJECTORIES,
        "HALT",
        "M2",
        "Trajectory list below minimum (30)",
    ),
    ErrorDescriptor(
        CREErrorCode.MISSING_NOMINAL_UTILITY,
        "HALT",
        "M2",
        "Nominal env score missing from utility dict",
    ),
    ErrorDescriptor(
        CREErrorCode.MISSING_ENV_SCORES,
        "HALT",
        "M2",
        "An env ID in spec.E_dep not in score dict",
    ),
    ErrorDescriptor(
        CREErrorCode.SCORE_OUT_OF_RANGE,
        "HALT",
        "M2",
        "A reward or utility score outside [0, 1]",
    ),
    ErrorDescriptor(
        CREErrorCode.SINGLE_ENV_WARN,
        "WARN",
        "M2",
        "Only one environment; gap metrics return 0",
    ),
    ErrorDescriptor(
        CREErrorCode.SINGLE_CONSTRAINT_DIVERSITY,
        "WARN",
        "M2",
        "m = 1; diversity returns 1.0 by convention",
    ),
    ErrorDescriptor(
        CREErrorCode.ZERO_CONSTRAINT_ACTIVATIONS,
        "WARN",
        "M2",
        "All p_j = 0; diversity returns 0.0",
    ),
    ErrorDescriptor(
        CREErrorCode.KJ_EMPTY_WARN,
        "WARN",
        "M2/M3",
        "Kj contains no sampled states",
    ),
    ErrorDescriptor(
        CREErrorCode.REWARD_OUT_OF_RANGE,
        "HALT",
        "M2",
        "Normalized reward score outside [0, 1]",
    ),
    ErrorDescriptor(
        CREErrorCode.CANONICAL_VIOLATION_ERROR,
        "HALT",
        "M2/M3/DP",
        "Enhanced or supplementary value written to canonical slot",
    ),
    ErrorDescriptor(
        CREErrorCode.GRADIENT_UNAVAILABLE,
        "HALT",
        "M3",
        "Policy has no differentiable parameters",
    ),
    ErrorDescriptor(
        CREErrorCode.SIM_MODEL_NOT_FITTED,
        "HALT",
        "M3",
        "Bisimulation model not yet trained",
    ),
    ErrorDescriptor(
        CREErrorCode.LATENT_INCONSISTENCY,
        "WARN",
        "DP",
        "Case A triggered; uncertainty interval expanded",
    ),
    ErrorDescriptor(
        CREErrorCode.CRITIC_QUALITY_WARN,
        "WARN",
        "DP",
        "Case B triggered; critic/gradient estimator may be unreliable",
    ),
    ErrorDescriptor(
        CREErrorCode.POINT_ESTIMATE_MUTATED,
        "HALT",
        "DP",
        "Case handler modified a canonical estimator value",
    ),
    ErrorDescriptor(
        CREErrorCode.M6_HYPOTHESIS_UNAVAILABLE,
        "WARN",
        "DP",
        "M6 (LLMg) exhausted retries; temporal hypothesis skipped",
    ),
    ErrorDescriptor(
        CREErrorCode.SEMANTIC_OVERWRITE_ERROR,
        "HALT",
        "M4",
        "M4 modified a numerical field of DiagReport",
    ),
    ErrorDescriptor(
        CREErrorCode.EMPTY_REPAIR_TARGETS,
        "WARN",
        "M4",
        "LLM returned empty repair-target list",
    ),
    ErrorDescriptor(
        CREErrorCode.TRANSFORM_INPUT_OUT_OF_RANGE,
        "HALT",
        "M5",
        "x not in [0, 1] passed to f(.)",
    ),
    ErrorDescriptor(
        CREErrorCode.TRANSFORM_K_NON_POSITIVE,
        "HALT",
        "M5",
        "Steepness k <= 0",
    ),
    ErrorDescriptor(
        CREErrorCode.TRANSFORM_X0_BOUNDARY,
        "HALT",
        "M5",
        "Inflection x0 not in (0, 1)",
    ),
    ErrorDescriptor(
        CREErrorCode.REPORTER_OUT_OF_RANGE,
        "HALT",
        "M5",
        "Canonical reporter value outside [0, 1]",
    ),
    ErrorDescriptor(
        CREErrorCode.CONFIG_WEIGHT_SUM_ERROR,
        "HALT",
        "M5/PO",
        "|wCR + wEC + wER - 1| > 1e-9",
    ),
    ErrorDescriptor(
        CREErrorCode.INSUFFICIENT_BOOTSTRAP_SAMPLES,
        "HALT",
        "M5",
        "B < 100",
    ),
    ErrorDescriptor(
        CREErrorCode.CI_INVERSION_WARN,
        "WARN",
        "M5",
        "Bootstrap lower > upper; values swapped",
    ),
    ErrorDescriptor(
        CREErrorCode.THRESHOLD_ORDER_VIOLATED,
        "HALT",
        "M5",
        "k_a <= k_d; ordering constraint violated",
    ),
    ErrorDescriptor(
        CREErrorCode.SMALL_CALIBRATION_CORPUS,
        "WARN",
        "M5",
        "Calibration corpus < 30 consistent specs",
    ),
    ErrorDescriptor(
        CREErrorCode.INVALID_AGGREGATION_MODE,
        "HALT",
        "M5",
        'ec_aggregation_mode not in {"mean","min"}',
    ),
    ErrorDescriptor(
        CREErrorCode.UNRELATED_SPECS,
        "HALT",
        "M7",
        "Specs have unrelated spec_ids",
    ),
    ErrorDescriptor(
        CREErrorCode.EDIT_DISTANCE_NEGATIVE,
        "WARN",
        "M7",
        "Underflow; value clipped to 0",
    ),
    ErrorDescriptor(
        CREErrorCode.UNKNOWN_OPERATOR,
        "WARN",
        "M7",
        "Proposal references operator outside V_R; proposal discarded",
    ),
    ErrorDescriptor(
        CREErrorCode.MISSING_SIDE_EFFECTS_DECLARATION,
        "WARN",
        "M7",
        "Proposal lacks declared_side_effects; discarded",
    ),
    ErrorDescriptor(
        CREErrorCode.JUSTIFICATION_TRUNCATED,
        "WARN",
        "M7",
        "Justification > 200 tokens; truncated",
    ),
    ErrorDescriptor(
        CREErrorCode.NO_PROPOSALS_GENERATED,
        "HALT",
        "M7",
        "Zero valid proposals after all retries",
    ),
    ErrorDescriptor(
        CREErrorCode.PROPOSAL_REJECTED_MINIMALITY,
        "WARN",
        "M7/M8",
        "d_spec > eta_edit; proposal discarded",
    ),
    ErrorDescriptor(
        CREErrorCode.LLM_ONLY_MODE_SAFETY_CRITICAL,
        "WARN",
        "M7",
        "LLM-only ranking in safety-critical mode",
    ),
    ErrorDescriptor(
        CREErrorCode.ROUGH_SCORE_UNAVAILABLE,
        "WARN",
        "M7",
        "Rollout failed; proposal ranked last",
    ),
    ErrorDescriptor(
        CREErrorCode.PROPOSAL_REJECTED_DIAGNOSTIC,
        "WARN",
        "M8",
        "C1 fails: Psi'_CRE <= Psi_CRE",
    ),
    ErrorDescriptor(
        CREErrorCode.PROPOSAL_REJECTED_SAFETY,
        "WARN",
        "M8",
        "C2 fails: safety regression",
    ),
    ErrorDescriptor(
        CREErrorCode.PROPOSAL_REJECTED_UTILITY,
        "WARN",
        "M8",
        "C3 fails: utility drop > eps_perf",
    ),
    ErrorDescriptor(
        CREErrorCode.SEM_SCORE_OUT_OF_RANGE,
        "WARN",
        "M8",
        "LLM s_sem outside [0, 1]; clipped",
    ),
    ErrorDescriptor(
        CREErrorCode.DEPARSING_FAILURE,
        "HALT",
        "M8",
        "spec_prime cannot be serialized to NL",
    ),
    ErrorDescriptor(
        CREErrorCode.HARD_REJECT,
        "WARN",
        "M8",
        "Repair loop exhausted N_max iterations",
    ),
    ErrorDescriptor(
        CREErrorCode.NO_PROPOSALS_AFTER_FILTER,
        "WARN",
        "M8",
        "All proposals in an iteration removed by minimality filter",
    ),
    ErrorDescriptor(
        CREErrorCode.LLM_RETRY_EXHAUSTED,
        "HALT",
        "All LLM",
        "All retries exhausted",
    ),
    ErrorDescriptor(
        CREErrorCode.PRECHECK_FATAL,
        "HALT",
        "M1",
        "Generic pre-check fatal wrapper",
    ),
)


def test_nlinput_contract_is_frozen() -> None:
    """T-NL-1: NLInput must be exposed as a frozen canonical schema."""

    assert is_dataclass(NLInput)
    assert NLInput.__dataclass_params__.frozen is True


def test_nlinput_contract_construction() -> None:
    """T-NL-2: NLInput exposes the four Part II §1.2 p.21 fields."""

    nl_input = _build_nlinput()
    assert [field.name for field in fields(NLInput)] == [
        "r_desc",
        "c_desc",
        "e_desc",
        "metadata",
    ]
    assert nl_input.r_desc == "maximize progress toward the goal"
    assert nl_input.c_desc == "avoid collisions and stay within workspace limits"
    assert nl_input.e_desc == "indoor cluttered navigation with dynamic obstacles"
    assert dict(nl_input.metadata) == {"source": "manual-yaml-bootstrap"}
    with pytest.raises(TypeError):
        nl_input.metadata["source"] = "mutated"


def test_nlinput_contract_rejects_missing_required_fields() -> None:
    """T-NL-3: Missing canonical NLInput fields must fail construction."""

    with pytest.raises(TypeError):
        NLInput(
            r_desc="reward",
            c_desc="constraint",
            e_desc="environment",
        )


@pytest.mark.parametrize("field_name", ["r_desc", "c_desc", "e_desc"])
def test_nlinput_contract_rejects_blank_required_descriptions(
    field_name: str,
) -> None:
    """T-NL-4: reward/constraint/environment descriptions are required and non-empty."""

    kwargs = {
        "r_desc": "reward",
        "c_desc": "constraint",
        "e_desc": "environment",
        "metadata": {},
    }
    kwargs[field_name] = "   "

    with pytest.raises(ValueError, match=f"{field_name} must be non-empty"):
        NLInput(**kwargs)


def test_nlinput_contract_rejects_invalid_field_types() -> None:
    """T-NL-5: Field types must match the canonical schema."""

    with pytest.raises(TypeError, match="r_desc must be a string"):
        NLInput(
            r_desc=123,
            c_desc="constraint",
            e_desc="environment",
            metadata={},
        )

    with pytest.raises(TypeError, match="metadata must be a dict"):
        NLInput(
            r_desc="reward",
            c_desc="constraint",
            e_desc="environment",
            metadata=[],
        )


def test_nlinput_contract_immutable_instance() -> None:
    """T-NL-6: Frozen NLInput rejects attribute reassignment."""

    nl_input = _build_nlinput()
    with pytest.raises(FrozenInstanceError):
        nl_input.r_desc = "changed"


def test_constraint_contract_is_frozen() -> None:
    """T-C-1: Constraint must be exposed as a frozen canonical schema."""

    assert is_dataclass(Constraint)
    assert Constraint.__dataclass_params__.frozen is True


def test_constraint_contract_construction() -> None:
    """T-C-2: Constraint exposes the Part II §1.2 p.22 fields."""

    constraint = _build_constraint()
    assert [field.name for field in fields(Constraint)] == [
        "k_id",
        "predicate",
        "sigma",
        "scope",
        "zeta",
        "lam",
        "delta",
    ]
    assert constraint.k_id == "C1"
    assert callable(constraint.predicate)
    assert constraint.sigma == "hard"
    assert constraint.scope == "instantaneous"
    assert constraint.zeta is None
    assert constraint.lam is None
    assert abs(constraint.delta - 0.1) < 1e-9


def test_constraint_contract_rejects_blank_k_id() -> None:
    """T-C-3: k_id must be a non-empty unique-style identifier."""

    with pytest.raises(ValueError, match="k_id must be non-empty"):
        _build_constraint(k_id="   ")


def test_constraint_contract_rejects_non_callable_predicate() -> None:
    """T-C-4: predicate must satisfy the callable O_j: S×A -> {0,1} contract."""

    with pytest.raises(TypeError, match="predicate must be callable"):
        _build_constraint(predicate="not-callable")


@pytest.mark.parametrize("sigma", ["", "warn", 1])
def test_constraint_contract_rejects_invalid_sigma(sigma: object) -> None:
    """T-C-5: sigma must lie in {hard, soft, info}."""

    with pytest.raises(ValueError, match="sigma must be one of"):
        _build_constraint(sigma=sigma)


@pytest.mark.parametrize("scope", ["", "global", 1])
def test_constraint_contract_rejects_invalid_scope(scope: object) -> None:
    """T-C-6: scope must lie in the canonical temporal-scope enum."""

    with pytest.raises(ValueError, match="scope must be one of"):
        _build_constraint(scope=scope)


def test_constraint_contract_requires_zeta_for_soft_constraints() -> None:
    """T-C-7: zeta is required iff sigma == soft."""

    with pytest.raises(ValueError, match="soft constraints require zeta"):
        _build_constraint(sigma="soft", zeta=None)

    constraint = _build_constraint(sigma="soft", zeta=0.2, lam=1.5)
    assert constraint.zeta is not None
    assert constraint.lam is not None
    assert abs(constraint.zeta - 0.2) < 1e-9
    assert abs(constraint.lam - 1.5) < 1e-9


def test_constraint_contract_rejects_soft_only_fields_for_non_soft_constraints() -> None:
    """T-C-8: zeta/lam must remain unset for non-soft constraints."""

    with pytest.raises(ValueError, match="non-soft constraints must set zeta=None"):
        _build_constraint(sigma="hard", zeta=0.1)

    with pytest.raises(ValueError, match="non-soft constraints must set lam=None"):
        _build_constraint(sigma="info", lam=1.0)


def test_constraint_contract_rejects_invalid_numeric_fields() -> None:
    """T-C-9: delta must be positive and optional numeric fields must be numeric."""

    with pytest.raises(ValueError, match="delta must be > 0"):
        _build_constraint(delta=0.0)

    with pytest.raises(TypeError, match="delta must be a real number"):
        _build_constraint(delta="0.1")

    with pytest.raises(TypeError, match="zeta must be a real number"):
        _build_constraint(sigma="soft", zeta="0.2")

    with pytest.raises(TypeError, match="lam must be a real number"):
        _build_constraint(sigma="soft", zeta=0.2, lam="1.0")


def test_constraint_contract_immutable_instance() -> None:
    """T-C-10: Frozen Constraint rejects attribute reassignment."""

    constraint = _build_constraint()
    with pytest.raises(FrozenInstanceError):
        constraint.delta = 0.2


def test_ambiguity_flag_contract_is_frozen() -> None:
    """T-AF-1: AmbiguityFlag must be exposed as a frozen canonical schema."""

    assert is_dataclass(AmbiguityFlag)
    assert AmbiguityFlag.__dataclass_params__.frozen is True


def test_ambiguity_flag_contract_construction() -> None:
    """T-AF-2: AmbiguityFlag exposes the Part II §1.2 p.22 fields."""

    flag = _build_ambiguity_flag()
    assert [field.name for field in fields(AmbiguityFlag)] == [
        "flag_type",
        "location",
        "impact_score",
    ]
    assert flag.flag_type == "UNDEFINED_THRESHOLD"
    assert flag.location == "R.nodes.0.clip_bounds.max"
    assert abs(flag.impact_score - 0.5) < 1e-9


@pytest.mark.parametrize(
    "flag_type",
    ["", "UNKNOWN_FLAG", 1],
)
def test_ambiguity_flag_contract_rejects_invalid_flag_type(flag_type: object) -> None:
    """T-AF-3: flag_type must lie in the canonical ambiguity enum."""

    with pytest.raises(ValueError, match="flag_type must be one of"):
        _build_ambiguity_flag(flag_type=flag_type)


@pytest.mark.parametrize("location", ["", "   "])
def test_ambiguity_flag_contract_rejects_blank_location(location: str) -> None:
    """T-AF-4: location must be a non-empty dot-separated path."""

    with pytest.raises(ValueError, match="location must be non-empty"):
        _build_ambiguity_flag(location=location)


def test_ambiguity_flag_contract_rejects_invalid_field_types_or_ranges() -> None:
    """T-AF-5: location type and impact_score numeric range must match the schema."""

    with pytest.raises(TypeError, match="location must be a string"):
        _build_ambiguity_flag(location=123)

    with pytest.raises(TypeError, match="impact_score must be a real number"):
        _build_ambiguity_flag(impact_score="0.5")

    with pytest.raises(ValueError, match="impact_score must be in \\[0, 1\\]"):
        _build_ambiguity_flag(impact_score=-0.1)

    with pytest.raises(ValueError, match="impact_score must be in \\[0, 1\\]"):
        _build_ambiguity_flag(impact_score=1.1)


@pytest.mark.parametrize("location", [".R.nodes", "R.nodes.", "R..nodes", "R. .nodes"])
def test_ambiguity_flag_contract_rejects_malformed_dot_paths(location: str) -> None:
    """T-AF-6: location must be a well-formed dot-separated JSON path within SpecS."""

    with pytest.raises(ValueError, match="location must be a dot-separated JSON path"):
        _build_ambiguity_flag(location=location)


def test_ambiguity_flag_contract_immutable_instance() -> None:
    """T-AF-7: Frozen AmbiguityFlag rejects attribute reassignment."""

    flag = _build_ambiguity_flag()
    with pytest.raises(FrozenInstanceError):
        flag.location = "C.0.delta"


def test_ambiguity_flag_contract_has_pdf_anchor_comment() -> None:
    """T-AF-8: AmbiguityFlag implementation must retain the PDF anchor comment."""

    source = inspect.getsource(AmbiguityFlag.__post_init__)
    assert "# CRE_v4 Eq.(N/A) Part II §1.2 p.22" in source


def test_diag_report_contract_is_frozen() -> None:
    """T-DR-1: DiagReport must be exposed as a frozen canonical schema."""

    assert is_dataclass(DiagReport)
    assert DiagReport.__dataclass_params__.frozen is True


def test_diag_report_contract_construction() -> None:
    """T-DR-2: DiagReport exposes the Part II §1.2 pp.22-23 fields."""

    report = _build_diag_report()
    assert [field.name for field in fields(DiagReport)] == [
        "spec_id",
        "timestamp",
        "phi_cr2",
        "phi_ec_bar",
        "phi_er3",
        "phi_cr1",
        "phi_ec2",
        "phi_ec3",
        "phi_ec_per_j",
        "phi_er1",
        "phi_er2",
        "kappa_cr",
        "gamma_ec",
        "delta_er",
        "psi_cre",
        "ci_95",
        "flags",
        "discrepancy",
        "failure_hypothesis",
        "repair_targets",
    ]
    assert report.spec_id == "spec-001"
    assert report.timestamp == "2026-04-14T10:30:00Z"
    assert abs(report.phi_cr2 - 0.8) < 1e-9
    assert abs(report.phi_ec_bar - 0.75) < 1e-9
    assert abs(report.phi_er3 - 0.7) < 1e-9
    assert abs(report.psi_cre - 0.76) < 1e-9
    assert report.phi_cr1 is None
    assert report.phi_ec2 is None
    assert report.phi_ec3 is None
    assert report.phi_ec_per_j is None
    assert report.phi_er1 is None
    assert report.phi_er2 is None
    assert report.kappa_cr is None
    assert report.gamma_ec is None
    assert report.delta_er is None
    assert report.ci_95 == {"phi_cr2": (0.72, 0.88), "psi_cre": (0.68, 0.84)}
    assert report.flags == ["WARN_REWARD_SPARSE"]
    assert report.discrepancy == [DiscrepancyRecord()]
    assert report.failure_hypothesis is None
    assert report.repair_targets is None


@pytest.mark.parametrize("field_name", ["spec_id", "timestamp"])
def test_diag_report_contract_rejects_blank_required_strings(field_name: str) -> None:
    """T-DR-3: spec_id and timestamp must be non-empty strings."""

    with pytest.raises(ValueError, match=f"{field_name} must be non-empty"):
        _build_diag_report(**{field_name: "   "})


@pytest.mark.parametrize("timestamp", ["2026/04/14", "not-a-timestamp"])
def test_diag_report_contract_rejects_non_iso8601_timestamp(timestamp: str) -> None:
    """T-DR-4: timestamp must satisfy the ISO 8601 string contract."""

    with pytest.raises(ValueError, match="timestamp must be ISO 8601"):
        _build_diag_report(timestamp=timestamp)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("phi_cr2", -0.1),
        ("phi_ec_bar", 1.1),
        ("phi_er3", 2.0),
        ("psi_cre", -0.01),
    ],
)
def test_diag_report_contract_rejects_canonical_reporters_out_of_range(
    field_name: str,
    value: float,
) -> None:
    """T-DR-5: canonical reporters and psi_cre must remain in [0,1]."""

    with pytest.raises(ValueError, match=rf"{field_name} must be in \[0, 1\]"):
        _build_diag_report(**{field_name: value})


def test_diag_report_contract_accepts_none_for_optional_reporters() -> None:
    """T-DR-6: supplementary and enhanced reporters may be None when skipped."""

    report = _build_diag_report(
        phi_cr1=None,
        phi_ec2=None,
        phi_ec3=None,
        phi_ec_per_j=None,
        phi_er1=None,
        phi_er2=None,
        kappa_cr=None,
        gamma_ec=None,
        delta_er=None,
        discrepancy=None,
        failure_hypothesis=None,
        repair_targets=None,
    )
    assert report.phi_cr1 is None
    assert report.phi_ec2 is None
    assert report.phi_ec3 is None
    assert report.phi_ec_per_j is None
    assert report.phi_er1 is None
    assert report.phi_er2 is None
    assert report.kappa_cr is None
    assert report.gamma_ec is None
    assert report.delta_er is None
    assert report.discrepancy is None
    assert report.failure_hypothesis is None
    assert report.repair_targets is None


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("phi_cr1", "0.4"),
        ("phi_ec2", "0.5"),
        ("phi_ec3", object()),
        ("phi_er1", "0.6"),
        ("phi_er2", object()),
        ("kappa_cr", "0.3"),
        ("gamma_ec", object()),
        ("delta_er", "0.2"),
    ],
)
def test_diag_report_contract_rejects_invalid_optional_numeric_fields(
    field_name: str,
    value: object,
) -> None:
    """T-DR-7: optional numeric reporters must be real numbers when present."""

    with pytest.raises(TypeError, match=rf"{field_name} must be a real number"):
        _build_diag_report(**{field_name: value})


def test_diag_report_contract_rejects_invalid_phi_ec_per_j_values() -> None:
    """T-DR-8: phi_ec_per_j must be a numeric list when present."""

    with pytest.raises(TypeError, match="phi_ec_per_j must be a list\\[float\\]"):
        _build_diag_report(phi_ec_per_j=(0.5, 0.7))

    with pytest.raises(TypeError, match="phi_ec_per_j entries must be real numbers"):
        _build_diag_report(phi_ec_per_j=[0.5, "0.7"])


def test_diag_report_contract_rejects_invalid_ci_95_structure() -> None:
    """T-DR-9: ci_95 must use canonical reporter names and two-float tuples."""

    with pytest.raises(TypeError, match="ci_95 must be a dict\\[str, tuple\\[float, float\\]\\]"):
        _build_diag_report(ci_95=[("phi_cr2", (0.1, 0.2))])

    with pytest.raises(TypeError, match="ci_95 keys must be strings"):
        _build_diag_report(ci_95={1: (0.1, 0.2)})

    with pytest.raises(TypeError, match="ci_95 values must be \\(float, float\\) tuples"):
        _build_diag_report(ci_95={"phi_cr2": [0.1, 0.2]})

    with pytest.raises(TypeError, match="ci_95 interval bounds must be real numbers"):
        _build_diag_report(ci_95={"phi_cr2": ("0.1", 0.2)})

    with pytest.raises(
        ValueError, match="ci_95 keys must be canonical reporter names"
    ):
        _build_diag_report(ci_95={"not_a_reporter": (0.1, 0.2)})


def test_diag_report_contract_rejects_invalid_flags_or_discrepancy_types() -> None:
    """T-DR-10: flags and discrepancy must match the canonical container types."""

    with pytest.raises(TypeError, match="flags must be a list\\[str\\]"):
        _build_diag_report(flags=("WARN",))

    with pytest.raises(TypeError, match="flags entries must be strings"):
        _build_diag_report(flags=["WARN", 1])

    with pytest.raises(TypeError, match="discrepancy must be a list\\[DiscrepancyRecord\\] or None"):
        _build_diag_report(discrepancy=("not", "a", "list"))

    with pytest.raises(TypeError, match="discrepancy entries must be DiscrepancyRecord instances"):
        _build_diag_report(discrepancy=["not-a-record"])


def test_diag_report_contract_rejects_invalid_failure_hypothesis_or_repair_targets() -> None:
    """T-DR-11: M4-populated metadata fields must respect string/list contracts."""

    with pytest.raises(ValueError, match="failure_hypothesis must be non-empty when provided"):
        _build_diag_report(failure_hypothesis="   ")

    with pytest.raises(TypeError, match="repair_targets must be a list\\[str\\] or None"):
        _build_diag_report(repair_targets="R.nodes.0.weight")

    with pytest.raises(TypeError, match="repair_targets entries must be strings"):
        _build_diag_report(repair_targets=["R.nodes.0.weight", 1])


def test_diag_report_contract_immutable_instance() -> None:
    """T-DR-12: Frozen DiagReport rejects attribute reassignment."""

    report = _build_diag_report()
    with pytest.raises(FrozenInstanceError):
        report.psi_cre = 0.5


def test_diag_report_contract_has_pdf_anchor_comment() -> None:
    """T-DR-13: DiagReport implementation must retain the PDF anchor comment."""

    source = inspect.getsource(DiagReport.__post_init__)
    assert "# CRE_v4 Eq.(N/A) Part II §1.2 p.23" in source


def test_reward_dag_contract_is_frozen() -> None:
    """T-R-1: RewardDAG must be exposed as a frozen canonical schema."""

    assert is_dataclass(RewardDAG)
    assert RewardDAG.__dataclass_params__.frozen is True


def test_reward_dag_contract_construction_and_read_only_normalization() -> None:
    """T-R-2: RewardDAG exposes canonical nodes/edges and stores them read-only."""

    dag = _build_reward_dag()
    assert [field.name for field in fields(RewardDAG)] == ["nodes", "edges"]
    assert isinstance(dag.nodes, tuple)
    assert isinstance(dag.edges, tuple)
    assert len(dag.nodes) == 1
    assert isinstance(dag.nodes[0], RewardTerm)
    assert dag.edges == (("r_goal", "r_progress"),)


def test_reward_dag_contract_rejects_invalid_nodes_container_or_entries() -> None:
    """T-R-3: nodes must be list[RewardTerm] before immutable normalization."""

    with pytest.raises(TypeError, match="nodes must be a list\\[RewardTerm\\]"):
        _build_reward_dag(nodes=("not", "a", "list"))

    with pytest.raises(TypeError, match="nodes entries must be RewardTerm instances"):
        _build_reward_dag(nodes=["not-a-reward-term"])


def test_reward_dag_contract_rejects_invalid_edges_container_or_entries() -> None:
    """T-R-4: edges must be list[(parent_id, child_id)] string tuples."""

    with pytest.raises(TypeError, match="edges must be a list\\[tuple\\[str, str\\]\\]"):
        _build_reward_dag(edges=(("r1", "r2"),))

    with pytest.raises(
        TypeError, match="edges entries must be \\(str, str\\) tuples"
    ):
        _build_reward_dag(edges=[("r1", 2)])

    with pytest.raises(
        TypeError, match="edges entries must be \\(str, str\\) tuples"
    ):
        _build_reward_dag(edges=[("r1", "r2", "r3")])


def test_reward_dag_contract_immutable_instance_and_nested_containers() -> None:
    """T-R-5: Frozen RewardDAG blocks top-level and nested in-place mutation."""

    dag = _build_reward_dag()
    with pytest.raises(FrozenInstanceError):
        dag.nodes = ()
    with pytest.raises(FrozenInstanceError):
        dag.nodes += (RewardTerm(),)
    with pytest.raises(FrozenInstanceError):
        dag.edges += (("r_progress", "r_terminal"),)


def test_reward_dag_contract_has_pdf_anchor_comment() -> None:
    """T-R-6: RewardDAG implementation must retain the PDF anchor comment."""

    source = inspect.getsource(RewardDAG.__post_init__)
    assert "# CRE_v4 Eq.(N/A) Part II §1.2 p.22" in source


def test_specs_contract_is_frozen() -> None:
    """T-Struct-1: SpecS must be a frozen dataclass (CRE_v4 Part II §1.2 p.22)."""

    assert is_dataclass(SpecS)
    assert SpecS.__dataclass_params__.frozen is True


def test_specs_contract_construction() -> None:
    """T-Struct-2: SpecS exposes canonical fields and defaults (CRE_v4 §1.2 p.22)."""

    spec = _build_specs()
    assert [field.name for field in fields(SpecS)] == [
        "spec_id",
        "E_tr",
        "E_dep",
        "R",
        "C",
        "Pi",
        "version",
    ]
    assert spec.spec_id == "spec-001"
    assert spec.version == 0
    assert len(spec.E_dep) == 1
    assert isinstance(spec.E_dep, tuple)
    assert isinstance(spec.E_tr, TrainingEnvDistribution)
    assert isinstance(spec.R, RewardDAG)
    assert isinstance(spec.R.nodes, tuple)
    assert isinstance(spec.R.edges, tuple)
    assert isinstance(spec.C[0], Constraint)
    assert isinstance(spec.C, tuple)
    assert isinstance(spec.Pi, PolicyClass)


def test_specs_contract_rejects_missing_required_fields() -> None:
    """T-Struct-3: Missing canonical fields must be rejected by construction."""

    with pytest.raises(TypeError):
        SpecS(
            spec_id="spec-001",
            E_tr=TrainingEnvDistribution(),
            E_dep=[Environment()],
            R=RewardDAG(nodes=[RewardTerm()], edges=[]),
            C=[],
        )


def test_specs_contract_rejects_empty_deployment_list() -> None:
    """T-Struct-4: E_dep must contain at least nominal e_0 (CRE_v4 §1.2 p.22)."""

    with pytest.raises(ValueError, match="nominal environment e_0"):
        SpecS(
            spec_id="spec-001",
            E_tr=TrainingEnvDistribution(),
            E_dep=[],
            R=RewardDAG(nodes=[RewardTerm()], edges=[]),
            C=[],
            Pi=PolicyClass(),
        )


def test_specs_contract_immutable_instance() -> None:
    """T-Struct-5: SpecS instances reject top-level field reassignment."""

    spec = _build_specs()
    with pytest.raises(FrozenInstanceError):
        spec.version = 1


def test_specs_contract_rejects_in_place_container_mutation() -> None:
    """T-Struct-6: Read-only contract blocks append/item assignment (CRE_v4 §1.2)."""

    spec = _build_specs()
    with pytest.raises(AttributeError):
        spec.E_dep.append(Environment())
    with pytest.raises(AttributeError):
        spec.C.append(
            Constraint(
                k_id="C2",
                predicate=lambda _state, _action: 0,
                sigma="hard",
                scope="instantaneous",
                zeta=None,
                lam=None,
                delta=0.2,
            )
        )
    with pytest.raises(AttributeError):
        spec.R.nodes.append(RewardTerm())
    with pytest.raises(AttributeError):
        spec.R.edges.append(("parent", "child"))
    with pytest.raises(TypeError):
        spec.E_dep[0] = Environment()
    with pytest.raises(TypeError):
        spec.C[0] = Constraint(
            k_id="C3",
            predicate=lambda _state, _action: 0,
            sigma="hard",
            scope="instantaneous",
            zeta=None,
            lam=None,
            delta=0.3,
        )


def test_repair_proposal_contract_is_frozen() -> None:
    """T-RP-1: RepairProposal must be exposed as a frozen canonical schema."""

    assert is_dataclass(RepairProposal)
    assert RepairProposal.__dataclass_params__.frozen is True


def test_repair_proposal_contract_construction() -> None:
    """T-RP-2: RepairProposal exposes the Part II §1.2 p.23 fields."""

    proposal = _build_repair_proposal()
    assert [field.name for field in fields(RepairProposal)] == [
        "proposal_id",
        "spec_prime",
        "operator_class",
        "declared_side_effects",
        "semantic_justification",
        "predicted_delta_psi",
        "rough_delta_psi",
    ]
    assert proposal.proposal_id == "123e4567-e89b-12d3-a456-426614174000"
    assert isinstance(proposal.spec_prime, SpecS)
    assert proposal.operator_class == "ReweightTerms"
    assert dict(proposal.declared_side_effects) == {
        "reward": "May reduce nominal progress while improving safety."
    }
    assert (
        proposal.semantic_justification
        == "Increase safety margin emphasis to reduce collision-seeking behavior."
    )
    assert abs(proposal.predicted_delta_psi - 0.12) < 1e-9
    assert abs(proposal.rough_delta_psi - 0.08) < 1e-9
    with pytest.raises(TypeError):
        proposal.declared_side_effects["reward"] = "mutated"


@pytest.mark.parametrize("field_name", ["proposal_id", "operator_class", "semantic_justification"])
def test_repair_proposal_contract_rejects_blank_required_strings(
    field_name: str,
) -> None:
    """T-RP-3: Required string fields must remain non-empty."""

    with pytest.raises(ValueError, match=f"{field_name} must be non-empty"):
        _build_repair_proposal(**{field_name: "   "})


def test_repair_proposal_contract_requires_uuid_proposal_id() -> None:
    """T-RP-4: proposal_id must be a legal UUID string."""

    with pytest.raises(ValueError, match="proposal_id must be a valid UUID string"):
        _build_repair_proposal(proposal_id="not-a-uuid")


def test_repair_proposal_contract_requires_operator_from_vr_vocabulary() -> None:
    """T-RP-5: operator_class must come from the Part II §8.1.2 V_R vocabulary."""

    with pytest.raises(ValueError, match="operator_class must be one of"):
        _build_repair_proposal(operator_class="DeleteSpec")


def test_repair_proposal_contract_rejects_non_specs_spec_prime() -> None:
    """T-RP-6: spec_prime must remain the canonical SpecS schema."""

    with pytest.raises(TypeError, match="spec_prime must be a SpecS"):
        _build_repair_proposal(spec_prime={"spec_id": "spec-001"})


def test_repair_proposal_contract_rejects_invalid_declared_side_effects() -> None:
    """T-RP-7: declared_side_effects must be a dict[str, str]."""

    with pytest.raises(TypeError, match="declared_side_effects must be a dict\\[str, str\\]"):
        _build_repair_proposal(declared_side_effects=[("reward", "desc")])

    with pytest.raises(TypeError, match="declared_side_effects keys must be strings"):
        _build_repair_proposal(declared_side_effects={1: "desc"})

    with pytest.raises(
        TypeError, match="declared_side_effects values must be strings"
    ):
        _build_repair_proposal(declared_side_effects={"reward": 1})


def test_repair_proposal_contract_rejects_justification_over_token_limit() -> None:
    """T-RP-8: semantic_justification must not exceed the 200-token PDF limit."""

    over_limit_text = " ".join(f"tok{i}" for i in range(201))

    with pytest.raises(
        ValueError, match="semantic_justification must contain at most 200 tokens"
    ):
        _build_repair_proposal(semantic_justification=over_limit_text)


def test_repair_proposal_contract_accepts_none_for_optional_delta_fields() -> None:
    """T-RP-9: predicted_delta_psi and rough_delta_psi may be None before ranking."""

    proposal = _build_repair_proposal(
        predicted_delta_psi=None,
        rough_delta_psi=None,
    )
    assert proposal.predicted_delta_psi is None
    assert proposal.rough_delta_psi is None


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("predicted_delta_psi", "0.12"),
        ("predicted_delta_psi", object()),
        ("rough_delta_psi", "0.08"),
        ("rough_delta_psi", object()),
    ],
)
def test_repair_proposal_contract_rejects_invalid_optional_numeric_fields(
    field_name: str,
    value: object,
) -> None:
    """T-RP-10: optional delta fields must be real numbers when present."""

    with pytest.raises(TypeError, match=rf"{field_name} must be a real number"):
        _build_repair_proposal(**{field_name: value})


def test_repair_proposal_contract_immutable_instance() -> None:
    """T-RP-11: Frozen RepairProposal rejects attribute reassignment."""

    proposal = _build_repair_proposal()
    with pytest.raises(FrozenInstanceError):
        proposal.operator_class = "env.shift"


def test_repair_proposal_contract_has_pdf_anchor_comment() -> None:
    """T-RP-12: RepairProposal implementation must retain the PDF anchor comment."""

    source = inspect.getsource(RepairProposal.__post_init__)
    assert "# CRE_v4 Eq.(N/A) Part II §1.2 p.23" in source


def test_acceptance_verdict_contract_is_frozen() -> None:
    """T-AV-1: AcceptanceVerdict must be exposed as a frozen canonical schema."""

    assert is_dataclass(AcceptanceVerdict)
    assert AcceptanceVerdict.__dataclass_params__.frozen is True


def test_acceptance_verdict_contract_construction() -> None:
    """T-AV-2: AcceptanceVerdict exposes the Part II §1.2 p.23 fields."""

    verdict = _build_acceptance_verdict()
    assert [field.name for field in fields(AcceptanceVerdict)] == [
        "accepted",
        "c1_pass",
        "c2_pass",
        "c3_pass",
        "c4_pass",
        "s_sem",
        "intent_preserved",
        "rejection_feedback",
    ]
    assert verdict.accepted is True
    assert verdict.c1_pass is True
    assert verdict.c2_pass is True
    assert verdict.c3_pass is True
    assert verdict.c4_pass is True
    assert abs(verdict.s_sem - 0.8) < 1e-9
    assert verdict.intent_preserved is True
    assert verdict.rejection_feedback is None


@pytest.mark.parametrize(
    "field_name",
    ["accepted", "c1_pass", "c2_pass", "c3_pass", "c4_pass", "intent_preserved"],
)
def test_acceptance_verdict_contract_requires_bool_flags(field_name: str) -> None:
    """T-AV-3: acceptance and criterion flags must be strict bool values."""

    with pytest.raises(TypeError, match=rf"{field_name} must be a bool"):
        _build_acceptance_verdict(**{field_name: 1})


@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_acceptance_verdict_contract_rejects_out_of_range_s_sem(value: float) -> None:
    """T-AV-4: s_sem must remain in [0,1]."""

    with pytest.raises(ValueError, match="s_sem must be in \\[0, 1\\]"):
        _build_acceptance_verdict(s_sem=value)


def test_acceptance_verdict_contract_rejects_invalid_s_sem_type() -> None:
    """T-AV-5: s_sem must be a real number."""

    with pytest.raises(TypeError, match="s_sem must be a real number"):
        _build_acceptance_verdict(s_sem="0.8")


def test_acceptance_verdict_contract_rejects_invalid_rejection_feedback_type() -> None:
    """T-AV-6: rejection_feedback must be str | None."""

    with pytest.raises(TypeError, match="rejection_feedback must be a string or None"):
        _build_acceptance_verdict(rejection_feedback=1)


def test_acceptance_verdict_contract_immutable_instance() -> None:
    """T-AV-7: Frozen AcceptanceVerdict rejects attribute reassignment."""

    verdict = _build_acceptance_verdict()
    with pytest.raises(FrozenInstanceError):
        verdict.accepted = False


def test_acceptance_verdict_contract_has_pdf_anchor_comment() -> None:
    """T-AV-8: AcceptanceVerdict implementation must retain the PDF anchor comment."""

    source = inspect.getsource(AcceptanceVerdict.__post_init__)
    assert "# CRE_v4 Eq.(N/A) Part II §1.2 p.23" in source


def test_cfg_contract_is_frozen() -> None:
    """T-CFG-1: CFGSchema must be exposed as a frozen canonical schema."""

    assert is_dataclass(CFGSchema)
    assert CFGSchema.__dataclass_params__.frozen is True


def test_cfg_contract_construction_and_defaults() -> None:
    """T-CFG-2: CFGSchema exposes the full Part II §1.3 Table 4 field set and defaults."""

    cfg = _build_cfg()
    assert [field.name for field in fields(CFGSchema)] == [
        "eta_flag",
        "llm_retry_limit",
        "delta_j_default",
        "n_ref_traj",
        "n_mc_kj",
        "critical_region_radius",
        "ec_aggregation_mode",
        "eps_stab",
        "enhanced_estimators_enabled",
        "eta_disc",
        "tau_low",
        "tau_high",
        "lambda_expand",
        "n_rechk",
        "f_steepness",
        "f_inflection",
        "w_cr",
        "w_ec",
        "w_er",
        "b_bootstrap",
        "k_detect",
        "k_alarm",
        "tau_alarm_psi",
        "k_proposals",
        "eta_edit",
        "n_rank_episodes",
        "eps_rank",
        "ranking_mode",
        "tau_sem",
        "eps_perf",
        "n_max_iterations",
    ]
    assert abs(cfg.eta_flag - 0.15) < 1e-9
    assert cfg.llm_retry_limit == 3
    assert abs(cfg.delta_j_default - 0.50) < 1e-9
    assert cfg.n_ref_traj == 500
    assert cfg.n_mc_kj == 1000
    assert abs(cfg.critical_region_radius - 0.10) < 1e-9
    assert cfg.ec_aggregation_mode == "mean"
    assert abs(cfg.eps_stab - 1e-6) < 1e-12
    assert cfg.enhanced_estimators_enabled is True
    assert abs(cfg.eta_disc - 0.15) < 1e-9
    assert abs(cfg.tau_low - 0.30) < 1e-9
    assert abs(cfg.tau_high - 0.70) < 1e-9
    assert abs(cfg.lambda_expand - 0.50) < 1e-9
    assert cfg.n_rechk == 1
    assert abs(cfg.f_steepness - 8.0) < 1e-9
    assert abs(cfg.f_inflection - 0.50) < 1e-9
    assert abs(cfg.w_cr - 0.333) < 1e-12
    assert abs(cfg.w_ec - 0.333) < 1e-12
    assert abs(cfg.w_er - 0.334) < 1e-12
    assert abs(cfg.w_cr + cfg.w_ec + cfg.w_er - 1.0) < 1e-9
    assert cfg.b_bootstrap == 1000
    assert abs(cfg.k_detect - 1.5) < 1e-9
    assert abs(cfg.k_alarm - 3.0) < 1e-9
    assert abs(cfg.tau_alarm_psi - 0.75) < 1e-9
    assert cfg.k_proposals == 3
    assert abs(cfg.eta_edit - 0.20) < 1e-9
    assert cfg.n_rank_episodes == 50
    assert abs(cfg.eps_rank - 0.02) < 1e-9
    assert cfg.ranking_mode == "rollout_first"
    assert abs(cfg.tau_sem - 0.80) < 1e-9
    assert abs(cfg.eps_perf - 0.05) < 1e-9
    assert cfg.n_max_iterations == 5


def test_cfg_contract_exposes_module_singleton() -> None:
    """T-CFG-3: analyzers.cfg must expose a module-level CFG singleton."""

    assert isinstance(CFG, CFGSchema)
    assert CFG == _build_cfg()


def test_cfg_contract_rejects_invalid_ec_aggregation_mode() -> None:
    """T-CFG-4: ec_aggregation_mode must remain within the canonical mean|min modes."""

    with pytest.raises(
        ValueError, match='ec_aggregation_mode must be "mean" or "min"'
    ):
        _build_cfg(ec_aggregation_mode="median")


def test_cfg_contract_requires_bool_enhanced_estimators_enabled() -> None:
    """T-CFG-5: enhanced_estimators_enabled must be a strict bool."""

    with pytest.raises(
        TypeError, match="enhanced_estimators_enabled must be a bool"
    ):
        _build_cfg(enhanced_estimators_enabled=1)


def test_cfg_contract_rejects_weight_sum_violation() -> None:
    """T-CFG-6: invalid Table 4 weight sums must raise CONFIG_WEIGHT_SUM_ERROR."""

    with pytest.raises(ValueError, match=CONFIG_WEIGHT_SUM_ERROR):
        _build_cfg(w_cr=0.5, w_ec=0.5, w_er=0.5)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [("w_cr", 0.0), ("w_ec", -0.1), ("w_er", 0.0)],
)
def test_cfg_contract_rejects_non_positive_weights(
    field_name: str,
    value: float,
) -> None:
    """T-CFG-7: all three PsiCRE weights must be strictly positive."""

    with pytest.raises(ValueError, match=CONFIG_WEIGHT_SUM_ERROR):
        _build_cfg(**{field_name: value})


def test_cfg_contract_rejects_non_positive_count_fields() -> None:
    """T-CFG-8: Table 4 sampling / iteration counts must stay positive integers."""

    with pytest.raises(ValueError, match="n_ref_traj must be a positive integer"):
        _build_cfg(n_ref_traj=0)

    with pytest.raises(ValueError, match="b_bootstrap must be a positive integer"):
        _build_cfg(b_bootstrap=0)


def test_cfg_contract_immutable_instance() -> None:
    """T-CFG-9: Frozen CFGSchema rejects attribute reassignment."""

    cfg = _build_cfg()
    with pytest.raises(FrozenInstanceError):
        cfg.w_cr = 0.5


def test_cfg_contract_has_pdf_anchor_comment() -> None:
    """T-CFG-10: CFGSchema implementation must retain the PDF anchor comment."""

    source = inspect.getsource(CFGSchema.__post_init__)
    assert "# CRE_v4 Eq.(N/A) Part II §1.3 Table 4 p.23-24" in source


def test_cre_error_contract_base_class_surface() -> None:
    """T-ERR-1: CREError is the canonical base type for all CRE error codes."""

    assert issubclass(CREError, ValueError)
    err = ConfigWeightSumError()
    assert isinstance(err, CREError)
    assert err.error_code == CREErrorCode.CONFIG_WEIGHT_SUM_ERROR
    assert err.severity == "HALT"
    assert err.module == "M5/PO"


def test_cre_error_contract_code_constants_are_complete_and_unique() -> None:
    """T-ERR-2: Table 5 codes remain unique string constants on CREErrorCode."""

    codes = _error_code_values()
    assert len(codes) == 62
    assert len(set(codes)) == 62
    assert codes == sorted(codes, key=codes.index)
    for name, value in vars(CREErrorCode).items():
        if name.isupper() and not name.startswith("_"):
            assert value == name


def test_cre_error_contract_registry_covers_all_codes() -> None:
    """T-ERR-3: ERROR_REGISTRY must provide a descriptor for every Table 5 code."""

    codes = set(_error_code_values())
    assert set(ERROR_REGISTRY) == codes
    assert all(isinstance(descriptor, ErrorDescriptor) for descriptor in ERROR_REGISTRY.values())


@pytest.mark.parametrize(
    "expected_row",
    TABLE_5_EXPECTED_ROWS,
    ids=[row.error_code for row in TABLE_5_EXPECTED_ROWS],
)
def test_cre_error_contract_registry_rows_match_pdf(expected_row: ErrorDescriptor) -> None:
    """T-ERR-4: every Table 5 row must match the PDF registry verbatim."""

    assert ERROR_REGISTRY[expected_row.error_code] == expected_row


def test_cre_error_contract_exposes_formal_subclass_registry() -> None:
    """T-ERR-5: every Table 5 code must map to a formal CREError subclass."""

    codes = set(_error_code_values())
    assert set(ERROR_CLASS_REGISTRY) == codes
    assert ERROR_CLASS_REGISTRY[CREErrorCode.CONFIG_WEIGHT_SUM_ERROR] is ConfigWeightSumError
    assert all(issubclass(error_cls, CREError) for error_cls in ERROR_CLASS_REGISTRY.values())


def test_config_weight_sum_error_contract_cfg_uses_formal_error_type() -> None:
    """T-ERR-6: CFG weight validation must raise the formal ConfigWeightSumError type."""

    with pytest.raises(ConfigWeightSumError, match=CONFIG_WEIGHT_SUM_ERROR):
        _build_cfg(w_cr=0.5, w_ec=0.5, w_er=0.5)


def test_config_weight_sum_error_contract_accepts_sum_within_tolerance() -> None:
    """T-ERR-7: sums strictly within the 1e-9 tolerance must remain valid."""

    cfg = _build_cfg(w_cr=0.333, w_ec=0.333, w_er=0.3340000005)
    assert abs(cfg.w_cr + cfg.w_ec + cfg.w_er - 1.0) < 1e-9


def test_config_weight_sum_error_contract_rejects_sum_at_or_above_tolerance() -> None:
    """T-ERR-8: sums at or above the 1e-9 tolerance must raise ConfigWeightSumError."""

    weight_sum = 0.333 + 0.333 + 0.3340000011
    assert abs(weight_sum - 1.0) >= 1e-9
    with pytest.raises(ConfigWeightSumError, match=CONFIG_WEIGHT_SUM_ERROR):
        _build_cfg(w_cr=0.333, w_ec=0.333, w_er=0.3340000011)


def test_cre_error_contract_has_pdf_anchor_comment() -> None:
    """T-ERR-9: CREError implementation must retain the PDF anchor comment."""

    source = inspect.getsource(CREError.__init__)
    assert "# CRE_v4 Eq.(N/A) Part II §11 p.49-51" in source
