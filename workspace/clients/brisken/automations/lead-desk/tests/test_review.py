"""Campaign review packets: seed, render, answer decisions, edit wording.

The packet is the owner-facing sign-off surface (/review/{packet_id}); these
tests walk it over real HTTP (Form parsing, redirects, Jinja render) plus the
function-level seed/validate paths.
"""
import json

import pytest
from fastapi.testclient import TestClient

from lead_desk.web.app import create_app
from lead_desk.maintenance import reconcile
from lead_desk.web.review import (
    build_review_view, packet_facts, seed_packet, unsendable_reason,
)
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


def test_mails_render_as_prose_not_as_template_code(client):
    """The reviewer reads the waves as mails, so the mail boxes must not
    inherit base.html's operator-editor monospace, and a raw merge token must
    come with the name it resolves to. Regression: the packet Dirk opened on
    2026-09-09 showed every mail as 12px monospace headed 'Hi {{first_name}},'
    with nothing saying the token fills in."""
    seed(client)
    body = client.get("/review/sept-test").text
    prose = body.split(".rv-step textarea {", 1)[1].split("}", 1)[0]
    assert "font-family: inherit" in prose, "mail boxes still inherit monospace"
    assert "Names fill in per person" in body
    assert "reads as Jane" in body, "the token is not shown resolved"
    assert "querySelectorAll('.rv-step textarea')" in body, \
        "mail boxes are not auto-sized to their content"


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
    assert r.headers["location"] == "/login?next=%2Freview%2Fsept-test"


# -- the roster cannot contain someone the engine would refuse ---------------
#
# Source: 2026-09-10. The live September packet asked Dirk to sign off on 62
# people, of whom the send path would have refused 36 (wave 2: 23 listed, 0
# sendable), and nothing on the page or in the seed path said so.

def _packet_with(email, pid="sept-test"):
    return {"packet_id": pid, "title": "T", "intro": "",
            "items": [{"kind": "sequence", "title": "Wave 1",
                       "body": {"audience": "a", "timing": "t",
                                "recipients": [{"name": "Zed", "company": "Co",
                                                "email": email}],
                                "steps": [{"step_no": 1, "text": "hi"}]}}]}


def test_seed_refuses_a_denied_domain_recipient(client):
    with ContactStore(client.db) as store:
        with pytest.raises(ValueError) as e:
            seed_packet(store, _packet_with("someone@sap.com"), NOW)
    assert "engine would refuse" in str(e.value)
    assert "denied domain" in str(e.value)


def test_seed_refuses_a_blocking_suppression_recipient(client):
    with ContactStore(client.db) as store:
        store.add_suppression_entry("gone@optout.com", "email", "rome-master",
                                    NOW, note="opt-out")
        with pytest.raises(ValueError) as e:
            seed_packet(store, _packet_with("gone@optout.com"), NOW)
    assert "opt-out" in str(e.value)


def test_seed_allows_an_advisory_suppression_recipient(client):
    """'crm' is context, not a refusal, so it must not block a roster."""
    with ContactStore(client.db) as store:
        store.add_suppression_entry("known@crm.com", "email", "zoho-crm", NOW,
                                    note="crm")
        rep = seed_packet(store, _packet_with("known@crm.com"), NOW)
    assert rep["items"] == 1


def test_allow_unsendable_is_an_explicit_override(client):
    with ContactStore(client.db) as store:
        rep = seed_packet(store, _packet_with("someone@sap.com"), NOW,
                          allow_unsendable=True)
    assert rep["items"] == 1


def test_unsendable_reason_uses_the_send_paths_own_predicates(client):
    with ContactStore(client.db) as store:
        assert unsendable_reason(store, "x@sap.com").startswith("denied domain")
        assert unsendable_reason(store, "") == "no usable address"
        assert unsendable_reason(store, "fine@example.com") is None


# -- headline figures are computed, never typed ------------------------------
#
# Source: 2026-09-10. Every figure in the packet's opening note was wrong and
# the sentence's own arithmetic did not close (124 reached vs 34 + 71).

