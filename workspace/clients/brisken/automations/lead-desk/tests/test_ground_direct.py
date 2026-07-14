"""Direct (non-E-wave) mailbox outreach grounding: a real send to a real contact
becomes a board event; post-dated ones count as post-event (distinct from the
sheet booth-wave); internal / OWN_TEAM / non-attendee recipients are dropped so
the Planner / receipt / forwarded-invoice noise never lands."""
from __future__ import annotations

from lead_desk import ground
from lead_desk.web.service import outreach_phases
from lead_desk.web.store import ContactStore

NOW = "2026-07-14T00:00:00+00:00"


def _seed(store: ContactStore) -> None:
    store.upsert_contact({"contact_id": "c1", "natural_key": "a@x.com",
                          "first_name": "Ann", "last_name": "Lee", "company": "X",
                          "email": "a@x.com", "tier": "T2", "campaign": "rome-2026"}, now=NOW)
    # An OWN_TEAM row that does NOT end in @brisken.com, to exercise the tier guard.
    store.upsert_contact({"contact_id": "own", "natural_key": "team@partner.io",
                          "first_name": "In", "last_name": "Ternal", "company": "Brisken",
                          "email": "team@partner.io", "tier": "OWN_TEAM",
                          "campaign": "rome-2026"}, now=NOW)


def test_post_event_direct_send_counts_as_post_event(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        _seed(store)
        direct = [("a@x.com", "2026-07-13", "Re: The MDH walkthrough, as promised")]
        rep = ground.ground_direct(store, "rome-2026", NOW, direct=direct)
        assert rep["post_event_events"] == 1
        assert rep["contacts_with_direct"] == 1
        events = [dict(e) for e in store.get_events("c1")]
        assert any(e["subject"] == "Post-event outreach" and e["source"] == "graph"
                   for e in events)
        ph = outreach_phases(events)
        assert ph["post_event"]["any"] and ph["post_event"]["sent"] == "2026-07-13"
        assert ph["during_event"]["any"] is False   # a direct send is not an E-wave


def test_pre_cutoff_send_is_neutral_direct_not_post_event(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        _seed(store)
        direct = [("a@x.com", "2026-06-20", "Great to meet you at the booth")]
        rep = ground.ground_direct(store, "rome-2026", NOW, direct=direct)
        assert rep["direct_during_events"] == 1 and rep["post_event_events"] == 0
        events = [dict(e) for e in store.get_events("c1")]
        assert any(e["subject"] == "Direct outreach" for e in events)
        assert outreach_phases(events)["post_event"]["any"] is False


def test_internal_and_non_contact_recipients_are_dropped(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        _seed(store)
        direct = [
            ("dirk.neumann@brisken.com", "2026-07-13", "FW: Your receipt from Anthropic"),
            ("team@partner.io", "2026-07-13", "FW: weekly billing report"),   # OWN_TEAM
            ("stranger@none.com", "2026-07-13", "You've been assigned a task"),  # non-contact
        ]
        rep = ground.ground_direct(store, "rome-2026", NOW, direct=direct)
        assert rep["recipients_skipped_internal"] == 2
        assert rep["recipients_skipped_non_contact"] == 1
        assert rep["post_event_events"] == 0
        assert store.find_by_email("stranger@none.com") is None   # never created


def test_post_event_direct_is_distinct_from_sheet_follow_up(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        _seed(store)
        store.add_event(contact_id="c1", ts="2026-07-08T00:00:00+00:00", channel="email",
                        direction="outbound", type="sent", subject="Post-event follow-up",
                        detail="Post-event: booth wave", source="sheet-postevent",
                        ext_key="pe-c1", now=NOW)
        ground.ground_direct(store, "rome-2026", NOW,
                             direct=[("a@x.com", "2026-07-13", "Re: MDH walkthrough")])
        events = [dict(e) for e in store.get_events("c1")]
        subs = {e["subject"] for e in events}
        assert {"Post-event follow-up", "Post-event outreach"} <= subs   # both kept
        ph = outreach_phases(events)
        assert ph["post_event"]["sent"] == "2026-07-13"   # latest post-event touch


def test_ground_direct_is_idempotent(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        _seed(store)
        direct = [("a@x.com", "2026-07-13", "Re: MDH walkthrough")]
        r1 = ground.ground_direct(store, "rome-2026", NOW, direct=direct)
        r2 = ground.ground_direct(store, "rome-2026", NOW, direct=direct)
        assert r1["post_event_events"] == 1 and r2["post_event_events"] == 0
