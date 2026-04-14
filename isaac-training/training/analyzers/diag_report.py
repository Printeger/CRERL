"""Core CRE data schemas used by Phase 0 data-structure freeze.

This file currently implements the canonical `SpecS` schema exactly where
Part II Section 1.2 specifies it, and keeps direct dependency types opaque when
their field layouts are only referenced by name in the PDF excerpt.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from numbers import Real
import re
from types import MappingProxyType
from typing import Any, Callable, ClassVar, Literal
from uuid import UUID


State = Any
Action = Any


@dataclass(frozen=True)
class NLInput:
    """Passive canonical natural-language envelope.

    # CRE_v4 Part II §1.2 p.21
    """

    r_desc: str
    c_desc: str
    e_desc: str
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        # CRE_v4 Part II §1.2 p.21: reward / constraint / environment
        # descriptions are required and non-empty.
        for field_name in ("r_desc", "c_desc", "e_desc"):
            value = getattr(self, field_name)
            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string")
            if not value.strip():
                raise ValueError(f"{field_name} must be non-empty")

        # CRE_v4 Part II §1.2 p.21: metadata is free-form and passed through
        # unchanged at the key/value level, but stored read-only in Phase 0.
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dict")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True)
class RewardTerm:
    """Opaque reward-term placeholder.

    # CRE_v4 Part II §1.2 p.22 references RewardTerm by name inside RewardDAG,
    # but does not inline its field schema in this excerpt.
    """

    pass


@dataclass(frozen=True)
class TrainingEnvDistribution:
    """Opaque training-environment distribution placeholder.

    # CRE_v4 Part II §1.2 p.22 references TrainingEnvDistribution by name
    # inside SpecS, but does not inline its field schema in this excerpt.
    """

    pass


@dataclass(frozen=True)
class Environment:
    """Opaque deployment-environment placeholder.

    # CRE_v4 Part II §1.2 p.22 references Environment by name inside SpecS,
    # but does not inline its field schema in this excerpt.
    """

    pass


@dataclass(frozen=True)
class PolicyClass:
    """Opaque policy-class placeholder for Pi.

    # CRE_v4 Part II §1.2 p.22 references PolicyClass by name inside SpecS,
    # but does not inline its field schema in this excerpt.
    """

    pass


@dataclass(frozen=True)
class AmbiguityFlag:
    """Canonical ambiguity marker schema.

    # CRE_v4 Part II §1.2 p.22
    """

    flag_type: Literal[
        "UNDEFINED_THRESHOLD",
        "MISSING_ENV_SCOPE",
        "REWARD_UNDERSPECIFIED",
        "CONSTRAINT_OVERLAP",
        "TEMPORAL_AMBIGUITY",
    ]
    location: str
    impact_score: float

    _PATH_SEGMENT_PATTERN = re.compile(r"(?:[A-Za-z_][A-Za-z0-9_]*|\d+)\Z")

    def __post_init__(self) -> None:
        # CRE_v4 Eq.(N/A) Part II §1.2 p.22: flag_type uses the canonical
        # ambiguity enum listed in the core data schema.
        valid_flag_types = {
            "UNDEFINED_THRESHOLD",
            "MISSING_ENV_SCOPE",
            "REWARD_UNDERSPECIFIED",
            "CONSTRAINT_OVERLAP",
            "TEMPORAL_AMBIGUITY",
        }
        if self.flag_type not in valid_flag_types:
            raise ValueError(f"flag_type must be one of {valid_flag_types}")

        # CRE_v4 Eq.(N/A) Part II §1.2 p.22: location is a dot-separated JSON
        # path within SpecS, and Phase 0 requires it to be a non-empty string.
        if not isinstance(self.location, str):
            raise TypeError("location must be a string")
        if not self.location.strip():
            raise ValueError("location must be non-empty")
        segments = self.location.split(".")
        if any(
            not segment
            or segment != segment.strip()
            or self._PATH_SEGMENT_PATTERN.fullmatch(segment) is None
            for segment in segments
        ):
            raise ValueError("location must be a dot-separated JSON path")

        # CRE_v4 Eq.(N/A) Part II §1.2 p.22: impact_score estimates the
        # |DeltaPsiCRE| reduction and is bounded to [0, 1].
        if isinstance(self.impact_score, bool) or not isinstance(self.impact_score, Real):
            raise TypeError("impact_score must be a real number")
        impact_score = float(self.impact_score)
        if not 0.0 <= impact_score <= 1.0:
            raise ValueError("impact_score must be in [0, 1]")
        object.__setattr__(self, "impact_score", impact_score)


@dataclass(frozen=True)
class DiscrepancyRecord:
    """Opaque discrepancy-record placeholder.

    # CRE_v4 Part II §1.2 pp.22-23 references DiscrepancyRecord by name inside
    # DiagReport, but does not inline its field schema in this excerpt.
    """

    pass


@dataclass(frozen=True)
class DiagReport:
    """Canonical diagnostic report schema.

    # CRE_v4 Part II §1.2 pp.22-23
    """

    spec_id: str
    timestamp: str
    phi_cr2: float
    phi_ec_bar: float
    phi_er3: float
    phi_cr1: float | None
    phi_ec2: float | None
    phi_ec3: float | None
    phi_ec_per_j: list[float] | None
    phi_er1: float | None
    phi_er2: float | None
    kappa_cr: float | None
    gamma_ec: float | None
    delta_er: float | None
    psi_cre: float
    ci_95: dict[str, tuple[float, float]]
    flags: list[str]
    discrepancy: list[DiscrepancyRecord] | None
    failure_hypothesis: str | None
    repair_targets: list[str] | None

    _CI95_REPORTER_NAMES: ClassVar[frozenset[str]] = frozenset(
        {
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
        }
    )

    def __post_init__(self) -> None:
        # CRE_v4 Eq.(N/A) Part II §1.2 p.23: spec_id identifies the report's
        # source SpecS and must remain a non-empty string.
        self._require_non_empty_str("spec_id", self.spec_id)

        # CRE_v4 Eq.(N/A) Part II §1.2 p.23: timestamp is recorded in ISO 8601.
        timestamp = self._require_non_empty_str("timestamp", self.timestamp)
        self._validate_iso8601_timestamp(timestamp)

        # CRE_v4 Eq.(N/A) Part II §1.2 pp.22-23: canonical reporters and the
        # composite PsiCRE score are always present and bounded to [0, 1].
        for field_name in ("phi_cr2", "phi_ec_bar", "phi_er3", "psi_cre"):
            value = self._coerce_real(field_name, getattr(self, field_name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be in [0, 1]")
            object.__setattr__(self, field_name, value)

        # CRE_v4 Eq.(N/A) Part II §1.2 p.23: supplementary / enhanced
        # reporters may be None when the corresponding computation is skipped.
        for field_name in (
            "phi_cr1",
            "phi_ec2",
            "phi_ec3",
            "phi_er1",
            "phi_er2",
            "kappa_cr",
            "gamma_ec",
            "delta_er",
        ):
            object.__setattr__(
                self,
                field_name,
                self._coerce_optional_real(field_name, getattr(self, field_name)),
            )

        if self.phi_ec_per_j is not None:
            # CRE_v4 Eq.(N/A) Part II §1.2 p.23: per-constraint coverage is a
            # numeric list when available; the excerpt does not impose a range.
            if not isinstance(self.phi_ec_per_j, list):
                raise TypeError("phi_ec_per_j must be a list[float]")
            for value in self.phi_ec_per_j:
                if isinstance(value, bool) or not isinstance(value, Real):
                    raise TypeError("phi_ec_per_j entries must be real numbers")

        # CRE_v4 Eq.(N/A) Part II §1.2 p.23: ci_95 maps reporter names to
        # two-bound numeric confidence intervals.
        if not isinstance(self.ci_95, dict):
            raise TypeError("ci_95 must be a dict[str, tuple[float, float]]")
        normalized_ci_95: dict[str, tuple[float, float]] = {}
        for key, interval in self.ci_95.items():
            if not isinstance(key, str):
                raise TypeError("ci_95 keys must be strings")
            if key not in self._CI95_REPORTER_NAMES:
                raise ValueError("ci_95 keys must be canonical reporter names")
            if not (isinstance(interval, tuple) and len(interval) == 2):
                raise TypeError("ci_95 values must be (float, float) tuples")
            lo, hi = interval
            if (
                isinstance(lo, bool)
                or not isinstance(lo, Real)
                or isinstance(hi, bool)
                or not isinstance(hi, Real)
            ):
                raise TypeError("ci_95 interval bounds must be real numbers")
            normalized_ci_95[key] = (float(lo), float(hi))
        object.__setattr__(self, "ci_95", normalized_ci_95)

        # CRE_v4 Eq.(N/A) Part II §1.2 p.23: flags stores error / warning code
        # strings and discrepancy stores typed discrepancy records.
        if not isinstance(self.flags, list):
            raise TypeError("flags must be a list[str]")
        if not all(isinstance(flag, str) for flag in self.flags):
            raise TypeError("flags entries must be strings")

        if self.discrepancy is not None:
            if not isinstance(self.discrepancy, list):
                raise TypeError("discrepancy must be a list[DiscrepancyRecord] or None")
            if not all(
                isinstance(record, DiscrepancyRecord) for record in self.discrepancy
            ):
                raise TypeError(
                    "discrepancy entries must be DiscrepancyRecord instances"
                )

        # CRE_v4 Eq.(N/A) Part II §1.2 p.23: M4 populates failure_hypothesis
        # and repair_targets when semantic diagnosis runs.
        if self.failure_hypothesis is not None:
            self._require_non_empty_str("failure_hypothesis", self.failure_hypothesis)
        if self.repair_targets is not None:
            if not isinstance(self.repair_targets, list):
                raise TypeError("repair_targets must be a list[str] or None")
            if not all(isinstance(target, str) for target in self.repair_targets):
                raise TypeError("repair_targets entries must be strings")

    @staticmethod
    def _require_non_empty_str(field_name: str, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string")
        if not value.strip():
            if field_name == "failure_hypothesis":
                raise ValueError("failure_hypothesis must be non-empty when provided")
            raise ValueError(f"{field_name} must be non-empty")
        return value

    @staticmethod
    def _coerce_real(field_name: str, value: object) -> float:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(f"{field_name} must be a real number")
        return float(value)

    @classmethod
    def _coerce_optional_real(cls, field_name: str, value: object) -> float | None:
        if value is None:
            return None
        return cls._coerce_real(field_name, value)

    @staticmethod
    def _validate_iso8601_timestamp(value: str) -> None:
        normalized = value.replace("Z", "+00:00")
        try:
            datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError("timestamp must be ISO 8601") from exc


@dataclass(frozen=True)
class AcceptanceVerdict:
    """Canonical acceptance verdict schema.

    # CRE_v4 Part II §1.2 p.23
    """

    accepted: bool
    c1_pass: bool
    c2_pass: bool
    c3_pass: bool
    c4_pass: bool
    s_sem: float
    intent_preserved: bool
    rejection_feedback: str | None

    def __post_init__(self) -> None:
        # CRE_v4 Eq.(N/A) Part II §1.2 p.23: acceptance and criterion fields
        # are boolean verdict flags in the canonical acceptance schema.
        for field_name in (
            "accepted",
            "c1_pass",
            "c2_pass",
            "c3_pass",
            "c4_pass",
            "intent_preserved",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be a bool")

        # CRE_v4 Eq.(N/A) Part II §1.2 p.23: s_sem is the semantic consistency
        # score and must remain a real-valued quantity in [0, 1].
        s_sem = self._coerce_real("s_sem", self.s_sem)
        if not 0.0 <= s_sem <= 1.0:
            raise ValueError("s_sem must be in [0, 1]")
        object.__setattr__(self, "s_sem", s_sem)

        # CRE_v4 Eq.(N/A) Part II §1.2 p.23: rejection_feedback is optional
        # text populated on rejection, therefore it must be str | None.
        if self.rejection_feedback is not None and not isinstance(
            self.rejection_feedback,
            str,
        ):
            raise TypeError("rejection_feedback must be a string or None")

    @staticmethod
    def _coerce_real(field_name: str, value: object) -> float:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(f"{field_name} must be a real number")
        return float(value)

@dataclass(frozen=True)
class Constraint:
    """Constraint schema defined by CRE_v4 Part II Section 1.2."""

    k_id: str
    predicate: Callable[[State, Action], int]
    sigma: Literal["hard", "soft", "info"]
    scope: Literal["instantaneous", "episodic", "cumulative"]
    zeta: float | None
    lam: float | None
    delta: float

    def __post_init__(self) -> None:
        # CRE_v4 Eq.(N/A) Part II §1.2 p.22: k_id is a unique constraint ID.
        if not isinstance(self.k_id, str):
            raise TypeError("k_id must be a string")
        if not self.k_id.strip():
            raise ValueError("k_id must be non-empty")

        # CRE_v4 Eq.(N/A) Part II §1.2 p.22: predicate satisfies O_j: S×A -> {0,1}.
        if not callable(self.predicate):
            raise TypeError("predicate must be callable")

        # CRE_v4 Eq.(N/A) Part II §1.2 p.22: sigma and scope use canonical enums.
        valid_sigma = {"hard", "soft", "info"}
        if self.sigma not in valid_sigma:
            raise ValueError("sigma must be one of {'hard', 'soft', 'info'}")

        valid_scope = {"instantaneous", "episodic", "cumulative"}
        if self.scope not in valid_scope:
            raise ValueError(
                "scope must be one of {'instantaneous', 'episodic', 'cumulative'}"
            )

        # CRE_v4 Eq.(N/A) Part II §1.2 p.22: zeta is required iff sigma == 'soft';
        # lam is an optional soft-constraint penalty weight.
        if self.sigma == "soft":
            if self.zeta is None:
                raise ValueError("soft constraints require zeta")
        else:
            if self.zeta is not None:
                raise ValueError("non-soft constraints must set zeta=None")
            if self.lam is not None:
                raise ValueError("non-soft constraints must set lam=None")

        zeta = self._coerce_optional_real("zeta", self.zeta)
        lam = self._coerce_optional_real("lam", self.lam)
        delta = self._coerce_real("delta", self.delta)
        # CRE_v4 Eq.(N/A) Part II §1.2 p.22: coverage threshold delta_j > 0.
        if delta <= 0.0:
            raise ValueError("delta must be > 0")

        object.__setattr__(self, "zeta", zeta)
        object.__setattr__(self, "lam", lam)
        object.__setattr__(self, "delta", delta)

    @staticmethod
    def _coerce_real(field_name: str, value: object) -> float:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(f"{field_name} must be a real number")
        return float(value)

    @classmethod
    def _coerce_optional_real(cls, field_name: str, value: object) -> float | None:
        if value is None:
            return None
        return cls._coerce_real(field_name, value)


@dataclass(frozen=True)
class RewardDAG:
    """Canonical reward DAG schema.

    # CRE_v4 Eq.(N/A) Part II §1.2 p.22
    """

    nodes: list[RewardTerm]
    edges: list[tuple[str, str]]

    def __post_init__(self) -> None:
        # CRE_v4 Eq.(N/A) Part II §1.2 p.22: RewardDAG stores `nodes` and
        # `edges` as the canonical reward-graph fields inside SpecS.R.
        if not isinstance(self.nodes, list):
            raise TypeError("nodes must be a list[RewardTerm]")
        if not all(isinstance(term, RewardTerm) for term in self.nodes):
            raise TypeError("nodes entries must be RewardTerm instances")
        # CRE_v4 Eq.(N/A) Part II §1.2 p.22: edges are shaping dependencies in
        # `(parent_id, child_id)` string-pair form.
        if not isinstance(self.edges, list):
            raise TypeError("edges must be a list[tuple[str, str]]")
        if not all(
            isinstance(edge, tuple)
            and len(edge) == 2
            and all(isinstance(item, str) for item in edge)
            for edge in self.edges
        ):
            raise TypeError("edges entries must be (str, str) tuples")

        # CRE_v4 Eq.(N/A) Part II §1.2 p.22: Phase 0 stores nested containers
        # read-only after validating the canonical list-based input contract.
        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "edges", tuple(self.edges))


@dataclass(frozen=True)
class SpecS:
    """Canonical immutable specification triple.

    # CRE_v4 Part II §1.2 p.22
    """

    spec_id: str
    E_tr: TrainingEnvDistribution
    E_dep: list[Environment]
    R: RewardDAG
    C: list[Constraint]
    Pi: PolicyClass
    version: int = 0

    def __post_init__(self) -> None:
        # CRE_v4 Part II §1.2 p.22: spec_id is assigned by M1 at parse time.
        if not isinstance(self.spec_id, str):
            raise TypeError("spec_id must be a string")
        if not self.spec_id:
            raise ValueError("spec_id must be non-empty")

        # CRE_v4 Part II §1.2 p.22: E_tr, R, C, Pi use the canonical schema types.
        if not isinstance(self.E_tr, TrainingEnvDistribution):
            raise TypeError("E_tr must be a TrainingEnvDistribution")
        if not isinstance(self.R, RewardDAG):
            raise TypeError("R must be a RewardDAG")
        if not isinstance(self.Pi, PolicyClass):
            raise TypeError("Pi must be a PolicyClass")

        # CRE_v4 Part II §1.2 p.22: E_dep = [e_0, e_1, ..., e_n]; e_0 is nominal.
        if not isinstance(self.E_dep, list):
            raise TypeError("E_dep must be a list[Environment]")
        if not self.E_dep:
            raise ValueError("E_dep must contain at least the nominal environment e_0")
        if not all(isinstance(env, Environment) for env in self.E_dep):
            raise TypeError("E_dep entries must be Environment instances")
        object.__setattr__(self, "E_dep", tuple(self.E_dep))

        # CRE_v4 Part II §1.2 p.22: C is the canonical list[Constraint] field.
        if not isinstance(self.C, list):
            raise TypeError("C must be a list[Constraint]")
        if not all(isinstance(constraint, Constraint) for constraint in self.C):
            raise TypeError("C entries must be Constraint instances")
        object.__setattr__(self, "C", tuple(self.C))

        # CRE_v4 Part II §1.2 p.22: version starts at 0 and increments on repair.
        if not isinstance(self.version, int):
            raise TypeError("version must be an int")
        if self.version < 0:
            raise ValueError("version must be >= 0")


@dataclass(frozen=True)
class RepairProposal:
    """Canonical repair proposal schema.

    # CRE_v4 Part II §1.2 p.23
    """

    proposal_id: str
    spec_prime: SpecS
    operator_class: str
    declared_side_effects: dict[str, str]
    semantic_justification: str
    predicted_delta_psi: float | None
    rough_delta_psi: float | None

    _VR_OPERATORS: ClassVar[frozenset[str]] = frozenset(
        {
            "ReweightTerms",
            "InjectPenalty",
            "ModifyShaping",
            "AdjustClip",
            "ExpandDomainRand",
            "InjectCriticalScenes",
            "RescaleShiftOp",
            "AdjustThreshold",
            "ScheduleCurriculum",
            "ReclassifySeverity",
        }
    )

    def __post_init__(self) -> None:
        # CRE_v4 Eq.(N/A) Part II §1.2 p.23: proposal_id is the repair
        # candidate identifier and is a UUID string in the schema.
        proposal_id = self._require_non_empty_str("proposal_id", self.proposal_id)
        self._validate_uuid_str("proposal_id", proposal_id)

        # CRE_v4 Eq.(N/A) Part II §1.2 p.23: spec_prime carries the repaired
        # candidate specification and must use the canonical SpecS schema.
        if not isinstance(self.spec_prime, SpecS):
            raise TypeError("spec_prime must be a SpecS")

        # CRE_v4 Eq.(N/A) Part II §1.2 p.23: operator_class names the repair
        # operator from the V_R vocabulary and must be present as a string.
        operator_class = self._require_non_empty_str(
            "operator_class",
            self.operator_class,
        )
        if operator_class not in self._VR_OPERATORS:
            raise ValueError(
                f"operator_class must be one of {sorted(self._VR_OPERATORS)}"
            )

        # CRE_v4 Eq.(N/A) Part II §1.2 p.23: declared_side_effects stores a
        # dim -> description mapping and is normalized to read-only storage.
        if not isinstance(self.declared_side_effects, dict):
            raise TypeError("declared_side_effects must be a dict[str, str]")
        normalized_side_effects: dict[str, str] = {}
        for key, value in self.declared_side_effects.items():
            if not isinstance(key, str):
                raise TypeError("declared_side_effects keys must be strings")
            if not isinstance(value, str):
                raise TypeError("declared_side_effects values must be strings")
            normalized_side_effects[key] = value
        object.__setattr__(
            self,
            "declared_side_effects",
            MappingProxyType(normalized_side_effects),
        )

        # CRE_v4 Eq.(N/A) Part II §1.2 p.23: semantic_justification is
        # required and bounded to at most 200 tokens in the schema comment.
        justification = self._require_non_empty_str(
            "semantic_justification",
            self.semantic_justification,
        )
        if len(justification.split()) > 200:
            raise ValueError(
                "semantic_justification must contain at most 200 tokens"
            )

        # CRE_v4 Eq.(N/A) Part II §1.2 p.23: predicted_delta_psi and
        # rough_delta_psi are optional numeric fields populated by ranking.
        object.__setattr__(
            self,
            "predicted_delta_psi",
            self._coerce_optional_real(
                "predicted_delta_psi",
                self.predicted_delta_psi,
            ),
        )
        object.__setattr__(
            self,
            "rough_delta_psi",
            self._coerce_optional_real(
                "rough_delta_psi",
                self.rough_delta_psi,
            ),
        )

    @staticmethod
    def _require_non_empty_str(field_name: str, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string")
        if not value.strip():
            raise ValueError(f"{field_name} must be non-empty")
        return value

    @staticmethod
    def _coerce_real(field_name: str, value: object) -> float:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(f"{field_name} must be a real number")
        return float(value)

    @staticmethod
    def _validate_uuid_str(field_name: str, value: str) -> None:
        try:
            UUID(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be a valid UUID string") from exc

    @classmethod
    def _coerce_optional_real(cls, field_name: str, value: object) -> float | None:
        if value is None:
            return None
        return cls._coerce_real(field_name, value)
