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

import re
from datetime import datetime, timezone

GRAPH = "https://graph.microsoft.com/v1.0"

SEND_FROM = "matthias.silva@brisken.com"
DIRK_SMTP = "dirk.neumann@brisken.com"
ALLOWED_MAILBOXES = (DIRK_SMTP, SEND_FROM)
OWN_DOMAIN = "@brisken.com"

# Recipient domains that must NEVER receive an outbound send, regardless of
# approval (a competitor we hold, and our own internal domain). Canonical
# home of the immutable floor: web/cadence.py re-exports it for the claim
# path and the worker backstop, and send_draft_by_id refuses it directly.
# Mirrors the hard @sap.com deny in the ga_send_wave.py guard pattern
# (rule_brisken_graph_send_by_id).
DEFAULT_DENY_DOMAINS = ("sap.com", "brisken.com")


class NotAllowlisted(RuntimeError):
    """A mailbox outside the hard dirk+matthias allowlist was requested."""


class GraphSendError(RuntimeError):
    """Graph returned a non-success status for a mail operation."""

    def __init__(self, status_code: int, body: str):
        super().__init__(f"HTTP {status_code}: {body[:300]}")
        self.status_code = status_code


class DraftGuardError(RuntimeError):
    """A pre-send guard refused the operation (wrong recipient, non-draft,
    denied domain, subject drift). Config problem the caller must fix -
    distinct from GraphSendError so callers can classify config vs
    transient."""


