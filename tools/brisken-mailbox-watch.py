# /// script
# requires-python = ">=3.10"
# dependencies = ["pywin32"]
# ///
"""READ-ONLY 3-surface watcher for Dirk's Outlook mailbox (Windows COM).

WHY THIS EXISTS
---------------
Two recurring 2026-07-11 failures the memory flags as needing a structural fix
(reference_dirk_outlook_com_drafts):

  1. Ghost-written drafts landed in MATTHIAS's Drafts, not Dirk's (3rd/4th
     occurrence). `SendUsingAccount` reads back empty, so placement can only be
     confirmed by which STORE actually holds the item. -> This tool lists Drafts
     across EVERY store, labelled by owner, so a mis-filed draft is obvious.
  2. A false "the invite to Ian was never sent" claim, drawn from a Sent-Items
     scan -- but meeting requests do NOT appear in Sent Items; the booked
     meeting was on the CALENDAR. -> This tool reads the calendar as a first-
     class surface, so "was it sent/booked" is answered from where the truth
     lives, not from Sent Items alone.

The three surfaces (Drafts, Sent, Calendar) are read together so the operator
never has to correlate them by hand or infer a negative from the wrong folder.

STRICTLY READ-ONLY: no .Send, no .Move, no .Delete, no property writes. Safe to
run under autonomy (rule_instantly_invasive / feedback_no_invasive_action apply
to state changes; this changes nothing).

NOTE: needs a running Outlook profile that has the mailbox(es) attached; it is
Windows + pywin32 only and cannot be exercised in Linux CI. Verify live by
running it once against the profile before trusting a placement/send claim.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta

DIRK = "dirk.neumann@brisken.com"

# Outlook OlDefaultFolders
OL_DRAFTS = 16
OL_SENT = 5
OL_CALENDAR = 9

# Localized display-name fallbacks (this profile is DE/EN mixed).
FOLDER_ALIASES = {
    "drafts": {"drafts", "entwürfe", "entwurfe"},
    "sent items": {"sent items", "gesendete elemente", "gesendete objekte"},
    "calendar": {"calendar", "kalender"},
}


def _get_session():
    import win32com.client
    return win32com.client.Dispatch("Outlook.Application").Session


def _store_label(store) -> str:
    try:
        return store.DisplayName or "?"
    except Exception:
        return "?"


def _default_folder(store, const, name_key):
    """store.GetDefaultFolder(const); fall back to a localized name search under
    the store root. Returns the folder or None."""
    try:
        return store.GetDefaultFolder(const)
    except Exception:
        pass
    try:
        root = store.GetRootFolder()
        aliases = FOLDER_ALIASES.get(name_key, {name_key})
        for f in root.Folders:
            if (f.Name or "").strip().lower() in aliases:
                return f
    except Exception:
        pass
    return None


def _fmt(v) -> str:
    try:
        return str(v)
    except Exception:
        return "?"


def _drafts_rows(folder, subject_match):
    rows = []
    try:
        for it in folder.Items:
            try:
                subj = (it.Subject or "").strip()
                if subject_match and subject_match.lower() not in subj.lower():
                    continue
                rows.append({"subject": subj, "to": (it.To or "").strip(),
                             "created": _fmt(getattr(it, "CreationTime", ""))})
            except Exception:
                continue
    except Exception:
        pass
    return rows


def _sent_rows(folder, since: datetime, subject_match):
    rows = []
    try:
        items = folder.Items
        items.Sort("[SentOn]", True)
        items = items.Restrict(f"[SentOn] >= '{since.strftime('%m/%d/%Y %H:%M')}'")
        for it in items:
            try:
                subj = (it.Subject or "").strip()
                if subject_match and subject_match.lower() not in subj.lower():
                    continue
                rows.append({"sent": _fmt(getattr(it, "SentOn", "")),
                             "to": (it.To or "")[:80], "subject": subj})
            except Exception:
                continue
    except Exception:
        pass
    return rows


def _calendar_rows(folder, since: datetime, until: datetime, subject_match):
    rows = []
    try:
        items = folder.Items
        items.IncludeRecurrences = True
        items.Sort("[Start]")
        rng = (f"[Start] >= '{since.strftime('%m/%d/%Y %H:%M')}' AND "
               f"[Start] <= '{until.strftime('%m/%d/%Y %H:%M')}'")
        items = items.Restrict(rng)
        for it in items:
            try:
                subj = (it.Subject or "").strip()
                if subject_match and subject_match.lower() not in subj.lower():
                    continue
                organizer = _fmt(getattr(it, "Organizer", ""))
                rows.append({"start": _fmt(getattr(it, "Start", "")), "subject": subj,
                             "organizer": organizer,
                             "meeting": bool(getattr(it, "IsOnlineMeeting", False))
                             or getattr(it, "MeetingStatus", 0) != 0})
            except Exception:
                continue
    except Exception:
        pass
    return rows


def collect(since_days: int, cal_days: int, subject_match: str | None) -> dict:
    session = _get_session()
    since = datetime.now() - timedelta(days=since_days)
    cal_since = datetime.now() - timedelta(days=1)
    cal_until = datetime.now() + timedelta(days=cal_days)

    stores = []
    try:
        stores = list(session.Stores)
    except Exception:
        pass

    out = {"generated": datetime.now().isoformat(timespec="seconds"),
           "target": DIRK, "since_days": since_days, "stores": []}

    for store in stores:
        label = _store_label(store)
        is_dirk = DIRK in label.lower()
        drafts = _default_folder(store, OL_DRAFTS, "drafts")
        sent = _default_folder(store, OL_SENT, "sent items")
        cal = _default_folder(store, OL_CALENDAR, "calendar")
        entry = {
            "store": label,
            "is_dirk": is_dirk,
            "drafts": _drafts_rows(drafts, subject_match) if drafts else [],
            "sent_since": _sent_rows(sent, since, subject_match) if sent else [],
            "calendar_window": _calendar_rows(cal, cal_since, cal_until, subject_match) if cal else [],
        }
        out["stores"].append(entry)

    out["dirk_store_present"] = any(s["is_dirk"] for s in out["stores"])
    return out


def _print_human(data: dict) -> None:
    print(f"Dirk mailbox watch  ({data['generated']})  target={data['target']}")
    if not data["dirk_store_present"]:
        print("  LIMITATION: no store matching Dirk's SMTP is attached to this "
              "Outlook profile. Drafts below may be in the WRONG mailbox.")
    for s in data["stores"]:
        tag = "  <-- DIRK" if s["is_dirk"] else ""
        print(f"\n=== store: {s['store']}{tag} ===")
        print(f"  DRAFTS ({len(s['drafts'])}):")
        for d in s["drafts"]:
            print(f"    [{d['to']:<34.34}] {d['subject']}")
        print(f"  SENT since window ({len(s['sent_since'])}):")
        for m in s["sent_since"]:
            print(f"    [{m['sent']}] -> {m['to']} | {m['subject']}")
        print(f"  CALENDAR window ({len(s['calendar_window'])}):")
        for c in s["calendar_window"]:
            mk = " (meeting)" if c["meeting"] else ""
            print(f"    [{c['start']}] {c['subject']}{mk}  org={c['organizer']}")
    # Cross-surface hint for the two named failure modes.
    misfiled = [s for s in data["stores"] if not s["is_dirk"] and s["drafts"]]
    if misfiled and data["dirk_store_present"]:
        print("\n  NOTE: drafts exist in a NON-Dirk store; if these were meant to "
              "be Dirk's, they are mis-filed (see reference_dirk_outlook_com_drafts).")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="READ-ONLY Dirk 3-surface mailbox watcher.")
    ap.add_argument("--since-days", type=int, default=7, help="Sent window lookback (days)")
    ap.add_argument("--cal-days", type=int, default=30, help="Calendar look-ahead (days)")
    ap.add_argument("--subject", default=None, help="case-insensitive subject filter")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    try:
        data = collect(args.since_days, args.cal_days, args.subject)
    except Exception as e:
        print(json.dumps({"error": "Outlook COM unavailable (Windows + running "
                          "Outlook profile required)", "detail": str(e)[:300]}))
        return 2

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        _print_human(data)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
