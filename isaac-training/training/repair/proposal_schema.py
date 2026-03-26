"""Structured repair proposal placeholders."""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class RepairProposal:
    """Machine-readable repair proposal."""

    proposal_id: str
    target: str
    rationale: str
    patch: Dict[str, Any] = field(default_factory=dict)

