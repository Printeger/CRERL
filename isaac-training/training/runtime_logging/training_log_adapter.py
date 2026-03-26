"""Adapter placeholder for routing training-loop outputs into CRE logs."""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class TrainingLogRecord:
    """Normalized training-side record for future CRE log integration."""

    step: int
    episode_id: int
    stats: Dict[str, Any] = field(default_factory=dict)
    rewards: Dict[str, Any] = field(default_factory=dict)
    done: Dict[str, Any] = field(default_factory=dict)


def adapt_training_step(*_args, **_kwargs) -> TrainingLogRecord:
    raise NotImplementedError(
        "training_log_adapter is a placeholder. "
        "The training loop has not been wired into runtime_logging yet."
    )

