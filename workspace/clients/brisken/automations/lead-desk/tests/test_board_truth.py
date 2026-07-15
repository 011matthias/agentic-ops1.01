"""P1: the board shows and counts EVERY campaign contact, not only the
enrolled subset; sheet-sync enrolls; search falls back to suppressed rows."""
from __future__ import annotations

from lead_desk.web.service import build_board
from lead_desk.web.store import ContactStore

NOW = "2026-07-16T00:00:00+00:00"


def _seed(store: ContactStore) -> None:
    store.create_campaign("rome-2026", "Rome 2026", NOW, status="done")
    for cid, first, last, email, supp, reason in [
        ("c1", "Ann", "Active", "ann@a.com", 0, None),
        ("c2", "Bob", "Unenrolled", "bob@b.com", 0, None),
        ("c3", "Cy", "Suppressed", "cy@c.com", 1, "no_consent"),
    ]:
        store.upsert_contact({
            "contact_id": cid, "natural_key": email, "campaign": "rome-2026",
            "first_name": first, "last_name": last, "email": email,
            "suppressed": supp, "suppress_reason": reason,
        }, now=NOW)
    # Only c1 is enrolled; c2 (active) and c3 (suppressed) are NOT.
    store.enroll("c1", "rome-2026", "test", NOW)


def test_unenrolled_contacts_appear_and_count(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        _seed(store)
        board = build_board(store, {"show_suppressed": "1"})
        ids = {r["contact_id"] for r in board["rows"]}
        assert ids == {"c1", "c2", "c3"}          # un-enrolled c2/c3 not vanished
        # counts over the full roster: 2 active (c1,c2), 1 suppressed (c3)
        assert board["total_active"] == 2
        assert board["total_suppressed"] == 1


def test_enroll_campaign_contacts_is_idempotent(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        _seed(store)
        # c2 and c3 are unenrolled -> 2 newly enrolled; a second pass adds none.
        assert store.enroll_campaign_contacts("rome-2026", "sync", NOW) == 2
        assert store.enroll_campaign_contacts("rome-2026", "sync", NOW) == 0
        n = store.conn.execute(
            "SELECT COUNT(*) FROM enrollments WHERE campaign_id='rome-2026'").fetchone()[0]
        assert n == 3


def test_enroll_campaign_contacts_noop_without_campaign(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        store.upsert_contact({"contact_id": "x", "natural_key": "x@y.com",
                              "email": "x@y.com", "campaign": "ghost"}, now=NOW)
        assert store.enroll_campaign_contacts("ghost", "sync", NOW) == 0  # FK: no campaign


def test_search_falls_back_to_suppressed(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        _seed(store)
        # "Suppressed" only matches c3, which is off-board; without fallback this
        # dead-ends. suppressed_matches surfaces it; rows stays empty.
        board = build_board(store, {"q": "Suppressed"})
        assert board["rows"] == []
        assert board["suppressed_matches"] == 1


def test_search_no_fallback_when_showing_suppressed(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        _seed(store)
        board = build_board(store, {"q": "Suppressed", "show_suppressed": "1"})
        assert len(board["rows"]) == 1 and board["rows"][0]["contact_id"] == "c3"
        assert board["suppressed_matches"] == 0


def test_sheet_status_is_carried_on_rows(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        _seed(store)
        store.update_fields("c1", {"outreach_status": "In conversation"}, NOW)
        board = build_board(store, {})
        row = next(r for r in board["rows"] if r["contact_id"] == "c1")
        assert row["outreach_status"] == "In conversation"
        # display-only: it does not change the derived stage
        assert row["stage"] == "sourced"
