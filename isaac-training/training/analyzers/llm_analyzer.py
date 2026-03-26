"""Compatibility entrypoint for LLM-backed semantic analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from analyzers.semantic_analyzer import run_semantic_analysis_with_provider_mode


def run_llm_analysis(
    *,
    static_bundle_dir: str | Path,
    dynamic_bundle_dir: str | Path,
    provider_mode: str = "mock",
    provider_config: Optional[Mapping[str, Any]] = None,
    spec_cfg_dir=None,
    env_cfg_dir=None,
    detector_cfg_dir=None,
    scene_families: Sequence[str] | None = None,
    output_path: str | Path | None = None,
):
    """Run the semantic analyzer through a named provider mode.

    Phase 6 keeps the implementation evidence-first:
    - semantic inputs are still built from static + dynamic bundles
    - the provider only proposes claims
    - crosscheck still determines support status
    """

    return run_semantic_analysis_with_provider_mode(
        static_bundle_dir=static_bundle_dir,
        dynamic_bundle_dir=dynamic_bundle_dir,
        provider_mode=provider_mode,
        provider_config=provider_config,
        spec_cfg_dir=spec_cfg_dir,
        env_cfg_dir=env_cfg_dir,
        detector_cfg_dir=detector_cfg_dir,
        scene_families=scene_families,
        output_path=output_path,
    )


__all__ = ["run_llm_analysis"]
