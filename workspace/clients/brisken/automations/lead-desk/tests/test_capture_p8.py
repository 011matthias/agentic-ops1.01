"""P8: capture-worker readiness - auto-reply/NDR classification, calendar
forward horizon, multi-mailbox allowlist, and the poll() query construction."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from lead_desk import capture
from lead_desk.capture import (
    ALLOWED_MAILBOXES, inbox_to_payloads, poll)
from lead_desk.web.service import ingest_event, now_iso
from lead_desk.web.store import ContactStore

MBX = "dirk.neumann@brisken.com"


# --- #2 auto-reply / OOO downgrade -------------------------------------------

def test_auto_reply_by_header_becomes_note():
    out = inbox_to_payloads([{
        "internetMessageId": "<a1>", "subject": "Out of office",
        "receivedDateTime": "2026-07-16T08:00:00Z",
        "from": {"emailAddress": {"address": "lead@acme.com"}},
        "internetMessageHeaders": [{"name": "Auto-Submitted", "value": "auto-replied"}],
    }], MBX)
    assert len(out) == 1 and out[0]["type"] == "note"        # NOT 'reply' -> cadence not halted


def test_auto_reply_by_subject_becomes_note():
    out = inbox_to_payloads([{
        "internetMessageId": "<a2>", "subject": "Automatische Antwort: MDH",
        "from": {"emailAddress": {"address": "lead@acme.com"}},
    }], MBX)
    assert out[0]["type"] == "note"


def test_genuine_reply_still_reply():
    out = inbox_to_payloads([{
        "internetMessageId": "<r>", "subject": "RE: MDH", "receivedDateTime": "2026-07-16T08:00:00Z",
        "from": {"emailAddress": {"address": "lead@acme.com"}},
    }], MBX)
    assert out[0]["type"] == "reply"


# --- #3 NDR -> bounce keyed on the failed recipient ---------------------------

def test_ndr_becomes_bounce_for_failed_recipient():
    out = inbox_to_payloads([{
        "internetMessageId": "<ndr>", "subject": "Undeliverable: MDH follow-up",
        "receivedDateTime": "2026-07-16T08:00:00Z",
        "from": {"emailAddress": {"address": "postmaster@brisken.com"}},
        "bodyPreview": "Your message to gone@deadco.com could not be delivered.",
    }], MBX)
    assert len(out) == 1
    assert out[0]["type"] == "bounce" and out[0]["email"] == "gone@deadco.com"


def test_bounce_payload_auto_suppresses_via_sink(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        s.upsert_contact({"contact_id": "c1", "natural_key": "gone@deadco.com",
                          "email": "gone@deadco.com"}, now=now_iso())
        ingest_event(s, {"email": "gone@deadco.com", "type": "bounce"})
        assert s.get_contact("c1")["suppressed"] == 1
        assert s.get_contact("c1")["suppress_reason"] == "bounced"


# --- #1 calendar forward horizon + poll() query ------------------------------

class _FakeGraph:
    def __init__(self):
        self.urls: list[str] = []

    def get_all(self, url):
        self.urls.append(url)
        return []


def test_poll_calendar_reaches_forward_horizon():
    g = _FakeGraph()
    until = datetime(2026, 7, 16, tzinfo=timezone.utc)
    poll(g, MBX, until, until)
    cal = next(u for u in g.urls if "calendarView" in u)
    # endDateTime is ~60 days after `until`, not `until` itself
    assert "endDateTime=2026-09-14" in cal
    assert "startDateTime=2026-07-16" in cal


# --- #4 mailbox allowlist -----------------------------------------------------

def test_poll_rejects_non_allowlisted_mailbox():
    with pytest.raises(AssertionError):
        poll(_FakeGraph(), "attacker@evil.com", datetime.now(timezone.utc),
             datetime.now(timezone.utc))


def test_main_rejects_no_allowlisted_mailbox(monkeypatch):
    for k in ("LEAD_DESK_TENANT_ID", "LEAD_DESK_CLIENT_ID", "LEAD_DESK_CLIENT_SECRET"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setenv("LEAD_DESK_MAILBOXES", "attacker@evil.com")
    monkeypatch.delenv("LEAD_DESK_MAILBOX", raising=False)
    assert capture.main([]) == 2      # refuses; no allowlisted mailbox


def test_allowlist_is_dirk_and_matthias():
    assert ALLOWED_MAILBOXES == ("dirk.neumann@brisken.com", "matthias.silva@brisken.com")
