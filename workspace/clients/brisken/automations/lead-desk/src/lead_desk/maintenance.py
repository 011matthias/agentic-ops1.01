"""Data-maintenance ops for the Lead Desk volume (idempotent, non-sending).

``clean-orphan-state`` removes result/report state-KV rows left behind when a
campaign is deleted. The web app writes ``approval:{cid}`` / ``sending-started:
{cid}`` / ``upload-report:{cid}`` / ``approve-result:{cid}`` / ``start-result:
{cid}`` as it drives a campaign; deleting a test campaign (test-gate, test-ndr,
...) drops its ``campaigns`` row but not these keys, so they accumulate as
orphans keyed on a campaign id that no longer exists.

Only those five prefixes are in scope, and only when the trailing campaign id
is NOT in ``campaigns``. ``kill_switch``, ``worker_heartbeat``, ``source:*``
and ``approval-superseded:*`` are never touched. Idempotent: a second run
finds nothing and is a no-op.

    lead-desk-maint clean-orphan-state --data /data --dry-run
    lead-desk-maint clean-orphan-state --data /data
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from .web.store import ContactStore

# State-key prefixes tied to a campaign lifecycle. Each key is
# ``<prefix><campaign_id>``; the row is an orphan when that campaign is gone.
ORPHAN_STATE_PREFIXES = (
    "approval:",
    "sending-started:",
    "upload-report:",
    "approve-result:",
    "start-result:",
)


def find_orphan_state_keys(store: ContactStore) -> list[str]:
    """State keys under the campaign-lifecycle prefixes whose campaign id is
    no longer present in ``campaigns``. Sorted, deduped."""
    live = store.campaign_ids()
    orphans: list[str] = []
    for prefix in ORPHAN_STATE_PREFIXES:
        for key in store.state_keys_with_prefix(prefix):
            cid = key[len(prefix):]
            if cid and cid not in live:
                orphans.append(key)
    return sorted(set(orphans))


def clean_orphan_state(store: ContactStore, dry_run: bool = False) -> dict:
    keys = find_orphan_state_keys(store)
    deleted: list[str] = []
    if not dry_run:
        for key in keys:
            if store.delete_state(key):
                deleted.append(key)
    return {
        "dry_run": dry_run,
        "orphan_keys": keys,
        "orphan_count": len(keys),
        "deleted": deleted if not dry_run else [],
        "deleted_count": len(deleted),
        "live_campaigns": sorted(store.campaign_ids()),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lead-desk-maint")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("clean-orphan-state",
                       help="delete state-KV rows for deleted campaigns")
    c.add_argument("--data", default=os.environ.get("LEAD_DESK_DATA", "lead-desk-data"))
    c.add_argument("--dry-run", action="store_true",
                   help="report the orphan keys without deleting")
    args = p.parse_args(argv)

    db = Path(args.data).resolve() / "lead-desk.sqlite"
    if not db.exists():
        print(f"ERROR: db not found: {db}")
        return 1
    with ContactStore(db) as store:
        report = clean_orphan_state(store, dry_run=args.dry_run)
    for k, v in report.items():
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
