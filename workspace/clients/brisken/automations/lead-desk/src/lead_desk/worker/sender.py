"""Per-send orchestration: preflight -> journal WAL -> COM -> ack/nack.

At-most-once is the whole game. The journal entry ``com_issued`` is written
IMMEDIATELY before the irreversible ``.Send()``; every crash window then has
a deterministic reconcile action (see journal.py). A duplicate cold email is
the one failure money can't fix, so ambiguity always resolves toward
"assume sent + tell a human", never toward resending.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

from . import com_mail
from .api import ApiRejected, ApiUnavailable, LeadDeskApi
from .journal import Journal


def body_hash(subject: str, body: str) -> str:
    return hashlib.sha256((subject + "\n" + body).encode("utf-8")).hexdigest()


def execute_one(ol, accounts: dict, send: dict, journal: Journal,
                api: LeadDeskApi, *, draft_to_self: bool = False) -> str:
    """Execute one claimed send. Returns the outcome string for counters.
    ``accounts``: {'auto': matthias acct, 'dirk': dirk acct, 'self_smtp': str}.
    """
    akey = send["attempt_key"]

    # Copy tamper check: the rendered payload must hash to what the app
    # claims was approved-and-pinned. A mismatch is an approval breach.
    if body_hash(send["subject"], send["body"]) != send["body_hash"]:
        journal.write(akey, "nacked", reason="body hash mismatch")
        api.result({"attempt_key": akey, "lease_id": send["lease_id"],
                    "status": "failed", "error_class": "config",
                    "failure_reason": "body hash mismatch (copy drift)"})
        return "hash_mismatch"

    journal.write(akey, "claimed", to=send["to"], lease_id=send["lease_id"],
                  mode=send["send_mode"])

    if draft_to_self:
        # Test mode: full pipeline, but the mail lands as a draft in OUR
        # mailbox and nothing is acked (repeatable, human-inspectable).
        target = dict(send, to=accounts["self_smtp"])
        com_mail.load_dirk_draft(ol, accounts["auto"], target)
        journal.write(akey, "nacked", reason="draft-to-self test mode")
        return "draft_to_self"

    if send["send_mode"] == "draft-dirk":
        try:
            res = com_mail.load_dirk_draft(ol, accounts["dirk"], send)
        except Exception as exc:
            journal.write(akey, "nacked", reason=str(exc)[:200])
            api.result({"attempt_key": akey, "lease_id": send["lease_id"],
                        "status": "failed", "error_class": "transient",
                        "failure_reason": f"draft load: {exc}"[:300]})
            return "draft_failed"
        journal.write(akey, "drafted", entry_id=res.get("entry_id"))
        api.result({"attempt_key": akey, "lease_id": send["lease_id"],
                    "status": "drafted", "entry_id": res.get("entry_id")})
        journal.write(akey, "acked", outcome="drafted")
        return "drafted"

    # auto-matthias
    issued_at = datetime.now()
    try:
        journal.write(akey, "com_issued", to=send["to"], subject=send["subject"])
        com_mail.send_auto(ol, accounts["auto"], send)
    except com_mail.UnresolvedRecipients as exc:
        journal.write(akey, "nacked", reason=f"unresolved: {exc.names}")
        api.result({"attempt_key": akey, "lease_id": send["lease_id"],
                    "status": "failed", "error_class": "resolve",
                    "failure_reason": f"unresolved recipients: {exc.names}"[:300]})
        return "unresolved"
    except Exception as exc:
        # COM error AFTER com_issued: .Send() may or may not have fired.
        # Do NOT nack (a nack re-queues = possible double-send). Leave the
        # journal at com_issued; the next tick's reconcile searches Sent
        # Items for evidence and a human resolves genuine ambiguity.
        journal.write(akey, "com_error", reason=str(exc)[:200])
        return "com_error"

    journal.write(akey, "com_sent")
    evidence = com_mail.readback_sent(
        accounts["auto"], send["to"], send["subject"],
        issued_at - timedelta(minutes=2))
    ack = {"attempt_key": akey, "lease_id": send["lease_id"], "status": "sent",
           "occurred_at": (evidence or {}).get("ts"),
           "internet_message_id": (evidence or {}).get("imid"),
           "entry_id": (evidence or {}).get("entry_id")}
    try:
        api.result(ack)
        journal.write(akey, "acked", outcome="sent",
                      imid=(evidence or {}).get("imid"))
    except (ApiUnavailable, ApiRejected) as exc:
        # Sent for real but the ack didn't land: journal stays at com_sent
        # and replay_pending delivers it next tick (result is idempotent).
        journal.write(akey, "ack_failed", reason=str(exc)[:200], ack=ack)
        return "ack_pending"
    return "sent"


def replay_pending(ol, accounts: dict, journal: Journal, api: LeadDeskApi,
                   alerts: list[str]) -> dict:
    """Crash/offline reconcile, run at tick start BEFORE any new claim."""
    counters = {"replayed": 0, "requeued": 0, "ambiguous": 0}
    for akey, entry in sorted(journal.pending().items()):
        state = entry.get("state")
        if state == "claimed":
            # COM never fired: safe to hand back.
            try:
                api.result({"attempt_key": akey,
                            "lease_id": entry.get("lease_id") or "",
                            "status": "failed", "error_class": "transient",
                            "failure_reason": "worker restarted before send"})
                journal.write(akey, "nacked", reason="restart before send")
                counters["requeued"] += 1
            except (ApiUnavailable, ApiRejected):
                pass
        elif state in ("com_issued", "com_error"):
            # Ambiguous: search Sent Items for evidence. Found -> ack sent.
            # Not found -> STILL ambiguous (Outbox may hold it); alert, never
            # resend. The lease expires server-side into 'stalled' where a
            # human decides.
            to = entry.get("to") or ""
            subject = entry.get("subject") or ""
            evidence = None
            if to and subject:
                try:
                    evidence = com_mail.search_sent_for(
                        accounts["auto"], to, subject,
                        com_mail.default_since(days=7))
                except Exception:
                    evidence = None
            if evidence:
                try:
                    api.result({"attempt_key": akey,
                                "lease_id": entry.get("lease_id") or "",
                                "status": "sent",
                                "occurred_at": evidence.get("ts"),
                                "internet_message_id": evidence.get("imid")})
                    journal.write(akey, "acked", outcome="sent-reconciled")
                    counters["replayed"] += 1
                except (ApiUnavailable, ApiRejected):
                    pass
            else:
                counters["ambiguous"] += 1
                alerts.append(
                    f"AMBIGUOUS send {akey} to {to!r}: crashed inside the send "
                    "window, no Sent Items evidence. NOT resending; resolve on "
                    "the campaign page (Retry or Mark sent).")
                journal.write(akey, "ambiguous_flagged")
        elif state in ("com_sent", "ack_failed"):
            ack = entry.get("ack") or {
                "attempt_key": akey, "lease_id": entry.get("lease_id") or "",
                "status": "sent"}
            try:
                api.result(ack)
                journal.write(akey, "acked", outcome="sent-replayed")
                counters["replayed"] += 1
            except (ApiUnavailable, ApiRejected):
                pass
        elif state == "ambiguous_flagged":
            counters["ambiguous"] += 1
    return counters
