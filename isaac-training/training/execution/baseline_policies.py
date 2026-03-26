"""Baseline policy placeholders for CRE comparison runs."""

import random
from dataclasses import dataclass
from typing import Sequence


@dataclass
class RandomPolicy:
    """Simple action sampler placeholder."""

    action_dim: int
    low: float = -1.0
    high: float = 1.0
    seed: int = 0

    def __post_init__(self):
        self._rng = random.Random(self.seed)

    def act(self, _observation) -> Sequence[float]:
        return [self._rng.uniform(self.low, self.high) for _ in range(self.action_dim)]


class GreedyPolicy:
    """Placeholder for a hand-crafted greedy baseline."""

    def act(self, _observation):
        raise NotImplementedError("GreedyPolicy is not implemented yet.")


class ConservativePolicy:
    """Placeholder for a safety-biased hand-crafted baseline."""

    def act(self, _observation):
        raise NotImplementedError("ConservativePolicy is not implemented yet.")

