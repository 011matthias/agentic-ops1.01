"""T3: truth-ledger backfill - idempotent imid-keyed replay, unmatched
parking (never auto-create), the ground.py de-* key upgrade, the H5
no-negative-state policy, the capture-parity reply/OOO mapping, and the
verify diff. Ledger fixtures are small in-test dicts mirroring the real
outreach-truth-ledger.json member shapes."""
from __future__ import annotations

import json

from lead_desk.backfill import backfill, sweep_id, verify
from lead_desk.web.store import ContactStore

DIRK = "dirk.neumann@brisken.com"
NOW = "2026-07-15T00:00:00+00:00"


def _store(tmp_path) -> ContactStore:
    return ContactStore(tmp_path / "t.sqlite")


def _contact(store, cid, email):
    store.upsert_contact({"contact_id": cid, "natural_key": email,
                          "email": email}, now=NOW)
    return cid


def _ev(imid, ts="2026-07-27T10:46:11Z", folder="Sent Items",
        subject="Good to have you at our booth in Rome"):
    return {"imid": imid, "ts": ts, "folder": folder, "mailbox": DIRK,
            "subject": subject}


def _ledger(cohorts: dict) -> dict:
    return {"tool": "brisken-truth-sweep v1",
            "generated_at": "2026-08-13T14:39:31Z", "since": "2026-05-01",
            "corpus": {"outbound": 10}, "cohorts": cohorts,
            "confirm_zero": {"cold_farm_53": {"method": "no farm mailboxes"}}}


def _events(store, cid):
    return store.get_events(cid)


# -- idempotency ---------------------------------------------------------------

def test_backfill_idempotent(tmp_path):
    with _store(tmp_path) as s:
        c1 = _contact(s, "c1", "a@acme.com")
        led = _ledger({"GA": {"members": {
            "a@acme.com": {"sent": True, "evidence": [_ev("<m1@x.com>")]}}}})
        r1 = backfill(s, led, apply=True)
        assert r1["totals"]["sent_inserted"] == 1
        assert r1["totals"]["sent_deduped"] == 0
        r2 = backfill(s, led, apply=True)
        assert r2["totals"]["sent_inserted"] == 0
        assert r2["totals"]["sent_deduped"] == 1
        evs = _events(s, c1)
        assert len(evs) == 1
        e = evs[0]
        assert (e["type"], e["direction"], e["ext_key"]) == \
            ("sent", "outbound", "<m1@x.com>")
        assert e["source"] == "truth-sweep"
        assert e["created_by"] == sweep_id(led)
        assert e["campaign"] == "rome-2026"
        assert json.loads(e["detail"]) == {
            "cohort": "GA", "folder": "Sent Items", "mailbox": DIRK}
        # every apply logs a truth_runs row
        runs = s.conn.execute(
            "SELECT kind FROM truth_runs ORDER BY finished_at").fetchall()
        assert [r["kind"] for r in runs] == ["backfill", "backfill"]


def test_backfill_dry_run_writes_nothing(tmp_path):
    with _store(tmp_path) as s:
        _contact(s, "c1", "a@acme.com")
        led = _ledger({"GA": {"members": {
            "a@acme.com": {"sent": True, "evidence": [_ev("<m1@x.com>")]}}}})
        rep = backfill(s, led)                       # dry-run default
        assert rep["totals"]["sent_inserted"] == 1   # would insert
        assert s.count_events() == 0
        assert s.conn.execute("SELECT COUNT(*) FROM truth_runs").fetchone()[0] == 0


# -- unknown roster members ----------------------------------------------------

def test_backfill_unknown_roster_member_queued_never_created(tmp_path):
    with _store(tmp_path) as s:
        led = _ledger({"GA": {"members": {
            "stranger@new.com": {"sent": True, "evidence": [_ev("<u1@x.com>")]}}}})
        rep = backfill(s, led, apply=True)
        assert rep["totals"]["queued_unmatched"] == 1
        assert rep["totals"]["sent_inserted"] == 0
        assert s.count_contacts() == 0               # never auto-created
        assert s.count_events() == 0
        rows = s.list_unmatched()
        assert len(rows) == 1 and rows[0]["email"] == "stranger@new.com"
        assert json.loads(rows[0]["payload"])["internet_message_id"] == "<u1@x.com>"
        # re-run bumps the same row instead of duplicating it
        backfill(s, led, apply=True)
        rows = s.list_unmatched()
        assert len(rows) == 1 and rows[0]["seen_count"] == 2


# -- ground.py de-* key handling ----------------------------------------------

def _seed_ewave(s, wave="E1"):
    cid = _contact(s, "c1", "a@acme.com")
    s.add_event(contact_id=cid, ts="2026-06-19T00:00:00+00:00",
                channel="email", direction="outbound", type="sent",
                subject=f"During-event {wave}", detail="mailbox-grounded",
                source="graph", ext_key=f"de-{wave}-{cid}", now=NOW)
    led = _ledger({wave: {"members": {
        "a@acme.com": {"sent": True, "evidence": [_ev("<e1@x.com>")],
                       "replied": False, "ooo": False}}}})
    return cid, led


