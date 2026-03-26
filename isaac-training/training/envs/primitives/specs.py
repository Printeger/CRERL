"""Transitional primitive schema exports.

During migration, the canonical dataclass definitions still live in
`envs.env_gen`. This module provides the stable import path that future code
should use.
"""

from envs.env_gen import (
    ALLOWED_PRIMITIVE_TYPES,
    ALLOWED_SEMANTIC_ROLES,
    ALLOWED_SUPPORT_MODES,
    ArenaConfig,
    CREScenarioFamily,
    CREScenarioMetadata,
    CREScenarioRequest,
    PrimitiveSpec,
    SceneMode,
    SpawnObstacle,
)

__all__ = [
    "ALLOWED_PRIMITIVE_TYPES",
    "ALLOWED_SEMANTIC_ROLES",
    "ALLOWED_SUPPORT_MODES",
    "ArenaConfig",
    "CREScenarioFamily",
    "CREScenarioMetadata",
    "CREScenarioRequest",
    "PrimitiveSpec",
    "SceneMode",
    "SpawnObstacle",
]

