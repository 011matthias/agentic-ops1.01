"""All Microsoft Graph mail I/O for the cloud worker in one place - the
headless twin of ``worker/com_mail.py`` (which needs a logged-on Windows
session with Outlook open; this needs only the app-only credential).

Patterns carried over from the proven paths (do not "simplify"):
  * HARD mailbox allowlist (rule_brisken_graph_first): every /users/{mbx}
    call asserts the mailbox is exactly dirk or matthias BEFORE the request,
    regardless of input. The app credential is tenant-wide until an Exchange
    Application Access Policy lands, so the code IS the compensating control.
  * auto-send only ever FROM matthias.silva (never as Dirk - his click on a
    staged draft stays the gate on his name, mirroring load_dirk_draft);
  * Dirk drafts: created via POST /users/{dirk}/messages, which lands in HIS
    Drafts folder by definition (no COM store mis-filing class of bug), with
    the same (subject, to) dupe guard as the COM loader;
  * sent-items readback for evidence: $filter on sentDateTime + client-side
    subject/recipient match, never $search (matches bodies, returns years).

The token comes from sync.graph_token() (BRISKEN_GRAPH_* Fly secrets, same
credential the sheet-sync already uses). Transport is ``requests`` like
sync.py (lazy import; the ``http`` constructor arg injects a fake in tests).
"""
from __future__ import annotations

from datetime import datetime, timezone

GRAPH = "https://graph.microsoft.com/v1.0"

SEND_FROM = "matthias.silva@brisken.com"
DIRK_SMTP = "dirk.neumann@brisken.com"
ALLOWED_MAILBOXES = (DIRK_SMTP, SEND_FROM)
OWN_DOMAIN = "@brisken.com"


class NotAllowlisted(RuntimeError):
    """A mailbox outside the hard dirk+matthias allowlist was requested."""


class GraphSendError(RuntimeError):
    """Graph returned a non-success status for a mail operation."""

    def __init__(self, status_code: int, body: str):
        super().__init__(f"HTTP {status_code}: {body[:300]}")
        self.status_code = status_code


def assert_allowlisted(mailbox: str) -> str:
    mbx = (mailbox or "").strip().lower()
    if mbx not in ALLOWED_MAILBOXES:
        raise NotAllowlisted(f"mailbox not allowlisted: {mailbox!r}")
    return mbx


def _recipients(addrs: list[str] | None) -> list[dict]:
    return [{"emailAddress": {"address": a}} for a in (addrs or []) if a]


def build_message(send: dict) -> dict:
    """Claim payload -> Graph message resource (plain-text body, to/cc/bcc)."""
    return {
        "subject": send["subject"],
        "body": {"contentType": "Text", "content": send["body"]},
        "toRecipients": _recipients([send["to"]]),
        "ccRecipients": _recipients(send.get("cc")),
        "bccRecipients": _recipients(send.get("bcc")),
    }


def _addrs_of(recipients: list | None) -> list[str]:
    out = []
    for r in recipients or []:
        addr = ((r or {}).get("emailAddress") or {}).get("address")
        if addr:
            out.append(addr.strip().lower())
    return out


