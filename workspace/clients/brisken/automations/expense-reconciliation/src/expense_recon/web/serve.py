"""`expense-recon-web` console entry point.

Launches the JSON API server with uvicorn (the browser UI is the
Lovable-hosted SPA; this server answers JSON + file downloads only).
Defaults to 127.0.0.1 (loopback only) so the API is reachable from the
machine running it and nowhere else, all of Brisken's financial data
stays on that machine.

    expense-recon-web                       # http://127.0.0.1:8000 (docs at /docs)
    expense-recon-web --port 9000
    expense-recon-web --data ./my-runs      # where runs + the db live
"""
from __future__ import annotations

import argparse
import os
import sys
import webbrowser
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="expense-recon-web",
        description="JSON API server for the Brisken expense reconciliation tool.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default loopback).")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default 8000).")
    parser.add_argument(
        "--data",
        default=os.environ.get("EXPENSE_RECON_WEB_DATA", "recon-web-data"),
        help="Directory for the run database + uploaded/generated files.",
    )
    parser.add_argument(
        "--no-open", action="store_true", help="Do not open the browser on start."
    )
    args = parser.parse_args(argv)

    try:
        import uvicorn
    except ModuleNotFoundError:
        print(
            "The web UI needs the optional 'web' dependencies. Install with:\n"
            "  uv sync --extra web\n"
            "or\n"
            "  pip install 'expense-recon[web]'",
            file=sys.stderr,
        )
        return 1

    os.environ["EXPENSE_RECON_WEB_DATA"] = str(Path(args.data).resolve())

    url = f"http://{args.host}:{args.port}"
    print(f"Brisken expense reconciliation API: {url} (docs at {url}/docs)")
    print(f"Run data: {os.environ['EXPENSE_RECON_WEB_DATA']}")
    if not args.no_open:
        try:
            webbrowser.open(f"{url}/docs")
        except Exception:
            pass

    # Import string so uvicorn can manage the app lifecycle; the factory
    # reads EXPENSE_RECON_WEB_DATA set above.
    uvicorn.run(
        "expense_recon.web.app:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
