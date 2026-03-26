"""Intermediate representation placeholders for CRE analysis."""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class SpecIR:
    """Minimal structured view of the specification under audit."""

    spec_version: str = "v0"
    scene_family: str = "nominal"
    constraints: Dict[str, Any] = field(default_factory=dict)
    rewards: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, Any] = field(default_factory=dict)