class GraphMailer:
    """Thin, allowlist-enforcing wrapper over the Graph mail endpoints."""

    def __init__(self, token: str | None = None, http=None):
        if http is None:
            import requests as http  # noqa: PLC0415 - lazy like sync.py
        self._http = http
        if token is None:
            from .sync import graph_token
            token = graph_token()
        self._headers = {"Authorization": f"Bearer {token}"}

    # -- low level ---------------------------------------------------------

    def _get(self, url: str) -> dict:
        r = self._http.get(url, headers=self._headers, timeout=60)
        if r.status_code >= 400:
            raise GraphSendError(r.status_code, r.text)
        return r.json()

    def _get_all(self, url: str) -> list[dict]:
        items: list[dict] = []
        while url:
            body = self._get(url)
            items.extend(body.get("value", []))
            url = body.get("@odata.nextLink")
        return items

    # -- send / draft ------------------------------------------------------

    def send_auto(self, send: dict) -> None:
        """Fire one auto-send. The POST is the irreversible moment - the
        caller journals graph_issued IMMEDIATELY before calling this.

        Auto mode sends ONLY as matthias.silva: a campaign misconfigured with
        another from_address is a config abort, never a send as Dirk."""
        from_addr = (send.get("from") or SEND_FROM).strip().lower()
        if from_addr != SEND_FROM:
            raise NotAllowlisted(
                f"auto-send is matthias-only; refusing from={from_addr!r}")
        mbx = assert_allowlisted(from_addr)
        r = self._http.post(
            f"{GRAPH}/users/{mbx}/sendMail",
            headers=self._headers,
            json={"message": build_message(send), "saveToSentItems": True},
            timeout=60,
        )
        # Graph acknowledges sendMail with 202 and an empty body.
        if r.status_code != 202:
            raise GraphSendError(r.status_code, r.text)

    def create_draft(self, mailbox: str, send: dict) -> dict:
        """Stage one draft in the mailbox's Drafts folder (draft-dirk mode,
        and draft-to-self test mode). Same dupe guard as the COM loader:
        an existing draft with this (subject, to) is returned, not doubled."""
        mbx = assert_allowlisted(mailbox)
        want_subj = (send["subject"] or "").strip()
        want_to = send["to"].strip().lower()
        existing = self._get_all(
            f"{GRAPH}/users/{mbx}/mailFolders/drafts/messages"
            "?$select=id,subject,toRecipients&$top=100")
        for it in existing:
            if (it.get("subject") or "").strip() == want_subj and \
                    want_to in _addrs_of(it.get("toRecipients")):
                return {"duplicate": True, "entry_id": it.get("id")}
        r = self._http.post(
            f"{GRAPH}/users/{mbx}/messages",
            headers=self._headers, json=build_message(send), timeout=60,
        )
        if r.status_code not in (200, 201):
            raise GraphSendError(r.status_code, r.text)
        return {"duplicate": False, "entry_id": r.json().get("id")}

    # -- sent-items evidence -------------------------------------------------

    def poll_sent(self, mailbox: str, since: datetime) -> list[dict]:
        """Sent items since the watermark -> plain dicts, same shape as
        com_mail.poll_sent (drafted-attempt correlation + reconcile)."""
        mbx = assert_allowlisted(mailbox)
        s = since.astimezone(timezone.utc).replace(microsecond=0) \
            .isoformat().replace("+00:00", "Z")
        items = self._get_all(
            f"{GRAPH}/users/{mbx}/mailFolders/sentitems/messages"
            "?$select=id,internetMessageId,subject,toRecipients,ccRecipients,"
            f"sentDateTime&$filter=sentDateTime ge {s}&$top=100")
        return [{
            "subject": (m.get("subject") or ""),
            "to_addrs": _addrs_of(m.get("toRecipients"))
            + _addrs_of(m.get("ccRecipients")),
            "ts": m.get("sentDateTime"),
            "imid": m.get("internetMessageId"),
            "entry_id": m.get("id"),
        } for m in items]

    def search_sent_for(self, mailbox: str, to_addr: str, subject: str,
                        since: datetime) -> dict | None:
        """Crash-reconcile evidence search: was this mail actually sent?"""
        for m in self.poll_sent(mailbox, since):
            if m["subject"].strip() == subject.strip() and \
                    any(to_addr.lower() in a for a in m["to_addrs"]):
                return m
        return None

    def readback_sent(self, mailbox: str, to_addr: str, subject: str,
                      since: datetime, budget_seconds: int = 45,
                      sleep=None) -> dict | None:
        """Find the just-sent mail in Sent Items (retry until budget; Graph
        materializes the saved copy with a small lag). Non-fatal on miss -
        the deterministic attempt_key is the idempotency anchor; the
        internetMessageId is enrichment."""
        import time as _time
        sleep = sleep or _time.sleep
        deadline = _time.monotonic() + budget_seconds
        while True:
            found = self.search_sent_for(mailbox, to_addr, subject, since)
            if found is not None or _time.monotonic() >= deadline:
                return found
            sleep(5)
