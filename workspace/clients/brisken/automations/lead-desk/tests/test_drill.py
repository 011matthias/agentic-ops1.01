"""Arming-drill CLI: the refusal guards on the sending steps, the step-4
verify pass, and the readiness-audit fields. FakeMailer pattern from
test_cloud_worker - no network, no Graph.
"""
from __future__ import annotations

import json

from lead_desk import drill
from lead_desk.cloud_worker import _capture_state_path
from lead_desk.graph_mail import SEND_FROM
from lead_desk.web.service import ingest_event, now_iso
from lead_desk.web.store import ContactStore


class FakeMailer:
    """Records calls; behavior configured per test."""

    def __init__(self):
        self.sent: list[dict] = []
        self.evidence: dict | None = None

    def send_auto(self, send):
        self.sent.append(send)

    def readback_sent(self, mailbox, to, subject, since, **kw):
        return self.evidence


def make_data(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    return data


def make_contact(store, cid, email):
    store.upsert_contact(
        {"contact_id": cid, "natural_key": cid, "campaign": "rome-2026",
         "first_name": "First", "last_name": "Last", "company": "Co",
         "email": email}, now_iso())


# -- sending-step refusal guards ---------------------------------------------

def test_step3_refuses_known_contact_address(tmp_path, capsys):
    data = make_data(tmp_path)
    with ContactStore(data / "lead-desk.sqlite") as store:
        make_contact(store, "c1", SEND_FROM)  # self enrolled as a contact row
    m = FakeMailer()
    assert drill.step3(data, SEND_FROM, mailer=m) == 2
    assert m.sent == []
    assert "REFUSED" in capsys.readouterr().out


def test_step3_refuses_non_self_recipient(tmp_path, capsys):
    data = make_data(tmp_path)
    m = FakeMailer()
    assert drill.step3(data, "someone.else@example.com", mailer=m) == 2
    assert m.sent == []
    out = capsys.readouterr().out
    assert "REFUSED" in out and SEND_FROM in out


def test_step4_refuses_known_contact_address(tmp_path, capsys):
    data = make_data(tmp_path)
    with ContactStore(data / "lead-desk.sqlite") as store:
        make_contact(store, "c1", "real.prospect@example.com")
    m = FakeMailer()
    assert drill.step4(data, "real.prospect@example.com", mailer=m) == 2
    assert m.sent == []
    assert "REFUSED" in capsys.readouterr().out


# -- step 4 verify ------------------------------------------------------------

def test_step4_verify_passes_on_bounce_plus_suppression(tmp_path, capsys):
    data = make_data(tmp_path)
    addr = "drill-nobody@invalid-example.com"
    m = FakeMailer()
    assert drill.step4(data, addr, mailer=m) == 0
    assert len(m.sent) == 1 and m.sent[0]["to"] == addr
    assert m.sent[0]["subject"].startswith(drill.DRILL_SUBJECT_PREFIX)
    # repeatable: the registered drill contact is admitted, a prospect is not
    assert drill.step4(data, addr, mailer=FakeMailer()) == 0

    # not yet bounced -> FAIL
    assert drill.step4_verify(data, addr) == 1

    # the captured NDR arrives: the sink records the bounce + auto-suppresses
    with ContactStore(data / "lead-desk.sqlite") as store:
        res = ingest_event(store, {
            "email": addr, "type": "bounce", "direction": "inbound",
            "channel": "email", "occurred_at": "2026-07-15T09:10:00+00:00",
            "subject": "Undeliverable: LEAD DESK ARMING DRILL step4",
            "source": "graph-auto", "internet_message_id": "<ndr-drill>"})
        assert res["ok"] and res.get("inserted")
    assert drill.step4_verify(data, addr) == 0
    assert "PASS step4-verify" in capsys.readouterr().out


# -- readiness audit -----------------------------------------------------------

def test_status_reports_readiness_fields(tmp_path):
    data = make_data(tmp_path)
    now = now_iso()
    with ContactStore(data / "lead-desk.sqlite") as store:
        store.set_state("kill_switch", "1", now)
        store.set_state("send_guard_alert:camp1",
                        json.dumps({"at": now, "count": 2}), now)
        store.set_state("worker_heartbeat",
                        json.dumps({"worker_id": "w", "ts": now}), now)
        # one drafted + one parked attempt hanging off a real enrollment
        make_contact(store, "c1", "c1@example.com")
        store.create_campaign("camp1", "Camp", now)
        store.enroll("c1", "camp1", "tester", now)
        eid = store.find_enrollment("c1", "camp1")["enrollment_id"]
        for key, st in (("a1", "drafted"), ("a2", "parked")):
            store.conn.execute(
                "INSERT INTO send_attempts (attempt_key, enrollment_id, "
                "step_no, status) VALUES (?, ?, 1, ?)", (key, eid, st))
        store.conn.commit()
    _capture_state_path(data).write_text(
        json.dumps({"watermarks": {SEND_FROM: now}}), encoding="utf-8")

    rep = drill.status_report(data)
    assert rep["kill_switch"] is True
    assert rep["guard_alerts"]["camp1"]["count"] == 2
    assert rep["drafted"] == 1 and rep["parked"] == 1
    assert rep["heartbeat_age_minutes"] is not None
    assert rep["heartbeat_age_minutes"] < 5
    assert rep["capture_watermark_age_minutes"] is not None
    assert rep["capture_watermark_age_minutes"] < 5
    assert rep["sending_campaigns"] == []  # 'draft' status campaign only
