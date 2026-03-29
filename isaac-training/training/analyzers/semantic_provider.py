"""Provider interface, mock provider, and real-provider-ready adapter hooks."""

from __future__ import annotations

import ast
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol

from analyzers.semantic_claims import SemanticClaim

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal envs
    class _YamlCompat:
        @staticmethod
        def _strip_comment(line: str) -> str:
            return line.split("#", 1)[0].rstrip()

        @staticmethod
        def _parse_scalar(value: str):
            lowered = value.lower()
            if lowered in {"true", "false"}:
                return lowered == "true"
            if lowered in {"null", "none", "~"}:
                return None
            if value.startswith(("'", '"')) and value.endswith(("'", '"')):
                return value[1:-1]
            if value.startswith(("[", "{", "(", "-")) or value[:1].isdigit():
                try:
                    normalized = (
                        value.replace("true", "True")
                        .replace("false", "False")
                        .replace("null", "None")
                    )
                    return ast.literal_eval(normalized)
                except Exception:
                    pass
            try:
                if "." in value or "e" in lowered:
                    return float(value)
                return int(value)
            except Exception:
                return value

        @classmethod
        def _parse_block(cls, lines, start_idx: int, indent: int):
            if start_idx >= len(lines):
                return {}, start_idx

            line_indent, content = lines[start_idx]
            if content.startswith("- "):
                items = []
                idx = start_idx
                while idx < len(lines):
                    current_indent, current = lines[idx]
                    if current_indent < indent or not current.startswith("- "):
                        break
                    if current_indent != indent:
                        break
                    payload = current[2:].strip()
                    idx += 1
                    if payload == "":
                        child, idx = cls._parse_block(lines, idx, indent + 2)
                        items.append(child)
                    else:
                        items.append(cls._parse_scalar(payload))
                return items, idx

            mapping = {}
            idx = start_idx
            while idx < len(lines):
                current_indent, current = lines[idx]
                if current_indent < indent or current_indent != indent:
                    break
                key, sep, raw_value = current.partition(":")
                if not sep:
                    raise ValueError(f"Invalid YAML line: {current}")
                key = key.strip()
                value = raw_value.strip()
                idx += 1
                if value == "":
                    if idx < len(lines) and lines[idx][0] > current_indent:
                        child, idx = cls._parse_block(lines, idx, current_indent + 2)
                        mapping[key] = child
                    else:
                        mapping[key] = {}
                else:
                    mapping[key] = cls._parse_scalar(value)
            return mapping, idx

        @classmethod
        def safe_load(cls, text):
            lines = []
            for raw_line in text.splitlines():
                stripped = cls._strip_comment(raw_line)
                if not stripped.strip():
                    continue
                indent = len(stripped) - len(stripped.lstrip(" "))
                lines.append((indent, stripped.lstrip(" ")))
            if not lines:
                return {}
            parsed, _ = cls._parse_block(lines, 0, lines[0][0])
            return parsed

    yaml = _YamlCompat()


TRAINING_ROOT = Path(__file__).resolve().parents[1]
CFG_ROOT = TRAINING_ROOT / "cfg"
SEMANTIC_CFG_DIR = CFG_ROOT / "semantic_cfg"
DEFAULT_SEMANTIC_PROMPT_CFG = SEMANTIC_CFG_DIR / "semantic_prompt_v1.yaml"

DEFAULT_SYSTEM_PROMPT = (
    "You are a CRE semantic analyzer. "
    "You must stay evidence-first. "
    "Only propose C-R, E-C, or E-R claims when supported by the provided "
    "witnesses, evidence objects, findings, and scope context. "
    "Do not invent ids, families, sources, scene cfg names, or repairs. "
    "Return strict JSON with top-level key 'claims'."
)
DEFAULT_TASK = "Produce grounded CRE semantic claims for downstream machine checking."
DEFAULT_RULES = [
    "Use only the provided claim types.",
    "Reference only provided ids.",
    "Leave fields empty instead of inventing unsupported values.",
    "Prefer fewer high-quality claims over many weak guesses.",
]
DEFAULT_REQUIRED_OUTPUT_SCHEMA = {
    "claims": [
        {
            "claim_id": "provider:claim:001",
            "claim_type": "C-R | E-C | E-R",
            "confidence": 0.0,
            "severity": "warning | medium | high | critical",
            "summary": "short summary",
            "rationale": "evidence-grounded rationale",
            "status": "weak",
            "supporting_evidence_ids": [],
            "supporting_witness_ids": [],
            "supporting_finding_ids": [],
            "affected_families": [],
            "affected_sources": [],
            "affected_scene_cfg_names": [],
            "repair_direction_hint": "short actionable direction",
        }
    ]
}


