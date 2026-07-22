#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests"]
# ///
"""Per-contact outreach truth for Brisken: READ-ONLY both-mailbox, ALL-FOLDERS
Graph scan.

Answers "has X been contacted / replied?" from the authoritative source: the
mailboxes themselves, per feedback_brisken_outreach_truth_is_mailbox +
rule_brisken_graph_first. Replaces the ad-hoc .scratch scan scripts rebuilt in
4 straight sessions (register 2026-07-11/14/16/17).

Method (the memory's prescription, verbatim):
  - ONE corpus pull per mailbox: GET /users/{mbx}/messages with
    `$filter=sentDateTime ge {since} and isDraft eq false` (the messages
    collection spans ALL folders -- Dirk files sent Rome mail into custom
    folders like "TA Cook 2026 Rome - Outreach", so a SentItems+Inbox scan
    produces false "not contacted" negatives).
  - A real send is `isDraft eq false`; a parked draft is NOT a send (drafts
    are pulled separately and reported as draft_only).
  - Inbound from the contact counts as a reply only when the subject is not
    an OOO auto-reply ("Automatic reply", "Automatische Antwort",
    "Out of office", "Abwesen...").
  - parentFolderId is resolved to the folder display name so a hit is
    traceable ("which folder was that send filed in?").

Hard mailbox allowlist: EXACTLY dirk.neumann@brisken.com and
matthias.silva@brisken.com (compensating control until the Exchange
Application Access Policy exists -- rule_brisken_graph_first).

Read-only: GET calls only. Runs under autonomy.

Creds: app-only client-credentials from the gitignored
workspace/clients/brisken/context/.env (BRISKEN_TENANT_ID,
BRISKEN_GRAPH_CLIENT_ID, BRISKEN_GRAPH_CLIENT_SECRET), overridable via
BRISKEN_ENV_FILE or pre-set env vars. Needs the primary clone (worktrees do
not carry the gitignored context/).

Usage:
  uv run tools/brisken-outreach-truth.py --contacts a@x.com b@y.com
  uv run tools/brisken-outreach-truth.py --csv contacts.csv --column email
  ... [--since 2026-06-27] [--json]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

try:
    import requests
except ImportError:  # CI test env execs this module without live deps;
    requests = None  # the pure logic stays importable, transport unused.

# Windows consoles default to cp1252; an emoji in a subject line kills the
# print (the register 2026-07-17 charmap class -- hit live by this very tool's
# first smoke test). Self-defend regardless of harness env.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

MAILBOXES = ("dirk.neumann@brisken.com", "matthias.silva@brisken.com")
GRAPH = "https://graph.microsoft.com/v1.0"
# Tightened 2026-07-22 per feedback_brisken_outreach_truth_is_mailbox step 5:
# the short list mis-flagged Jose Vergel ("out of THE office" variant) as a
# genuine reply. Shared with brisken-outreach-reconcile.py (imports this).
OOO_RE = re.compile(
    r"automatic reply|automatische antwort|out of (the )?office|abwesen"
    r"|auto-?reply|risposta automatica|annual leave|on vacation",
    re.IGNORECASE,
)
PAGE_CAP = 300  # safety cap on paging per query


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_env() -> dict:
    """BRISKEN_* creds from env, BRISKEN_ENV_FILE, or the client context/.env."""
    keys = ("BRISKEN_TENANT_ID", "BRISKEN_GRAPH_CLIENT_ID",
            "BRISKEN_GRAPH_CLIENT_SECRET")
    if all(os.environ.get(k) for k in keys):
        return {k: os.environ[k] for k in keys}
    env_path = Path(os.environ.get("BRISKEN_ENV_FILE") or
                    repo_root() / "workspace" / "clients" / "brisken" /
                    "context" / ".env")
    creds: dict = {}
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            creds[k.strip()] = v.strip().strip('"').strip("'")
    missing = [k for k in keys if not (creds.get(k) or os.environ.get(k))]
    if missing:
        sys.exit(f"ERROR: missing {', '.join(missing)} (looked in env + {env_path}). "
                 "Run from the primary clone or set BRISKEN_ENV_FILE.")
    return {k: creds.get(k) or os.environ[k] for k in keys}


def get_token(creds: dict) -> str:
    r = requests.post(
        f"https://login.microsoftonline.com/{creds['BRISKEN_TENANT_ID']}"
        "/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": creds["BRISKEN_GRAPH_CLIENT_ID"],
            "client_secret": creds["BRISKEN_GRAPH_CLIENT_SECRET"],
            "scope": "https://graph.microsoft.com/.default",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def paged_get(url: str, token: str, params: dict | None = None) -> list[dict]:
    out: list[dict] = []
    pages = 0
    while url and pages < PAGE_CAP:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"},
                         params=params, timeout=60)
        r.raise_for_status()
        body = r.json()
        out.extend(body.get("value", []))
        url = body.get("@odata.nextLink")
        params = None  # nextLink already carries the query
        pages += 1
    if pages >= PAGE_CAP:
        print(f"WARN: page cap {PAGE_CAP} hit for {url[:80]} -- corpus truncated",
              file=sys.stderr)
    return out


SELECT = ("subject,sentDateTime,receivedDateTime,from,toRecipients,"
          "ccRecipients,bccRecipients,parentFolderId,isDraft")


def pull_corpus(mbx: str, token: str, since: str) -> tuple[list[dict], list[dict]]:
    """(sent-or-received real messages, drafts) for one mailbox, ALL folders."""
    assert mbx in MAILBOXES, f"mailbox {mbx!r} not in hard allowlist"
    base = f"{GRAPH}/users/{mbx}/messages"
    real = paged_get(base, token, {
        "$filter": f"sentDateTime ge {since}T00:00:00Z and isDraft eq false",
        "$select": SELECT, "$top": "100",
    })
    drafts = paged_get(base, token, {
        "$filter": "isDraft eq true",
        "$select": SELECT, "$top": "100",
    })
    return real, drafts


def folder_name(mbx: str, fid: str, token: str, cache: dict) -> str:
    assert mbx in MAILBOXES
    key = (mbx, fid)
    if key not in cache:
        try:
            r = requests.get(f"{GRAPH}/users/{mbx}/mailFolders/{fid}",
                             headers={"Authorization": f"Bearer {token}"},
                             params={"$select": "displayName"}, timeout=30)
            r.raise_for_status()
            cache[key] = r.json().get("displayName", "?")
        except Exception:
            cache[key] = "?"
    return cache[key]


def addrs(msg: dict) -> tuple[str, set[str]]:
    sender = ((msg.get("from") or {}).get("emailAddress") or {}).get(
        "address", "").lower()
    rcpt = {
        (r.get("emailAddress") or {}).get("address", "").lower()
        for field in ("toRecipients", "ccRecipients", "bccRecipients")
        for r in (msg.get(field) or [])
    }
    rcpt.discard("")
    return sender, rcpt


def scan(contacts: list[str], since: str) -> list[dict]:
    creds = load_env()
    token = get_token(creds)
    fcache: dict = {}
    corpora = {mbx: pull_corpus(mbx, token, since) for mbx in MAILBOXES}
    mbx_set = {m.lower() for m in MAILBOXES}

    results = []
    for contact in contacts:
        c = contact.strip().lower()
        outbound, inbound, ooo, draft_hits = [], [], [], []
        for mbx, (real, drafts) in corpora.items():
            for msg in real:
                sender, rcpt = addrs(msg)
                hit = {
                    "mailbox": mbx,
                    "date": msg.get("sentDateTime"),
                    "subject": (msg.get("subject") or "")[:90],
                    "folder": folder_name(mbx, msg.get("parentFolderId", ""),
                                          token, fcache),
                }
                if sender in mbx_set and c in rcpt:
                    outbound.append(hit)
                elif sender == c:
                    (ooo if OOO_RE.search(msg.get("subject") or "")
                     else inbound).append(hit)
            for msg in drafts:
                _, rcpt = addrs(msg)
                if c in rcpt:
                    draft_hits.append({
                        "mailbox": mbx,
                        "subject": (msg.get("subject") or "")[:90],
                    })
        outbound.sort(key=lambda h: h["date"] or "")
        inbound.sort(key=lambda h: h["date"] or "")
        results.append({
            "contact": c,
            "contacted": bool(outbound),
            "replied": bool(inbound),
            "ooo_only": bool(ooo) and not inbound,
            "draft_only": bool(draft_hits) and not outbound,
            "first_outbound": outbound[0]["date"] if outbound else None,
            "last_outbound": outbound[-1]["date"] if outbound else None,
            "last_reply": inbound[-1]["date"] if inbound else None,
            "outbound": outbound,
            "inbound": inbound,
            "drafts": draft_hits,
        })
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--contacts", nargs="*", default=[],
                    help="contact email addresses")
    ap.add_argument("--csv", help="CSV file of contacts")
    ap.add_argument("--column", default="email",
                    help="CSV column holding the address (default: email)")
    ap.add_argument("--since", default=None,
                    help="corpus window start YYYY-MM-DD (default: 120 days back)")
    ap.add_argument("--json", action="store_true", help="JSON output")
    args = ap.parse_args()

    contacts = list(args.contacts)
    if args.csv:
        with open(args.csv, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                v = (row.get(args.column) or "").strip()
                if v:
                    contacts.append(v)
    contacts = [c for c in dict.fromkeys(c.lower() for c in contacts) if "@" in c]
    if not contacts:
        sys.exit("ERROR: no contacts given (--contacts or --csv)")

    since = args.since or (
        dt.date.today() - dt.timedelta(days=120)).isoformat()
    results = scan(contacts, since)

    if args.json:
        print(json.dumps({"since": since, "results": results}, indent=2))
        return 0

    print(f"Outreach truth (both mailboxes, ALL folders, since {since}, "
          f"isDraft=false = real send):")
    for r in results:
        status = ("REPLIED" if r["replied"]
                  else "OOO-only" if r["ooo_only"]
                  else "CONTACTED, awaiting reply" if r["contacted"]
                  else "DRAFT-only (NOT sent)" if r["draft_only"]
                  else "no trace in either mailbox")
        print(f"\n  {r['contact']}: {status}")
        for h in r["outbound"][-3:]:
            print(f"    -> {h['date']}  [{h['folder']}] {h['subject']}")
        for h in r["inbound"][-3:]:
            print(f"    <- {h['date']}  {h['subject']}")
        for h in r["drafts"][:3]:
            print(f"    (draft, unsent) {h['subject']}")
    print("\nNOTE: 'no trace' is mailbox silence, not proof of no contact -- "
          "H5 rows use an off-mailbox bespoke channel; never auto-downgrade "
          "an H5 lead on this output alone (hold for Dirk).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
