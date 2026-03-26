"""Cross-validation for Phase 6 semantic claims."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from analyzers.semantic_claims import (
    SemanticClaim,
    SemanticClaimSet,
    SemanticCrossCheckResult,
)


def _to_payload(semantic_input: Any) -> Dict[str, Any]:
    if hasattr(semantic_input, "to_dict"):
        return dict(semantic_input.to_dict())
    return dict(semantic_input or {})


def _dedupe(values: Iterable[Any]) -> List[str]:
    seen = set()
    result: List[str] = []
    for item in values:
        if item in (None, ""):
            continue
        value = str(item)
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _collect_known_context(payload: Mapping[str, Any]) -> Dict[str, Any]:
    evidence_context = dict(payload.get("evidence_context") or {})
    cross_validation = dict(payload.get("cross_validation_requirements") or {})
    contract = dict(cross_validation.get("cross_validation_contract") or {})
    spec_summary = dict(payload.get("spec_summary") or {})

    evidence_objects = list(evidence_context.get("evidence_objects", []) or [])
    failure_hotspots = list(evidence_context.get("failure_hotspots", []) or [])
    attribution_candidates = list(evidence_context.get("attribution_candidates", []) or [])
    static_findings = dict(evidence_context.get("static_findings") or {})
    dynamic_findings = dict(evidence_context.get("dynamic_findings") or {})
    witness_summaries = list(evidence_context.get("witness_summaries", []) or [])

    evidence_index: Dict[str, Dict[str, Any]] = {}
    for item in evidence_objects:
        evidence_id = item.get("evidence_id")
        if evidence_id not in (None, ""):
            evidence_index[str(evidence_id)] = dict(item)
    for item in failure_hotspots:
        evidence_id = item.get("evidence_id") or item.get("candidate_id")
        if evidence_id not in (None, ""):
            evidence_index.setdefault(str(evidence_id), dict(item))
    for item in attribution_candidates:
        evidence_id = item.get("candidate_id") or item.get("evidence_id")
        if evidence_id not in (None, ""):
            evidence_index.setdefault(str(evidence_id), dict(item))

    witness_ids = _dedupe(item.get("witness_id") for item in witness_summaries)
    finding_ids = _dedupe(
        list(static_findings.get("finding_ids", []) or [])
        + list(dynamic_findings.get("finding_ids", []) or [])
    )
    families = _dedupe(
        list(spec_summary.get("environment_families", []) or [])
        + [family for item in evidence_objects for family in item.get("scenario_types", []) or []]
    )
    sources = _dedupe(
        source for item in evidence_objects for source in item.get("sources", []) or []
    )
    scene_cfg_names = _dedupe(
        name for item in evidence_objects for name in item.get("scene_cfg_names", []) or []
    )

    return {
        "required_claim_types": _dedupe(
            list(cross_validation.get("required_claim_types", []) or [])
            + list(contract.get("required_supported_claim_types", []) or [])
        ),
        "claim_to_witness_map": {
            str(key): _dedupe(value)
            for key, value in dict(contract.get("claim_to_witness_map") or {}).items()
        },
        "evidence_index": evidence_index,
        "witness_ids": witness_ids,
        "finding_ids": finding_ids,
        "families": families,
        "sources": sources,
        "scene_cfg_names": scene_cfg_names,
    }


def check_claim_type_alignment(
    claim: SemanticClaim,
    semantic_input: Any,
) -> Tuple[bool, List[str]]:
    payload = _to_payload(semantic_input)
    known = _collect_known_context(payload)
    required_claim_types = list(known["required_claim_types"])
    if claim.claim_type == "unknown":
        return False, ["Claim type is unknown."]
    if required_claim_types and claim.claim_type not in required_claim_types:
        return False, [f"Claim type '{claim.claim_type}' is not allowed by the semantic contract."]
    return True, [f"Claim type '{claim.claim_type}' is allowed by the semantic contract."]


def check_claim_evidence_support(
    claim: SemanticClaim,
    semantic_input: Any,
) -> Tuple[bool, List[str], List[str], List[str], List[str]]:
    payload = _to_payload(semantic_input)
    known = _collect_known_context(payload)

    evidence_index: Dict[str, Dict[str, Any]] = dict(known["evidence_index"])
    finding_ids = set(known["finding_ids"])
    witness_ids = set(known["witness_ids"])

    matched_evidence_ids = [item for item in claim.supporting_evidence_ids if item in evidence_index]
    matched_finding_ids = [item for item in claim.supporting_finding_ids if item in finding_ids]
    matched_witness_ids = [item for item in claim.supporting_witness_ids if item in witness_ids]

    messages: List[str] = []
    if matched_evidence_ids:
        messages.append(
            f"Claim cites {len(matched_evidence_ids)} known evidence object(s)."
        )
    if matched_finding_ids:
        messages.append(
            f"Claim cites {len(matched_finding_ids)} known finding id(s)."
        )
    if matched_witness_ids:
        messages.append(
            f"Claim cites {len(matched_witness_ids)} known witness id(s)."
        )

    passed = bool(matched_evidence_ids or matched_finding_ids or matched_witness_ids)
    if not passed:
        messages.append("Claim has no recognized supporting evidence, witness, or finding reference.")
    return passed, messages, matched_evidence_ids, matched_witness_ids, matched_finding_ids


def check_claim_witness_alignment(
    claim: SemanticClaim,
    semantic_input: Any,
) -> Tuple[bool, List[str], List[str]]:
    payload = _to_payload(semantic_input)
    known = _collect_known_context(payload)

    claim_to_witness_map: Dict[str, List[str]] = dict(known["claim_to_witness_map"])
    required_witnesses = list(claim_to_witness_map.get(claim.claim_type, []))
    if not required_witnesses:
        return True, [f"No explicit witness alignment is required for claim type '{claim.claim_type}'."], []

    evidence_index: Dict[str, Dict[str, Any]] = dict(known["evidence_index"])
    matched = set()
    for witness_id in claim.supporting_witness_ids:
        if witness_id in required_witnesses:
            matched.add(witness_id)
    for evidence_id in claim.supporting_evidence_ids:
        evidence_payload = evidence_index.get(evidence_id, {})
        witness_id = evidence_payload.get("witness_id")
        if witness_id in required_witnesses:
            matched.add(str(witness_id))
        for hint in evidence_payload.get("attribution_hints", []) or []:
            if hint == claim.claim_type:
                matched.update(required_witnesses)

    matched_list = sorted(matched)
    if matched_list:
        return True, [f"Claim is aligned with witness id(s): {', '.join(matched_list)}."], matched_list
    return False, [f"Claim type '{claim.claim_type}' is not backed by the required witness family."], []


def check_claim_scope_alignment(
    claim: SemanticClaim,
    semantic_input: Any,
) -> Tuple[bool, List[str]]:
    payload = _to_payload(semantic_input)
    known = _collect_known_context(payload)

    messages: List[str] = []
    checks: List[bool] = []

    if claim.affected_families:
        families = set(known["families"])
        matched = families.intersection(claim.affected_families)
        checks.append(bool(matched))
        messages.append(
            "Matched families: " + (", ".join(sorted(matched)) if matched else "<none>")
        )
    if claim.affected_sources:
        sources = set(known["sources"])
        matched = sources.intersection(claim.affected_sources)
        checks.append(bool(matched))
        messages.append(
            "Matched sources: " + (", ".join(sorted(matched)) if matched else "<none>")
        )
    if claim.affected_scene_cfg_names:
        scene_cfg_names = set(known["scene_cfg_names"])
        matched = scene_cfg_names.intersection(claim.affected_scene_cfg_names)
        checks.append(bool(matched))
        messages.append(
            "Matched scene configs: " + (", ".join(sorted(matched)) if matched else "<none>")
        )

    if not checks:
        return True, ["Claim does not narrow scope beyond the global bundle context."]
    return all(checks), messages


def validate_semantic_claims(
    claims: Sequence[SemanticClaim | Mapping[str, Any]],
    *,
    semantic_input: Any,
) -> SemanticClaimSet:
    claim_objects = [
        claim if isinstance(claim, SemanticClaim) else SemanticClaim.from_dict(claim)
        for claim in claims
    ]

    supported_claims: List[SemanticClaim] = []
    weak_claims: List[SemanticClaim] = []
    rejected_claims: List[SemanticClaim] = []
    cross_checks: List[SemanticCrossCheckResult] = []

    for claim in claim_objects:
        type_ok, type_messages = check_claim_type_alignment(claim, semantic_input)
        evidence_ok, evidence_messages, matched_evidence_ids, matched_witness_ids, matched_finding_ids = (
            check_claim_evidence_support(claim, semantic_input)
        )
        witness_ok, witness_messages, aligned_witnesses = check_claim_witness_alignment(
            claim,
            semantic_input,
        )
        scope_ok, scope_messages = check_claim_scope_alignment(claim, semantic_input)

        messages = type_messages + evidence_messages + witness_messages + scope_messages
        support_status = "supported"
        passed = True
        if not type_ok or not evidence_ok:
            support_status = "rejected"
            passed = False
        elif not witness_ok or not scope_ok:
            support_status = "weak"
            passed = False

        normalized_claim = SemanticClaim.from_dict(
            {
                **claim.to_dict(),
                "status": support_status,
                "supporting_evidence_ids": matched_evidence_ids or claim.supporting_evidence_ids,
                "supporting_witness_ids": aligned_witnesses or matched_witness_ids or claim.supporting_witness_ids,
                "supporting_finding_ids": matched_finding_ids or claim.supporting_finding_ids,
                "provider_metadata": {
                    **dict(claim.provider_metadata or {}),
                    "crosscheck_passed": passed,
                    "crosscheck_messages": messages,
                },
            }
        )

        cross_checks.append(
            SemanticCrossCheckResult(
                claim_id=claim.claim_id,
                passed=passed,
                support_status=support_status,
                messages=messages,
                matched_evidence_ids=matched_evidence_ids,
                matched_witness_ids=aligned_witnesses or matched_witness_ids,
            )
        )

        if support_status == "supported":
            supported_claims.append(normalized_claim)
        elif support_status == "weak":
            weak_claims.append(normalized_claim)
        else:
            rejected_claims.append(normalized_claim)

    payload = _to_payload(semantic_input)
    metadata = {
        "semantic_input_type": payload.get("input_type", ""),
        "semantic_contract_type": (
            payload.get("cross_validation_requirements", {}) or {}
        ).get("semantic_contract_type", ""),
    }
    return SemanticClaimSet(
        supported_claims=supported_claims,
        weak_claims=weak_claims,
        rejected_claims=rejected_claims,
        cross_checks=cross_checks,
        metadata=metadata,
    )


__all__ = [
    "check_claim_evidence_support",
    "check_claim_scope_alignment",
    "check_claim_type_alignment",
    "check_claim_witness_alignment",
    "validate_semantic_claims",
]
