"""Cloud worker: the Graph-headless replacement for the local Outlook-COM
worker (``worker/cli.py``). Runs inside the Fly app (in-app scheduler) or by
hand via ``lead-desk-cloud-worker``; no Windows session, no Outlook.

The tick is the same contract as the COM tick, in the same order (the
ordering IS the cadence-halt guarantee - capture runs before claim, so a
reply that arrived five minutes ago halts the send server-side):

    1. pre-flight (kill switch state, creds)
    2. replay unacked journal entries (crash reconcile)
    3. capture sent/replies/bounces/meetings for BOTH mailboxes -> ingest
       (in-process ingest_event; the sink dedupes + auto-suppresses bounces),
       and correlate Dirk's Sent Items with 'drafted' attempts
    4. claim due sends -> execute via Graph -> ack, throttled
    5. heartbeat

Everything server-side is called in-process (same SQLite, no HTTP hop, no
worker secret): cadence.claim_sends / resolve_result / confirm_draft_sent
carry the lease + idempotency machinery unchanged. At-most-once still rides
on the write-ahead journal: ``graph_issued`` is written IMMEDIATELY before
the irreversible sendMail POST, and every crash window reconciles from Sent
Items evidence - ambiguity always resolves toward "assume sent + tell a
human", never toward resending.

Sending stays DORMANT until armed: the global kill switch short-circuits
claim_sends, and with no campaign in status 'sending' there is nothing to
claim. Capture is read-only Graph + internal events and runs regardless -
it is the Phase-2 board-freshness unlock (mailbox truth on the board).
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import random
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import capture as graph_capture
from .graph_mail import DIRK_SMTP, SEND_FROM, DraftGuardError, GraphMailer, \
    GraphSendError, NotAllowlisted, OWN_DOMAIN
from .sync import _load_creds, have_creds
from .web import cadence
from .web.service import ingest_event, now_iso
from .web.store import ContactStore
from .worker.com_mail import match_drafted
from .worker.journal import Journal

WORKER_ID = "leaddesk-cloud-fly"
MAILBOXES = (SEND_FROM, DIRK_SMTP)
MAX_CLAIM = 25
CAPTURE_OVERLAP = timedelta(hours=2)
CAPTURE_LOOKBACK_DAYS = 3
RECONCILE_LOOKBACK_DAYS = 7


def _now_utc() -> datetime:
    return cadence.now_utc()


def cloud_worker_enabled() -> tuple[bool, str]:
    """The in-app tick loop is OPT-IN: it runs only where LEAD_DESK_CLOUD_WORKER=1
    is set (fly.toml [env] on the hosted app). Local dev and test runs never set
    it, so a TestClient app or a laptop `lead-desk-web` can never start a loop
    that talks to real Graph (the dev .env creds fallback would otherwise make
    that possible)."""
    if os.environ.get("LEAD_DESK_CLOUD_WORKER") != "1":
        return False, "LEAD_DESK_CLOUD_WORKER != 1 (opt-in; set on Fly only)"
    if not have_creds():
        return False, "BRISKEN_GRAPH_* credentials absent"
    return True, "enabled"


# -- capture ------------------------------------------------------------------

def _capture_state_path(data_dir: Path) -> Path:
    return data_dir / "cloud-capture-state.json"


def _since_for(state: dict, mailbox: str, now: datetime) -> datetime:
    raw = (state.get("watermarks") or {}).get(mailbox)
    if raw:
        try:
            return datetime.fromisoformat(raw) - CAPTURE_OVERLAP
        except ValueError:
            pass
    return now - timedelta(days=CAPTURE_LOOKBACK_DAYS)


def filter_payloads(store: ContactStore, payloads: list[dict]) -> list[dict]:
    """Drop what the sink should never see from a mailbox sweep:

    * own-team mail (@brisken.com sits in the sheet as OWN_TEAM rows, so a
      CC to Dirk or internal thread would otherwise land as lead activity);
    * 'sent' items that are worker sends whose readback missed the
      internetMessageId (the sink's imid dedupe can't catch those; match
      (to, subject) against send_attempts instead)."""
    out = []
    for p in payloads:
        email = (p.get("email") or "").lower()
        if email.endswith(OWN_DOMAIN):
            continue
        if p.get("type") == "sent":
            hit = store.conn.execute(
                "SELECT 1 FROM send_attempts WHERE lower(to_addr) = ? "
                "AND rendered_subject = ? AND status IN ('sent', 'drafted')",
                (email, p.get("subject") or "")).fetchone()
            if hit is not None:
                continue
        out.append(p)
    return out


def run_capture(store: ContactStore, data_dir: Path, poll_fn, mailer,
                *, now: datetime, dry_run: bool = False) -> dict:
    """One capture pass: poll both mailboxes, ingest in-process, and complete
    'drafted' cadence steps that Dirk actually sent."""
    state_path = _capture_state_path(data_dir)
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state = {}
    run_started = now
    payloads: list[dict] = []
    polled: dict[str, int] = {}
    for mbx in MAILBOXES:
        raw = poll_fn(mbx, _since_for(state, mbx, now), now)
        polled[mbx] = len(raw)
        payloads.extend(filter_payloads(store, raw))

    # Drafted-attempt correlation against Dirk's Sent Items BEFORE ingest, so
    # the attempt carries its imid by the time the sweep's copy of the same
    # mail hits the sink's dedupe.
    drafted = [dict(r) for r in store.conn.execute(
        "SELECT attempt_key, to_addr AS 'to', rendered_subject AS subject "
        "FROM send_attempts WHERE status = 'drafted'").fetchall()]
    confirmations: list[dict] = []
    if drafted:
        sent_items = mailer.poll_sent(
            DIRK_SMTP, now - timedelta(days=14))
        confirmations = match_drafted(sent_items, drafted)

    if dry_run:
        return {"dry_run": True, "polled": polled, "payloads": payloads,
                "draft_confirmations": confirmations}

    confirmed = 0
    for c in confirmations:
        if cadence.confirm_draft_sent(store, c).get("ok"):
            confirmed += 1
    inserted = 0
    for p in payloads:
        if ingest_event(store, p).get("inserted"):
            inserted += 1

    # Advance watermarks only after a successful pass (idempotent sink makes
    # a re-poll harmless; an un-advanced watermark just re-reads the window).
    state.setdefault("watermarks", {})
    for mbx in MAILBOXES:
        state["watermarks"][mbx] = run_started.isoformat(timespec="seconds")
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, indent=1), encoding="utf-8")
    except OSError:
        pass
    return {"polled": polled, "events_considered": len(payloads),
            "events_inserted": inserted, "draft_confirmations": confirmed}


# -- send execution -------------------------------------------------------------

def _body_as_html(text: str) -> str:
    """The claim's rendered plain-text body (what send_auto sends verbatim as
    contentType Text) carried as HTML for create_reply_draft: entities
    escaped, newlines as <br>. Same rendering, different wire encoding."""
    return html.escape(text or "").replace("\n", "<br>\n")


def _resolve_anchor(store: ContactStore, mailer, send: dict) -> dict | None:
    """The Graph message a reply step threads onto: the PRIOR step's sent
    mail, resolved via the internetMessageId on its attempt row
    (send['thread_ext_key'] is the prior step's attempt_key). Returns None -
    park, never fresh-send - when the prior attempt or its imid is missing,
    or the message cannot be resolved in the mailbox. The anchor lives in
    the mailbox the prior step was sent FROM: SEND_FROM for auto-matthias,
    DIRK_SMTP for draft-dirk."""
    prior_key = send.get("thread_ext_key")
    prior = store.get_attempt(prior_key) if prior_key else None
    if prior is None or not prior["internet_message_id"]:
        return None
    mailbox = DIRK_SMTP if send["send_mode"] == "draft-dirk" else SEND_FROM
    try:
        return mailer.find_message_by_imid(mailbox, prior["internet_message_id"])
    except Exception:  # noqa: BLE001 - a failed lookup parks; it never fresh-sends
        return None


def execute_one(store: ContactStore, mailer, send: dict, journal: Journal,
                *, draft_to_self: bool = False, now: datetime,
                alerts: list[str] | None = None) -> str:
    """Execute one claimed send. Returns the outcome string for counters.
    Mirrors worker/sender.execute_one with resolve_result called in-process.
    ``alerts`` (run_tick's list) collects the human-readable lines that land
    in the cloud_worker_alert state key at tick end."""
    akey = send["attempt_key"]
    alerts = alerts if alerts is not None else []

    # Copy tamper check (same as worker/sender.body_hash, inlined so the web
    # app's import of this module never pulls the COM worker's httpx client).
    rendered = hashlib.sha256(
        (send["subject"] + "\n" + send["body"]).encode("utf-8")).hexdigest()
    if rendered != send["body_hash"]:
        journal.write(akey, "nacked", reason="body hash mismatch")
        cadence.resolve_result(store, {
            "attempt_key": akey, "lease_id": send["lease_id"],
            "status": "failed", "error_class": "config",
            "failure_reason": "body hash mismatch (copy drift)"})
        return "hash_mismatch"

    journal.write(akey, "claimed", to=send["to"], lease_id=send["lease_id"],
                  mode=send["send_mode"])

    # In-thread reply step: resolve the anchor (the prior step's sent mail)
    # up front. Read-only, so the drill mode below exercises it for real.
    reply_to_prior = bool(send.get("reply_to_prior"))
    anchor = _resolve_anchor(store, mailer, send) if reply_to_prior else None

    if draft_to_self:
        # Test mode: full pipeline, but the mail lands as a draft in OUR
        # mailbox and nothing is acked (repeatable, human-inspectable). A
        # reply step stages a real threaded reply, recipient rewritten to
        # self; with no resolvable anchor it degrades to a plain self-draft.
        if reply_to_prior and anchor is not None:
            mailer.create_reply_draft(
                SEND_FROM, anchor["id"], to=SEND_FROM,
                html_body=_body_as_html(send["body"]),
                cc=send.get("cc"), bcc=send.get("bcc"))
        else:
            mailer.create_draft(SEND_FROM, dict(send, to=SEND_FROM))
        journal.write(akey, "nacked", reason="draft-to-self test mode")
        return "draft_to_self"

    # Hard recipient-domain backstop: even if a claim-time guard regressed, a
    # send to a hard-denied domain never reaches Graph. Uses the immutable
    # floor (cadence.DEFAULT_DENY_DOMAINS), not the state-configurable set, so a
    # bad state write cannot weaken it. draft-to-self above targets our own
    # mailbox and returns before this point.
    if cadence._recipient_domain(send["to"]) in set(cadence.DEFAULT_DENY_DOMAINS):
        journal.write(akey, "nacked", reason=f"recipient domain denied: {send['to']}")
        cadence.resolve_result(store, {
            "attempt_key": akey, "lease_id": send["lease_id"],
            "status": "failed", "error_class": "config",
            "failure_reason": f"recipient domain hard-denied: {send['to']}"[:300]})
        return "recipient_denied"

    if reply_to_prior and anchor is None:
        # A reply step with no resolvable anchor NEVER silently falls back
        # to a fresh send (that would break the thread promise). Park it for
        # a human: Retry re-runs the resolution; Send fresh (force_fresh)
        # re-queues it as a plain fresh send.
        reason = f"reply anchor not found: {akey}"
        journal.write(akey, "nacked", reason=reason)
        cadence.resolve_result(store, {
            "attempt_key": akey, "lease_id": send["lease_id"],
            "status": "failed", "error_class": "permanent",
            "failure_reason": reason[:300]})
        alerts.append(reason)
        return "reply_anchor_missing"

    if send["send_mode"] == "draft-dirk":
        try:
            if reply_to_prior:
                # Stage the threaded reply into Dirk's Drafts; his click (or
                # a wave release) sends it and the existing match_drafted
                # correlation completes the step.
                res = mailer.create_reply_draft(
                    DIRK_SMTP, anchor["id"], to=send["to"],
                    html_body=_body_as_html(send["body"]),
                    cc=send.get("cc"), bcc=send.get("bcc"))
            else:
                res = mailer.create_draft(DIRK_SMTP, send)
        except Exception as exc:  # noqa: BLE001 - draft creation is safely retryable
            journal.write(akey, "nacked", reason=str(exc)[:200])
            cadence.resolve_result(store, {
                "attempt_key": akey, "lease_id": send["lease_id"],
                "status": "failed", "error_class": "transient",
                "failure_reason": f"draft load: {exc}"[:300]})
            return "draft_failed"
        journal.write(akey, "drafted", entry_id=res.get("entry_id"))
        cadence.resolve_result(store, {
            "attempt_key": akey, "lease_id": send["lease_id"],
            "status": "drafted", "entry_id": res.get("entry_id")})
        journal.write(akey, "acked", outcome="drafted")
        return "drafted"

    if reply_to_prior:
        # auto-matthias reply: a two-phase send-by-id
        # (rule_brisken_graph_send_by_id). Staging the threaded reply draft
        # is retryable (nothing has left); the /send POST is the
        # irreversible moment, so graph_issued lands between the two.
        try:
            draft = mailer.create_reply_draft(
                SEND_FROM, anchor["id"], to=send["to"],
                html_body=_body_as_html(send["body"]),
                cc=send.get("cc"), bcc=send.get("bcc"))
        except Exception as exc:  # noqa: BLE001 - nothing sent yet: safe to retry
            journal.write(akey, "nacked", reason=str(exc)[:200])
            cadence.resolve_result(store, {
                "attempt_key": akey, "lease_id": send["lease_id"],
                "status": "failed", "error_class": "transient",
                "failure_reason": f"reply draft: {exc}"[:300]})
            return "draft_failed"
        # The wire subject is the draft's RE:-prefixed one; the reconcile
        # evidence search must look for THAT in Sent Items.
        wire_subject = draft.get("subject") or send["subject"]
        try:
            journal.write(akey, "graph_issued", to=send["to"],
                          subject=wire_subject, lease_id=send["lease_id"])
            snapshot = mailer.send_draft_by_id(
                SEND_FROM, draft["entry_id"], expect_to=send["to"],
                expect_subject=draft.get("subject"))
        except (NotAllowlisted, DraftGuardError) as exc:
            # Guard refused BEFORE the POST: the send did not happen.
            journal.write(akey, "nacked", reason=str(exc)[:200])
            cadence.resolve_result(store, {
                "attempt_key": akey, "lease_id": send["lease_id"],
                "status": "failed", "error_class": "config",
                "failure_reason": str(exc)[:300]})
            return "reply_guard_refused"
        except GraphSendError as exc:
            # Graph answered non-2xx on /send: the send did not happen.
            journal.write(akey, "nacked", reason=str(exc)[:200])
            cadence.resolve_result(store, {
                "attempt_key": akey, "lease_id": send["lease_id"],
                "status": "failed",
                "error_class": "transient" if exc.status_code >= 500 else "permanent",
                "failure_reason": str(exc)[:300]})
            return "graph_rejected"
        except Exception as exc:
            # Network error inside the send window: may or may not have
            # reached Graph. Same ambiguity contract as send_auto - do NOT
            # nack; next tick's reconcile searches Sent Items for evidence
            # (search_sent_for normalizes the RE: prefix).
            journal.write(akey, "graph_error", reason=str(exc)[:200],
                          to=send["to"], subject=wire_subject,
                          lease_id=send["lease_id"])
            return "graph_error"
        journal.write(akey, "graph_sent")
        # THREADING VERIFY: the reply must still sit in the anchor's
        # conversation. On a mismatch the mail DID go (ack it), but flag it.
        conv = draft.get("conversation_id") or snapshot.get("conversation_id")
        if conv != anchor.get("conversationId"):
            alerts.append(f"thread_verify_failed: {akey}")
        ack = {"attempt_key": akey, "lease_id": send["lease_id"],
               "status": "sent",
               "internet_message_id": snapshot.get("internet_message_id")}
        res = cadence.resolve_result(store, ack)
        if res.get("ok"):
            journal.write(akey, "acked", outcome="sent",
                          imid=snapshot.get("internet_message_id"))
        else:
            journal.write(akey, "ack_failed", reason=str(res)[:200], ack=ack)
            return "ack_pending"
        return "sent"

    # auto-matthias via Graph sendMail
    issued_at = now
    try:
        # to/subject/lease_id ride on EVERY crash-window entry: the reconcile
        # pass reads only the LATEST entry per key, so an evidence search (and
        # the lease it must ack with) has to survive into graph_error too.
        journal.write(akey, "graph_issued", to=send["to"],
                      subject=send["subject"], lease_id=send["lease_id"])
        mailer.send_auto(send)
    except NotAllowlisted as exc:
        # Never reached Graph (raised before the POST): safe to park.
        journal.write(akey, "nacked", reason=str(exc)[:200])
        cadence.resolve_result(store, {
            "attempt_key": akey, "lease_id": send["lease_id"],
            "status": "failed", "error_class": "config",
            "failure_reason": str(exc)[:300]})
        return "not_allowlisted"
    except GraphSendError as exc:
        # Graph answered non-202: the send definitively did not happen.
        journal.write(akey, "nacked", reason=str(exc)[:200])
        cadence.resolve_result(store, {
            "attempt_key": akey, "lease_id": send["lease_id"],
            "status": "failed",
            "error_class": "transient" if exc.status_code >= 500 else "permanent",
            "failure_reason": str(exc)[:300]})
        return "graph_rejected"
    except Exception as exc:
        # Network error AFTER the POST was issued: the request may or may not
        # have reached Graph. Do NOT nack (a nack re-queues = possible
        # double-send). The next tick's reconcile searches Sent Items for
        # evidence and a human resolves genuine ambiguity.
        journal.write(akey, "graph_error", reason=str(exc)[:200],
                      to=send["to"], subject=send["subject"],
                      lease_id=send["lease_id"])
        return "graph_error"

    journal.write(akey, "graph_sent")
    evidence = mailer.readback_sent(
        SEND_FROM, send["to"], send["subject"], issued_at - timedelta(minutes=2))
    ack = {"attempt_key": akey, "lease_id": send["lease_id"], "status": "sent",
           "occurred_at": (evidence or {}).get("ts"),
           "internet_message_id": (evidence or {}).get("imid"),
           "entry_id": (evidence or {}).get("entry_id")}
    res = cadence.resolve_result(store, ack)
    if res.get("ok"):
        journal.write(akey, "acked", outcome="sent",
                      imid=(evidence or {}).get("imid"))
    else:
        # In-process ack can only fail on a store error; journal keeps the
        # outcome and replay delivers it next tick (result is idempotent).
        journal.write(akey, "ack_failed", reason=str(res)[:200], ack=ack)
        return "ack_pending"
    return "sent"


def replay_pending(store: ContactStore, mailer, journal: Journal,
                   alerts: list[str], *, now: datetime) -> dict:
    """Crash reconcile, run at tick start BEFORE any new claim."""
    counters = {"replayed": 0, "requeued": 0, "ambiguous": 0}
    for akey, entry in sorted(journal.pending().items()):
        state = entry.get("state")
        if state == "claimed":
            # The send call never fired: safe to hand back.
            cadence.resolve_result(store, {
                "attempt_key": akey, "lease_id": entry.get("lease_id") or "",
                "status": "failed", "error_class": "transient",
                "failure_reason": "worker restarted before send"})
            journal.write(akey, "nacked", reason="restart before send")
            counters["requeued"] += 1
        elif state in ("graph_issued", "graph_error"):
            to = entry.get("to") or ""
            subject = entry.get("subject") or ""
            evidence = None
            if to and subject:
                try:
                    evidence = mailer.search_sent_for(
                        SEND_FROM, to, subject,
                        now - timedelta(days=RECONCILE_LOOKBACK_DAYS))
                except Exception:  # noqa: BLE001 - evidence search is best-effort
                    evidence = None
            if evidence:
                cadence.resolve_result(store, {
                    "attempt_key": akey, "lease_id": entry.get("lease_id") or "",
                    "status": "sent", "occurred_at": evidence.get("ts"),
                    "internet_message_id": evidence.get("imid")})
                journal.write(akey, "acked", outcome="sent-reconciled")
                counters["replayed"] += 1
            else:
                counters["ambiguous"] += 1
                alerts.append(
                    f"AMBIGUOUS send {akey} to {to!r}: crashed inside the send "
                    "window, no Sent Items evidence. NOT resending; resolve on "
                    "the campaign page (Retry or Mark sent).")
                journal.write(akey, "ambiguous_flagged")
        elif state in ("graph_sent", "ack_failed"):
            ack = entry.get("ack") or {
                "attempt_key": akey, "lease_id": entry.get("lease_id") or "",
                "status": "sent"}
            res = cadence.resolve_result(store, ack)
            if res.get("ok") or res.get("idempotent"):
                journal.write(akey, "acked", outcome="sent-replayed")
                counters["replayed"] += 1
        elif state == "ambiguous_flagged":
            counters["ambiguous"] += 1
    return counters


# -- the tick ---------------------------------------------------------------------

def run_tick(data_dir: str | Path, *, mailer=None, poll_fn=None,
             at: datetime | None = None, dry_run: bool = False,
             draft_to_self: bool = False, sleep=time.sleep) -> dict:
    """One full cloud tick. ``mailer`` / ``poll_fn`` are injectable for tests;
    the prod defaults are built from the BRISKEN_GRAPH_* credential."""
    data_dir = Path(data_dir).resolve()
    at = at or _now_utc()
    if mailer is None or poll_fn is None:
        creds = _load_creds()
        if mailer is None:
            mailer = GraphMailer()
        if poll_fn is None:
            client = graph_capture.GraphClient(
                creds["BRISKEN_TENANT_ID"], creds["BRISKEN_GRAPH_CLIENT_ID"],
                creds["BRISKEN_GRAPH_CLIENT_SECRET"])
            def poll_fn(mbx, since, until, _c=client):  # noqa: E306
                return graph_capture.poll(_c, mbx, since, until)

    journal = Journal(data_dir / "cloud-journal.jsonl")
    alerts: list[str] = []
    counters = {"sent": 0, "drafted": 0, "failed": 0, "ambiguous": 0}
    report: dict = {"worker_id": WORKER_ID, "at": cadence._iso(at)}

    with ContactStore(data_dir / "lead-desk.sqlite") as store:
        report["kill_switch"] = (store.get_state("kill_switch") or "0") == "1"

        if not dry_run:
            replay = replay_pending(store, mailer, journal, alerts, now=at)
            counters["ambiguous"] = replay["ambiguous"]
            report["replay"] = replay

        # Capture before claim; a capture failure must block claiming
        # (unseen replies could mean sending to someone who already answered).
        try:
            report["capture"] = run_capture(store, data_dir, poll_fn, mailer,
                                            now=at, dry_run=dry_run)
        except Exception as exc:  # noqa: BLE001
            report["capture_error"] = str(exc)[:300]
            report["aborted"] = "capture-failed"
            _heartbeat(store, counters, report)
            return report

        claims = cadence.claim_sends(store, WORKER_ID, MAX_CLAIM, at=at,
                                     peek=dry_run)
        report["paused"] = bool(claims.get("paused"))
        sends = claims.get("claims", [])
        report["claimed"] = len(sends)
        if dry_run:
            report["due_preview"] = [
                {"to": s["to"], "subject": s["subject"],
                 "mode": s["send_mode"]} for s in sends]
            return report

        for i, send in enumerate(sends):
            outcome = execute_one(store, mailer, send, journal,
                                  draft_to_self=draft_to_self, now=at,
                                  alerts=alerts)
            if outcome in ("sent", "ack_pending"):
                counters["sent"] += 1
            elif outcome == "drafted":
                counters["drafted"] += 1
            elif outcome != "draft_to_self":
                counters["failed"] += 1
            if outcome in ("graph_error",):
                alerts.append(
                    f"Graph error inside send window for {send['attempt_key']} "
                    f"to {send['to']}: reconcile searches Sent Items next tick.")
            if i < len(sends) - 1:
                sleep(send.get("throttle_seconds", 12)
                      + random.uniform(0, send.get("jitter_seconds", 4)))

        for msg in alerts:
            print(f"ALERT: {msg}")
        if alerts:
            store.set_state("cloud_worker_alert",
                            json.dumps({"ts": now_iso(), "alerts": alerts}),
                            now_iso())
        journal.compact()
        _heartbeat(store, counters, report)

    report["counters"] = counters
    report["alerts"] = alerts
    return report


def _heartbeat(store: ContactStore, counters: dict, report: dict) -> None:
    store.set_state("worker_heartbeat", json.dumps({
        "worker_id": WORKER_ID, "ts": now_iso(), "counters": counters,
    }), now_iso())
    report["heartbeat"] = True


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lead-desk-cloud-worker")
    p.add_argument("--data", default=os.environ.get("LEAD_DESK_DATA", "lead-desk-data"))
    p.add_argument("--dry-run", action="store_true",
                   help="peek + print, lease nothing, send nothing")
    p.add_argument("--draft-to-self", action="store_true",
                   help="full pipeline but drafts into our own mailbox, no ack")
    p.add_argument("--loop", type=int, default=0,
                   help="seconds between ticks; 0 = one tick and exit")
    args = p.parse_args(argv)

    if not have_creds():
        print("ERROR: BRISKEN_GRAPH_* credentials not configured")
        return 2

    def once() -> int:
        try:
            report = run_tick(Path(args.data), dry_run=args.dry_run,
                              draft_to_self=args.draft_to_self)
            print(json.dumps(report, indent=1, default=str))
            return 0
        except Exception as exc:  # noqa: BLE001 - a scheduled loop must survive a bad tick
            print(f"TICK ERROR: {exc}")
            return 1

    if args.loop <= 0:
        return once()
    print(f"lead-desk-cloud-worker loop every {args.loop}s (Ctrl-C to stop)")
    while True:
        once()
        time.sleep(args.loop)


if __name__ == "__main__":
    raise SystemExit(main())
