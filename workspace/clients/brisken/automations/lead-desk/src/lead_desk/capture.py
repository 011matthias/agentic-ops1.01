"""Cloud auto-capture: read the allowlisted mailboxes + calendars app-only
via Microsoft Graph and POST the touches to the Lead Desk ``/events`` sink.

The in-app cloud worker (``cloud_worker.py``) drives these mappers on every
tick; this module's own ``main`` remains a standalone CLI for ssh drills.
Credential decision (4d, 2026-07-16): reuse the "BRISKEN MARKETING OPS
INTEGRATION" app registration (BRISKEN_* env fallback below) instead of a
dedicated least-privilege app; the compensating control is the HARD
dirk+matthias mailbox allowlist asserted in code (an Exchange Application
Access Policy on that app remains recommended, tracked in
rule_brisken_graph_first). Nothing here sends, edits, or deletes: it issues
Graph GETs and HTTP POSTs to our own sink.

Idempotency is the sink's job: every event carries the message's
``internetMessageId`` (calendar: ``iCalUId``) as ``ext_key``, so re-polling the
same item is a no-op. That also means the poller does not need a durable delta
cursor to be correct; a fixed lookback window each run is safe. A watermark file
is used only as an efficiency hint.

    lead-desk-capture --since-days 3            # poll + post
    lead-desk-capture --dry-run                 # fetch + map + print, no POST

Env (all required unless noted):
    LEAD_DESK_TENANT_ID       Entra tenant (falls back to BRISKEN_TENANT_ID)
    LEAD_DESK_CLIENT_ID       app client id (falls back to BRISKEN_GRAPH_CLIENT_ID)
    LEAD_DESK_CLIENT_SECRET   app secret (falls back to BRISKEN_GRAPH_CLIENT_SECRET)
    LEAD_DESK_MAILBOX(ES)     mailbox UPN(s) to read, hard-filtered to the allowlist
    LEAD_DESK_URL             sink base url (https://brisken-lead-desk.fly.dev)
    LEAD_DESK_INGEST_SECRET   bearer for POST /events
    LEAD_DESK_CAPTURE_STATE   optional watermark file (default /data/capture-state.json)
"""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

GRAPH = "https://graph.microsoft.com/v1.0"
TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
SCOPE = "https://graph.microsoft.com/.default"

# Graph $select sets, kept minimal (only what the sink needs to match + record).
_MSG_SELECT = "internetMessageId,subject,sentDateTime,receivedDateTime,from,toRecipients,ccRecipients"
# Inbox needs the auto-reply headers + a body snippet to attribute an NDR bounce.
_INBOX_SELECT = _MSG_SELECT + ",internetMessageHeaders,bodyPreview"
_EVT_SELECT = "iCalUId,subject,start,organizer,attendees"

# Future demos are invisible until the meeting day unless calendarView reaches
# forward; the sink is idempotent on iCalUId, so a generous horizon is safe.
CALENDAR_HORIZON_DAYS = 60

# HARD mailbox allowlist (rule_brisken_graph_first): the capture worker may only
# ever read these two mailboxes, regardless of env input.
ALLOWED_MAILBOXES = ("dirk.neumann@brisken.com", "matthias.silva@brisken.com")

_EMAIL_RE = re.compile(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}", re.IGNORECASE)
_NDR_SENDERS = ("postmaster@", "mailer-daemon@", "microsoftexchange")
_NDR_SUBJECT_RE = re.compile(
    r"undeliverable|delivery has failed|mail delivery failed|delivery status "
    r"notification|returned mail|unzustellbar|nicht zugestellt", re.IGNORECASE)
_AUTO_SUBJECT_RE = re.compile(
    r"automatic reply|out of office|auto[- ]?reply|abwesenhe|autosvar|"
    r"automatische antwort|absence du bureau", re.IGNORECASE)


