"""Journal WAL: state machine, pending detection, compaction."""
from lead_desk.worker.journal import Journal


def test_pending_tracks_latest_nonterminal_state(tmp_path):
    j = Journal(tmp_path / "journal.jsonl")
    j.write("cadence:1:1", "claimed", to="a@x.com")
    j.write("cadence:1:1", "com_issued")
    j.write("cadence:2:1", "claimed", to="b@x.com")
    j.write("cadence:2:1", "com_sent")
    j.write("cadence:2:1", "acked", outcome="sent")
    j.write("cadence:3:1", "drafted")
    j.write("cadence:3:1", "acked", outcome="drafted")

    pending = j.pending()
    assert set(pending) == {"cadence:1:1"}
    assert pending["cadence:1:1"]["state"] == "com_issued"


def test_pending_preserves_metadata_for_reconcile(tmp_path):
    j = Journal(tmp_path / "journal.jsonl")
    j.write("cadence:9:2", "claimed", to="c@x.com", lease_id="abc")
    j.write("cadence:9:2", "com_issued", to="c@x.com", subject="Hello")
    entry = j.pending()["cadence:9:2"]
    # The reconcile pass needs to find the mail in Sent Items by (to, subject).
    assert entry["to"] == "c@x.com"
    assert entry["subject"] == "Hello"


def test_ack_failed_keeps_replayable_payload(tmp_path):
    j = Journal(tmp_path / "journal.jsonl")
    ack = {"attempt_key": "cadence:4:1", "lease_id": "L", "status": "sent"}
    j.write("cadence:4:1", "com_sent")
    j.write("cadence:4:1", "ack_failed", ack=ack)
    entry = j.pending()["cadence:4:1"]
    assert entry["state"] == "ack_failed"
    assert entry["ack"]["lease_id"] == "L"


def test_corrupt_lines_are_skipped(tmp_path):
    p = tmp_path / "journal.jsonl"
    j = Journal(p)
    j.write("cadence:1:1", "claimed")
    with p.open("a", encoding="utf-8") as fh:
        fh.write("not json at all\n")
    j.write("cadence:1:1", "acked")
    assert j.pending() == {}
    assert len(j.entries()) == 2


def test_compact_keeps_pending_drops_old_terminal(tmp_path):
    j = Journal(tmp_path / "journal.jsonl")
    j.write("old:done", "acked")
    j.write("live:one", "com_issued")
    # Backdate the terminal entry far past the retention window.
    lines = (tmp_path / "journal.jsonl").read_text(encoding="utf-8").splitlines()
    lines[0] = lines[0].replace("2026-", "2020-").replace("2027-", "2020-")
    (tmp_path / "journal.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    j.compact(keep_terminal_days=14)
    keys = {e["key"] for e in j.entries()}
    assert "live:one" in keys
    assert "old:done" not in keys
