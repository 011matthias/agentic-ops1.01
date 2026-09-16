"""The two unlocked period writers, and the two byte-destroying file writes.

Backlog item 66 (carved from the item-49 storage review; disclosed in
`docs/electronic-storage-system-description.md` section 12, rows 3 and 14).

Two paths rebuilt the WHOLE period record from the row they had read minutes
earlier, with no lock and no re-read: the manual per-charge attach and the
bulk receipt-folder ingest. `_BATCH_ADD_LOCK` already serialized mail intake,
add-receipts, delete-period and every `rematch_month` commit, so a write from
either of these two could be lost under a concurrent one, silently, with no
error on either side. The interleaving test below drives both routes at once
with a barrier at their reads; before the fix one of the two receipts is gone
when the dust settles.

Separately, two writes destroyed stored bytes. Re-attaching a receipt to the
same charge under the same filename wrote over it in place, and replacing a
file on a queued upload deleted the file it replaced; neither kept a version
and neither left a record, in a system whose stated purpose is retaining what
arrived. A superseded file is now moved aside under a versioned name instead,
and the manual attach records the replacement on the snapshot.
"""
from __future__ import annotations

import hashlib
import inspect
import threading
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web import service  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import INTAKE_RECEIVED, RunStore  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

PNG_V1 = b"\x89PNG\r\n\x1a\n first-version-bytes"
PNG_V2 = b"\x89PNG\r\n\x1a\n second-version-bytes-entirely-different"

# How long a writer holds at the rendezvous before concluding the other one
# cannot reach it (because the lock is holding it out) and going on alone. The
# fixed path pays this once; it is wall clock, not a correctness margin, so it
# only has to exceed the milliseconds the other writer needs to get from one
# read to the next when nothing is serializing them.
BARRIER_HOLD_S = 2.0
# Generous by contrast: a writer that never returns is a hang to report, not a
# timing assumption.
JOIN_TIMEOUT_S = 120.0


@pytest.fixture
def client(tmp_path, monkeypatch):
    # No OCR anywhere in this module: every receipt lands on the bare-filename
    # path, which is enough to be IN the pool, and that is all these tests ask.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _files():
    return {
        "statement": (
            "statement.example.csv",
            (EXAMPLES / "statement.example.csv").read_bytes(),
            "text/csv",
        ),
        "receipts": (
            "receipts.example.csv",
            (EXAMPLES / "receipts.example.csv").read_bytes(),
            "text/csv",
        ),
    }


def _create_run(client) -> str:
    resp = client.post(
        "/api/runs",
        files=_files(),
        data={
            "account_id": "amex-9001",
            "legal_entity_id": "brisken-llc",
            "account_card_currency": "USD",
            "receipts_source": "csv",
        },
    )
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job["run_id"]


def _run(client, run_id):
    with RunStore(client._data_root / "recon-web.sqlite") as db:
        return db.get_run(run_id)


def _doc_ids(client, run_id) -> set[str]:
    snapshot = _run(client, run_id).snapshot
    return {r["document_id"] for r in snapshot["receipts"]}


def _unmatched_tx(client, run_id) -> str:
    """The one example charge left unmatched: STAPLES NYC."""
    unmatched = _run(client, run_id).snapshot["outcome"]["unmatched_transactions"]
    assert unmatched, "the example month should leave one charge unmatched"
    return unmatched[0]


def _attach(client, run_id, tx_id, name="emailed.png", data=PNG_V1):
    return client.post(
        f"/api/runs/{run_id}/transactions/{tx_id}/receipt",
        files={"file": (name, data, "application/octet-stream")},
    )


def _manual_dir(client, run_id) -> Path:
    return Path(_run(client, run_id).work_dir) / "manual-receipts"


def _current_files(d: Path) -> list[Path]:
    return sorted(p for p in d.glob("*") if p.is_file())


def _archived_bytes(d: Path) -> list[bytes]:
    archive = d / "superseded"
    if not archive.is_dir():
        return []
    return [p.read_bytes() for p in sorted(archive.glob("*")) if p.is_file()]


# ── the interleaving: two writers, one period record ────────────────


