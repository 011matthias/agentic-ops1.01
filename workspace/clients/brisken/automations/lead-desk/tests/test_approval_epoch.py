"""Epoch-keyed approval + single dispatch claim (web/approval.py, store v14).

The four contract tests the port was specified against, each driven through
the caller that ships it (claim_sends / run_tick / the HTTP routes), plus the
database-level guarantees underneath:

1. a stale-epoch approval is refused, and a decision keyed to an old epoch
   releases nothing;
2. concurrent claimants yield exactly one dispatch permission;
3. altered text or recipient cannot claim or dispatch;
4. an unknown outcome blocks every retry until a trusted reconcile.
"""
from __future__ import annotations

import re
import sqlite3
import threading
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from lead_desk.cloud_worker import WORKER_ID, execute_one, run_tick
from lead_desk.web import approval, cadence
from lead_desk.web.app import create_app
from lead_desk.web.service import now_iso
from lead_desk.web.store import ContactStore
from lead_desk.worker.journal import Journal

IN_WINDOW = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)
NOW = "2026-07-14T09:00:00+00:00"


class FakeMailer:
    def __init__(self):
        self.sent: list[dict] = []
        self.send_exc: Exception | None = None
        self.evidence: dict | None = None

    def send_auto(self, send):
        if self.send_exc is not None:
            raise self.send_exc
        self.sent.append(send)

    def create_draft(self, mailbox, send):
        return {"duplicate": False, "entry_id": "draft-1"}

    def poll_sent(self, mailbox, since):
        return []

    def readback_sent(self, mailbox, to, subject, since, **kw):
        return self.evidence

    def search_sent_for(self, mailbox, to, subject, since):
        return self.evidence


def no_events(mbx, since, until):
    return []


def tick(data, mailer, **kw):
    return run_tick(data, mailer=mailer, poll_fn=no_events, at=IN_WINDOW,
                    sleep=lambda s: None, **kw)


def make_store(tmp_path) -> tuple:
    data = tmp_path / "data"
    data.mkdir()
    return data, ContactStore(data / "lead-desk.sqlite")


def make_campaign(store, *, emails=("ada@example.test",), approve=True,
                  start=True, cid="camp1"):
    store.create_campaign(cid, "Camp", NOW, throttle_seconds=0, jitter_seconds=0)
    store.save_template("t1", "email", "Hello {{first_name}}",
                        "Body for {{company}}", "tester", NOW)
    store.upsert_sequence(cid, "cold", "cold seq", "auto-matthias",
                          [{"step_no": 1, "channel": "email", "template_key": "t1",
                            "day_offset": 0}])
    for i, email in enumerate(emails, 1):
        store.upsert_contact({"contact_id": f"c{i}", "natural_key": f"c{i}",
                              "campaign": "rome-2026", "first_name": f"First{i}",
                              "last_name": "Last", "company": "Acme", "email": email},
                             NOW)
        store.enroll(f"c{i}", cid, "tester", NOW)
        store.set_degree(store.find_enrollment(f"c{i}", cid)["enrollment_id"],
                         "cold", "manual", "test")
    if approve:
        assert cadence.approve_campaign(store, cid, "tester", cid, now=NOW)["ok"]
    if start:
        assert cadence.start_sending(store, cid, "tester", cid, now=NOW)["ok"]
    return cid


def set_company(store, contact_id, company):
    store.conn.execute("UPDATE contacts SET company = ? WHERE contact_id = ?",
                       (company, contact_id))
    store.conn.commit()


def alert_kinds(store, cid="camp1") -> str:
    return store.get_state(f"send_guard_alert:{cid}") or ""


# -- the approval writes the ledger atomically -----------------------------------

