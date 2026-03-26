"""Pipeline placeholder for top-level CRE orchestration."""

from dataclasses import dataclass


@dataclass
class PipelineConfig:
    """Minimal top-level pipeline configuration."""

    run_id: str = "cre_pipeline_v0"


def run_pipeline(*_args, **_kwargs):
    raise NotImplementedError("Top-level pipeline execution is not implemented yet.")

