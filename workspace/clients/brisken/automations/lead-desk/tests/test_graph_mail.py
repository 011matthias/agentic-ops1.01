"""GraphMailer: allowlist enforcement, message building, send/draft/readback
semantics against a fake transport (no network)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from lead_desk import graph_mail
from lead_desk.graph_mail import (
    DIRK_SMTP, SEND_FROM, GraphMailer, GraphSendError, NotAllowlisted,
    build_message,
)

SINCE = datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc)


class FakeResp:
    def __init__(self, status_code=200, body=None, text=""):
        self.status_code = status_code
        self._body = body if body is not None else {}
        self.text = text

    def json(self):
        return self._body


class FakeHttp:
    """Requests-shaped fake: routes drafts-list / sentitems / sendMail /
    draft-create and records every call."""

    def __init__(self):
        self.calls: list[tuple[str, str, dict | None]] = []
        self.send_status = 202
        self.drafts: list[dict] = []
        self.sent: list[dict] = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append(("GET", url, None))
        if "/mailFolders/drafts/messages" in url:
            return FakeResp(200, {"value": self.drafts})
        if "/mailFolders/sentitems/messages" in url:
            return FakeResp(200, {"value": self.sent})
        return FakeResp(404, {}, "no route")

    def post(self, url, headers=None, json=None, timeout=None):
        self.calls.append(("POST", url, json))
        if url.endswith("/sendMail"):
            return FakeResp(self.send_status, {},
                            "" if self.send_status == 202 else "boom")
        if url.endswith("/messages"):
            return FakeResp(201, {"id": "draft-abc"})
        return FakeResp(404, {}, "no route")


def mailer(http=None) -> tuple[GraphMailer, FakeHttp]:
    http = http or FakeHttp()
    return GraphMailer(token="tok", http=http), http


SEND = {"to": "lead@example.com", "cc": ["dirk.neumann@brisken.com"],
        "bcc": ["s9hitl_pv69mu@mails4.zohocrm.com"],
        "subject": "Hello", "body": "Body text", "from": SEND_FROM}


def test_build_message_shape():
    msg = build_message(SEND)
    assert msg["subject"] == "Hello"
    assert msg["body"] == {"contentType": "Text", "content": "Body text"}
    assert msg["toRecipients"] == [{"emailAddress": {"address": "lead@example.com"}}]
    assert msg["ccRecipients"][0]["emailAddress"]["address"].startswith("dirk")
    assert msg["bccRecipients"][0]["emailAddress"]["address"].startswith("s9hitl")


def test_build_message_no_cc_bcc():
    msg = build_message({"to": "a@b.co", "subject": "s", "body": "b"})
    assert msg["ccRecipients"] == [] and msg["bccRecipients"] == []


def test_send_auto_posts_sendmail_as_matthias():
    m, http = mailer()
    m.send_auto(SEND)
    method, url, body = http.calls[-1]
    assert method == "POST" and url.endswith(f"/users/{SEND_FROM}/sendMail")
    assert body["saveToSentItems"] is True
    assert body["message"]["subject"] == "Hello"


def test_send_auto_never_sends_as_dirk():
    m, http = mailer()
    with pytest.raises(NotAllowlisted):
        m.send_auto(dict(SEND, **{"from": DIRK_SMTP}))
    assert http.calls == []  # refused before any request


def test_send_auto_refuses_unknown_from():
    m, http = mailer()
    with pytest.raises(NotAllowlisted):
        m.send_auto(dict(SEND, **{"from": "someone@else.com"}))
    assert http.calls == []


def test_send_auto_raises_on_non_202():
    m, http = mailer()
    http.send_status = 400
    with pytest.raises(GraphSendError) as exc:
        m.send_auto(SEND)
    assert exc.value.status_code == 400


def test_create_draft_only_allowlisted_mailboxes():
    m, http = mailer()
    with pytest.raises(NotAllowlisted):
        m.create_draft("attacker@evil.com", SEND)
    assert http.calls == []


def test_create_draft_creates_in_dirks_mailbox():
    m, http = mailer()
    res = m.create_draft(DIRK_SMTP, SEND)
    assert res == {"duplicate": False, "entry_id": "draft-abc"}
    method, url, body = http.calls[-1]
    assert method == "POST" and url.endswith(f"/users/{DIRK_SMTP}/messages")
    assert body["subject"] == "Hello"


def test_create_draft_dupe_guard():
    m, http = mailer()
    http.drafts = [{"id": "old-1", "subject": " Hello ",
                    "toRecipients": [{"emailAddress": {"address": "LEAD@example.com"}}]}]
    res = m.create_draft(DIRK_SMTP, SEND)
    assert res == {"duplicate": True, "entry_id": "old-1"}
    assert not any(c[0] == "POST" for c in http.calls)


def test_poll_sent_maps_fields_and_asserts_allowlist():
    m, http = mailer()
    http.sent = [{"id": "m1", "internetMessageId": "<im1>", "subject": "Hello",
                  "sentDateTime": "2026-07-15T09:01:00Z",
                  "toRecipients": [{"emailAddress": {"address": "Lead@example.com"}}],
                  "ccRecipients": [{"emailAddress": {"address": "cc@x.co"}}]}]
    rows = m.poll_sent(SEND_FROM, SINCE)
    assert rows == [{"subject": "Hello", "to_addrs": ["lead@example.com", "cc@x.co"],
                     "ts": "2026-07-15T09:01:00Z", "imid": "<im1>",
                     "entry_id": "m1"}]
    with pytest.raises(NotAllowlisted):
        m.poll_sent("other@brisken.com", SINCE)


def test_search_sent_for_matches_subject_and_recipient():
    m, http = mailer()
    http.sent = [{"id": "m1", "internetMessageId": "<im1>", "subject": "Hello",
                  "sentDateTime": "2026-07-15T09:01:00Z",
                  "toRecipients": [{"emailAddress": {"address": "lead@example.com"}}]}]
    hit = m.search_sent_for(SEND_FROM, "lead@example.com", "Hello", SINCE)
    assert hit and hit["imid"] == "<im1>"
    assert m.search_sent_for(SEND_FROM, "other@x.co", "Hello", SINCE) is None
    assert m.search_sent_for(SEND_FROM, "lead@example.com", "Nope", SINCE) is None


def test_readback_sent_returns_none_when_budget_exhausted():
    m, http = mailer()
    assert m.readback_sent(SEND_FROM, "lead@example.com", "Hello", SINCE,
                           budget_seconds=0) is None


def test_readback_sent_finds_immediately_without_sleep():
    m, http = mailer()
    http.sent = [{"id": "m1", "internetMessageId": "<im1>", "subject": "Hello",
                  "sentDateTime": "2026-07-15T09:01:00Z",
                  "toRecipients": [{"emailAddress": {"address": "lead@example.com"}}]}]
    slept = []
    hit = m.readback_sent(SEND_FROM, "lead@example.com", "Hello", SINCE,
                          budget_seconds=45, sleep=slept.append)
    assert hit["imid"] == "<im1>" and slept == []


def test_assert_allowlisted_normalizes_case():
    assert graph_mail.assert_allowlisted(" Matthias.Silva@BRISKEN.com ") == SEND_FROM
