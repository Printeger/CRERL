import sys
from pathlib import Path

import pytest

pytest.importorskip("torch")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from execution.baseline_runner import resolve_baseline_seeds


def test_resolve_baseline_seeds_uses_explicit_list_when_given():
    assert resolve_baseline_seeds(base_seed=3, num_episodes=4, explicit_seeds=[11, 13]) == [11, 13]


def test_resolve_baseline_seeds_falls_back_to_incrementing_sequence():
    assert resolve_baseline_seeds(base_seed=5, num_episodes=3, explicit_seeds=None) == [5, 6, 7]
