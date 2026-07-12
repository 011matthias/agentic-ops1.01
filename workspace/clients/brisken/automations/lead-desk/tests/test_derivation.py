"""The core invariant: pipeline stage is derived from the event log, not stored."""
from __future__ import annotations

from lead_desk.web.service import build_board, build_contact_view, now_iso
from lead_desk.web.store import ContactStore


def _contact(store, cid="c1", **over):
    data = {"contact_id": cid, "natural_key": cid, "campaign": "rome-2026",
            "first_name": "A", "last_name": "B", "company": "Co", "email": f"{cid}@x.com"}
    data.update(over)
    store.upsert_contact(data, now_iso())
    return cid


def _stage(store, cid):
    return {r["contact_id"]: r["stage"] for r in store.board_rows()}[cid]


def test_no_events_is_sourced(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        _contact(s)
        assert _stage(s, "c1") == "sourced"


def test_outbound_makes_sent(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        _contact(s)
        s.add_event(contact_id="c1", ts="2026-06-19T00:00:00+00:00", channel="email",
                    direction="outbound", type="sent", now=now_iso())
        assert _stage(s, "c1") == "sent"


def test_inbound_reply_makes_replied(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        _contact(s)
        s.add_event(contact_id="c1", ts="2026-06-19T00:00:00+00:00", channel="email",
                    direction="outbound", type="sent", now=now_iso())
        s.add_event(contact_id="c1", ts="2026-06-22T00:00:00+00:00", channel="email",
                    direction="inbound", type="reply", now=now_iso())
        assert _stage(s, "c1") == "replied"


def test_bant_plus_reply_is_qualifying(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        _contact(s, bant_need=1)
        s.add_event(contact_id="c1", ts="2026-06-22T00:00:00+00:00", channel="email",
                    direction="inbound", type="reply", now=now_iso())
        assert _stage(s, "c1") == "qualifying"


def test_demo_date_makes_booked(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        _contact(s, demo_date="2026-07-20")
        assert _stage(s, "c1") == "booked"


def test_accepted_verdict_makes_accepted(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        _contact(s, dirk_verdict="accepted")
        assert _stage(s, "c1") == "accepted"


def test_outbound_touch_makes_sent(tmp_path):
    """A Dirk personal touch carries the contact to at least 'sent'."""
    with ContactStore(tmp_path / "db.sqlite") as s:
        _contact(s)
        s.add_event(contact_id="c1", ts="2026-06-19T00:00:00+00:00", channel="meeting",
                    direction="outbound", type="touch", now=now_iso())
        assert _stage(s, "c1") == "sent"


def _board_row(store, cid):
    return {r["contact_id"]: dict(r) for r in store.board_rows()}[cid]


def test_reached_dirk_status_label(tmp_path):
    from lead_desk.web.service import status_label
    with ContactStore(tmp_path / "db.sqlite") as s:
        _contact(s)
        s.add_event(contact_id="c1", ts="2026-06-19T00:00:00+00:00", channel="meeting",
                    direction="outbound", type="touch", now=now_iso())
        assert status_label(_board_row(s, "c1")) == "Reached (Dirk)"


def test_campaign_send_overrides_reached_label(tmp_path):
    """A touch behind a real campaign send reads as a normal send, not 'Reached'."""
    from lead_desk.web.service import status_label
    with ContactStore(tmp_path / "db.sqlite") as s:
        _contact(s)
        s.add_event(contact_id="c1", ts="2026-06-19T00:00:00+00:00", channel="email",
                    direction="outbound", type="sent", now=now_iso())
        s.add_event(contact_id="c1", ts="2026-06-20T00:00:00+00:00", channel="meeting",
                    direction="outbound", type="touch", now=now_iso())
        assert status_label(_board_row(s, "c1")) == "Awaiting reply"


def test_reached_dirk_bucket(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        _contact(s, "c1")
        s.add_event(contact_id="c1", ts="2026-06-19T00:00:00+00:00", channel="meeting",
                    direction="outbound", type="touch", now=now_iso())
        _contact(s, "c2")  # untouched, stays sourced
        view = build_board(s)
        assert view["buckets"]["reached_dirk"] == 1
        filtered = build_board(s, {"bucket": "reached"})
        assert [r["contact_id"] for r in filtered["rows"]] == ["c1"]


def test_idempotent_event_insert(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        _contact(s)
        kw = dict(contact_id="c1", ts="2026-06-19T00:00:00+00:00", channel="email",
                  direction="outbound", type="sent", detail="E1 invite")
        assert s.add_event(**kw, now=now_iso()) is True
        assert s.add_event(**kw, now=now_iso()) is False  # deduped by hash
        assert s.count_events() == 1


def test_suppressed_excluded_from_active(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        _contact(s, "c1")
        _contact(s, "c2", suppressed=1, suppress_reason="stop")
        view = build_board(s)
        assert view["total_active"] == 1
        assert view["total_suppressed"] == 1


def test_held_bucket_off_board_but_filterable(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        _contact(s, "c1")  # active
        _contact(s, "c2", suppressed=1, suppress_reason="held")
        _contact(s, "c3", suppressed=1, suppress_reason="stop")
        view = build_board(s)
        assert view["total_active"] == 1               # held + stop are off-board
        assert view["buckets"]["held"] == 1            # only c2
        held = build_board(s, {"bucket": "held"})
        assert [r["contact_id"] for r in held["rows"]] == ["c2"]
        assert held["rows"][0]["status"] == "Held"


def test_awaiting_and_ingest_by_email(tmp_path):
    from lead_desk.web.service import ingest_event
    with ContactStore(tmp_path / "db.sqlite") as s:
        _contact(s, email="lead@acme.com")
        # cloud worker posts a sent event matched by email
        res = ingest_event(s, {"email": "lead@acme.com", "type": "sent",
                               "occurred_at": "2026-07-01T09:00:00+00:00"})
        assert res["ok"] and res["inserted"]
        view = build_board(s)
        assert view["buckets"]["awaiting_reply"] == 1
        # re-post is idempotent
        res2 = ingest_event(s, {"email": "lead@acme.com", "type": "sent",
                                "occurred_at": "2026-07-01T09:00:00+00:00"})
        assert res2["inserted"] is False
