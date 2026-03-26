"""Stable logger exports for the CRE runtime pipeline."""

from pathlib import Path
from typing import Optional

from envs.cre_logging import (
    FlightEpisodeLogger,
    SCHEMA_VERSION,
    STANDARD_REWARD_COMPONENT_KEYS,
    aggregate_log_directory,
    normalize_reward_components,
)


def create_run_logger(
    *,
    source: str,
    run_name: str,
    base_dir: Optional[str | Path] = None,
    near_violation_distance: float = 0.5,
    use_timestamp: bool = True,
    schema_version: str = SCHEMA_VERSION,
) -> FlightEpisodeLogger:
    return FlightEpisodeLogger(
        run_name=run_name,
        base_dir=base_dir,
        near_violation_distance=near_violation_distance,
        use_timestamp=use_timestamp,
        source=source,
        schema_version=schema_version,
    )

__all__ = [
    "FlightEpisodeLogger",
    "SCHEMA_VERSION",
    "STANDARD_REWARD_COMPONENT_KEYS",
    "aggregate_log_directory",
    "create_run_logger",
    "normalize_reward_components",
]
