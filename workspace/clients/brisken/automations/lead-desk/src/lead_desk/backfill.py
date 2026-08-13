"""Backfill the outreach-truth ledger into the Lead Desk event log.

The truth sweep (``tools/brisken-truth-sweep.py``) reconciled every historical
send against the two allowlisted mailboxes and wrote a per-cohort ledger with
per-member evidence (imid, ts, folder, mailbox). This module replays that
evidence into ``outreach_events`` so the DB matches mailbox truth
(feedback_brisken_outreach_truth_is_mailbox): one outbound ``sent`` event per
evidence message, keyed on the internetMessageId, so re-runs and live capture
dedupe against the same basis.

Hard rules (mirroring ground.py):
- Contacts only: a roster member with no matching contact is parked in the
  unmatched queue (same path ingest_event uses), NEVER auto-created
  (owner 2026-07-14).
- Evidence only: an event is written only from an imid-carrying evidence
  entry. Members whose ledger flags say replied/OOO but carry no message
  evidence are counted in the report, not fabricated into events (B4).
- Inbound mapping matches capture.inbox_to_payloads: a genuine reply is
  ``type='reply'``; an OOO auto-reply is a low-signal ``type='note'`` (does
  not promote the stage, does not halt a cadence).
- H5 is judged by mailbox silence only: sent events carry
  ``detail.cohort='H5'`` and NO negative/derived state is ever emitted.
- Confirm-zero cohorts and held sets produce NO events; their names+methods
  ride in the run report only.

BUILD ONLY: this CLI mutates nothing until ``--apply``, and the production
run happens only after an owner signs the ledger.

    lead-desk-backfill --truth ledger.json --data ./lead-desk-data            # dry-run
    lead-desk-backfill --truth ledger.json --data ./lead-desk-data --apply
    lead-desk-backfill --truth ledger.json --data ./lead-desk-data --verify
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from uuid import uuid4

from .web.service import now_iso
from .web.store import ContactStore, event_hash

# Canonical short cohort name -> the ledger's cohorts key. Selection via
# --cohort accepts either spelling.
COHORT_KEYS = {
    "E1": "E1",
    "E2": "E2",
    "E3": "E3",
    "T1": "T1_booth_network",
    "T2": "T2_warm_engaged",
    "H5": "H5_hottest_leads",
    "T3": "T3",
    "GA": "GA",
}
# Every current cohort belongs to the Rome campaign; a future sweep adds its
# mapping here before it can backfill.
COHORT_CAMPAIGN = {short: "rome-2026" for short in COHORT_KEYS}

# During-event waves whose sends may already exist as ground.py-era synthetic
# events (ext_key 'de-{wave}-{cid}', ground.py:148-153).
EWAVES = ("E1", "E2", "E3")

# Ledger member bookkeeping keys. Anything else on a member is a per-member
# flag (e.g. a future 'misrouted': true) and rides into the sent detail JSON.
MEMBER_BASE_KEYS = frozenset({
    "sent", "evidence", "replied", "ooo", "ooo_only", "reply_evidence",
    "last_reply", "first_send", "last_send", "send_count", "draft_pending",
})

# Cohorts that are held sets, not send rosters: never events, report only.
HELD_COHORT_KEYS = ("dirk_exclusions",)


def sweep_id(ledger: dict) -> str:
    """The ledger's run identity for ``created_by``. The ledger carries no
    single id field; (tool, generated_at) is the sweep's identity."""
    return f"{ledger.get('tool') or 'truth-sweep'}@{ledger.get('generated_at') or '?'}"


def iter_cohorts(ledger: dict, selected: list[str] | None = None):
    """Yield (short_name, cohort_dict) for the selected (default: all known)
    roster cohorts present in the ledger. Raises ValueError on an unknown
    selection so a typo cannot silently backfill nothing."""
    by_ledger_key = {v: k for k, v in COHORT_KEYS.items()}
    if selected:
        shorts: list[str] = []
        for name in selected:
            short = name.upper() if name.upper() in COHORT_KEYS \
                else by_ledger_key.get(name)
            if short is None:
                raise ValueError(f"unknown cohort {name!r} "
                                 f"(known: {', '.join(COHORT_KEYS)})")
            shorts.append(short)
    else:
        shorts = list(COHORT_KEYS)
    cohorts = ledger.get("cohorts") or {}
    for short in shorts:
        cohort = cohorts.get(COHORT_KEYS[short])
        if isinstance(cohort, dict) and isinstance(cohort.get("members"), dict):
            yield short, cohort


