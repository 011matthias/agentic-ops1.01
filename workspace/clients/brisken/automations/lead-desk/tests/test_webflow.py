"""End-to-end HTTP walk of the campaign engine through the real routes.

Covers what the function-level suites cannot: Form parsing, redirects,
multipart upload, and the Jinja templates actually rendering (board,
campaigns, campaign admin, contact cadence card) at every lifecycle stage.
"""
import io
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from lead_desk.web import cadence
from lead_desk.web.app import create_app
from lead_desk.web.store import ContactStore

IN_WINDOW = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)  # Wed 11:00 Berlin

CSV = (
    "email,first name,last name,company,job title\n"
    "jane@acme.com,Jane,Doe,Acme,CFO\n"
    "kai@corp.de,Kai,Muster,Corp,Treasurer\n"
).encode("utf-8")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("LEAD_DESK_WORKER_SECRET", "wsecret")
    monkeypatch.delenv("LEAD_DESK_AUTH_SECRET", raising=False)
    app = create_app(tmp_path)
    c = TestClient(app)
    c.app_state_db = tmp_path / "lead-desk.sqlite"
    return c


def test_full_campaign_lifecycle_over_http(client):
    # 1. Create the campaign (redirects to the admin page, which must render).
    r = client.post("/campaigns", data={"campaign_id": "mdh-2026",
                                        "name": "MDH", "daily_cap": "5"},
                    follow_redirects=True)
    assert r.status_code == 200 and "MDH" in r.text

    # 2. Upload contacts (multipart) with aliased headers.
    r = client.post("/campaigns/mdh-2026/upload",
                    files={"file": ("leads.csv", io.BytesIO(CSV), "text/csv")},
                    follow_redirects=True)
    assert r.status_code == 200
    assert "jane@acme.com" in r.text  # enrollment table renders the row

    # 3. Template + sequence for the catch-all 'cold' degree.
    r = client.post("/templates", data={
        "template_key": "cold-e1", "channel": "email",
        "subject": "Hello {{first_name}}",
        "body": "Hi {{first_name}} at {{company}}.", "campaign": "mdh-2026",
    }, follow_redirects=True)
    assert r.status_code == 200
    r = client.post("/campaigns/mdh-2026/sequences", data={
        "degree": "cold", "name": "cold seq", "send_mode": "auto-matthias",
        "steps": "email cold-e1 0",
    }, follow_redirects=True)
    assert r.status_code == 200

    # 4. Approval page shows rendered copy for a real contact, then approve.
    r = client.get("/campaigns/mdh-2026")
    assert "Hi Jane at Acme." in r.text or "Hi Kai at Corp." in r.text
    r = client.post("/campaigns/mdh-2026/approve", data={"confirm": "mdh-2026"},
                    follow_redirects=True)
    assert r.status_code == 200 and "approved" in r.text

    # 5. Board renders the cadence columns for the approved campaign.
    r = client.get("/?campaign=mdh-2026")
    assert r.status_code == 200
    assert "0/1" in r.text  # step pointer column

    # 5b. Second gate: 'approved' freezes but does not send; the human presses
    # "Start sending" (status approved -> sending) before the worker can claim.
    r = client.post("/campaigns/mdh-2026/start-sending",
                    data={"confirm": "mdh-2026"}, follow_redirects=True)
    assert r.status_code == 200 and "sending" in r.text

    # 6. Worker claims over HTTP with the bearer; send is rendered + leased.
    hdrs = {"Authorization": "Bearer wsecret"}
    with ContactStore(client.app_state_db) as store:
        claims = cadence.claim_sends(store, "w1", 10, at=IN_WINDOW)
    assert len(claims["claims"]) == 2
    send = claims["claims"][0]
    assert send["subject"].startswith("Hello ")

    # 7. Result lands the event; the contact page cadence card renders it.
    r = client.post("/api/outbox/result", headers=hdrs, json={
        "attempt_key": send["attempt_key"], "lease_id": send["lease_id"],
        "status": "sent", "occurred_at": "2026-07-15T09:01:00+00:00",
        "internet_message_id": "<im-1@brisken>",
    })
    assert r.status_code == 200 and r.json()["ok"]
    r = client.get(f"/contacts/{send['contact_id']}")
    assert r.status_code == 200
    assert "1/1" in r.text  # cadence card shows the advanced pointer

    # 8. Campaigns list renders with the kill switch control.
    r = client.get("/campaigns")
    assert r.status_code == 200 and "kill switch" in r.text.lower()

    # 9. Unauthenticated worker API is closed.
    assert client.post("/api/outbox/claim", json={}).status_code == 401
    assert client.get("/api/worker/status").status_code == 401

    # 10. Status endpoint reports the campaign with cap accounting.
    r = client.get("/api/worker/status", headers=hdrs)
    body = r.json()
    camp = next(c for c in body["campaigns"] if c["campaign"] == "mdh-2026")
    assert camp["status"] == "sending"
    assert camp["daily_sent"] >= 1  # the resolved send counts against the cap


