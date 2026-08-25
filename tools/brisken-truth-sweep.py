#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests"]
# ///
"""Brisken outreach truth sweep: full-corpus mailbox pull + canonical
cross-cohort truth ledger.

Extends the per-contact truth tool (tools/brisken-outreach-truth.py) from
"answer for these N addresses" to "build the one ledger every cohort claim is
reconciled against". Two phases:

  CORPUS  For each allowlisted mailbox, enumerate EVERY mail folder and pull,
          per non-empty folder, all real messages since --since (outbound =
          from==owner, inbound = everything else) plus all drafts in that
          folder (drafts anywhere, not only the Drafts folder: the 2026-07-08
          T1 wave left 19 unsent decoy copies in Matthias's Deleted Items).
          Each folder lands in its own JSON cache file so a 503 on one
          archived subtree never loses the rest; --resume refetches only the
          folders that previously failed.
  LEDGER  Cross-reference the corpus against every known outreach cohort
          (E1/E2/E3 during-event waves, T1 booth network, T2 warm-engaged,
          H5 hottest leads, T3, GA) plus the confirm-zero cohorts, the master
          sheet (read-only Graph workbook snapshot, columns resolved BY
          HEADER NAME), the Lead Desk sqlite (read-only flyctl sftp copy),
          the Zoho CRM cache, and the suppression list. Emit
          <out>/outreach-truth-ledger.json with per-member mailbox evidence
          (internetMessageId / timestamp / folder / mailbox), the known
          contradictions with resolutions, and complete:true|false with the
          enumerated failed folders.

Judgment policy: sends are recorded as facts for every cohort. H5 rows NEVER
get a negative judgment (no-reply, stale) derived from mailbox silence; their
channel is partly off-mailbox (rule: "mailbox-silence-only; never downgraded
off-mailbox").

READ-ONLY throughout: Graph GETs, a GET-shaped workbook usedRange snapshot,
an sftp *get* of the Lead Desk sqlite. Nothing in the tenant is created,
sent, or mutated. Hard mailbox allowlist: EXACTLY dirk.neumann@brisken.com
and matthias.silva@brisken.com (rule_brisken_graph_first).

Creds: app-only client-credentials from the gitignored
workspace/clients/brisken/context/.env (see tools/brisken-outreach-truth.py).
Worktrees do not carry the gitignored context/: pass --main-repo (or
BRISKEN_ENV_FILE) pointing at the primary clone.

Usage:
  uv run tools/brisken-truth-sweep.py --since 2026-05-01 --out <dir> \
      [--main-repo <primary-clone>] [--mailbox both] [--resume] \
      [--skip-corpus] [--ledger-only] [--leaddesk-db <sqlite>] [--skip-leaddesk]

Capture-adequacy verify mode (no Graph calls; reads the EXISTING corpus
cache under <out>/corpus-cache and diffs the window's outbound
internetMessageIds against the Lead Desk DB):

  uv run tools/brisken-truth-sweep.py --verify-live-capture \
      --window 2026-07-18..2026-08-01 --out <dir> \
      (--db <local lead-desk.sqlite copy> [--write-run] \
       | --base-url https://... [--secret <ingest secret>])

Prints total / present / missing (imid, to, subject, folder) and a verdict
line: CAPTURE-ADEQUATE (0 missing) or CAPTURE-GAPS (N). Read-only; the one
exception is --write-run, which appends a truth_runs row
(kind='capture-verify') to the LOCAL --db copy.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:  # CI test env execs this module without live deps;
    requests = None  # the pure logic stays importable, transport unused.

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _load(name: str, filename: str):
    path = Path(__file__).resolve().parent / filename
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Shared Graph plumbing (token, paged_get, folder walk, allowlist asserts)
truth = _load("brisken_outreach_truth", "brisken-outreach-truth.py")
# Sheet identity + usedRange reader + inbound noise classifier
recon = _load("brisken_outreach_reconcile", "brisken-outreach-reconcile.py")

GRAPH = truth.GRAPH
MAILBOXES = truth.MAILBOXES
OOO_RE = truth.OOO_RE
SELECT = truth.SELECT

# ---------------------------------------------------------------------------
# Cohort constants (stable strings; rosters load from the input files below)
# ---------------------------------------------------------------------------

# During-event wave subjects; canonical source is lead-desk ground.py
# CAMPAIGN_WAVES. Cross-checked against that file at run time when present.
WAVE_SUBJECTS = {
    "E1": "worth fifteen minutes at booth #2, rome",
    "E2": "what treasury teams are actually doing with ai now",
    "E3": "last day at booth #2 in rome, thursday",
}
GROUND_PY = ("workspace/clients/brisken/automations/lead-desk/src/"
             "lead_desk/ground.py")

T1_SUBJECT = "following up from the sap conference in rome"

# T2 warm-engaged: Dirk sent the batch himself 2026-07-12. The comms-log
# STATE entry labels the window "14:11 and 16:26 UTC", but the mailbox
# timestamps prove those clock times were CEST (UTC+2): the batch runs
# 12:11-14:26Z and the two misroutes land 13:31Z/13:56Z. Cohort membership
# is corpus-derived from Dirk's outbound in the corrected window; the ICD
# wave (15:32Z+) stays out.
T2_WINDOW = ("2026-07-12T12:00:00Z", "2026-07-12T14:40:00Z")
T2_MISROUTED_SUBJECTS = {"market data hub, picking it back up",
                         "missed you in rome"}
T2_EXPECTED = {"total": 16, "prospect": 14, "misrouted": 2}

GA_EXPECTED_COUNT = 19
GA_DATE = "2026-07-27"

# brisken.io shows up only on junk contact-card sync artifacts
# ("wireless caller@brisken.io"); treat both as internal, never cohort mail.
INTERNAL_DOMAINS = ("brisken.com", "brisken.io")
NOREPLY_RE = re.compile(r"^no-?reply@")

# Input files, relative to the primary clone root (m) or its brisken context
# dir (c). Every one is existence-checked; a missing file is recorded in the
# ledger inputs section with the actual directory listing, never skipped
# silently.
INPUTS = {
    "e1_send_log": ("c", "lead-generation/Rome-Event/email-campaign/"
                         "rome2026-send-log-E1.csv"),
    "e2_send_log": ("c", "lead-generation/Rome-Event/email-campaign/"
                         "rome2026-send-log-E2.csv"),
    "e3_send_log": ("c", "lead-generation/Rome-Event/email-campaign/"
                         "rome2026-send-log-E3.csv"),
    "e1_send_list": ("c", "lead-generation/Rome-Event/audience-lists/"
                          "rome2026-E1-send-list.csv"),
    "e3_send_list": ("c", "lead-generation/Rome-Event/audience-lists/"
                          "rome2026-E3-send-list.csv"),
    "dirk_exclusions": ("c", "lead-generation/Rome-Event/audience-lists/"
                             "dirk-exclusions.txt"),
    "t1_roster": ("m", "workspace/clients/brisken/deliverables/"
                       "lead-generation/rome-2026/"
                       "booth-network-touch-for-dirk.md"),
    "h5_roster": ("m", "workspace/clients/brisken/deliverables/"
                       "lead-generation/rome-2026/dirk-send-pack/README.md"),
    "t3_roster": ("c", "lead-generation/rome-t3-wave-rebuilt.md"),
    "t3_snapshot": ("m", ".scratch/t3-touch2-truth.json"),
    "ga_send_script": ("m", ".scratch/ga_send_wave.py"),
    "ga_wave_doc": ("c", "lead-generation/rome-ga-wave.md"),
    "suppression": ("c", "lead-generation/outreach-assets/"
                         "suppression-list.csv"),
    "nestle_contacts": ("c", "lead-generation/nestle-stratifi-contacts.csv"),
    "zoho_cache": ("c", "zoho-crm.json"),
    "comms_log": ("c", "comms-log.md"),
}


# T3 per-variant subjects (rome-t3-wave-rebuilt.md Assignment table). Several
# overlap the GA subject set; both waves are disambiguated by roster, not
# subject alone.
T3_SUBJECTS = {
    "following up after rome",
    "after the sap treasury conference in rome",
    "we were at the same event in rome",
    "following up on your visit to our rome booth",
    "picking up from our booth in rome",
}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def norm_subject(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def clean_addr(raw: str) -> str:
    """Extract the real address from a recipient string. The E1 send pass
    stored malformed recipient fields verbatim (newline + LinkedIn URL glued
    onto the address, '(apollo) ' prefixes); Exchange kept them, so the
    corpus echoes them back. First RFC-shaped match wins; a string with no
    @-match comes back lowercased as-is."""
    raw = (raw or "").strip().lower()
    if not raw or ("@" in raw and EMAIL_RE.fullmatch(raw)):
        return raw
    m = EMAIL_RE.search(raw)
    return m.group(0) if m else raw


def base_domain(addr: str) -> str:
    return addr.rsplit("@", 1)[-1] if "@" in addr else ""


def is_internal(addr: str) -> bool:
    return base_domain(addr) in INTERNAL_DOMAINS


# ---------------------------------------------------------------------------
# CORPUS phase: per-folder cached pull with retry
# ---------------------------------------------------------------------------

BACKOFFS = (5, 15, 45)  # seconds; Retry-After wins when larger


class TokenBox:
    """App-only token that re-mints itself before Graph's ~60-min expiry.
    The corpus phase alone can run past an hour; a single token minted at
    start would 401 the ledger phase."""

    TTL = 40 * 60  # refresh comfortably ahead of expiry

    def __init__(self, creds: dict):
        self._creds = creds
        self._token: str | None = None
        self._minted = 0.0

    def get(self) -> str:
        if self._token is None or time.monotonic() - self._minted > self.TTL:
            self._token = truth.get_token(self._creds)
            self._minted = time.monotonic()
        return self._token


def _fid_slug(fid: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_=-]", "_", fid)[:40]
    return f"{safe}-{hashlib.sha1(fid.encode()).hexdigest()[:10]}"


def _msg_row(m: dict, kind: str, folder_path: str) -> dict:
    def rcpts(field):
        return [((r.get("emailAddress") or {}).get("address") or "").lower()
                for r in (m.get(field) or [])]
    return {
        "id": m.get("id"),
        "imid": m.get("internetMessageId"),
        "from": ((m.get("from") or {}).get("emailAddress") or {}).get(
            "address", "").lower(),
        "to": rcpts("toRecipients"),
        "cc": rcpts("ccRecipients"),
        "bcc": rcpts("bccRecipients"),
        "subject": m.get("subject") or "",
        "sent": m.get("sentDateTime"),
        "received": m.get("receivedDateTime"),
        "is_draft": bool(m.get("isDraft")),
        "kind": kind,
        "folder": folder_path,
    }


def _paged_get_retry(url: str, token: str, params: dict,
                     label: str) -> list[dict]:
    """truth.paged_get with per-folder retry x3 (backoff 5/15/45s, honoring
    Retry-After on 429/503). Raises on final failure."""
    last: Exception | None = None
    for attempt in range(len(BACKOFFS) + 1):
        try:
            return truth.paged_get(url, token, dict(params))
        except requests.HTTPError as e:
            last = e
            status = e.response.status_code if e.response is not None else 0
            if attempt >= len(BACKOFFS):
                break
            wait = BACKOFFS[attempt]
            if status in (429, 503) and e.response is not None:
                try:
                    wait = max(wait, int(e.response.headers.get(
                        "Retry-After", "0")))
                except ValueError:
                    pass
            print(f"    retry {attempt + 1}/3 in {wait}s "
                  f"({label}: HTTP {status})", file=sys.stderr)
            time.sleep(wait)
        except requests.RequestException as e:  # timeouts, resets
            last = e
            if attempt >= len(BACKOFFS):
                break
            wait = BACKOFFS[attempt]
            print(f"    retry {attempt + 1}/3 in {wait}s ({label}: {e})",
                  file=sys.stderr)
            time.sleep(wait)
    raise last  # type: ignore[misc]


def pull_folder(mbx: str, folder: dict, tb: TokenBox, since: str) -> dict:
    """One folder -> cache record. Never raises; failure is recorded."""
    assert mbx in MAILBOXES, f"mailbox {mbx!r} not in hard allowlist"
    token = tb.get()
    base = f"{GRAPH}/users/{mbx}/mailFolders/{folder['id']}/messages"
    rec = {
        "mailbox": mbx,
        "folder_id": folder["id"],
        "folder_path": folder["_path"],
        "total_item_count": folder.get("totalItemCount", 0),
        "since": since,
        "pulled_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "ok": False,
        "error": None,
        "messages": [],
    }
    try:
        real = _paged_get_retry(base, token, {
            "$filter": f"sentDateTime ge {since}T00:00:00Z "
                       "and isDraft eq false",
            "$select": SELECT, "$top": "100",
        }, f"{mbx} [{folder['_path']}] real")
        drafts = _paged_get_retry(base, token, {
            "$filter": "isDraft eq true",
            "$select": SELECT, "$top": "100",
        }, f"{mbx} [{folder['_path']}] drafts")
    except Exception as e:  # recorded, never fatal to the sweep
        rec["error"] = f"{type(e).__name__}: {e}"
        return rec
    owner = mbx.lower()
    for m in real:
        sender = ((m.get("from") or {}).get("emailAddress") or {}).get(
            "address", "").lower()
        rec["messages"].append(_msg_row(
            m, "outbound" if sender == owner else "inbound", folder["_path"]))
    for m in drafts:
        rec["messages"].append(_msg_row(m, "draft", folder["_path"]))
    rec["ok"] = True
    return rec


def run_corpus(mailboxes: list[str], tb: TokenBox, since: str,
               cache_root: Path, resume: bool) -> None:
    for mbx in mailboxes:
        assert mbx in MAILBOXES, f"mailbox {mbx!r} not in hard allowlist"
        mbx_dir = cache_root / mbx
        mbx_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n== corpus: {mbx}")
        folders = truth.list_folders(mbx, tb.get())
        nonempty = [f for f in folders if f.get("totalItemCount")]
        print(f"   {len(folders)} folders, {len(nonempty)} non-empty")
        done = failed = skipped = 0
        for i, f in enumerate(nonempty, 1):
            cache_file = mbx_dir / f"{_fid_slug(f['id'])}.json"
            if cache_file.is_file():
                try:
                    prev = json.loads(cache_file.read_text(encoding="utf-8"))
                except Exception:
                    prev = None
                if prev and prev.get("ok") and (resume or prev.get(
                        "since") == since):
                    skipped += 1
                    continue
                if prev and not prev.get("ok") and not resume:
                    pass  # full run refetches failures too
            rec = pull_folder(mbx, f, tb, since)
            cache_file.write_text(
                json.dumps(rec, ensure_ascii=False), encoding="utf-8")
            if rec["ok"]:
                done += 1
            else:
                failed += 1
                print(f"   FAIL [{f['_path']}]: {rec['error']}",
                      file=sys.stderr)
            if i % 25 == 0:
                print(f"   ... {i}/{len(nonempty)} folders "
                      f"({done} pulled, {skipped} cached, {failed} failed)")
        print(f"   done: {done} pulled, {skipped} reused from cache, "
              f"{failed} failed")


def load_corpus(cache_root: Path) -> dict:
    """All cached folder records -> deduped message lists + failure roster."""
    out: dict = {"outbound": [], "inbound": [], "drafts": [],
                 "folders_ok": 0, "folders_failed": [], "by_mailbox": {}}
    seen: set[tuple[str, str]] = set()
    if not cache_root.is_dir():
        return out
    for mbx_dir in sorted(p for p in cache_root.iterdir() if p.is_dir()):
        mb = out["by_mailbox"].setdefault(
            mbx_dir.name, {"outbound": 0, "inbound": 0, "drafts": 0,
                           "folders_ok": 0, "folders_failed": 0})
        for cf in sorted(mbx_dir.glob("*.json")):
            rec = json.loads(cf.read_text(encoding="utf-8"))
            if not rec.get("ok"):
                out["folders_failed"].append({
                    "mailbox": rec["mailbox"],
                    "folder_path": rec["folder_path"],
                    "folder_id": rec["folder_id"],
                    "error": rec.get("error"),
                })
                mb["folders_failed"] += 1
                continue
            out["folders_ok"] += 1
            mb["folders_ok"] += 1
            for row in rec["messages"]:
                key = (rec["mailbox"], row.get("id") or row.get("imid")
                       or repr(row))
                if key in seen:
                    continue
                seen.add(key)
                row["mailbox"] = rec["mailbox"]
                out[{"outbound": "outbound", "inbound": "inbound",
                     "draft": "drafts"}[row["kind"]]].append(row)
                mb[{"outbound": "outbound", "inbound": "inbound",
                    "draft": "drafts"}[row["kind"]]] += 1
    return out


# ---------------------------------------------------------------------------
# Corpus indexes
# ---------------------------------------------------------------------------

def build_indexes(corpus: dict) -> dict:
    """outbound by recipient, genuine replies + OOO by sender, drafts by
    recipient. Outbound counts ONLY messages sitting in the SENDER's own
    mailbox (from == mailbox owner), so a BCC/decoy copy in the other mailbox
    never reads as a send."""
    sends: dict[str, list] = {}
    replies: dict[str, list] = {}
    ooo: dict[str, list] = {}
    drafts: dict[str, list] = {}
    malformed: dict[str, str] = {}

    def cleaned(addrs_raw):
        out = set()
        for raw in addrs_raw:
            if not raw:
                continue
            c = clean_addr(raw)
            if c != raw:
                malformed[raw] = c
            out.add(c)
        return out

    for m in corpus["outbound"]:
        ev = {"imid": m["imid"], "ts": m["sent"], "folder": m["folder"],
              "mailbox": m["mailbox"], "subject": m["subject"][:90]}
        for a in cleaned(m["to"] + m["cc"] + m["bcc"]):
            sends.setdefault(a, []).append(ev)
    for m in corpus["inbound"]:
        sender = m["from"]
        if not sender or is_internal(sender):
            continue
        noise = recon.inbound_noise(m["subject"], sender)
        if noise == "ooo":
            bucket = ooo
        elif noise is None:
            bucket = replies
        else:
            continue  # NDR / calendar-system noise
        bucket.setdefault(sender, []).append(
            {"imid": m["imid"], "ts": m["sent"] or m["received"],
             "folder": m["folder"], "mailbox": m["mailbox"],
             "subject": m["subject"][:90]})
    for m in corpus["drafts"]:
        for a in cleaned(m["to"] + m["cc"] + m["bcc"]):
            drafts.setdefault(a, []).append(
                {"mailbox": m["mailbox"], "folder": m["folder"],
                 "subject": m["subject"][:90]})
    for d in (sends, replies, ooo):
        for hits in d.values():
            hits.sort(key=lambda h: h["ts"] or "")
    return {"sends": sends, "replies": replies, "ooo": ooo, "drafts": drafts,
            "malformed_addresses": malformed}


def member_facts(email: str, idx: dict, judge: bool = True) -> dict:
    e = email.lower()
    sends = idx["sends"].get(e, [])
    out = {
        "sent": bool(sends),
        "send_count": len(sends),
        "first_send": sends[0]["ts"] if sends else None,
        "last_send": sends[-1]["ts"] if sends else None,
        "evidence": sends,
    }
    if judge:  # never for H5 (mailbox-silence-only policy)
        repl = idx["replies"].get(e, [])
        oo = idx["ooo"].get(e, [])
        out.update({
            "replied": bool(repl),
            "last_reply": repl[-1]["ts"] if repl else None,
            "reply_evidence": repl,
            "ooo_only": bool(oo) and not repl,
            "draft_pending": bool(idx["drafts"].get(e)) and not sends,
        })
    return out


def wave_sends(corpus: dict, subject: str,
               from_mbx: str | None = None) -> list[dict]:
    """Outbound rows whose subject IS the wave subject (exact after
    whitespace/case normalization; no Re:-stripping, so our own replies on
    the thread never count as wave sends)."""
    subj = norm_subject(subject)
    rows = [m for m in corpus["outbound"] if norm_subject(m["subject"]) == subj]
    if from_mbx:
        rows = [m for m in rows if m["mailbox"] == from_mbx]
    return rows


def recipients_of(rows: list[dict]) -> dict[str, list[dict]]:
    by: dict[str, list[dict]] = {}
    for m in rows:
        ev = {"imid": m["imid"], "ts": m["sent"], "folder": m["folder"],
              "mailbox": m["mailbox"], "subject": m["subject"][:90]}
        for a in {clean_addr(a) for a in m["to"] if a}:
            if not is_internal(a):
                by.setdefault(a, []).append(ev)
    return by


# ---------------------------------------------------------------------------
# Capture-adequacy verify (--verify-live-capture): did every real outbound
# send in the window land in the Lead Desk DB?
# ---------------------------------------------------------------------------

def window_outbound(corpus: dict, start: str, end: str) -> list[dict]:
    """Outbound corpus rows sent inside the window (dates inclusive) with at
    least one EXTERNAL to/cc recipient. Internal-only mail is invisible to
    the Lead Desk by design (capture builds payloads from to+cc and its
    filter drops own-domain recipients), so it never counts as a gap.
    Deduped by imid: folder copies of one message are one send."""
    lo, hi = f"{start}T00:00:00Z", f"{end}T23:59:59Z"
    rows, seen = [], set()
    for m in corpus["outbound"]:
        sent = m.get("sent") or ""
        if not (lo <= sent <= hi):
            continue
        ext = sorted({a for a in (clean_addr(x) for x in
                                  (m["to"] + m["cc"]) if x)
                      if "@" in a and not is_internal(a)})
        if not ext:
            continue
        key = m.get("imid") or m.get("id")
        if key in seen:
            continue
        seen.add(key)
        rows.append({**m, "external": ext})
    return rows


def diff_capture(rows: list[dict], present: dict[str, str]) -> dict:
    """Pure diff: windowed corpus outbound rows vs the imid->source map of
    what the DB already knows. Returns totals, per-source presence counts,
    and the missing rows (imid, to, subject, folder)."""
    missing: list[dict] = []
    by_source: dict[str, int] = {}
    for m in rows:
        src = present.get(m.get("imid") or "")
        if src:
            by_source[src] = by_source.get(src, 0) + 1
        else:
            missing.append({"imid": m.get("imid"),
                            "to": m.get("external") or m.get("to"),
                            "subject": (m.get("subject") or "")[:90],
                            "folder": m.get("folder"),
                            "sent": m.get("sent"),
                            "mailbox": m.get("mailbox")})
    return {"total": len(rows), "present": len(rows) - len(missing),
            "present_by_source": by_source, "missing": missing}


def db_imid_sources(db_path: Path) -> dict[str, str]:
    """imid -> where the local DB copy knows it from: an outreach_events row
    (captured send: ext_key IS the internetMessageId), a worker send
    (send_attempts carries the imid; its event's ext_key is the cadence
    key), or a parked unmatched payload (captured, awaiting operator
    link)."""
    con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        out: dict[str, str] = {}
        for (k,) in con.execute(
                "SELECT DISTINCT ext_key FROM outreach_events "
                "WHERE ext_key IS NOT NULL AND direction = 'outbound'"):
            out.setdefault(k, "events")
        for (k,) in con.execute(
                "SELECT DISTINCT internet_message_id FROM send_attempts "
                "WHERE internet_message_id IS NOT NULL"):
            out.setdefault(k, "send_attempts")
        for (p,) in con.execute("SELECT payload FROM unmatched_events"):
            try:
                imid = (json.loads(p).get("internet_message_id") or "").strip()
            except (ValueError, AttributeError):
                continue
            if imid:
                out.setdefault(imid, "unmatched")
        return out
    finally:
        con.close()


def api_imid_sources(base_url: str, secret: str) -> dict[str, str]:
    """Page GET /api/events for outbound ext_keys. Only the event log is
    visible over the API (send_attempts / unmatched_events are not), so a
    worker send whose event carries the cadence ext_key reads as missing
    here; use --db for the authoritative diff."""
    hdrs = {"Authorization": f"Bearer {secret}"}
    out: dict[str, str] = {}
    offset, page = 0, 1000
    while True:
        r = requests.get(f"{base_url.rstrip('/')}/api/events", headers=hdrs,
                         params={"direction": "outbound",
                                 "limit": page, "offset": offset},
                         timeout=60)
        r.raise_for_status()
        body = r.json()
        for ev in body["events"]:
            if ev.get("ext_key"):
                out.setdefault(ev["ext_key"], "events")
        offset += len(body["events"])
        if not body["events"] or offset >= body["total"]:
            return out


def write_verify_run(db_path: Path, window: str, corpus: dict,
                     rep: dict, started_at: str) -> str:
    """Record the verify pass as a truth_runs row (kind='capture-verify') in
    the LOCAL DB copy. Never runs in --base-url mode."""
    run_id = f"capture-verify-{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}"
    finished = dt.datetime.now(dt.timezone.utc).isoformat()
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            "INSERT INTO truth_runs (run_id, kind, started_at, finished_at, "
            "window_since, corpus_messages, folders_scanned, folders_failed, "
            "events_added, anomalies, report) "
            "VALUES (?, 'capture-verify', ?, ?, ?, ?, ?, ?, 0, NULL, ?)",
            (run_id, started_at, finished, window, rep["total"],
             corpus["folders_ok"], json.dumps(corpus["folders_failed"]),
             json.dumps({"present": rep["present"],
                         "present_by_source": rep["present_by_source"],
                         "missing": [m["imid"] for m in rep["missing"]]})))
        con.commit()
    finally:
        con.close()
    return run_id


def run_verify_live_capture(args) -> int:
    if not args.window or ".." not in args.window:
        sys.exit("ERROR: --verify-live-capture needs --window START..END "
                 "(YYYY-MM-DD..YYYY-MM-DD)")
    if not (args.db or args.base_url):
        sys.exit("ERROR: pass --db <local lead-desk.sqlite copy> or "
                 "--base-url <lead-desk origin>")
    if args.write_run and not args.db:
        sys.exit("ERROR: --write-run needs --db (the run row is written to "
                 "the local copy only, never over the API)")
    start, end = args.window.split("..", 1)
    started_at = dt.datetime.now(dt.timezone.utc).isoformat()

    cache_root = Path(args.out) / "corpus-cache"
    corpus = load_corpus(cache_root)
    if not corpus["outbound"]:
        sys.exit(f"ERROR: no cached outbound messages under {cache_root}; "
                 "run the corpus phase first")
    rows = window_outbound(corpus, start, end)

    if args.db:
        present = db_imid_sources(Path(args.db))
    else:
        secret = args.secret or os.environ.get("LEAD_DESK_INGEST_SECRET", "")
        if not secret:
            sys.exit("ERROR: --base-url needs --secret or "
                     "LEAD_DESK_INGEST_SECRET")
        present = api_imid_sources(args.base_url, secret)

    rep = diff_capture(rows, present)
    print(f"window {start}..{end}: {rep['total']} corpus sends "
          f"(external to/cc recipients, deduped by imid)")
    print(f"present in db: {rep['present']} {rep['present_by_source']}")
    if corpus["folders_failed"]:
        print(f"NOTE: {len(corpus['folders_failed'])} corpus folders failed "
              "to pull; the corpus side may undercount", file=sys.stderr)
    for m in rep["missing"]:
        print(f"  MISSING {m['imid']}  to={','.join(m['to'])}  "
              f"[{m['sent']}]  {m['subject']!r}  "
              f"({m['mailbox']}: {m['folder']})")
    n = len(rep["missing"])
    print("CAPTURE-ADEQUATE (0 missing)" if n == 0
          else f"CAPTURE-GAPS ({n})")
    if args.write_run:
        run_id = write_verify_run(Path(args.db), args.window, corpus, rep,
                                  started_at)
        print(f"truth_runs row written: {run_id}")
    return 0 if n == 0 else 1


# ---------------------------------------------------------------------------
# Input loaders (existence-verified; misses recorded with the real listing)
# ---------------------------------------------------------------------------

def resolve_inputs(main_repo: Path, ctx: Path) -> tuple[dict, dict]:
    meta: dict = {}
    paths: dict = {}
    for key, (root, rel) in INPUTS.items():
        p = (main_repo if root == "m" else ctx) / rel
        entry = {"path": str(p), "exists": p.is_file()}
        if not entry["exists"]:
            parent = p.parent
            entry["dir_listing"] = (sorted(x.name for x in parent.iterdir())
                                    if parent.is_dir() else
                                    f"missing dir {parent}")
        meta[key] = entry
        paths[key] = p if entry["exists"] else None
    return paths, meta


def load_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_send_log(path: Path) -> dict:
    """Send-log rows, with the email field CLEANED (the E1 log carries
    '(apollo) ' prefixes, 'a; b' double addresses, bare LinkedIn URLs, and
    internal brisken addresses among its 'sent' rows). Unparseable rows are
    kept visible, never silently dropped."""
    rows = load_csv(path)
    st = {"sent": 0, "failed": 0, "blank": 0}
    emails: dict[str, dict] = {}
    garbage: list[str] = []
    for r in rows:
        raw = (r.get("email") or "").strip().lower()
        s = (r.get("status") or "").strip().lower() or "blank"
        st[s if s in st else "blank"] += 1
        e = clean_addr(raw)
        if raw and "@" not in e:
            garbage.append(raw)
            continue
        if e:
            emails.setdefault(e, r)
    return {"rows": len(rows), "unique_emails": len(emails),
            "status_counts": st,
            "unparseable_rows": garbage,
            "sent_emails": sorted(e for e, r in emails.items()
                                  if (r.get("status") or "").strip().lower()
                                  == "sent"),
            "all_emails": sorted(emails)}


def load_t1_roster(path: Path) -> list[str]:
    """Names (no addresses in the doc) from the 'Who it goes to' table."""
    names, in_table = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## Who it goes to"):
            in_table = True
            continue
        if in_table:
            if line.startswith("## "):
                break
            m = re.match(r"\|\s*([^|]+?)\s*\|", line)
            if m and m.group(1) not in ("Name", "---", ""):
                if not set(m.group(1)) <= set("-: "):
                    names.append(m.group(1))
    return names


def load_h5_roster(path: Path) -> list[str]:
    """Every To:/Cc: address in the dirk-send-pack README (11 across 6 notes)."""
    addrs: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if re.match(r"\s*-\s*\*\*(To|Cc):\*\*", line):
            addrs.extend(a.lower() for a in EMAIL_RE.findall(line))
    return sorted(dict.fromkeys(addrs))


def load_t3_roster(path: Path) -> list[str]:
    """Emails in <> inside the Assignment table rows (DROPPED line excluded)."""
    addrs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("|") and "<" in line:
            addrs.extend(a.lower() for a in EMAIL_RE.findall(line))
    return sorted(dict.fromkeys(addrs))


def load_ga_script(path: Path) -> dict:
    """EXPECTED / HELD4 / GA_SUBJECTS parsed out of the guarded send script
    (.scratch/ga_send_wave.py) -- the exact 19 that went out 2026-07-27."""
    text = path.read_text(encoding="utf-8")

    def block(name):
        m = re.search(rf"{name}\s*=\s*\{{(.*?)\}}", text, re.DOTALL)
        return m.group(1) if m else ""

    return {
        "expected": sorted(a.lower() for a in EMAIL_RE.findall(
            block("EXPECTED"))),
        "held4": sorted(a.lower() for a in EMAIL_RE.findall(block("HELD4"))),
        "subjects": re.findall(r'"([^"]+)"', block("GA_SUBJECTS")),
    }


def load_suppression(path: Path) -> dict:
    rows = load_csv(path)
    kinds: dict[str, int] = {}
    for r in rows:
        kinds[(r.get("kind") or "?").strip()] = kinds.get(
            (r.get("kind") or "?").strip(), 0) + 1
    return {"rows": len(rows), "by_kind": kinds,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def crosscheck_wave_subjects(main_repo: Path) -> dict:
    """Verify the embedded wave subjects against lead-desk ground.py."""
    p = main_repo / GROUND_PY
    if not p.is_file():
        return {"checked": False, "note": f"{GROUND_PY} not found"}
    text = p.read_text(encoding="utf-8")
    mismatches = [f"{w}: {s!r} not in ground.py"
                  for w, s in WAVE_SUBJECTS.items() if s not in text]
    return {"checked": True, "mismatches": mismatches}


# ---------------------------------------------------------------------------
# Sheet snapshot (read-only Graph workbook usedRange; header-name resolution)
# ---------------------------------------------------------------------------

def pull_sheet(token: str) -> dict:
    ur = recon.sheet_used_range(token)
    values = ur["values"]
    headers = [str(h).strip() for h in values[0]]
    lower = {h.lower(): i for i, h in enumerate(headers)}

    def find(*cands, contains=None):
        for c in cands:
            if c.lower() in lower:
                return lower[c.lower()]
        if contains:
            for h, i in lower.items():
                if contains in h:
                    return i
        return None

    cols = {
        "email": find("email"),
        "alt_email": find("alt_email"),
        "tier": find("Tier"),
        "status": find(recon.STATUS_COL),
        "last_outreach": find("last_outreach", contains="last_outreach"),
        "linkedin_status": find("linkedin_status", contains="linkedin"),
        "salesnav_status": find("salesnav_status", contains="salesnav"),
        "stop": find("stop"),
    }
    start_row, _ = recon.parse_a1_start(ur["address"])
    per_email: dict[str, dict] = {}
    tier_counts: dict[str, int] = {}
    salesnav_counts: dict[str, int] = {}

    def cell(row, key):
        i = cols.get(key)
        if i is None or i >= len(row):
            return None
        v = row[i]
        return str(v).strip() if v not in (None, "") else ""

    for offset, row in enumerate(values[1:], start=start_row + 1):
        tier = (cell(row, "tier") or "").upper()
        tier_counts[tier or "(blank)"] = tier_counts.get(
            tier or "(blank)", 0) + 1
        sn = cell(row, "salesnav_status") or "(blank)"
        salesnav_counts[sn] = salesnav_counts.get(sn, 0) + 1
        rec = {"row": offset, "tier": cell(row, "tier"),
               "status": cell(row, "status"),
               "last_outreach": cell(row, "last_outreach"),
               "linkedin_status": cell(row, "linkedin_status"),
               "salesnav_status": cell(row, "salesnav_status"),
               "stop": cell(row, "stop")}
        for key in ("email", "alt_email"):
            e = (cell(row, key) or "").lower()
            if e and "@" in e:
                per_email.setdefault(e, rec)
    return {
        "pulled_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "file": recon.FILE_PATH, "tab": recon.TAB,
        "rows": len(values) - 1,
        "headers": headers,
        "columns_resolved": {k: (headers[i] if i is not None else None)
                             for k, i in cols.items()},
        "tier_counts": tier_counts,
        "anon_count": tier_counts.get("ANON", 0),
        "salesnav_status_counts": salesnav_counts,
        "per_email": per_email,
    }


# ---------------------------------------------------------------------------
# Lead Desk sqlite (read-only sftp copy)
# ---------------------------------------------------------------------------

def fetch_leaddesk_db(dest: Path) -> tuple[Path | None, str | None]:
    flyctl = shutil.which("flyctl") or shutil.which("fly")
    if not flyctl:
        return None, "flyctl not on PATH"
    dest.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, MSYS_NO_PATHCONV="1")
    err = None
    for attempt in range(3):
        if dest.exists():
            dest.unlink()
        r = subprocess.run(
            [flyctl, "ssh", "sftp", "get", "/data/lead-desk.sqlite",
             str(dest), "-a", "brisken-lead-desk"],
            capture_output=True, text=True, timeout=300, env=env)
        if r.returncode == 0 and dest.is_file() and dest.stat().st_size > 0:
            return dest, None
        err = (r.stderr or r.stdout or "").strip()[-300:]
        time.sleep(BACKOFFS[min(attempt, 2)])
    return None, f"flyctl sftp get failed after 3 tries: {err}"


def read_leaddesk(db_path: Path, cohort_emails: dict[str, list[str]]) -> dict:
    con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    out: dict = {"db_file": str(db_path)}
    try:
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")]
        out["tables"] = sorted(tables)
        out["contacts"] = con.execute(
            "SELECT COUNT(*) FROM contacts").fetchone()[0]
        out["events_by_type_campaign"] = [
            dict(r) for r in con.execute(
                "SELECT type, campaign, COUNT(*) AS n FROM outreach_events "
                "GROUP BY type, campaign ORDER BY campaign, type")]
        out["e_wave_ext_keys"] = {
            w: con.execute(
                "SELECT COUNT(*) FROM outreach_events WHERE ext_key LIKE ?",
                (f"de-{w}-%",)).fetchone()[0]
            for w in ("E1", "E2", "E3", "reply")}
        # Contact email + key columns (defensive: schema may drift)
        ccols = [r[1] for r in con.execute("PRAGMA table_info(contacts)")]
        email_col = "email" if "email" in ccols else None
        pk_col = next((c for c in ("contact_id", "id") if c in ccols), None)
        out["contact_email_column"] = email_col
        out["contact_pk_column"] = pk_col
        if email_col and pk_col:
            db_emails = {(r[0] or "").lower() for r in con.execute(
                f"SELECT {email_col} FROM contacts") if r[0]}
            sent_emails = {(r[0] or "").lower() for r in con.execute(
                f"SELECT c.{email_col} FROM outreach_events e "
                f"JOIN contacts c ON c.{pk_col} = e.contact_id "
                f"WHERE e.type = 'sent'") if r[0]}
            out["cohort_presence"] = {
                name: {
                    "members": len(members),
                    "as_contacts": sum(1 for e in members if e in db_emails),
                    "with_sent_event": sum(
                        1 for e in members if e in sent_emails),
                }
                for name, members in cohort_emails.items()}
    except sqlite3.Error as e:
        out["error"] = str(e)
    finally:
        con.close()
    return out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:  # noqa: C901  (one linear ledger assembly, kept in order)
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--since", default="2026-05-01",
                    help="corpus window start YYYY-MM-DD (default 2026-05-01)")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--mailbox", default="both",
                    choices=["both", *MAILBOXES],
                    help="which mailbox(es) to sweep (default both)")
    ap.add_argument("--resume", action="store_true",
                    help="refetch ONLY previously-failed folders; reuse the "
                         "rest of the cache")
    ap.add_argument("--skip-corpus", action="store_true",
                    help="skip the corpus pull; use the existing cache as-is")
    ap.add_argument("--ledger-only", action="store_true",
                    help="build the ledger from the existing cache only "
                         "(implies --skip-corpus)")
    ap.add_argument("--main-repo", default=None,
                    help="primary clone root holding the gitignored context/ "
                         "+ .scratch inputs (default: this repo root)")
    ap.add_argument("--leaddesk-db", default=None,
                    help="pre-fetched lead-desk.sqlite (skips the flyctl "
                         "sftp get)")
    ap.add_argument("--skip-leaddesk", action="store_true",
                    help="skip the Lead Desk DB section entirely")
    ap.add_argument("--verify-live-capture", action="store_true",
                    help="capture-adequacy verify mode: diff the cached "
                         "corpus window against the Lead Desk DB, no Graph")
    ap.add_argument("--window", default=None,
                    help="verify window START..END (YYYY-MM-DD..YYYY-MM-DD)")
    ap.add_argument("--db", default=None,
                    help="verify mode: local copy of lead-desk.sqlite to "
                         "diff against (direct read)")
    ap.add_argument("--base-url", default=None,
                    help="verify mode: Lead Desk origin; diff via GET "
                         "/api/events pages instead of --db")
    ap.add_argument("--secret", default=None,
                    help="verify mode: ingest bearer for --base-url "
                         "(default: LEAD_DESK_INGEST_SECRET)")
    ap.add_argument("--write-run", action="store_true",
                    help="verify mode + --db only: append a truth_runs row "
                         "(kind='capture-verify') to the local copy")
    args = ap.parse_args()

    if args.verify_live_capture:
        return run_verify_live_capture(args)

    main_repo = Path(args.main_repo) if args.main_repo else truth.repo_root()
    ctx = main_repo / "workspace" / "clients" / "brisken" / "context"
    if not ctx.is_dir():
        sys.exit(f"ERROR: context dir not found at {ctx}; pass --main-repo "
                 "pointing at the primary clone")
    os.environ.setdefault("BRISKEN_ENV_FILE", str(ctx / ".env"))

    out_dir = Path(args.out)
    cache_root = out_dir / "corpus-cache"
    out_dir.mkdir(parents=True, exist_ok=True)

    mailboxes = list(MAILBOXES) if args.mailbox == "both" else [args.mailbox]
    tb = TokenBox(truth.load_env())

    if not (args.skip_corpus or args.ledger_only):
        run_corpus(mailboxes, tb, args.since, cache_root, args.resume)
    elif args.resume:
        run_corpus(mailboxes, tb, args.since, cache_root, resume=True)

    corpus = load_corpus(cache_root)
    idx = build_indexes(corpus)
    print(f"\ncorpus: {len(corpus['outbound'])} outbound, "
          f"{len(corpus['inbound'])} inbound, {len(corpus['drafts'])} drafts "
          f"across {corpus['folders_ok']} folders "
          f"({len(corpus['folders_failed'])} failed)")

    # ---- inputs --------------------------------------------------------
    paths, inputs_meta = resolve_inputs(main_repo, ctx)
    inputs_meta["wave_subjects_crosscheck"] = crosscheck_wave_subjects(
        main_repo)
    missing = [k for k, m in inputs_meta.items()
               if isinstance(m, dict) and m.get("exists") is False]

    ledger: dict = {
        "tool": "brisken-truth-sweep v1",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "since": args.since,
        "mailboxes": mailboxes,
        "judgment_policy": {
            "H5": "mailbox-silence-only; never downgraded off-mailbox"},
        "corpus": {
            "outbound": len(corpus["outbound"]),
            "inbound": len(corpus["inbound"]),
            "drafts": len(corpus["drafts"]),
            "folders_ok": corpus["folders_ok"],
            "folders_failed_count": len(corpus["folders_failed"]),
            "by_mailbox": corpus["by_mailbox"],
        },
        "folders_failed": corpus["folders_failed"],
        "malformed_recipient_addresses": idx["malformed_addresses"],
        "inputs": inputs_meta,
        "cohorts": {},
        "confirm_zero": {},
        "contradictions": [],
    }
    if paths["suppression"]:
        ledger["inputs"]["suppression"].update(
            load_suppression(paths["suppression"]))

    coh = ledger["cohorts"]
    cohort_emails_for_db: dict[str, list[str]] = {}

    # ---- E1 / E2 / E3 --------------------------------------------------
    e_claims = {
        "E1": {"comms_log_claim": 252, "send_list": 246,
               "log_sent_status_rows": 250, "log_unique_addrs": 254},
        "E2": {"log_sent_status_rows": 88},
        "E3": {"log_sent_status_rows": 86, "send_list": 126},
    }
    for wave in ("E1", "E2", "E3"):
        log_key = f"{wave.lower()}_send_log"
        log = load_send_log(paths[log_key]) if paths[log_key] else None
        list_key = f"{wave.lower()}_send_list"
        roster = None
        if list_key in paths and paths.get(list_key):
            roster = sorted({(r.get("email") or "").strip().lower()
                             for r in load_csv(paths[list_key])} - {""})
        rows = wave_sends(corpus, WAVE_SUBJECTS[wave])
        by_rcpt = recipients_of(rows)
        corpus_set = set(by_rcpt)
        log_sent = set(log["sent_emails"]) if log else set()
        mbx_counts: dict[str, int] = {}
        for m in rows:
            mbx_counts[m["mailbox"]] = mbx_counts.get(m["mailbox"], 0) + 1
        entry = {
            "subject": WAVE_SUBJECTS[wave],
            "expected": e_claims[wave],
            "send_log": ({k: log[k] for k in
                          ("rows", "unique_emails", "status_counts",
                           "unparseable_rows")}
                         if log else None),
            "send_messages_by_mailbox": mbx_counts,
            "corpus_distinct_recipients": len(corpus_set),
            "corpus_send_messages": len(rows),
            # corpus recipients are EXTERNAL by construction; internal
            # brisken addresses on the log/roster are split out so the
            # mismatch lists hold real external deltas only
            "log_sent_internal_excluded": sorted(
                e for e in log_sent if is_internal(e)),
            "log_sent_not_in_corpus": sorted(
                e for e in log_sent - corpus_set if not is_internal(e)),
            "corpus_not_in_log_sent": sorted(corpus_set - log_sent),
            "members": {e: {"sent": True, "evidence": ev,
                            "replied": bool(idx["replies"].get(e)),
                            "ooo": bool(idx["ooo"].get(e))}
                        for e, ev in sorted(by_rcpt.items())},
        }
        if roster is not None:
            entry["roster_size"] = len(roster)
            entry["roster_internal_excluded"] = sorted(
                e for e in roster if is_internal(e))
            entry["roster_not_sent"] = sorted(
                e for e in set(roster) - corpus_set if not is_internal(e))
            entry["sent_not_on_roster"] = sorted(corpus_set - set(roster))
            if wave == "E3":
                entry["note"] = ("roster_not_sent is EXPECTED for E3: the "
                                 "126-list was cut to the 86 actually sent; "
                                 "the ~40 never got E3 by design")
        coh[wave] = entry
        cohort_emails_for_db[wave] = sorted(corpus_set)

    # ---- Dirk exclusions ----------------------------------------------
    if paths["dirk_exclusions"]:
        excl = [line.strip().lower() for line in
                paths["dirk_exclusions"].read_text(encoding="utf-8")
                .splitlines() if line.strip()]
        touched = {e: idx["sends"][e] for e in excl if e in idx["sends"]}
        coh["dirk_exclusions"] = {
            "size": len(excl),
            "policy": "deliberately held from bulk sends",
            "with_any_outbound_in_window": {
                e: ev for e, ev in sorted(touched.items())},
            "note": "outbound to an excluded address is not automatically a "
                    "violation (1:1 warm mail is allowed); listed as facts",
        }

    # ---- T1 booth network ---------------------------------------------
    t1_names = load_t1_roster(paths["t1_roster"]) if paths["t1_roster"] else []
    t1_rows = wave_sends(corpus, T1_SUBJECT,
                         from_mbx="dirk.neumann@brisken.com")
    t1_by = recipients_of(t1_rows)
    t1_decoys = [
        {"mailbox": m["mailbox"], "folder": m["folder"],
         "to": m["to"], "subject": m["subject"][:90], "kind": m["kind"]}
        for m in corpus["drafts"] + corpus["inbound"]
        if norm_subject(m["subject"]) == T1_SUBJECT
        and m["mailbox"] == "matthias.silva@brisken.com"]
    coh["T1_booth_network"] = {
        "subject": T1_SUBJECT,
        "expected": {"sent": 19},
        "roster_names": t1_names,
        "roster_size": len(t1_names),
        "corpus_distinct_recipients": len(t1_by),
        "members": {e: {"sent": True, "evidence": ev,
                        "replied": bool(idx["replies"].get(e)),
                        "ooo": bool(idx["ooo"].get(e))}
                    for e, ev in sorted(t1_by.items())},
        "decoy_copies_matthias_mailbox": {
            "count": len(t1_decoys),
            "note": "unsent copies in Matthias's mailbox (Deleted Items); "
                    "EXCLUDED from send counts, which only accept messages "
                    "sent from Dirk's own mailbox",
            "rows": t1_decoys,
        },
    }
    cohort_emails_for_db["T1"] = sorted(t1_by)

    # ---- T2 warm-engaged ----------------------------------------------
    lo, hi = T2_WINDOW
    t2_rows = [m for m in corpus["outbound"]
               if m["mailbox"] == "dirk.neumann@brisken.com"
               and m["sent"] and lo <= m["sent"] <= hi]
    t2_prospect: dict[str, list] = {}
    t2_misrouted, t2_other_internal, t2_noise = [], [], []
    for m in t2_rows:
        ev = {"imid": m["imid"], "ts": m["sent"], "folder": m["folder"],
              "mailbox": m["mailbox"], "subject": m["subject"][:90]}
        to = {clean_addr(a) for a in m["to"] if a}
        ext = sorted(a for a in to
                     if not is_internal(a) and not NOREPLY_RE.match(a))
        if not ext:
            if any(NOREPLY_RE.match(a) for a in to):
                t2_noise.append({**ev, "to": sorted(to)})
            elif norm_subject(m["subject"]) in T2_MISROUTED_SUBJECTS:
                t2_misrouted.append({**ev, "to": sorted(to)})
            else:
                t2_other_internal.append({**ev, "to": sorted(to)})
        for a in ext:
            t2_prospect.setdefault(a, []).append(ev)
    coh["T2_warm_engaged"] = {
        "window_utc": T2_WINDOW,
        "expected": T2_EXPECTED,
        "source": "comms-log 2026-07-12 STATE entry (roster names) + corpus "
                  "(Dirk outbound in the window) as the address authority",
        "corpus_send_messages": len(t2_rows),
        "corpus_distinct_prospects": len(t2_prospect),
        "misrouted_to_internal": t2_misrouted,
        "misrouted_expected_subjects": sorted(T2_MISROUTED_SUBJECTS),
        "other_internal_mail_in_window": t2_other_internal,
        "notification_noise_in_window": t2_noise,
        "members": {e: {"sent": True, "evidence": ev,
                        "replied": bool(idx["replies"].get(e)),
                        "ooo": bool(idx["ooo"].get(e))}
                    for e, ev in sorted(t2_prospect.items())},
    }
    cohort_emails_for_db["T2"] = sorted(t2_prospect)

    # ---- H5 hottest leads (facts only, never judged) -------------------
    h5 = load_h5_roster(paths["h5_roster"]) if paths["h5_roster"] else []
    coh["H5_hottest_leads"] = {
        "expected": {"addresses": 11, "bespoke_notes": 6},
        "roster": h5,
        "roster_size": len(h5),
        "judgment_policy": ledger["judgment_policy"]["H5"],
        "members": {e: member_facts(e, idx, judge=False) for e in h5},
    }
    cohort_emails_for_db["H5"] = h5

    # ---- T3 -------------------------------------------------------------
    t3 = load_t3_roster(paths["t3_roster"]) if paths["t3_roster"] else []
    t3_members = {e: member_facts(e, idx) for e in t3}
    t3_sent = sum(1 for m in t3_members.values() if m["sent"])
    t3_replied = sum(1 for m in t3_members.values() if m.get("replied"))
    t3_ooo = sum(1 for m in t3_members.values() if m.get("ooo_only"))
    snap = None
    if paths["t3_snapshot"]:
        s = json.loads(paths["t3_snapshot"].read_text(encoding="utf-8"))
        rs = s.get("results", [])
        snap = {"since": s.get("since"),
                "contacted": sum(1 for r in rs if r.get("contacted")),
                "replied": sum(1 for r in rs if r.get("replied")),
                "ooo_only": sum(1 for r in rs if r.get("ooo_only"))}
    coh["T3"] = {
        "expected": {"sent": 24, "sent_date": "2026-07-21"},
        "roster_size": len(t3),
        "corpus": {"sent": t3_sent, "replied": t3_replied,
                   "ooo_only": t3_ooo},
        "verified_snapshot": snap,
        "snapshot_match": (snap is not None and t3_sent == snap["contacted"]
                           and t3_replied == snap["replied"]),
        "members": t3_members,
    }
    cohort_emails_for_db["T3"] = t3

    # ---- GA -------------------------------------------------------------
    ga = load_ga_script(paths["ga_send_script"]) if paths["ga_send_script"] \
        else {"expected": [], "held4": [], "subjects": []}
    ga_members = {e: member_facts(e, idx) for e in ga["expected"]}
    ga_sent = sum(1 for m in ga_members.values() if m["sent"])
    ga_subjects_norm = {norm_subject(s) for s in ga["subjects"]}
    ga_subject_rows = [m for m in corpus["outbound"]
                       if norm_subject(m["subject"]) in ga_subjects_norm]
    ga_subject_rcpts = recipients_of(ga_subject_rows)
    stray = sorted(set(ga_subject_rcpts) - set(ga["expected"])
                   - set(cohort_emails_for_db.get("T1", []))
                   - set(cohort_emails_for_db.get("T3", [])))
    held_check = {e: {"ga_subject_send": e in ga_subject_rcpts,
                      "any_outbound": bool(idx["sends"].get(e))}
                  for e in ga["held4"]}
    sap_hits = sorted(a for a in ga_subject_rcpts
                      if base_domain(a) == "sap.com")
    coh["GA"] = {
        "expected": {"sent": GA_EXPECTED_COUNT, "sent_date": GA_DATE,
                     "cohort_size": 40, "sap_held": 15, "held4": ga["held4"],
                     "dropped": ["milena.zang@nagarro.com (wrong contact)",
                                 "April Eaton, J.P. Morgan (mis-target; no "
                                 "address in rome-ga-wave.md)"]},
        "subjects": ga["subjects"],
        "corpus": {"sent": ga_sent,
                   "ga_subject_distinct_recipients": len(ga_subject_rcpts)},
        "held4_check": held_check,
        "sap_addresses_hit_by_ga_subjects": sap_hits,
        "ga_subject_recipients_outside_known_cohorts": stray,
        "alias_note": {
            "sent_to": "stiaan.scheepers@globalpayments.com",
            "sheet_primary": "ss50866@globalpayments.com",
            "evidence": idx["sends"].get(
                "stiaan.scheepers@globalpayments.com", []),
        },
        "members": ga_members,
    }
    cohort_emails_for_db["GA"] = ga["expected"]

    # ---- confirm-zero cohorts ------------------------------------------
    cz = ledger["confirm_zero"]
    nestle = []
    if paths["nestle_contacts"]:
        nestle = sorted({(r.get("email") or "").strip().lower()
                         for r in load_csv(paths["nestle_contacts"])} - {""})
    nestle_hits = {e: idx["sends"][e] for e in nestle if e in idx["sends"]}
    # The confirm-zero claim is about CAMPAIGN outreach. The roster is built
    # from the won-account ecosystem, so organic project/thread mail to these
    # addresses is expected and does not violate the claim; a campaign-subject
    # send does.
    campaign_subjects = ({norm_subject(s) for s in WAVE_SUBJECTS.values()}
                         | {T1_SUBJECT} | T3_SUBJECTS
                         | {norm_subject(s) for s in ga["subjects"]})
    nestle_campaign = {
        e: [h for h in ev if norm_subject(h["subject"]) in campaign_subjects]
        for e, ev in nestle_hits.items()}
    nestle_campaign = {e: h for e, h in nestle_campaign.items() if h}
    cz["nestle_214"] = {
        "method": "corpus scan of every roster address for outbound hits, "
                  "split campaign-subject vs organic thread mail",
        "corpus_binding": f"{len(nestle)} addresses scanned against the "
                          "outbound index",
        "roster_size": len(nestle),
        "campaign_subject_sends": nestle_campaign,
        "organic_outbound_hits": {
            e: ev for e, ev in nestle_hits.items()
            if e not in nestle_campaign},
        "confirmed_zero_campaign_sends": not nestle_campaign,
        "residual_risk": "none for the mailbox channel; off-mailbox contact "
                         "is not observable here",
    }
    cz["getken_834"] = {
        "method": "external agency sends are unknowable from local systems; "
                  "bounded by the suppression list delivered 2026-07-26",
        "corpus_binding": "none possible (sends would originate outside the "
                          "two allowlisted mailboxes)",
        "confirmed_zero": None,
        "residual_risk": "OPEN: whether getken honored the suppression list "
                         "cannot be verified locally; owner attestation or "
                         "a getken-side export needed",
    }
    sn_emails = []
    cz["linkedin_salesnav"] = {
        "method": "sheet salesnav_status rows bound to the outbound index; "
                  "LinkedIn-native touches are out of scope for a mailbox "
                  "sweep",
        "corpus_binding": "emails of sheet rows with non-blank "
                          "salesnav_status scanned for outbound hits "
                          "(filled after sheet pull)",
        "residual_risk": "LinkedIn-native activity (InMail, connect notes) "
                         "is invisible to Graph; ~65-member list history "
                         "needs owner attestation",
    }
    cz["booth_consent_74"] = {
        "method": "campaign was never executed; no send script, subject, or "
                  "roster artifact exists to bind against",
        "corpus_binding": "none available",
        "confirmed_zero": None,
        "residual_risk": "no local artifact can prove the negative; owner "
                         "attestation that it never ran",
    }
    cz["cold_farm_53"] = {
        "method": "the 53-domain farm has no MX / no mailboxes provisioned "
                  "(project_brisken_outreach_domains: 0/53 email-ready)",
        "corpus_binding": "corpus contains only the two allowlisted "
                          "mailboxes by construction; no farm sender exists",
        "confirmed_zero": True,
        "residual_risk": "none",
    }
    cz["instantly"] = {
        "method": "no Instantly workspace used in this engagement",
        "corpus_binding": "not bindable (Instantly sends would not transit "
                          "the tenant mailboxes)",
        "confirmed_zero": None,
        "residual_risk": "KNOWN HOLE: no historical opt-out export from any "
                         "prior Instantly use exists; suppression list may "
                         "under-cover historical opt-outs",
    }

    # ---- sheet snapshot -------------------------------------------------
    sheet_ok = False
    try:
        sheet = pull_sheet(tb.get())
        sheet_ok = True
        # keep per_email out of the printed summary but in the ledger
        ledger["sheet"] = sheet
        sn_emails = sorted(
            e for e, r in sheet["per_email"].items()
            if (r.get("salesnav_status") or "").strip().lower()
            == "in sales nav list")
        sn_hits = {e: idx["sends"][e] for e in sn_emails
                   if e in idx["sends"]}
        # A SalesNav member also sitting in an email cohort legitimately has
        # email touches; the claim under test is that no SEPARATE salesnav
        # email campaign exists, i.e. every email hit traces to a known
        # cohort subject or an organic thread.
        sn_uncohorted = {
            e: [h for h in ev
                if norm_subject(h["subject"]) not in campaign_subjects]
            for e, ev in sn_hits.items()}
        sn_uncohorted = {e: h for e, h in sn_uncohorted.items() if h}
        cz["linkedin_salesnav"].update({
            "sheet_members_in_salesnav_list": len(sn_emails),
            "members_with_any_email_touch": len(sn_hits),
            "email_touches": {e: ev for e, ev in sorted(sn_hits.items())},
            "email_touches_outside_known_campaign_subjects": sn_uncohorted,
            "finding": "no bulk salesnav email campaign subject exists in "
                       "the corpus; the touches outside the campaign-subject "
                       "set are bespoke 1:1 notes (T2/H5 subjects), reply "
                       "threads, or organic customer mail. Judged over the "
                       "evidence above, not mechanically provable",
            "salesnav_status_counts": sheet["salesnav_status_counts"],
        })
    except Exception as e:
        ledger["sheet"] = {"error": f"{type(e).__name__}: {e}"}
        print(f"WARN: sheet snapshot failed: {e}", file=sys.stderr)

    # ---- Lead Desk ------------------------------------------------------
    leaddesk_ok = False
    if args.skip_leaddesk:
        ledger["lead_desk"] = {"skipped": True}
    else:
        db_path = Path(args.leaddesk_db) if args.leaddesk_db else None
        err = None
        if db_path is None:
            db_path, err = fetch_leaddesk_db(
                out_dir / "tmp" / "lead-desk.sqlite")
        if db_path:
            ledger["lead_desk"] = read_leaddesk(db_path, cohort_emails_for_db)
            leaddesk_ok = "error" not in ledger["lead_desk"]
            ledger["lead_desk"]["note"] = (
                "what the DB currently claims vs the corpus truth above; "
                "the per-cohort gap IS the backfill workload. Hierarchy: "
                "mailbox > DB (codified 2026-08; the DB is a partial "
                "projection, not the source of truth)")
        else:
            ledger["lead_desk"] = {"error": err}
            print(f"WARN: lead-desk DB unavailable: {err}", file=sys.stderr)

    # ---- Zoho existence-only -------------------------------------------
    zoho_ok = False
    if paths["zoho_cache"]:
        z = json.loads(paths["zoho_cache"].read_text(encoding="utf-8"))
        z_emails = {(c.get("email") or "").lower()
                    for c in z.get("contacts", [])} - {""}
        cache_mtime = dt.datetime.fromtimestamp(
            paths["zoho_cache"].stat().st_mtime,
            dt.timezone.utc).isoformat()
        ledger["zoho"] = {
            "cache_contacts": len(z.get("contacts", [])),
            "cache_mtime_utc": cache_mtime,
            "staleness_note": "existence checked against a LOCAL cache; a "
                              "cohort's absence (e.g. T3/GA) proves nothing "
                              "about dropbox-BCC filing if the cache predates "
                              "the wave. Compare cache_mtime_utc with each "
                              "cohort's send date before reading absence as "
                              "a filing failure",
            "cohort_presence": {
                name: {"members": len(members),
                       "in_zoho_contacts": sorted(
                           e for e in members if e in z_emails)}
                for name, members in cohort_emails_for_db.items()},
            "residual": "existence-only from the local cache; Zoho Leads "
                        "module returns 401 with the current read-only "
                        "grant, so lead-module presence is unknowable",
        }
        zoho_ok = True

    # ---- contradictions -------------------------------------------------
    e1 = coh.get("E1", {})
    t2c = coh.get("T2_warm_engaged", {})
    anon_live = ledger.get("sheet", {}).get("anon_count")
    ledger["contradictions"] = [
        {"id": "e1-count",
         "claims": {"comms-log": 252, "send-list": 246,
                    "log sent-status rows": 250, "log unique addrs": 254},
         "resolution": "corpus is the arbiter: "
                       f"{e1.get('corpus_distinct_recipients')} distinct "
                       "in-window recipients of the E1 subject",
         "evidence": f"log_sent_not_in_corpus="
                     f"{e1.get('log_sent_not_in_corpus')}, "
                     f"corpus_not_in_log_sent="
                     f"{e1.get('corpus_not_in_log_sent')}"},
        {"id": "ga-doc-vs-sent",
         "claims": {"rome-ga-wave.md": "Sequence B, consultancies only "
                                       "(10 send-ready) greenlit",
                    "actually sent": f"{coh['GA']['corpus']['sent']} of the "
                                     "19-address allowlist on 2026-07-27, "
                                     "using the Sequence A/booth subject "
                                     "set, incl. payment firms + corporates"},
         "status": "rome-ga-wave.md is STALE",
         "owner_action": "update rome-ga-wave.md to record the 19 actually "
                         "sent (Sequence A/7) and the standing holds "
                         "(SAP-15 + held-4)",
         "evidence": f"ga members sent={coh['GA']['corpus']['sent']}/19; "
                     f"held4_check={coh['GA']['held4_check']}"},
        {"id": "salesnav-count",
         "claims": {"salesnav list memory": 34, "cohort claim": 40,
                    "task briefing": "~65"},
         "resolution": "live sheet salesnav_status counts: "
                       f"{ledger.get('sheet', {}).get('salesnav_status_counts')}",
         "owner_action": "owner attestation needed for the list's history "
                         "(members added/removed before the sheet snapshot)"},
        {"id": "anon-count",
         "claims": {"prior reads": "89 / 90 / 91"},
         "resolution": f"live sheet Tier==ANON count = {anon_live}",
         "evidence": f"tier_counts="
                     f"{ledger.get('sheet', {}).get('tier_counts')}"},
        {"id": "lead-desk-truth-hierarchy",
         "claims": {"lead-desk positioning": "single source of truth",
                    "observed": "partial projection (E-wave grounding only; "
                                "post-event waves largely absent)"},
         "resolution": "hierarchy codified: mailbox > DB. This ledger IS "
                       "the mailbox truth; the per-cohort gap in "
                       "lead_desk.cohort_presence is the backfill workload"},
        {"id": "reconcile-tool-pull-corpus",
         "claims": {"tools/brisken-outreach-reconcile.py": "called "
                    "truth.pull_corpus(), which no longer exists"},
         "resolution": "fixed in this PR: build_indexes now composes "
                       "truth.pull_outbound + pull_inbound + pull_drafts "
                       "with id-level dedup"},
        {"id": "zoho-bcc-filing",
         "claims": {"house convention": "Zoho dropbox BCC files each send "
                                        "into CRM",
                    "verified": "never verified end-to-end"},
         "owner_action": "drill step 6: send one watched test mail with the "
                         "dropbox BCC and confirm it lands in Zoho"},
        {"id": "t2-zoho-filing",
         "claims": {"T2 sends 2026-07-12": "whether Dirk added the dropbox "
                    "BCC is not visible from Matthias's BCC copy"},
         "owner_action": "ask Dirk / check Zoho for the "
                         f"{t2c.get('corpus_distinct_prospects')} T2 "
                         "prospects",
         "evidence": f"zoho cohort_presence T2="
                     f"{ledger.get('zoho', {}).get('cohort_presence', {}).get('T2')}"},
        {"id": "t2-window-timezone",
         "claims": {"comms-log 2026-07-12 STATE": "Dirk sent the batch "
                    "'between 14:11 and 16:26 UTC'",
                    "mailbox truth": "the batch runs 12:11-14:26Z; the two "
                    "misroutes land 13:31Z/13:56Z; the ICD wave (logged as "
                    "17:32-17:37) runs 15:32-15:37Z"},
         "resolution": "the comms-log clock times were CEST (UTC+2) "
                       "mislabeled as UTC; this ledger uses the corrected "
                       f"window {T2_WINDOW}",
         "evidence": "compare comms-log entry timestamps with the "
                     "sentDateTime values in T2_warm_engaged.members"},
        {"id": "sheet-column-letters",
         "claims": {"older tooling": "addressed sheet columns by letter; "
                    "letters shift when Dirk inserts columns"},
         "resolution": "header-name resolution policy codified in this "
                       "tool (columns_resolved map in the sheet section)"},
    ]

    # ---- completeness ---------------------------------------------------
    reasons = []
    if corpus["folders_failed"]:
        reasons.append(f"{len(corpus['folders_failed'])} folders failed "
                       "after retries (enumerated in folders_failed)")
    if missing:
        reasons.append(f"missing inputs: {missing}")
    if not sheet_ok:
        reasons.append("sheet snapshot failed")
    if not args.skip_leaddesk and not leaddesk_ok:
        reasons.append("lead-desk DB not read")
    if not zoho_ok:
        reasons.append("zoho cache not read")
    ledger["complete"] = not reasons
    ledger["incomplete_reasons"] = reasons

    ledger_path = out_dir / "outreach-truth-ledger.json"
    ledger_path.write_text(
        json.dumps(ledger, indent=2, ensure_ascii=False), encoding="utf-8")

    # ---- summary --------------------------------------------------------
    print(f"\nLEDGER: {ledger_path}")
    print(f"complete: {ledger['complete']}"
          + (f"  ({'; '.join(reasons)})" if reasons else ""))
    for name in ("E1", "E2", "E3"):
        c = coh[name]
        print(f"  {name}: corpus={c['corpus_distinct_recipients']} "
              f"expected={c['expected']}")
    print(f"  T1: corpus={coh['T1_booth_network']['corpus_distinct_recipients']}"
          f"/19  decoys_excluded="
          f"{coh['T1_booth_network']['decoy_copies_matthias_mailbox']['count']}")
    print(f"  T2: prospects={t2c['corpus_distinct_prospects']}/14 "
          f"misrouted={len(t2c['misrouted_to_internal'])}/2")
    print(f"  H5: sends recorded for "
          f"{sum(1 for m in coh['H5_hottest_leads']['members'].values() if m['sent'])}"
          f"/{len(h5)} (facts only, never judged)")
    print(f"  T3: sent={t3_sent}/24 replied={t3_replied} ooo={t3_ooo} "
          f"snapshot_match={coh['T3']['snapshot_match']}")
    print(f"  GA: sent={ga_sent}/19 sap_hits="
          f"{len(coh['GA']['sap_addresses_hit_by_ga_subjects'])}")
    if sheet_ok:
        print(f"  sheet: {ledger['sheet']['rows']} rows, "
              f"ANON={ledger['sheet']['anon_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
