"""Two leftovers of the 2026-09-24 LLM-key outage (backlog items 196/197).

1. A mail that failed to render and was later rendered and ingested kept
   the failure's `error` (the 429 text) on its intake-log row, beside the
   status `ingested`. Live: archive `20260924T162158-0f4f64aa`, the only
   row of 146 that read ingested and carried an error. Any surface that
   shows `error` showed a failure on a success.
2. A statement attach whose job died left its uploaded file in the month's
   folder. Nothing reads the folder (only `statements[]` does), so the file
   was inert, but the retry of the same file was stored as
   `20260804-statements-9693--2.pdf`: the dead attempt kept the name.

The third leftover (the overlap advisory calling two cards "the same
account") shipped with item 195.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.intake_mail import _append_log, inbound_root  # noqa: E402
from expense_recon.web.store import JOB_DONE, RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
HEADER = "Date,Amount,Vendor\n"
QUOTA = "Error code: 429 - You have no credits remaining."


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    mock = MockLLMClient(
        extraction_responses=[
            ExtractedReceipt(
                date="2026-04-15", total="42.50", currency="USD",
                vendor="Staples", reference="", line_items=(),
                confidence=0.9, notes="", payment_hint=None,
            )
        ] * 4,
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9, implied_rate=1.0,
                converted_amount=Decimal("42.50"), reasoning="same purchase",
            )
        ] * 24,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


# ── 1. the intake log ───────────────────────────────────────────────────


def _seed_mail(data_root: Path, archive: str, *, status: str, error: str) -> None:
    """One archive the way the outage left it: the log row written when the
    render failed, and the archive's meta as it reads now."""
    arch = inbound_root(data_root) / archive
    arch.mkdir(parents=True)
    (arch / "meta.json").write_text(json.dumps({
        "status": status, "error": error, "from": "criss@example.com",
        "subject": "Fatura", "rendered": True,
    }), encoding="utf-8")
    _append_log(data_root, {
        "at": "2026-09-24T16:21:58+00:00", "from": "criss@example.com",
        "subject": "Fatura", "n_files": 0, "status": "held_failed",
        "archive": archive, "error": error,
    })


def _log_rows(client) -> dict[str, dict]:
    resp = client.get("/api/inbound/log?limit=50")
    assert resp.status_code == 200, resp.text
    return {r["archive"]: r for r in resp.json()["entries"]}


def test_an_ingested_mail_shows_no_error_from_an_earlier_failed_try(client):
    _seed_mail(client._data_root, "20260924T162158-0f4f64aa",
               status="ingested", error=QUOTA)

    row = _log_rows(client)["20260924T162158-0f4f64aa"]

    assert row["status"] == "ingested"
    assert "error" not in row


def test_a_mail_still_held_keeps_its_error(client):
    """The error is the only thing that says why a held mail is held."""
    _seed_mail(client._data_root, "20260924T162158-held0001",
               status="held_failed", error=QUOTA)

    row = _log_rows(client)["20260924T162158-held0001"]

    assert row["status"] == "held_failed"
    assert row["error"] == QUOTA


def test_the_archive_keeps_the_failure_on_record(client):
    """Read-side only: the custody record still says the first try failed."""
    _seed_mail(client._data_root, "20260924T162158-0f4f64aa",
               status="ingested", error=QUOTA)
    _log_rows(client)

    meta = json.loads(
        (inbound_root(client._data_root) / "20260924T162158-0f4f64aa"
         / "meta.json").read_text(encoding="utf-8")
    )
    assert meta["error"] == QUOTA


# ── 2. a dead attach leaves no file behind ──────────────────────────────


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _batch(client, label="April 2026") -> str:
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": label},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("a.jpg", JPG, "application/octet-stream"))],
    ))
    return batch_id


def _csv(*rows: tuple[str, str, str]) -> bytes:
    return (HEADER + "".join(f"{d},{a},{v}\n" for d, a, v in rows)).encode()


GOOD = _csv(("2026-04-15", "42.50", "STAPLES"))


def _attach(client, batch_id, body: bytes, name="statement.csv") -> dict:
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (name, body, "application/octet-stream")},
        data={
            "account_id": "amex-9001",
            "account_legal_entities": '{"amex-9001": "Corporate Services"}',
            "account_card_currency": "USD",
            "map_transaction_date": "Date",
            "map_amount": "Amount",
            "map_vendor": "Vendor",
        },
    )
    assert resp.status_code == 200, resp.text
    return client.get(f"/jobs/{resp.json()['job_id']}").json()


def _stored(client, batch_id) -> tuple[Path, list[dict]]:
    with RunStore(Path(client._data_root) / "recon-web.sqlite") as store:
        run = store.get_run(batch_id)
    return Path(run.work_dir), list((run.snapshot or {}).get("statements") or [])


def test_a_failed_attach_leaves_no_file_in_the_month(client):
    batch_id = _batch(client)

    job = _attach(client, batch_id, _csv(), name="statement.csv")

    assert job["status"] == "error", job
    work_dir, statements = _stored(client, batch_id)
    assert statements == []
    assert not (work_dir / "statement.csv").exists()


def test_the_retry_of_a_failed_attach_keeps_the_file_name(client):
    """The live symptom: the retry of the 9693 PDF was stored as
    `...-9693--2.pdf` because the dead attempt still held the name."""
    batch_id = _batch(client)
    _attach(client, batch_id, _csv(), name="statement.csv")

    job = _attach(client, batch_id, GOOD, name="statement.csv")

    assert job["status"] == "done", job
    work_dir, statements = _stored(client, batch_id)
    assert [e["file"] for e in statements] == ["statement.csv"]
    assert (work_dir / "statement.csv").read_bytes() == GOOD


def test_a_job_that_fails_after_the_month_recorded_the_file_keeps_it(
    client, monkeypatch
):
    """The attach is atomic: once `statements[]` names the file, the month's
    charges point into it and the re-read reads it, so a failure AFTER that
    commit must not take it away."""
    original = RunStore.set_job_status

    def fail_on_done(self, job_id, status, **kw):
        if status == JOB_DONE:
            raise RuntimeError("lost the job row after the commit")
        return original(self, job_id, status, **kw)

    batch_id = _batch(client, label="May 2026")
    monkeypatch.setattr(RunStore, "set_job_status", fail_on_done)

    job = _attach(client, batch_id, GOOD, name="statement.csv")

    assert job["status"] == "error", job
    work_dir, statements = _stored(client, batch_id)
    assert [e["file"] for e in statements] == ["statement.csv"]
    assert (work_dir / "statement.csv").read_bytes() == GOOD
