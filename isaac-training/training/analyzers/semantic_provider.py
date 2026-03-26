"""Provider interface and mock implementation for Phase 6 semantic claims."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Protocol

from analyzers.semantic_claims import SemanticClaim


CLAIM_TO_REPAIR_HINT = {
    "C-R": "review reward shaping and constraint penalties",
    "E-C": "review family coverage and critical scenario exposure",
    "E-R": "review shifted-family robustness and environment-reward alignment",
}


def _to_payload(semantic_input: Any) -> Dict[str, Any]:
    if hasattr(semantic_input, "to_dict"):
        return dict(semantic_input.to_dict())
    return dict(semantic_input or {})


class SemanticProvider(Protocol):
    """Provider interface for semantic claim generation."""

    provider_name: str

    def generate_claims(self, semantic_input: Any) -> List[SemanticClaim]:
        ...


def _claim_type_from_witness(
    witness_id: str,
    semantic_input_payload: Mapping[str, Any],
) -> str:
    requirements = dict(semantic_input_payload.get("cross_validation_requirements") or {})
    contract = dict(requirements.get("cross_validation_contract") or {})
    claim_to_witness_map = dict(contract.get("claim_to_witness_map") or {})
    for claim_type, witness_ids in claim_to_witness_map.items():
        if str(witness_id) in {str(item) for item in witness_ids or []}:
            return str(claim_type)
    if witness_id == "W_CR":
        return "C-R"
    if witness_id == "W_EC":
        return "E-C"
    if witness_id == "W_ER":
        return "E-R"
    return "unknown"


def _severity_from_score(score: float, fallback: str) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.6:
        return "medium"
    if score > 0.0:
        return "warning"
    return fallback


def _collect_scope_from_hotspots(
    claim_type: str,
    hotspots: Iterable[Mapping[str, Any]],
) -> Dict[str, List[str]]:
    families = set()
    sources = set()
    scene_cfg_names = set()
    evidence_ids = []
    for hotspot in hotspots:
        hints = {str(item) for item in hotspot.get("attribution_hints", []) or []}
        scenario_types = [str(item) for item in hotspot.get("scenario_types", []) or [] if item not in (None, "")]
        witness_id = str(hotspot.get("witness_id", "") or "")
        if claim_type not in hints:
            if claim_type == "E-R":
                if "shifted-family-hotspot" not in hints and "shifted" not in scenario_types and witness_id != "W_ER":
                    continue
            elif claim_type == "E-C":
                if "critical-state-undercoverage" not in hints and witness_id != "W_EC":
                    continue
            elif claim_type == "C-R":
                if "reward-constraint-coupling" not in hints and witness_id != "W_CR":
                    continue
        evidence_id = hotspot.get("evidence_id")
        if evidence_id not in (None, ""):
            evidence_ids.append(str(evidence_id))
        for family in scenario_types:
            if family not in (None, ""):
                families.add(str(family))
        for source in hotspot.get("sources", []) or []:
            if source not in (None, ""):
                sources.add(str(source))
        for scene_cfg_name in hotspot.get("scene_cfg_names", []) or []:
            if scene_cfg_name not in (None, ""):
                scene_cfg_names.add(str(scene_cfg_name))
    return {
        "families": sorted(families),
        "sources": sorted(sources),
        "scene_cfg_names": sorted(scene_cfg_names),
        "evidence_ids": list(dict.fromkeys(evidence_ids)),
    }


@dataclass
class MockSemanticProvider:
    """Deterministic mock provider used before any real LLM backend."""

    provider_name: str = "mock_semantic_provider.v1"
    min_score: float = 0.05
    max_claims: int = 3

    def generate_claims(self, semantic_input: Any) -> List[SemanticClaim]:
        payload = _to_payload(semantic_input)
        dynamic_section = dict(payload.get("dynamic_context") or {})
        evidence_context = dict(payload.get("evidence_context") or {})
        witness_overview = list(evidence_context.get("witness_summaries", []) or [])
        failure_hotspots = list(evidence_context.get("failure_hotspots", []) or [])
        evidence_objects = list(evidence_context.get("evidence_objects", []) or [])
        dynamic_findings = list((evidence_context.get("dynamic_findings") or {}).get("finding_ids", []) or [])

        claims: List[SemanticClaim] = []
        for index, witness in enumerate(
            sorted(
                witness_overview,
                key=lambda item: float(item.get("score", 0.0) or 0.0),
                reverse=True,
            ),
            start=1,
        ):
            score = float(witness.get("score", 0.0) or 0.0)
            if score < self.min_score:
                continue
            witness_id = str(witness.get("witness_id", ""))
            claim_type = _claim_type_from_witness(witness_id, payload)
            hotspot_scope = _collect_scope_from_hotspots(
                claim_type,
                [*failure_hotspots, *evidence_objects],
            )

            claims.append(
                SemanticClaim(
                    claim_id=f"{self.provider_name}:claim:{index:03d}",
                    claim_type=claim_type,
                    confidence=score,
                    severity=_severity_from_score(score, str(witness.get("severity", "warning"))),
                    summary=str(witness.get("summary", f"{claim_type} inconsistency candidate.")),
                    rationale=(
                        f"Generated from witness {witness_id} with score {score:.3f} "
                        f"and real runtime evidence from accepted bundles."
                    ),
                    status="weak",
                    supporting_evidence_ids=hotspot_scope["evidence_ids"],
                    supporting_witness_ids=[witness_id] if witness_id else [],
                    supporting_finding_ids=list(dynamic_findings[:2]),
                    affected_families=hotspot_scope["families"],
                    affected_sources=hotspot_scope["sources"] or ["unknown"],
                    affected_scene_cfg_names=hotspot_scope["scene_cfg_names"],
                    repair_direction_hint=CLAIM_TO_REPAIR_HINT.get(
                        claim_type,
                        "review evidence and clarify the inconsistency source",
                    ),
                    provider_metadata={
                        "provider_name": self.provider_name,
                        "generation_mode": "deterministic_mock",
                        "primary_run_ids": list(dynamic_section.get("primary_run_ids", []) or []),
                        "comparison_run_ids": list(dynamic_section.get("comparison_run_ids", []) or []),
                    },
                )
            )
            if len(claims) >= self.max_claims:
                break
        return claims


def generate_mock_claims(semantic_input: Any, *, min_score: float = 0.05, max_claims: int = 3) -> List[SemanticClaim]:
    provider = MockSemanticProvider(min_score=min_score, max_claims=max_claims)
    return provider.generate_claims(semantic_input)


__all__ = [
    "MockSemanticProvider",
    "SemanticProvider",
    "generate_mock_claims",
]