def test_approval_writes_decision_and_snapshot_in_one_unit(tmp_path):
    _, store = make_store(tmp_path)
    make_campaign(store, emails=("ada@example.test", "bob@example.test"), start=False)
    decision = approval.latest_decision(store, "camp1")
    assert decision["kind"] == "approve" and decision["snapshot_count"] == 2
    snaps = store.conn.execute(
        "SELECT * FROM approval_snapshots WHERE decision_id = ?",
        (decision["decision_id"],)).fetchall()
    assert {s["recipient"] for s in snaps} == {"ada@example.test", "bob@example.test"}
    for s in snaps:
        assert s["draft_sha256"] == approval.draft_sha256(s["subject"], s["body"])
        assert s["draft_epoch"] == 1
    campaign = store.get_campaign("camp1")
    assert campaign["draft_epoch"] == 1
    assert campaign["draft_manifest_sha256"] == decision["manifest_sha256"]


def test_failed_approval_writes_nothing(tmp_path, monkeypatch):
    """A failure after the decision row but before commit rolls back the
    status flip, pins and decision together."""
    _, store = make_store(tmp_path)
    make_campaign(store, approve=False, start=False)

    def boom(*a, **k):
        raise RuntimeError("disk full")

    monkeypatch.setattr(store, "approve_pending_enrollments", boom)
    with pytest.raises(RuntimeError):
        cadence.approve_campaign(store, "camp1", "tester", "camp1", now=NOW)
    assert store.get_campaign("camp1")["status"] == "draft"
    assert approval.latest_decision(store, "camp1") is None
    assert store.get_pins("camp1") == {}


# -- 1. stale epoch ---------------------------------------------------------------

def test_stale_epoch_approval_is_refused(tmp_path):
    _, store = make_store(tmp_path)
    make_campaign(store, approve=False, start=False)
    seen = cadence.approval_report(store, "camp1")["draft"]
    set_company(store, "c1", "Acme Holdings")   # the copy changes under the page
    res = cadence.approve_campaign(store, "camp1", "tester", "camp1", now=NOW,
                                  expected_manifest=seen["manifest_sha256"],
                                  expected_epoch=seen["draft_epoch"])
    assert res["ok"] is False and res["stale"] is True
    assert store.get_campaign("camp1")["status"] == "draft"
    assert approval.latest_decision(store, "camp1") is None
    fresh = cadence.approval_report(store, "camp1")["draft"]
    assert fresh["manifest_sha256"] != seen["manifest_sha256"]
    ok = cadence.approve_campaign(store, "camp1", "tester", "camp1", now=NOW,
                                 expected_manifest=fresh["manifest_sha256"],
                                 expected_epoch=fresh["draft_epoch"])
    assert ok["ok"] and ok["draft_epoch"] == fresh["draft_epoch"]


def test_stale_approval_refused_over_http_and_shown_on_panel(tmp_path, monkeypatch):
    monkeypatch.delenv("LEAD_DESK_AUTH_SECRET", raising=False)
    with ContactStore(tmp_path / "lead-desk.sqlite") as store:
        make_campaign(store, approve=False, start=False)
    client = TestClient(create_app(tmp_path))
    page = client.get("/campaigns/camp1").text
    manifest = re.search(r'name="draft_manifest" value="([0-9a-f]{64})"', page).group(1)
    epoch = re.search(r'name="draft_epoch" value="(\d+)"', page).group(1)
    assert manifest[:8] in page                        # hash prefix on the panel
    with ContactStore(tmp_path / "lead-desk.sqlite") as store:
        set_company(store, "c1", "Changed Co")
    r = client.post("/campaigns/camp1/approve", follow_redirects=True, data={
        "confirm": "camp1", "draft_manifest": manifest, "draft_epoch": epoch})
    assert r.status_code == 200
    assert "Approval refused: stale page" in r.text
    # no reviewed epoch at all: refused too
    client.post("/campaigns/camp1/approve", data={"confirm": "camp1"})
    with ContactStore(tmp_path / "lead-desk.sqlite") as store:
        assert store.get_campaign("camp1")["status"] == "draft"
        assert approval.latest_decision(store, "camp1") is None


