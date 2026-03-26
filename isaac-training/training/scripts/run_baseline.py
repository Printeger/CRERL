"""CLI entrypoint for Phase 3 non-RL baseline rollouts."""

from __future__ import annotations

import os
import sys

import hydra
from omegaconf import OmegaConf
from omni.isaac.kit import SimulationApp
from omni_drones.controllers import LeePositionController
from omni_drones.utils.torchrl.transforms import VelController
from torchrl.envs.transforms import Compose, TransformedEnv


FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cfg")
TRAINING_ROOT = os.path.dirname(os.path.dirname(__file__))
if TRAINING_ROOT not in sys.path:
    sys.path.insert(0, TRAINING_ROOT)

from execution.baseline_runner import run_baseline_rollouts


@hydra.main(config_path=FILE_PATH, config_name="baseline", version_base=None)
def main(cfg):
    sim_app = SimulationApp({"headless": cfg.headless, "anti_aliasing": 1})

    from env import NavigationEnv

    env = NavigationEnv(cfg)
    controller = LeePositionController(9.81, env.drone.params).to(cfg.device)
    vel_transform = VelController(controller, yaw_control=False)
    transformed_env = TransformedEnv(env, Compose(vel_transform)).train()
    transformed_env.set_seed(cfg.seed)

    result = run_baseline_rollouts(
        env=transformed_env,
        cfg=cfg,
        baseline_name=str(cfg.baseline.name),
        policy_cfg=OmegaConf.to_container(cfg.baseline, resolve=True),
        explicit_seeds=list(cfg.baseline.seeds) if cfg.baseline.seeds else None,
    )

    print(
        f"[CRE] baseline {result.baseline_name} acceptance: "
        f"{'PASS' if result.acceptance['passed'] else 'FAIL'} | run_dir={result.run_dir}"
    )
    print(
        "[CRE] baseline summary: "
        f"episodes={result.summary.get('episode_count', 0)}, "
        f"success_rate={result.summary.get('success_rate')}, "
        f"collision_rate={result.summary.get('collision_rate')}, "
        f"min_distance={result.summary.get('min_distance')}, "
        f"average_return={result.summary.get('average_return')}, "
        f"near_violation_ratio={result.summary.get('near_violation_ratio')}"
    )
    if result.acceptance["errors"]:
        print("[CRE] baseline acceptance errors:")
        for error in result.acceptance["errors"]:
            print(f"  - {error}")

    sim_app.close()


if __name__ == "__main__":
    main()
