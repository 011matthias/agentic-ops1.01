"""Outbox claim/result semantics: leases, idempotent results, caps, stops.

Framework-free over a tmp_path ContactStore, calling cadence.claim_sends /
cadence.resolve_result directly with explicit at= datetimes. One TestClient
test covers the worker bearer gate at HTTP level.

Fixed clock points (default send window is Mon-Fri 08:30-17:30 Europe/Berlin):
  IN_WINDOW = Wed 2026-07-15 09:00 UTC (11:00 Berlin)
  SATURDAY  = Sat 2026-07-18 09:00 UTC
  EVENING   = Wed 2026-07-15 20:00 UTC (22:00 Berlin)
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from lead_desk.web import cadence
from lead_desk.web.service import ingest_event, now_iso
from lead_desk.web.store import ContactStore, attempt_key_for

IN_WINDOW = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)
SATURDAY = datetime(2026, 7, 18, 9, 0, tzinfo=timezone.utc)
EVENING = datetime(2026, 7, 15, 20, 0, tzinfo=timezone.utc)


def make_contact(store, cid_suffix, email=None, **fields):
    cid = f"c{cid_suffix}"
    data = {"contact_id": cid, "natural_key": cid, "campaign": "rome-2026",
            "first_name": f"First{cid_suffix}", "last_name": f"Last{cid_suffix}",
            "company": f"Co{cid_suffix}",
            "email": f"{cid}@example.com" if email is None else email}
    data.update(fields)
    store.upsert_contact(data, now_iso())
    return cid


def make_engine_campaign(store, contact_ids, cid="camp1", *, daily_cap=40,
                         degree="cold", send_mode="auto-matthias", n_steps=1,
                         approve=True, start=True):
    """Campaign + template + one sequence + enrollments, then the two gates.

    Two-gate flow: approve_campaign freezes copy + list (status 'approved',
    which does NOT send), then start_sending flips it to 'sending' so the
    worker can claim. ``start`` defaults True so the common case yields a
    live 'sending' campaign; pass start=False to hold at 'approved'.

    Enrollment/approval timestamps use a FIXED base one day before the test
    window; the reply-stop tests rely on reply ts >= enrolled_at, and the
    replies use fixed 2026-07-15 timestamps. Using real now here made the suite
    a time-bomb: once the wall clock passed the fixed reply timestamps,
    reply ts < enrolled_at and the reply-stop no longer registered.
    """
    now = "2026-07-14T09:00:00+00:00"
    store.create_campaign(cid, "Test Campaign", now, daily_cap=daily_cap)
    store.save_template("t1", "email", "Hello {{first_name}}",
                        "Body for {{company}}", "tester", now)
    steps = [{"step_no": i + 1, "channel": "email", "template_key": "t1",
              "day_offset": 0} for i in range(n_steps)]
    store.upsert_sequence(cid, degree, f"{degree} seq", send_mode, steps)
    for contact_id in contact_ids:
        store.enroll(contact_id, cid, "tester", now)
        enr = store.find_enrollment(contact_id, cid)
        store.set_degree(enr["enrollment_id"], degree, "manual", "test")
    if approve:
        # Pin approved_at to the fixed base so a day-0 step's due date does not
        # depend on the wall clock (else once real-now passes the fixed IN_WINDOW,
        # approved_at > IN_WINDOW and the claim tests break - a latent time-bomb).
        res = cadence.approve_campaign(store, cid, "tester", cid, now=now)
        assert res["ok"], res
        if start:
            sres = cadence.start_sending(store, cid, "tester", cid, now=now)
            assert sres["ok"], sres
    return cid


def _resolve_sent(store, claim, occurred="2026-07-15T09:00:00+00:00", imid=None):
    payload = {"attempt_key": claim["attempt_key"], "lease_id": claim["lease_id"],
               "status": "sent", "occurred_at": occurred}
    if imid:
        payload["internet_message_id"] = imid
    res = cadence.resolve_result(store, payload)
    assert res["ok"], res
    return res


def _steps_done(store, enrollment_id):
    row = store.conn.execute(
        "SELECT steps_done FROM enrollment_progress WHERE enrollment_id = ?",
        (enrollment_id,),
    ).fetchone()
    return int(row["steps_done"])


# -- 1. draft vs approved + rendered claim payload ---------------------------

def test_draft_campaign_zero_claims_then_sending_claim_renders(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        c1 = make_contact(s, 1)
        make_engine_campaign(s, [c1], approve=False)
        res = cadence.claim_sends(s, "w1", 10, at=IN_WINDOW)
        assert res == {"paused": False, "claims": []}

        # Two gates: approve freezes copy + list (no send), start turns it on.
        assert cadence.approve_campaign(s, "camp1", "tester", "camp1")["ok"]
        assert cadence.start_sending(s, "camp1", "tester", "camp1")["ok"]
        res = cadence.claim_sends(s, "w1", 10, at=IN_WINDOW)
        assert len(res["claims"]) == 1
        claim = res["claims"][0]
        assert claim["subject"] == "Hello First1"          # merge vars substituted
        assert claim["body"] == "Body for Co1"
        assert claim["body_hash"] == hashlib.sha256(
            ("Hello First1" + "\n" + "Body for Co1").encode("utf-8")).hexdigest()
        assert claim["to"] == "c1@example.com"
        assert claim["from"] == "matthias.silva@brisken.com"
        assert claim["cc"] == ["dirk.neumann@brisken.com"]
        assert claim["bcc"] == ["s9hitl_pv69mu@mails4.zohocrm.com"]
        assert claim["attempt_key"] == attempt_key_for(claim["enrollment_id"], 1)


# -- 2. double claim -----------------------------------------------------------

def test_double_claim_returns_empty_while_leased(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        c1 = make_contact(s, 1)
        make_engine_campaign(s, [c1])
        first = cadence.claim_sends(s, "w1", 10, at=IN_WINDOW)
        assert len(first["claims"]) == 1
        second = cadence.claim_sends(s, "w2", 10,
                                     at=IN_WINDOW + timedelta(minutes=1))
        assert second["claims"] == []


# -- 3. resolve 'sent' is idempotent -------------------------------------------

def test_resolve_sent_emits_exactly_one_event(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        c1 = make_contact(s, 1)
        make_engine_campaign(s, [c1])
        claim = cadence.claim_sends(s, "w1", 10, at=IN_WINDOW)["claims"][0]
        akey = claim["attempt_key"]
        payload = {"attempt_key": akey, "lease_id": claim["lease_id"],
                   "status": "sent", "occurred_at": "2026-07-15T09:05:00+00:00",
                   "internet_message_id": "<m1@brisken.com>"}
        res = cadence.resolve_result(s, payload)
        assert res["ok"] and res["event_inserted"]
        sent = [e for e in s.get_events(c1) if e["ext_key"] == akey]
        assert len(sent) == 1 and sent[0]["type"] == "sent"

        n = s.count_events()
        res2 = cadence.resolve_result(s, payload)          # duplicate ack
        assert res2["ok"] and res2["event_inserted"] is False
        assert s.count_events() == n
        # repeat ack with another lease after the outcome landed: idempotent ok
        res3 = cadence.resolve_result(s, {**payload, "lease_id": "other"})
        assert res3 == {"ok": True, "idempotent": True}
        assert s.count_events() == n


# -- 4. lease enforcement -------------------------------------------------------

def test_wrong_lease_409_and_expiry_stalls_without_release(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        c1 = make_contact(s, 1)
        make_engine_campaign(s, [c1])
        claim = cadence.claim_sends(s, "w1", 10, at=IN_WINDOW)["claims"][0]
        akey = claim["attempt_key"]
        bad = cadence.resolve_result(s, {"attempt_key": akey,
                                         "lease_id": "wrong", "status": "sent"})
        assert bad["ok"] is False and bad["http"] == 409
        assert s.get_attempt(akey)["status"] == "leased"

        # 2h later the 30-min lease is expired: stalled, and NOT re-leased.
        later = IN_WINDOW + timedelta(hours=2)
        res = cadence.claim_sends(s, "w1", 10, at=later)
        assert res["claims"] == []
        assert s.get_attempt(akey)["status"] == "stalled"


# -- 5. failure classes -----------------------------------------------------------

def test_transient_failure_requeues_then_parks_at_attempt_cap(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        c1 = make_contact(s, 1)
        make_engine_campaign(s, [c1])
        akey = attempt_key_for(
            int(s.find_enrollment(c1, "camp1")["enrollment_id"]), 1)
        at = IN_WINDOW
        fail = None
        for round_no in range(1, cadence.MAX_SEND_ATTEMPTS + 1):
            res = cadence.claim_sends(s, "w1", 10, at=at)
            assert len(res["claims"]) == 1, f"round {round_no} not claimable"
            claim = res["claims"][0]
            assert s.get_attempt(akey)["attempt_count"] == round_no
            fail = cadence.resolve_result(s, {
                "attempt_key": akey, "lease_id": claim["lease_id"],
                "status": "failed", "error_class": "transient",
                "failure_reason": "smtp 421"})
            assert fail["ok"]
            if round_no < cadence.MAX_SEND_ATTEMPTS:
                assert fail["requeued"] is True
                assert s.get_attempt(akey)["status"] == "queued"
            at = at + timedelta(minutes=5)
        # the MAX_SEND_ATTEMPTS-th transient failure parks it
        assert fail["requeued"] is False
        assert s.get_attempt(akey)["status"] == "parked"
        assert cadence.claim_sends(s, "w1", 10, at=at)["claims"] == []


def test_permanent_failure_parks_immediately(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        c1 = make_contact(s, 1)
        make_engine_campaign(s, [c1])
        claim = cadence.claim_sends(s, "w1", 10, at=IN_WINDOW)["claims"][0]
        res = cadence.resolve_result(s, {
            "attempt_key": claim["attempt_key"], "lease_id": claim["lease_id"],
            "status": "failed", "error_class": "permanent",
            "failure_reason": "550 no such user"})
        assert res["ok"] and res["requeued"] is False
        assert s.get_attempt(claim["attempt_key"])["status"] == "parked"
        assert cadence.claim_sends(
            s, "w1", 10, at=IN_WINDOW + timedelta(minutes=5))["claims"] == []


# -- 6. daily cap + send window -----------------------------------------------------

def test_daily_cap_and_send_window(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        c1, c2 = make_contact(s, 1), make_contact(s, 2)
        make_engine_campaign(s, [c1, c2], daily_cap=1)
        assert cadence.claim_sends(s, "w1", 10, at=SATURDAY)["claims"] == []
        assert cadence.claim_sends(s, "w1", 10, at=EVENING)["claims"] == []
        res = cadence.claim_sends(s, "w1", 10, at=IN_WINDOW)
        assert len(res["claims"]) == 1     # cap=1 beats the 2 due enrollments


# -- 7. reply between claims stops the follow-up ---------------------------------------

def test_reply_after_first_send_stops_next_step(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        c1, c2 = make_contact(s, 1), make_contact(s, 2)
        make_engine_campaign(s, [c1, c2], n_steps=2)
        res = cadence.claim_sends(s, "w1", 10, at=IN_WINDOW)
        assert len(res["claims"]) == 2
        for claim in res["claims"]:
            _resolve_sent(s, claim)
        # c1 replies between the step-1 resolution and the next claim pass
        assert s.add_event(contact_id=c1, ts="2026-07-15T10:00:00+00:00",
                           channel="email", direction="inbound", type="reply",
                           now=now_iso())
        res = cadence.claim_sends(s, "w1", 10, at=IN_WINDOW + timedelta(hours=2))
        assert [c["contact_id"] for c in res["claims"]] == [c2]
        assert res["claims"][0]["step_no"] == 2


# -- 8. suppression between claims ---------------------------------------------------

def test_suppression_between_claims_stops_next_step(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        c1 = make_contact(s, 1)
        make_engine_campaign(s, [c1], n_steps=2)
        claim = cadence.claim_sends(s, "w1", 10, at=IN_WINDOW)["claims"][0]
        _resolve_sent(s, claim)
        s.set_suppressed(c1, True, "do_not_contact", "tester", now_iso())
        res = cadence.claim_sends(s, "w1", 10, at=IN_WINDOW + timedelta(hours=2))
        assert res["claims"] == []


# -- 9. kill switch ---------------------------------------------------------------------

def test_kill_switch_pauses_all_claims(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        c1 = make_contact(s, 1)
        make_engine_campaign(s, [c1])
        s.set_state("kill_switch", "1", now_iso())
        res = cadence.claim_sends(s, "w1", 10, at=IN_WINDOW)
        assert res["paused"] is True and res["claims"] == []
        s.set_state("kill_switch", "0", now_iso())
        res = cadence.claim_sends(s, "w1", 10, at=IN_WINDOW)
        assert res["paused"] is False and len(res["claims"]) == 1


# -- 10. draft-dirk send mode -------------------------------------------------------------

def test_draft_dirk_mode_defers_event_until_confirmed(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        c1 = make_contact(s, 1)
        make_engine_campaign(s, [c1], degree="warm", send_mode="draft-dirk")
        claim = cadence.claim_sends(s, "w1", 10, at=IN_WINDOW)["claims"][0]
        assert claim["send_mode"] == "draft-dirk"
        eid = int(claim["enrollment_id"])

        events_before = s.count_events()
        drafted = cadence.resolve_result(s, {
            "attempt_key": claim["attempt_key"], "lease_id": claim["lease_id"],
            "status": "drafted", "entry_id": "outlook-entry-1"})
        assert drafted["ok"] and drafted["event_inserted"] is False
        assert s.count_events() == events_before               # NO event yet
        assert s.get_attempt(claim["attempt_key"])["status"] == "drafted"
        assert _steps_done(s, eid) == 0                        # pointer parked

        confirmed = cadence.confirm_draft_sent(s, {
            "attempt_key": claim["attempt_key"],
            "occurred_at": "2026-07-15T12:00:00+00:00",
            "internet_message_id": "<dirk-1@brisken.com>"})
        assert confirmed["ok"] and confirmed["event_inserted"]
        assert s.get_attempt(claim["attempt_key"])["status"] == "sent"
        assert _steps_done(s, eid) == 1                        # step advanced


# -- 11. bearer auth on the outbox API (HTTP level) -----------------------------------------

def test_outbox_claim_bearer_auth(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from lead_desk.web.app import create_app

    monkeypatch.delenv("LEAD_DESK_AUTH_SECRET", raising=False)
    monkeypatch.setenv("LEAD_DESK_WORKER_SECRET", "s3cret")
    app = create_app(tmp_path)
    with TestClient(app) as client:
        r = client.post("/api/outbox/claim", json={"worker_id": "w1"})
        assert r.status_code == 401
        r = client.post("/api/outbox/claim", json={"worker_id": "w1"},
                        headers={"Authorization": "Bearer s3cret"})
        assert r.status_code == 200
        assert r.json() == {"paused": False, "claims": []}


# -- 12. ingest_event guards ------------------------------------------------------------------

def test_ingest_rejects_reserved_cadence_ext_key(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        c1 = make_contact(s, 1)
        res = ingest_event(s, {"contact_id": c1, "type": "sent",
                               "ext_key": "cadence:1:1"})
        assert res["ok"] is False and "reserved" in res["reason"]
        assert s.count_events() == 0


def test_ingest_bounce_auto_suppresses_contact(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        c1 = make_contact(s, 1)
        res = ingest_event(s, {"contact_id": c1, "type": "bounce",
                               "occurred_at": "2026-07-15T09:30:00+00:00"})
        assert res["ok"] and res["inserted"]
        row = s.get_contact(c1)
        assert row["suppressed"] == 1
        assert row["suppress_reason"] == "bounced"


def test_ingest_dedupes_captured_worker_send_by_imid(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        c1 = make_contact(s, 1)
        make_engine_campaign(s, [c1])
        claim = cadence.claim_sends(s, "w1", 10, at=IN_WINDOW)["claims"][0]
        _resolve_sent(s, claim, occurred="2026-07-15T09:05:00+00:00",
                      imid="<m1@brisken.com>")
        # capture worker sees the same mail in Sent Items and posts it
        res = ingest_event(s, {"email": "c1@example.com", "type": "sent",
                               "internet_message_id": "<m1@brisken.com>",
                               "occurred_at": "2026-07-15T09:06:00+00:00"})
        assert res["ok"] and res["inserted"] is False
        assert res["deduped"] == "worker send"
        assert sum(1 for e in s.get_events(c1) if e["type"] == "sent") == 1


# -- 13. the two-gate contract: approve freezes, start turns sending on -------------------

def test_approve_alone_is_gated_start_sending_opens_claims(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        c1 = make_contact(s, 1)
        # approved but NOT started: frozen copy + list, but nothing sends yet
        make_engine_campaign(s, [c1], start=False)
        assert s.get_campaign("camp1")["status"] == "approved"
        assert cadence.claim_sends(s, "w1", 10, at=IN_WINDOW)["claims"] == []

        # the second gate flips 'approved' -> 'sending' and unblocks the outbox
        assert cadence.start_sending(s, "camp1", "tester", "camp1")["ok"]
        assert s.get_campaign("camp1")["status"] == "sending"
        res = cadence.claim_sends(s, "w1", 10, at=IN_WINDOW)
        assert len(res["claims"]) == 1


# -- 14. supersede a live SENDING campaign drops it to draft and stops claims -------------

def test_supersede_on_sending_drops_to_draft_and_stops_claims(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        c1 = make_contact(s, 1)
        make_engine_campaign(s, [c1])                      # approved + started
        assert s.get_campaign("camp1")["status"] == "sending"

        cadence.supersede_approval(s, "camp1", "copy changed after go-live")
        assert s.get_campaign("camp1")["status"] == "draft"
        assert cadence.claim_sends(s, "w1", 10, at=IN_WINDOW)["claims"] == []
