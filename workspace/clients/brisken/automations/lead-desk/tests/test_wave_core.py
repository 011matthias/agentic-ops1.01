"""Shared wave core: enumerate the staged draft-dirk set + campaign-page
visibility. Enumeration only - no release/send action exists in this layer.

enumerate_wave assembles the wave from journaled attempts (status 'drafted'
with a correlated entry_id), re-runs the claim-time send guards as pre-checks
(recipient pin, denied domain, suppression), and fingerprints the set with an
order-independent ids_hash. Fixtures mirror test_cloud_worker /
test_send_guards; conftest pins cadence.now_utc to IN_WINDOW.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

import pytest

from lead_desk.web import cadence
from lead_desk.web.app import create_app
from lead_desk.web.service import now_iso
from lead_desk.web.store import ContactStore

IN_WINDOW = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)
WORKER = "w"


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


def make_engine_campaign(store, contact_ids, cid="camp1", *, degree="warm",
                         send_mode="draft-dirk", n_steps=1):
    """Campaign + template + sequence + enrollments through both gates
    (same shape as test_cloud_worker; warm/draft-dirk is the wave case)."""
    now = "2026-07-14T09:00:00+00:00"
    store.create_campaign(cid, "Test Campaign", now, daily_cap=40,
                          throttle_seconds=0, jitter_seconds=0)
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


def _store(tmp_path) -> ContactStore:
    data = tmp_path / "data"
    data.mkdir()
    return ContactStore(data / "lead-desk.sqlite")


def stage_drafts(store, entry_ids: dict[str, str | None]):
    """Claim every due send and ack each as 'drafted' with the given
    per-contact entry_id (the worker's draft-dirk path). Returns the claims
    keyed by contact_id."""
    claims = {c["contact_id"]: c
              for c in cadence.claim_sends(store, WORKER, 50, at=IN_WINDOW)["claims"]}
    assert set(entry_ids) <= set(claims), (entry_ids, claims)
    for contact_id, entry_id in entry_ids.items():
        cl = claims[contact_id]
        res = cadence.resolve_result(store, {
            "attempt_key": cl["attempt_key"], "lease_id": cl["lease_id"],
            "status": "drafted", "entry_id": entry_id})
        assert res["ok"], res
    return claims


# -- enumeration ------------------------------------------------------------

def test_enumerate_wave_lists_only_drafted_with_entry_ids(tmp_path):
    store = _store(tmp_path)
    cids = [make_contact(store, i) for i in (1, 2, 3)]
    make_engine_campaign(store, cids)
    claims = {c["contact_id"]: c
              for c in cadence.claim_sends(store, WORKER, 50, at=IN_WINDOW)["claims"]}
    assert len(claims) == 3
    # c1: drafted with entry_id (in the wave); c2: sent; c3: drafted, no entry_id.
    assert cadence.resolve_result(store, {
        "attempt_key": claims["c1"]["attempt_key"], "lease_id": claims["c1"]["lease_id"],
        "status": "drafted", "entry_id": "AAA-1"})["ok"]
    assert cadence.resolve_result(store, {
        "attempt_key": claims["c2"]["attempt_key"], "lease_id": claims["c2"]["lease_id"],
        "status": "sent"})["ok"]
    assert cadence.resolve_result(store, {
        "attempt_key": claims["c3"]["attempt_key"], "lease_id": claims["c3"]["lease_id"],
        "status": "drafted"})["ok"]
    wave = cadence.enumerate_wave(store, "camp1")
    assert wave["count"] == 1 and wave["blocks"] == []
    item = wave["items"][0]
    assert item["attempt_key"] == claims["c1"]["attempt_key"]
    assert item["entry_id"] == "AAA-1"
    assert item["to"] == "c1@example.com"
    assert item["subject"] == "Hello First1"
    assert item["contact_id"] == "c1" and item["contact_name"] == "First1 Last1"
    assert item["step_no"] == 1
    assert item["staged_days"] == 0                       # staged at the pinned now
    assert wave["oldest_staged_at"] == item["staged_at"]


def test_enumerate_wave_blocks_unpinned_or_drifted_recipient(tmp_path):
    store = _store(tmp_path)
    cids = [make_contact(store, i) for i in (1, 2)]
    make_engine_campaign(store, cids)
    stage_drafts(store, {"c1": "E-1", "c2": "E-2"})
    # c1's pin vanishes; c2's pin was re-snapshotted to a different address
    # after staging (an incremental re-approval over a synced sheet edit).
    store.conn.execute(
        "DELETE FROM campaign_recipient_pins WHERE campaign_id = 'camp1' "
        "AND contact_id = 'c1'")
    store.conn.execute(
        "UPDATE campaign_recipient_pins SET email = 'reviewed@example.com' "
        "WHERE campaign_id = 'camp1' AND contact_id = 'c2'")
    store.conn.commit()
    wave = cadence.enumerate_wave(store, "camp1")
    assert wave["count"] == 0 and wave["items"] == []
    kinds = {b["contact_id"]: b["kind"] for b in wave["blocks"]}
    assert kinds == {"c1": "recipient_not_approved", "c2": "recipient_drift"}
    drift = next(b for b in wave["blocks"] if b["contact_id"] == "c2")
    assert "re-approve" in drift["detail"]


def test_enumerate_wave_blocks_denied_domain_and_suppressed(tmp_path):
    store = _store(tmp_path)
    c1 = make_contact(store, 1, email="a@blocked.example")
    c2 = make_contact(store, 2, email="b@ok.example")
    make_engine_campaign(store, [c1, c2])
    stage_drafts(store, {"c1": "E-1", "c2": "E-2"})
    # The world moves after staging: the domain gets deny-listed and the
    # contact opts out. Both must fall out of the wave, loudly.
    store.set_state("send_deny_domains", json.dumps(["blocked.example"]), now_iso())
    store.set_suppressed("c2", True, "unsubscribed", "tester", now_iso())
    wave = cadence.enumerate_wave(store, "camp1")
    assert wave["count"] == 0 and wave["items"] == []
    kinds = {b["contact_id"]: b["kind"] for b in wave["blocks"]}
    assert kinds == {"c1": "domain_denied", "c2": "suppressed"}


def test_enumerate_wave_ids_hash_stable_and_order_independent(tmp_path):
    store = _store(tmp_path)
    cids = [make_contact(store, i) for i in (1, 2, 3)]
    make_engine_campaign(store, cids)
    claims = stage_drafts(store, {"c1": "zz", "c2": "aa", "c3": "mm"})
    expected = hashlib.sha256("\n".join(["aa", "mm", "zz"]).encode("utf-8")).hexdigest()
    wave = cadence.enumerate_wave(store, "camp1")
    assert wave["count"] == 3 and wave["ids_hash"] == expected
    # Re-order the underlying rows (attempts_for_campaign sorts by claimed_at):
    # the fingerprint must not move.
    store.conn.execute(
        "UPDATE send_attempts SET claimed_at = '2026-07-15T23:00:00+00:00' "
        "WHERE attempt_key = ?", (claims["c1"]["attempt_key"],))
    store.conn.commit()
    assert cadence.enumerate_wave(store, "camp1")["ids_hash"] == expected


# -- campaign page ----------------------------------------------------------

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("LEAD_DESK_AUTH_SECRET", raising=False)
    c = TestClient(create_app(tmp_path))
    c.db = tmp_path / "lead-desk.sqlite"
    return c


def test_campaign_page_renders_staged_card(client):
    with ContactStore(client.db) as s:
        cids = [make_contact(s, i) for i in (1, 2)]
        make_engine_campaign(s, cids)
    # Nothing staged yet: no card (the cheap check gates the enumeration).
    r = client.get("/campaigns/camp1")
    assert r.status_code == 200 and "Staged in Dirk's Drafts" not in r.text
    with ContactStore(client.db) as s:
        claims = stage_drafts(s, {"c1": "E-1", "c2": "E-2"})
        ids_hash = cadence.enumerate_wave(s, "camp1")["ids_hash"]
    r = client.get("/campaigns/camp1")
    assert r.status_code == 200
    assert "Staged in Dirk's Drafts (2)" in r.text
    assert "First1 Last1" in r.text and "c1@example.com" in r.text
    assert "Hello First2" in r.text
    assert ids_hash[-8:] in r.text
    assert "days old" not in r.text                        # staged today: no banner
    # Age one draft past the stale threshold: the banner names the oldest age.
    with ContactStore(client.db) as s:
        s.update_attempt(claims["c1"]["attempt_key"],
                         {"resolved_at": "2026-07-08T09:00:00+00:00"})
    r = client.get("/campaigns/camp1")
    assert "Oldest staged draft is 7 days old" in r.text
