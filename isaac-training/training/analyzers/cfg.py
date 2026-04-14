"""Phase 0 CFG skeleton aligned to CRE_v4 Part II Section 1.3 Table 4."""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Real
from typing import Literal

from analyzers.errors import CREErrorCode, ConfigWeightSumError

CONFIG_WEIGHT_SUM_ERROR = CREErrorCode.CONFIG_WEIGHT_SUM_ERROR


@dataclass(frozen=True)
class CFGSchema:
    """Immutable global configuration schema for the CRE pipeline.

    The module-level ``CFG`` singleton is the only configuration object that
    later M5 / orchestrator code should depend on.
    """

    # CRE_v4 Eq.(N/A) Part II §1.3 Table 4 p.24: ambiguity detection defaults.
    eta_flag: float = 0.15
    llm_retry_limit: int = 3
    delta_j_default: float = 0.50

    # CRE_v4 Eq.(N/A) Part II §1.3 Table 4 p.24: estimator defaults.
    n_ref_traj: int = 500
    n_mc_kj: int = 1000
    critical_region_radius: float = 0.10
    ec_aggregation_mode: Literal["mean", "min"] = "mean"
    eps_stab: float = 1e-6
    enhanced_estimators_enabled: bool = True

    # CRE_v4 Eq.(N/A) Part II §1.3 Table 4 p.24: discrepancy protocol defaults.
    eta_disc: float = 0.15
    tau_low: float = 0.30
    tau_high: float = 0.70
    lambda_expand: float = 0.50
    n_rechk: int = 1

    # CRE_v4 Eq.(N/A) Part II §1.3 Table 4 p.24: composite-scoring defaults.
    f_steepness: float = 8.0
    f_inflection: float = 0.50
    w_cr: float = 0.333
    w_ec: float = 0.333
    w_er: float = 0.334
    b_bootstrap: int = 1000
    k_detect: float = 1.5
    k_alarm: float = 3.0
    tau_alarm_psi: float = 0.75

    # CRE_v4 Eq.(N/A) Part II §1.3 Table 4 p.24: repair-generation defaults.
    k_proposals: int = 3
    eta_edit: float = 0.20
    n_rank_episodes: int = 50
    eps_rank: float = 0.02
    ranking_mode: str = "rollout_first"

    # CRE_v4 Eq.(N/A) Part II §1.3 Table 4 p.24: acceptance defaults.
    tau_sem: float = 0.80
    eps_perf: float = 0.05
    n_max_iterations: int = 5

    def __post_init__(self) -> None:
        # CRE_v4 Eq.(N/A) Part II §1.3 Table 4 p.23-24: CFG is the canonical
        # singleton configuration surface for all pipeline modules, so every
        # field is normalized and validated at construction time.
        object.__setattr__(self, "eta_flag", self._coerce_positive_real("eta_flag", self.eta_flag))
        object.__setattr__(
            self,
            "llm_retry_limit",
            self._coerce_non_negative_int("llm_retry_limit", self.llm_retry_limit),
        )
        object.__setattr__(
            self,
            "delta_j_default",
            self._coerce_positive_real("delta_j_default", self.delta_j_default),
        )

        object.__setattr__(self, "n_ref_traj", self._coerce_positive_int("n_ref_traj", self.n_ref_traj))
        object.__setattr__(self, "n_mc_kj", self._coerce_positive_int("n_mc_kj", self.n_mc_kj))
        object.__setattr__(
            self,
            "critical_region_radius",
            self._coerce_positive_real("critical_region_radius", self.critical_region_radius),
        )
        object.__setattr__(
            self,
            "ec_aggregation_mode",
            self._coerce_ec_aggregation_mode(self.ec_aggregation_mode),
        )
        object.__setattr__(self, "eps_stab", self._coerce_positive_real("eps_stab", self.eps_stab))
        object.__setattr__(
            self,
            "enhanced_estimators_enabled",
            self._coerce_bool(
                "enhanced_estimators_enabled",
                self.enhanced_estimators_enabled,
            ),
        )

        object.__setattr__(self, "eta_disc", self._coerce_positive_real("eta_disc", self.eta_disc))
        object.__setattr__(self, "tau_low", self._coerce_unit_interval("tau_low", self.tau_low))
        object.__setattr__(self, "tau_high", self._coerce_unit_interval("tau_high", self.tau_high))
        if self.tau_low >= self.tau_high:
            raise ValueError("tau_low must be strictly less than tau_high")
        object.__setattr__(
            self,
            "lambda_expand",
            self._coerce_positive_real("lambda_expand", self.lambda_expand),
        )
        object.__setattr__(self, "n_rechk", self._coerce_positive_int("n_rechk", self.n_rechk))

        object.__setattr__(
            self,
            "f_steepness",
            self._coerce_positive_real("f_steepness", self.f_steepness),
        )
        object.__setattr__(
            self,
            "f_inflection",
            self._coerce_unit_interval("f_inflection", self.f_inflection),
        )
        object.__setattr__(self, "w_cr", self._coerce_real("w_cr", self.w_cr))
        object.__setattr__(self, "w_ec", self._coerce_real("w_ec", self.w_ec))
        object.__setattr__(self, "w_er", self._coerce_real("w_er", self.w_er))
        object.__setattr__(
            self,
            "b_bootstrap",
            self._coerce_positive_int("b_bootstrap", self.b_bootstrap),
        )
        object.__setattr__(self, "k_detect", self._coerce_positive_real("k_detect", self.k_detect))
        object.__setattr__(self, "k_alarm", self._coerce_positive_real("k_alarm", self.k_alarm))
        object.__setattr__(
            self,
            "tau_alarm_psi",
            self._coerce_unit_interval("tau_alarm_psi", self.tau_alarm_psi),
        )

        object.__setattr__(
            self,
            "k_proposals",
            self._coerce_positive_int("k_proposals", self.k_proposals),
        )
        object.__setattr__(self, "eta_edit", self._coerce_positive_real("eta_edit", self.eta_edit))
        object.__setattr__(
            self,
            "n_rank_episodes",
            self._coerce_positive_int("n_rank_episodes", self.n_rank_episodes),
        )
        object.__setattr__(self, "eps_rank", self._coerce_positive_real("eps_rank", self.eps_rank))
        object.__setattr__(
            self,
            "ranking_mode",
            self._coerce_non_empty_str("ranking_mode", self.ranking_mode),
        )

        object.__setattr__(self, "tau_sem", self._coerce_unit_interval("tau_sem", self.tau_sem))
        object.__setattr__(self, "eps_perf", self._coerce_non_negative_real("eps_perf", self.eps_perf))
        object.__setattr__(
            self,
            "n_max_iterations",
            self._coerce_positive_int("n_max_iterations", self.n_max_iterations),
        )

        self.validate_weight_sum()

    def validate_weight_sum(self) -> None:
        """Validation hook reserved for the next implementation step.

        The real implementation must enforce the PDF rule:
        abs(w_cr + w_ec + w_er - 1.0) < 1e-9 and all weights > 0,
        raising CONFIG_WEIGHT_SUM_ERROR on violation.
        """

        # CRE_v4 Eq.(N/A) Part II §1.3 Table 4 p.23-24: pipeline startup must
        # reject any non-positive weight or non-unit weight sum before modules run.
        if self.w_cr <= 0.0 or self.w_ec <= 0.0 or self.w_er <= 0.0:
            raise self._weight_sum_error()
        if abs(self.w_cr + self.w_ec + self.w_er - 1.0) >= 1e-9:
            raise self._weight_sum_error()

    @staticmethod
    def _weight_sum_error() -> ConfigWeightSumError:
        # CRE_v4 Eq.(N/A) Part II §11 p.49-51: Table 5 binds the weight-sum
        # precondition to the canonical CONFIG_WEIGHT_SUM_ERROR surface.
        return ConfigWeightSumError()

    @staticmethod
    def _coerce_real(field_name: str, value: object) -> float:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(f"{field_name} must be a real number")
        return float(value)

    @classmethod
    def _coerce_positive_real(cls, field_name: str, value: object) -> float:
        coerced = cls._coerce_real(field_name, value)
        if coerced <= 0.0:
            raise ValueError(f"{field_name} must be positive")
        return coerced

    @classmethod
    def _coerce_non_negative_real(cls, field_name: str, value: object) -> float:
        coerced = cls._coerce_real(field_name, value)
        if coerced < 0.0:
            raise ValueError(f"{field_name} must be non-negative")
        return coerced

    @classmethod
    def _coerce_unit_interval(cls, field_name: str, value: object) -> float:
        coerced = cls._coerce_non_negative_real(field_name, value)
        if coerced > 1.0:
            raise ValueError(f"{field_name} must be in [0, 1]")
        return coerced

    @staticmethod
    def _coerce_positive_int(field_name: str, value: object) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{field_name} must be an integer")
        if value <= 0:
            raise ValueError(f"{field_name} must be a positive integer")
        return value

    @staticmethod
    def _coerce_non_negative_int(field_name: str, value: object) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"{field_name} must be a non-negative integer")
        return value

    @staticmethod
    def _coerce_bool(field_name: str, value: object) -> bool:
        if not isinstance(value, bool):
            raise TypeError(f"{field_name} must be a bool")
        return value

    @staticmethod
    def _coerce_non_empty_str(field_name: str, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string")
        if not value.strip():
            raise ValueError(f"{field_name} must be non-empty")
        return value

    @classmethod
    def _coerce_ec_aggregation_mode(cls, value: object) -> str:
        mode = cls._coerce_non_empty_str("ec_aggregation_mode", value)
        if mode not in {"mean", "min"}:
            raise ValueError('ec_aggregation_mode must be "mean" or "min"')
        return mode


CFG = CFGSchema()


__all__ = ["CFG", "CFGSchema", "CONFIG_WEIGHT_SUM_ERROR"]
