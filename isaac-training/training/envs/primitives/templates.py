"""Template metadata placeholders for gradual extraction from `env_gen.py`."""

SUPPORTED_TEMPLATE_TYPES = (
    "bottleneck",
    "clutter_cluster",
    "perforated_barrier",
    "low_clearance_passage",
    "pillar_field",
    "moving_crossing",
    "box_field",
    "slab_field",
    "perforated_field",
    "dynamic_field",
)


def list_supported_template_types():
    """Return the current template names recognized by the scene backend."""

    return list(SUPPORTED_TEMPLATE_TYPES)

