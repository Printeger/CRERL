# Training Workspace

This directory hosts the CRE-oriented training and evaluation workspace.

Current migration rules:

- keep `cfg/`, `scripts/`, and `unit_test/` as compatibility anchors,
- move new functionality into dedicated packages,
- gradually extract oversized files such as `envs/env_gen.py`,
- keep runtime logs under `logs/`.