def _member_flags(member: dict) -> dict:
    return {k: v for k, v in member.items() if k not in MEMBER_BASE_KEYS}


def _detail(short: str, ev: dict, flags: dict | None = None) -> str:
    d = {"cohort": short, "folder": ev.get("folder"),
         "mailbox": ev.get("mailbox"), **(flags or {})}
    return json.dumps(d, sort_keys=True)


def member_outbound(short: str, email: str, member: dict) -> list[dict]:
    """A member's send evidence -> ingest-compatible 'sent' payloads (one per
    evidence message, imid-keyed). Evidence without an imid cannot be keyed
    and is skipped (the caller counts it)."""
    if not member.get("sent"):
        return []
    flags = _member_flags(member)
    out = []
    for ev in member.get("evidence") or []:
        if not ev.get("imid"):
            continue
        out.append({
            "email": email, "type": "sent", "direction": "outbound",
            "channel": "email", "occurred_at": ev.get("ts"),
            "subject": ev.get("subject"), "detail": _detail(short, ev, flags),
            "source": "truth-sweep", "internet_message_id": ev["imid"],
            "campaign": COHORT_CAMPAIGN[short],
        })
    return out


def member_inbound(short: str, email: str, member: dict) -> list[dict]:
    """A member's reply evidence -> inbound payloads, mapped exactly like
    capture.inbox_to_payloads: ``replied`` evidence is a genuine 'reply';
    OOO-only evidence is a low-signal 'note'. H5 never emits inbound (its
    judgment policy is mailbox-silence-only; no derived state)."""
    if short == "H5":
        return []
    type_ = "reply" if member.get("replied") \
        else "note" if (member.get("ooo") or member.get("ooo_only")) else None
    if type_ is None:
        return []
    out = []
    for ev in member.get("reply_evidence") or []:
        if not ev.get("imid"):
            continue
        out.append({
            "email": email, "type": type_, "direction": "inbound",
            "channel": "email", "occurred_at": ev.get("ts"),
            "subject": ev.get("subject"), "detail": _detail(short, ev),
            "source": "truth-sweep", "internet_message_id": ev["imid"],
            "campaign": COHORT_CAMPAIGN[short],
        })
    return out


def build_payloads(ledger: dict, cohorts: list[str] | None = None) -> list[dict]:
    """Every payload the ledger supports, for the POST /events channel (the
    server resolves contacts, dedupes, and parks unmatched)."""
    out: list[dict] = []
    for short, cohort in iter_cohorts(ledger, cohorts):
        for email, member in (cohort.get("members") or {}).items():
            out.extend(member_outbound(short, email, member))
            out.extend(member_inbound(short, email, member))
    return out


def report_only_sets(ledger: dict) -> dict:
    """Held sets + confirm-zero cohorts: names and methods for the run
    report. These produce NO events by design."""
    held: dict[str, dict] = {}
    cohorts = ledger.get("cohorts") or {}
    for key in HELD_COHORT_KEYS:
        c = cohorts.get(key)
        if isinstance(c, dict):
            held[key] = {"size": c.get("size"), "policy": c.get("policy")}
    ga = cohorts.get("GA") or {}
    if isinstance(ga.get("held4_check"), dict):
        held["ga_held"] = {"members": sorted(ga["held4_check"]),
                           "policy": "held from the GA wave"}
    confirm_zero = {name: (c or {}).get("method")
                    for name, c in (ledger.get("confirm_zero") or {}).items()}
    return {"held": held, "confirm_zero": confirm_zero}


def _event_exists(store: ContactStore, h: str) -> bool:
    return store.conn.execute(
        "SELECT 1 FROM outreach_events WHERE event_hash = ?", (h,)
    ).fetchone() is not None


