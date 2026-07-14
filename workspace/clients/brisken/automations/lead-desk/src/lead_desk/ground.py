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
import os
from pathlib import Path

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


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lead-desk-ground")
    p.add_argument("--data", default=os.environ.get("LEAD_DESK_DATA", "lead-desk-data"))
    p.add_argument("--campaign", default="rome-2026")
    args = p.parse_args(argv)
    if args.campaign not in CAMPAIGN_WAVES:
        print(f"no wave config for campaign '{args.campaign}'")
        return 1
    db = Path(args.data).resolve() / "lead-desk.sqlite"
    with ContactStore(db) as store:
        rep = ground(store, args.campaign, now_iso())
    print(f"[ground] {args.campaign}: {rep}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
