"""Ground DURING-EVENT (E1/E2/E3) outreach status from the real mailboxes.

The sheet's ``emails_sent`` column over-states the during-event waves (2026-07-14:
199 marked vs ~37 actually sent). The authoritative record of what went out is the
Sent Items of the two brisken mailboxes, so this reads them app-only via Microsoft
Graph and writes DISTINCT, clearly-labelled ``During-event`` events, kept separate
from the sheet-sourced ``Post-event follow-up`` phase (see ``migrate.post_event``).

Hard rules:
- Mailbox HARD-allowlist: only dirk.neumann@ / matthias.silva@ (per rule_brisken_graph_first).
- Non-attendees stay out: an E-wave recipient is grounded ONLY if it already matches an
  existing contact by email; recipients with no contact are never added (owner 2026-07-14).
- Idempotent: one ``sent`` event per (contact, wave) via a stable ext_key + send date;
  one ``reply`` event per contact. Re-runnable, non-destructive.

    lead-desk-ground --data ./lead-desk-data --campaign rome-2026
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

from .migrate import is_during_event
from .sync import GRAPH, graph_token
from .web.service import now_iso
from .web.store import ContactStore

# HARD mailbox allowlist. Any read is asserted against this before the call.
MAILBOXES = ("dirk.neumann@brisken.com", "matthias.silva@brisken.com")

# Per-campaign during-event wave subjects (lower-cased, exact) -> wave label. The
# subjects ARE the campaign's bulk-send templates as they appear in Sent Items.
CAMPAIGN_WAVES: dict[str, dict] = {
    "rome-2026": {
        "mailboxes": MAILBOXES,
        "waves": {
            "worth fifteen minutes at booth #2, rome": "E1",
            "what treasury teams are actually doing with ai now": "E2",
            "last day at booth #2 in rome, thursday": "E3",
        },
        "send_window": ("2026-06-01T00:00:00Z", "2026-07-15T00:00:00Z"),
        "reply_window": ("2026-06-15T00:00:00Z", "2026-07-12T00:00:00Z"),
    },
}

# First POST-event day per campaign: a direct (non-E-wave) send dated on/after
# this counts as post-event outreach on the board; earlier ones are recorded as
# neutral "Direct outreach". Rome's SAP conference last day was Thu 2026-06-25.
EVENT_END: dict[str, str] = {"rome-2026": "2026-06-26"}


def _norm(s) -> str:
    return (s or "").strip().lower()


def _base_subject(subj: str) -> str:
    """Strip a single Re:/Fw: prefix so a reply/forward maps to its wave."""
    s = _norm(subj)
    for p in ("re: ", "fw: ", "fwd: "):
        if s.startswith(p):
            return s[len(p):].strip()
    return s


def _pull(mbx: str, folder: str, flt: str, select: str, headers: dict) -> list[dict]:
    import requests

    url = (f"{GRAPH}/users/{mbx}/mailFolders/{folder}/messages"
           f"?$filter={flt}&$select={select}&$top=100")
    out: list[dict] = []
    while url:
        r = requests.get(url, headers=headers, timeout=40)
        r.raise_for_status()
        j = r.json()
        out.extend(j.get("value", []))
        url = j.get("@odata.nextLink")
    return out


def collect(campaign: str) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    """Return (sends, replies): sends[email] = {wave: first_send_date};
    replies[email] = first_reply_date. Merged across both mailboxes."""
    cfg = CAMPAIGN_WAVES[campaign]
    waves = cfg["waves"]
    headers = {"Authorization": "Bearer " + graph_token()}
    sw0, sw1 = cfg["send_window"]
    rw0, rw1 = cfg["reply_window"]
    sends: dict[str, dict[str, str]] = {}
    replies: dict[str, str] = {}
    for mbx in cfg["mailboxes"]:
        assert mbx in MAILBOXES, f"mailbox not allowlisted: {mbx}"
        for m in _pull(mbx, "SentItems",
                       f"sentDateTime ge {sw0} and sentDateTime le {sw1}",
                       "subject,sentDateTime,toRecipients", headers):
            wave = waves.get(_base_subject(m.get("subject")))
            if not wave:
                continue
            d = (m.get("sentDateTime") or "")[:10]
            for tr in (m.get("toRecipients") or []):
                addr = _norm(tr.get("emailAddress", {}).get("address"))
                if addr:
                    sends.setdefault(addr, {}).setdefault(wave, d)
        for m in _pull(mbx, "Inbox",
                       f"receivedDateTime ge {rw0} and receivedDateTime le {rw1}",
                       "subject,receivedDateTime,from", headers):
            # A genuine reply keeps the wave subject (minus Re:); OOO auto-replies
            # ("Automatic reply: ...") do not match and are correctly ignored.
            if _base_subject(m.get("subject")) not in waves:
                continue
            frm = _norm(m.get("from", {}).get("emailAddress", {}).get("address"))
            d = (m.get("receivedDateTime") or "")[:10]
            if frm and (frm not in replies or d < replies[frm]):
                replies[frm] = d
    return sends, replies


def _ts(date_str: str) -> str:
    return f"{date_str}T00:00:00+00:00"


def ground(store: ContactStore, campaign: str, now: str,
           collected: tuple | None = None) -> dict:
    """Write during-event events for CONTACTS ONLY (non-attendees excluded)."""
    sends, replies = collected or collect(campaign)
    grounded: set[str] = set()
    sent_events = reply_events = skipped_non_contacts = 0
    for email, waves in sends.items():
        row = store.find_by_email(email)
        if row is None:
            skipped_non_contacts += 1          # non-attendee: stays out
            continue
        cid = row["contact_id"]
        grounded.add(cid)
        for wave, d in sorted(waves.items()):
            if store.add_event(
                contact_id=cid, ts=_ts(d), channel="email", direction="outbound",
                type="sent", subject=f"During-event {wave}",
                detail=f"{wave} outreach sent {d} (mailbox-grounded)",
                source="graph", ext_key=f"de-{wave}-{cid}", campaign=campaign, now=now,
            ):
                sent_events += 1
    for email, d in replies.items():
        row = store.find_by_email(email)
        if row is None:
            continue
        cid = row["contact_id"]
        if store.add_event(
            contact_id=cid, ts=_ts(d), channel="email", direction="inbound",
            type="reply", subject="During-event reply",
            detail=f"Replied to E-wave outreach {d} (mailbox-grounded)",
            source="graph", ext_key=f"de-reply-{cid}", campaign=campaign, now=now,
        ):
            reply_events += 1
    return {
        "contacts_grounded": len(grounded),
        "sent_events": sent_events,
        "reply_events": reply_events,
        "recipients_skipped_non_contact": skipped_non_contacts,
    }


def collect_direct(campaign: str) -> list[tuple[str, str, str]]:
    """Return (email, send_date, subject) for every NON-E-wave outbound send
    across both mailboxes. Recipient-matched to contacts, and internal-address
    exclusion, happen in ``ground_direct`` (owner 2026-07-14: search the outbox,
    match the master-sheet contacts). The E-waves are skipped here because
    ``ground`` already writes them as During-event events."""
    cfg = CAMPAIGN_WAVES[campaign]
    waves = cfg["waves"]
    headers = {"Authorization": "Bearer " + graph_token()}
    sw0, sw1 = cfg["send_window"]
    out: list[tuple[str, str, str]] = []
    for mbx in cfg["mailboxes"]:
        assert mbx in MAILBOXES, f"mailbox not allowlisted: {mbx}"
        for m in _pull(mbx, "SentItems",
                       f"sentDateTime ge {sw0} and sentDateTime le {sw1}",
                       "subject,sentDateTime,toRecipients,ccRecipients", headers):
            subject = (m.get("subject") or "").strip()
            if _base_subject(subject) in waves:
                continue                       # during-event E-wave, already grounded
            d = (m.get("sentDateTime") or "")[:10]
            if not d:
                continue
            recips = (m.get("toRecipients") or []) + (m.get("ccRecipients") or [])
            for tr in recips:
                addr = _norm(tr.get("emailAddress", {}).get("address"))
                if addr:
                    out.append((addr, d, subject))
    return out


def _subj_hash(subject: str) -> str:
    return hashlib.sha1(_base_subject(subject).encode("utf-8")).hexdigest()[:8]


def ground_direct(store: ContactStore, campaign: str, now: str,
                  direct: list[tuple[str, str, str]] | None = None) -> dict:
    """Ground DIRECT (non-E-wave) mailbox outreach onto existing contacts.

    A send to a real contact dated on/after ``EVENT_END`` is written as a
    ``Post-event outreach`` event (source=graph) that counts under the board's
    post-event phase, kept DISTINCT from the sheet's ``Post-event follow-up``;
    earlier ones are neutral ``Direct outreach``. Internal ``@brisken.com`` /
    ``OWN_TEAM`` recipients and non-attendees (no matching contact) are excluded,
    which is what strips the Planner / receipt / forwarded-invoice noise that a
    naive outbox ingest would pull in. Idempotent + non-destructive."""
    direct = collect_direct(campaign) if direct is None else direct
    cutoff = EVENT_END.get(campaign, "9999-12-31")
    post_events = during_events = 0
    skipped_internal = skipped_non_contact = 0
    grounded: set[str] = set()
    seen: set[str] = set()
    for email, d, subject in direct:
        if not d or email.endswith("@brisken.com"):
            skipped_internal += 1
            continue
        row = store.find_by_email(email)
        if row is None:
            skipped_non_contact += 1
            continue
        if (row["tier"] or "").upper() == "OWN_TEAM":
            skipped_internal += 1
            continue
        cid = row["contact_id"]
        post = d >= cutoff
        ext = f"mbx-{cid}-{d}-{_subj_hash(subject)}"
        if ext in seen:
            continue
        seen.add(ext)
        if store.add_event(
            contact_id=cid, ts=_ts(d), channel="email", direction="outbound",
            type="sent", subject=("Post-event outreach" if post else "Direct outreach"),
            detail=f"{subject} ({d}, mailbox-grounded)",
            source="graph", ext_key=ext, campaign=campaign, now=now,
        ):
            grounded.add(cid)
            if post:
                post_events += 1
            else:
                during_events += 1
    return {
        "contacts_with_direct": len(grounded),
        "post_event_events": post_events,
        "direct_during_events": during_events,
        "recipients_skipped_internal": skipped_internal,
        "recipients_skipped_non_contact": skipped_non_contact,
    }


def drop_import_during_event(store: ContactStore, campaign: str,
                             dry_run: bool = False) -> dict:
    """Remove sheet/import-sourced DURING-EVENT events now that Graph is the
    authoritative during-event source (owner 2026-07-14: "stick to just Graph").

    Deletes ``source='import'`` events that are E-wave sends/replies
    ("E1 pre-event invite sent", "E3 response: ...") or send-log rows
    ("E1 send-log: sent"), plus the generic ``last_outreach``/``last_reply``
    gap-fills for contacts that already carry a graph-grounded during-event
    event. Leaves the Dirk touch, post-event follow-up, and all non-during-event
    import rows untouched. Non-destructive with ``dry_run=True``."""
    con = store.conn
    graphed = {r[0] for r in con.execute(
        "SELECT DISTINCT contact_id FROM outreach_events "
        "WHERE campaign=? AND source='graph' AND subject LIKE 'During-event%'",
        (campaign,)).fetchall()}
    rows = con.execute(
        "SELECT event_id, contact_id, subject, detail FROM outreach_events "
        "WHERE campaign=? AND source='import'", (campaign,)).fetchall()
    victims = []
    for eid, cid, subject, detail in rows:
        text = f"{subject or ''} {detail or ''}"
        if is_during_event(text) or "send-log" in text.lower():
            victims.append(eid)
        elif cid in graphed and (detail or "") in ("last_outreach", "last_reply"):
            victims.append(eid)
    if victims and not dry_run:
        con.executemany("DELETE FROM outreach_events WHERE event_id=?",
                        [(v,) for v in victims])
        con.commit()
    return {"campaign": campaign, "import_during_event_removed": len(victims),
            "dry_run": dry_run}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lead-desk-ground")
    p.add_argument("--data", default=os.environ.get("LEAD_DESK_DATA", "lead-desk-data"))
    p.add_argument("--campaign", default="rome-2026")
    p.add_argument("--drop-import-dupes", action="store_true",
                   help="remove sheet/import during-event events (Graph is authoritative)")
    p.add_argument("--dry-run", action="store_true",
                   help="with --drop-import-dupes: report the count, delete nothing")
    args = p.parse_args(argv)
    if args.campaign not in CAMPAIGN_WAVES:
        print(f"no wave config for campaign '{args.campaign}'")
        return 1
    db = Path(args.data).resolve() / "lead-desk.sqlite"
    with ContactStore(db) as store:
        if args.drop_import_dupes:
            rep = drop_import_during_event(store, args.campaign, dry_run=args.dry_run)
            print(f"[dedupe] {rep}")
            return 0
        now = now_iso()
        rep = ground(store, args.campaign, now)
        drep = ground_direct(store, args.campaign, now)
    print(f"[ground] {args.campaign}: {rep}")
    print(f"[direct] {args.campaign}: {drep}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
