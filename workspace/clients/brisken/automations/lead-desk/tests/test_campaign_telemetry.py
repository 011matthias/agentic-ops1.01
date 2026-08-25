"""O6: the campaign-page Engine telemetry card. Worker liveness + last-tick
counters, outbox attempts by status with the cap/ramp meters, capture-grounded
inbound since approval, and the staged-wave summary line. Rendered over HTTP
like test_truth_ui (gate disabled, user 'local')."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from lead_desk.web.app import create_app
from lead_desk.web.service import now_iso
from lead_desk.web.store import ContactStore, attempt_key_for


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("LEAD_DESK_AUTH_SECRET", raising=False)
    app = create_app(tmp_path)
    c = TestClient(app)
    c.data_root = tmp_path
    c.db = tmp_path / "lead-desk.sqlite"
    return c


def _store(client) -> ContactStore:
    return ContactStore(client.db)


def _contact(store, cid: str, email: str, **extra) -> None:
    store.upsert_contact({"contact_id": cid, "natural_key": email,
                          "campaign": "rome-2026", "email": email, **extra},
                         now_iso())


def _enroll(store, cid: str, campaign: str) -> int:
    store.enroll(cid, campaign, "test", now_iso())
    return int(store.find_enrollment(cid, campaign)["enrollment_id"])


def _attempt(store, eid: int, step_no: int, status: str,
             to: str = "x@corp.com", **fields) -> str:
    akey = attempt_key_for(eid, step_no)
    store.try_lease(
        attempt_key=akey, enrollment_id=eid, step_no=step_no,
        send_mode="auto-matthias", lease_id="l", lease_expires="2099-01-01",
        worker_id="w", to_addr=to, rendered_subject="Rome intro",
        rendered_body="b", template_key="t", template_version=1, now=now_iso(),
    )
    if status != "leased" or fields:
        store.update_attempt(akey, {"status": status, **fields})
    return akey


def test_engine_card_renders_attempt_aggregates(client):
    now = datetime.now(timezone.utc)
    with _store(client) as s:
        s.create_campaign("rome-2026", "Rome 2026", now_iso())
        s.update_campaign("rome-2026", {"ramp_per_day": 5}, now_iso())
        for i, status in enumerate(("queued", "sent", "parked"), start=1):
            cid = f"c{i}"
            _contact(s, cid, f"p{i}@corp.com", first_name=f"P{i}", last_name="X")
            eid = _enroll(s, cid, "rome-2026")
            _attempt(s, eid, 1, status)
            if status == "sent":
                # A landed step-1 send TODAY (engine clock pinned to
                # 2026-07-15): feeds both the cap and the ramp meter.
                s.add_event(contact_id=cid, ts="2026-07-15T08:00:00+00:00",
                            channel="email", direction="outbound", type="sent",
                            subject="Rome intro", source="worker-auto",
                            ext_key=attempt_key_for(eid, 1),
                            campaign="rome-2026", now=now_iso())
        s.set_state("worker_heartbeat", json.dumps(
            {"worker_id": "w", "ts": now.isoformat(timespec="seconds"),
             "counters": {"claimed": 2, "capture_inserted": 3}}), now_iso())
    r = client.get("/campaigns/rome-2026")
    assert r.status_code == 200
    assert "worker tick 0m ago" in r.text                # fresh heartbeat badge
    assert "claimed 2" in r.text and "capture_inserted 3" in r.text  # counters
    assert "queued 1" in r.text and "parked 1" in r.text  # attempts by status
    assert "drafted 0" in r.text                          # zero statuses render
    assert "sends today 1/40" in r.text                   # landed vs daily cap
    assert "new contacts today 1/5" in r.text             # step-1 vs ramp


def test_engine_card_shows_capture_grounded_inbound(client):
    with _store(client) as s:
        s.create_campaign("rome-2026", "Rome 2026", now_iso())
        _contact(s, "c1", "ann@corp.com", first_name="Ann", last_name="A")
        _contact(s, "c2", "bob@corp.com", first_name="Bob", last_name="B")
        _enroll(s, "c1", "rome-2026")
        _enroll(s, "c2", "rome-2026")
        s.update_campaign("rome-2026", {
            "status": "approved", "approved_at": "2026-07-10T00:00:00+00:00",
            "approved_by": "test"}, now_iso())
        # A reply BEFORE approval is excluded; a reply + a bounce after count.
        s.add_event(contact_id="c1", ts="2026-07-09T10:00:00+00:00",
                    channel="email", direction="inbound", type="reply",
                    subject="Re: old thread", source="graph-auto", now=now_iso())
        s.add_event(contact_id="c1", ts="2026-07-12T10:00:00+00:00",
                    channel="email", direction="inbound", type="reply",
                    subject="Re: Rome intro", source="graph-auto", now=now_iso())
        s.add_event(contact_id="c2", ts="2026-07-13T10:00:00+00:00",
                    channel="email", direction="inbound", type="bounce",
                    subject="Undeliverable", source="graph-auto", now=now_iso())
    r = client.get("/campaigns/rome-2026")
    assert r.status_code == 200
    assert "inbound since approval: 1 reply, 1 bounce" in r.text


def test_engine_card_staged_wave_line(client):
    with _store(client) as s:
        s.create_campaign("rome-2026", "Rome 2026", now_iso())
        _contact(s, "c1", "ann@corp.com", first_name="Ann", last_name="A")
        eid = _enroll(s, "c1", "rome-2026")
        s.pin_recipients("rome-2026", {"c1": "ann@corp.com"})
        _attempt(s, eid, 1, "drafted", to="ann@corp.com",
                 entry_id="EID-1", resolved_at="2026-07-10T09:00:00+00:00")
    r = client.get("/campaigns/rome-2026")
    assert r.status_code == 200
    # Summary line on the Engine card (engine clock pinned to 2026-07-15).
    assert "Staged wave: 1 draft(s) in Dirk's Drafts" in r.text
    assert "oldest 5d" in r.text
    assert 'href="#staged-wave"' in r.text               # links the staged card
    assert 'id="staged-wave"' in r.text                  # which still renders
    assert "drafted 1" in r.text                         # and the status badge
