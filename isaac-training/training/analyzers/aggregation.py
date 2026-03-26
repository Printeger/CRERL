"""Aggregation placeholder for multi-source CRE findings."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AggregatedFinding:
    """Merged finding emitted by the report aggregation stage."""

    finding_id: str
    severity: str
    summary: str
    details: Dict[str, Any] = field(default_factory=dict)


def aggregate_findings(*_args, **_kwargs) -> List[AggregatedFinding]:
    raise NotImplementedError("Finding aggregation is not implemented yet.")

