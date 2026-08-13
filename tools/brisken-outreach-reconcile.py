#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests"]
# ///
"""Whole-sheet outreach reconciliation for Brisken Rome 2026: mailbox truth
vs the master sheet's `email outreach_status`, with draft-prepared as a
first-class state.

The owner has corrected the same error class three times (2026-07-14 /
07-16 / 07-22: leads called "open"/"not contacted" that were already sent,
replied, or sitting prepared in Dirk's Drafts). Memory-layer fixes did not
hold; this tool operationalizes the proven method from
feedback_brisken_outreach_truth_is_mailbox (and the one-off
.scratch/rome_ground.py pipeline) at the tool layer:

  scan    ONE corpus pull per mailbox since --since (default 2026-06-01,
          BEFORE the event: a post-event-only window misses the
          during-event reply that justifies a live "In conversation" and
          produces false downgrades). /users/{mbx}/messages spans ALL
          folders (Dirk files sent Rome mail in per-account folders, so a
          SentItems+Inbox scan yields false "not contacted"). Real send =
          `isDraft eq false`; a separate drafts pull surfaces prepared
          outreach; calendarView supplies the strongest "In conversation"
          signal (a booked meeting email matching alone misses).
  derive  Per sheet row, matched on `email` AND `alt_email`: post-event
          (>= 2026-06-27) sends and genuine replies, during-event
          (<= 2026-06-26) evidence, prepared drafts, meetings. The reply
          signal strips OOO auto-replies, calendar-system notices
          (Accepted:/Declined:/Meeting Forward Notification/...), and NDRs.
  diff    Propose transitions. THREE states, never two: sent /
          draft-prepared / genuinely untouched.
            - UPGRADES only are auto-appliable (post send -> "Contacted -
              awaiting reply"; post reply -> "Replied - action needed", or
              "In conversation" when we sent after it; booked meeting ->
              "In conversation"; prepared draft -> "draft ready").
            - Downgrades are NEVER applied: surfaced for Dirk. H5 rows are
              not even surfaced (their channel is off-mailbox; silence
              means nothing).
            - Excluded tiers (ORGANISER, OWN_TEAM, TEST, DUPLICATE, STOP,
              ANON), holds ('-' as the EXACT whole value, phrase holds,
              non-empty `stop`) are never touched.
            - During-event-only evidence never sets the post-event status
              column; it is reported informationally (sheet convention:
              the column is POST-event only).
  write   (--write) Apply the upgrade set via app-only workbook range
          PATCH (Sites.ReadWrite.All application grant, 2026-07-21).
          usedRange snapshot lands in .scratch/ first; the post-write
          whole-sheet diff must show exactly the planned cells changed
          (concurrent live edits are reported loudly, never absorbed).

INVASIVE-ACTION GATE: --write mutates the live SharePoint sheet and runs
ONLY on an explicit owner order for that specific write
(rule_brisken_graph_first, feedback_no_invasive_action_without_ask).
Without --write the tool is 100% read-only GETs and runs under autonomy.

Hard mailbox allowlist: EXACTLY dirk.neumann@brisken.com and
matthias.silva@brisken.com (asserted before every Mail/Calendar call).

Creds: app-only client-credentials from the gitignored
workspace/clients/brisken/context/.env, overridable via BRISKEN_ENV_FILE.
Worktrees do not carry gitignored context/: point BRISKEN_ENV_FILE at the
primary clone's file when running from one.

Usage:
  uv run tools/brisken-outreach-reconcile.py                # dry-run diff
  uv run tools/brisken-outreach-reconcile.py --json         # machine output
  uv run tools/brisken-outreach-reconcile.py --contact a@x.com b@y.com
  uv run tools/brisken-outreach-reconcile.py --write        # owner order only
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

try:
    import requests
except ImportError:  # CI test env execs this module without live deps;
    requests = None  # the pure logic stays importable, transport unused.

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _load_truth():
    """Shared Graph plumbing lives in tools/brisken-outreach-truth.py."""
    path = Path(__file__).resolve().parent / "brisken-outreach-truth.py"
    spec = importlib.util.spec_from_file_location("brisken_outreach_truth", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["brisken_outreach_truth"] = mod
    spec.loader.exec_module(mod)
    return mod


truth = _load_truth()
GRAPH = truth.GRAPH
MAILBOXES = truth.MAILBOXES
OOO_RE = truth.OOO_RE

# ---- Master sheet identity (project_brisken_rome_master_contact_sheet) ----
SITE_ID = ("brisken.sharepoint.com,65b8d36f-2777-4cff-bd80-58ff9022d17c,"
           "e9089a15-9498-4149-a6f3-b4bc8e4d21ac")
DRIVE_ID = "b!b9O4ZXcn_0y9gFj_kCLRfBWaCOmYlElBpvO0vI5NIaw5KcH3HSGsSpXXuNOLZ1ZQ"
ITEM_ID = "01SQ6DZAFWTLXNN5CKPNAZVUQ3BQYEM4NC"
FILE_PATH = ("30_Events/TA Cook/TA Cook 2026/"
             "TAC Rome2026-post-event-master-contacts_260627_DN-Edits.xlsx")
TAB = "Master contacts"
STATUS_COL = "email outreach_status"

# ---- Event window (sheet convention: status column is POST-event only) ----
DURING_END = "2026-06-26"    # <= during/pre-Rome
POST_START = "2026-06-27"    # >= post-Rome
DEFAULT_SINCE = "2026-06-01"  # corpus window opens BEFORE the event

# ---- Policy tables (proven 2026-07-15/16/21 reconciliation passes) ----
EXCLUDED_TIERS = {"ORGANISER", "OWN_TEAM", "TEST", "DUPLICATE", "STOP", "ANON"}
# '-' is a VALID dropdown value (No channel/NA) and matches ONLY as the exact
# whole value; substring matching would flag "Contacted - awaiting reply".
PHRASE_HOLDS = ("do not contact", "no channel", "unsubscribe", "opt-out",
                "opt out")
RANK = {
    "": 0, "not contacted": 0,
    "draft ready": 1,
    "contacted - awaiting reply": 2,
    "replied - action needed": 3,
    "in conversation": 4,
}

CAL_SYS_RE = re.compile(
    r"^(accepted|declined|tentative|cancell?ed|invitation):"
    r"|meeting forward notification",
    re.IGNORECASE,
)
NDR_FROM_RE = re.compile(r"^(postmaster@|mailer-daemon@|microsoftexchange)",
                         re.IGNORECASE)
NDR_SUBJ_RE = re.compile(
    r"undeliverable|delivery has failed|delivery status notification"
    r"|zustellung fehlgeschlagen|mail delivery failed",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Pure logic (unit-tested in tools/tests/test_brisken_outreach_reconcile.py)
# ---------------------------------------------------------------------------

def inbound_noise(subject: str, sender: str) -> str | None:
    """Classify an inbound message as non-reply noise, or None if genuine."""
    subj = subject or ""
    if NDR_FROM_RE.search(sender or "") or NDR_SUBJ_RE.search(subj):
        return "ndr"
    if CAL_SYS_RE.search(subj):
        return "calsys"
    if OOO_RE.search(subj):
        return "ooo"
    return None


def is_hold(status: str, stop_val) -> bool:
    stl = (status or "").strip().lower()
    return (stl == "-" or any(h in stl for h in PHRASE_HOLDS)
            or stop_val not in (None, ""))


def _last(hits: list[dict]) -> str | None:
    return max((h["date"] for h in hits if h.get("date")), default=None)


def propose_transition(status: str, tier: str, stop_val, ev: dict) -> dict | None:
    """One finding for a sheet row, or None if nothing to say.

    ev keys (each a list of {date, subject, ...}): post_sends, post_replies,
    during_sends, during_replies, drafts, meetings.

    Returns {kind, to?, why} with kind:
      upgrade   -- auto-appliable, mailbox/calendar-proven rank increase
      surface   -- hold for Dirk (downgrade candidate / stale draft ready)
      info      -- during-event-only evidence; the post-event column stays
      unknown   -- status value outside the known vocabulary; never touched
    """
    st = (status or "").strip()
    stl = st.lower()
    tier_u = (tier or "").strip().upper()

    if tier_u in EXCLUDED_TIERS or is_hold(st, stop_val):
        return None

    post_send = _last(ev.get("post_sends") or [])
    post_reply = _last(ev.get("post_replies") or [])
    during = bool(ev.get("during_sends") or ev.get("during_replies"))
    drafts = ev.get("drafts") or []
    meetings = ev.get("meetings") or []

    if stl not in RANK:
        return {"kind": "unknown",
                "why": f"status {st!r} outside known vocabulary; not touched"}

    # Candidate upgrades, each guarded by the from-set proven in the
    # 2026-07-15 consistency pass; highest rank wins.
    candidates: list[tuple[str, str]] = []
    if post_reply and stl in ("", "not contacted", "contacted - awaiting reply",
                              "draft ready"):
        if post_send and post_send > post_reply:
            candidates.append(("In conversation",
                               f"reply {post_reply[:10]}, we sent after"))
        else:
            candidates.append(("Replied - action needed",
                               f"mailbox reply {post_reply[:10]}"))
    if meetings and stl in ("", "not contacted", "contacted - awaiting reply"):
        mtg = sorted(meetings, key=lambda m: m["date"])[-1]
        candidates.append(("In conversation",
                           f"booked meeting {mtg['date'][:10]}"))
    if post_send and not post_reply and stl in ("", "not contacted",
                                                "draft ready"):
        candidates.append(("Contacted - awaiting reply",
                           f"mailbox send {post_send[:10]}"))
    # Draft-prepared is a first-class state (2026-07-21 owner correction:
    # "sent / draft-prepared / genuinely untouched -- never collapse the
    # middle one"). Only from genuinely-untouched, only absent any send.
    if drafts and not post_send and not post_reply and not meetings \
            and stl in ("", "not contacted"):
        candidates.append(("draft ready",
                           f"unsent draft: {drafts[0]['subject'][:60]!r}"))

    best = max(candidates, key=lambda c: RANK[c[0].lower()], default=None)
    if best and RANK[best[0].lower()] > RANK[stl]:
        return {"kind": "upgrade", "to": best[0], "why": best[1]}

    # No post-event evidence at all: the dangerous direction. Report-only,
    # and never for H5 (off-mailbox bespoke channel -- silence means nothing).
    if not (post_send or post_reply or meetings or drafts):
        if tier_u.startswith("H5"):
            return None
        if during and RANK[stl] == 0:
            d = ev.get("during_replies") or ev.get("during_sends")
            return {"kind": "info",
                    "why": f"during-event touch only ({_last(d)[:10]}); "
                           "post-event column stays"}
        if stl == "draft ready":
            return {"kind": "surface",
                    "why": "status says draft ready but no unsent draft found"}
        if RANK[stl] >= 2:
            return {"kind": "surface",
                    "why": f"status {st!r} but no mailbox trace since window "
                           "start; hold for Dirk, never auto-downgrade"}
    return None


# ---------------------------------------------------------------------------
# Graph transport (thin; shares plumbing with brisken-outreach-truth.py)
# ---------------------------------------------------------------------------

def _norm(v) -> str:
    return str(v).strip().lower() if v not in (None, "") else ""


def wb_base() -> str:
    return f"{GRAPH}/drives/{DRIVE_ID}/items/{ITEM_ID}/workbook"


def sheet_used_range(token: str) -> dict:
    url = (f"{wb_base()}/worksheets('{quote(TAB)}')"
           "/usedRange(valuesOnly=true)")
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"},
                     params={"$select": "address,values"}, timeout=120)
    r.raise_for_status()
    return r.json()


A1_RE = re.compile(r"([A-Z]+)(\d+)")


def parse_a1_start(address: str) -> tuple[int, int]:
    """'Master contacts'!A1:AH301 -> (row 1, col 0) zero-based col."""
    m = A1_RE.search(address.split("!")[-1].split(":")[0])
    if not m:
        raise ValueError(f"unparseable usedRange address {address!r}")
    col = 0
    for ch in m.group(1):
        col = col * 26 + (ord(ch) - 64)
    return int(m.group(2)), col - 1


def colletter(idx: int) -> str:
    out = ""
    idx += 1
    while idx:
        idx, rem = divmod(idx - 1, 26)
        out = chr(65 + rem) + out
    return out


def pull_calendar(mbx: str, token: str, start: str, end: str) -> list[dict]:
    assert mbx in MAILBOXES, f"mailbox {mbx!r} not in hard allowlist"
    return truth.paged_get(
        f"{GRAPH}/users/{mbx}/calendarView", token, {
            "startDateTime": f"{start}T00:00:00Z",
            "endDateTime": f"{end}T23:59:59Z",
            "$select": "subject,start,attendees,organizer",
            "$top": "100",
        })


def build_indexes(since: str, cal_end: str, token: str) -> dict:
    """One corpus pull per mailbox; index every hit by contact address."""
    sends: dict[str, list] = {}
    replies: dict[str, list] = {}
    ooo: dict[str, list] = {}
    drafts: dict[str, list] = {}
    meetings: dict[str, list] = {}
    mbx_set = {m.lower() for m in MAILBOXES}

    for mbx in MAILBOXES:
        # truth.pull_corpus() was split into three pulls (2026-07-22 rework):
        # compose them here, preserving the old (real, drafts) shape. The
        # all-folders outbound sweep and the aggregate inbound pull can both
        # return the same message, so dedup by id before indexing.
        real_by_id: dict[str, dict] = {}
        for msg in (truth.pull_outbound(mbx, token, since)
                    + truth.pull_inbound(mbx, token, since)):
            real_by_id[msg.get("id") or msg.get("internetMessageId")
                       or repr(msg)] = msg
        real = list(real_by_id.values())
        draft_msgs = truth.pull_drafts(mbx, token)
        for msg in real:
            sender, rcpt = truth.addrs(msg)
            hit = {"mailbox": mbx, "date": msg.get("sentDateTime"),
                   "subject": (msg.get("subject") or "")[:90]}
            if sender in mbx_set:
                for a in rcpt - mbx_set:
                    sends.setdefault(a, []).append(hit)
            elif sender:
                noise = inbound_noise(msg.get("subject") or "", sender)
                if noise is None:
                    replies.setdefault(sender, []).append(hit)
                elif noise == "ooo":
                    ooo.setdefault(sender, []).append(hit)
        for msg in draft_msgs:
            _, rcpt = truth.addrs(msg)
            for a in rcpt - mbx_set:
                drafts.setdefault(a, []).append(
                    {"mailbox": mbx,
                     "subject": (msg.get("subject") or "")[:90]})
        for ev in pull_calendar(mbx, token, since, cal_end):
            when = ((ev.get("start") or {}).get("dateTime") or "")[:19]
            hit = {"mailbox": mbx, "date": when,
                   "subject": (ev.get("subject") or "")[:90]}
            people = list(ev.get("attendees") or [])
            org = (ev.get("organizer") or {}).get("emailAddress") or {}
            addresses = {_norm(a.get("emailAddress", {}).get("address"))
                         for a in people} | {_norm(org.get("address"))}
            for a in addresses - mbx_set - {""}:
                meetings.setdefault(a, []).append(hit)
    return {"sends": sends, "replies": replies, "ooo": ooo,
            "drafts": drafts, "meetings": meetings}


def split_window(hits: list[dict]) -> tuple[list[dict], list[dict]]:
    """(during, post) by the Rome cutoff; undated hits count as post."""
    during = [h for h in hits if (h.get("date") or "9999")[:10] <= DURING_END]
    post = [h for h in hits if (h.get("date") or "9999")[:10] >= POST_START]
    return during, post


def derive_rows(values: list[list], headers: list, start_row: int,
                idx: dict, indexes: dict, only: set[str]) -> list[dict]:
    findings = []
    for offset, row in enumerate(values[1:], start=start_row + 1):
        def cell(name):
            i = idx.get(name)
            return row[i] if i is not None and i < len(row) else None

        email, alt = _norm(cell("email")), _norm(cell("alt_email"))
        keys = [e for e in (email, alt) if e]
        if not keys or (only and not (set(keys) & only)):
            continue
        sends, repl, drafts, mtgs = [], [], [], []
        for e in keys:
            sends += indexes["sends"].get(e, [])
            repl += indexes["replies"].get(e, [])
            drafts += indexes["drafts"].get(e, [])
            mtgs += indexes["meetings"].get(e, [])
        d_sends, p_sends = split_window(sends)
        d_repl, p_repl = split_window(repl)
        ev = {"post_sends": p_sends, "post_replies": p_repl,
              "during_sends": d_sends, "during_replies": d_repl,
              "drafts": drafts, "meetings": mtgs}
        status = cell(STATUS_COL)
        finding = propose_transition(
            str(status).strip() if status not in (None, "") else "",
            str(cell("Tier") or ""), cell("stop"), ev)
        if finding:
            name = f"{cell('first_name') or ''} {cell('last_name') or ''}".strip()
            finding.update({
                "row": offset, "contact": name or email, "email": email,
                "tier": str(cell("Tier") or "").strip(),
                "from": str(status).strip() if status not in (None, "") else "",
                "cell": f"{TAB}!{colletter(idx[STATUS_COL])}{offset}",
            })
            findings.append(finding)
    return findings


# ---------------------------------------------------------------------------
# Write path (invasive; owner order only)
# ---------------------------------------------------------------------------

def apply_upgrades(token: str, upgrades: list[dict], snapshot: dict) -> int:
    root = Path(__file__).resolve().parent.parent
    scratch = root / ".scratch"
    scratch.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = scratch / f"outreach-reconcile-backup-{stamp}.json"
    backup.write_text(json.dumps(snapshot, ensure_ascii=False),
                      encoding="utf-8")
    print(f"backup: {backup}")

    hdr = {"Authorization": f"Bearer {token}",
           "Content-Type": "application/json"}
    for u in upgrades:
        a1 = u["cell"].split("!")[-1]
        url = (f"{wb_base()}/worksheets('{quote(TAB)}')"
               f"/range(address='{a1}')")
        r = requests.patch(url, headers=hdr,
                           json={"values": [[u["to"]]]}, timeout=60)
        r.raise_for_status()
        print(f"  PATCH {a1}: {u['from']!r} -> {u['to']!r}")

    # Whole-sheet verify: exactly the planned cells changed. Concurrent live
    # edits (Dirk works in this file) are reported, never silently absorbed.
    after = sheet_used_range(token)
    before_vals, after_vals = snapshot["values"], after["values"]
    planned = {u["cell"].split("!")[-1]: u["to"] for u in upgrades}
    start_row, start_col = parse_a1_start(snapshot["address"])
    unexpected, misapplied = [], []
    for ri in range(max(len(before_vals), len(after_vals))):
        brow = before_vals[ri] if ri < len(before_vals) else []
        arow = after_vals[ri] if ri < len(after_vals) else []
        for ci in range(max(len(brow), len(arow))):
            b = brow[ci] if ci < len(brow) else None
            a = arow[ci] if ci < len(arow) else None
            if b == a:
                continue
            a1 = f"{colletter(start_col + ci)}{start_row + ri}"
            if a1 in planned:
                if a != planned[a1]:
                    misapplied.append((a1, planned[a1], a))
                planned.pop(a1)
            else:
                unexpected.append((a1, b, a))
    ok = not planned and not misapplied
    if planned:
        print(f"  !! NOT APPLIED: {sorted(planned)}")
    for a1, want, got in misapplied:
        print(f"  !! MISAPPLIED {a1}: wanted {want!r} got {got!r}")
    for a1, b, a in unexpected[:10]:
        print(f"  note: concurrent live edit {a1}: {b!r} -> {a!r}")
    print(f"VERIFY: {'CLEAN' if ok else 'REVIEW NEEDED'} "
          f"({len(upgrades)} planned, {len(unexpected)} concurrent edits)")
    return 0 if ok else 1


# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--since", default=DEFAULT_SINCE,
                    help=f"corpus window start (default {DEFAULT_SINCE}, "
                         "before the event -- do not narrow to post-event)")
    ap.add_argument("--contact", nargs="*", default=[],
                    help="restrict to these contact emails (spot check)")
    ap.add_argument("--json", action="store_true", help="JSON output")
    ap.add_argument("--write", action="store_true",
                    help="INVASIVE: apply the upgrade set to the live sheet "
                         "(explicit owner order only)")
    ap.add_argument("--yes", action="store_true",
                    help="skip the interactive confirm (scripted use AFTER "
                         "the owner order)")
    args = ap.parse_args()

    token = truth.get_token(truth.load_env())
    ur = sheet_used_range(token)
    values = ur["values"]
    if not values:
        sys.exit("ERROR: empty usedRange")
    headers = [str(h).strip() for h in values[0]]
    idx = {h: i for i, h in enumerate(headers)}
    for required in ("email", STATUS_COL, "Tier"):
        if required not in idx:
            sys.exit(f"ERROR: column {required!r} not found in {TAB} "
                     f"(headers: {headers[:12]}...)")
    start_row, _ = parse_a1_start(ur["address"])

    cal_end = (dt.date.today() + dt.timedelta(days=120)).isoformat()
    indexes = build_indexes(args.since, cal_end, token)
    only = {c.strip().lower() for c in args.contact if c.strip()}
    findings = derive_rows(values, headers, start_row, idx, indexes, only)

    upgrades = [f for f in findings if f["kind"] == "upgrade"]
    surface = [f for f in findings if f["kind"] == "surface"]
    info = [f for f in findings if f["kind"] == "info"]
    unknown = [f for f in findings if f["kind"] == "unknown"]

    if args.json:
        print(json.dumps({"since": args.since, "rows": len(values) - 1,
                          "findings": findings}, indent=2, ensure_ascii=False))
    else:
        print(f"BRISKEN OUTREACH RECONCILE  (window >= {args.since}; "
              f"post-event >= {POST_START}; {len(values) - 1} sheet rows)")
        print(f"\nUPGRADES -- mailbox/calendar-proven, auto-appliable "
              f"({len(upgrades)}):")
        for f in upgrades:
            print(f"  {f['cell']:24} {f['contact'][:26]:26} "
                  f"{f['from']!r:30} -> {f['to']!r}  ({f['why']})")
        print(f"\nDURING-EVENT-ONLY -- informational, column stays "
              f"({len(info)}):")
        for f in info:
            print(f"  row {f['row']:<4} {f['contact'][:26]:26} {f['why']}")
        print(f"\nHOLD FOR DIRK -- never auto-applied ({len(surface)}):")
        for f in surface:
            print(f"  row {f['row']:<4} {f['contact'][:26]:26} "
                  f"[{f['tier']}] {f['why']}")
        if unknown:
            print(f"\nUNKNOWN STATUS VALUES ({len(unknown)}):")
            for f in unknown:
                print(f"  row {f['row']:<4} {f['contact'][:26]:26} {f['why']}")

    if not args.write:
        return 0
    if not upgrades:
        print("\n--write: nothing to apply (0 upgrades)")
        return 0
    print(f"\n--write will PATCH {len(upgrades)} cells in the LIVE master "
          f"sheet ({FILE_PATH}).\nThis changes Dirk's working file. "
          "Reversible via the backup + SharePoint version history.")
    if not args.yes:
        answer = input("Type YES to proceed: ").strip()
        if answer != "YES":
            print("aborted")
            return 1
    return apply_upgrades(token, upgrades, ur)


if __name__ == "__main__":
    sys.exit(main())
