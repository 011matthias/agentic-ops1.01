"""The three legacy 'do not contact' encodings collapse into one flag."""
from __future__ import annotations

from lead_desk.migrate import (
    classify_log_line, dirk_touch, is_held, natural_key, suppression,
)


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


# --- Iteration 2: held + Dirk-touch classifiers ------------------------------

def test_ga_tier_is_held():
    assert suppression({"Tier": "GA"}) == (1, "held")


def test_ga_dirk_note_is_held():
    assert is_held({"dirk_notes": "GA"}) is True


def test_next_step_hold_is_held():
    assert is_held({"next_step": "On hold: excluded_no_verified_email"}) is True
    assert is_held({"next_step": "Covered by the LSEG note; no separate send planned."}) is True
    assert is_held({"next_step": "DO NOT SEND yet: confirm the contact first."}) is True


def test_transient_hold_stays_active():
    # OOO / awaiting-decision / scheduling are transient: still active, not held.
    assert is_held({"next_step": "On hold: awaiting Dirk's decision (question sent 2026-07-09)."}) is False
    assert is_held({"next_step": "OOO until 2026-07-20; nudge after return."}) is False
    assert is_held({"next_step": "Scheduling in progress: Dirk to confirm a new slot."}) is False


def test_consent_beats_held():
    # A GA contact who is also stop=X keeps the stronger, permanent consent reason.
    assert suppression({"Tier": "GA", "stop": "X"}) == (1, "stop")
    # An exclusion tier also outranks a held signal.
    assert suppression({"Tier": "ANON", "next_step": "On hold: excluded"}) == (1, "anon")


def test_clean_contact_not_held():
    assert suppression({"Tier": "T1", "next_step": "Send the pending Outlook draft."}) == (0, None)


def test_dirk_touch_from_notes():
    ch, detail = dirk_touch({"dirk_notes": "personal outreach DN"})
    assert ch == "email" and "personal outreach" in detail


def test_dirk_touch_from_if_we_know_them():
    ch, _ = dirk_touch({"if_we_know_them": "Met at TAC Brussels 2024 (Dirk personally engaged)"})
    assert ch == "meeting"


def test_no_dirk_touch_without_signal():
    assert dirk_touch({"dirk_notes": "GA"}) is None
    assert dirk_touch({"if_we_know_them": "Met at the booth"}) is None  # no Dirk named
    assert dirk_touch({}) is None