def _install_read_barrier(monkeypatch, barrier, targets):
    """Hold each named service function at EVERY snapshot read it makes, until
    the other named one reaches a read too, and proceed alone if it does not.

    The discriminator is whether both writers can sit between their re-read and
    their write at the same time; that is precisely what the lock forbids and
    what losing a write requires. Placing the hold at the read makes it exact:

      * Unlocked, both reach their pre-write read together, the barrier trips
        at once, and both then commit a record neither saw the other build.
        One receipt is gone.
      * Locked, the second writer is still waiting to ACQUIRE while the first
        sits at the barrier, so the first times out after `BARRIER_HOLD_S`,
        commits and releases; the second then re-reads, sees that commit, and
        keeps both. A timed-out barrier is the fixed path's normal outcome, not
        a failure, so the wait proceeds on `BrokenBarrierError` rather than
        raising -- the fix must never be able to deadlock on the instrument
        that measures it.

    Keying on the calling frame rather than on the thread keeps the other
    `snapshot_from_dict` calls in the same request (the view build, the claim
    sync) out of the rendezvous.
    """
    real = service.snapshot_from_dict

    def patched(payload):
        if inspect.currentframe().f_back.f_code.co_name in targets:
            try:
                barrier.wait(timeout=BARRIER_HOLD_S)
            except threading.BrokenBarrierError:
                pass  # the other writer is locked out, or already went through
        return real(payload)

    monkeypatch.setattr(service, "snapshot_from_dict", patched)


def test_concurrent_manual_attach_and_folder_ingest_keep_both_receipts(
    client, monkeypatch
):
    """Both writers rebuild the whole period record. Run them at once, each
    holding at its read until the other has read too, and both receipts must
    still be in the pool afterwards.

    Without the lock the second commit rewrites `receipts` from its own stale
    copy and the first writer's receipt is gone -- no error, no warning, and
    nothing in the payload that says a receipt was ever there.
    """
    run_id = _create_run(client)
    tx_id = _unmatched_tx(client, run_id)
    folder_bytes = b"\xff\xd8\xff\xe0folder-receipt-bytes"
    folder_id = "folder:" + hashlib.sha1(folder_bytes).hexdigest()[:16]
    manual_id = f"manual:{tx_id}"

    barrier = threading.Barrier(2)
    _install_read_barrier(
        monkeypatch,
        barrier,
        {"attach_emailed_receipt", "ingest_receipts_folder_into_run"},
    )

    results: dict[str, object] = {}

    def _do_attach():
        try:
            results["attach"] = _attach(client, run_id, tx_id)
        except Exception as exc:  # noqa: BLE001 - reported by the assertions
            results["attach_error"] = repr(exc)

    def _do_folder():
        try:
            results["folder"] = client.post(
                f"/api/runs/{run_id}/receipts/folder",
                files=[(
                    "files",
                    ("dropped.jpg", folder_bytes, "application/octet-stream"),
                )],
            )
        except Exception as exc:  # noqa: BLE001 - reported by the assertions
            results["folder_error"] = repr(exc)

    threads = [
        threading.Thread(target=_do_attach, daemon=True),
        threading.Thread(target=_do_folder, daemon=True),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=JOIN_TIMEOUT_S)
        assert not t.is_alive(), f"writer never finished: {results}"

    assert "attach_error" not in results, results
    assert "folder_error" not in results, results
    assert results["attach"].status_code == 200, results["attach"].text
    assert results["folder"].status_code == 200, results["folder"].text
    job = client.get(f"/jobs/{results['folder'].json()['job_id']}").json()
    assert job["status"] == "done", job

    ids = _doc_ids(client, run_id)
    assert manual_id in ids, (
        f"the hand-attached receipt was lost by the concurrent folder ingest; "
        f"pool = {sorted(ids)}"
    )
    assert folder_id in ids, (
        f"the folder receipt was lost by the concurrent manual attach; "
        f"pool = {sorted(ids)}"
    )

    # Every receipt still sits in exactly one bucket: a commit that carried a
    # foreign receipt into the pool must carry it into the outcome too.
    outcome = _run(client, run_id).snapshot["outcome"]
    bucketed = set(outcome["unmatched_receipts"])
    for key in ("matches", "judgment_required", "ambiguous"):
        bucketed |= {m["document_id"] for m in outcome.get(key) or []}
    assert manual_id in bucketed and folder_id in bucketed, sorted(bucketed)


# ── the manual attach: no byte overwrite, and a record of the swap ──


def test_reattach_same_filename_keeps_the_replaced_bytes(client):
    """The defect verbatim: same charge, same filename, different bytes. The
    earlier receipt used to be overwritten in place with nothing kept."""
    run_id = _create_run(client)
    tx_id = _unmatched_tx(client, run_id)

    assert _attach(client, run_id, tx_id, "emailed.png", PNG_V1).status_code == 200
    assert _attach(client, run_id, tx_id, "emailed.png", PNG_V2).status_code == 200

    d = _manual_dir(client, run_id)
    current = _current_files(d)
    assert len(current) == 1, [p.name for p in current]
    assert current[0].read_bytes() == PNG_V2
    assert _archived_bytes(d) == [PNG_V1], "the replaced bytes were destroyed"


