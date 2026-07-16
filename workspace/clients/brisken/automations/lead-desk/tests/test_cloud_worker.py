"""Cloud worker tick semantics: kill-switch dormancy, Graph send + ack,
draft-dirk staging + correlation, crash reconcile (never resend), capture
filtering, dry-run inertness. Runs over a tmp ContactStore with a fake
mailer + fake poll - no network, no Graph.

Clock: conftest pins cadence.now_utc to IN_WINDOW (Wed 2026-07-15 09:00 UTC);
campaign fixtures mirror test_outbox.make_engine_campaign.
"""
from __future__ import annotations

from datetime import datetime, timezone

from lead_desk.cloud_worker import WORKER_ID, execute_one, filter_payloads, \
    replay_pending, run_tick
from lead_desk.graph_mail import DIRK_SMTP, SEND_FROM, GraphSendError
from lead_desk.web import cadence
from lead_desk.web.service import now_iso
from lead_desk.web.store import ContactStore
from lead_desk.worker.journal import Journal

IN_WINDOW = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)


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


def make_engine_campaign(store, contact_ids, cid="camp1", *, daily_cap=40,
                         degree="cold", send_mode="auto-matthias", n_steps=1,
                         throttle=0):
    """Campaign + template + sequence + enrollments through both gates
    (same shape as test_outbox; throttle 0 keeps ticks sleep-free)."""
    now = "2026-07-14T09:00:00+00:00"
    store.create_campaign(cid, "Test Campaign", now, daily_cap=daily_cap,
                          throttle_seconds=throttle, jitter_seconds=0)
    store.save_template("t1", "email", "Hello {{first_name}}",
                        "Body for {{company}}", "tester", now)
    steps = [{"step_no": i + 1, "channel": "email", "template_key": "t1",
              "day_offset": 0} for i in range(n_steps)]
    store.upsert_sequence(cid, degree, f"{degree} seq", send_mode, steps)
    for contact_id in contact_ids:
        store.enroll(contact_id, cid, "tester", now)
        enr = store.find_enrollment(contact_id, cid)
        store.set_degree(enr["enrollment_id"], degree, "manual", "test")
    res = cadence.approve_campaign(store, cid, "tester", cid, now=now)
    assert res["ok"], res
    sres = cadence.start_sending(store, cid, "tester", cid, now=now)
    assert sres["ok"], sres
    return cid


class FakeMailer:
    """Records calls; behavior configured per test."""

    def __init__(self):
        self.sent: list[dict] = []
        self.drafts: list[tuple[str, dict]] = []
        self.send_exc: Exception | None = None
        self.dirk_sent_items: list[dict] = []
        self.evidence: dict | None = None   # readback / search result

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


def no_events(mbx, since, until):
    return []


def setup(tmp_path, **campaign_kw):
    data = tmp_path / "data"
    data.mkdir()
    store = ContactStore(data / "lead-desk.sqlite")
    cid = make_contact(store, 1)
    make_engine_campaign(store, [cid], **campaign_kw)
    return data, store


def tick(data, mailer=None, poll_fn=no_events, **kw):
    return run_tick(data, mailer=mailer or FakeMailer(), poll_fn=poll_fn,
                    at=IN_WINDOW, sleep=lambda s: None, **kw)


def events_for(store, contact_id):
    return [dict(r) for r in store.conn.execute(
        "SELECT * FROM outreach_events WHERE contact_id = ? ORDER BY ts",
        (contact_id,)).fetchall()]


# -- dormancy ---------------------------------------------------------------

def test_kill_switch_pauses_claims_but_capture_still_runs(tmp_path):
    data, store = setup(tmp_path)
    store.set_state("kill_switch", "1", now_iso())
    m = FakeMailer()
    reply = [{"email": "c1@example.com", "type": "reply", "direction": "inbound",
              "channel": "email", "occurred_at": "2026-07-15T08:00:00+00:00",
              "subject": "Re: hi", "source": "graph-auto",
              "internet_message_id": "<r1>"}]
    rep = tick(data, m, poll_fn=lambda mbx, s, u: reply if mbx == SEND_FROM else [])
    assert rep["kill_switch"] is True and rep["paused"] is True
    assert rep["claimed"] == 0 and m.sent == [] and m.drafts == []
    assert any(e["type"] == "reply" for e in events_for(store, "c1"))
    # nothing was ever leased
    assert store.conn.execute("SELECT COUNT(*) c FROM send_attempts").fetchone()["c"] == 0


