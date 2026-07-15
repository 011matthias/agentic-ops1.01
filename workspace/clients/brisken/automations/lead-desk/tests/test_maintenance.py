"""P0: clean-orphan-state deletes only lifecycle state rows for campaigns that
no longer exist, never protected keys, and is idempotent."""
from __future__ import annotations

from lead_desk.maintenance import clean_orphan_state, find_orphan_state_keys
from lead_desk.web.store import ContactStore

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
