"""Batch lifecycle (owner directive 2026-07-28): receipts arrive gradually,
the statement only at month end.

An expense batch is the month's container: receipts get ADDED to it over
time (`POST /api/expense-batches/{id}/receipts`, content-dedup'd,
memory-consulted, OCR'd incrementally), and attaching the bank statement
later (`POST /api/expense-batches/{id}/statement` — the FIRST place the
card/account id is asked) graduates the SAME run into a reconciliation:
the reviewer's edits are baked into the receipt pool, the statement is
matched against it with the same primitives `reconcile()` uses, and from
then on GET /api/runs/{id} serves the normal workbench while the expense
grid stays readable and the expense-edit overlay freezes.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(
        date="2026-04-15", total="42.50", currency="USD", vendor="Staples",
        reference="", line_items=(), confidence=0.9, notes="",
    )
    base.update(overrides)
    return ExtractedReceipt(**base)


def _patch_ocr(monkeypatch, *extractions: ExtractedReceipt) -> None:
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _create_batch(client, files=None, legal_entity="Corporate Services"):
    resp = client.post(
        "/api/expense-batches",
        files=[
            ("files", (n, d, "application/octet-stream"))
            for n, d in (files or [("a.jpg", JPG)])
        ],
        data={"legal_entity": legal_entity},
    )
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return resp.json()["batch_id"]


def _grid(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _attach_statement(client, batch_id, entity_map='{"amex-9001": "Corporate Services"}'):
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={
            "statement": (
                "statement.example.csv",
                (EXAMPLES / "statement.example.csv").read_bytes(),
                "text/csv",
            ),
        },
        data={
            "account_id": "amex-9001",
            "account_legal_entities": entity_map,
            "account_card_currency": "USD",
        },
    )
    return resp


# ── incremental receipt adds ────────────────────────────────────────


class _DecimalTracker:
    """The real CostTracker's shape: `total_cost_usd` is a Decimal. The
    2026-07-28 live run died at 'saving' because the ingest summary put it
    straight into json.dumps; MockLLM's tracker-less default hid it."""

    call_count = 1

    @property
    def total_cost_usd(self):
        from decimal import Decimal

        return Decimal("0.0123")


def test_add_receipts_with_real_shaped_tracker_serializes(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    mock = MockLLMClient(
        extraction_responses=[_extraction(vendor="Cafe", total="9.00")]
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client",
        lambda cfg: (mock, _DecimalTracker()),
    )
    resp = client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("cafe.jpg", JPG + b"2", "application/octet-stream"))],
    )
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job  # Decimal cost must not kill 'saving'
    assert _grid(client, batch_id)["expense_ingest"]["cost_usd"] == 0.0123


def test_folder_ingest_with_real_shaped_tracker_serializes(client, monkeypatch):
    # Same latent bug existed in the statement-run folder ingest; cover it.
    mock = MockLLMClient(extraction_responses=[_extraction()])
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client",
        lambda cfg: (mock, _DecimalTracker()),
    )
    resp = client.post(
        "/api/runs",
        files={
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
        },
        data={"account_id": "amex-9001", "receipts_source": "csv"},
    )
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    run_id = job["run_id"]
    resp = client.post(
        f"/api/runs/{run_id}/receipts/folder",
        files=[("files", ("a.jpg", JPG, "application/octet-stream"))],
    )
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    assert client.get(f"/api/runs/{run_id}").status_code == 200


def test_add_receipts_appends_and_dedupes(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction())
    batch_id = _create_batch(client)

    # Add two files: one is byte-identical to the stored receipt (skipped),
    # one is genuinely new (OCR'd + appended).
    _patch_ocr(monkeypatch, _extraction(vendor="Cafe Lisboa", total="18.00"))
    resp = client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[
            ("files", ("same-bytes.jpg", JPG, "application/octet-stream")),
            ("files", ("cafe.jpg", JPG + b"2", "application/octet-stream")),
        ],
    )
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job

    grid = _grid(client, batch_id)
    assert grid["summary"]["n_expenses"] == 2
    assert grid["expense_ingest"]["n_added"] == 1  # duplicate bytes skipped
    vendors = {e["vendor"] for e in grid["expenses"]}
    assert vendors == {"Staples", "Cafe Lisboa"}
    # The added receipt's image serves like any other.
    cafe = next(e for e in grid["expenses"] if e["vendor"] == "Cafe Lisboa")
    img = client.get(
        f"/api/runs/{batch_id}/receipts/{cafe['document_id']}/image"
    )
    assert img.status_code == 200
    assert img.content == JPG + b"2"
    # The batch list reflects the new count and the pre-statement state.
    (row,) = client.get("/api/expense-batches").json()["batches"]
    assert row["summary"]["n_expenses"] == 2
    assert row["has_statement"] is False


