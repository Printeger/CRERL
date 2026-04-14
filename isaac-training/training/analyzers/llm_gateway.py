"""Shared LLM gateway skeleton for strict PDF CRE modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Any, Literal, Protocol

# CRE_v4 Eq.(N/A) Part II §2.1 p.25 / §7.1 p.41 / §8.1.2 pp.42-43 / §9.1.2 p.46
# COMP OpenAI Access Guide v3.11: AzureOpenAI + api-key + deployment endpoint

__all__ = [
    "CompOpenAIGateway",
    "LLMConfig",
    "LLMGateway",
    "LLMRequest",
    "LLMResponse",
]


@dataclass(frozen=True)
class LLMConfig:
    provider: Literal["comp_openai"]
    base_url: str
    api_version: str
    api_key_env: str
    deployment: str
    timeout_s: float = 60.0
    max_retries: int = 3
    temperature: float = 0.0
    max_tokens: int = 1024

    def deployment_base_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/openai/deployments/{self.deployment}"


@dataclass(frozen=True)
class LLMRequest:
    messages: tuple[dict[str, Any], ...]
    response_format: Literal["text", "json"] = "text"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str
    finish_reason: str | None
    raw_payload: dict[str, Any] = field(default_factory=dict)


class LLMGateway(Protocol):
    def complete(self, request: LLMRequest, config: LLMConfig) -> LLMResponse:
        """Submit a completion request via the canonical LLM provider."""


class CompOpenAIGateway:
    """COMP OpenAI gateway wrapper used by strict PDF mode modules."""

    def _resolve_api_key(self, config: LLMConfig) -> str:
        api_key = os.getenv(config.api_key_env)
        if not api_key:
            raise RuntimeError(f"Missing environment variable: {config.api_key_env}")
        return api_key

    def _build_client(self, config: LLMConfig) -> Any:
        try:
            from openai import AzureOpenAI
        except ImportError as exc:  # pragma: no cover - exercised only when SDK missing.
            raise RuntimeError(
                "CompOpenAIGateway requires openai>=1.x; "
                "the strict PDF gateway skeleton is present, but the SDK is not installed"
            ) from exc

        return AzureOpenAI(
            api_key=self._resolve_api_key(config),
            api_version=config.api_version,
            base_url=config.deployment_base_url(),
            timeout=config.timeout_s,
            max_retries=config.max_retries,
        )

    def complete(self, request: LLMRequest, config: LLMConfig) -> LLMResponse:
        """Call the COMP OpenAI chat completions endpoint for one module request."""

        client = self._build_client(config)
        response = client.chat.completions.create(
            model=config.deployment,
            messages=list(request.messages),
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
        choice = response.choices[0]
        content = choice.message.content or ""
        raw_payload = response.model_dump() if hasattr(response, "model_dump") else {}
        return LLMResponse(
            content=content,
            model=getattr(response, "model", config.deployment),
            finish_reason=getattr(choice, "finish_reason", None),
            raw_payload=raw_payload,
        )
