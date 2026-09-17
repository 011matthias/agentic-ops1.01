"""Item 114 (audit draft #112): a restart mid-drop.

`POST /api/receipts` writes the dropped files to the volume
(`drops/<job>`) before its background job reads them. Before this item a
restart killed the job, the boot sweep told the page "run it again", and the
files sat in that folder for good: nothing re-ran or removed them, and the
operator's month pick lived only in the dead thread. Pinned here, through
the real route and the real boot path (`create_app` again on the same data
root is the restart):

1. An interrupted drop runs again at boot under its own job id, with the
   month the operator picked, and leaves nothing behind.
2. Files that landed before the kill are skipped by content, not doubled.
3. A drop resumed once and cut off again is given up, not re-run forever.
4. A folder with no interrupted job, and a month's `drop-add-*` copy, are
   deleted at boot; a finished drop leaves no sidecar.

The month-deletion half of the audit item is not built: its reviewer
corrections refute it (the operator keeps the originals, and deletion needs
the typed month label).
"""
from __future__ import annotations

import calendar
import time
from datetime import date, timedelta

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

import expense_recon.web.app as app_mod  # noqa: E402
from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0" + b"x" * 5000

DAY_M1 = date.today().replace(day=1) - timedelta(days=20)
DAY_M2 = date.today().replace(day=1) - timedelta(days=50)
MONTH_M2 = f"{DAY_M2.year:04d}-{DAY_M2.month:02d}"
LABEL_M1 = f"{calendar.month_name[DAY_M1.month]} {DAY_M1.year}"
LABEL_M2 = f"{calendar.month_name[DAY_M2.month]} {DAY_M2.year}"

REAL_RUNNER = app_mod._run_receipts_drop_job


def _killed_runner(*_args, **_kwargs) -> None:
    """Stands in for a job thread the restart killed: nothing ran, so the
    job row stays `running` and the folder stays on the volume."""


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def _extraction(day: date, vendor="Staples", total="42.50") -> ExtractedReceipt:
    return ExtractedReceipt(
        date=day.isoformat(), total=total, currency="EUR", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
    )


