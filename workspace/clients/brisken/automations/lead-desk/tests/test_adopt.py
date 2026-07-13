"""Adopting a legacy cohort is inert: history untouched, and the adopted
campaign (status 'done') can never reach the outbox. Plus reconcile repairs
for lock-table/event-log drift."""
from __future__ import annotations

from datetime import datetime, timezone

from lead_desk.adopt import adopt
from lead_desk.web import cadence
from lead_desk.web.service import now_iso
from lead_desk.web.store import ContactStore, attempt_key_for

IN_WINDOW = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)   # Wed 11:00 Berlin
OUT_WINDOW = datetime(2026, 7, 18, 9, 0, tzinfo=timezone.utc)  # Saturday
BACKDATE = "2026-07-10T09:00:00+00:00"


def make_contact(store, cid_suffix, email=None, **fields):
    cid = f"c-{cid_suffix}"
    data = {"contact_id": cid, "natural_key": cid, "campaign": "rome-2026",
            "first_name": f"F{cid_suffix}", "last_name": f"L{cid_suffix}",
            "company": "Acme", "email": email or f"{cid_suffix}@example.com"}
    data.update(fields)
    store.upsert_contact(data, now_iso())
    return cid


def _seed_legacy(store):
    """Three rome-2026 contacts at mixed stages: sourced / sent / replied."""
    src = make_contact(store, "src")
    sent = make_contact(store, "sent")
    rep = make_contact(store, "rep")
    store.add_event(contact_id=sent, ts="2026-07-01T09:00:00+00:00", channel="email",
                    direction="outbound", type="sent", now=now_iso())
    store.add_event(contact_id=rep, ts="2026-07-01T09:00:00+00:00", channel="email",
                    direction="outbound", type="sent", now=now_iso())
    store.add_event(contact_id=rep, ts="2026-07-05T10:00:00+00:00", channel="email",
                    direction="inbound", type="reply", now=now_iso())
    return src, sent, rep


def _backdate_approvals(store, campaign_id):
    """Pin enrollment approval stamps to a fixed past date so step-1 due dates
    are deterministic against the fixed claim datetimes."""
    store.conn.execute(
        "UPDATE enrollments SET approved_at = ? "
        "WHERE campaign_id = ? AND approved_at IS NOT NULL",
        (BACKDATE, campaign_id),
    )
    store.conn.commit()


def make_engine_campaign(store, contact_ids, campaign_id="engine-1"):
    """A real, approved engine campaign: template + 1-step cold sequence +
    enrollments, approved through the actual gate."""
    now = now_iso()
    store.create_campaign(campaign_id, "Engine test", now)
    store.save_template("t-intro", "email", "Hello {{first_name}}",
                        "Word from {{company}}.", "tester", now)
    store.upsert_sequence(campaign_id, "cold", "Cold seq", "auto-matthias",
                          [{"step_no": 1, "channel": "email",
                            "template_key": "t-intro", "day_offset": 0}])
    for cid in contact_ids:
        store.enroll(cid, campaign_id, "tester", now)
        enr = store.find_enrollment(cid, campaign_id)
        store.set_degree(int(enr["enrollment_id"]), "cold", "manual", None)
    res = cadence.approve_campaign(store, campaign_id, "tester", campaign_id)
    assert res["ok"], res
    _backdate_approvals(store, campaign_id)
    return campaign_id


# -- 1 + 2: adopt ---------------------------------------------------------------


