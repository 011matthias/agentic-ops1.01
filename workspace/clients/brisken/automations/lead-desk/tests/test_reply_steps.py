"""Phase 3: in-thread reply steps end-to-end. A follow-up step flagged
reply_to_prior sends as a Graph reply threaded onto the prior step's sent
mail (anchor resolved by the imid on its attempt row) instead of a fresh
mail. Anchor missing -> park + alert, NEVER a silent fresh send; the
operator escape hatch is POST /attempts/send-fresh (force_fresh).

FakeMailer follows the test_cloud_worker pattern, extended with
find_message_by_imid / create_reply_draft / send_draft_by_id recorders.
Clock: conftest pins cadence.now_utc to IN_WINDOW (Wed 2026-07-15 09:00 UTC).
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from lead_desk.cloud_worker import WORKER_ID, _resolve_anchor, run_tick
from lead_desk.graph_mail import DIRK_SMTP, SEND_FROM
from lead_desk.web import cadence
from lead_desk.web.app import create_app
from lead_desk.web.service import now_iso
from lead_desk.web.store import ContactStore, attempt_key_for
from lead_desk.worker.com_mail import match_drafted

IN_WINDOW = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)
NOW = "2026-07-14T09:00:00+00:00"

# The prior step's sent mail as find_message_by_imid returns it.
ANCHOR = {"id": "anchor-1", "conversationId": "conv-1", "subject": "Hello First1"}


# -- fixtures ---------------------------------------------------------------

def make_contact(store, cid_suffix, email=None, **fields):
    cid = f"c{cid_suffix}"
    data = {"contact_id": cid, "natural_key": cid, "campaign": "rome-2026",
            "first_name": f"First{cid_suffix}", "last_name": f"Last{cid_suffix}",
            "company": f"Co{cid_suffix}",
            "email": f"{cid}@example.com" if email is None else email}
    data.update(fields)
    store.upsert_contact(data, now_iso())
    return cid


def make_reply_campaign(store, contact_ids, cid="camp1", *,
                        send_mode="auto-matthias"):
    """Two-email-step campaign whose step 2 is an in-thread reply, through
    both gates (same shape as test_cloud_worker.make_engine_campaign)."""
    store.create_campaign(cid, "Test Campaign", NOW, daily_cap=40,
                          throttle_seconds=0, jitter_seconds=0)
    store.save_template("t1", "email", "Hello {{first_name}}",
                        "Body one {{company}}", "tester", NOW)
    store.save_template("t2", "email", "Follow-up", "Body two", "tester", NOW)
    steps = [
        {"step_no": 1, "channel": "email", "template_key": "t1", "day_offset": 0},
        {"step_no": 2, "channel": "email", "template_key": "t2",
         "day_offset": 0, "reply_to_prior": 1},
    ]
    store.upsert_sequence(cid, "cold", "cold seq", send_mode, steps)
    for contact_id in contact_ids:
        store.enroll(contact_id, cid, "tester", NOW)
        enr = store.find_enrollment(contact_id, cid)
        store.set_degree(enr["enrollment_id"], "cold", "manual", "test")
    res = cadence.approve_campaign(store, cid, "tester", cid, now=NOW)
    assert res["ok"], res
    sres = cadence.start_sending(store, cid, "tester", cid, now=NOW)
    assert sres["ok"], sres
    return cid


class FakeMailer:
    """Records calls; behavior configured per test (test_cloud_worker pattern
    + the reply-step surface)."""

    def __init__(self):
        self.sent: list[dict] = []
        self.drafts: list[tuple[str, dict]] = []
        self.send_exc: Exception | None = None
        self.dirk_sent_items: list[dict] = []
        self.evidence: dict | None = None   # readback / search result
        # reply-step surface
        self.messages: dict[str, dict] = {}          # imid -> message
        self.imid_lookups: list[tuple[str, str]] = []
        self.reply_drafts: list[dict] = []
        self.sent_by_id: list[dict] = []
        self.reply_conversation: str | None = None   # None = the anchor's own

    def send_auto(self, send):
        if self.send_exc is not None:
            raise self.send_exc
        self.sent.append(send)

    def create_draft(self, mailbox, send):
        self.drafts.append((mailbox, send))
        return {"duplicate": False, "entry_id": f"draft-{len(self.drafts)}"}

    def poll_sent(self, mailbox, since):
        return self.dirk_sent_items

    def readback_sent(self, mailbox, to, subject, since, **kw):
        return self.evidence

    def search_sent_for(self, mailbox, to, subject, since):
        return self.evidence

    def find_message_by_imid(self, mailbox, imid):
        self.imid_lookups.append((mailbox, imid))
        return self.messages.get(imid)

    def create_reply_draft(self, mailbox, anchor_id, *, to, html_body,
                           cc=None, bcc=None):
        anchor = next((m for m in self.messages.values()
                       if m.get("id") == anchor_id), {})
        self.reply_drafts.append({
            "mailbox": mailbox, "anchor_id": anchor_id, "to": to,
            "html_body": html_body, "cc": cc, "bcc": bcc})
        return {"entry_id": f"reply-{len(self.reply_drafts)}",
                "conversation_id": self.reply_conversation
                or anchor.get("conversationId"),
                "subject": "RE: " + (anchor.get("subject") or ""),
                "duplicate": False}

    def send_draft_by_id(self, mailbox, message_id, *, expect_to,
                         expect_subject=None):
        self.sent_by_id.append({
            "mailbox": mailbox, "message_id": message_id,
            "expect_to": expect_to, "expect_subject": expect_subject})
        return {"internet_message_id": f"<reply-sent-{len(self.sent_by_id)}>",
                "conversation_id": self.reply_conversation,
                "subject": expect_subject}


def no_events(mbx, since, until):
    return []


def setup(tmp_path, **campaign_kw):
    data = tmp_path / "data"
    data.mkdir()
    store = ContactStore(data / "lead-desk.sqlite")
    cid = make_contact(store, 1)
    make_reply_campaign(store, [cid], **campaign_kw)
    return data, store


def tick(data, mailer=None, **kw):
    return run_tick(data, mailer=mailer or FakeMailer(), poll_fn=no_events,
                    at=IN_WINDOW, sleep=lambda s: None, **kw)


def send_step1(data, store, *, with_imid=True):
    """Tick 1: step 1 auto-sends; its attempt records (or misses) the imid."""
    m = FakeMailer()
    if with_imid:
        m.evidence = {"imid": "<step1>", "ts": "2026-07-15T09:00:30Z",
                      "entry_id": "g1"}
    rep = tick(data, m)
    assert rep["counters"]["sent"] == 1
    return store.get_attempt(attempt_key_for(1, 1))


def events_for(store, contact_id):
    return [dict(r) for r in store.conn.execute(
        "SELECT * FROM outreach_events WHERE contact_id = ? ORDER BY ts, event_id",
        (contact_id,)).fetchall()]


# -- authoring --------------------------------------------------------------

def test_upsert_sequence_rejects_reply_flag_on_step_one(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        store.create_campaign("c1", "C", NOW)
        with pytest.raises(ValueError, match="no prior step to reply to"):
            store.upsert_sequence("c1", "cold", "cold", "auto-matthias",
                                  [{"step_no": 1, "channel": "email",
                                    "template_key": "t1", "day_offset": 0,
                                    "reply_to_prior": 1}])
        # validation fires before any write: nothing was stored
        assert store.get_sequence("c1", "cold") is None


# -- claim payload ----------------------------------------------------------

def test_claim_payload_carries_reply_flag_and_thread_ext_key(tmp_path):
    data, store = setup(tmp_path)
    first = cadence.claim_sends(store, WORKER_ID, 5, at=IN_WINDOW,
                                peek=True)["claims"]
    assert first[0]["step_no"] == 1
    assert first[0]["reply_to_prior"] is False
    assert first[0]["thread_ext_key"] is None
    send_step1(data, store)
    claims = cadence.claim_sends(store, WORKER_ID, 5, at=IN_WINDOW,
                                 peek=True)["claims"]
    assert len(claims) == 1
    c = claims[0]
    assert c["step_no"] == 2
    assert c["reply_to_prior"] is True
    assert c["thread_ext_key"] == attempt_key_for(c["enrollment_id"], 1)


# -- anchor resolution --------------------------------------------------------

def test_reply_step_resolves_anchor_from_prior_attempt_imid(tmp_path):
    data, store = setup(tmp_path)
    attempt = send_step1(data, store)
    assert attempt["internet_message_id"] == "<step1>"
    m = FakeMailer()
    m.messages["<step1>"] = ANCHOR
    send = {"thread_ext_key": attempt["attempt_key"],
            "send_mode": "auto-matthias"}
    assert _resolve_anchor(store, m, send) == ANCHOR
    assert m.imid_lookups == [(SEND_FROM, "<step1>")]
    # draft-dirk: the anchor lives in the mailbox the prior step was sent
    # from, so resolution goes against Dirk's mailbox.
    m2 = FakeMailer()
    m2.messages["<step1>"] = ANCHOR
    assert _resolve_anchor(store, m2, {**send, "send_mode": "draft-dirk"}) == ANCHOR
    assert m2.imid_lookups == [(DIRK_SMTP, "<step1>")]


def test_reply_step_missing_prior_imid_parks_with_alert(tmp_path):
    data, store = setup(tmp_path)
    send_step1(data, store, with_imid=False)   # readback missed: imid NULL
    m = FakeMailer()
    rep = tick(data, m)
    akey = attempt_key_for(1, 2)
    attempt = store.get_attempt(akey)
    assert attempt["status"] == "parked"
    assert "reply anchor not found" in (attempt["failure_reason"] or "")
    assert m.sent == [] and m.reply_drafts == [] and m.sent_by_id == []
    assert f"reply anchor not found: {akey}" in \
        (store.get_state("cloud_worker_alert") or "")
    assert rep["counters"]["failed"] == 1
    assert len(events_for(store, "c1")) == 1   # only step 1's sent event


def test_reply_step_anchor_not_found_parks_never_fresh_sends(tmp_path):
    data, store = setup(tmp_path)
    send_step1(data, store)
    m = FakeMailer()                 # messages empty -> lookup returns None
    tick(data, m)
    akey = attempt_key_for(1, 2)
    assert m.imid_lookups == [(SEND_FROM, "<step1>")]  # it DID try to resolve
    assert store.get_attempt(akey)["status"] == "parked"
    assert m.sent == []              # NEVER fell back to a fresh send
    assert m.reply_drafts == [] and m.sent_by_id == []
    assert len(events_for(store, "c1")) == 1


# -- auto-matthias reply path -------------------------------------------------

def test_reply_auto_path_sends_by_id_and_acks_with_imid(tmp_path):
    data, store = setup(tmp_path)
    send_step1(data, store)
    m = FakeMailer()
    m.messages["<step1>"] = ANCHOR
    rep = tick(data, m)
    assert rep["counters"]["sent"] == 1
    assert m.sent == []                       # reply path never uses sendMail
    rd = m.reply_drafts[0]
    assert rd["mailbox"] == SEND_FROM and rd["anchor_id"] == "anchor-1"
    assert rd["to"] == "c1@example.com"
    assert "Body two" in rd["html_body"]
    sb = m.sent_by_id[0]
    assert sb["mailbox"] == SEND_FROM and sb["message_id"] == "reply-1"
    assert sb["expect_to"] == "c1@example.com"
    assert sb["expect_subject"] == "RE: Hello First1"
    attempt = store.get_attempt(attempt_key_for(1, 2))
    assert attempt["status"] == "sent"
    assert attempt["internet_message_id"] == "<reply-sent-1>"
    assert len(events_for(store, "c1")) == 2  # both steps' sent events
    assert not (store.get_state("cloud_worker_alert") or "")


def test_reply_threading_mismatch_acks_sent_but_alerts(tmp_path):
    data, store = setup(tmp_path)
    send_step1(data, store)
    m = FakeMailer()
    m.messages["<step1>"] = ANCHOR
    m.reply_conversation = "conv-OTHER"       # draft left the anchor's thread
    rep = tick(data, m)
    akey = attempt_key_for(1, 2)
    assert rep["counters"]["sent"] == 1
    assert len(m.sent_by_id) == 1
    assert store.get_attempt(akey)["status"] == "sent"   # the mail DID go
    assert f"thread_verify_failed: {akey}" in \
        (store.get_state("cloud_worker_alert") or "")


def test_reply_step_carries_zoho_bcc(tmp_path):
    data, store = setup(tmp_path)
    send_step1(data, store)
    m = FakeMailer()
    m.messages["<step1>"] = ANCHOR
    tick(data, m)
    rd = m.reply_drafts[0]
    assert rd["bcc"] == ["s9hitl_pv69mu@mails4.zohocrm.com"]  # Zoho keeps riding
    assert rd["cc"] == ["dirk.neumann@brisken.com"]


# -- draft-dirk reply path ----------------------------------------------------

def test_reply_draft_dirk_stages_reply_and_holds_followup(tmp_path):
    data, store = setup(tmp_path, send_mode="draft-dirk")
    rep1 = tick(data, FakeMailer())           # step 1 staged in Dirk's Drafts
    assert rep1["counters"]["drafted"] == 1
    a1 = store.get_attempt(attempt_key_for(1, 1))
    assert a1["status"] == "drafted"
    # Dirk sends it; the next tick correlates (imid lands on attempt 1) and
    # then stages the reply step - also as a draft in HIS mailbox.
    m2 = FakeMailer()
    m2.dirk_sent_items = [{"subject": a1["rendered_subject"],
                           "to_addrs": ["c1@example.com"],
                           "ts": "2026-07-15T08:00:00Z", "imid": "<dirk1>"}]
    m2.messages["<dirk1>"] = {"id": "anchor-d", "conversationId": "conv-d",
                              "subject": a1["rendered_subject"]}
    rep2 = tick(data, m2)
    assert rep2["capture"]["draft_confirmations"] == 1
    assert rep2["counters"]["drafted"] == 1
    rd = m2.reply_drafts[0]
    assert rd["mailbox"] == DIRK_SMTP and rd["anchor_id"] == "anchor-d"
    assert rd["to"] == "c1@example.com"
    a2 = store.get_attempt(attempt_key_for(1, 2))
    assert a2["status"] == "drafted"          # held until HIS click
    assert m2.sent == [] and m2.sent_by_id == []
    assert len(events_for(store, "c1")) == 1  # only step 1 completed


# -- operator escape hatch ----------------------------------------------------

def test_send_fresh_action_requeues_with_force_fresh(tmp_path, monkeypatch):
    monkeypatch.delenv("LEAD_DESK_AUTH_SECRET", raising=False)
    data, store = setup(tmp_path)
    send_step1(data, store)
    tick(data, FakeMailer())                  # anchor not found -> parked
    akey = attempt_key_for(1, 2)
    assert store.get_attempt(akey)["status"] == "parked"
    client = TestClient(create_app(data))
    r = client.post("/attempts/send-fresh",
                    data={"attempt_key": akey, "campaign": "camp1"},
                    follow_redirects=False)
    assert r.status_code == 303
    attempt = store.get_attempt(akey)
    assert attempt["status"] == "queued"
    assert attempt["force_fresh"] == 1
    assert attempt["attempt_count"] == 0
    # the claim now treats it as a FRESH send (reply flag dropped)
    claims = cadence.claim_sends(store, WORKER_ID, 5, at=IN_WINDOW,
                                 peek=True)["claims"]
    assert claims and claims[0]["attempt_key"] == akey
    assert claims[0]["reply_to_prior"] is False


# -- RE:-subject completion matching ------------------------------------------

def test_match_drafted_confirms_re_prefixed_subject_case_insensitively():
    sent = [{"subject": "RE: hello first1", "to_addrs": ["c1@example.com"],
             "ts": "2026-07-15T10:00:00Z", "imid": "<m1>"}]
    drafted = [{"attempt_key": "cadence:1:2", "to": "c1@example.com",
                "subject": "Hello First1"}]
    assert match_drafted(sent, drafted) == [
        {"attempt_key": "cadence:1:2",
         "occurred_at": "2026-07-15T10:00:00Z",
         "internet_message_id": "<m1>"}]
    # a different subject still refuses (normalization is not fuzzing)
    assert match_drafted(
        [{"subject": "RE: something else", "to_addrs": ["c1@example.com"]}],
        drafted) == []
