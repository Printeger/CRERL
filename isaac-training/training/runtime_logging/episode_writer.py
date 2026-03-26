"""Episode writing helpers.

This module is a thin transitional layer around `FlightEpisodeLogger`.
"""

from envs.cre_logging import FlightEpisodeLogger


def create_episode_writer(*args, **kwargs):
    """Return the current episode logger implementation."""

    return FlightEpisodeLogger(*args, **kwargs)

