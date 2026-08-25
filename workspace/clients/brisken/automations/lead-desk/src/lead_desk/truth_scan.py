"""Scheduled deep truth reconcile: read-only ALL-FOLDERS outbound scan.

Live capture (the cloud-worker tick) polls only sentitems/inbox/calendar
every ~15 minutes, and Dirk files sent mail into per-company folders - so a
send capture missed was invisible forever (the 2026-07-21 class: 21/24 real
sends false-negatived). This module walks EVERY mail folder of both
allowlisted mailboxes, diffs each folder's item count against the
folder_cache table (v11) so unchanged folders cost nothing, pulls the
owner-sent corpus for changed folders, and feeds anything the DB does not
know through the one sanctioned ingress (``service.ingest_event``): known
messages dedupe via event_hash, unknown addresses park in the unmatched
queue, no contact is ever auto-created.

Read-only against Graph: GETs only, no sends, no drafts, nothing in the
mailbox changes. Every ``FULL_SCAN_EVERY``-th run ignores the count diff
(a fixed early window bound) so a diff blind spot cannot hide forever; the
run counter persists in the state KV (``truth_scan_run_count``).

Ops surface: one truth_runs row per run, plus the state keys
``truth_scan_heartbeat`` (ts + counts) and ``truth_scan_alert`` - set when
folders failed or missed events were recovered (both mean live capture has
a blind spot worth a look), cleared on a clean run.

    lead-desk-truth-scan [--window-days 14] [--full] [--dry-run]

Scheduled by the web app (LEAD_DESK_TRUTH_SCAN_INTERVAL, default daily),
guarded like the sheet-sync scheduler: disabled flag, no creds -> logged
skip, never a crash.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from .cloud_worker import filter_payloads
from .graph_mail import ALLOWED_MAILBOXES, GraphMailer, GraphRetryError
from .sync import have_creds
from .web.service import ingest_event, now_iso
from .web.store import ContactStore

FULL_SCAN_EVERY = 7
# Fixed early bound for a full scan: before the first Rome outreach wave,
# so a full pass covers the entire campaign-era corpus.
FULL_SCAN_SINCE = "2026-05-01T00:00:00Z"
RETRY_BACKOFF = (5, 15, 45)

HEARTBEAT_KEY = "truth_scan_heartbeat"
ALERT_KEY = "truth_scan_alert"
RUN_COUNT_KEY = "truth_scan_run_count"


def _z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0) \
        .isoformat().replace("+00:00", "Z")


def outbound_to_payloads(msg: dict) -> list[dict]:
    """One pulled outbound message -> one 'sent' event per to/cc recipient,
    in EXACTLY the shape capture.sent_to_payloads emits (same type/channel/
    detail/occurred_at, so the event_hash basis lines up and a message the
    live sweep already ingested dedupes instead of double-logging). The
    input is pull_folder_outbound's normalized shape, so the mapper is
    mirrored here rather than imported."""
    out = []
    for addr in (msg.get("to") or []) + (msg.get("cc") or []):
        out.append({
            "email": addr, "type": "sent", "direction": "outbound",
            "channel": "email", "occurred_at": msg.get("sent_at"),
            "subject": msg.get("subject"),
            "detail": "auto: sent mail", "source": "graph-auto",
            "internet_message_id": msg.get("internet_message_id"),
        })
    return out


def _pull_with_retry(mailer, mailbox: str, folder_id: str, since_iso: str,
                     sleep) -> tuple[list[dict] | None, str | None]:
    """Pull one folder, retrying GraphRetryError x3 with 5/15/45s backoff.
    Returns (messages, None) or (None, error): a folder that stays broken
    is reported, never raised - one bad folder must not kill the run."""
    last = ""
    for delay in (0, *RETRY_BACKOFF):
        if delay:
            sleep(delay)
        try:
            return mailer.pull_folder_outbound(
                mailbox, folder_id, since_iso), None
        except GraphRetryError as exc:
            last = str(exc)[:200]
        except Exception as exc:  # noqa: BLE001 - non-retryable read error
            return None, str(exc)[:200]
    return None, last


def run_scan(store: ContactStore, mailer, *, window_days: int = 14,
             full: bool = False, now: datetime | None = None,
             sleep=time.sleep, dry_run: bool = False) -> dict:
    """One deep scan over both allowlisted mailboxes. Returns the report
    dict; unless ``dry_run``, also writes the truth_runs row, the folder
    cache, and the heartbeat/alert state keys."""
    now = now or datetime.now(timezone.utc)
    run_count = None
    if not dry_run:
        run_count = int(store.get_state(RUN_COUNT_KEY) or "0") + 1
        store.set_state(RUN_COUNT_KEY, str(run_count), now_iso())
        if run_count % FULL_SCAN_EVERY == 0:
            full = True
    since_iso = FULL_SCAN_SINCE if full \
        else _z(now - timedelta(days=window_days))

    started = now_iso()
    folders_scanned = 0
    folders_failed: list[dict] = []
    corpus = 0
    counts = {"inserted": 0, "deduped": 0, "queued": 0, "would_ingest": 0}

    for mbx in ALLOWED_MAILBOXES:
        try:
            folders = mailer.list_mail_folders(mbx)
        except Exception as exc:  # noqa: BLE001 - one mailbox down != run dead
            folders_failed.append({"mailbox": mbx, "path": "*",
                                   "error": str(exc)[:200]})
            continue
        cache = store.get_folder_cache(mbx)
        for f in folders:
            cached = cache.get(f["id"])
            if cached is not None and cached["skip"]:
                continue                       # operator-parked, always
            if not full and cached is not None \
                    and cached["total_item_count"] == f["total_item_count"]:
                continue                       # unchanged count: nothing new
            msgs, err = _pull_with_retry(mailer, mbx, f["id"], since_iso,
                                         sleep)
            if err is not None:
                folders_failed.append({"mailbox": mbx, "path": f["path"],
                                       "error": err})
                continue
            folders_scanned += 1
            corpus += len(msgs)
            # filter_payloads drops own-domain recipients and worker sends
            # whose readback missed the imid (same pre-ingest guard the
            # live capture pass runs).
            payloads = filter_payloads(
                store, [p for m in msgs for p in outbound_to_payloads(m)])
            if dry_run:
                counts["would_ingest"] += len(payloads)
                continue
            hit = False
            for payload in payloads:
                res = ingest_event(store, payload)
                if res.get("inserted"):
                    counts["inserted"] += 1
                    hit = True
                elif res.get("queued"):
                    counts["queued"] += 1
                    hit = True
                else:
                    counts["deduped"] += 1
            store.upsert_folder_cache(mbx, f["id"], f["path"],
                                      f["total_item_count"], now_iso(),
                                      hit=hit)

    finished = now_iso()
    report = {
        "kind": "deep-scan", "full": full, "run_count": run_count,
        "dry_run": dry_run, "window_since": since_iso,
        "folders_scanned": folders_scanned, "folders_failed": folders_failed,
        "corpus_messages": corpus, **counts,
    }
    if dry_run:
        return report

    store.insert_truth_run(
        run_id=uuid4().hex, kind="deep-scan", started_at=started,
        finished_at=finished, window_since=since_iso,
        corpus_messages=corpus, folders_scanned=folders_scanned,
        folders_failed=json.dumps(folders_failed),
        events_added=counts["inserted"],
        report=json.dumps(report, default=str))
    store.set_state(HEARTBEAT_KEY, json.dumps({
        "ts": finished,
        "counts": {"folders_scanned": folders_scanned,
                   "folders_failed": len(folders_failed),
                   "inserted": counts["inserted"],
                   "deduped": counts["deduped"],
                   "queued": counts["queued"]},
    }), finished)
    if folders_failed or counts["inserted"] > 0:
        # Both halves mean live capture has a blind spot worth a look.
        store.set_state(ALERT_KEY, json.dumps({
            "ts": finished,
            "alert": f"deep scan: {counts['inserted']} event(s) live capture "
                     f"missed, {len(folders_failed)} folder(s) failed",
        }), finished)
    else:
        store.delete_state(ALERT_KEY)
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="lead-desk-truth-scan",
        description="Deep ALL-FOLDERS outbound truth scan (read-only Graph; "
                    "no sends)")
    p.add_argument("--data",
                   default=os.environ.get("LEAD_DESK_DATA", "lead-desk-data"))
    p.add_argument("--window-days", type=int, default=14,
                   help="outbound lookback for changed folders")
    p.add_argument("--full", action="store_true",
                   help="ignore the folder-cache diff (skip=1 still skips) "
                        "and scan from the fixed early bound")
    p.add_argument("--dry-run", action="store_true",
                   help="pull + diff + print would-ingest counts; no ingest, "
                        "no truth_runs row, no cache/state writes")
    args = p.parse_args(argv)

    if not have_creds():
        print("ERROR: BRISKEN_GRAPH_* credentials not configured")
        return 2
    with ContactStore(Path(args.data) / "lead-desk.sqlite") as store:
        report = run_scan(store, GraphMailer(),
                          window_days=args.window_days, full=args.full,
                          dry_run=args.dry_run)
    print(json.dumps(report, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
