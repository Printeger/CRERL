"""ASGI app for the local CRE monitoring dashboard."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

try:  # pragma: no cover - exercised in NavRL environment
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
    from fastapi.templating import Jinja2Templates

    _APP_BACKEND = "fastapi"
except Exception:  # pragma: no cover - fallback for current repo env
    from starlette.applications import Starlette as FastAPI
    from starlette.requests import Request
    from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse
    from starlette.templating import Jinja2Templates

    _APP_BACKEND = "starlette"

from dashboard.state import DEFAULT_LOGS_ROOT, DEFAULT_REPORTS_ROOT, build_dashboard_state


TEMPLATE_ROOT = Path(__file__).resolve().parent / "templates"


def _register_filters(templates: Jinja2Templates) -> None:
    templates.env.filters["asjson"] = lambda value: json.dumps(value, ensure_ascii=False)


def _config_dict(
    *,
    logs_root: str | Path,
    reports_root: str | Path,
    watch_roots: Sequence[str | Path] | None,
    include_default_watch_roots: bool,
) -> dict[str, Any]:
    return {
        "logs_root": str(logs_root),
        "reports_root": str(reports_root),
        "watch_roots": [str(path) for path in (watch_roots or [])],
        "include_default_watch_roots": bool(include_default_watch_roots),
    }


def create_dashboard_app(
    *,
    logs_root: str | Path = DEFAULT_LOGS_ROOT,
    reports_root: str | Path = DEFAULT_REPORTS_ROOT,
    watch_roots: Sequence[str | Path] | None = None,
    include_default_watch_roots: bool = True,
) -> Any:
    """Create the local dashboard app.

    The implementation prefers FastAPI when the environment supports it, but
    falls back to Starlette in the current NavRL environment where FastAPI's
    pydantic dependency chain is not healthy. The HTTP surface is intentionally
    the same either way.
    """

    app = FastAPI()
    templates = Jinja2Templates(directory=str(TEMPLATE_ROOT))
    _register_filters(templates)
    config = _config_dict(
        logs_root=logs_root,
        reports_root=reports_root,
        watch_roots=watch_roots,
        include_default_watch_roots=include_default_watch_roots,
    )

    def _build_state() -> dict[str, Any]:
        return build_dashboard_state(
            logs_root=config["logs_root"],
            reports_root=config["reports_root"],
            watch_roots=config["watch_roots"],
            include_default_watch_roots=bool(config["include_default_watch_roots"]),
        )

    async def homepage(request: Request):
        state = _build_state()
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "state": state,
                "backend": _APP_BACKEND,
                "config": config,
            },
        )

    async def overview_partial(request: Request):
        return templates.TemplateResponse(
            "partials/overview.html",
            {"request": request, "state": _build_state()},
        )

    async def live_partial(request: Request):
        return templates.TemplateResponse(
            "partials/live_grid.html",
            {"request": request, "state": _build_state()},
        )

    async def charts_partial(request: Request):
        return templates.TemplateResponse(
            "partials/charts.html",
            {"request": request, "state": _build_state()},
        )

    async def api_state(_: Request):
        return JSONResponse(_build_state())

    async def health(_: Request):
        return PlainTextResponse("ok")

    if _APP_BACKEND == "fastapi":  # pragma: no cover - same behavior via Starlette tests
        app.get("/", response_class=HTMLResponse)(homepage)
        app.get("/partials/overview", response_class=HTMLResponse)(overview_partial)
        app.get("/partials/live", response_class=HTMLResponse)(live_partial)
        app.get("/partials/charts", response_class=HTMLResponse)(charts_partial)
        app.get("/api/state")(api_state)
        app.get("/healthz", response_class=PlainTextResponse)(health)
    else:  # pragma: no cover - exercised in NavRL environment
        app.add_route("/", homepage)
        app.add_route("/partials/overview", overview_partial)
        app.add_route("/partials/live", live_partial)
        app.add_route("/partials/charts", charts_partial)
        app.add_route("/api/state", api_state)
        app.add_route("/healthz", health)

    app.state.dashboard_config = config
    app.state.dashboard_backend = _APP_BACKEND
    return app


__all__ = ["create_dashboard_app"]
