"""P0: clean-orphan-state deletes only lifecycle state rows for campaigns that
no longer exist, never protected keys, and is idempotent. T3 adds
suppression-import (external list -> ledger + contact flags) and the
truth-audit report."""
from __future__ import annotations

from lead_desk.identity import contact_id_for
from lead_desk.maintenance import (
    clean_orphan_state, find_orphan_state_keys, rekey_anon_contacts,
    suppression_import, truth_audit,
)
from lead_desk.web.store import ContactStore, event_hash

NOW = "2026-07-15T00:00:00+00:00"


def _seed(store: ContactStore) -> None:
    store.create_campaign("rome-2026", "Rome 2026", NOW, status="done")
    # live campaign keys -> keep
    store.set_state("approval:rome-2026", "{}", NOW)
    store.set_state("approve-result:rome-2026", "{}", NOW)
    # orphan keys (campaign deleted) -> delete
    store.set_state("upload-report:test-gate", "{}", NOW)
    store.set_state("start-result:test-gate", "{}", NOW)
    store.set_state("sending-started:test-ndr", "{}", NOW)
    # protected keys / prefixes -> never touched
    store.set_state("kill_switch", "1", NOW)
    store.set_state("worker_heartbeat", "{}", NOW)
    store.set_state("source:rome-2026", "{}", NOW)
    store.set_state("approval-superseded:test-gate", "{}", NOW)  # not in scope


