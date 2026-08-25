"""Send-safety guards (rule_brisken_graph_send_by_id ported into the engine).

A campaign send only ever goes to an address a human froze at approval, never
to a hard-denied domain, and only under approved (pinned) copy. The claim path
blocks any breach and surfaces a per-campaign alert; the worker re-checks the
denied-domain floor before the Graph POST. Framework-free over a tmp_path
ContactStore, mirroring test_outbox / test_cloud_worker fixtures.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from lead_desk.cloud_worker import WORKER_ID, execute_one
from lead_desk.web import cadence
from lead_desk.web.service import now_iso
from lead_desk.web.store import ContactStore
from lead_desk.worker.journal import Journal

IN_WINDOW = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)
BASE = "2026-07-14T09:00:00+00:00"


def _store(tmp_path) -> ContactStore:
    data = tmp_path / "data"
    data.mkdir()
    return ContactStore(data / "lead-desk.sqlite")


def make_contact(store, cid, email):
    store.upsert_contact(
        {"contact_id": cid, "natural_key": cid, "campaign": "rome-2026",
         "first_name": f"F{cid}", "last_name": f"L{cid}", "company": f"Co{cid}",
         "email": email}, now_iso())
    return cid


def make_campaign(store, cid="camp1", *, emails, degree="cold",
                  send_mode="auto-matthias", approve=True, start=True):
    store.create_campaign(cid, "Guarded Campaign", BASE, daily_cap=40)
    store.save_template("t1", "email", "Hi {{first_name}}", "Body {{company}}", "t", BASE)
    store.upsert_sequence(cid, degree, f"{degree} seq", send_mode,
                          [{"step_no": 1, "channel": "email",
                            "template_key": "t1", "day_offset": 0}])
    for i, email in enumerate(emails, 1):
        contact_id = make_contact(store, f"c{i}", email)
        store.enroll(contact_id, cid, "t", BASE)
        enr = store.find_enrollment(contact_id, cid)
        store.set_degree(enr["enrollment_id"], degree, "manual", "test")
    if approve:
        assert cadence.approve_campaign(store, cid, "t", cid, now=BASE)["ok"]
        if start:
            assert cadence.start_sending(store, cid, "t", cid, now=BASE)["ok"]
    return cid


def _set_email(store, contact_id, email):
    store.conn.execute("UPDATE contacts SET email = ? WHERE contact_id = ?",
                       (email, contact_id))
    store.conn.commit()


def _alert(store, cid="camp1"):
    raw = store.get_state(f"send_guard_alert:{cid}")
    return json.loads(raw) if raw else None


# -- happy path ---------------------------------------------------------------

def test_pinned_recipient_sends(tmp_path):
    store = _store(tmp_path)
    make_campaign(store, emails=["a@example.com"])
    res = cadence.claim_sends(store, WORKER_ID, 5, at=IN_WINDOW)
    assert len(res["claims"]) == 1
    assert res["claims"][0]["to"] == "a@example.com"
    assert _alert(store) is None


def test_approval_writes_recipient_pins(tmp_path):
    store = _store(tmp_path)
    make_campaign(store, emails=["a@example.com", "b@example.com"])
    pins = store.get_recipient_pins("camp1")
    assert set(pins.values()) == {"a@example.com", "b@example.com"}


# -- the drift hole (the verified defect) -------------------------------------

def test_recipient_drift_blocks_and_alerts(tmp_path):
    store = _store(tmp_path)
    make_campaign(store, emails=["a@example.com"])
    # Simulate a post-approval sheet-sync overwriting the address.
    _set_email(store, "c1", "attacker@evil.com")
    res = cadence.claim_sends(store, WORKER_ID, 5, at=IN_WINDOW)
    assert res["claims"] == []
    alert = _alert(store)
    assert alert and alert["count"] == 1
    assert alert["blocked"][0]["kind"] == "recipient_drift"


def test_reapproval_updates_pin_and_unblocks(tmp_path):
    store = _store(tmp_path)
    make_campaign(store, emails=["a@example.com"])
    _set_email(store, "c1", "a.new@example.com")
    assert cadence.claim_sends(store, WORKER_ID, 5, at=IN_WINDOW)["claims"] == []
    # Owner reviews the new address and re-approves + re-starts.
    assert cadence.approve_campaign(store, "camp1", "t", "camp1", now=BASE)["ok"]
    assert cadence.start_sending(store, "camp1", "t", "camp1", now=BASE)["ok"]
    res = cadence.claim_sends(store, WORKER_ID, 5, at=IN_WINDOW)
    assert [c["to"] for c in res["claims"]] == ["a.new@example.com"]
    assert _alert(store) is None  # stale alert cleared on the clean pass


# -- denied domains -----------------------------------------------------------

def test_denied_domain_blocks(tmp_path):
    store = _store(tmp_path)
    make_campaign(store, emails=["treasury@sap.com"])
    res = cadence.claim_sends(store, WORKER_ID, 5, at=IN_WINDOW)
    assert res["claims"] == []
    assert _alert(store)["blocked"][0]["kind"] == "domain_denied"


def test_state_deny_domains_extends_floor(tmp_path):
    store = _store(tmp_path)
    make_campaign(store, emails=["x@competitor.io"])
    store.set_state("send_deny_domains", json.dumps(["competitor.io"]), BASE)
    res = cadence.claim_sends(store, WORKER_ID, 5, at=IN_WINDOW)
    assert res["claims"] == []
    assert _alert(store)["blocked"][0]["kind"] == "domain_denied"


def test_malformed_deny_state_falls_back_to_floor(tmp_path):
    store = _store(tmp_path)
    store.set_state("send_deny_domains", "not json", BASE)
    assert cadence.deny_domains(store) == {"sap.com", "brisken.com"}


# -- suppression list (imported ledger) ---------------------------------------

def test_claim_blocks_suppression_list_email_and_domain(tmp_path):
    store = _store(tmp_path)
    make_campaign(store, emails=["blocked@x.com", "b@heldco.com",
                                 "ok@example.com"])
    store.add_suppression_entry("blocked@x.com", "email", "test", BASE)
    store.add_suppression_entry("@heldco.com", "domain", "test", BASE)
    res = cadence.claim_sends(store, WORKER_ID, 5, at=IN_WINDOW)
    assert [c["to"] for c in res["claims"]] == ["ok@example.com"]
    alert = _alert(store)
    assert alert["count"] == 2
    assert {b["kind"] for b in alert["blocked"]} == {"suppression-list"}


# -- unpinned template leak ---------------------------------------------------

def test_unpinned_template_blocks(tmp_path):
    store = _store(tmp_path)
    make_campaign(store, emails=["a@example.com"])
    # Simulate a step whose template_key never got pinned (the get_template(key,
    # None) -> latest leak): wipe the pin, keep the campaign sending.
    store.pin_templates("camp1", {})
    res = cadence.claim_sends(store, WORKER_ID, 5, at=IN_WINDOW)
    assert res["claims"] == []
    assert _alert(store)["blocked"][0]["kind"] == "unpinned_template"


# -- peek must not mutate state ----------------------------------------------

def test_peek_does_not_write_alert(tmp_path):
    store = _store(tmp_path)
    make_campaign(store, emails=["a@example.com"])
    _set_email(store, "c1", "attacker@evil.com")
    cadence.claim_sends(store, WORKER_ID, 5, at=IN_WINDOW, peek=True)
    assert _alert(store) is None


# -- worker execute-time backstop (immutable floor) ---------------------------

def test_worker_backstop_denies_sap_recipient(tmp_path):
    store = _store(tmp_path)
    make_campaign(store, emails=["a@example.com"])
    claims = cadence.claim_sends(store, WORKER_ID, 5, at=IN_WINDOW)["claims"]

    class Mailer:
        def __init__(self):
            self.sent = []

        def send_auto(self, send):
            self.sent.append(send)

    m = Mailer()
    # Even if a claim somehow carried a denied recipient, the worker refuses it.
    send = dict(claims[0], to="treasury@sap.com")
    out = execute_one(store, m, send, Journal(tmp_path / "j.jsonl"), now=IN_WINDOW)
    assert out == "recipient_denied"
    assert m.sent == []


def test_worker_backstop_denies_suppressed_recipient(tmp_path):
    store = _store(tmp_path)
    make_campaign(store, emails=["a@example.com"])
    claims = cadence.claim_sends(store, WORKER_ID, 5, at=IN_WINDOW)["claims"]

    class Mailer:
        def __init__(self):
            self.sent = []

        def send_auto(self, send):
            self.sent.append(send)

    m = Mailer()
    # An entry imported between claim and execution still never reaches Graph.
    store.add_suppression_entry("a@example.com", "email", "test", BASE)
    out = execute_one(store, m, claims[0], Journal(tmp_path / "j.jsonl"),
                      now=IN_WINDOW)
    assert out == "recipient_suppressed"
    assert m.sent == []
