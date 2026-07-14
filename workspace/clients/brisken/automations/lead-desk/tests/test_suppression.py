"""The three legacy 'do not contact' encodings collapse into one flag."""
from __future__ import annotations

from lead_desk.migrate import classify_log_line, natural_key, suppression


def test_stop_flag():
    assert suppression({"stop": "X"}) == (1, "stop")


def test_no_consent_wins():
    assert suppression({"email outreach_status": "Do not contact (no consent)"}) == (1, "no_consent")


def test_do_not_contact_status():
    assert suppression({"linkedin_status": "Do not contact"}) == (1, "do_not_contact")


def test_anon_tier_suppressed():
    assert suppression({"Tier": "ANON"}) == (1, "anon")


def test_duplicate_tier():
    assert suppression({"Tier": "DUPLICATE"}) == (1, "duplicate")


def test_clean_contact_not_suppressed():
    assert suppression({"Tier": "T1", "email outreach_status": "Not contacted"}) == (0, None)


def test_natural_key_prefers_email():
    assert natural_key("A@X.com", "a", "b", "c") == "a@x.com"


def test_natural_key_falls_back_to_name():
    k = natural_key(None, "Jane", "Doe", "Acme")
    assert k.startswith("anon:") and len(k) > 5


def test_log_line_classification():
    assert classify_log_line("2026-06-19 E1 pre-event invite sent") == ("email", "outbound", "invite")
    assert classify_log_line('2026-06-24 E3 response: "yes"') == ("email", "inbound", "reply")
    assert classify_log_line("LinkedIn connect note sent") == ("linkedin", "outbound", "sent")
