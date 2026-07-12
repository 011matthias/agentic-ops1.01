"""``lead-desk-web`` console entry point.

Launches the Lead Desk server with uvicorn. Defaults to 127.0.0.1 so local
use is loopback-only (no gate needed); the hosted container binds 0.0.0.0.

    lead-desk-web                      # http://127.0.0.1:8000
    lead-desk-web --port 9000
    lead-desk-web --data ./ld-data     # where the SQLite db lives
"""
from __future__ import annotations

import argparse
import os
import sys
import webbrowser
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lead-desk-web",
        description="Browser UI for the Brisken Lead Desk lead-gen tracker.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default loopback).")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default 8000).")
    parser.add_argument(
        "--data",
        default=os.environ.get("LEAD_DESK_DATA", "lead-desk-data"),
        help="Directory for the SQLite database.",
    )
    parser.add_argument("--no-open", action="store_true", help="Do not open the browser on start.")
    args = parser.parse_args(argv)

    try:
        import uvicorn
    except ModuleNotFoundError:
        print(
            "The web UI needs the optional 'web' dependencies. Install with:\n"
            "  uv pip install '.[web]'",
            file=sys.stderr,
        )
        return 1

    os.environ["LEAD_DESK_DATA"] = str(Path(args.data).resolve())

    url = f"http://{args.host}:{args.port}"
    print(f"Brisken Lead Desk UI: {url}")
    print(f"Data: {os.environ['LEAD_DESK_DATA']}")
    if not args.no_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    uvicorn.run(
        "lead_desk.web.app:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