def _headers_map(msg: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for h in msg.get("internetMessageHeaders") or []:
        name = (h.get("name") or "").strip().lower()
        if name:
            out[name] = (h.get("value") or "").strip()
    return out


def is_auto_reply(msg: dict) -> bool:
    """An OOO / vacation / auto-generated message. Detected from RFC 3834
    ``Auto-Submitted`` / ``X-Auto-Response-Suppress`` headers, else the subject."""
    h = _headers_map(msg)
    auto = h.get("auto-submitted", "").lower()
    if auto and auto != "no":            # auto-replied | auto-generated
        return True
    if h.get("x-auto-response-suppress"):
        return True
    return bool(_AUTO_SUBJECT_RE.search(msg.get("subject") or ""))


def is_ndr(msg: dict) -> bool:
    """A bounce / non-delivery report from a mailer daemon."""
    frm = (((msg.get("from") or {}).get("emailAddress") or {}).get("address") or "").lower()
    if any(s in frm for s in _NDR_SENDERS):
        return True
    return bool(_NDR_SUBJECT_RE.search(msg.get("subject") or ""))


def _failed_recipient(msg: dict, owner: str) -> str | None:
    """Best-effort extraction of the bounced address from an NDR's subject +
    body snippet (skipping our own address and the daemon's)."""
    text = f"{msg.get('subject') or ''} {msg.get('bodyPreview') or ''}"
    for addr in _EMAIL_RE.findall(text):
        a = addr.lower()
        if a != owner and "postmaster" not in a and "mailer-daemon" not in a:
            return a
    return None


# -- pure mapping (unit-tested without network) -------------------------------

def _addrs(recipients: list | None) -> list[str]:
    out = []
    for r in recipients or []:
        addr = ((r or {}).get("emailAddress") or {}).get("address")
        if addr:
            out.append(addr.strip().lower())
    return out


def sent_to_payloads(msgs: list[dict]) -> list[dict]:
    """A message from SentItems -> one outbound 'sent' event per recipient."""
    out = []
    for m in msgs:
        mid = m.get("internetMessageId")
        ts = m.get("sentDateTime")
        subj = m.get("subject")
        for addr in _addrs(m.get("toRecipients")) + _addrs(m.get("ccRecipients")):
            out.append({
                "email": addr, "type": "sent", "direction": "outbound",
                "channel": "email", "occurred_at": ts, "subject": subj,
                "detail": "auto: sent mail", "source": "graph-auto",
                "internet_message_id": mid,
            })
    return out


def inbox_to_payloads(msgs: list[dict], mailbox: str = "") -> list[dict]:
    """An Inbox message -> a sink payload, classified so a cadence is not halted
    or a stage promoted by noise:

    * an NDR / bounce -> ``type='bounce'`` keyed on the FAILED recipient, so the
      sink auto-suppresses that contact (not the mailer daemon);
    * an OOO / auto-reply -> a low-signal ``type='note'`` (does not promote to
      'replied' and does not halt the cadence);
    * a genuine inbound -> ``type='reply'``.
    """
    owner = (mailbox or "").strip().lower()
    out = []
    for m in msgs:
        mid = m.get("internetMessageId")
        subj = m.get("subject")
        ts = m.get("receivedDateTime")
        addr = (((m.get("from") or {}).get("emailAddress") or {}).get("address") or "").strip().lower()
        if is_ndr(m):
            failed = _failed_recipient(m, owner)
            if failed:
                out.append({
                    "email": failed, "type": "bounce", "direction": "inbound",
                    "channel": "email", "occurred_at": ts, "subject": subj,
                    "detail": "auto: non-delivery report", "source": "graph-auto",
                    "internet_message_id": mid,
                })
            continue
        if not addr:
            continue
        if is_auto_reply(m):
            out.append({
                "email": addr, "type": "note", "direction": "inbound",
                "channel": "email", "occurred_at": ts, "subject": subj,
                "detail": "auto: auto-reply / OOO (cadence not halted)",
                "source": "graph-auto", "internet_message_id": mid,
            })
            continue
        out.append({
            "email": addr, "type": "reply", "direction": "inbound",
            "channel": "email", "occurred_at": ts, "subject": subj,
            "detail": "auto: inbound reply", "source": "graph-auto",
            "internet_message_id": mid,
        })
    return out


def calendar_to_payloads(events: list[dict], mailbox: str) -> list[dict]:
    """A calendar event -> one 'booked' meeting event per attendee that is not
    the mailbox owner. The sink drops attendees that are not known contacts."""
    me = (mailbox or "").strip().lower()
    out = []
    for e in events:
        uid = e.get("iCalUId")
        ts = ((e.get("start") or {}).get("dateTime")) or None
        subj = e.get("subject")
        for addr in _addrs(e.get("attendees")):
            if addr == me:
                continue
            out.append({
                "email": addr, "type": "booked", "direction": "outbound",
                "channel": "meeting", "occurred_at": ts, "subject": subj,
                "detail": "auto: calendar meeting", "source": "graph-auto",
                # calendar has no internetMessageId; iCalUId is the stable key
                "ext_key": f"cal-{uid}",
            })
    return out


# -- Graph client (network) ---------------------------------------------------

class GraphClient:
    def __init__(self, tenant: str, client_id: str, client_secret: str):
        import httpx
        self._httpx = httpx
        self.tenant = tenant
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: str | None = None

    def _auth(self) -> str:
        if self._token:
            return self._token
        r = self._httpx.post(
            TOKEN_URL.format(tenant=self.tenant),
            data={"client_id": self.client_id, "client_secret": self.client_secret,
                  "scope": SCOPE, "grant_type": "client_credentials"},
            timeout=30,
        )
        r.raise_for_status()
        self._token = r.json()["access_token"]
        return self._token

    def get_all(self, url: str) -> list[dict]:
        """GET with paging (@odata.nextLink) -> flat list of value[] items."""
        items: list[dict] = []
        headers = {"Authorization": f"Bearer {self._auth()}"}
        while url:
            r = self._httpx.get(url, headers=headers, timeout=60)
            r.raise_for_status()
            body = r.json()
            items.extend(body.get("value", []))
            url = body.get("@odata.nextLink")
        return items


def _z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def poll(client: GraphClient, mailbox: str, since: datetime, until: datetime,
         horizon_days: int = CALENDAR_HORIZON_DAYS) -> list[dict]:
    """Fetch sent + inbox + calendar and return sink payloads. Mail is bounded
    [since, until]; the CALENDAR upper bound reaches ``horizon_days`` forward so
    a demo booked for a future date is captured now, not on the meeting day."""
    assert mailbox.strip().lower() in ALLOWED_MAILBOXES, f"mailbox not allowlisted: {mailbox}"
    s = _z(since)
    cal_u = _z(until + timedelta(days=horizon_days))
    box = f"{GRAPH}/users/{mailbox}"
    sent = client.get_all(
        f"{box}/mailFolders/sentitems/messages?$select={_MSG_SELECT}"
        f"&$filter=sentDateTime ge {s}&$top=100")
    inbox = client.get_all(
        f"{box}/mailFolders/inbox/messages?$select={_INBOX_SELECT}"
        f"&$filter=receivedDateTime ge {s}&$top=100")
    events = client.get_all(
        f"{box}/calendarView?startDateTime={s}&endDateTime={cal_u}"
        f"&$select={_EVT_SELECT}&$top=100")
    return (sent_to_payloads(sent) + inbox_to_payloads(inbox, mailbox)
            + calendar_to_payloads(events, mailbox))


def post_events(base_url: str, ingest_secret: str, payloads: list[dict]) -> dict:
    import httpx
    r = httpx.post(
        f"{base_url.rstrip('/')}/events",
        headers={"Authorization": f"Bearer {ingest_secret}"},
        json=payloads, timeout=60,
    )
    r.raise_for_status()
    return r.json()


# -- watermark (efficiency hint only; correctness comes from idempotency) ------

def _read_watermark(path: Path) -> datetime | None:
    try:
        return datetime.fromisoformat(json.loads(path.read_text())["last_run"])
    except Exception:
        return None


def _write_watermark(path: Path, when: datetime) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"last_run": when.isoformat()}))
    except Exception:
        pass  # a missing watermark just means the next run re-scans the window


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lead-desk-capture")
    p.add_argument("--since-days", type=int, default=3,
                   help="lookback window if no watermark; idempotency makes overlap safe")
    p.add_argument("--dry-run", action="store_true", help="fetch + map + print, no POST")
    args = p.parse_args(argv)

    env = os.environ
    # 4d creds decision: the dedicated LEAD_DESK_* app was never provisioned;
    # fall back to the BRISKEN MARKETING OPS INTEGRATION creds (Fly secrets).
    creds = {k: env.get(k) or env.get(fb) for k, fb in (
        ("LEAD_DESK_TENANT_ID", "BRISKEN_TENANT_ID"),
        ("LEAD_DESK_CLIENT_ID", "BRISKEN_GRAPH_CLIENT_ID"),
        ("LEAD_DESK_CLIENT_SECRET", "BRISKEN_GRAPH_CLIENT_SECRET"))}
    missing = [k for k, v in creds.items() if not v]
    if missing:
        print(f"ERROR: missing env: {', '.join(missing)}")
        return 2

    # Resolve the mailbox set (LEAD_DESK_MAILBOXES comma-list, else the single
    # LEAD_DESK_MAILBOX) and HARD-filter to the allowlist - never poll another.
    raw = env.get("LEAD_DESK_MAILBOXES") or env.get("LEAD_DESK_MAILBOX") or ""
    mailboxes = [m for m in (x.strip().lower() for x in raw.split(",") if x.strip())
                 if m in ALLOWED_MAILBOXES]
    if not mailboxes:
        print(f"ERROR: no allowlisted mailbox configured (allowed: {', '.join(ALLOWED_MAILBOXES)})")
        return 2

    now = datetime.now(timezone.utc)
    state_path = Path(env.get("LEAD_DESK_CAPTURE_STATE", "/data/capture-state.json"))
    watermark = _read_watermark(state_path)
    # Re-scan a small overlap even when a watermark exists (dedup absorbs it).
    since = min(watermark, now - timedelta(days=1)) if watermark else now - timedelta(days=args.since_days)

    client = GraphClient(creds["LEAD_DESK_TENANT_ID"],
                         creds["LEAD_DESK_CLIENT_ID"],
                         creds["LEAD_DESK_CLIENT_SECRET"])
    payloads: list[dict] = []
    for mbx in mailboxes:
        payloads.extend(poll(client, mbx, since, now))
    print(f"polled {', '.join(mailboxes)} since {since.isoformat()}: "
          f"{len(payloads)} candidate events")

    if args.dry_run:
        for pl in payloads[:25]:
            print(f"  {pl['direction']:8} {pl['type']:7} {pl.get('email','-'):40} {pl.get('subject') or ''}")
        if len(payloads) > 25:
            print(f"  ... +{len(payloads) - 25} more")
        return 0

    base_url = env.get("LEAD_DESK_URL")
    secret = env.get("LEAD_DESK_INGEST_SECRET")
    if not base_url or not secret:
        print("ERROR: LEAD_DESK_URL and LEAD_DESK_INGEST_SECRET required to POST")
        return 2
    if not payloads:
        _write_watermark(state_path, now)
        print("nothing to post")
        return 0
    res = post_events(base_url, secret, payloads)
    print(f"posted {len(payloads)} events -> inserted {res.get('inserted')} "
          f"(the rest were duplicates or unknown contacts)")
    _write_watermark(state_path, now)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
