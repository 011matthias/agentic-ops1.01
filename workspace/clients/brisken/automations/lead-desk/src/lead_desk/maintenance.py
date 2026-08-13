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

``suppression-import`` loads an external suppression list (CSV cols
value,kind,reason,source) into the ``suppression_entries`` ledger the send
guards check, and suppresses any matching CONTACT that is not already
suppressed. ``truth-audit`` reports event-provenance health (non-imid
ext_keys, open unmatched, suppression size, recent truth runs) - a report,
never a gate.

    lead-desk-maint clean-orphan-state --data /data --dry-run
    lead-desk-maint clean-orphan-state --data /data
    lead-desk-maint suppression-import --data /data --csv list.csv [--apply]
    lead-desk-maint truth-audit --data /data
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from collections import defaultdict
from pathlib import Path

from .identity import contact_id_for, natural_key
from .web.service import now_iso
from .web.store import CONTACT_COLUMNS, ContactStore

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


# Suppression reasons ranked most-restrictive first (permanent consent blocks,
# then exclusion tiers, then the revisitable hold). Used to pick the winning
# reason when merging duplicate contacts.
_SUPPRESS_PRIORITY = (
    "no_consent", "stop", "do_not_contact", "bounced",
    "duplicate", "test", "organiser", "own_team", "unreachable", "anon", "held",
)


def _strongest_reason(reasons: set[str]) -> str | None:
    for r in _SUPPRESS_PRIORITY:
        if r in reasons:
            return r
    return next(iter(sorted(reasons)), None)


def _merge_anon_group(store: ContactStore, members: list[dict],
                      new_nk: str, new_cid: str, now: str) -> None:
    """Collapse an anon-contact group onto one canonical row at (new_cid,new_nk),
    repointing events + enrollments and unioning suppression most-restrictively."""
    survivor = next((m for m in members if m["contact_id"] == new_cid), None)
    if survivor is None:
        base = members[0]
        data = {k: base[k] for k in CONTACT_COLUMNS if k in base.keys()}
        data["contact_id"] = new_cid
        data["natural_key"] = new_nk
        store.upsert_contact(data, now)
    elif survivor["natural_key"] != new_nk:
        store.conn.execute("UPDATE contacts SET natural_key = ? WHERE contact_id = ?",
                           (new_nk, new_cid))

    reasons = {m["suppress_reason"] for m in members
               if m["suppressed"] and m["suppress_reason"]}
    for old in members:
        oc = old["contact_id"]
        if oc == new_cid:
            continue
        # events: plain UPDATE moves every row (event_hash embeds the old
        # contact_id, so no collision with the canonical's own events).
        store.conn.execute(
            "UPDATE outreach_events SET contact_id = ? WHERE contact_id = ?", (new_cid, oc))
        # enrollments: OR IGNORE past the UNIQUE(contact_id,campaign_id), then
        # drop any that could not move because the canonical is already enrolled.
        store.conn.execute(
            "UPDATE OR IGNORE enrollments SET contact_id = ? WHERE contact_id = ?", (new_cid, oc))
        store.conn.execute("DELETE FROM enrollments WHERE contact_id = ?", (oc,))
        store.conn.execute("DELETE FROM contacts WHERE contact_id = ?", (oc,))
    if reasons:
        store.conn.execute(
            "UPDATE contacts SET suppressed = 1, suppress_reason = ?, "
            "suppressed_at = COALESCE(suppressed_at, ?), "
            "suppressed_by = COALESCE(suppressed_by, 'rekey'), updated_at = ? "
            "WHERE contact_id = ?",
            (_strongest_reason(reasons), now, now, new_cid))
    store.conn.commit()


