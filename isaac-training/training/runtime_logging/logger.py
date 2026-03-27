"""Stable logger exports for the CRE runtime pipeline."""

import os
from pathlib import Path
from typing import Mapping, Optional, Any

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


def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() not in {"0", "false", "no", "off"}


def create_run_logger(
    *,
    source: str,
    run_name: str,
    base_dir: Optional[str | Path] = None,
    near_violation_distance: float = 0.5,
    use_timestamp: bool = True,
    schema_version: str = SCHEMA_VERSION,
    run_metadata: Optional[Mapping[str, Any]] = None,
) -> FlightEpisodeLogger:
    resolved_run_name = os.environ.get("CRE_RUN_NAME_OVERRIDE", run_name)
    resolved_base_dir = os.environ.get("CRE_RUN_LOG_BASE_DIR")
    resolved_use_timestamp = _env_flag("CRE_RUN_USE_TIMESTAMP", use_timestamp)
    return FlightEpisodeLogger(
        run_name=resolved_run_name,
        base_dir=resolved_base_dir if resolved_base_dir is not None else base_dir,
        near_violation_distance=near_violation_distance,
        use_timestamp=resolved_use_timestamp,
        source=source,
        schema_version=schema_version,
        run_metadata=run_metadata,
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