CLAIM_TO_REPAIR_HINT = {
    "C-R": "review reward shaping and constraint penalties",
    "E-C": "review family coverage and critical scenario exposure",
    "E-R": "review shifted-family robustness and environment-reward alignment",
}


def _to_payload(semantic_input: Any) -> Dict[str, Any]:
    if hasattr(semantic_input, "to_dict"):
        return dict(semantic_input.to_dict())
    return dict(semantic_input or {})


def _extract_json_object(text: str) -> Dict[str, Any]:
    try:
        payload = json.loads(text)
        return dict(payload if isinstance(payload, dict) else {})
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            payload = json.loads(text[start : end + 1])
            return dict(payload if isinstance(payload, dict) else {})
        except json.JSONDecodeError:
            return {}
    return {}


class SemanticProvider(Protocol):
    """Provider interface for semantic claim generation."""

    provider_name: str

    def generate_claims(self, semantic_input: Any) -> List[SemanticClaim]:
        ...


@dataclass
class SemanticProviderConfig:
    provider_mode: str = "mock"
    max_claims: int = 3
    prompt_cfg_path: str = str(DEFAULT_SEMANTIC_PROMPT_CFG)


@dataclass
class AzureGatewayProviderConfig(SemanticProviderConfig):
    """Config for a real OpenAI-compatible provider via COMP Azure gateway."""

    provider_mode: str = "azure_gateway"
    base_url: str = "https://comp.azure-api.net/azure"
    deployment_name: str = "gpt4o"
    api_version: str = "2024-02-01"
    api_key: str = ""
    api_key_env_var: str = "COMP_OPENAI_API_KEY"
    timeout_s: float = 30.0
    max_claims: int = 3
    model: str = ""
    extra_headers: Dict[str, str] = field(default_factory=dict)


def _load_yaml_file(path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, Mapping):
        raise ValueError(f"Expected YAML mapping in {path}")
    return dict(data)


def load_semantic_prompt_template(path: str | Path = DEFAULT_SEMANTIC_PROMPT_CFG) -> Dict[str, Any]:
    prompt_path = Path(path)
    if not prompt_path.exists():
        raise FileNotFoundError(f"Semantic prompt config not found: {prompt_path}")
    payload = _load_yaml_file(prompt_path)
    normalized = {
        "prompt_type": str(payload.get("prompt_type", "phase6_semantic_prompt_template.v1")),
        "system_prompt": str(payload.get("system_prompt", DEFAULT_SYSTEM_PROMPT)),
        "task": str(payload.get("task", DEFAULT_TASK)),
        "rules": [str(item) for item in payload.get("rules", DEFAULT_RULES) or DEFAULT_RULES],
        "required_output_schema": dict(
            payload.get("required_output_schema", DEFAULT_REQUIRED_OUTPUT_SCHEMA)
            or DEFAULT_REQUIRED_OUTPUT_SCHEMA
        ),
    }
    return normalized


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


def build_provider_messages(
    semantic_input: Any,
    *,
    prompt_cfg_path: str | Path = DEFAULT_SEMANTIC_PROMPT_CFG,
) -> List[Dict[str, Any]]:
    payload = _to_payload(semantic_input)
    prompt_sections = dict(payload.get("prompt_sections") or {})
    evidence_context = dict(payload.get("evidence_context") or {})
    cross_validation = dict(payload.get("cross_validation_requirements") or {})
    prompt_template = load_semantic_prompt_template(prompt_cfg_path)

    user_payload = {
        "task": prompt_template["task"],
        "prompt_template": {
            "prompt_type": prompt_template["prompt_type"],
            "prompt_cfg_path": str(Path(prompt_cfg_path)),
        },
        "required_output_schema": prompt_template["required_output_schema"],
        "semantic_input": {
            "spec_version": payload.get("spec_version", ""),
            "spec_summary": payload.get("spec_summary", {}),
            "static_context": payload.get("static_context", {}),
            "dynamic_context": payload.get("dynamic_context", {}),
            "prompt_sections": prompt_sections,
            "evidence_context": {
                "static_findings": evidence_context.get("static_findings", {}),
                "dynamic_findings": evidence_context.get("dynamic_findings", {}),
                "witness_summaries": evidence_context.get("witness_summaries", []),
                "evidence_objects": evidence_context.get("evidence_objects", []),
                "failure_hotspots": evidence_context.get("failure_hotspots", []),
                "attribution_candidates": evidence_context.get("attribution_candidates", []),
            },
            "cross_validation_requirements": cross_validation,
        },
        "rules": prompt_template["rules"],
    }
    return [
        {"role": "system", "content": prompt_template["system_prompt"]},
        {
            "role": "user",
            "content": json.dumps(user_payload, indent=2, sort_keys=True),
        },
    ]


