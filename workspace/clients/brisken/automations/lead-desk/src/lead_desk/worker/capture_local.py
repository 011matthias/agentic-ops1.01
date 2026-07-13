"""Reply + bounce capture via Outlook COM (the no-Graph twin of capture.py).

Polls the matthias + dirk inboxes since a per-mailbox watermark (minus a
2-hour overlap - the sink's event-hash idempotency absorbs re-posts),
matches senders against the enrolled watchlist, and posts ``reply`` /
``bounce`` events to ``POST /events``. Also correlates Dirk's Sent Items
with 'drafted' attempts (recipient + subject) so a draft he actually sent
completes its cadence step via ``/api/outbox/draft-sent``.

Watchlist filtering happens LOCALLY: unrelated inbound mail never leaves
this machine. A reply landing in both inboxes carries one
internetMessageId, so the sink collapses the duplicate - and the same
mechanism makes the later Graph capture a drop-in supplement.

v1 semantics: ANY inbound reply halts the cadence, OOO included. A false
halt costs one follow-up; a false continue mails someone who answered.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from . import com_mail
from .api import LeadDeskApi
from .config import WorkerConfig, load_capture_state, save_capture_state

OVERLAP = timedelta(hours=2)
DEFAULT_LOOKBACK_DAYS = 3


def _since_for(state: dict, mailbox: str) -> datetime:
    raw = (state.get("watermarks") or {}).get(mailbox)
    if raw:
        try:
            return datetime.fromisoformat(raw) - OVERLAP
        except ValueError:
            pass
    return datetime.now() - timedelta(days=DEFAULT_LOOKBACK_DAYS)


def build_payloads(items: list[dict], watch: set[str]) -> list[dict]:
    """Map raw inbox item dicts to /events payloads (pure; unit-tested)."""
    payloads: list[dict] = []
    for it in items:
        if com_mail.is_bounce(it.get("message_class"), it.get("subject")):
            for failed in com_mail.extract_bounced_addresses(
                    it.get("body_head"), watch):
                payloads.append(com_mail.bounce_payload(
                    failed, it.get("subject"), it.get("ts") or "",
                    it.get("imid")))
            continue
        sender = (it.get("sender") or "").lower()
        if sender and sender in watch:
            payloads.append(com_mail.reply_payload(
                sender, it.get("subject"), it.get("ts") or "",
                it.get("imid"), it.get("body_head")))
    return payloads


def run_capture(ol, api: LeadDeskApi, cfg: WorkerConfig,
                mailboxes: tuple[str, ...], *, dry_run: bool = False) -> dict:
    wl = api.watchlist()
    watch = {(e or "").lower()
             for c in wl.get("contacts", [])
             for e in (c.get("email"), c.get("alt_email")) if e}
    state = load_capture_state(cfg)
    run_started = datetime.now()
    all_payloads: list[dict] = []
    polled: dict[str, int] = {}

    for smtp in mailboxes:
        acct = com_mail.resolve_account(ol, smtp)
        if acct is None:
            continue
        items = com_mail.poll_inbox(acct, _since_for(state, smtp))
        polled[smtp] = len(items)
        all_payloads.extend(build_payloads(items, watch))

    # Drafted-attempt correlation against Dirk's Sent Items.
    confirmations: list[dict] = []
    drafted = wl.get("drafted", [])
    if drafted:
        dirk = com_mail.resolve_account(ol, mailboxes[-1])
        if dirk is not None:
            sent = com_mail.poll_sent(dirk, datetime.now() - timedelta(days=14))
            confirmations = com_mail.match_drafted(sent, drafted)

    if dry_run:
        return {"dry_run": True, "polled": polled, "watch": len(watch),
                "payloads": all_payloads, "draft_confirmations": confirmations}

    posted = api.post_events(all_payloads) if all_payloads else {"inserted": 0}
    confirmed = 0
    for c in confirmations:
        try:
            api.draft_sent(c)
            confirmed += 1
        except Exception:
            continue
    # Advance watermarks only after a successful post (idempotent sink makes
    # a re-poll harmless; an un-advanced watermark just re-reads the window).
    state.setdefault("watermarks", {})
    for smtp in mailboxes:
        state["watermarks"][smtp] = run_started.isoformat(timespec="seconds")
    save_capture_state(cfg, state)
    return {"polled": polled, "watch": len(watch),
            "events_posted": len(all_payloads),
            "events_inserted": posted.get("inserted", 0),
            "draft_confirmations": confirmed}
