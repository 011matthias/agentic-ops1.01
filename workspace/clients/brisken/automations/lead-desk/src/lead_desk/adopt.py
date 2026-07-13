"""Adopt legacy contacts into the campaign-engine model (idempotent).

Creates the campaign row for an EXISTING contact cohort (default: the Rome
290) with ``status='done'`` - the outbox claims only from 'approved'
campaigns, so an adopted historical campaign can never auto-send - and
enrolls every contact carrying that legacy ``contacts.campaign`` tag. Degree
stays NULL (unclassified); the event history is untouched (verified by the
event-count assertion).

    lead-desk-adopt --data /data                 # on the Fly volume
    lead-desk-adopt --data ../../.scratch/lead-desk-data --campaign rome-2026
"""
from __future__ import annotations

import argparse
import os
from collections import Counter
from pathlib import Path

from .web.service import now_iso
from .web.store import ContactStore


def adopt(store: ContactStore, campaign_id: str, name: str) -> dict:
    events_before = store.count_events()
    stages_before = Counter(r["stage"] for r in store.board_rows(campaign_id))
    now = now_iso()

    store.create_campaign(campaign_id, name, now, status="done")
    contacts = store.conn.execute(
        "SELECT contact_id, created_at FROM contacts WHERE campaign = ?",
        (campaign_id,),
    ).fetchall()
    enrolled = 0
    for c in contacts:
        cur = store.conn.execute(
            "INSERT OR IGNORE INTO enrollments "
            "(contact_id, campaign_id, enrolled_at, enrolled_by) VALUES (?, ?, ?, ?)",
            (c["contact_id"], campaign_id, c["created_at"], "adopt"),
        )
        enrolled += cur.rowcount
    store.conn.commit()

    total = store.conn.execute(
        "SELECT COUNT(*) FROM enrollments WHERE campaign_id = ?", (campaign_id,)
    ).fetchone()[0]
    events_after = store.count_events()
    stages_after = Counter(r["stage"] for r in store.board_rows(campaign_id))
    return {
        "campaign": campaign_id,
        "contacts": len(contacts),
        "newly_enrolled": enrolled,
        "total_enrollments": total,
        "events_unchanged": events_before == events_after,
        "stages_unchanged": stages_before == stages_after,
        "stage_distribution": dict(stages_after),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lead-desk-adopt")
    p.add_argument("--data", default=os.environ.get("LEAD_DESK_DATA", "lead-desk-data"))
    p.add_argument("--campaign", default="rome-2026")
    p.add_argument("--name", default="Rome 2026")
    args = p.parse_args(argv)

    db = Path(args.data).resolve() / "lead-desk.sqlite"
    if not db.exists():
        print(f"ERROR: db not found: {db}")
        return 1
    with ContactStore(db) as store:
        report = adopt(store, args.campaign, args.name)
    for k, v in report.items():
        print(f"{k}: {v}")
    if not (report["events_unchanged"] and report["stages_unchanged"]):
        print("ERROR: adoption disturbed history - investigate before deploying")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
