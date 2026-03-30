"""Launch the local CRE dashboard server."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _training_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ensure_training_root_on_path() -> None:
    root = _training_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local CRE monitoring dashboard.")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host address for the local dashboard server.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port for the local dashboard server.",
    )
    parser.add_argument(
        "--logs-root",
        default=str(_training_root() / "logs"),
        help="Primary accepted-run logs root.",
    )
    parser.add_argument(
        "--reports-root",
        default=str(_training_root() / "reports"),
        help="Primary analysis reports root.",
    )
    parser.add_argument(
        "--watch-root",
        action="append",
        default=[],
        help="Additional work root to scan for logs, reports, and smoke summaries.",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable uvicorn auto-reload.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _ensure_training_root_on_path()

    try:
        import uvicorn
    except Exception as exc:  # pragma: no cover - environment dependent
        raise SystemExit(f"uvicorn is required to launch the dashboard: {exc}") from exc

    from dashboard.app import create_dashboard_app

    app = create_dashboard_app(
        logs_root=Path(args.logs_root),
        reports_root=Path(args.reports_root),
        watch_roots=[Path(path) for path in args.watch_root],
    )

    uvicorn.run(app, host=args.host, port=int(args.port), reload=bool(args.reload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
