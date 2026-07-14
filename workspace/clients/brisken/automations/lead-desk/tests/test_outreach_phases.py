"""Outreach phases: during-event (E1/E2/E3, mailbox-grounded) and post-event
(sheet booth follow-up) are kept DISTINCT and never conflate; non-attendees
are never brought into the list."""
from __future__ import annotations

from lead_desk import ground
from lead_desk.web.service import outreach_phases
from lead_desk.web.store import ContactStore

NOW = "2026-07-14T00:00:00+00:00"


def _seed(store: ContactStore) -> None:
    store.upsert_contact({"contact_id": "c1", "natural_key": "a@x.com",
                          "first_name": "Ann", "last_name": "Lee", "company": "X",
                          "email": "a@x.com", "campaign": "rome-2026"}, now=NOW)


def test_ground_distinct_during_event_and_skips_non_contacts(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        _seed(store)
        sends = {"a@x.com": {"E1": "2026-06-19", "E3": "2026-06-24"},
                 "stranger@none.com": {"E1": "2026-06-19"}}      # non-attendee
        replies = {"a@x.com": "2026-06-22"}
        rep = ground.ground(store, "rome-2026", NOW, collected=(sends, replies))
        assert rep["contacts_grounded"] == 1
        assert rep["recipients_skipped_non_contact"] == 1         # stranger stays OUT
        assert store.find_by_email("stranger@none.com") is None   # never created
        events = [dict(e) for e in store.get_events("c1")]
        subs = {e["subject"] for e in events}
        assert {"During-event E1", "During-event E3", "During-event reply"} <= subs
        ph = outreach_phases(events)
        assert ph["during_event"]["waves"] == ["E1", "E3"]
        assert ph["during_event"]["replied"] == "2026-06-22"
        assert ph["post_event"]["any"] is False


def test_post_event_stays_separate_from_during_event(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        _seed(store)
        store.add_event(contact_id="c1", ts="2026-07-08T00:00:00+00:00", channel="email",
                        direction="outbound", type="sent", subject="Post-event follow-up",
                        detail="Post-event: Booth follow-up sent 2026-07-08",
                        source="sheet-postevent", ext_key="pe-c1", now=NOW)
        store.add_event(contact_id="c1", ts="2026-06-19T00:00:00+00:00", channel="email",
                        direction="outbound", type="sent", subject="During-event E1",
                        detail="E1", source="graph", ext_key="de-E1-c1", now=NOW)
        ph = outreach_phases([dict(e) for e in store.get_events("c1")])
        assert ph["during_event"]["waves"] == ["E1"]              # not mixed
        assert ph["post_event"]["any"] and ph["post_event"]["sent"] == "2026-07-08"


def test_ground_is_idempotent(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        _seed(store)
        collected = ({"a@x.com": {"E1": "2026-06-19"}}, {})
        r1 = ground.ground(store, "rome-2026", NOW, collected=collected)
        r2 = ground.ground(store, "rome-2026", NOW, collected=collected)
        assert r1["sent_events"] == 1 and r2["sent_events"] == 0  # re-run adds nothing