def test_decision_on_old_epoch_releases_nothing(tmp_path):
    """Re-filing advances the epoch. A change that is reverted still leaves
    the old decision dead: only a new approval releases the message."""
    data, store = make_store(tmp_path)
    make_campaign(store)
    set_company(store, "c1", "Acme Holdings")
    m = FakeMailer()
    rep = tick(data, m)
    assert rep["claimed"] == 0 and m.sent == []
    assert "approval_stale" in alert_kinds(store)
    set_company(store, "c1", "Acme")               # back to the approved text
    rep = tick(data, m)
    assert rep["claimed"] == 0 and m.sent == []    # epoch 1 -> 3; decision was epoch 1
    assert store.get_attempt("cadence:1:1") is None
    assert cadence.approve_campaign(store, "camp1", "tester", "camp1")["ok"]
    assert cadence.start_sending(store, "camp1", "tester", "camp1")["ok"]
    rep = tick(data, m)
    assert rep["counters"]["sent"] == 1 and len(m.sent) == 1


# -- 2. concurrent claimants ---------------------------------------------------------

def test_concurrent_claimants_get_one_permission(tmp_path):
    data, store = make_store(tmp_path)
    make_campaign(store)
    db = data / "lead-desk.sqlite"
    n = 8
    barrier = threading.Barrier(n)
    results: list[int] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def worker(i):
        try:
            with ContactStore(db) as s:
                barrier.wait()
                got = cadence.claim_sends(s, f"w{i}", 5, at=IN_WINDOW)["claims"]
            with lock:
                results.append(len(got))
        except BaseException as exc:  # noqa: BLE001 - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert sum(results) == 1
    rows = store.conn.execute("SELECT state FROM dispatch_claims").fetchall()
    assert [r["state"] for r in rows] == ["claimed"]


def test_claim_insert_cannot_be_doubled_by_the_database(tmp_path):
    """Even a caller that skipped every check cannot hold two active claims
    for one obligation, or dispatch twice under one decision."""
    _, store = make_store(tmp_path)
    make_campaign(store)
    cadence.claim_sends(store, "w1", 5, at=IN_WINDOW)
    row = approval.latest_claim(store, "cadence:1:1")
    with pytest.raises(sqlite3.IntegrityError):
        store.conn.execute(
            "INSERT INTO dispatch_claims (attempt_key, decision_id, token, state, "
            "created_at, updated_at) VALUES (?, ?, 'x', 'claimed', ?, ?)",
            (row["attempt_key"], row["decision_id"], NOW, NOW))
    store.conn.rollback()


# -- 3. altered text or recipient ------------------------------------------------------

def test_altered_recipient_cannot_claim(tmp_path):
    data, store = make_store(tmp_path)
    make_campaign(store)
    store.conn.execute("UPDATE contacts SET email = 'eve@example.test' WHERE contact_id = 'c1'")
    store.conn.commit()
    m = FakeMailer()
    assert tick(data, m)["claimed"] == 0 and m.sent == []
    assert store.get_attempt("cadence:1:1") is None


def test_altered_text_after_claim_cannot_dispatch(tmp_path):
    """The claim was valid; the contact changed between claim and transport.
    begin_dispatch re-renders, refuses, cancels the claim and re-files."""
    data, store = make_store(tmp_path)
    make_campaign(store)
    send = cadence.claim_sends(store, WORKER_ID, 5, at=IN_WINDOW)["claims"][0]
    set_company(store, "c1", "Someone Else")
    m = FakeMailer()
    out = execute_one(store, m, send, Journal(data / "j.jsonl"), now=IN_WINDOW)
    assert out == "approval_refused" and m.sent == []
    assert approval.latest_claim(store, send["attempt_key"])["state"] == "cancelled"
    assert approval.get_draft(store, send["attempt_key"])["draft_epoch"] == 2
    assert store.get_attempt(send["attempt_key"])["status"] == "parked"