def _dekey_row(store: ContactStore, contact_id: str, short: str):
    """The ground.py-era synthetic during-event send for this contact
    (ext_key 'de-{wave}-{cid}', ground.py:148-153), if present."""
    return store.conn.execute(
        "SELECT event_id FROM outreach_events "
        "WHERE contact_id = ? AND type = 'sent' AND ext_key = ?",
        (contact_id, f"de-{short}-{contact_id}"),
    ).fetchone()


def _insert_upgrade(store: ContactStore, payload: dict, contact_id: str,
                    created_by: str, de_event_id: int, now: str) -> bool:
    """ONE transaction: insert the imid-keyed sent event and delete the
    matching de-* synthetic row (net event count unchanged). Returns True
    when the imid event was newly inserted."""
    imid = payload["internet_message_id"]
    h = event_hash(contact_id, payload["occurred_at"], "email", "sent",
                   payload["detail"], imid)
    with store.conn:
        cur = store.conn.execute(
            "INSERT OR IGNORE INTO outreach_events "
            "(contact_id, campaign, ts, channel, direction, type, subject, "
            " detail, source, created_by, ext_key, created_at, event_hash) "
            "VALUES (?, ?, ?, 'email', 'outbound', 'sent', ?, ?, ?, ?, ?, ?, ?)",
            (contact_id, payload["campaign"], payload["occurred_at"],
             payload["subject"], payload["detail"], payload["source"],
             created_by, imid, now, h),
        )
        store.conn.execute("DELETE FROM outreach_events WHERE event_id = ?",
                           (de_event_id,))
    return cur.rowcount > 0


def _ingest_direct(store: ContactStore, payload: dict, contact_id: str,
                   created_by: str, now: str, apply: bool) -> bool:
    """One payload onto a known contact's timeline. Returns True when the
    event is new (would be inserted / was inserted)."""
    imid = payload["internet_message_id"]
    h = event_hash(contact_id, payload["occurred_at"], payload["channel"],
                   payload["type"], payload["detail"], imid)
    if not apply:
        return not _event_exists(store, h)
    return store.add_event(
        contact_id=contact_id, ts=payload["occurred_at"],
        channel=payload["channel"], direction=payload["direction"],
        type=payload["type"], subject=payload["subject"],
        detail=payload["detail"], source=payload["source"],
        created_by=created_by, ext_key=imid, campaign=payload["campaign"],
        now=now)


def _queue_unmatched(store: ContactStore, payload: dict, now: str,
                     apply: bool) -> None:
    """Park a payload whose address matches no contact - the same hash basis
    ingest_event uses (email standing in for the contact_id), so a later
    capture of the same message bumps the row instead of duplicating it."""
    if not apply:
        return
    h = event_hash(payload["email"], payload["occurred_at"],
                   payload["channel"], payload["type"], payload["detail"],
                   payload["internet_message_id"])
    store.record_unmatched(payload["email"],
                           json.dumps(payload, sort_keys=True), h, now)


def _zero_counts() -> dict:
    return {"members": 0, "sent_inserted": 0, "sent_deduped": 0,
            "queued_unmatched": 0, "skipped_dekey": 0, "upgraded_dekey": 0,
            "replies_inserted": 0, "ooo_notes_inserted": 0,
            "inbound_deduped": 0, "replied_no_evidence": 0,
            "ooo_no_evidence": 0, "skipped_no_imid": 0}