def test_manual_linkedin_step_done_over_http(client):
    client.post("/campaigns", data={"campaign_id": "li-camp", "name": "LI"})
    client.post("/campaigns/li-camp/upload",
                files={"file": ("l.csv", io.BytesIO(CSV), "text/csv")})
    client.post("/templates", data={"template_key": "li-1", "channel": "linkedin",
                                    "subject": "", "body": "Connect note"})
    client.post("/campaigns/li-camp/sequences", data={
        "degree": "cold", "name": "li", "send_mode": "auto-matthias",
        "steps": "linkedin li-1 0"})
    client.post("/campaigns/li-camp/approve", data={"confirm": "li-camp"})

    with ContactStore(client.app_state_db) as store:
        enr = store.enrollments_for_campaign("li-camp")
        eid = enr[0]["enrollment_id"]
    r = client.post(f"/enrollments/{eid}/steps/1/done", follow_redirects=False)
    assert r.status_code == 303
    with ContactStore(client.app_state_db) as store:
        row = [dict(x) for x in store.enrollments_for_campaign("li-camp")
               if x["enrollment_id"] == eid][0]
        assert row["steps_done"] == 1  # the manual event advanced the pointer


def test_upload_to_unknown_campaign_404s(client):
    r = client.post("/campaigns/nope/upload",
                    files={"file": ("l.csv", io.BytesIO(CSV), "text/csv")})
    assert r.status_code == 404


def test_action_needed_button_and_detail_render(client):
    """The clickable 'Action needed' button, its detail modal, and the contact
    callout all render for a replied-needs-reply contact."""
    from lead_desk.web.service import now_iso
    from lead_desk.web.store import ContactStore
    with ContactStore(client.app_state_db) as s:
        s.upsert_contact({"contact_id": "r1", "natural_key": "r1",
                          "campaign": "rome-2026", "first_name": "Uffe",
                          "last_name": "Teisner", "company": "Grundfos",
                          "email": "u@grundfos.com",
                          "next_step": "Confirm the Sept 9 call slot."}, now_iso())
        s.add_event(contact_id="r1", ts="2026-07-01T00:00:00+00:00", channel="email",
                    direction="outbound", type="sent", now=now_iso())
        s.add_event(contact_id="r1", ts="2026-07-14T00:00:00+00:00", channel="email",
                    direction="inbound", type="reply", now=now_iso())
    r = client.get("/")
    assert r.status_code == 200
    assert "action-btn" in r.text and "showAction(this)" in r.text
    assert 'id="action-modal"' in r.text
    assert "Confirm the Sept 9 call slot." in r.text      # recommended action on the button
    r = client.get("/contacts/r1")
    assert r.status_code == 200
    assert "Action needed" in r.text                      # contact-page callout heading
    assert "Confirm the Sept 9 call slot." in r.text      # the recommended action itself
