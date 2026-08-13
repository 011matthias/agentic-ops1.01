"""T6: the truth-surface UI. Board freshness strip + persisted alert
surfacing, the /unmatched review page (link / dismiss), the /sheet
all-contacts view, timeline evidence chips, and the export column extension.
Rendered over HTTP like test_webflow (gate disabled, user 'local')."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from lead_desk.cloud_worker import _capture_state_path
from lead_desk.export import EXPORT_COLUMNS, to_csv_bytes
from lead_desk.web.app import create_app
from lead_desk.web.service import ingest_event, now_iso
from lead_desk.web.store import ContactStore


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


def _unmatched(store, email: str, *, type="reply", direction="inbound",
               subject="Re: Rome", imid="<u1@x>") -> dict:
    return ingest_event(store, {
        "email": email, "type": type, "direction": direction,
        "channel": "email", "occurred_at": "2026-07-14T10:00:00+00:00",
        "subject": subject, "source": "graph-auto",
        "internet_message_id": imid,
    })


# -- board freshness + alerts --------------------------------------------------

def test_board_freshness_from_state(client):
    # Empty state: the strip reads stale/never (and the old hard-coded FALSE
    # "no live mail capture yet" banner is gone for good).
    r = client.get("/")
    assert r.status_code == 200
    assert "Stage may be stale" not in r.text
    assert "capture never" in r.text and "deep scan never" in r.text
    assert 'class="badge suppressed"' in r.text          # stale color class

    now = datetime.now(timezone.utc)
    with _store(client) as s:
        s.set_state("worker_heartbeat", json.dumps(
            {"worker_id": "w", "ts": now.isoformat(timespec="seconds"),
             "counters": {"sent": 0}}), now_iso())
        s.set_state("truth_scan_heartbeat", json.dumps(
            {"ts": now.isoformat(timespec="seconds"),
             "counts": {"folders_scanned": 12, "inserted": 3}}), now_iso())
    _capture_state_path(client.data_root).write_text(json.dumps({
        "watermarks": {"matthias.silva@brisken.com":
                       (now - timedelta(minutes=30)).isoformat(timespec="seconds")}}),
        encoding="utf-8")

    r = client.get("/")
    assert r.status_code == 200
    assert "capture 0m ago" in r.text and "deep scan 0m ago" in r.text
    assert 'class="badge stage-booked"' in r.text        # fresh color class
    assert "matthias.silva 30m" in r.text                # per-mailbox watermark
    assert "folders_scanned 12" in r.text                # scan counts render


def test_board_renders_worker_alert(client):
    with _store(client) as s:
        s.set_state("cloud_worker_alert", json.dumps(
            {"ts": "2026-07-15T09:00:00+00:00",
             "alerts": ["AMBIGUOUS send cadence:9:1 crashed inside the send window"]}),
            now_iso())
        s.set_state("send_guard_alert:rome-2026", json.dumps(
            {"at": "2026-07-15T09:00:00+00:00", "count": 2,
             "blocked": [{"contact_id": "c1", "kind": "recipient_drift",
                          "detail": "approved a, now b; re-approve"}]}), now_iso())
    r = client.get("/")
    assert r.status_code == 200
    assert "Worker alert" in r.text
    assert "AMBIGUOUS send cadence:9:1" in r.text
    assert "Send guard" in r.text and "[rome-2026]" in r.text
    # The campaign page surfaces its own guard alert with the block detail.
    with _store(client) as s:
        s.create_campaign("rome-2026", "Rome 2026", now_iso())
    r = client.get("/campaigns/rome-2026")
    assert "Send guard alert" in r.text
    assert "recipient_drift" in r.text and "re-approve" in r.text


# -- /unmatched ---------------------------------------------------------------

def test_unmatched_page_lists_open_groups(client):
    with _store(client) as s:
        for _ in range(2):                    # re-poll of the same message
            _unmatched(s, "ghost@corp.com", imid="<g1@corp>")
        _unmatched(s, "other@corp.com", type="sent", direction="outbound",
                   subject="Rome intro", imid="<g2@corp>")
    r = client.get("/unmatched")
    assert r.status_code == 200
    assert "ghost@corp.com" in r.text and "other@corp.com" in r.text
    assert "2&times;" in r.text                          # seen_count bumped
    assert "Re: Rome" in r.text and "inbound" in r.text  # latest payload preview


def test_unmatched_link_action_replays(client):
    with _store(client) as s:
        _contact(s, "c1", "ann@corp.com", first_name="Ann", last_name="A")
        _unmatched(s, "ann.alt@corp.com", imid="<a1@corp>")
        _unmatched(s, "ann.alt@corp.com", type="sent", direction="outbound",
                   subject="Rome intro", imid="<a2@corp>")
    r = client.post("/unmatched/link",
                    data={"email": "ann.alt@corp.com", "contact_id": "c1",
                          "set_alt_email": "1"},
                    follow_redirects=False)
    assert r.status_code == 303
    with _store(client) as s:
        assert s.list_unmatched("open") == []
        linked = s.list_unmatched("linked")
        assert len(linked) == 2
        assert {x["resolved_contact_id"] for x in linked} == {"c1"}
        assert {x["resolved_by"] for x in linked} == {"local"}   # audited
        types = {e["type"] for e in s.get_events("c1")}
        assert {"reply", "sent"} <= types                # payloads replayed
        assert s.get_contact("c1")["alt_email"] == "ann.alt@corp.com"


def test_unmatched_dismiss_requires_reason(client):
    with _store(client) as s:
        _unmatched(s, "ghost@corp.com", imid="<d1@corp>")
    r = client.post("/unmatched/dismiss",
                    data={"email": "ghost@corp.com", "reason": "  "})
    assert r.status_code == 400
    with _store(client) as s:
        assert len(s.list_unmatched("open")) == 1        # still open
    r = client.post("/unmatched/dismiss",
                    data={"email": "ghost@corp.com", "reason": "spam vendor"},
                    follow_redirects=False)
    assert r.status_code == 303
    with _store(client) as s:
        assert s.list_unmatched("open") == []
        row = s.list_unmatched("dismissed")[0]
        assert row["resolved_by"] == "local: spam vendor"


# -- /sheet -------------------------------------------------------------------

def test_sheet_page_renders_all_contacts_incl_suppressed(client):
    with _store(client) as s:
        s.create_campaign("rome-2026", "Rome 2026", now_iso())
        _contact(s, "c1", "ann@corp.com", first_name="Ann", last_name="Active",
                 company="Acme", tier="T1")
        _contact(s, "c2", "sup@corp.com", first_name="Sue", last_name="Stopped",
                 company="Beta", suppressed=1, suppress_reason="stop")
        s.update_fields("c1", {"outreach_status": "In conversation"}, now_iso())
    r = client.get("/sheet")
    assert r.status_code == 200
    assert "Ann Active" in r.text and "Sue Stopped" in r.text
    assert 'class="suppressed"' in r.text                # muted row
    assert "In conversation" in r.text                   # sheet-status column
    assert "rome-2026" in r.text                         # campaign column
    r = client.get("/sheet?sort=name&dir=desc")          # header-link sort
    assert r.status_code == 200
    assert r.text.index("Sue Stopped") < r.text.index("Ann Active")


def test_export_columns_extended_stable_order(client):
    legacy = [
        "contact_id", "tier", "lead_type", "stage", "status", "suppressed",
        "suppress_reason", "first_name", "last_name", "company", "job_title",
        "email", "alt_email", "phone", "country", "linkedin_url", "crm_owner",
        "next_step", "next_step_due", "last_out", "last_in", "demo_date",
        "dirk_verdict", "bant_need", "bant_authority", "bant_timeline",
        "bant_budget", "source", "tier_reason", "dirk_notes",
    ]
    assert EXPORT_COLUMNS[:len(legacy)] == legacy        # order stable
    assert set(EXPORT_COLUMNS[len(legacy):]) == {"campaign", "outreach_status"}
    with _store(client) as s:
        s.create_campaign("rome-2026", "Rome 2026", now_iso())
        _contact(s, "c1", "ann@corp.com", first_name="Ann", last_name="A")
        s.update_fields("c1", {"outreach_status": "Sent"}, now_iso())
        header, row = to_csv_bytes(s).decode("utf-8").splitlines()[:2]
    assert header.split(",") == EXPORT_COLUMNS
    cells = row.split(",")
    assert cells[EXPORT_COLUMNS.index("campaign")] == "rome-2026"
    assert cells[EXPORT_COLUMNS.index("outreach_status")] == "Sent"
    # /sheet.csv is an alias of the one exporter, same columns.
    r = client.get("/sheet.csv")
    assert r.status_code == 200
    assert r.text.splitlines()[0] == ",".join(EXPORT_COLUMNS)


# -- timeline evidence chips ---------------------------------------------------

def test_contact_timeline_evidence_chips(client):
    with _store(client) as s:
        _contact(s, "c1", "ann@corp.com", first_name="Ann", last_name="A")
        s.add_event(contact_id="c1", ts="2026-07-10T09:00:00+00:00",
                    channel="email", direction="outbound", type="sent",
                    subject="Rome intro",
                    detail=json.dumps({"folder": "Inbox/Companies/Acme",
                                       "cohort": "H5",
                                       "internet_message_id": "<im-9@brisken>"}),
                    source="graph-auto", now=now_iso())
        s.add_event(contact_id="c1", ts="2026-07-11T09:00:00+00:00",
                    channel="email", direction="inbound", type="reply",
                    subject="Re: Rome intro", detail="auto: inbound reply",
                    source="graph-auto", now=now_iso())
    r = client.get("/contacts/c1")
    assert r.status_code == 200
    assert "Inbox/Companies/Acme" in r.text              # folder chip
    assert 'title="cohort">H5' in r.text                 # cohort chip
    assert "&lt;im-9@brisken&gt;" in r.text              # imid dot title
    assert "auto: inbound reply" in r.text               # plain detail untouched
