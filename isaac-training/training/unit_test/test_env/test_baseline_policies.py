import sys
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from execution.baseline_policies import (
    ConservativePolicy,
    GreedyPolicy,
    RandomPolicy,
)


def _dummy_observation():
    return {
        "state": torch.tensor([[1.0, 0.0, 0.0, 4.0, 0.5, 0.0, 0.0, 0.0]], dtype=torch.float32),
        "direction": torch.tensor([[1.0, 0.0, 0.0]], dtype=torch.float32),
        "lidar": torch.zeros((1, 1, 8, 4), dtype=torch.float32),
        "dynamic_obstacle": torch.zeros((1, 1, 2, 10), dtype=torch.float32),
    }


def test_random_policy_is_seeded_and_deterministic():
    obs = _dummy_observation()
    policy_a = RandomPolicy(action_limit=2.0, seed=7)
    policy_b = RandomPolicy(action_limit=2.0, seed=7)

    action_a = policy_a.compute_action(obs)
    action_b = policy_b.compute_action(obs)

    assert torch.allclose(action_a, action_b)


def test_greedy_policy_moves_forward_toward_goal():
    obs = _dummy_observation()
    policy = GreedyPolicy(action_limit=2.0, seed=0, forward_speed=1.5, vertical_gain=0.8)
    action = policy.compute_action(obs)

    assert action.shape == (1, 3)
    assert action[0, 0] > 0.0
    assert abs(float(action[0, 1])) < 1e-6
    assert action[0, 2] > 0.0


def test_conservative_policy_slows_down_when_static_clearance_is_low():
    far_obs = _dummy_observation()
    near_obs = _dummy_observation()
    # lidar stores proximity as (range - hit_distance), so larger means closer.
    near_obs["lidar"][:] = 39.6

    policy = ConservativePolicy(
        action_limit=2.0,
        seed=0,
        forward_speed=0.8,
        vertical_gain=0.6,
        safety_distance=1.5,
        stop_distance=0.6,
        lateral_gain=1.2,
        dynamic_avoidance_gain=0.8,
    )

    far_action = policy.compute_action(far_obs)
    near_action = policy.compute_action(near_obs)

    assert far_action[0, 0] > near_action[0, 0]
    assert near_action[0, 0] <= 1e-6