def _patch_ocr(monkeypatch, *extractions: ExtractedReceipt) -> None:
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _post_drop(client, files, month: str | None = None) -> str:
    resp = client.post(
        "/api/receipts",
        files=[("files", (n, b, "application/octet-stream")) for n, b in files],
        data={"month": month} if month else {},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["job_id"]


def _wait(client, job_id: str, timeout: float = 60.0) -> dict:
    deadline = time.monotonic() + timeout
    while True:
        job = client.get(f"/jobs/{job_id}").json()
        if job.get("status") != "running" or time.monotonic() > deadline:
            return job
        time.sleep(0.05)


def _batches(client) -> list[dict]:
    body = client.get("/api/expense-batches").json()
    return body["batches"] if isinstance(body, dict) else body


def _drop_leftovers(root) -> list[str]:
    drops = root / "drops"
    return sorted(p.name for p in drops.iterdir()) if drops.is_dir() else []


def test_restart_mid_drop_runs_it_again_with_the_month_pick(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(app_mod, "_run_receipts_drop_job", _killed_runner)
    with TestClient(create_app(tmp_path)) as c:
        job_id = _post_drop(
            c, [("a.jpg", JPG), ("b.jpg", JPG + b"2")], month=MONTH_M2,
        )
        assert c.get(f"/jobs/{job_id}").json()["status"] == "running"
    assert _drop_leftovers(tmp_path) == [job_id, f"{job_id}.json"]

    # The restart: the real runner, and vision answers for the ingest only
    # (a month pick skips the date pass).
    monkeypatch.setattr(app_mod, "_run_receipts_drop_job", REAL_RUNNER)
    # Two different purchases, or the month rules the second a copy.
    _patch_ocr(
        monkeypatch,
        _extraction(DAY_M1),
        _extraction(DAY_M1, vendor="Rewe", total="17.30"),
    )
    with TestClient(create_app(tmp_path)) as c:
        job = _wait(c, job_id)
        assert job["status"] == "done", job
        assert job["error"] is None
        result = job["result"]
        assert result["n_filed"] == 2, result
        assert {r["month"] for r in result["files"]} == {MONTH_M2}
        assert {r["month_source"] for r in result["files"]} == {"operator"}
        batches = _batches(c)
        assert [b["label"] for b in batches] == [LABEL_M2]
        assert batches[0]["summary"]["n_expenses"] == 2
    assert _drop_leftovers(tmp_path) == []


def test_files_that_landed_before_the_kill_are_not_doubled(
    tmp_path, monkeypatch
):
    _patch_ocr(
        monkeypatch,
        _extraction(DAY_M1), _extraction(DAY_M1),  # first drop: read + ingest
        _extraction(DAY_M1), _extraction(DAY_M1),  # resumed: read a, read b
        _extraction(DAY_M1, vendor="Rewe", total="17.30"),  # ingest b only
    )
    with TestClient(create_app(tmp_path)) as c:
        first = _post_drop(c, [("a.jpg", JPG)])
        assert _wait(c, first)["status"] == "done"
        monkeypatch.setattr(app_mod, "_run_receipts_drop_job", _killed_runner)
        job_id = _post_drop(c, [("a.jpg", JPG), ("b.jpg", JPG + b"2")])

    monkeypatch.setattr(app_mod, "_run_receipts_drop_job", REAL_RUNNER)
    with TestClient(create_app(tmp_path)) as c:
        job = _wait(c, job_id)
        assert job["status"] == "done", job
        entry = job["result"]["months"][0]
        assert entry["created_batch"] is False
        assert entry["n_added"] == 1  # a.jpg landed before the kill
        batches = _batches(c)
        assert [b["label"] for b in batches] == [LABEL_M1]
        assert batches[0]["summary"]["n_expenses"] == 2
    assert _drop_leftovers(tmp_path) == []


def test_a_drop_cut_off_again_after_resuming_is_given_up(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(app_mod, "_run_receipts_drop_job", _killed_runner)
    with TestClient(create_app(tmp_path)) as c:
        job_id = _post_drop(c, [("a.jpg", JPG)], month=MONTH_M2)
    # First restart resumes it, and that run is killed too.
    with TestClient(create_app(tmp_path)) as c:
        job = c.get(f"/jobs/{job_id}").json()
        assert job["status"] == "running"
        assert job["stage"] == "resuming after a server restart"
    assert _drop_leftovers(tmp_path) == [job_id, f"{job_id}.json"]

    # Second restart: no third attempt.
    monkeypatch.setattr(app_mod, "_run_receipts_drop_job", REAL_RUNNER)
    _patch_ocr(monkeypatch, _extraction(DAY_M1))
    with TestClient(create_app(tmp_path)) as c:
        job = c.get(f"/jobs/{job_id}").json()
        assert job["status"] == "error", job
        assert "drop the files again" in job["error"]
        assert _batches(c) == []
    assert _drop_leftovers(tmp_path) == []


def test_boot_deletes_leftovers_that_have_no_interrupted_drop(
    tmp_path, monkeypatch
):
    _patch_ocr(monkeypatch)
    with TestClient(create_app(tmp_path)) as c:
        created = c.post(
            "/api/expense-batches",
            data={"legal_entity": "Corporate Services", "label": LABEL_M1},
        ).json()
        assert _wait(c, created["job_id"])["status"] == "done"
    with RunStore(tmp_path / "recon-web.sqlite") as store:
        work = store.get_run(created["batch_id"]).work_dir
    stale_copy = type(tmp_path)(work) / "drop-add-deadbeef"
    stale_copy.mkdir(parents=True)
    (stale_copy / "0000__a.jpg").write_bytes(JPG)
    orphan = tmp_path / "drops" / "nojob000000"
    orphan.mkdir(parents=True)
    (orphan / "0000__a.jpg").write_bytes(JPG)

    with TestClient(create_app(tmp_path)) as c:
        assert [b["label"] for b in _batches(c)] == [LABEL_M1]
    assert not stale_copy.exists()
    assert _drop_leftovers(tmp_path) == []


def test_a_finished_drop_leaves_no_sidecar(tmp_path, monkeypatch):
    _patch_ocr(monkeypatch, _extraction(DAY_M1))
    with TestClient(create_app(tmp_path)) as c:
        job_id = _post_drop(c, [("a.jpg", JPG)], month=MONTH_M2)
        assert _wait(c, job_id)["status"] == "done"
    assert _drop_leftovers(tmp_path) == []
