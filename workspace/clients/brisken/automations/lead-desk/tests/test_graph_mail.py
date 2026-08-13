"""GraphMailer: allowlist enforcement, message building, send/draft/readback
semantics against a fake transport (no network)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from lead_desk import graph_mail
from lead_desk.graph_mail import (
    DIRK_SMTP, SEND_FROM, DraftGuardError, GraphMailer, GraphSendError,
    NotAllowlisted, build_message,
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
    draft-create / message-by-id / imid-filter / createReplyAll / send-by-id
    / patch and records every call."""

    def __init__(self):
        self.calls: list[tuple[str, str, dict | None]] = []
        self.send_status = 202
        self.drafts: list[dict] = []
        self.sent: list[dict] = []
        self.messages: dict[str, dict] = {}   # id -> message resource
        self.by_imid: dict[str, dict] = {}    # imid -> message resource
        self.reply_draft: dict | None = None  # returned by createReplyAll
        self.draft_send_status = 202

    def get(self, url, headers=None, timeout=None):
        self.calls.append(("GET", url, None))
        if "/mailFolders/drafts/messages" in url:
            return FakeResp(200, {"value": self.drafts})
        if "/mailFolders/sentitems/messages" in url:
            return FakeResp(200, {"value": self.sent})
        if "$filter=internetMessageId eq '" in url:
            lit = url.split("$filter=internetMessageId eq '", 1)[1]
            lit = lit.split("'&", 1)[0].replace("''", "'")
            hit = self.by_imid.get(lit)
            return FakeResp(200, {"value": [hit] if hit else []})
        if "/messages/" in url:
            mid = url.rsplit("/messages/", 1)[1].split("?", 1)[0]
            msg = self.messages.get(mid)
            return FakeResp(200, msg) if msg else FakeResp(404, {}, "no msg")
        return FakeResp(404, {}, "no route")

    def post(self, url, headers=None, json=None, timeout=None):
        self.calls.append(("POST", url, json))
        if url.endswith("/sendMail"):
            return FakeResp(self.send_status, {},
                            "" if self.send_status == 202 else "boom")
        if url.endswith("/send"):
            return FakeResp(self.draft_send_status, {},
                            "" if self.draft_send_status == 202 else "boom")
        if url.endswith("/createReplyAll"):
            if self.reply_draft is None:
                return FakeResp(404, {}, "no reply draft staged")
            self.messages[self.reply_draft["id"]] = self.reply_draft
            return FakeResp(201, self.reply_draft)
        if url.endswith("/messages"):
            return FakeResp(201, {"id": "draft-abc"})
        return FakeResp(404, {}, "no route")

    def patch(self, url, headers=None, json=None, timeout=None):
        self.calls.append(("PATCH", url, json))
        mid = url.rsplit("/messages/", 1)[1].split("?", 1)[0]
        msg = self.messages.get(mid)
        if msg is None:
            return FakeResp(404, {}, "no msg")
        for key in ("body", "toRecipients", "ccRecipients", "bccRecipients"):
            if key in (json or {}):
                msg[key] = json[key]
        return FakeResp(200, msg)


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


# -- send-by-id / reply-draft primitives -----------------------------------


def _msg(mid, subject="Hello", to=("lead@example.com",), cc=(), *,
         is_draft=True, conv="conv-1", imid=None):
    return {"id": mid, "subject": subject, "isDraft": is_draft,
            "conversationId": conv,
            "internetMessageId": imid or f"<{mid}@x>",
            "toRecipients": [{"emailAddress": {"address": a}} for a in to],
            "ccRecipients": [{"emailAddress": {"address": a}} for a in cc]}