def rekey_anon_contacts(store: ContactStore, dry_run: bool = False) -> dict:
    """Re-key NAMED email-less (anon) contacts onto the stable content key
    (name+company, no row-ordinal) and merge the duplicates the old ordinal key
    created. Idempotent: a second run finds every named anon contact already at
    its content key and changes nothing. Event count is invariant (events are
    repointed, never dropped); contact/enrollment counts fall by the dupes.

    NAMELESS org-only rows (TA Cook PII-withheld opt-outs recorded company-only)
    are deliberately EXCLUDED: they are indistinguishable by content, so a merge
    would collapse distinct attendees into one and lose the org headcount. They
    keep their ordinal key (see identity.natural_key) and are left untouched."""
    anon = store.conn.execute(
        "SELECT * FROM contacts WHERE natural_key LIKE 'anon:%' "
        "AND (TRIM(COALESCE(first_name,'')) != '' OR TRIM(COALESCE(last_name,'')) != '') "
        "ORDER BY created_at, contact_id"
    ).fetchall()
    groups: dict[str, list[dict]] = defaultdict(list)
    for c in anon:
        nk = natural_key(None, c["first_name"], c["last_name"], c["company"])
        groups[nk].append(dict(c))

    changes = []
    for new_nk, members in groups.items():
        new_cid = contact_id_for(new_nk)
        stable = (len(members) == 1 and members[0]["contact_id"] == new_cid
                  and members[0]["natural_key"] == new_nk)
        if stable:
            continue
        changes.append({
            "new_nk": new_nk, "new_cid": new_cid, "size": len(members),
            "members": members,
            "old_cids": [m["contact_id"] for m in members if m["contact_id"] != new_cid],
        })

    events_before = store.count_events()
    contacts_before = store.count_contacts()
    if not dry_run:
        for ch in changes:
            _merge_anon_group(store, ch["members"], ch["new_nk"], ch["new_cid"], now_iso())

    return {
        "dry_run": dry_run,
        "anon_total": len(anon),
        "groups_changed": len(changes),
        "contacts_removed": (0 if dry_run
                             else contacts_before - store.count_contacts()),
        "events_before": events_before,
        "events_after": store.count_events(),
        "events_unchanged": events_before == store.count_events(),
        "changed": [{"new_cid": c["new_cid"], "size": c["size"],
                     "merged_away": c["old_cids"]} for c in changes],
    }


def _suppression_entry(row: dict) -> tuple[str, str, str, str] | None:
    """(entry, kind, source, note) for one CSV row, normalized to the
    suppression_entries convention (emails bare lowercase, domains as
    '@domain' lowercase), or None for a blank value."""
    value = (row.get("value") or "").strip().lower()
    if not value:
        return None
    kind = (row.get("kind") or "").strip().lower()
    if kind not in ("email", "domain"):
        kind = "email" if "@" in value.lstrip("@") else "domain"
    entry = value if kind == "email" else "@" + value.lstrip("@")
    return (entry, kind, (row.get("source") or "").strip() or "external",
            (row.get("reason") or "").strip() or None)


def suppression_import(store: ContactStore, csv_path: Path,
                       apply: bool = False) -> dict:
    """Load an external suppression list (cols value,kind,reason,source)
    into ``suppression_entries`` (INSERT OR IGNORE) and suppress every
    matching, not-yet-suppressed contact (email exact for email rows; email
    domain for domain rows). Dry-run (default) counts, writes nothing.
    Idempotent: a second apply finds every entry existing and no contact
    left to suppress."""
    now = now_iso()
    rows = skipped = entries_new = entries_existing = 0
    contacts_suppressed = 0
    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            rows += 1
            norm = _suppression_entry(row)
            if norm is None:
                skipped += 1
                continue
            entry, kind, source, note = norm
            if apply:
                new = store.add_suppression_entry(entry, kind, source, now, note)
            else:
                new = store.conn.execute(
                    "SELECT 1 FROM suppression_entries WHERE entry = ?",
                    (entry,)).fetchone() is None
            entries_new += int(new)
            entries_existing += int(not new)
            if kind == "email":
                c = store.find_by_email(entry)
                hits = [c] if c is not None and not c["suppressed"] else []
            else:
                hits = store.conn.execute(
                    "SELECT * FROM contacts WHERE suppressed = 0 "
                    "AND merged_into IS NULL AND lower(email) LIKE ?",
                    ("%" + entry,)).fetchall()
            for contact in hits:
                if apply:
                    store.set_suppressed(contact["contact_id"], True,
                                         "external-suppression-list",
                                         "suppression-import", now)
                contacts_suppressed += 1
    return {"dry_run": not apply, "csv": str(csv_path), "rows": rows,
            "skipped_blank": skipped, "entries_new": entries_new,
            "entries_existing": entries_existing,
            "contacts_suppressed": contacts_suppressed}