def backfill(store: ContactStore, ledger: dict, *,
             cohorts: list[str] | None = None, apply: bool = False,
             upgrade_ewave_keys: bool = False) -> dict:
    """Replay the ledger into the store. Dry-run (default) computes the same
    counts with zero writes. Apply also writes one truth_runs row
    (kind='backfill') carrying the full report."""
    created_by = sweep_id(ledger)
    started = now_iso()
    per_cohort: dict[str, dict] = {}
    for short, cohort in iter_cohorts(ledger, cohorts):
        c = _zero_counts()
        per_cohort[short] = c
        for email, member in (cohort.get("members") or {}).items():
            c["members"] += 1
            now = now_iso()
            outbound = member_outbound(short, email, member)
            inbound = member_inbound(short, email, member)
            if member.get("sent"):
                c["skipped_no_imid"] += sum(
                    1 for ev in member.get("evidence") or []
                    if not ev.get("imid"))
            if member.get("replied") and not inbound:
                c["replied_no_evidence"] += 1
            if (member.get("ooo") or member.get("ooo_only")) and not inbound \
                    and not member.get("replied"):
                c["ooo_no_evidence"] += 1

            row = store.find_by_email(email)
            if row is None:
                for payload in outbound + inbound:
                    _queue_unmatched(store, payload, now, apply)
                    c["queued_unmatched"] += 1
                continue
            cid = row["contact_id"]

            de_row = _dekey_row(store, cid, short) \
                if short in EWAVES and outbound else None
            if de_row is not None and not upgrade_ewave_keys:
                # The send already exists as the ground.py synthetic event;
                # inserting the imid event too would double-count it.
                c["skipped_dekey"] += 1
            else:
                for i, payload in enumerate(outbound):
                    if de_row is not None and i == 0:
                        h = event_hash(cid, payload["occurred_at"], "email",
                                       "sent", payload["detail"],
                                       payload["internet_message_id"])
                        inserted = not _event_exists(store, h)
                        if apply:
                            inserted = _insert_upgrade(
                                store, payload, cid, created_by,
                                de_row["event_id"], now)
                        c["upgraded_dekey"] += 1
                        c["sent_inserted" if inserted else "sent_deduped"] += 1
                        continue
                    if _ingest_direct(store, payload, cid, created_by, now, apply):
                        c["sent_inserted"] += 1
                    else:
                        c["sent_deduped"] += 1
            for payload in inbound:
                if _ingest_direct(store, payload, cid, created_by, now, apply):
                    c["replies_inserted" if payload["type"] == "reply"
                      else "ooo_notes_inserted"] += 1
                else:
                    c["inbound_deduped"] += 1

    totals = _zero_counts()
    for c in per_cohort.values():
        for k, v in c.items():
            totals[k] += v
    report = {
        "kind": "backfill", "apply": apply, "sweep_id": created_by,
        "upgrade_ewave_keys": upgrade_ewave_keys,
        "cohorts": per_cohort, "totals": totals, **report_only_sets(ledger),
    }
    if apply:
        events_added = (totals["sent_inserted"] + totals["replies_inserted"]
                        + totals["ooo_notes_inserted"])
        store.insert_truth_run(
            run_id=uuid4().hex, kind="backfill", started_at=started,
            finished_at=now_iso(), window_since=ledger.get("since") or "",
            corpus_messages=int((ledger.get("corpus") or {}).get("outbound") or 0),
            folders_scanned=0, folders_failed="[]",
            events_added=events_added, report=json.dumps(report, default=str))
    return report


def verify(store: ContactStore, ledger: dict,
           cohorts: list[str] | None = None) -> dict:
    """Diff DB aggregates against the ledger, cohort by cohort. A matched
    member's send counts when ANY of its evidence imids is on the contact's
    timeline, or (E-waves, without --upgrade-ewave-keys) when the ground.py
    de-* synthetic still represents it. Members with no contact are expected
    in the unmatched queue, not on a timeline, so they are excluded."""
    rows: list[dict] = []
    ok = True
    for short, cohort in iter_cohorts(ledger, cohorts):
        members = cohort.get("members") or {}
        matched = sent_exp = sent_db = reply_exp = reply_db = 0
        for email, member in members.items():
            evid = [e for e in (member.get("evidence") or []) if e.get("imid")] \
                if member.get("sent") else []
            revid = [e for e in (member.get("reply_evidence") or [])
                     if e.get("imid")] if member.get("replied") else []
            if not evid and not revid:
                continue
            row = store.find_by_email(email)
            if row is None:
                continue
            matched += 1
            cid = row["contact_id"]
            if evid:
                sent_exp += 1
                has = any(store.conn.execute(
                    "SELECT 1 FROM outreach_events WHERE contact_id = ? "
                    "AND type = 'sent' AND ext_key = ?",
                    (cid, e["imid"])).fetchone() for e in evid)
                if not has and short in EWAVES:
                    has = _dekey_row(store, cid, short) is not None
                sent_db += int(has)
            if revid and short != "H5":
                reply_exp += 1
                reply_db += int(any(store.conn.execute(
                    "SELECT 1 FROM outreach_events WHERE contact_id = ? "
                    "AND type = 'reply' AND ext_key = ?",
                    (cid, e["imid"])).fetchone() for e in revid))
        match = sent_exp == sent_db and reply_exp == reply_db
        ok = ok and match
        rows.append({"cohort": short, "members": len(members),
                     "matched": matched, "sent_expected": sent_exp,
                     "sent_in_db": sent_db, "replies_expected": reply_exp,
                     "replies_in_db": reply_db, "ok": match})
    return {"ok": ok, "cohorts": rows}


