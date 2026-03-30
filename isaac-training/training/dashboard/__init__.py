"""CRE local dashboard helpers."""

from .state import build_dashboard_state

__all__ = ["build_dashboard_state", "create_dashboard_app"]


def create_dashboard_app(*args, **kwargs):
    from .app import create_dashboard_app as _create_dashboard_app

    return _create_dashboard_app(*args, **kwargs)
