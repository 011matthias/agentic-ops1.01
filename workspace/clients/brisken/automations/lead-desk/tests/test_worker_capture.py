"""Capture mapping: inbox item dicts -> /events payloads (COM-free)."""
from lead_desk.worker import com_mail
from lead_desk.worker.capture_local import build_payloads

WATCH = {"jane@acme.com", "kai@corp.de"}


def _item(**kw):
    base = {"message_class": "IPM.Note", "subject": "Re: hello",
            "sender": "jane@acme.com", "ts": "2026-07-15T10:00:00+02:00",
            "imid": "<m1@acme>", "body_head": "Thanks, interested."}
    base.update(kw)
    return base


def test_watched_sender_becomes_reply_payload():
    payloads = build_payloads([_item()], WATCH)
    assert len(payloads) == 1
    p = payloads[0]
    assert p["type"] == "reply" and p["direction"] == "inbound"
    assert p["email"] == "jane@acme.com"
    assert p["internet_message_id"] == "<m1@acme>"
    assert p["occurred_at"] == "2026-07-15T10:00:00+02:00"


def test_unwatched_sender_is_dropped_locally():
    payloads = build_payloads([_item(sender="random@spam.io")], WATCH)
    assert payloads == []


def test_ndr_message_class_yields_bounce_for_watched_recipients():
    ndr = _item(message_class="REPORT.IPM.Note.NDR",
                subject="Undeliverable: hello",
                sender="postmaster@brisken.com",
                body_head="Delivery failed for kai@corp.de and other@else.com")
    payloads = build_payloads([ndr], WATCH)
    assert len(payloads) == 1
    p = payloads[0]
    assert p["type"] == "bounce" and p["email"] == "kai@corp.de"


def test_bounce_subject_heuristic_without_ndr_class():
    ndr = _item(message_class="IPM.Note",
                subject="Mail delivery failed: returning message",
                sender="mailer-daemon@x.com",
                body_head="jane@acme.com could not be reached")
    payloads = build_payloads([ndr], WATCH)
    assert [p["type"] for p in payloads] == ["bounce"]
    assert payloads[0]["email"] == "jane@acme.com"


def test_bounce_imid_is_per_recipient_unique():
    body = "failed: jane@acme.com, kai@corp.de"
    ndr = _item(message_class="REPORT.IPM.Note.NDR", body_head=body)
    payloads = build_payloads([ndr], WATCH)
    imids = {p["internet_message_id"] for p in payloads}
    assert len(imids) == 2  # one NDR, two suppressions, distinct hashes


def test_match_drafted_correlates_by_recipient_and_subject():
    sent = [{"subject": "Warm hello", "to_addrs": ["jane@acme.com"],
             "ts": "2026-07-15T11:00:00+02:00", "imid": "<d1@brisken>"},
            {"subject": "Other", "to_addrs": ["x@y.z"], "ts": "", "imid": None}]
    drafted = [{"attempt_key": "cadence:5:1", "to": "jane@acme.com",
                "subject": "Warm hello"},
               {"attempt_key": "cadence:6:1", "to": "kai@corp.de",
                "subject": "Never sent"}]
    out = com_mail.match_drafted(sent, drafted)
    assert len(out) == 1
    assert out[0]["attempt_key"] == "cadence:5:1"
    assert out[0]["internet_message_id"] == "<d1@brisken>"