def test_finds_only_orphans(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        _seed(store)
        assert find_orphan_state_keys(store) == [
            "sending-started:test-ndr",
            "start-result:test-gate",
            "upload-report:test-gate",
        ]


def test_clean_deletes_orphans_only(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        _seed(store)
        report = clean_orphan_state(store)
        assert report["deleted_count"] == 3
        # live + protected keys survive
        assert store.get_state("approval:rome-2026") == "{}"
        assert store.get_state("approve-result:rome-2026") == "{}"
        assert store.get_state("kill_switch") == "1"
        assert store.get_state("worker_heartbeat") == "{}"
        assert store.get_state("source:rome-2026") == "{}"
        assert store.get_state("approval-superseded:test-gate") == "{}"
        # orphans gone
        assert store.get_state("upload-report:test-gate") is None
        assert store.get_state("start-result:test-gate") is None
        assert store.get_state("sending-started:test-ndr") is None


def test_idempotent(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        _seed(store)
        clean_orphan_state(store)
        again = clean_orphan_state(store)
        assert again["orphan_count"] == 0 and again["deleted_count"] == 0


def test_dry_run_deletes_nothing(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        _seed(store)
        report = clean_orphan_state(store, dry_run=True)
        assert report["orphan_count"] == 3 and report["deleted_count"] == 0
        assert store.get_state("upload-report:test-gate") == "{}"


# --- rekey-anon: merge the ordinal-key duplicates -----------------------------

def _seed_anon_dupes(store: ContactStore) -> tuple[str, str]:
    """Two anon rows for the SAME person under different OLD (ordinal) keys,
    each with an event and an enrollment. Returns the two old contact_ids."""
    store.create_campaign("rome-2026", "Rome 2026", NOW, status="done")
    a = contact_id_for("anon:aaa")   # old ordinal-based keys, now duplicates
    b = contact_id_for("anon:bbb")
    for cid, nk, supp, reason in [(a, "anon:aaa", 1, "anon"), (b, "anon:bbb", 0, None)]:
        store.upsert_contact({
            "contact_id": cid, "natural_key": nk, "campaign": "rome-2026",
            "first_name": "Jo", "last_name": "Blank", "company": "Acme",
            "suppressed": supp, "suppress_reason": reason,
        }, now=NOW)
        store.add_event(contact_id=cid, ts=NOW, channel="email",
                        direction="outbound", type="sent", detail=f"e-{cid}", now=NOW)
        store.enroll(cid, "rome-2026", "test", NOW)
    return a, b


def test_rekey_merges_ordinal_duplicates(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        a, b = _seed_anon_dupes(store)
        report = rekey_anon_contacts(store)
        assert report["groups_changed"] == 1
        assert report["contacts_removed"] == 1        # 2 anon rows -> 1
        assert report["events_unchanged"] is True     # events repointed, not dropped
        # exactly one contact remains, carrying both events
        remaining = store.conn.execute("SELECT contact_id FROM contacts").fetchall()
        assert len(remaining) == 1
        canon = remaining[0]["contact_id"]
        assert store.count_events() == 2
        assert len(store.get_events(canon)) == 2
        # enrollment deduped to one; suppression union kept (one row was suppressed)
        enr = store.conn.execute(
            "SELECT COUNT(*) FROM enrollments WHERE campaign_id='rome-2026'").fetchone()[0]
        assert enr == 1
        assert store.get_contact(canon)["suppressed"] == 1


def test_rekey_is_idempotent(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        _seed_anon_dupes(store)
        rekey_anon_contacts(store)
        again = rekey_anon_contacts(store)
        assert again["groups_changed"] == 0 and again["contacts_removed"] == 0


def test_rekey_leaves_nameless_orgonly_untouched(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        store.create_campaign("rome-2026", "Rome 2026", NOW, status="done")
        # three org-only opt-outs from the same company: distinct headcount,
        # no name -> rekey must NOT merge them (that would be data loss).
        for nk in ("anon:z1", "anon:z2", "anon:z3"):
            store.upsert_contact({"contact_id": contact_id_for(nk), "natural_key": nk,
                                  "company": "Zanders", "tier": "ANON",
                                  "suppressed": 1, "suppress_reason": "no_consent",
                                  "campaign": "rome-2026"}, now=NOW)
        report = rekey_anon_contacts(store)
        assert report["anon_total"] == 0          # named-only scope excludes them
        assert report["groups_changed"] == 0
        assert store.count_contacts() == 3         # all three preserved


def test_rekey_leaves_distinct_people_alone(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        store.create_campaign("rome-2026", "Rome 2026", NOW, status="done")
        # two genuinely different email-less people -> different content keys
        for nk, first, company in [("anon:x", "Ann", "Acme"), ("anon:y", "Bob", "Beta")]:
            store.upsert_contact({"contact_id": contact_id_for(nk), "natural_key": nk,
                                  "first_name": first, "company": company,
                                  "campaign": "rome-2026"}, now=NOW)
        report = rekey_anon_contacts(store)
        # both re-key (drop the old key) but neither merges into the other
        assert report["contacts_removed"] == 0
        assert store.count_contacts() == 2


# --- suppression-import: external list -> ledger + contact flags --------------

SUPPRESSION_CSV = """value,kind,reason,source
blocked@x.com,email,opt-out,external-list
heldco.com,domain,customer-domain,zoho-crm
"""


def _seed_suppression(store: ContactStore, tmp_path):
    for cid, email in [("c1", "blocked@x.com"), ("c2", "b@heldco.com"),
                       ("c3", "ok@other.com")]:
        store.upsert_contact({"contact_id": cid, "natural_key": email,
                              "email": email}, now=NOW)
    csv_path = tmp_path / "list.csv"
    csv_path.write_text(SUPPRESSION_CSV, encoding="utf-8")
    return csv_path


def test_suppression_import_idempotent_and_sets_contacts(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        csv_path = _seed_suppression(store, tmp_path)
        # dry-run (default): counts only, nothing written
        dry = suppression_import(store, csv_path)
        assert dry["dry_run"] is True
        assert dry["entries_new"] == 2 and dry["contacts_suppressed"] == 2
        assert store.conn.execute(
            "SELECT COUNT(*) FROM suppression_entries").fetchone()[0] == 0
        assert store.get_contact("c1")["suppressed"] == 0
        # apply: ledger rows land (domains as '@domain'), contacts flagged
        rep = suppression_import(store, csv_path, apply=True)
        assert rep["entries_new"] == 2 and rep["entries_existing"] == 0
        assert rep["contacts_suppressed"] == 2
        entries = {r["entry"]: r["kind"] for r in store.conn.execute(
            "SELECT entry, kind FROM suppression_entries").fetchall()}
        assert entries == {"blocked@x.com": "email", "@heldco.com": "domain"}
        for cid in ("c1", "c2"):
            c = store.get_contact(cid)
            assert c["suppressed"] == 1
            assert c["suppress_reason"] == "external-suppression-list"
            assert c["suppressed_by"] == "suppression-import"
        assert store.get_contact("c3")["suppressed"] == 0
        # second apply: everything existing, nothing left to suppress
        again = suppression_import(store, csv_path, apply=True)
        assert again["entries_new"] == 0 and again["entries_existing"] == 2
        assert again["contacts_suppressed"] == 0


# --- truth-audit: provenance report (never a gate) ----------------------------

def test_truth_audit_reports_nonimid_events(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        store.upsert_contact({"contact_id": "c1", "natural_key": "a@x.com",
                              "email": "a@x.com"}, now=NOW)
        # ext_key NULL (manual), synthetic de-* (graph), real imid (truth-sweep)
        store.add_event(contact_id="c1", ts=NOW, channel="email",
                        direction="outbound", type="sent", detail="hand-logged",
                        source="manual", now=NOW)
        store.add_event(contact_id="c1", ts=NOW, channel="email",
                        direction="outbound", type="sent", ext_key="de-E1-c1",
                        source="graph", now=NOW)
        store.add_event(contact_id="c1", ts=NOW, channel="email",
                        direction="outbound", type="sent", ext_key="<m1@x.com>",
                        source="truth-sweep", now=NOW)
        # inbound non-imid events are out of scope for the outbound audit
        store.add_event(contact_id="c1", ts=NOW, channel="email",
                        direction="inbound", type="reply", detail="reply",
                        source="manual", now=NOW)
        store.record_unmatched("stranger@new.com", "{}",
                               event_hash("stranger@new.com", NOW, "email",
                                          "sent", None, "<u1@x.com>"), NOW)
        store.add_suppression_entry("@heldco.com", "domain", "test", NOW)
        store.insert_truth_run(run_id="r1", kind="backfill", started_at=NOW,
                               finished_at=NOW, window_since="2026-05-01",
                               corpus_messages=1, folders_scanned=0,
                               folders_failed="[]", events_added=1, report="{}")
        rep = truth_audit(store)
        assert rep["non_imid_outbound"]["total"] == 2
        assert rep["non_imid_outbound"]["by_source"] == {"manual": 1, "graph": 1}
        assert rep["unmatched_open"] == 1
        assert rep["suppression_entries"] == 1
        assert [r["run_id"] for r in rep["recent_truth_runs"]] == ["r1"]