@dataclass
class AzureGatewaySemanticProvider:
    """Real-provider-ready adapter using the COMP Azure OpenAI gateway pattern."""

    config: AzureGatewayProviderConfig = field(default_factory=AzureGatewayProviderConfig)
    provider_name: str = "azure_gateway_semantic_provider.v1"

    def _resolve_api_key(self) -> str:
        if self.config.api_key:
            return self.config.api_key
        env_value = os.environ.get(self.config.api_key_env_var, "")
        if env_value:
            return env_value
        raise RuntimeError(
            "Missing API key for Azure gateway semantic provider. "
            f"Set {self.config.api_key_env_var} or pass api_key in AzureGatewayProviderConfig."
        )

    def _build_client(self):
        try:
            from openai import AzureOpenAI
        except Exception as exc:  # pragma: no cover - dependency depends on host environment
            raise RuntimeError(
                "openai package is required for Azure gateway semantic provider. "
                "Install it first, then retry."
            ) from exc

        api_key = self._resolve_api_key()
        deployment_name = self.config.model or self.config.deployment_name
        return AzureOpenAI(
            api_key=api_key,
            api_version=self.config.api_version,
            base_url=f"{self.config.base_url}/openai/deployments/{deployment_name}",
            default_headers=dict(self.config.extra_headers),
            timeout=self.config.timeout_s,
        )

    def generate_claims(self, semantic_input: Any) -> List[SemanticClaim]:
        client = self._build_client()
        deployment_name = self.config.model or self.config.deployment_name
        response = client.chat.completions.create(
            model=deployment_name,
            messages=build_provider_messages(
                semantic_input,
                prompt_cfg_path=self.config.prompt_cfg_path,
            ),
            temperature=0.0,
        )
        message = response.choices[0].message.content or ""
        payload = _extract_json_object(str(message))
        raw_claims = list(payload.get("claims", []) or [])
        claims = [
            SemanticClaim.from_dict(
                {
                    **dict(item or {}),
                    "provider_metadata": {
                        **dict((item or {}).get("provider_metadata", {}) or {}),
                        "provider_name": self.provider_name,
                        "provider_mode": self.config.provider_mode,
                        "deployment_name": deployment_name,
                        "api_version": self.config.api_version,
                        "base_url": self.config.base_url,
                        "prompt_cfg_path": self.config.prompt_cfg_path,
                    },
                }
            )
            for item in raw_claims[: self.config.max_claims]
        ]
        return claims


def build_semantic_provider(
    provider_mode: str = "mock",
    *,
    config: Optional[SemanticProviderConfig | Mapping[str, Any]] = None,
) -> SemanticProvider:
    normalized_mode = str(provider_mode or "mock").strip().lower()
    if normalized_mode == "mock":
        if isinstance(config, Mapping):
            payload = dict(config)
            effective = SemanticProviderConfig(
                provider_mode=str(payload.get("provider_mode", "mock")),
                max_claims=int(payload.get("max_claims", 3) or 3),
                prompt_cfg_path=str(payload.get("prompt_cfg_path", DEFAULT_SEMANTIC_PROMPT_CFG)),
            )
        elif isinstance(config, SemanticProviderConfig):
            effective = config
        else:
            effective = SemanticProviderConfig()
        return MockSemanticProvider(max_claims=effective.max_claims)
    if normalized_mode in {"azure_gateway", "azure_openai_gateway", "openai_gateway"}:
        if isinstance(config, Mapping):
            effective = AzureGatewayProviderConfig(**dict(config))
        elif isinstance(config, AzureGatewayProviderConfig):
            effective = config
        else:
            effective = AzureGatewayProviderConfig()
        return AzureGatewaySemanticProvider(config=effective)
    raise ValueError(f"Unsupported semantic provider mode '{provider_mode}'.")


def generate_mock_claims(semantic_input: Any, *, min_score: float = 0.05, max_claims: int = 3) -> List[SemanticClaim]:
    provider = MockSemanticProvider(min_score=min_score, max_claims=max_claims)
    return provider.generate_claims(semantic_input)


__all__ = [
    "AzureGatewayProviderConfig",
    "AzureGatewaySemanticProvider",
    "MockSemanticProvider",
    "SemanticProvider",
    "SemanticProviderConfig",
    "build_provider_messages",
    "build_semantic_provider",
    "generate_mock_claims",
    "load_semantic_prompt_template",
]