def test_send_draft_by_id_posts_send_endpoint_after_refetch():
    m, http = mailer()
    http.messages["d1"] = _msg("d1", to=("Lead@example.com",))
    res = m.send_draft_by_id(SEND_FROM, "d1", expect_to="lead@example.com",
                             expect_subject="RE: hello")
    assert res == {"internet_message_id": "<d1@x>",
                   "conversation_id": "conv-1", "subject": "Hello"}
    method, url, _ = http.calls[0]
    assert method == "GET" and "/messages/d1?" in url  # re-fetch first
    method, url, _ = http.calls[-1]
    assert method == "POST" and \
        url == f"{graph_mail.GRAPH}/users/{SEND_FROM}/messages/d1/send"


def test_send_draft_by_id_refuses_non_draft_and_wrong_sole_recipient():
    m, http = mailer()
    http.messages["d1"] = _msg("d1", is_draft=False)
    with pytest.raises(DraftGuardError, match="not a draft"):
        m.send_draft_by_id(SEND_FROM, "d1", expect_to="lead@example.com")
    http.messages["d2"] = _msg(
        "d2", to=("lead@example.com", "second@example.com"))
    with pytest.raises(DraftGuardError, match="solely"):
        m.send_draft_by_id(SEND_FROM, "d2", expect_to="lead@example.com")
    http.messages["d3"] = _msg("d3", to=("other@example.com",))
    with pytest.raises(DraftGuardError, match="solely"):
        m.send_draft_by_id(SEND_FROM, "d3", expect_to="lead@example.com")
    assert not any(c[0] == "POST" for c in http.calls)


def test_send_draft_by_id_refuses_denied_domain_recipient():
    m, http = mailer()
    http.messages["d1"] = _msg("d1", to=("treasury@sap.com",))
    with pytest.raises(DraftGuardError, match="hard-denied"):
        m.send_draft_by_id(SEND_FROM, "d1", expect_to="treasury@sap.com")
    http.messages["d2"] = _msg("d2", cc=("cc@sap.com",))
    with pytest.raises(DraftGuardError, match="hard-denied"):
        m.send_draft_by_id(SEND_FROM, "d2", expect_to="lead@example.com")
    assert not any(c[0] == "POST" for c in http.calls)


def test_send_draft_by_id_subject_mismatch_refuses():
    m, http = mailer()
    http.messages["d1"] = _msg("d1", subject="Howdy")
    with pytest.raises(DraftGuardError, match="subject mismatch"):
        m.send_draft_by_id(SEND_FROM, "d1", expect_to="lead@example.com",
                           expect_subject="Hello")
    assert not any(c[0] == "POST" for c in http.calls)


def test_find_message_by_imid_uses_exact_filter_and_escapes_quotes():
    m, http = mailer()
    http.by_imid["<it's@x>"] = {"id": "m9", "conversationId": "conv-9",
                                "subject": "Hello"}
    hit = m.find_message_by_imid(SEND_FROM, "<it's@x>")
    assert hit and hit["id"] == "m9"
    _, url, _ = http.calls[-1]
    assert "$filter=internetMessageId eq '<it''s@x>'" in url
    assert "contains(" not in url and "$orderby" not in url
    assert f"/users/{SEND_FROM}/messages?" in url  # mailbox-wide, no folder
    assert m.find_message_by_imid(SEND_FROM, "<none@x>") is None


def test_create_reply_draft_uses_createreplyall_and_patches_to_bcc_body():
    m, http = mailer()
    http.messages["a1"] = _msg("a1", is_draft=False)
    http.reply_draft = _msg(
        "r1", subject="RE: Hello", to=(SEND_FROM, DIRK_SMTP))
    http.reply_draft["body"] = {"contentType": "HTML",
                                "content": "<blockquote>old</blockquote>"}
    res = m.create_reply_draft(
        SEND_FROM, "a1", to="lead@example.com", html_body="<p>New</p>",
        bcc=["s9hitl_pv69mu@mails4.zohocrm.com"])
    assert res == {"entry_id": "r1", "conversation_id": "conv-1",
                   "subject": "RE: Hello", "duplicate": False}
    assert ("POST",
            f"{graph_mail.GRAPH}/users/{SEND_FROM}/messages/a1/createReplyAll",
            None) in http.calls
    patch = next(c for c in http.calls if c[0] == "PATCH")
    assert patch[1].endswith("/messages/r1")
    assert patch[2]["toRecipients"] == \
        [{"emailAddress": {"address": "lead@example.com"}}]
    assert patch[2]["ccRecipients"] == []
    assert patch[2]["bccRecipients"][0]["emailAddress"]["address"] \
        .startswith("s9hitl")
    assert patch[2]["body"]["contentType"] == "HTML"