def test_tampered_payload_cannot_dispatch(tmp_path):
    """A payload whose text or recipient differs from the snapshot (hash kept
    consistent, so the older body-hash check passes) is refused."""
    data, store = make_store(tmp_path)
    make_campaign(store, emails=("ada@example.test", "bob@example.test"))
    first, second = cadence.claim_sends(store, WORKER_ID, 5, at=IN_WINDOW)["claims"]
    m = FakeMailer()
    j = Journal(data / "j.jsonl")
    # recipient swapped on a valid claim
    out = execute_one(store, m, dict(first, to="eve@example.test"), j, now=IN_WINDOW)
    assert out == "approval_refused" and m.sent == []
    assert approval.latest_claim(store, first["attempt_key"])["state"] == "cancelled"
    # text swapped on a valid claim, body_hash recomputed to match
    body = second["body"] + " PS: wire the money"
    evil = dict(second, body=body, body_hash=approval.draft_sha256(second["subject"], body))
    out = execute_one(store, m, evil, j, now=IN_WINDOW)
    assert out == "approval_refused" and m.sent == []
    assert approval.latest_claim(store, second["attempt_key"])["state"] == "cancelled"
    # a cancelled claim's token can never dispatch
    out = execute_one(store, m, second, j, now=IN_WINDOW)
    assert out == "approval_refused" and m.sent == []


def test_approved_bytes_are_what_gets_transported(tmp_path):
    data, store = make_store(tmp_path)
    make_campaign(store)
    m = FakeMailer()
    rep = tick(data, m)
    assert rep["counters"]["sent"] == 1
    snap = approval.bound_snapshot(store, "cadence:1:1")
    assert approval.draft_sha256(m.sent[0]["subject"], m.sent[0]["body"]) == snap["draft_sha256"]
    assert m.sent[0]["to"] == snap["recipient"]
    claim = approval.latest_claim(store, "cadence:1:1")
    assert claim["state"] == "delivered" and claim["dispatched_at"]


def test_snapshots_and_decisions_are_immutable(tmp_path):
    _, store = make_store(tmp_path)
    make_campaign(store)
    for sql in ("UPDATE approval_snapshots SET body = 'evil'",
                "DELETE FROM approval_snapshots",
                "UPDATE approval_decisions SET decided_by = 'evil'",
                "DELETE FROM approval_decisions"):
        with pytest.raises(sqlite3.IntegrityError):
            store.conn.execute(sql)
        store.conn.rollback()


# -- 4. unknown outcome ----------------------------------------------------------------

def test_unknown_outcome_blocks_retry_until_reconciled(tmp_path, monkeypatch):
    data, store = make_store(tmp_path)
    make_campaign(store)
    m = FakeMailer()
    m.send_exc = TimeoutError("read timed out after POST")
    rep = tick(data, m)
    akey = "cadence:1:1"
    assert rep["counters"]["ambiguous"] == 1
    assert store.get_attempt(akey)["status"] == "unknown"
    # no automatic retry: later ticks, lease expiry, nothing re-leases it
    m2 = FakeMailer()
    later = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    rep2 = run_tick(data, mailer=m2, poll_fn=no_events, at=later, sleep=lambda s: None)
    assert rep2["claimed"] == 0 and m2.sent == []
    assert store.get_attempt(akey)["status"] == "unknown"
    # the operator cannot Retry / Send fresh / Mark sent it either
    monkeypatch.delenv("LEAD_DESK_AUTH_SECRET", raising=False)
    client = TestClient(create_app(data))
    for route in ("/attempts/retry", "/attempts/send-fresh", "/attempts/mark-sent"):
        r = client.post(route, data={"attempt_key": akey, "campaign": "camp1"})
        assert r.status_code == 400, route
    # even a forced requeue in the DB cannot get past the claim table
    store.update_attempt(akey, {"status": "queued"})
    assert cadence.claim_sends(store, "w9", 5, at=later)["claims"] == []
    store.update_attempt(akey, {"status": "unknown"})
    # the page offers reconcile; evidence is mandatory
    page = client.get("/campaigns/camp1").text
    assert "/attempts/reconcile" in page
    r = client.post("/attempts/reconcile", data={
        "attempt_key": akey, "outcome": "not_delivered", "evidence": "",
        "campaign": "camp1"})
    assert r.status_code == 400
    r = client.post("/attempts/reconcile", data={
        "attempt_key": akey, "outcome": "not_delivered",
        "evidence": "Sent Items empty 09:00-12:00", "campaign": "camp1"})
    assert r.status_code in (200, 303)
    assert approval.latest_claim(store, akey)["state"] == "void"
    # voided under decision #1: Retry still refused until a new decision
    r = client.post("/attempts/retry", data={"attempt_key": akey, "campaign": "camp1"})
    assert r.status_code == 400 and "Re-approve" in r.text
    assert cadence.approve_campaign(store, "camp1", "tester", "camp1")["ok"]
    assert cadence.start_sending(store, "camp1", "tester", "camp1")["ok"]
    r = client.post("/attempts/retry", data={"attempt_key": akey, "campaign": "camp1"})
    assert r.status_code in (200, 303)
    m3 = FakeMailer()
    rep3 = run_tick(data, mailer=m3, poll_fn=no_events, at=later, sleep=lambda s: None)
    assert rep3["counters"]["sent"] == 1 and len(m3.sent) == 1