def test_dry_run_leases_and_sends_nothing(tmp_path):
    data, store = setup(tmp_path)
    m = FakeMailer()
    rep = tick(data, m, dry_run=True)
    assert rep["claimed"] == 1 and rep["due_preview"][0]["to"] == "c1@example.com"
    assert m.sent == [] and m.drafts == []
    assert store.conn.execute("SELECT COUNT(*) c FROM send_attempts").fetchone()["c"] == 0
    assert events_for(store, "c1") == []


# -- auto send --------------------------------------------------------------

def test_auto_send_happy_path(tmp_path):
    data, store = setup(tmp_path)
    m = FakeMailer()
    m.evidence = {"imid": "<sent1>", "ts": "2026-07-15T09:00:30Z",
                  "entry_id": "g1"}
    rep = tick(data, m)
    assert rep["counters"]["sent"] == 1 and rep["claimed"] == 1
    assert len(m.sent) == 1 and m.sent[0]["to"] == "c1@example.com"
    assert m.sent[0]["from"] == SEND_FROM
    attempt = store.conn.execute("SELECT * FROM send_attempts").fetchone()
    assert attempt["status"] == "sent"
    assert attempt["internet_message_id"] == "<sent1>"
    evs = events_for(store, "c1")
    assert [e["type"] for e in evs] == ["sent"]
    # journal terminal + heartbeat stamped
    assert Journal(data / "cloud-journal.jsonl").pending() == {}
    assert WORKER_ID in (store.get_state("worker_heartbeat") or "")


def test_second_tick_is_idempotent(tmp_path):
    data, store = setup(tmp_path)
    m = FakeMailer()
    m.evidence = {"imid": "<sent1>", "ts": "2026-07-15T09:00:30Z"}
    tick(data, m)
    rep2 = tick(data, m)
    assert rep2["claimed"] == 0 and len(m.sent) == 1
    assert len(events_for(store, "c1")) == 1


def test_graph_500_requeues_graph_400_parks(tmp_path):
    data, store = setup(tmp_path)
    m = FakeMailer()
    m.send_exc = GraphSendError(503, "throttled")
    tick(data, m)
    attempt = store.conn.execute("SELECT * FROM send_attempts").fetchone()
    assert attempt["status"] == "queued"      # transient: server re-queues
    m2 = FakeMailer()
    m2.send_exc = GraphSendError(400, "bad request")
    tick(data, m2)
    attempt = store.conn.execute("SELECT * FROM send_attempts").fetchone()
    assert attempt["status"] == "parked"      # permanent: a human decides


def test_never_auto_sends_as_dirk(tmp_path):
    data, store = setup(tmp_path)
    store.conn.execute("UPDATE campaigns SET from_address = ?", (DIRK_SMTP,))
    store.conn.commit()
    from lead_desk.graph_mail import GraphMailer
    # use the REAL GraphMailer with a fake transport so the allowlist runs
    class NoHttp:
        def get(self, *a, **k):
            raise AssertionError("no request may fire")
        post = get
    real = GraphMailer(token="tok", http=NoHttp())
    rep = run_tick(data, mailer=real, poll_fn=no_events, at=IN_WINDOW,
                   sleep=lambda s: None)
    attempt = store.conn.execute("SELECT * FROM send_attempts").fetchone()
    assert attempt["status"] == "parked"
    assert "matthias-only" in (attempt["failure_reason"] or "")
    assert rep["counters"]["failed"] == 1


