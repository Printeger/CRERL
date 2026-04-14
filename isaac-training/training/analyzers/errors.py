"""Canonical CRE error surface aligned to CRE_v4 Part II Section 11."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal


CREErrorSeverity = Literal["HALT", "WARN"]


class CREErrorCode:
    """Table 5 string constants.

    # CRE_v4 Eq.(N/A) Part II §11 p.49-51
    """

    SPEC_PARSE_FAILURE = "SPEC_PARSE_FAILURE"
    NULL_REWARD = "NULL_REWARD"
    EMPTY_CONSTRAINT_SET = "EMPTY_CONSTRAINT_SET"
    EMPTY_ENV_SET = "EMPTY_ENV_SET"
    AMBIGUITY_UNRESOLVABLE = "AMBIGUITY_UNRESOLVABLE"
    PRECHECK_TYPE_MISMATCH = "PRECHECK_TYPE_MISMATCH"
    PRECHECK_DOMAIN_TRIVIAL = "PRECHECK_DOMAIN_TRIVIAL"
    PRECHECK_COVERAGE_INSUFFICIENT = "PRECHECK_COVERAGE_INSUFFICIENT"
    PRECHECK_SOFT_NO_TOLERANCE = "PRECHECK_SOFT_NO_TOLERANCE"
    DEGENERATE_CR1_VAR = "DEGENERATE_CR1_VAR"
    BOUNDARY_BASELINE_DEGENERATE = "BOUNDARY_BASELINE_DEGENERATE"
    ER_CORRELATION_DEGENERATE = "ER_CORRELATION_DEGENERATE"
    NO_HARD_CONSTRAINTS = "NO_HARD_CONSTRAINTS"
    WRONG_SEVERITY = "WRONG_SEVERITY"
    EMPTY_KJ_ESTIMATE = "EMPTY_KJ_ESTIMATE"
    EMPTY_HARD_CONSTRAINTS = "EMPTY_HARD_CONSTRAINTS"
    INSUFFICIENT_TRAJECTORIES = "INSUFFICIENT_TRAJECTORIES"
    MISSING_NOMINAL_UTILITY = "MISSING_NOMINAL_UTILITY"
    MISSING_ENV_SCORES = "MISSING_ENV_SCORES"
    SCORE_OUT_OF_RANGE = "SCORE_OUT_OF_RANGE"
    SINGLE_ENV_WARN = "SINGLE_ENV_WARN"
    SINGLE_CONSTRAINT_DIVERSITY = "SINGLE_CONSTRAINT_DIVERSITY"
    ZERO_CONSTRAINT_ACTIVATIONS = "ZERO_CONSTRAINT_ACTIVATIONS"
    KJ_EMPTY_WARN = "KJ_EMPTY_WARN"
    REWARD_OUT_OF_RANGE = "REWARD_OUT_OF_RANGE"
    CANONICAL_VIOLATION_ERROR = "CANONICAL_VIOLATION_ERROR"
    GRADIENT_UNAVAILABLE = "GRADIENT_UNAVAILABLE"
    SIM_MODEL_NOT_FITTED = "SIM_MODEL_NOT_FITTED"
    LATENT_INCONSISTENCY = "LATENT_INCONSISTENCY"
    CRITIC_QUALITY_WARN = "CRITIC_QUALITY_WARN"
    POINT_ESTIMATE_MUTATED = "POINT_ESTIMATE_MUTATED"
    M6_HYPOTHESIS_UNAVAILABLE = "M6_HYPOTHESIS_UNAVAILABLE"
    SEMANTIC_OVERWRITE_ERROR = "SEMANTIC_OVERWRITE_ERROR"
    EMPTY_REPAIR_TARGETS = "EMPTY_REPAIR_TARGETS"
    TRANSFORM_INPUT_OUT_OF_RANGE = "TRANSFORM_INPUT_OUT_OF_RANGE"
    TRANSFORM_K_NON_POSITIVE = "TRANSFORM_K_NON_POSITIVE"
    TRANSFORM_X0_BOUNDARY = "TRANSFORM_X0_BOUNDARY"
    REPORTER_OUT_OF_RANGE = "REPORTER_OUT_OF_RANGE"
    CONFIG_WEIGHT_SUM_ERROR = "CONFIG_WEIGHT_SUM_ERROR"
    INSUFFICIENT_BOOTSTRAP_SAMPLES = "INSUFFICIENT_BOOTSTRAP_SAMPLES"
    CI_INVERSION_WARN = "CI_INVERSION_WARN"
    THRESHOLD_ORDER_VIOLATED = "THRESHOLD_ORDER_VIOLATED"
    SMALL_CALIBRATION_CORPUS = "SMALL_CALIBRATION_CORPUS"
    INVALID_AGGREGATION_MODE = "INVALID_AGGREGATION_MODE"
    UNRELATED_SPECS = "UNRELATED_SPECS"
    EDIT_DISTANCE_NEGATIVE = "EDIT_DISTANCE_NEGATIVE"
    UNKNOWN_OPERATOR = "UNKNOWN_OPERATOR"
    MISSING_SIDE_EFFECTS_DECLARATION = "MISSING_SIDE_EFFECTS_DECLARATION"
    JUSTIFICATION_TRUNCATED = "JUSTIFICATION_TRUNCATED"
    NO_PROPOSALS_GENERATED = "NO_PROPOSALS_GENERATED"
    PROPOSAL_REJECTED_MINIMALITY = "PROPOSAL_REJECTED_MINIMALITY"
    LLM_ONLY_MODE_SAFETY_CRITICAL = "LLM_ONLY_MODE_SAFETY_CRITICAL"
    ROUGH_SCORE_UNAVAILABLE = "ROUGH_SCORE_UNAVAILABLE"
    PROPOSAL_REJECTED_DIAGNOSTIC = "PROPOSAL_REJECTED_DIAGNOSTIC"
    PROPOSAL_REJECTED_SAFETY = "PROPOSAL_REJECTED_SAFETY"
    PROPOSAL_REJECTED_UTILITY = "PROPOSAL_REJECTED_UTILITY"
    SEM_SCORE_OUT_OF_RANGE = "SEM_SCORE_OUT_OF_RANGE"
    DEPARSING_FAILURE = "DEPARSING_FAILURE"
    HARD_REJECT = "HARD_REJECT"
    NO_PROPOSALS_AFTER_FILTER = "NO_PROPOSALS_AFTER_FILTER"
    LLM_RETRY_EXHAUSTED = "LLM_RETRY_EXHAUSTED"
    PRECHECK_FATAL = "PRECHECK_FATAL"


@dataclass(frozen=True)
class ErrorDescriptor:
    """Registry row for a CRE error code.

    # CRE_v4 Eq.(N/A) Part II §11 p.49-51
    """

    error_code: str
    severity: CREErrorSeverity
    module: str
    description: str


class CREError(ValueError):
    """Base class for all CRE errors.

    # CRE_v4 Eq.(N/A) Part II §11 p.49-51
    """

    error_code: ClassVar[str] = "CRE_ERROR"
    severity: ClassVar[CREErrorSeverity] = "HALT"
    module: ClassVar[str] = "CORE"

    def __init__(self, message: str | None = None) -> None:
        # CRE_v4 Eq.(N/A) Part II §11 p.49-51
        descriptor = ERROR_REGISTRY.get(self.error_code)
        resolved_message = message or self.error_code
        super().__init__(resolved_message)
        self.message = resolved_message
        self.descriptor = descriptor


class ConfigWeightSumError(CREError):
    """Formal CONFIG_WEIGHT_SUM_ERROR type.

    # CRE_v4 Eq.(N/A) Part II §11 p.49-51
    """

    error_code: ClassVar[str] = CREErrorCode.CONFIG_WEIGHT_SUM_ERROR
    severity: ClassVar[CREErrorSeverity] = "HALT"
    module: ClassVar[str] = "M5/PO"


_ERROR_ROWS: tuple[ErrorDescriptor, ...] = (
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

ERROR_REGISTRY: dict[str, ErrorDescriptor] = {
    descriptor.error_code: descriptor for descriptor in _ERROR_ROWS
}


def _error_class_name(error_code: str) -> str:
    if error_code == CREErrorCode.CONFIG_WEIGHT_SUM_ERROR:
        return "ConfigWeightSumError"
    return "".join(part.capitalize() for part in error_code.lower().split("_")) + "Error"


def _build_error_subclass(descriptor: ErrorDescriptor) -> type[CREError]:
    class_name = _error_class_name(descriptor.error_code)
    existing = globals().get(class_name)
    if isinstance(existing, type) and issubclass(existing, CREError):
        return existing

    # CRE_v4 Eq.(N/A) Part II §11 p.49-51
    error_cls = type(
        class_name,
        (CREError,),
        {
            "__doc__": (
                f"Formal error type for {descriptor.error_code}.\n\n"
                "# CRE_v4 Eq.(N/A) Part II §11 p.49-51"
            ),
            "error_code": descriptor.error_code,
            "severity": descriptor.severity,
            "module": descriptor.module,
        },
    )
    globals()[class_name] = error_cls
    return error_cls


ERROR_CLASS_REGISTRY: dict[str, type[CREError]] = {
    descriptor.error_code: _build_error_subclass(descriptor) for descriptor in _ERROR_ROWS
}

_DYNAMIC_ERROR_CLASS_EXPORTS = sorted(
    error_cls.__name__
    for error_cls in ERROR_CLASS_REGISTRY.values()
    if error_cls is not ConfigWeightSumError
)


__all__ = [
    "CREError",
    "CREErrorCode",
    "CREErrorSeverity",
    "ConfigWeightSumError",
    "ErrorDescriptor",
    "ERROR_CLASS_REGISTRY",
    "ERROR_REGISTRY",
    *_DYNAMIC_ERROR_CLASS_EXPORTS,
]