def truth_audit(store: ContactStore) -> dict:
    """Event-provenance health report: outbound events not keyed on an
    internetMessageId ('<...@...>'), the open unmatched queue, the
    suppression ledger size, and the last truth runs. A report, not a gate."""
    non_imid = store.conn.execute(
        "SELECT source, COUNT(*) AS n FROM outreach_events "
        "WHERE direction = 'outbound' "
        "AND (ext_key IS NULL OR ext_key NOT LIKE '<%@%>') "
        "GROUP BY source ORDER BY n DESC").fetchall()
    runs = store.conn.execute(
        "SELECT run_id, kind, finished_at, events_added FROM truth_runs "
        "ORDER BY finished_at DESC LIMIT 5").fetchall()
    return {
        "non_imid_outbound": {"total": sum(r["n"] for r in non_imid),
                              "by_source": {r["source"]: r["n"]
                                            for r in non_imid}},
        "unmatched_open": store.conn.execute(
            "SELECT COUNT(*) FROM unmatched_events WHERE status = 'open'"
        ).fetchone()[0],
        "suppression_entries": store.conn.execute(
            "SELECT COUNT(*) FROM suppression_entries").fetchone()[0],
        "recent_truth_runs": [dict(r) for r in runs],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lead-desk-maint")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("clean-orphan-state",
                       help="delete state-KV rows for deleted campaigns")
    c.add_argument("--data", default=os.environ.get("LEAD_DESK_DATA", "lead-desk-data"))
    c.add_argument("--dry-run", action="store_true",
                   help="report the orphan keys without deleting")
    rk = sub.add_parser("rekey-anon",
                        help="re-key email-less contacts to the stable content key + merge dupes")
    rk.add_argument("--data", default=os.environ.get("LEAD_DESK_DATA", "lead-desk-data"))
    rk.add_argument("--dry-run", action="store_true",
                    help="report the merge plan without changing anything")
    si = sub.add_parser("suppression-import",
                        help="load an external suppression CSV into the "
                             "ledger + suppress matching contacts")
    si.add_argument("--data", default=os.environ.get("LEAD_DESK_DATA", "lead-desk-data"))
    si.add_argument("--csv", required=True, help="CSV with value,kind,reason,source")
    si.add_argument("--apply", action="store_true",
                    help="write (default is a dry-run count)")
    ta = sub.add_parser("truth-audit",
                        help="event-provenance health report (never a gate)")
    ta.add_argument("--data", default=os.environ.get("LEAD_DESK_DATA", "lead-desk-data"))
    args = p.parse_args(argv)

    db = Path(args.data).resolve() / "lead-desk.sqlite"
    if not db.exists():
        print(f"ERROR: db not found: {db}")
        return 1
    with ContactStore(db) as store:
        if args.cmd == "clean-orphan-state":
            report = clean_orphan_state(store, dry_run=args.dry_run)
        elif args.cmd == "rekey-anon":
            report = rekey_anon_contacts(store, dry_run=args.dry_run)
        elif args.cmd == "suppression-import":
            report = suppression_import(store, Path(args.csv), apply=args.apply)
        else:
            report = truth_audit(store)
    if args.cmd == "truth-audit":
        print(json.dumps(report, indent=1, default=str))
        return 0
    for k, v in report.items():
        print(f"{k}: {v}")
    if args.cmd == "rekey-anon" and not args.dry_run and not report["events_unchanged"]:
        print("ERROR: rekey changed the event count - investigate, do not deploy")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