def test_backfill_ewave_skip_without_flag(tmp_path):
    with _store(tmp_path) as s:
        cid, led = _seed_ewave(s)
        rep = backfill(s, led, apply=True)
        assert rep["cohorts"]["E1"]["skipped_dekey"] == 1
        assert rep["totals"]["sent_inserted"] == 0
        evs = _events(s, cid)
        assert [e["ext_key"] for e in evs] == [f"de-E1-{cid}"]  # untouched


def test_backfill_ewave_key_upgrade_net_zero(tmp_path):
    with _store(tmp_path) as s:
        cid, led = _seed_ewave(s)
        before = s.count_events()
        rep = backfill(s, led, apply=True, upgrade_ewave_keys=True)
        assert rep["cohorts"]["E1"]["upgraded_dekey"] == 1
        assert s.count_events() == before            # net count unchanged
        keys = [e["ext_key"] for e in _events(s, cid)]
        assert keys == ["<e1@x.com>"]                # imid in, de-* row gone
        # idempotent: the second run is a plain dedupe, nothing to upgrade
        rep2 = backfill(s, led, apply=True, upgrade_ewave_keys=True)
        assert rep2["cohorts"]["E1"]["upgraded_dekey"] == 0
        assert rep2["cohorts"]["E1"]["sent_deduped"] == 1
        assert s.count_events() == before


# -- H5 policy -----------------------------------------------------------------

def test_backfill_h5_carries_cohort_and_no_negative_state(tmp_path):
    with _store(tmp_path) as s:
        cid = _contact(s, "c1", "hot@lead.com")
        led = _ledger({"H5_hottest_leads": {"members": {
            "hot@lead.com": {"sent": True, "send_count": 1,
                             "evidence": [_ev("<h5@x.com>",
                                              subject="Rafa says hello back")]}}}})
        rep = backfill(s, led, apply=True)
        assert rep["cohorts"]["H5"]["sent_inserted"] == 1
        evs = _events(s, cid)
        assert [e["type"] for e in evs] == ["sent"]  # nothing derived/negative
        assert json.loads(evs[0]["detail"])["cohort"] == "H5"


# -- inbound mapping (capture parity) -----------------------------------------

def test_backfill_ooo_maps_to_note_reply_maps_to_reply(tmp_path):
    with _store(tmp_path) as s:
        cr = _contact(s, "cr", "replied@x.com")
        co = _contact(s, "co", "away@x.com")
        led = _ledger({"GA": {"members": {
            "replied@x.com": {
                "sent": True, "evidence": [_ev("<s1@x.com>")],
                "replied": True, "ooo_only": False,
                "reply_evidence": [_ev("<r1@x.com>", folder="Inbox",
                                       subject="Re: our booth in Rome")]},
            "away@x.com": {
                "sent": True, "evidence": [_ev("<s2@x.com>")],
                "replied": False, "ooo_only": True,
                "reply_evidence": [_ev("<r2@x.com>", folder="Inbox",
                                       subject="Automatic reply: Rome")]},
        }}})
        rep = backfill(s, led, apply=True)
        assert rep["totals"]["replies_inserted"] == 1
        assert rep["totals"]["ooo_notes_inserted"] == 1
        reply = [e for e in _events(s, cr) if e["direction"] == "inbound"]
        assert [(e["type"], e["ext_key"]) for e in reply] == \
            [("reply", "<r1@x.com>")]
        note = [e for e in _events(s, co) if e["direction"] == "inbound"]
        assert [(e["type"], e["ext_key"]) for e in note] == \
            [("note", "<r2@x.com>")]                 # OOO never promotes


# -- verify --------------------------------------------------------------------

def test_backfill_verify_detects_mismatch(tmp_path):
    with _store(tmp_path) as s:
        _contact(s, "c1", "a@acme.com")
        led = _ledger({"GA": {"members": {
            "a@acme.com": {"sent": True, "evidence": [_ev("<m1@x.com>")]}}}})
        backfill(s, led, apply=True)
        v = verify(s, led)
        assert v["ok"] is True
        ga = v["cohorts"][0]
        assert (ga["sent_expected"], ga["sent_in_db"]) == (1, 1)
        # an event lost from the DB flips the cohort to MISMATCH
        s.conn.execute("DELETE FROM outreach_events WHERE ext_key = '<m1@x.com>'")
        s.conn.commit()
        v2 = verify(s, led)
        assert v2["ok"] is False
        assert v2["cohorts"][0]["sent_in_db"] == 0


def test_backfill_verify_accepts_dekey_as_sent(tmp_path):
    """An E-wave member still on the ground.py synthetic key IS represented
    in the DB; verify must not flag the un-upgraded state as a mismatch."""
    with _store(tmp_path) as s:
        _cid, led = _seed_ewave(s)
        backfill(s, led, apply=True)     # skip-if-de-key-exists
        assert verify(s, led)["ok"] is True
