"""Campaign review packets: seed, render, answer decisions, edit wording.

The packet is the owner-facing sign-off surface (/review/{packet_id}); these
tests walk it over real HTTP (Form parsing, redirects, Jinja render) plus the
function-level seed/validate paths.
"""
import json

import pytest
from fastapi.testclient import TestClient

from lead_desk.web.app import create_app
from lead_desk.web.review import build_review_view, seed_packet
from lead_desk.web.store import ContactStore

NOW = "2026-09-07T10:00:00Z"

PACKET = {
    "packet_id": "sept-test",
    "title": "September campaigns",
    "intro": "Answer the questions; edit the wording freely.",
    "items": [
        {"kind": "note", "title": "Where things stand",
         "body": {"text": "Engine ready. Nothing sends without the switch-on."}},
        {"kind": "decision", "title": "Release mode",
         "body": {"question": "How should mails in your name go out?",
                  "options": [
                      {"key": "wave", "label": "One release per wave",
                       "detail": "You approve list and copy once per wave."},
                      {"key": "click", "label": "Click each draft",
                       "detail": "Every mail staged in your Drafts."}],
                  "recommended": "wave"}},
        {"kind": "sequence", "title": "Wave 1: warm nudge",
         "body": {"audience": "24 warm non-responders",
                  "timing": "week of Sep 14",
                  "recipients": [{"name": "Jane Doe", "company": "Acme",
                                  "email": "jane@acme.com"}],
                  "steps": [
                      {"step_no": 1, "label": "Reply in thread", "subject": "",
                       "text": "Hi, picking this up after the summer."},
                      {"step_no": 2, "label": "Value-add", "subject": "",
                       "text": "Sending over the short summary."}]}},
    ],
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("LEAD_DESK_AUTH_SECRET", raising=False)
    app = create_app(tmp_path)
    c = TestClient(app)
    c.db = tmp_path / "lead-desk.sqlite"
    return c


def seed(client, packet=PACKET):
    with ContactStore(client.db) as store:
        return seed_packet(store, packet, NOW)


def item_ids(client):
    with ContactStore(client.db) as store:
        return {r["kind"]: r["item_id"]
                for r in store.list_review_items("sept-test")}


def test_seed_and_render(client):
    report = seed(client)
    assert report == {"packet_id": "sept-test", "items": 3, "replaced": 0}
    r = client.get("/review/sept-test")
    assert r.status_code == 200
    for needle in ("September campaigns", "How should mails in your name go out?",
                   "One release per wave", "our suggestion",
                   "picking this up after the summer", "Jane Doe",
                   "decision open", "wording review open"):
        assert needle in r.text


def test_unknown_packet_is_404(client):
    assert client.get("/review/nope").status_code == 404


def test_decision_roundtrip(client):
    seed(client)
    ids = item_ids(client)
    r = client.post(f"/review/sept-test/decision/{ids['decision']}",
                    data={"choice": "click", "comment": "prefer to see each"},
                    follow_redirects=True)
    assert r.status_code == 200
    assert "Answered: Click each draft" in r.text
    with ContactStore(client.db) as store:
        resp = json.loads(store.get_review_item(ids["decision"])["response"])
    assert resp["choice"] == "click"
    assert resp["comment"] == "prefer to see each"
    assert resp["by"] == "local"


def test_decision_invalid_choice_rejected(client):
    seed(client)
    ids = item_ids(client)
    r = client.post(f"/review/sept-test/decision/{ids['decision']}",
                    data={"choice": "nope"})
    assert r.status_code == 400


def test_sequence_edit_then_approve(client):
    seed(client)
    ids = item_ids(client)
    edited = {"action": "save", "comment": "",
              "subject_1": "", "text_1": "My own wording.",
              "subject_2": "", "text_2": "Second mail, my words."}
    r = client.post(f"/review/sept-test/sequence/{ids['sequence']}",
                    data=edited, follow_redirects=True)
    assert r.status_code == 200
    assert "Edited, not yet approved" in r.text
    assert "My own wording." in r.text  # editor prefills the reviewer's text
    edited["action"] = "approve"
    r = client.post(f"/review/sept-test/sequence/{ids['sequence']}",
                    data=edited, follow_redirects=True)
    assert "Wording approved" in r.text
    with ContactStore(client.db) as store:
        resp = json.loads(store.get_review_item(ids["sequence"])["response"])
    assert resp["status"] == "approved"
    assert resp["steps"][0]["text"] == "My own wording."


def test_change_request_needs_comment_and_step_set_must_match(client):
    seed(client)
    ids = item_ids(client)
    base = {"subject_1": "", "text_1": "a", "subject_2": "", "text_2": "b"}
    r = client.post(f"/review/sept-test/sequence/{ids['sequence']}",
                    data={**base, "action": "changes", "comment": ""})
    assert r.status_code == 400
    r = client.post(f"/review/sept-test/sequence/{ids['sequence']}",
                    data={"action": "save", "subject_1": "", "text_1": "only one"})
    assert r.status_code == 400


def test_progress_reaches_complete(client):
    seed(client)
    ids = item_ids(client)
    client.post(f"/review/sept-test/decision/{ids['decision']}",
                data={"choice": "wave", "comment": ""})
    client.post(f"/review/sept-test/sequence/{ids['sequence']}",
                data={"action": "approve", "comment": "",
                      "subject_1": "", "text_1": "x", "subject_2": "", "text_2": "y"})
    r = client.get("/review/sept-test")
    assert "All answered" in r.text
    with ContactStore(client.db) as store:
        view = build_review_view(store, "sept-test")
    assert view["complete"] is True


def test_seed_refuses_overwrite_without_replace(client):
    seed(client)
    with ContactStore(client.db) as store:
        with pytest.raises(ValueError, match="already has"):
            seed_packet(store, PACKET, NOW)
        report = seed_packet(store, PACKET, NOW, replace=True)
    assert report["replaced"] == 3


def test_seed_validates_shapes(client):
    with ContactStore(client.db) as store:
        with pytest.raises(ValueError, match="packet_id"):
            seed_packet(store, {"items": [{}]}, NOW)
        with pytest.raises(ValueError, match="no items"):
            seed_packet(store, {"packet_id": "x"}, NOW)
        bad = {"packet_id": "x", "items": [
            {"kind": "decision", "title": "t",
             "body": {"question": "q", "options": [{"key": "a", "label": "A"}]}}]}
        with pytest.raises(ValueError, match="option keys"):
            seed_packet(store, bad, NOW)
        bad = {"packet_id": "x", "items": [
            {"kind": "sequence", "title": "t",
             "body": {"steps": [{"step_no": 1, "text": "  "}]}}]}
        with pytest.raises(ValueError, match="steps with text"):
            seed_packet(store, bad, NOW)


def test_review_sits_behind_the_login_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("LEAD_DESK_AUTH_SECRET", "s3cret")
    app = create_app(tmp_path)
    c = TestClient(app)
    r = c.get("/review/sept-test", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"