def test_adopt_creates_done_campaign_and_enrollments(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as store:
        cids = _seed_legacy(store)
        report = adopt(store, "rome-2026", "Rome 2026")

        row = store.get_campaign("rome-2026")
        assert row is not None
        assert row["status"] == "done"

        assert report["contacts"] == 3
        assert report["newly_enrolled"] == 3
        assert report["total_enrollments"] == 3
        assert report["events_unchanged"] is True
        assert report["stages_unchanged"] is True
        assert report["stage_distribution"] == {"sourced": 1, "sent": 1, "replied": 1}

        for cid in cids:
            enr = store.find_enrollment(cid, "rome-2026")
            assert enr is not None
            assert enr["enrolled_by"] == "adopt"
            assert enr["approved_at"] is None


def test_adopt_rerun_is_idempotent(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as store:
        _seed_legacy(store)
        adopt(store, "rome-2026", "Rome 2026")
        again = adopt(store, "rome-2026", "Rome 2026")
        assert again["newly_enrolled"] == 0
        assert again["total_enrollments"] == 3
        assert again["events_unchanged"] is True
        assert again["stages_unchanged"] is True


# -- 3: an adopted campaign can never claim ---------------------------------------


def test_adopted_campaign_never_claims(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as store:
        _seed_legacy(store)
        adopt(store, "rome-2026", "Rome 2026")

        # Make rome-2026 claimable in every respect EXCEPT its status: a
        # sequence, degrees, pinned template, and manually approved enrollments.
        now = now_iso()
        v = store.save_template("t-rome", "email", "Hi {{first_name}}",
                                "Rome {{company}}.", "tester", now)
        store.upsert_sequence("rome-2026", "cold", "Rome seq", "auto-matthias",
                              [{"step_no": 1, "channel": "email",
                                "template_key": "t-rome", "day_offset": 0}])
        for row in store.enrollments_for_campaign("rome-2026"):
            store.set_degree(int(row["enrollment_id"]), "cold", "manual", None)
        store.approve_pending_enrollments("rome-2026", "tester", now)
        store.pin_templates("rome-2026", {"t-rome": v})
        _backdate_approvals(store, "rome-2026")
        assert store.get_campaign("rome-2026")["status"] == "done"

        # Positive control proving the in-window datetime CAN claim: a second,
        # genuinely approved campaign with one fresh contact.
        eng = make_contact(store, "eng")
        make_engine_campaign(store, [eng])

        out = cadence.claim_sends(store, "w1", 50, at=OUT_WINDOW)
        assert out["claims"] == []  # Saturday: nobody sends at all

        res = cadence.claim_sends(store, "w1", 50, at=IN_WINDOW)
        assert res["paused"] is False
        assert [c["campaign_id"] for c in res["claims"]] == ["engine-1"]
        assert store.attempts_for_campaign("rome-2026") == []


# -- 4: reconcile ------------------------------------------------------------------


def _enrolled_bare(store, suffix, campaign_id):
    cid = make_contact(store, suffix)
    store.create_campaign(campaign_id, "Recon", now_iso())
    store.enroll(cid, campaign_id, "tester", now_iso())
    enr = store.find_enrollment(cid, campaign_id)
    return cid, int(enr["enrollment_id"])


def test_reconcile_emits_missing_sent_event(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as store:
        cid, eid = _enrolled_bare(store, "ra", "camp-ra")
        akey = attempt_key_for(eid, 1)
        assert store.try_lease(
            attempt_key=akey, enrollment_id=eid, step_no=1,
            send_mode="auto-matthias", lease_id="l1",
            lease_expires="2099-01-01T00:00:00+00:00", worker_id="w1",
            to_addr="ra@example.com", rendered_subject="Subj",
            rendered_body="Body", template_key="t", template_version=1,
            now="2026-07-10T09:00:00+00:00",
        )
        # Worker marked it sent but the event write was lost.
        store.update_attempt(akey, {"status": "sent",
                                    "resolved_at": "2026-07-10T09:05:00+00:00"})
        rep = cadence.reconcile(store)
        assert rep["repaired_events"] == 1
        assert rep["repaired_attempts"] == 0
        evs = [e for e in store.get_events(cid) if e["ext_key"] == akey]
        assert len(evs) == 1
        assert evs[0]["type"] == "sent"
        assert evs[0]["ts"] == "2026-07-10T09:05:00+00:00"
        # Repaired state is stable: a second pass changes nothing.
        rep2 = cadence.reconcile(store)
        assert (rep2["repaired_events"], rep2["repaired_attempts"]) == (0, 0)


def test_reconcile_backfills_missing_attempt(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as store:
        cid, eid = _enrolled_bare(store, "rb", "camp-rb")
        akey = attempt_key_for(eid, 1)
        # A cadence 'sent' event landed but the attempt row is gone.
        store.add_event(contact_id=cid, ts="2026-07-10T09:00:00+00:00",
                        channel="email", direction="outbound", type="sent",
                        subject="Subj", source="worker-auto", ext_key=akey,
                        campaign="camp-rb", now=now_iso())
        assert store.get_attempt(akey) is None
        rep = cadence.reconcile(store)
        assert rep["repaired_attempts"] == 1
        att = store.get_attempt(akey)
        assert att is not None
        assert att["status"] == "sent"
        assert att["resolved_at"] == "2026-07-10T09:00:00+00:00"
        assert att["enrollment_id"] == eid and att["step_no"] == 1
        rep2 = cadence.reconcile(store)
        assert (rep2["repaired_events"], rep2["repaired_attempts"]) == (0, 0)


def test_reconcile_stalls_expired_lease(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as store:
        cid, eid = _enrolled_bare(store, "rc", "camp-rc")
        akey = attempt_key_for(eid, 1)
        assert store.try_lease(
            attempt_key=akey, enrollment_id=eid, step_no=1,
            send_mode="auto-matthias", lease_id="l1",
            lease_expires="2026-07-01T00:00:00+00:00", worker_id="w1",
            to_addr="rc@example.com", rendered_subject="Subj",
            rendered_body="Body", template_key="t", template_version=1,
            now="2026-07-01T00:00:00+00:00",
        )
        rep = cadence.reconcile(store)
        assert rep["stalled"] == 1
        assert store.get_attempt(akey)["status"] == "stalled"
        # A stalled lease is never auto re-leased or repaired further.
        rep2 = cadence.reconcile(store)
        assert rep2["stalled"] == 0
        assert store.get_attempt(akey)["status"] == "stalled"