def test_reattach_records_the_replacement_on_the_snapshot(client):
    """A kept file nobody can find is not a record. The snapshot names the
    current file and every version it replaced."""
    run_id = _create_run(client)
    tx_id = _unmatched_tx(client, run_id)
    _attach(client, run_id, tx_id, "emailed.png", PNG_V1)

    # First attach: nothing was replaced, so nothing is recorded.
    assert "receipt_files" not in (_run(client, run_id).snapshot or {})

    _attach(client, run_id, tx_id, "emailed.png", PNG_V2)
    entry = _run(client, run_id).snapshot["receipt_files"][f"manual:{tx_id}"]
    assert entry["stored"].endswith("emailed.png")
    assert len(entry["superseded"]) == 1
    replaced = entry["superseded"][0]
    assert replaced["stored"].endswith("emailed.png")
    assert replaced["archived"].endswith("emailed.png")
    assert (
        _manual_dir(client, run_id) / "superseded" / replaced["archived"]
    ).read_bytes() == PNG_V1

    # A third attach accumulates rather than forgetting the second.
    _attach(client, run_id, tx_id, "emailed.png", b"\x89PNG third-version")
    entry = _run(client, run_id).snapshot["receipt_files"][f"manual:{tx_id}"]
    assert len(entry["superseded"]) == 2


def test_reattach_under_a_new_name_leaves_one_current_file(client):
    """The other half of the same defect: a re-attach under a DIFFERENT name
    left both files in the glob the image endpoint reads, and `sorted(...)[0]`
    could serve the superseded one. One current file per charge, always."""
    run_id = _create_run(client)
    tx_id = _unmatched_tx(client, run_id)
    # "a.png" sorts before "b.png", so a stale first hit would win here.
    _attach(client, run_id, tx_id, "a.png", PNG_V1)
    _attach(client, run_id, tx_id, "b.png", PNG_V2)

    d = _manual_dir(client, run_id)
    current = _current_files(d)
    assert [p.name.endswith("b.png") for p in current] == [True]
    assert _archived_bytes(d) == [PNG_V1]

    served = client.get(f"/api/runs/{run_id}/receipts/manual:{tx_id}/image")
    assert served.status_code == 200, served.text
    assert served.content == PNG_V2


def test_identical_reupload_archives_nothing(client):
    """Re-uploading the same file is not a replacement; it must not manufacture
    a version or a record."""
    run_id = _create_run(client)
    tx_id = _unmatched_tx(client, run_id)
    _attach(client, run_id, tx_id, "emailed.png", PNG_V1)
    _attach(client, run_id, tx_id, "emailed.png", PNG_V1)

    d = _manual_dir(client, run_id)
    assert len(_current_files(d)) == 1
    assert _archived_bytes(d) == []
    assert "receipt_files" not in (_run(client, run_id).snapshot or {})


# ── the queued upload: a replaced file is archived, never deleted ───


def _create_intake(client):
    resp = client.post(
        "/api/intakes", files=_files(), data={"card_name": "Corporate card 2838"}
    )
    assert resp.status_code == 200, resp.text
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        intake = store.list_intakes()[0]
    assert intake.status == INTAKE_RECEIVED
    return intake


def test_queued_upload_replacement_keeps_the_replaced_file(client):
    """A wrongly attached file needs a way out; it does not need to be
    destroyed. Pre-fix the superseded upload was unlinked from the volume with
    no copy and no record."""
    intake = _create_intake(client)
    work = Path(intake.work_dir)
    original = (work / intake.statement_name).read_bytes()

    resp = client.post(
        f"/api/intakes/{intake.intake_id}/files",
        files={"statement": ("corrected.csv", b"date,amount\n2026-04-01,1.00\n",
                             "text/csv")},
    )
    assert resp.status_code == 200, resp.text

    assert not (work / intake.statement_name).exists()  # not servable any more
    archived = sorted((work / "superseded").glob("*"))
    assert [p.read_bytes() for p in archived] == [original]
    assert archived[0].name.endswith(intake.statement_name)


def test_queued_upload_same_name_replacement_keeps_the_replaced_file(client):
    """Same name is the harder half: pre-fix `write_bytes` went straight over
    the stored bytes and the unlink branch never even ran."""
    intake = _create_intake(client)
    work = Path(intake.work_dir)
    name = intake.statement_name
    original = (work / name).read_bytes()

    resp = client.post(
        f"/api/intakes/{intake.intake_id}/files",
        files={"statement": (name, b"date,amount\n2026-04-02,2.00\n", "text/csv")},
    )
    assert resp.status_code == 200, resp.text

    assert (work / name).read_bytes() == b"date,amount\n2026-04-02,2.00\n"
    assert [p.read_bytes() for p in sorted((work / "superseded").glob("*"))] == [
        original
    ]
