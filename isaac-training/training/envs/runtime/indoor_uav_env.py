"""Runtime environment placeholder.

The authoritative training/runtime environment still lives in `scripts/env.py`.
This module marks the target import path for the extracted implementation.
"""


class IndoorUAVEnv:
    """Placeholder adapter for the future extracted runtime environment."""

    def __init__(self, *_args, **_kwargs):
        raise NotImplementedError(
            "IndoorUAVEnv has not been extracted from scripts/env.py yet."
        )