class GraphRetryError(RuntimeError):
    """Graph throttled or was briefly unavailable (429/503) on a
    truth-scan read. Distinct from GraphSendError so the caller can apply
    retry POLICY (the deep scan's bounded backoff) without swallowing
    genuine failures."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
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


_REPLY_PREFIX_RE = re.compile(r"^(re|aw|wg|fwd|fw)\s*:\s*", re.IGNORECASE)


def _norm_subject(s: str) -> str:
    """Subject comparison key: case-folded, all leading reply/forward
    prefixes stripped (Exchange uppercases RE:, German Outlook writes
    AW:/WG:), applied repeatedly until stable."""
    out = (s or "").strip()
    while True:
        nxt = _REPLY_PREFIX_RE.sub("", out).strip()
        if nxt == out:
            return out.casefold()
        out = nxt


def _merge_above_quote(html_new: str, html_history: str) -> str:
    """Reply body assembly: the new HTML in its own <div>, the quoted
    history untouched below it. html_new is already HTML - no escaping,
    no parsing. Dumb and predictable on purpose."""
    return f"<div>{html_new}</div>{html_history or ''}"


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

    # -- message reads -----------------------------------------------------

    def get_message(self, mailbox: str, message_id: str) -> dict:
        """One message by id, with the correlation + guard fields
        (isDraft/recipients/conversationId/internetMessageId)."""
        mbx = assert_allowlisted(mailbox)
        return self._get(
            f"{GRAPH}/users/{mbx}/messages/{message_id}"
            "?$select=id,subject,isDraft,toRecipients,ccRecipients,"
            "bccRecipients,conversationId,internetMessageId")

    def find_message_by_imid(self, mailbox: str,
                             internet_message_id: str) -> dict | None:
        """Resolve a message anywhere in the mailbox by internetMessageId
        (the bare /messages collection spans all mail folders, so a filed
        or archived anchor still resolves). Exact eq filter only -
        contains() + $orderby trips Graph's InefficientFilter."""
        mbx = assert_allowlisted(mailbox)
        imid = (internet_message_id or "").replace("'", "''")
        items = self._get_all(
            f"{GRAPH}/users/{mbx}/messages"
            f"?$filter=internetMessageId eq '{imid}'"
            "&$select=id,conversationId,subject,toRecipients,from")
        return items[0] if items else None

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

    def send_draft_by_id(self, mailbox: str, message_id: str, *,
                         expect_to: str,
                         expect_subject: str | None = None) -> dict:
        """Send ONE explicitly identified draft (rule_brisken_graph_send_by_id:
        never folder-level, never broad-filter). Re-fetches the message and
        REFUSES unless it is still a draft addressed solely to expect_to,
        outside the deny floor, with the expected subject. Returns the
        PRE-send snapshot: the message id changes when Graph moves the mail
        to Sent Items; internetMessageId + conversationId are the stable
        correlators."""
        mbx = assert_allowlisted(mailbox)
        msg = self.get_message(mbx, message_id)
        if not msg.get("isDraft"):
            raise DraftGuardError(f"not a draft: {message_id}")
        want_to = (expect_to or "").strip().lower()
        to_addrs = _addrs_of(msg.get("toRecipients"))
        if to_addrs != [want_to]:
            raise DraftGuardError(
                f"draft must be addressed solely to {want_to!r}; "
                f"got {to_addrs!r}")
        for addr in [want_to, *_addrs_of(msg.get("ccRecipients"))]:
            if addr.rsplit("@", 1)[-1] in DEFAULT_DENY_DOMAINS:
                raise DraftGuardError(
                    f"recipient domain hard-denied: {addr}")
        if expect_subject is not None and \
                _norm_subject(msg.get("subject") or "") != \
                _norm_subject(expect_subject):
            raise DraftGuardError(
                f"subject mismatch: {msg.get('subject')!r} "
                f"vs expected {expect_subject!r}")
        r = self._http.post(
            f"{GRAPH}/users/{mbx}/messages/{message_id}/send",
            headers=self._headers, timeout=60)
        # Graph documents 202 for /send; tolerate the empty-success variants.
        if r.status_code not in (200, 202, 204):
            raise GraphSendError(r.status_code, r.text)
        return {"internet_message_id": msg.get("internetMessageId"),
                "conversation_id": msg.get("conversationId"),
                "subject": msg.get("subject")}

    def create_reply_draft(self, mailbox: str, anchor_id: str, *, to: str,
                           html_body: str, cc: list[str] | None = None,
                           bcc: list[str] | None = None) -> dict:
        """Reply draft threaded off one of our OWN sent messages (the
        anchor). createReplyAll, not createReply: a plain reply to our own
        sent mail would address ourselves - and threading headers cannot be
        retrofitted by PATCH, only a reply created off the anchor threads
        correctly. Same (subject, to) dupe guard as create_draft. On a
        failed readiness check the draft is NOT deleted - it stays
        inspectable in Drafts."""
        mbx = assert_allowlisted(mailbox)
        anchor = self.get_message(mbx, anchor_id)
        anchor_subj = _norm_subject(anchor.get("subject") or "")
        want_to = (to or "").strip().lower()
        existing = self._get_all(
            f"{GRAPH}/users/{mbx}/mailFolders/drafts/messages"
            "?$select=id,subject,toRecipients&$top=100")
        for it in existing:
            if _norm_subject(it.get("subject") or "") == anchor_subj and \
                    _addrs_of(it.get("toRecipients")) == [want_to]:
                return {"duplicate": True, "entry_id": it.get("id")}
        r = self._http.post(
            f"{GRAPH}/users/{mbx}/messages/{anchor_id}/createReplyAll",
            headers=self._headers, timeout=60)
        if r.status_code not in (200, 201):
            raise GraphSendError(r.status_code, r.text)
        draft_id = r.json().get("id")
        cur = self._get(f"{GRAPH}/users/{mbx}/messages/{draft_id}"
                        "?$select=id,body")
        history = ((cur.get("body") or {}).get("content")) or ""
        r = self._http.patch(
            f"{GRAPH}/users/{mbx}/messages/{draft_id}",
            headers=self._headers,
            json={
                "body": {"contentType": "HTML",
                         "content": _merge_above_quote(html_body, history)},
                # Replace wholesale: createReplyAll pre-fills ourselves.
                "toRecipients": _recipients([to]),
                "ccRecipients": _recipients(cc),
                "bccRecipients": _recipients(bcc),
            },
            timeout=60)
        if r.status_code >= 400:
            raise GraphSendError(r.status_code, r.text)
        ready = self.get_message(mbx, draft_id)
        subj = ready.get("subject") or ""
        if _addrs_of(ready.get("toRecipients")) != [want_to]:
            raise DraftGuardError(
                f"reply draft {draft_id} not addressed solely to "
                f"{want_to!r} after patch; left in Drafts")
        if not _REPLY_PREFIX_RE.match(subj) or \
                _norm_subject(subj) != anchor_subj:
            raise DraftGuardError(
                f"reply draft {draft_id} subject {subj!r} does not reply to "
                f"anchor {anchor.get('subject')!r}; left in Drafts")
        if ready.get("conversationId") != anchor.get("conversationId"):
            raise DraftGuardError(
                f"reply draft {draft_id} left the anchor's conversation; "
                "left in Drafts")
        return {"entry_id": draft_id,
                "conversation_id": ready.get("conversationId"),
                "subject": subj, "duplicate": False}

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
        """Crash-reconcile evidence search: was this mail actually sent?
        Subjects compare via _norm_subject (a superset of the old exact
        match) so a reply step's 'RE: '-prefixed wire subject still matches
        the journaled subject."""
        want = _norm_subject(subject)
        for m in self.poll_sent(mailbox, since):
            if _norm_subject(m["subject"]) == want and \
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

    # -- folder-walk truth scan (read-only) ---------------------------------

    def list_mail_folders(self, mailbox: str) -> list[dict]:
        """The full recursive folder tree (slash-joined display paths),
        empty folders skipped. Ported from tools/brisken-outreach-truth.py
        list_folders: the ALL-FOLDERS walk is what finds a send Dirk FILED
        out of Sent Items into a per-company folder (the aggregate
        /messages endpoint false-negatived 21/24 real 2026-07-21 sends)."""
        mbx = assert_allowlisted(mailbox)
        out: list[dict] = []

        def walk(fid: str | None, prefix: str) -> None:
            base = (f"{GRAPH}/users/{mbx}/mailFolders/{fid}/childFolders"
                    if fid else f"{GRAPH}/users/{mbx}/mailFolders")
            for f in self._get_all(
                    f"{base}?$top=100"
                    "&$select=id,displayName,totalItemCount,childFolderCount"):
                path = f"{prefix}{f.get('displayName', '?')}"
                if f.get("totalItemCount"):
                    out.append({"id": f["id"], "path": path,
                                "total_item_count": f["totalItemCount"]})
                if f.get("childFolderCount", 0):
                    walk(f["id"], f"{path} / ")

        walk(None, "")
        return out

    def pull_folder_outbound(self, mailbox: str, folder_id: str,
                             since_iso: str) -> list[dict]:
        """Messages in ONE folder sent BY the mailbox owner since the bound
        (``isDraft eq false``), $select minimal. The per-folder from==owner
        filter keeps each response tiny, so the full-tree walk stays cheap
        (tools/brisken-outreach-truth.py pull_outbound). 429/503 surface as
        GraphRetryError; the retry POLICY lives in the caller."""
        mbx = assert_allowlisted(mailbox)
        try:
            items = self._get_all(
                f"{GRAPH}/users/{mbx}/mailFolders/{folder_id}/messages"
                f"?$filter=from/emailAddress/address eq '{mbx}' "
                f"and sentDateTime ge {since_iso} and isDraft eq false"
                "&$select=id,internetMessageId,subject,toRecipients,"
                "ccRecipients,sentDateTime&$top=100")
        except GraphSendError as exc:
            if exc.status_code in (429, 503):
                raise GraphRetryError(exc.status_code, str(exc)) from exc
            raise
        return [{
            "id": m.get("id"),
            "internet_message_id": m.get("internetMessageId"),
            "to": _addrs_of(m.get("toRecipients")),
            "cc": _addrs_of(m.get("ccRecipients")),
            "subject": m.get("subject"),
            "sent_at": m.get("sentDateTime"),
            "folder_id": folder_id,
        } for m in items]
