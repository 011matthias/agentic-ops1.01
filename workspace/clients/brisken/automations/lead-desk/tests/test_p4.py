"""P4: engine-safety legibility - kill-switch surfacing, retry reset, and the
done-campaign approval guard."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lead_desk.web import cadence
from lead_desk.web.app import create_app
from lead_desk.web.service import build_board, now_iso
from lead_desk.web.store import ContactStore

NOW = "2026-07-16T00:00:00+00:00"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("LEAD_DESK_ACCESS_CODES", raising=False)
    c = TestClient(create_app(tmp_path))
    c.db = tmp_path / "lead-desk.sqlite"
    return c


def test_build_board_reports_kill_switch(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        s.create_campaign("rome-2026", "Rome", NOW, status="done")
        assert build_board(s, {})["kill_switch"] is False
        s.set_state("kill_switch", "1", NOW)
        assert build_board(s, {})["kill_switch"] is True


def test_approve_campaign_blocks_done(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        s.create_campaign("rome-2026", "Rome", NOW, status="done")
        res = cadence.approve_campaign(s, "rome-2026", "matthias", "rome-2026")
        assert res["ok"] is False
        assert any("done" in e.lower() for e in res["errors"])


def test_attempt_retry_resets_count(client):
    # seed a campaign + enrollment + a stalled attempt that exhausted its cap
    with ContactStore(client.db) as s:
        s.create_campaign("c", "C", NOW, status="sending")
        s.upsert_contact({"contact_id": "x", "natural_key": "x@y.com",
                          "email": "x@y.com", "campaign": "c"}, now=NOW)
        s.enroll("x", "c", "t", NOW)
        enr = s.find_enrollment("x", "c")["enrollment_id"]
        s.conn.execute(
            "INSERT INTO send_attempts (attempt_key, enrollment_id, step_no, status, "
            "attempt_count, failure_reason) VALUES ('c:1:0', ?, 0, 'stalled', 3, 'gave up')",
            (enr,))
        s.conn.commit()
    r = client.post("/attempts/retry", data={"attempt_key": "c:1:0", "campaign": "c"},
                    follow_redirects=False)
    assert r.status_code == 303
    with ContactStore(client.db) as s:
        a = s.get_attempt("c:1:0")
        assert a["status"] == "queued"
        assert a["attempt_count"] == 0          # reset, so try_lease can re-lease it
        assert a["failure_reason"] is None


def test_campaigns_page_kill_switch_affordance(client):
    with ContactStore(client.db) as s:
        s.create_campaign("c", "C", NOW, status="done")
        s.set_state("kill_switch", "1", NOW)
    r = client.get("/campaigns")
    assert r.status_code == 200
    assert "SENDING BLOCKED" in r.text and "Re-enable sending" in r.text
