"""Phase 2 cloud auto-capture: read Dirk's mailbox + calendar app-only via
Microsoft Graph and POST the touches to the Lead Desk ``/events`` sink.

Runs as a scheduled Fly Machine (same image, CMD overridden to
``lead-desk-capture``). It is app-only (client-credentials); the credential is
scoped to Dirk's mailbox alone by an Exchange Application Access Policy (see
``PHASE2-IT-REQUEST.md``). Nothing here sends, edits, or deletes: it issues
Graph GETs and HTTP POSTs to our own sink.

Idempotency is the sink's job: every event carries the message's
``internetMessageId`` (calendar: ``iCalUId``) as ``ext_key``, so re-polling the
same item is a no-op. That also means the poller does not need a durable delta
cursor to be correct; a fixed lookback window each run is safe. A watermark file
is used only as an efficiency hint.

    lead-desk-capture --since-days 3            # poll + post
    lead-desk-capture --dry-run                 # fetch + map + print, no POST

Env (all required unless noted):
    LEAD_DESK_TENANT_ID       Entra tenant (aa3bd2bf-...)
    LEAD_DESK_CLIENT_ID       app registration (client) id
    LEAD_DESK_CLIENT_SECRET   app secret
    LEAD_DESK_MAILBOX         mailbox UPN to read (dirk.neumann@brisken.com)
    LEAD_DESK_URL             sink base url (https://brisken-lead-desk.fly.dev)
    LEAD_DESK_INGEST_SECRET   bearer for POST /events
    LEAD_DESK_CAPTURE_STATE   optional watermark file (default /data/capture-state.json)
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

GRAPH = "https://graph.microsoft.com/v1.0"
TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
SCOPE = "https://graph.microsoft.com/.default"

# Graph $select sets, kept minimal (only what the sink needs to match + record).
_MSG_SELECT = "internetMessageId,subject,sentDateTime,receivedDateTime,from,toRecipients,ccRecipients"
_EVT_SELECT = "iCalUId,subject,start,organizer,attendees"


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


def inbox_to_payloads(msgs: list[dict]) -> list[dict]:
    """A message from Inbox -> one inbound 'reply' event keyed on the sender."""
    out = []
    for m in msgs:
        addr = (((m.get("from") or {}).get("emailAddress") or {}).get("address") or "").strip().lower()
        if not addr:
            continue
        out.append({
            "email": addr, "type": "reply", "direction": "inbound",
            "channel": "email", "occurred_at": m.get("receivedDateTime"),
            "subject": m.get("subject"), "detail": "auto: inbound reply",
            "source": "graph-auto", "internet_message_id": m.get("internetMessageId"),
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


def poll(client: GraphClient, mailbox: str, since: datetime, until: datetime) -> list[dict]:
    """Fetch sent + inbox + calendar in [since, until] and return sink payloads."""
    s = since.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    u = until.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    box = f"{GRAPH}/users/{mailbox}"
    sent = client.get_all(
        f"{box}/mailFolders/sentitems/messages?$select={_MSG_SELECT}"
        f"&$filter=sentDateTime ge {s}&$top=100")
    inbox = client.get_all(
        f"{box}/mailFolders/inbox/messages?$select={_MSG_SELECT}"
        f"&$filter=receivedDateTime ge {s}&$top=100")
    events = client.get_all(
        f"{box}/calendarView?startDateTime={s}&endDateTime={u}"
        f"&$select={_EVT_SELECT}&$top=100")
    return (sent_to_payloads(sent) + inbox_to_payloads(inbox)
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
    missing = [k for k in ("LEAD_DESK_TENANT_ID", "LEAD_DESK_CLIENT_ID",
                           "LEAD_DESK_CLIENT_SECRET", "LEAD_DESK_MAILBOX")
               if not env.get(k)]
    if missing:
        print(f"ERROR: missing env: {', '.join(missing)}")
        return 2

    now = datetime.now(timezone.utc)
    state_path = Path(env.get("LEAD_DESK_CAPTURE_STATE", "/data/capture-state.json"))
    watermark = _read_watermark(state_path)
    # Re-scan a small overlap even when a watermark exists (dedup absorbs it).
    since = min(watermark, now - timedelta(days=1)) if watermark else now - timedelta(days=args.since_days)

    client = GraphClient(env["LEAD_DESK_TENANT_ID"], env["LEAD_DESK_CLIENT_ID"],
                         env["LEAD_DESK_CLIENT_SECRET"])
    payloads = poll(client, env["LEAD_DESK_MAILBOX"], since, now)
    print(f"polled {env['LEAD_DESK_MAILBOX']} since {since.isoformat()}: {len(payloads)} candidate events")

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