def test_body_hash_mismatch_parks_without_sending(tmp_path):
    data, store = setup(tmp_path)
    claims = cadence.claim_sends(store, WORKER_ID, 5, at=IN_WINDOW)["claims"]
    send = dict(claims[0], body=claims[0]["body"] + " TAMPERED")
    m = FakeMailer()
    out = execute_one(store, m, send, Journal(data / "j.jsonl"), now=IN_WINDOW)
    assert out == "hash_mismatch" and m.sent == []
    attempt = store.get_attempt(send["attempt_key"])
    assert attempt["status"] == "parked"


# -- crash reconcile ----------------------------------------------------------

def crash_inside_send_window(data, store):
    """Claim + journal graph_issued, then 'crash' (no ack): the ambiguous window."""
    claims = cadence.claim_sends(store, WORKER_ID, 5, at=IN_WINDOW)["claims"]
    j = Journal(data / "cloud-journal.jsonl")
    send = claims[0]
    j.write(send["attempt_key"], "claimed", to=send["to"],
            lease_id=send["lease_id"], mode=send["send_mode"])
    j.write(send["attempt_key"], "graph_issued", to=send["to"],
            subject=send["subject"], lease_id=send["lease_id"])
    return send, j


def test_reconcile_with_evidence_acks_sent(tmp_path):
    data, store = setup(tmp_path)
    send, j = crash_inside_send_window(data, store)
    m = FakeMailer()
    m.evidence = {"imid": "<found>", "ts": "2026-07-15T09:00:10Z"}
    alerts: list[str] = []
    counters = replay_pending(store, m, j, alerts, now=IN_WINDOW)
    assert counters["replayed"] == 1 and alerts == []
    attempt = store.get_attempt(send["attempt_key"])
    assert attempt["status"] == "sent"
    assert attempt["internet_message_id"] == "<found>"
    assert m.sent == []  # reconciled from evidence, never re-sent


def test_reconcile_without_evidence_flags_never_resends(tmp_path):
    data, store = setup(tmp_path)
    send, j = crash_inside_send_window(data, store)
    m = FakeMailer()      # evidence None
    alerts: list[str] = []
    counters = replay_pending(store, m, j, alerts, now=IN_WINDOW)
    assert counters["ambiguous"] == 1
    assert alerts and "NOT resending" in alerts[0]
    attempt = store.get_attempt(send["attempt_key"])
    assert attempt["status"] == "leased"   # untouched; lease expiry -> stalled
    assert m.sent == []


def test_reconcile_claimed_state_requeues(tmp_path):
    data, store = setup(tmp_path)
    claims = cadence.claim_sends(store, WORKER_ID, 5, at=IN_WINDOW)["claims"]
    j = Journal(data / "cloud-journal.jsonl")
    send = claims[0]
    j.write(send["attempt_key"], "claimed", to=send["to"],
            lease_id=send["lease_id"], mode=send["send_mode"])
    counters = replay_pending(store, FakeMailer(), j, [], now=IN_WINDOW)
    assert counters["requeued"] == 1
    assert store.get_attempt(send["attempt_key"])["status"] == "queued"


def test_network_error_leaves_ambiguous_then_reconciles(tmp_path):
    data, store = setup(tmp_path)
    m = FakeMailer()
    m.send_exc = ConnectionError("socket dropped mid-request")
    rep = tick(data, m)
    attempt = store.conn.execute("SELECT * FROM send_attempts").fetchone()
    assert attempt["status"] == "leased"   # NOT nacked, NOT requeued
    assert events_for(store, "c1") == []
    # next tick: evidence appears in Sent Items -> reconciled, still one send
    m2 = FakeMailer()
    m2.evidence = {"imid": "<late>", "ts": "2026-07-15T09:00:40Z"}
    rep2 = tick(data, m2)
    attempt = store.conn.execute("SELECT * FROM send_attempts").fetchone()
    assert attempt["status"] == "sent" and m2.sent == []
    assert rep2["replay"]["replayed"] == 1


# -- draft-dirk (warm) ---------------------------------------------------------

