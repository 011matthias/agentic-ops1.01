"""The arming drill (ARMING-DRILL.md) end to end against the fixture
transport, with epoch-keyed approval in the loop. No Graph, no network: the
FixtureTransport records what the engine hands to transport.

It walks the same order the owner-present drill uses (dry run -> draft-to-
self -> live send -> reply-halt), through the real surfaces (HTTP approval
panel, the lead-desk-drill step functions, run_tick), and adds the legs the
approval port introduced: a stale approval, a decision keyed to an old epoch,
an unknown outcome and its trusted reconcile. ``pytest -s`` prints the drill
sheet.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from lead_desk import drill
from lead_desk.cloud_worker import run_tick
from lead_desk.graph_mail import SEND_FROM
from lead_desk.web import approval, cadence
from lead_desk.web.app import create_app
from lead_desk.web.service import ingest_event
from lead_desk.web.store import ContactStore

T0 = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 7, 15, 10, 0, tzinfo=timezone.utc)
T2 = datetime(2026, 7, 15, 11, 0, tzinfo=timezone.utc)
CID = "drill"
TEST_ADDR = "drill-fixture-a@example.test"
SECOND_ADDR = "drill-fixture-b@example.test"
ALL_WEEK = json.dumps({"days": [0, 1, 2, 3, 4, 5, 6], "start": "00:00",
                       "end": "23:59", "tz": "Europe/Berlin"})


class FixtureTransport:
    """The send-drill fixture: records transport calls, never sends."""

    def __init__(self):
        self.sent: list[dict] = []
        self.drafts: list[tuple[str, dict]] = []
        self.fail_next: Exception | None = None
        self.evidence: dict | None = None

    def send_auto(self, send):
        if self.fail_next is not None:
            exc, self.fail_next = self.fail_next, None
            raise exc
        self.sent.append(dict(send))

    def create_draft(self, mailbox, send):
        self.drafts.append((mailbox, dict(send)))
        return {"duplicate": False, "entry_id": f"fixture-draft-{len(self.drafts)}"}

    def poll_sent(self, mailbox, since):
        return []

    def readback_sent(self, mailbox, to, subject, since, **kw):
        return {"imid": f"<fixture-{len(self.sent)}@example.test>",
                "ts": "2026-07-15T10:00:05+00:00"}

    def search_sent_for(self, mailbox, to, subject, since):
        return self.evidence


def no_events(mbx, since, until):
    return []


def test_send_drill_end_to_end_against_fixture(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("LEAD_DESK_AUTH_SECRET", raising=False)
    db = tmp_path / "lead-desk.sqlite"
    sheet: list[tuple[str, str, str]] = []

    def record(step, ok, evidence):
        sheet.append((step, "PASS" if ok else "FAIL", evidence))
        assert ok, f"{step}: {evidence}"

    def tick(at, transport, **kw):
        return run_tick(tmp_path, mailer=transport, poll_fn=no_events, at=at,
                        sleep=lambda s: None, **kw)

    def lift(client, on):
        client.post("/worker/kill", data={"on": "0" if on else "1"})

    # -- prerequisites: a dedicated drill campaign, two fixture addresses, 2 steps
    with ContactStore(db) as store:
        store.set_state("kill_switch", "1", "2026-07-15T08:00:00+00:00")
        store.create_campaign(CID, "Arming drill", "2026-07-15T08:00:00+00:00",
                              cc_address="", send_window=ALL_WEEK, daily_cap=4,
                              throttle_seconds=0, jitter_seconds=0)
        store.save_template("drill-e1", "email", "LEAD DESK ARMING DRILL step 1",
                            "Drill step 1 for {{first_name}} at {{company}}.",
                            "matthias", "2026-07-15T08:00:00+00:00")
        store.save_template("drill-e2", "email", "LEAD DESK ARMING DRILL step 2",
                            "Drill follow-up for {{first_name}}.",
                            "matthias", "2026-07-15T08:00:00+00:00")
        store.upsert_sequence(CID, "cold", "drill", "auto-matthias", [
            {"step_no": 1, "channel": "email", "template_key": "drill-e1", "day_offset": 0},
            {"step_no": 2, "channel": "email", "template_key": "drill-e2", "day_offset": 0}])
        for cid_, addr in (("fx-a", TEST_ADDR), ("fx-b", SECOND_ADDR)):
            store.upsert_contact({"contact_id": cid_, "natural_key": cid_,
                                  "campaign": CID, "first_name": "Drill",
                                  "last_name": cid_, "company": "Fixture",
                                  "email": addr}, "2026-07-15T08:00:00+00:00")
            store.enroll(cid_, CID, "matthias", "2026-07-15T08:00:00+00:00")
            store.set_degree(store.find_enrollment(cid_, CID)["enrollment_id"],
                             "cold", "manual", "drill")

    client = TestClient(create_app(tmp_path))

    # -- approval panel: stale page refused, reviewed epoch approves
    page = client.get(f"/campaigns/{CID}").text
    manifest = re.search(r'name="draft_manifest" value="([0-9a-f]{64})"', page).group(1)
    epoch = re.search(r'name="draft_epoch" value="(\d+)"', page).group(1)
    record("panel shows hash prefix", manifest[:8] in page,
           f"manifest sha256 {manifest[:8]}, epoch {epoch}")
    with ContactStore(db) as store:
        store.conn.execute("UPDATE contacts SET first_name = 'Changed' WHERE contact_id = 'fx-b'")
        store.conn.commit()
    r = client.post(f"/campaigns/{CID}/approve", follow_redirects=True, data={
        "confirm": CID, "draft_manifest": manifest, "draft_epoch": epoch})
    with ContactStore(db) as store:
        refused = store.get_campaign(CID)["status"] == "draft"
        store.conn.execute("UPDATE contacts SET first_name = 'Drill' WHERE contact_id = 'fx-b'")
        store.conn.commit()
    record("stale approval refused", refused and "stale page" in r.text,
           "copy changed under the page; status stays draft")
    page = client.get(f"/campaigns/{CID}").text
    manifest = re.search(r'name="draft_manifest" value="([0-9a-f]{64})"', page).group(1)
    epoch = re.search(r'name="draft_epoch" value="(\d+)"', page).group(1)
    client.post(f"/campaigns/{CID}/approve", data={
        "confirm": CID, "draft_manifest": manifest, "draft_epoch": epoch})
    client.post(f"/campaigns/{CID}/start-sending", data={"confirm": CID})
    with ContactStore(db) as store:
        d = approval.latest_decision(store, CID)
        status = store.get_campaign(CID)["status"]
    record("approve + start sending", status == "sending" and d["snapshot_count"] == 4,
           f"decision #{d['decision_id']}, epoch {d['campaign_draft_epoch']}, "
           f"sha256 {d['manifest_sha256'][:8]}, {d['snapshot_count']} snapshots")

    # -- step 1: dry run, dormant engine is inert
    rc = drill.step1(tmp_path, mailer=FixtureTransport(), poll_fn=no_events)
    record("step 1 dry run", rc == 0, "kill switch on, zero leases, watermarks unchanged")

    # -- step 2: draft-to-self under a scoped lift; claim verified, never dispatched
    fx = FixtureTransport()
    lift(client, True)
    rc = drill.step2(tmp_path, mailer=fx, poll_fn=no_events)
    lift(client, False)
    with ContactStore(db) as store:
        states = approval.claim_state_counts(store)
    record("step 2 draft-to-self",
           rc == 0 and fx.sent == [] and fx.drafts
           and all(d[1]["to"] == SEND_FROM for d in fx.drafts)
           and states == {"claimed": 2},
           f"{len(fx.drafts)} self-draft(s), 0 sent, claims {states}")

    # lease expiry cancels the pre-dispatch claims; Retry re-queues
    with ContactStore(db) as store:
        expired = store.expire_leases(cadence._iso(T1))
        states = approval.claim_state_counts(store)
        keys = [a["attempt_key"] for a in store.attempts_for_campaign(CID)]
    for k in keys:
        client.post("/attempts/retry", data={"attempt_key": k, "campaign": CID})
    with ContactStore(db) as store:
        queued = [store.get_attempt(k)["status"] for k in keys]
    record("lease expiry + Retry", expired == 2 and states == {"cancelled": 2}
           and queued == ["queued", "queued"],
           f"{expired} leases expired, claims {states}, attempts {queued}")

    # -- step 5a: live send of step 1 through the fixture transport
    fx = FixtureTransport()
    lift(client, True)
    rep = tick(T1, fx)
    lift(client, False)
    with ContactStore(db) as store:
        bound = {a["attempt_key"]: approval.bound_snapshot(store, a["attempt_key"])
                 for a in store.attempts_for_campaign(CID)}
        claims = approval.claims_for_campaign(store, CID)
    exact = all(approval.draft_sha256(s["subject"], s["body"]) ==
                bound[f"cadence:{i}:1"]["draft_sha256"] and s["to"] ==
                bound[f"cadence:{i}:1"]["recipient"]
                for i, s in zip((1, 2), fx.sent))
    record("step 5 live send (fixture)",
           rep["counters"]["sent"] == 2 and exact
           and all(claims[f"cadence:{i}:1"]["state"] == "delivered" for i in (1, 2)),
           f"sent {len(fx.sent)}; transported bytes == snapshot hash + recipient; "
           f"claims delivered")

    # -- step 5b: reply-halt for fixture A
    with ContactStore(db) as store:
        res = ingest_event(store, {
            "email": TEST_ADDR, "type": "reply", "direction": "inbound",
            "channel": "email", "occurred_at": "2026-07-15T10:30:00+00:00",
            "subject": "RE: LEAD DESK ARMING DRILL step 1", "source": "graph-auto",
            "internet_message_id": "<fixture-reply@example.test>"})
        # and a decision on an old epoch for fixture B: a merge field its
        # step-2 copy uses changes after approval
        store.conn.execute("UPDATE contacts SET first_name = 'Drillo' WHERE contact_id = 'fx-b'")
        store.conn.commit()
    fx = FixtureTransport()
    lift(client, True)
    rep = tick(T2, fx)
    lift(client, False)
    with ContactStore(db) as store:
        alert = store.get_state(f"send_guard_alert:{CID}") or ""
        a2 = store.get_attempt("cadence:1:2")
    record("reply ingested", bool(res.get("inserted")), "capture sink took the reply")
    record("step 5 reply-halt", a2 is None and fx.sent == [],
           f"follow-up for A never claimed (tick claimed {rep['claimed']})")
    record("old-epoch decision releases nothing",
           "approval_stale" in alert and rep["claimed"] == 0,
           "B's step 2 refused at claim: draft re-filed since approval")

    # -- re-approve B, then an unknown outcome on its step 2
    page = client.get(f"/campaigns/{CID}").text
    manifest = re.search(r'name="draft_manifest" value="([0-9a-f]{64})"', page).group(1)
    epoch = re.search(r'name="draft_epoch" value="(\d+)"', page).group(1)
    client.post(f"/campaigns/{CID}/approve", data={
        "confirm": CID, "draft_manifest": manifest, "draft_epoch": epoch})
    client.post(f"/campaigns/{CID}/start-sending", data={"confirm": CID})
    fx = FixtureTransport()
    fx.fail_next = TimeoutError("fixture: read timed out after POST")
    lift(client, True)
    rep = tick(T2, fx)
    rep_again = tick(T2, FixtureTransport())
    lift(client, False)
    r_retry = client.post("/attempts/retry", data={"attempt_key": "cadence:2:2",
                                                    "campaign": CID})
    with ContactStore(db) as store:
        unknown = drill.status_report(tmp_path)["unknown_claims"]
    record("unknown outcome held, no retry",
           rep["counters"]["ambiguous"] == 1 and rep_again["claimed"] == 0
           and r_retry.status_code == 400 and unknown == ["cadence:2:2"],
           f"claim unknown; re-tick claimed {rep_again['claimed']}; Retry HTTP "
           f"{r_retry.status_code}; readiness unknown_claims {unknown}")

    r = client.post("/attempts/reconcile", data={
        "attempt_key": "cadence:2:2", "outcome": "delivered",
        "coordinate": "<fixture-late@example.test>",
        "evidence": "fixture Sent Items shows the mail at 11:00:03", "campaign": CID})
    with ContactStore(db) as store:
        audit = drill.status_report(tmp_path)
        attempt = store.get_attempt("cadence:2:2")
    record("trusted reconcile -> readiness clean",
           r.status_code in (200, 303) and attempt["status"] == "sent"
           and audit["unknown_claims"] == [] and audit["kill_switch"] is True,
           f"claims {audit['claims']}; unknown_claims []; kill_switch on")

    width = max(len(s) for s, _, _ in sheet)
    lines = ["", "SEND DRILL (fixture transport, epoch-keyed approval)"]
    lines += [f"  {v}  {s.ljust(width)}  {e}" for s, v, e in sheet]
    lines.append(f"PASS send drill: {len(sheet)}/{len(sheet)} checks")
    with capsys.disabled():
        print("\n".join(lines))