def _print_verify(v: dict) -> None:
    cols = ("cohort", "members", "matched", "sent_expected", "sent_in_db",
            "replies_expected", "replies_in_db", "ok")
    print("  ".join(f"{c:>16}" for c in cols))
    for r in v["cohorts"]:
        print("  ".join(f"{str(r[c]):>16}" for c in cols))
    print(f"verify: {'MATCH' if v['ok'] else 'MISMATCH'}")


def post_events(base_url: str, secret: str, payloads: list[dict]) -> dict:
    """POST the payloads through the /events sink (same auth as
    capture.post_events). The server resolves, dedupes, and parks unmatched;
    created_by and the de-* key upgrade are direct-mode-only."""
    import httpx
    r = httpx.post(
        f"{base_url.rstrip('/')}/events",
        headers={"Authorization": f"Bearer {secret}"},
        json=payloads, timeout=120,
    )
    r.raise_for_status()
    return r.json()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="lead-desk-backfill",
        description="Replay the outreach-truth ledger into the event log "
                    "(dry-run by default; the prod run waits on an "
                    "owner-signed ledger)")
    p.add_argument("--truth", required=True, help="outreach-truth-ledger.json")
    p.add_argument("--data", default=os.environ.get("LEAD_DESK_DATA",
                                                    "lead-desk-data"))
    p.add_argument("--cohort", nargs="+", metavar="NAME",
                   help="cohort subset (default: all), e.g. E1 GA H5")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true",
                   help="count everything, write nothing (the default)")
    g.add_argument("--apply", action="store_true", help="write the events")
    p.add_argument("--upgrade-ewave-keys", action="store_true",
                   help="replace ground.py de-{wave}-{cid} synthetic sends "
                        "with the imid-keyed event (net count unchanged)")
    p.add_argument("--verify", action="store_true",
                   help="diff DB aggregates vs the ledger (after apply, or "
                        "standalone); nonzero exit on any mismatch")
    p.add_argument("--base-url", help="POST through /events instead of "
                                      "writing the store directly")
    p.add_argument("--secret", help="ingest secret for --base-url")
    args = p.parse_args(argv)

    ledger = json.loads(Path(args.truth).read_text(encoding="utf-8"))
    try:
        list(iter_cohorts(ledger, args.cohort))
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    if args.base_url:
        if args.upgrade_ewave_keys:
            print("ERROR: --upgrade-ewave-keys needs direct --data mode")
            return 2
        if not args.secret:
            print("ERROR: --base-url needs --secret")
            return 2
        payloads = build_payloads(ledger, args.cohort)
        if not args.apply:
            print(f"dry-run: would POST {len(payloads)} payload(s) to "
                  f"{args.base_url}/events")
            return 0
        res = post_events(args.base_url, args.secret, payloads)
        print(f"posted {len(payloads)} payload(s) -> inserted "
              f"{res.get('inserted')} (rest deduped or queued unmatched)")
        return 0

    db = Path(args.data).resolve() / "lead-desk.sqlite"
    if not db.exists():
        print(f"ERROR: db not found: {db}")
        return 1
    verify_only = args.verify and not args.apply and not args.dry_run
    with ContactStore(db) as store:
        if not verify_only:
            report = backfill(store, ledger, cohorts=args.cohort,
                              apply=args.apply,
                              upgrade_ewave_keys=args.upgrade_ewave_keys)
            print(json.dumps(report, indent=1, default=str))
        if args.verify:
            v = verify(store, ledger, args.cohort)
            _print_verify(v)
            if not v["ok"]:
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