def test_lease_expiry_mid_dispatch_is_unknown_before_dispatch_is_cancelled(tmp_path):
    _, store = make_store(tmp_path)
    make_campaign(store, emails=("ada@example.test", "bob@example.test"))
    sends = cadence.claim_sends(store, WORKER_ID, 5, at=IN_WINDOW)["claims"]
    assert len(sends) == 2
    # the first worker got past begin_dispatch, then died
    approval.begin_dispatch(store, sends[0]["claim_token"], sends[0], now_iso())
    later = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    store.expire_leases(cadence._iso(later))
    assert approval.latest_claim(store, sends[0]["attempt_key"])["state"] == "unknown"
    assert store.get_attempt(sends[0]["attempt_key"])["status"] == "unknown"
    assert approval.latest_claim(store, sends[1]["attempt_key"])["state"] == "cancelled"
    assert store.get_attempt(sends[1]["attempt_key"])["status"] == "stalled"


def test_claim_transitions_are_enforced_by_the_database(tmp_path):
    _, store = make_store(tmp_path)
    make_campaign(store)
    cadence.claim_sends(store, "w1", 5, at=IN_WINDOW)
    row = approval.latest_claim(store, "cadence:1:1")
    for sql in ("UPDATE dispatch_claims SET state = 'delivered'",
                "UPDATE dispatch_claims SET state = 'unknown'",
                "UPDATE dispatch_claims SET token = 'forged'",
                "DELETE FROM dispatch_claims"):
        with pytest.raises(sqlite3.IntegrityError):
            store.conn.execute(sql)
        store.conn.rollback()
    assert approval.latest_claim(store, "cadence:1:1")["token"] == row["token"]


def test_graph_error_reported_through_result_api_after_dispatch_is_unknown(tmp_path):
    """The HTTP result path cannot requeue a send whose dispatch began."""
    _, store = make_store(tmp_path)
    make_campaign(store)
    send = cadence.claim_sends(store, WORKER_ID, 5, at=IN_WINDOW)["claims"][0]
    approval.begin_dispatch(store, send["claim_token"], send, now_iso())
    res = cadence.resolve_result(store, {
        "attempt_key": send["attempt_key"], "lease_id": send["lease_id"],
        "status": "failed", "error_class": "transient", "failure_reason": "503"})
    assert res.get("unknown") is True and res["requeued"] is False
    assert store.get_attempt(send["attempt_key"])["status"] == "unknown"


def test_sequence_delta_snapshots_only_the_new_steps(tmp_path):
    data, store = make_store(tmp_path)
    make_campaign(store)
    m = FakeMailer()
    assert tick(data, m)["counters"]["sent"] == 1   # step 1 went
    store.save_template("t2", "email", "Follow up", "Second note for {{company}}",
                        "tester", NOW)
    res = cadence.apply_sequence_delta(store, "camp1", "cold", [
        {"channel": "email", "template_key": "t1", "day_offset": 0},
        {"channel": "email", "template_key": "t2", "day_offset": 0}], "tester")
    assert res["ok"] and res["snapshots"] == 1
    decision = approval.latest_decision(store, "camp1")
    assert decision["kind"] == "sequence_delta"
    step2 = f"cadence:1:{res['added'][0]['step_no']}"
    assert approval.bound_snapshot(store, step2)["decision_id"] == decision["decision_id"]
    # the already-sent step keeps its original approval
    assert approval.bound_snapshot(store, "cadence:1:1")["decision_id"] < decision["decision_id"]
