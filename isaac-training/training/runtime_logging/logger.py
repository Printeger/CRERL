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
from runtime_logging.acceptance import (
    CANONICAL_DONE_TYPES,
    REQUIRED_EPISODE_FIELDS,
    REQUIRED_STEP_FIELDS,
    SUMMARY_METRIC_KEYS,
    load_run_summary,
    run_acceptance_check,
    validate_run_directory,
    write_acceptance_report,
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
    "CANONICAL_DONE_TYPES",
    "create_run_logger",
    "load_run_summary",
    "normalize_reward_components",
    "REQUIRED_EPISODE_FIELDS",
    "REQUIRED_STEP_FIELDS",
    "run_acceptance_check",
    "SUMMARY_METRIC_KEYS",
    "validate_run_directory",
    "write_acceptance_report",
]
