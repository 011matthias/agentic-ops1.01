"""A next_step authored before the contact's latest reply is stale and must
not drive the board's action or a past-due-follow-up flag.

Regression: Asako Teruki / NYK (2026-07-21) replied on 07-14 (captured, status
'Replied - action needed'), but her board action still read her pre-reply plan
"No reply yet; one optional nudge from ~2026-07-15" because next_step had no
authored-time to compare against the reply.
"""
from __future__ import annotations

from datetime import date

from lead_desk.web.service import (
    is_dangling, next_step_is_stale, recommended_action,
)
from lead_desk.web.store import SCHEMA_VERSION, ContactStore

NOW = "2026-07-20T00:00:00+00:00"
REPLY = "2026-07-14T09:50:16Z"           # Asako's captured reply
CREATED = "2026-07-12T11:50:36+00:00"    # her contact row, before the reply
TODAY = date(2026, 7, 21)


def _replied_row(**over) -> dict:
    """A contact who replied 07-14 while carrying the stale pre-reply nudge plan."""
    row = {
        "stage": "replied", "suppressed": 0,
        "last_in": REPLY, "last_out": "2026-07-08T00:00:00+00:00",
        "next_step": "No reply yet; one optional nudge from ~2026-07-15 (per pack concept).",
        "next_step_due": "2026-07-15", "next_step_at": CREATED,
    }
    row.update(over)
    return row


# -- pure staleness rule -------------------------------------------------------

def test_stale_when_plan_predates_reply():
    assert next_step_is_stale(_replied_row()) is True


def test_fresh_when_plan_authored_after_reply():
    assert next_step_is_stale(_replied_row(next_step_at="2026-07-15T09:00:00+00:00")) is False


def test_not_stale_without_a_reply():
    assert next_step_is_stale(_replied_row(last_in=None)) is False


def test_not_stale_when_authored_time_unknown():
    # A legacy row the backfill never reached: honor the plan verbatim.
    assert next_step_is_stale(_replied_row(next_step_at=None)) is False


# -- recommended_action (the board action Dirk sees) ---------------------------

def test_recommended_action_ignores_the_stale_plan():
    rec = recommended_action(_replied_row(), TODAY)
    assert rec["needed"] and rec["kind"] == "reply"
    assert rec["action"] == "Reply to their latest message."
    assert rec["from_next_step"] is False


def test_recommended_action_keeps_a_fresh_post_reply_plan():
    rec = recommended_action(
        _replied_row(next_step="Send the TreasuryCentral one-pager.",
                     next_step_at="2026-07-15T09:00:00+00:00"), TODAY)
    assert rec["action"] == "Send the TreasuryCentral one-pager."
    assert rec["from_next_step"] is True


# -- is_dangling (the past-due-follow-up flag) ---------------------------------

def test_is_dangling_false_when_plan_overtaken_by_reply():
    assert is_dangling(_replied_row(), TODAY) is False


def test_is_dangling_true_for_a_genuine_pastdue_with_no_reply():
    row = _replied_row(stage="sent", last_in=None)  # never replied, nudge overdue
    assert is_dangling(row, TODAY) is True


# -- store: the authored-time is stamped + backfilled --------------------------

def test_update_fields_stamps_next_step_at(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        s.upsert_contact({"contact_id": "c1", "natural_key": "a@x.com",
                          "email": "a@x.com"}, now=CREATED)
        s.update_fields("c1", {"next_step": "call them"}, NOW)
        assert s.get_contact("c1")["next_step_at"] == NOW


def test_upsert_stamps_next_step_at_on_adopt(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        s.upsert_contact({"contact_id": "c1", "natural_key": "a@x.com",
                          "email": "a@x.com", "next_step": "do X"}, now=CREATED)
        assert s.get_contact("c1")["next_step_at"] == CREATED


def _replay_v5(s):
    """Simulate a legacy pre-v5 DB (no stamp) and re-run the migration."""
    s.conn.execute("UPDATE contacts SET next_step_at = NULL")
    s.conn.execute("PRAGMA user_version = 4")
    s.conn.commit()
    s._run_migrations()


def test_v5_backfills_no_reply_plans_to_created_at(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        s.upsert_contact({"contact_id": "c1", "natural_key": "a@x.com",
                          "email": "a@x.com",
                          "next_step": "No reply yet; one optional nudge from ~2026-07-15."},
                         now=CREATED)
        _replay_v5(s)
        row = s.get_contact("c1")
        assert s.conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert row["next_step_at"] == row["created_at"]  # a reply now supersedes it


def test_v5_leaves_a_genuine_note_unstamped(tmp_path):
    # Regression: Lokesh Doggala / Zalando carried "HOT: he asked for a call".
    # The backfill must NOT date it (that would suppress a live hot-lead note).
    with ContactStore(tmp_path / "t.sqlite") as s:
        s.upsert_contact({"contact_id": "c1", "natural_key": "a@x.com",
                          "email": "a@x.com",
                          "next_step": "HOT: he asked for a call incl. Adela."}, now=CREATED)
        s.conn.execute("UPDATE contacts SET next_step_at = NULL")  # legacy row
        s.conn.execute("PRAGMA user_version = 4"); s.conn.commit()
        s._run_migrations()
        assert s.get_contact("c1")["next_step_at"] is None  # honored verbatim
