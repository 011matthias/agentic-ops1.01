"""One-time, idempotent migration of the Rome master sheet into the Lead Desk.

Reads the live ``rome2026-post-event-master-contacts.xlsx`` ("Master contacts",
290 rows / 32 cols), maps it into ``contacts``, unifies the three "do not
contact" encodings into one ``suppressed`` flag, and parses the free-text
``outreach_log`` into structured ``outreach_events``. Optionally folds the
E1/E2/E3 send-log CSVs as precise ``sent``/``bounce`` events when present.

Re-runnable: contacts UPSERT by natural_key, events INSERT OR IGNORE by hash,
so a second run inserts nothing new.

    lead-desk-migrate --xlsx <path> --data ./lead-desk-data
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

from .web.service import now_iso
from .web.store import ContactStore

DEFAULT_XLSX = (
    "C:/Users/neuma_p1qrsic/Repo/agentic-ops1/workspace/clients/brisken/context/"
    "lead-generation/Rome-Event/event-admin/rome2026-post-event-master-contacts.xlsx"
)
DEFAULT_EXTRAS = (
    "C:/Users/neuma_p1qrsic/Repo/agentic-ops1/workspace/clients/brisken/context/"
    "lead-generation/Rome-Event"
)

_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")

# Deterministic fallback timestamp (Rome event week) for events whose own date
# does not parse. Never use a wall-clock "now" for an event ts: it would change
# the event hash every run and break idempotency.
EVENT_WEEK_TS = "2026-06-24T00:00:00+00:00"

# Tier -> suppression reason for the exclusion tiers.
TIER_SUPPRESS = {
    "STOP": "stop", "DUPLICATE": "duplicate", "TEST": "test",
    "ORGANISER": "organiser", "OWN_TEAM": "own_team",
    "UNREACHABLE": "unreachable", "ANON": "anon",
}


def _s(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _yn(v) -> int:
    return 1 if str(v).strip().lower() in ("yes", "true", "1", "y") else 0


def _date(v) -> str | None:
    if v is None:
        return None
    m = _DATE_RE.search(str(v))
    return m.group(1) if m else None


def _ts(datestr: str | None) -> str | None:
    return f"{datestr}T00:00:00+00:00" if datestr else None


def natural_key(email: str | None, first: str | None, last: str | None,
                company: str | None, ordinal: int | None = None) -> str:
    if email:
        return email.strip().lower()
    # No email: key on identity plus the stable sheet row ordinal, so two
    # anonymous booth taps (blank name/company) never merge into one contact.
    # Losing distinct booth records (under-merge) is worse than over-splitting,
    # which the same-name duplicate report surfaces for review.
    parts = [first or "", last or "", company or ""]
    if ordinal is not None:
        parts.append(f"#{ordinal}")
    basis = "|".join(parts).strip().lower()
    return "anon:" + hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def contact_id_for(nk: str) -> str:
    return hashlib.sha1(nk.encode("utf-8")).hexdigest()[:16]


def suppression(row: dict) -> tuple[int, str | None]:
    """Collapse Tier=STOP, stop=X, and the two *_status 'do not contact' text
    values (plus the exclusion tiers) into one suppressed flag + reason."""
    stop = str(row.get("stop") or "").strip().upper() == "X"
    es = (row.get("email outreach_status") or "").strip().lower()
    ls = (row.get("linkedin_status") or "").strip().lower()
    tier = (row.get("Tier") or "").strip().upper()
    if "no consent" in es or "no consent" in ls:
        return 1, "no_consent"
    if stop:
        return 1, "stop"
    if "do not contact" in es or "do not contact" in ls:
        return 1, "do_not_contact"
    if tier in TIER_SUPPRESS:
        return 1, TIER_SUPPRESS[tier]
    return 0, None


def classify_log_line(line: str) -> tuple[str, str, str]:
    low = line.lower()
    ch = "linkedin" if "linkedin" in low else ("meeting" if ("meeting" in low or "call" in low) else "email")
    if "bounce" in low:
        return ("email", "inbound", "bounce")
    if any(w in low for w in ("response", "reply", "replied", "responded")):
        return (ch, "inbound", "reply")
    if "invite" in low:
        return (ch, "outbound", "invite")
    if any(w in low for w in ("sent", "e1", "e2", "e3", "follow", "nudge", "connect")):
        return (ch, "outbound", "sent")
    return (ch, "outbound", "note")


def import_workbook(store: ContactStore, xlsx: Path, campaign: str, report: dict) -> dict:
    from openpyxl import load_workbook

    wb = load_workbook(str(xlsx), read_only=True, data_only=True)
    ws = wb["Master contacts"]
    it = ws.iter_rows(values_only=True)
    header = list(next(it))
    idx = {h: i for i, h in enumerate(header)}

    def col(r, name):
        i = idx.get(name)
        return r[i] if i is not None and i < len(r) else None

    now = now_iso()
    email_index: dict[str, str] = {}
    name_groups: dict[str, list[str]] = defaultdict(list)
    events_added = 0
    contacts = 0

    for ordinal, r in enumerate(it):
        if all(c is None for c in r):
            continue
        first = _s(col(r, "first_name"))
        last = _s(col(r, "last_name"))
        company = _s(col(r, "company"))
        email = _s(col(r, "email"))
        email_l = email.lower() if email else None
        nk = natural_key(email, first, last, company, ordinal)
        cid = contact_id_for(nk)

        rowdict = {h: col(r, h) for h in header}
        supp, reason = suppression(rowdict)

        next_step = _s(col(r, "next_step"))
        data = {
            "contact_id": cid, "natural_key": nk, "campaign": campaign,
            "first_name": first, "last_name": last, "company": company,
            "job_title": _s(col(r, "job_title")), "email": email,
            "alt_email": _s(col(r, "alt_email")), "phone": _s(col(r, "phone")),
            "country": _s(col(r, "country")), "linkedin_url": _s(col(r, "linkedin_url")),
            "tier": _s(col(r, "Tier")), "tier_reason": _s(col(r, "Tier_reason")),
            "lead_type": _s(col(r, "lead_type")),
            "suppressed": supp, "suppress_reason": reason,
            "suppressed_at": now if supp else None,
            "suppressed_by": "import" if supp else None,
            "crm_owner": _s(col(r, "crm_owner")),
            "next_step": next_step, "next_step_due": _date(next_step),
            "source": _s(col(r, "source")), "in_our_booth": _yn(col(r, "in_our_booth")),
            "scanned_at_booth": _yn(col(r, "scanned_at_booth")),
            "if_we_know_them": _s(col(r, "if_we_know_them")),
            "brisken_customer": _s(col(r, "brisken_customer")),
            "attendee_type": _s(col(r, "attendee_type")),
            "sponsor_opt_in": _yn(col(r, "sponsor_opt_in")), "no_show": _yn(col(r, "no_show")),
            "fob_encoded": _yn(col(r, "fob_encoded")),
            "booth_registered_at": _s(col(r, "booth_registered_at")),
            "crm_last_activity": _s(col(r, "crm_last_activity")),
            "dirk_notes": _s(col(r, "dirk_notes")),
        }
        store.upsert_contact(data, now)
        contacts += 1
        if email_l:
            email_index[email_l] = cid
        alt = _s(col(r, "alt_email"))
        if alt:
            email_index[alt.lower()] = cid
        if first and last:
            name_groups[f"{first.lower()} {last.lower()}"].append(nk)

        # Parse outreach_log into events.
        last_out = _date(col(r, "last_outreach"))
        last_rep = _date(col(r, "last_reply"))
        log = col(r, "outreach_log")
        has_out = has_in = False
        if log:
            for raw in str(log).splitlines():
                line = raw.strip()
                if not line:
                    continue
                d = _date(line) or last_out or _date(col(r, "booth_registered_at"))
                ch, direction, typ = classify_log_line(line)
                if direction == "outbound":
                    has_out = True
                if direction == "inbound":
                    has_in = True
                if store.add_event(
                    contact_id=cid, ts=_ts(d) or EVENT_WEEK_TS, channel=ch, direction=direction,
                    type=typ, detail=line, source="import", campaign=campaign, now=now,
                ):
                    events_added += 1
        # Fill stage-critical gaps from the summary dates.
        if last_out and not has_out:
            if store.add_event(contact_id=cid, ts=_ts(last_out), channel="email",
                               direction="outbound", type="sent",
                               detail="last_outreach", source="import",
                               campaign=campaign, now=now):
                events_added += 1
        if last_rep and not has_in:
            if store.add_event(contact_id=cid, ts=_ts(last_rep), channel="email",
                               direction="inbound", type="reply",
                               detail="last_reply", source="import",
                               campaign=campaign, now=now):
                events_added += 1

    report["contacts"] = contacts
    report["events_from_sheet"] = events_added
    report["fuzzy_dups"] = {k: v for k, v in name_groups.items() if len(set(v)) > 1}
    return email_index


def fold_send_logs(store: ContactStore, email_index: dict, campaign: str,
                   extras: Path, report: dict) -> None:
    now = now_iso()
    added = 0
    for wave in ("E1", "E2", "E3"):
        path = extras / "email-campaign" / f"rome2026-send-log-{wave}.csv"
        if not path.exists():
            continue
        try:
            with path.open(newline="", encoding="utf-8-sig") as fh:
                for row in csv.DictReader(fh):
                    addr = (row.get("email") or "").strip().lower()
                    cid = email_index.get(addr)
                    if not cid:
                        continue
                    status = (row.get("status") or "").strip()
                    ts = _ts(_date(row.get("utc"))) or EVENT_WEEK_TS
                    is_bounce = "bounce" in status.lower()
                    if store.add_event(
                        contact_id=cid, ts=ts, channel="email",
                        direction="inbound" if is_bounce else "outbound",
                        type="bounce" if is_bounce else "sent",
                        detail=f"{wave} send-log: {status}", source="import",
                        # stable idempotency key so a re-run never re-inserts
                        ext_key=f"sendlog-{wave}-{addr}-{status}",
                        campaign=campaign, now=now,
                    ):
                        added += 1
        except Exception as exc:  # noqa: BLE001 - a malformed optional file must not abort the import
            report.setdefault("warnings", []).append(f"send-log {wave}: {exc}")
    report["events_from_send_logs"] = added


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lead-desk-migrate")
    p.add_argument("--xlsx", default=DEFAULT_XLSX)
    p.add_argument("--extras", default=DEFAULT_EXTRAS, help="Rome-Event dir for optional send logs.")
    p.add_argument("--data", default=os.environ.get("LEAD_DESK_DATA", "lead-desk-data"))
    p.add_argument("--campaign", default="rome-2026")
    p.add_argument("--no-send-logs", action="store_true")
    args = p.parse_args(argv)

    xlsx = Path(args.xlsx)
    if not xlsx.exists():
        print(f"ERROR: xlsx not found: {xlsx}")
        return 1
    db = Path(args.data).resolve() / "lead-desk.sqlite"
    report: dict = {}
    with ContactStore(db) as store:
        email_index = import_workbook(store, xlsx, args.campaign, report)
        if not args.no_send_logs:
            fold_send_logs(store, email_index, args.campaign, Path(args.extras), report)
        # Stage distribution after import.
        rows = store.board_rows(args.campaign)
        stages = Counter(r["stage"] for r in rows)
        supp = sum(1 for r in rows if r["suppressed"])
        total_events = store.count_events()

    print(f"DB: {db}")
    print(f"contacts upserted: {report.get('contacts')}")
    print(f"suppressed: {supp}")
    print(f"events (sheet): {report.get('events_from_sheet')} | "
          f"(send-logs): {report.get('events_from_send_logs', 0)} | total in db: {total_events}")
    print(f"stage distribution: {dict(stages)}")
    dups = report.get("fuzzy_dups") or {}
    if dups:
        print(f"POSSIBLE DUPLICATES (same name, different key), {len(dups)}:")
        for name, keys in dups.items():
            print(f"  {name}: {sorted(set(keys))}")
    for w in report.get("warnings", []):
        print(f"WARNING: {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
