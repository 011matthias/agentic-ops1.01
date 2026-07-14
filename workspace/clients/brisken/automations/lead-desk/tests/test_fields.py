"""Iteration 4a: every editable field is writable, changes are audited, and
protected/unknown keys are ignored."""
from __future__ import annotations

from lead_desk.web.service import apply_fields, build_contact_view, create_contact
from lead_desk.web.store import ContactStore

NOW = "2026-07-14T00:00:00+00:00"


def _seed(store: ContactStore) -> None:
    store.upsert_contact(
        {
            "contact_id": "c1", "natural_key": "a@x.com",
            "first_name": "Ann", "last_name": "Lee", "company": "OldCo",
            "email": "a@x.com", "tier": "T3",
        },
        now=NOW,
    )


def test_edit_identity_and_classification(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        _seed(store)
        apply_fields(store, "c1", {
            "company": "NewCo", "job_title": "CFO", "phone": "123",
            "tier": "T1", "tier_reason": "hot", "bant_need": 1,
        }, user="dirk")
        row = store.get_contact("c1")
        assert row["company"] == "NewCo"
        assert row["job_title"] == "CFO"
        assert row["phone"] == "123"
        assert row["tier"] == "T1"
        assert row["tier_reason"] == "hot"
        assert row["bant_need"] == 1
        notes = [e for e in store.get_events("c1")
                 if e["type"] == "note" and e["subject"] == "Fields updated"]
        assert len(notes) == 1
        assert "company" in notes[0]["detail"] and "tier" in notes[0]["detail"]


def test_no_change_writes_no_audit(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        _seed(store)
        apply_fields(store, "c1", {"company": "OldCo", "tier": "T3"}, user="dirk")
        assert [e for e in store.get_events("c1") if e["subject"] == "Fields updated"] == []


def test_protected_and_unknown_keys_ignored(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        _seed(store)
        apply_fields(store, "c1", {
            "contact_id": "hacked", "natural_key": "x", "campaign": "z",
            "bogus": 1, "company": "C2",
        }, user="dirk")
        row = store.get_contact("c1")
        assert row["contact_id"] == "c1"
        assert row["natural_key"] == "a@x.com"
        assert row["company"] == "C2"


def test_demo_date_still_emits_milestone(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        _seed(store)
        apply_fields(store, "c1", {"demo_date": "2026-08-01"}, user="dirk")
        assert any(e["type"] == "booked" for e in store.get_events("c1"))


def test_contact_view_exposes_tier_vocab(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        _seed(store)
        view = build_contact_view(store, "c1")
        assert "T1" in view["tier_vocab"] and "GA" in view["tier_vocab"]


def test_create_contact_and_dedup(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        cid, created = create_contact(store, {
            "first_name": "New", "last_name": "Lead", "company": "Acme",
            "email": "new@acme.com", "tier": "T2",
        }, user="dirk")
        assert created is True
        row = store.get_contact(cid)
        assert row["company"] == "Acme" and row["tier"] == "T2"
        assert row["source"] == "manual" and row["campaign"] == "rome-2026"
        assert any(e["subject"] == "Contact created" for e in store.get_events(cid))
        # a second add with the same email dedupes to the existing contact
        cid2, created2 = create_contact(store, {"email": "new@acme.com",
                                                "first_name": "Dup"}, user="dirk")
        assert created2 is False and cid2 == cid


def test_create_contact_without_email_uses_name_key(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        cid, created = create_contact(store, {"first_name": "No", "last_name": "Mail",
                                              "company": "X"}, user="dirk")
        assert created is True and store.get_contact(cid) is not None
