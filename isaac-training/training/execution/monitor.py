"""Execution monitor placeholder."""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class MonitorSnapshot:
    """Lightweight execution monitor snapshot."""

    step: int
    metrics: Dict[str, Any] = field(default_factory=dict)