# ── graduation: statement attach ────────────────────────────────────


def test_statement_attach_graduates_batch(client, monkeypatch):
    # Receipt matching one real statement charge exactly (STAPLES NYC,
    # 42.50, 2026-04-15 in examples/statement.example.csv).
    _patch_ocr(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    doc = _grid(client, batch_id)["expenses"][0]["document_id"]

    # Reviewer edits BEFORE the statement: a tax fix and a manual expense.
    # Both must be baked into the pool the matcher sees.
    assert client.put(
        f"/api/runs/{batch_id}/expenses/{doc}",
        json={"field": "tax", "value": "5.00"},
    ).status_code == 200
    assert client.post(
        f"/api/runs/{batch_id}/expenses",
        json={"vendor": "Taxi Roma", "total": "30.00", "currency": "EUR"},
    ).status_code == 200

    resp = _attach_statement(client, batch_id)
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job

    # GET /api/runs/{id} now serves the WORKBENCH (transaction spine).
    view = client.get(f"/api/runs/{batch_id}").json()
    assert "rows" in view and "expenses" not in view
    assert view["summary"]["invariant_ok"] is True
    staples = next(r for r in view["rows"] if "STAPLES" in r["vendor"])
    assert staples["effective_bucket"] == "reconciled"
    assert staples["chosen_document_id"] == doc
    # Baked reviewer truth: the matched receipt carries the tax edit, and
    # the manual expense sits in the pool (unmatched — no charge for it).
    chosen = next(c for c in staples["candidates"] if c["is_chosen"])
    assert chosen["receipt"]["document_id"] == doc
    unmatched_docs = {r["document_id"] for r in view["unmatched_receipts"]}
    assert any(d.startswith("manual:") for d in unmatched_docs)

    # The expense grid stays readable and reports the attached state.
    grid = _grid(client, batch_id)
    assert grid["has_statement"] is True
    assert grid["summary"]["n_expenses"] == 2
    (row,) = client.get("/api/expense-batches").json()["batches"]
    assert row["has_statement"] is True
    assert row["summary"]["n_transactions"] == 5

    # Statement-mode surfaces work on the graduated run.
    assert client.get(f"/runs/{batch_id}/zoho.csv").status_code == 200
    resp = client.post(
        f"/api/runs/{batch_id}/decisions",
        json={
            "transaction_id": staples["transaction_id"],
            "status": "confirmed",
            "chosen_document_id": doc,
        },
    )
    assert resp.status_code == 200

    # The expense-edit overlay is frozen: pool = reconciliation provenance.
    frozen = client.put(
        f"/api/runs/{batch_id}/expenses/{doc}",
        json={"field": "vendor", "value": "X"},
    )
    assert frozen.status_code == 400
    assert "workbench" in frozen.json()["error"]
    assert client.post(
        f"/api/runs/{batch_id}/expenses", json={"vendor": "Y", "total": "1"}
    ).status_code == 400
    assert client.request(
        "DELETE", f"/api/runs/{batch_id}/expenses/{doc}"
    ).status_code == 400
    assert client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("late.jpg", JPG + b"9", "application/octet-stream"))],
    ).status_code == 400
    # And a second statement is refused.
    assert _attach_statement(client, batch_id).status_code == 400


def test_statement_attach_unmappable_csv_is_sync_400(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": ("junk.csv", b"foo,bar\n1,2\n", "text/csv")},
        data={"account_id": "amex-9001"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert "column" in body["error"].lower()
    assert body.get("headers")  # the file's real headers, for the re-prompt


def test_statement_attach_entity_mismatch_warns(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction())
    batch_id = _create_batch(client)  # batch entity: Corporate Services
    resp = _attach_statement(
        client, batch_id, entity_map='{"amex-9001": "Other LLC"}'
    )
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    # Cross-entity => nothing can match; the warning is loud, not silent.
    assert "warning" in (job["stage"] or "")
    view = client.get(f"/api/runs/{batch_id}").json()
    assert view["summary"]["n_reconciled"] == 0
