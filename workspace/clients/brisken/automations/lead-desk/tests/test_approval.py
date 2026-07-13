"""Approval gate: approval_report validation, approve_campaign freeze, supersede.

Approval is THE gate: it validates the campaign, pins template versions,
hashes the enrolled list, and stamps enrollments. Nothing sends before it;
a supersede drops it back to draft and the outbox goes silent.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from lead_desk.web import cadence
from lead_desk.web.service import now_iso
from lead_desk.web.store import ContactStore

CID = "rome-eng"

# Wednesday 2026-07-15 09:00 UTC = 11:00 Europe/Berlin -> inside default window.
INSIDE = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)
# Saturday -> outside the default weekday window.
OUTSIDE = datetime(2026, 7, 18, 9, 0, tzinfo=timezone.utc)

_DEFAULT = object()


def make_contact(store, cid_suffix, email=_DEFAULT, **fields):
    cid = f"c{cid_suffix}"
    if email is _DEFAULT:
        email = f"{cid}@example.com"
    data = {"contact_id": cid, "natural_key": cid, "campaign": "rome-2026",
            "first_name": "Ann", "last_name": f"Lee{cid_suffix}",
            "company": "Acme", "email": email}
    data.update(fields)
    store.upsert_contact(data, now_iso())
    return cid


def make_campaign(store, campaign_id=CID):
    store.create_campaign(campaign_id, "Engine Test", now_iso())
    return campaign_id


def add_template(store, key="t1", body="V1 body {{first_name}}", subject="Intro"):
    return store.save_template(key, "email", subject, body, "tester", now_iso())


def add_sequence(store, campaign_id=CID, degree="cold", steps=None):
    steps = steps if steps is not None else [
        {"step_no": 1, "channel": "email", "template_key": "t1", "day_offset": 0},
    ]
    return store.upsert_sequence(campaign_id, degree, f"{degree} seq",
                                 "auto-matthias", steps)


def enroll(store, contact_id, campaign_id=CID, degree="cold"):
    store.enroll(contact_id, campaign_id, "tester", now_iso())
    enr = store.find_enrollment(contact_id, campaign_id)
    if degree is not None:
        store.set_degree(enr["enrollment_id"], degree, "manual", "test")
    return int(enr["enrollment_id"])


def make_engine_campaign(store):
    """Campaign + template + cold sequence + one enrolled contact, approved."""
    cid = make_campaign(store)
    add_template(store)
    add_sequence(store)
    contact = make_contact(store, 1)
    enroll(store, contact)
    res = cadence.approve_campaign(store, cid, "tester", cid)
    assert res["ok"], res
    return cid, contact


def _errors(store, campaign_id=CID):
    report = cadence.approval_report(store, campaign_id)
    assert report["ok"] is False
    return report["errors"]


# -- 1. approval blocked, one test per validation ---------------------------

def test_approve_blocked_no_enrollments(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid = make_campaign(s)
        add_template(s)
        add_sequence(s)
        res = cadence.approve_campaign(s, cid, "tester", cid)
        assert res["ok"] is False
        assert any("no contacts enrolled" in e for e in res["errors"])
        assert s.get_campaign(cid)["status"] == "draft"


def test_approve_blocked_null_degree(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid = make_campaign(s)
        add_template(s)
        add_sequence(s)
        c1 = make_contact(s, 1)
        enroll(s, c1, degree=None)  # active enrollment, degree stays NULL
        errors = _errors(s, cid)
        assert any("active enrollment(s) have no degree" in e for e in errors)
        res = cadence.approve_campaign(s, cid, "tester", cid)
        assert res["ok"] is False


def test_approve_blocked_degree_without_sequence(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid = make_campaign(s)
        add_template(s)
        c1 = make_contact(s, 1)
        enroll(s, c1, degree="cold")  # no sequence for 'cold'
        errors = _errors(s, cid)
        assert any("degree 'cold' has no sequence/steps" in e for e in errors)


def test_approve_blocked_missing_template(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid = make_campaign(s)
        add_sequence(s, steps=[
            {"step_no": 1, "channel": "email", "template_key": "ghost", "day_offset": 0},
        ])
        c1 = make_contact(s, 1)
        enroll(s, c1)
        errors = _errors(s, cid)
        assert any("template 'ghost' does not exist" in e for e in errors)


def test_approve_blocked_missing_merge_var(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid = make_campaign(s)
        add_template(s, body="Hi {{first_name}}, quick question.")
        add_sequence(s)
        c1 = make_contact(s, 1, first_name="")  # has email, empty first_name
        enroll(s, c1)
        errors = _errors(s, cid)
        assert any("missing first_name" in e for e in errors)


def test_approve_blocked_email_step_without_email(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid = make_campaign(s)
        add_template(s)
        add_sequence(s)
        c1 = make_contact(s, 1, email="")
        enroll(s, c1)
        errors = _errors(s, cid)
        assert any("(no email address)" in e for e in errors)


# -- 2. confirm slug ---------------------------------------------------------

def test_wrong_confirm_slug_does_not_approve(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid = make_campaign(s)
        add_template(s)
        add_sequence(s)
        c1 = make_contact(s, 1)
        enroll(s, c1)
        res = cadence.approve_campaign(s, cid, "tester", "not-the-id")
        assert res["ok"] is False
        assert "type the campaign id to confirm" in res["errors"]
        assert s.get_campaign(cid)["status"] == "draft"
        assert s.find_enrollment(c1, cid)["approved_at"] is None


# -- 3. happy path: pin freezes copy ------------------------------------------

def test_approve_pins_latest_version_and_freezes_claims(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid = make_campaign(s)
        assert add_template(s, body="V1 body {{first_name}}") == 1
        assert add_template(s, body="V2 body {{first_name}}") == 2
        add_sequence(s)
        c1 = make_contact(s, 1)
        enroll(s, c1)
        res = cadence.approve_campaign(s, cid, "tester", cid)
        assert res["ok"]
        assert res["pins"] == {"t1": 2}  # latest version at approval time
        assert s.get_pins(cid) == {"t1": 2}
        # Template edit AFTER approval must not change what the outbox renders.
        assert add_template(s, body="V3 body {{first_name}}") == 3
        out = cadence.claim_sends(s, "w1", 10, at=INSIDE)
        assert out["paused"] is False
        assert len(out["claims"]) == 1
        claim = out["claims"][0]
        assert claim["contact_id"] == c1
        assert claim["to"] == "c1@example.com"
        assert claim["template_version"] == 2
        assert "V2 body Ann" in claim["body"]
        assert "V3 body" not in claim["body"]


# -- 4. late enrollment ---------------------------------------------------------

def test_late_enrollment_pending_until_second_approval(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid, c1 = make_engine_campaign(s)
        c2 = make_contact(s, 2)
        eid2 = enroll(s, c2)
        assert s.get_enrollment(eid2)["approved_at"] is None
        # Only the approved enrollment is claimable; the late one is pending.
        due = cadence.due_items(s, cid, INSIDE)
        assert [i["enrollment"]["contact_id"] for i in due["emails"]] == [c1]
        out = cadence.claim_sends(s, "w1", 10, at=INSIDE)
        assert [cl["contact_id"] for cl in out["claims"]] == [c1]
        # Second approval stamps the addition; it becomes claimable.
        res2 = cadence.approve_campaign(s, cid, "tester", cid)
        assert res2["ok"]
        assert res2["approved_enrollments"] == 1
        assert s.get_enrollment(eid2)["approved_at"] is not None
        out2 = cadence.claim_sends(s, "w2", 10, at=INSIDE)
        assert [cl["contact_id"] for cl in out2["claims"]] == [c2]


# -- 5. supersede ----------------------------------------------------------------

def test_supersede_drops_to_draft_and_stops_claims(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid, _c1 = make_engine_campaign(s)
        # Sequence changed after approval -> the frozen scope is stale.
        s.upsert_sequence(cid, "cold", "cold seq v2", "auto-matthias", [
            {"step_no": 1, "channel": "email", "template_key": "t1", "day_offset": 2},
        ])
        cadence.supersede_approval(s, cid, "sequence changed")
        assert s.get_campaign(cid)["status"] == "draft"
        marker = s.get_state(f"approval-superseded:{cid}")
        assert marker is not None and "sequence changed" in marker
        out = cadence.claim_sends(s, "w1", 10, at=INSIDE)
        assert out["claims"] == []


# -- 6. approval side effects ------------------------------------------------------

def test_approval_hash_and_enrollment_stamps(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid = make_campaign(s)
        add_template(s)
        add_sequence(s)
        ids = [make_contact(s, i) for i in (1, 2, 3)]
        for c in ids:
            enroll(s, c)
        res = cadence.approve_campaign(s, cid, "tester", cid)
        assert res["ok"]
        assert res["approved_enrollments"] == 3
        camp = s.get_campaign(cid)
        expected = hashlib.sha1("|".join(sorted(ids)).encode("utf-8")).hexdigest()
        assert camp["approved_contacts_hash"] == expected
        assert camp["approved_by"] == "tester"
        for c in ids:
            enr = s.find_enrollment(c, cid)
            assert enr["approved_at"] is not None
            assert enr["approved_by"] == "tester"