def test_draft_dirk_stages_then_correlates(tmp_path):
    data, store = setup(tmp_path, send_mode="draft-dirk", degree="warm")
    m = FakeMailer()
    rep = tick(data, m)
    assert rep["counters"]["drafted"] == 1
    assert m.drafts and m.drafts[0][0] == DIRK_SMTP
    assert m.sent == []                     # never auto-sent as Dirk
    attempt = store.conn.execute("SELECT * FROM send_attempts").fetchone()
    assert attempt["status"] == "drafted"
    assert events_for(store, "c1") == []    # no event until HIS click

    # Dirk actually sends it -> next tick's capture correlates + completes
    m2 = FakeMailer()
    m2.dirk_sent_items = [{"subject": attempt["rendered_subject"],
                           "to_addrs": ["c1@example.com"],
                           "ts": "2026-07-15T10:00:00Z", "imid": "<dirk1>"}]
    rep2 = tick(data, m2)
    assert rep2["capture"]["draft_confirmations"] == 1
    attempt = store.conn.execute("SELECT * FROM send_attempts").fetchone()
    assert attempt["status"] == "sent"
    evs = events_for(store, "c1")
    assert len(evs) == 1 and "sent by Dirk" in evs[0]["detail"]


def test_draft_to_self_mode_never_acks(tmp_path):
    data, store = setup(tmp_path)
    m = FakeMailer()
    rep = tick(data, m, draft_to_self=True)
    assert m.drafts and m.drafts[0][0] == SEND_FROM
    assert m.drafts[0][1]["to"] == SEND_FROM   # redirected to our own mailbox
    assert m.sent == []
    attempt = store.conn.execute("SELECT * FROM send_attempts").fetchone()
    assert attempt["status"] == "leased"       # not acked; expires -> stalled
    assert events_for(store, "c1") == []
    assert rep["counters"]["sent"] == 0


# -- capture filtering ----------------------------------------------------------

def test_filter_payloads_drops_own_team_and_worker_sends(tmp_path):
    data, store = setup(tmp_path)
    m = FakeMailer()
    m.evidence = None                       # readback misses -> imid stays NULL
    tick(data, m)                           # one auto send recorded
    attempt = store.conn.execute("SELECT * FROM send_attempts").fetchone()
    assert attempt["status"] == "sent" and attempt["internet_message_id"] is None
    payloads = [
        # the sweep's copy of our own worker send (imid unknown to the sink)
        {"email": "c1@example.com", "type": "sent",
         "subject": attempt["rendered_subject"], "internet_message_id": "<x>"},
        # internal own-team mail must never become lead activity
        {"email": "dirk.neumann@brisken.com", "type": "reply", "subject": "internal"},
        # a genuine manual send to a lead is kept (mailbox truth on the board)
        {"email": "c1@example.com", "type": "sent", "subject": "Manual follow-up"},
    ]
    kept = filter_payloads(store, payloads)
    assert [p.get("subject") for p in kept] == ["Manual follow-up"]


def test_capture_failure_blocks_claiming(tmp_path):
    data, store = setup(tmp_path)
    m = FakeMailer()

    def broken(mbx, since, until):
        raise RuntimeError("graph 503")

    rep = tick(data, m, poll_fn=broken)
    assert rep["aborted"] == "capture-failed"
    assert "claimed" not in rep and m.sent == []
    assert store.conn.execute("SELECT COUNT(*) c FROM send_attempts").fetchone()["c"] == 0


def test_capture_bounce_auto_suppresses(tmp_path):
    data, store = setup(tmp_path)
    store.set_state("kill_switch", "1", now_iso())
    bounce = [{"email": "c1@example.com", "type": "bounce", "direction": "inbound",
               "channel": "email", "occurred_at": "2026-07-15T08:30:00+00:00",
               "subject": "Undeliverable: Hello", "source": "graph-auto",
               "internet_message_id": "<ndr1>"}]
    tick(data, FakeMailer(), poll_fn=lambda mbx, s, u: bounce if mbx == SEND_FROM else [])
    c = store.get_contact("c1")
    assert c["suppressed"] == 1 and c["suppress_reason"] == "bounced"
