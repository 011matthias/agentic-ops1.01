"""P2: action-needed + stage-derivation correctness fixes."""
from __future__ import annotations

from datetime import date

from lead_desk.web.service import (
    apply_fields, build_board, now_iso, recommended_action, status_label)
from lead_desk.web.store import ContactStore

TODAY = date(2026, 7, 15)


def _c(store, cid="c1", **over):
    data = {"contact_id": cid, "natural_key": cid, "campaign": "rome-2026",
            "first_name": "A", "last_name": cid, "email": f"{cid}@x.com"}
    data.update(over)
    store.upsert_contact(data, now_iso())
    return cid


def _stage(store, cid):
    return {r["contact_id"]: r["stage"] for r in store.board_rows()}[cid]


# --- #2 full-precision answered/unanswered ------------------------------------

def test_same_day_reply_then_answer_is_answered():
    # they replied 09:00, we answered 15:00 the SAME day -> answered, not owing
    row = {"stage": "replied", "last_in": "2026-07-14T09:00:00+00:00",
           "last_out": "2026-07-14T15:00:00+00:00"}
    assert status_label(row) == "Replied"
    assert recommended_action(row, TODAY)["needed"] is False


def test_reply_after_our_send_still_needs_reply():
    row = {"stage": "replied", "last_in": "2026-07-14T15:00:00+00:00",
           "last_out": "2026-07-14T09:00:00+00:00"}
    assert status_label(row) == "Replied, needs reply"
    assert recommended_action(row, TODAY)["needed"] is True


# --- #1 future next_step_due defers ------------------------------------------

def test_future_next_step_defers_the_nudge():
    row = {"stage": "replied", "last_in": "2026-07-14", "last_out": "2026-07-10",
           "next_step_due": "2026-07-20"}
    assert recommended_action(row, TODAY)["needed"] is False


# --- #3 stage-agnostic dangling ----------------------------------------------

def test_booked_with_pastdue_next_step_flags():
    row = {"stage": "booked", "next_step_due": "2026-07-01", "last_out": "2026-06-20"}
    assert recommended_action(row, TODAY)["needed"] is True


# --- #4 qualifying flags a fresh reply immediately ---------------------------

def test_qualifying_fresh_reply_flags_immediately():
    row = {"stage": "qualifying", "last_in": "2026-07-15", "last_out": "2026-07-10"}
    assert recommended_action(row, TODAY)["needed"] is True


# --- #5 dangling clears after we send past the due date ----------------------

def test_dangling_clears_once_we_send():
    row = {"stage": "sent", "next_step_due": "2026-07-01", "last_out": "2026-07-05"}
    assert recommended_action(row, TODAY)["needed"] is False


# --- #6 bant_budget counts toward qualifying ---------------------------------

def test_bant_budget_makes_qualifying(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        _c(s, bant_budget=1)
        s.add_event(contact_id="c1", ts="2026-07-01T00:00:00+00:00", channel="email",
                    direction="inbound", type="reply", now=now_iso())
        assert _stage(s, "c1") == "qualifying"


# --- #7 demo_date / verdict reversibility ------------------------------------

def test_clearing_demo_date_unbooks(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        _c(s)
        apply_fields(s, "c1", {"demo_date": "2026-08-01"}, user="d")
        assert _stage(s, "c1") == "booked"
        apply_fields(s, "c1", {"demo_date": ""}, user="d")
        assert _stage(s, "c1") != "booked"      # compensating 'unbooked' wins


def test_revoking_verdict_unaccepts(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        _c(s)
        apply_fields(s, "c1", {"dirk_verdict": "accepted"}, user="d")
        assert _stage(s, "c1") == "accepted"
        apply_fields(s, "c1", {"dirk_verdict": "declined"}, user="d")
        assert _stage(s, "c1") != "accepted"


# --- #8 Needs-action bucket + filter -----------------------------------------

def test_needs_action_bucket_and_filter(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        _c(s, "c1")  # replied, unanswered -> owes action
        s.add_event(contact_id="c1", ts="2026-07-01T00:00:00+00:00", channel="email",
                    direction="outbound", type="sent", now=now_iso())
        s.add_event(contact_id="c1", ts="2026-07-14T00:00:00+00:00", channel="email",
                    direction="inbound", type="reply", now=now_iso())
        _c(s, "c2")  # sent only -> awaiting their reply, no action owed
        s.add_event(contact_id="c2", ts="2026-07-14T00:00:00+00:00", channel="email",
                    direction="outbound", type="sent", now=now_iso())
        view = build_board(s)
        assert view["buckets"]["needs_action"] == 1
        f = build_board(s, {"bucket": "action"})
        assert [r["contact_id"] for r in f["rows"]] == ["c1"]
