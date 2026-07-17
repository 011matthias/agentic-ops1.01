"""Phase 2 capture: the Graph -> /events mapping is pure and unit-tested without
network. Idempotency keys (internetMessageId / iCalUId) are the sink's dedup basis."""
from __future__ import annotations

from lead_desk.capture import (
    calendar_to_payloads, inbox_to_payloads, sent_to_payloads,
)


def test_sent_message_maps_to_outbound_per_recipient():
    msgs = [{
        "internetMessageId": "<m1@brisken.com>",
        "subject": "MDH follow-up",
        "sentDateTime": "2026-07-11T09:00:00Z",
        "toRecipients": [{"emailAddress": {"address": "Lead@Acme.com"}}],
        "ccRecipients": [{"emailAddress": {"address": "cc@acme.com"}}],
    }]
    out = sent_to_payloads(msgs)
    assert len(out) == 2
    assert {p["email"] for p in out} == {"lead@acme.com", "cc@acme.com"}
    p = out[0]
    assert p["direction"] == "outbound" and p["type"] == "sent" and p["channel"] == "email"
    assert p["internet_message_id"] == "<m1@brisken.com>"      # idempotency key
    assert p["occurred_at"] == "2026-07-11T09:00:00Z"


def test_inbox_message_maps_to_inbound_reply_from_sender():
    msgs = [{
        "internetMessageId": "<r1@acme.com>",
        "subject": "RE: MDH follow-up",
        "receivedDateTime": "2026-07-12T08:00:00Z",
        "from": {"emailAddress": {"address": "Lead@Acme.com"}},
    }]
    out = inbox_to_payloads(msgs)
    assert len(out) == 1
    p = out[0]
    assert p["email"] == "lead@acme.com" and p["direction"] == "inbound" and p["type"] == "reply"
    assert p["internet_message_id"] == "<r1@acme.com>"


def test_inbox_message_without_sender_is_skipped():
    assert inbox_to_payloads([{"internetMessageId": "<x>", "from": {}}]) == []


def test_calendar_event_maps_to_booked_and_excludes_owner():
    mailbox = "dirk.neumann@brisken.com"
    events = [{
        "iCalUId": "cal-uid-1",
        "subject": "Rome demo",
        "start": {"dateTime": "2026-07-20T14:00:00", "timeZone": "UTC"},
        "attendees": [
            {"emailAddress": {"address": "dirk.neumann@brisken.com"}},   # owner, excluded
            {"emailAddress": {"address": "Lead@Acme.com"}},
        ],
    }]
    out = calendar_to_payloads(events, mailbox)
    assert len(out) == 1
    p = out[0]
    assert p["email"] == "lead@acme.com" and p["type"] == "booked" and p["channel"] == "meeting"
    assert p["ext_key"] == "cal-cal-uid-1"      # stable dedup key


def test_empty_inputs_produce_no_payloads():
    assert sent_to_payloads([]) == []
    assert inbox_to_payloads([]) == []
    assert calendar_to_payloads([], "dirk.neumann@brisken.com") == []