def test_create_reply_draft_merges_body_above_quoted_history():
    m, http = mailer()
    http.messages["a1"] = _msg("a1", is_draft=False)
    http.reply_draft = _msg("r1", subject="RE: Hello", to=(SEND_FROM,))
    http.reply_draft["body"] = {"contentType": "HTML",
                                "content": "<blockquote>old</blockquote>"}
    m.create_reply_draft(SEND_FROM, "a1", to="lead@example.com",
                         html_body="<p>New</p>")
    patch = next(c for c in http.calls if c[0] == "PATCH")
    assert patch[2]["body"]["content"] == \
        "<div><p>New</p></div><blockquote>old</blockquote>"


def test_create_reply_draft_readiness_mismatch_raises_draft_guard():
    m, http = mailer()
    http.messages["a1"] = _msg("a1", is_draft=False, conv="conv-1")
    # PATCH cannot move a draft between conversations - a drifted
    # conversationId must fail readiness, and the draft stays in Drafts.
    http.reply_draft = _msg("r1", subject="RE: Hello", to=(SEND_FROM,),
                            conv="conv-OTHER")
    http.reply_draft["body"] = {"contentType": "HTML", "content": "old"}
    with pytest.raises(DraftGuardError, match="left in Drafts"):
        m.create_reply_draft(SEND_FROM, "a1", to="lead@example.com",
                             html_body="<p>New</p>")
    assert "r1" in http.messages  # never deleted, stays inspectable
    assert not any(c[0] == "DELETE" for c in http.calls)


def test_create_reply_draft_dupe_guard_matches_re_normalized_subject():
    m, http = mailer()
    http.messages["a1"] = _msg("a1", is_draft=False)  # anchor subject Hello
    http.drafts = [{"id": "old-9", "subject": "RE: hello",
                    "toRecipients": [{"emailAddress":
                                      {"address": "Lead@example.com"}}]}]
    res = m.create_reply_draft(SEND_FROM, "a1", to="lead@example.com",
                               html_body="<p>New</p>")
    assert res == {"duplicate": True, "entry_id": "old-9"}
    assert not any(c[0] == "POST" for c in http.calls)


def test_new_primitives_refuse_unallowlisted_mailbox():
    m, http = mailer()
    for attempt in (
            lambda: m.get_message("attacker@evil.com", "m1"),
            lambda: m.find_message_by_imid("attacker@evil.com", "<i@x>"),
            lambda: m.send_draft_by_id("attacker@evil.com", "m1",
                                       expect_to="lead@example.com"),
            lambda: m.create_reply_draft("attacker@evil.com", "m1",
                                         to="lead@example.com",
                                         html_body="<p>x</p>")):
        with pytest.raises(NotAllowlisted):
            attempt()
    assert http.calls == []  # refused before any request


def test_norm_subject_strips_stacked_prefixes():
    assert graph_mail._norm_subject("RE: AW: Re: x") == "x"
    assert graph_mail._norm_subject(" WG: Fwd: FW:  Budget 2026 ") == \
        "budget 2026"
    assert graph_mail._norm_subject("Regarding: x") == "regarding: x"
    assert graph_mail._norm_subject("Hello") == "hello"


def test_deny_floor_alias_unchanged_in_cadence():
    from lead_desk.web import cadence
    assert cadence.DEFAULT_DENY_DOMAINS is graph_mail.DEFAULT_DENY_DOMAINS
    assert graph_mail.DEFAULT_DENY_DOMAINS == ("sap.com", "brisken.com")
