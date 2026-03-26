"""Static analysis placeholders."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class StaticCheckResult:
    """Structured result for a static consistency check."""

    check_id: str
    passed: bool
    severity: str = "info"
    details: Dict[str, Any] = field(default_factory=dict)


def run_static_checks(*_args, **_kwargs) -> List[StaticCheckResult]:
    raise NotImplementedError("Static analyzers have not been implemented yet.")

