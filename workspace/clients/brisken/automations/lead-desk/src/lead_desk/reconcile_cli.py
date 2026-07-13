"""CLI wrapper for the cadence reconcile pass (also run per worker tick).

Repairs lock-table/event-log drift: emits missing 'sent' events for acked
attempts, backfills attempt rows for orphan cadence events, and flips
expired leases to 'stalled' (surfaced on the board for a human decision).

    lead-desk-reconcile --data /data
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from .web import cadence
from .web.store import ContactStore


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lead-desk-reconcile")
    p.add_argument("--data", default=os.environ.get("LEAD_DESK_DATA", "lead-desk-data"))
    args = p.parse_args(argv)
    db = Path(args.data).resolve() / "lead-desk.sqlite"
    if not db.exists():
        print(f"ERROR: db not found: {db}")
        return 1
    with ContactStore(db) as store:
        report = cadence.reconcile(store)
    for k, v in report.items():
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