def _event(store, cid, direction, typ, ts, subject=""):
    store.add_event(contact_id=cid, ts=ts, channel="email",
                    direction=direction, type=typ, subject=subject,
                    detail=subject, source="test", created_by="test", now=NOW)


def _contact(store, cid, email):
    store.upsert_contact({"contact_id": cid, "natural_key": cid,
                          "campaign": "rome-2026", "first_name": "F",
                          "last_name": cid, "company": "Co", "email": email},
                         NOW)


def test_facts_arithmetic_closes_and_excludes_auto_replies(client):
    with ContactStore(client.db) as store:
        for i, em in enumerate(["a@x.com", "b@x.com", "c@x.com", "d@x.com"], 1):
            _contact(store, f"c{i}", em)
            _event(store, f"c{i}", "outbound", "sent", "2026-06-02T09:00:00Z")
        # c1 answers for real; c2 only bounces an out-of-office back; c3 books
        _event(store, "c1", "inbound", "reply", "2026-06-03T09:00:00Z", "Re: hi")
        _event(store, "c2", "inbound", "reply", "2026-06-03T09:00:00Z",
               "Automatic reply: hi")
        _event(store, "c3", "booked", "booked", "2026-06-04T09:00:00Z", "Call")
        f = packet_facts(store, "sept-test")

    assert f["reached"] == 4
    assert f["in_conversation"] == 2, "an out-of-office is not a conversation"
    assert f["booked"] == 1
    assert f["no_response"] == 2
    assert f["in_conversation"] + f["no_response"] == f["reached"]


def test_note_placeholders_render_as_live_numbers(client):
    packet = {
        "packet_id": "sept-test", "title": "T", "intro": "",
        "items": [{"kind": "note", "title": "Where things stand",
                   "body": {"text": "We wrote to {reached}; {no_response} "
                                    "have not responded. Unknown {nope} "
                                    "stays."}}]}
    with ContactStore(client.db) as store:
        seed_packet(store, packet, NOW)
        _contact(store, "c1", "a@x.com")
        _event(store, "c1", "outbound", "sent", "2026-06-02T09:00:00Z")
    text = client.get("/review/sept-test").text
    assert "We wrote to 1; 1 have not responded." in text
    assert "{nope}" in text, "an unknown placeholder must be left alone"
    assert "{reached}" not in text


# -- the two stores are reconciled, and disagreement is named ----------------

def test_an_overridden_roster_says_so_on_the_page(client):
    """allow_unsendable is an override, not a way to hide the problem: the
    page recomputes sendability at render, so a name that cannot be reached
    is named to whoever is being asked to approve the wave."""
    with ContactStore(client.db) as store:
        seed_packet(store, _packet_with("someone@sap.com"), NOW,
                    allow_unsendable=True)
    body = client.get("/review/sept-test").text
    assert "cannot be sent to" in body
    assert "denied domain" in body
    assert "Zed" in body


def test_a_clean_roster_shows_no_warning(client):
    with ContactStore(client.db) as store:
        seed_packet(store, _packet_with("fine@example.com"), NOW)
    assert "cannot be sent to" not in client.get("/review/sept-test").text


def test_reconcile_names_the_board_vs_engine_gap(client):
    with ContactStore(client.db) as store:
        _contact(store, "c1", "quiet@optout.com")
        store.add_suppression_entry("quiet@optout.com", "email", "rome-master",
                                    NOW, note="opt-out")
        rep = reconcile(store)
    assert rep["divergent"] is True
    assert rep["board_says_contactable_engine_refuses"] == 1
    assert rep["detail_engine_refuses"][0]["email"] == "quiet@optout.com"
    assert "opt-out" in rep["detail_engine_refuses"][0]["engine"]


def test_reconcile_is_quiet_when_the_stores_agree(client):
    with ContactStore(client.db) as store:
        _contact(store, "c1", "fine@example.com")
        rep = reconcile(store)
    assert rep["divergent"] is False
    assert rep["board_says_contactable_engine_refuses"] == 0
