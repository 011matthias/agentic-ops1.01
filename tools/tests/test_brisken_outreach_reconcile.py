"""Unit tests for the pure diff logic in tools/brisken-outreach-reconcile.py.

The Graph transport (token, corpus pulls, workbook PATCH) needs live
credentials and is deliberately not exercised. The transition policy is the
part a regression would silently break: the 2026-07-14/16/21 incidents were
all policy errors (folder-restricted scans, drafts counted as sends, drafts
collapsed into "not contacted", false downgrades), not transport errors.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "brisken_outreach_reconcile", TOOLS / "brisken-outreach-reconcile.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["brisken_outreach_reconcile"] = mod
    spec.loader.exec_module(mod)
    return mod


MOD = _load()


def ev(**kw):
    base = {"post_sends": [], "post_replies": [], "during_sends": [],
            "during_replies": [], "drafts": [], "meetings": []}
    base.update(kw)
    return base


def hit(date, subject="s"):
    return {"date": date, "subject": subject}


# ---- inbound noise filters (memory step 5: each miss produced a false reply)

def test_ooo_variants_filtered():
    for subj in ("Automatic reply: Rome", "Automatische Antwort",
                 "Out of office", "Out of the office until Aug",
                 "Risposta automatica: fuori sede", "On annual leave",
                 "I am on vacation this week", "Abwesenheitsnotiz"):
        assert MOD.inbound_noise(subj, "a@x.com") == "ooo", subj


def test_calendar_system_subjects_filtered():
    for subj in ("Accepted: OnePilot demo", "Declined: intro call",
                 "Tentative: sync", "Canceled: MDH walkthrough",
                 "Cancelled: sync", "Invitation: Rome follow-up",
                 "Meeting Forward Notification: OnePilot"):
        assert MOD.inbound_noise(subj, "a@x.com") == "calsys", subj


def test_ndr_filtered_by_sender_and_subject():
    assert MOD.inbound_noise("anything", "postmaster@x.com") == "ndr"
    assert MOD.inbound_noise("anything", "mailer-daemon@x.com") == "ndr"
    assert MOD.inbound_noise(
        "x", "MicrosoftExchange329e71ec88ae4615@brisken.com") == "ndr"
    assert MOD.inbound_noise("Undeliverable: Rome follow-up", "a@x.com") == "ndr"


def test_genuine_reply_is_not_noise():
    assert MOD.inbound_noise("RE: Good to see you in Rome", "a@x.com") is None
    # 'office' inside a genuine subject must not trip the OOO filter
    assert MOD.inbound_noise("RE: your office visit", "a@x.com") is None


# ---- hold detection ('-' exact-value gotcha from the 07-15 pass)

def test_dash_is_hold_only_as_whole_value():
    assert MOD.is_hold("-", None) is True
    assert MOD.is_hold("Contacted - awaiting reply", None) is False
    assert MOD.is_hold("Replied - action needed", None) is False


def test_phrase_holds_and_stop_column():
    assert MOD.is_hold("Do not contact", None) is True
    assert MOD.is_hold("Not contacted", "REMOVE") is True
    assert MOD.is_hold("Not contacted", None) is False


# ---- transition policy

def test_post_send_upgrades_not_contacted():
    f = MOD.propose_transition(
        "Not contacted", "T2", None, ev(post_sends=[hit("2026-07-12T09:00:00Z")]))
    assert f["kind"] == "upgrade" and f["to"] == "Contacted - awaiting reply"


def test_draft_is_first_class_never_collapsed():
    # The 2026-07-21 Georgiou case: unsent draft => 'draft ready', NOT open.
    f = MOD.propose_transition(
        "Not contacted", "T2", None,
        ev(drafts=[{"subject": "T2 Market Data Hub, picking it back up"}]))
    assert f["kind"] == "upgrade" and f["to"] == "draft ready"


def test_send_beats_draft():
    f = MOD.propose_transition(
        "Not contacted", "T2", None,
        ev(post_sends=[hit("2026-07-12T09:00:00Z")],
           drafts=[{"subject": "d"}]))
    assert f["to"] == "Contacted - awaiting reply"


def test_reply_upgrades_to_action_needed():
    f = MOD.propose_transition(
        "Contacted - awaiting reply", "T1", None,
        ev(post_replies=[hit("2026-07-13T08:00:00Z")]))
    assert f["kind"] == "upgrade" and f["to"] == "Replied - action needed"


def test_reply_then_our_send_is_in_conversation():
    f = MOD.propose_transition(
        "Contacted - awaiting reply", "T1", None,
        ev(post_replies=[hit("2026-07-13T08:00:00Z")],
           post_sends=[hit("2026-07-14T08:00:00Z")]))
    assert f["to"] == "In conversation"


def test_meeting_is_strongest_signal():
    f = MOD.propose_transition(
        "Contacted - awaiting reply", "T1", None,
        ev(meetings=[hit("2026-08-17T10:00:00")]))
    assert f["kind"] == "upgrade" and f["to"] == "In conversation"


def test_no_downgrade_ever_only_surface():
    f = MOD.propose_transition("In conversation", "T1", None, ev())
    assert f["kind"] == "surface"
    assert "never auto-downgrade" in f["why"]


def test_h5_silence_not_even_surfaced():
    assert MOD.propose_transition("In conversation", "H5", None, ev()) is None


def test_during_event_only_never_sets_post_column():
    f = MOD.propose_transition(
        "Not contacted", "T2", None,
        ev(during_replies=[hit("2026-06-24T09:00:00Z")]))
    assert f["kind"] == "info"


def test_excluded_tiers_untouched():
    for tier in ("ORGANISER", "OWN_TEAM", "TEST", "DUPLICATE", "STOP", "ANON"):
        assert MOD.propose_transition(
            "Not contacted", tier, None,
            ev(post_sends=[hit("2026-07-12T09:00:00Z")])) is None


def test_unknown_vocabulary_is_reported_not_touched():
    f = MOD.propose_transition(
        "Warm intro pending", "T2", None,
        ev(post_sends=[hit("2026-07-12T09:00:00Z")]))
    assert f["kind"] == "unknown"


def test_already_higher_rank_no_change():
    assert MOD.propose_transition(
        "In conversation", "T1", None,
        ev(post_sends=[hit("2026-07-12T09:00:00Z")])) is None


def test_stale_draft_ready_surfaced():
    f = MOD.propose_transition("draft ready", "T2", None, ev())
    assert f["kind"] == "surface"


# ---- window split + A1 helpers

def test_split_window_cutoffs():
    during, post = MOD.split_window(
        [hit("2026-06-26T23:00:00Z"), hit("2026-06-27T00:10:00Z")])
    assert len(during) == 1 and len(post) == 1


def test_parse_a1_and_colletter_roundtrip():
    row, col = MOD.parse_a1_start("'Master contacts'!A1:AH301")
    assert (row, col) == (1, 0)
    assert MOD.colletter(0) == "A"
    assert MOD.colletter(26) == "AA"
    assert MOD.parse_a1_start("X!AA3:AB9") == (3, 26)
