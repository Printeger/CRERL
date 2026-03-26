"""Factory placeholders for future primitive-construction extraction.

The concrete construction logic still lives in `envs.env_gen` and will be
split out incrementally.
"""


class PrimitiveFactoryRegistry:
    """Placeholder registry for future primitive factory extraction."""

    def build(self, *_args, **_kwargs):
        raise NotImplementedError(
            "PrimitiveFactoryRegistry is a placeholder. "
            "Construction logic still lives in envs.env_gen."
        )

