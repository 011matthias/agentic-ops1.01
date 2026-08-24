"""The extraction baseline survives the bake (living month, PR 2b-2 prereq).

`rematch_month` BAKES the reviewer's corrections into the receipt pool the
matcher sees, then commits that pool as the run's snapshot. The snapshot is
also the audit baseline: `_expense_view` reads it to show the ORIGINAL
extracted value as the vendor object's `raw` ("always kept for audit"), and
`apply_expense_edits` composes the grid by laying the overlay ON TOP of it.

So the bake overwrote the very thing both promises rest on. Measured on
2026-08-25 against a batch whose reviewer corrected vendor and total:

    pre-bake   snapshot {'vendor': 'OriginalVendor', 'total': '42.50'}
               view.raw 'OriginalVendor'
    post-bake  snapshot {'vendor': 'EDITED-BY-REVIEWER', 'total': '99.99'}
               view.raw 'EDITED-BY-REVIEWER'      <- the audit value lies
    clear the override -> still 'EDITED-BY-REVIEWER'  <- revert is a no-op,
        against store.set_expense_field_override's documented "the expense
        reverts to its extracted value"

Once a month is living this stops being a month-end event: a re-match runs on
every receipt arrival, so the erasure happens continuously and the OCR truth
for a corrected row is gone minutes after the correction.

These tests drive the real HTTP routes, not the helper, so a baseline that is
written but not read fails them.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
DOC_ID = "0000__a.jpg"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _wire(monkeypatch, mock):
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _extraction(vendor="OriginalVendor", total="42.50"):
    return ExtractedReceipt(
        date="2026-04-15", total=total, currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
    )


def _create_batch(client):
    resp = client.post(
        "/api/expense-batches",
        files=[("files", ("a.jpg", JPG, "application/octet-stream"))],
        data={"legal_entity": "Corporate Services"},
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return resp.json()["batch_id"]


def _attach(client, batch_id):
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "statement.example.csv",
            (EXAMPLES / "statement.example.csv").read_bytes(), "text/csv",
        )},
        data={
            "account_id": "amex-9001",
            "account_legal_entities": '{"amex-9001": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    )
    assert resp.status_code == 200, resp.text
    job_id = resp.json().get("job_id")
    if job_id:
        assert client.get(f"/jobs/{job_id}").json()["status"] == "done"


def _row(client, batch_id, doc_id=DOC_ID):
    view = client.get(f"/api/expense-batches/{batch_id}").json()
    rows = view.get("expenses") or view.get("receipts") or []
    return next((r for r in rows if r.get("document_id") == doc_id), None)


def _edit(client, batch_id, field, value, doc_id=DOC_ID):
    resp = client.put(
        f"/api/runs/{batch_id}/expenses/{doc_id}",
        json={"field": field, "value": value},
    )
    assert resp.status_code == 200, resp.text


def _store(client):
    return RunStore(Path(client._data_root) / "recon-web.sqlite")


def test_raw_still_shows_the_extracted_vendor_after_the_bake(client, monkeypatch):
    """The vendor object's `raw` is documented as the ORIGINAL extracted
    name, always kept for audit. The bake used to overwrite it with the
    reviewer's own edit, so the audit field echoed the edit it existed to
    distinguish."""
    _wire(monkeypatch, MockLLMClient(extraction_responses=[_extraction()]))
    batch_id = _create_batch(client)

    _edit(client, batch_id, "vendor", "EDITED-BY-REVIEWER")
    assert _row(client, batch_id)["vendor"]["raw"] == "OriginalVendor"

    _attach(client, batch_id)

    vendor = _row(client, batch_id)["vendor"]
    assert vendor["display"] == "EDITED-BY-REVIEWER"
    assert vendor["source"] == "override"
    assert vendor["raw"] == "OriginalVendor", (
        "the bake overwrote the audit baseline: `raw` is echoing the "
        "reviewer's edit instead of what the OCR read"
    )


def test_clearing_an_edit_reverts_to_the_extracted_value_after_the_bake(
    client, monkeypatch
):
    """`set_expense_field_override(value=None)` documents "the expense
    reverts to its extracted value". Post-bake the extracted value was gone,
    so clearing an edit silently did nothing -- a control that discards what
    the reviewer does, the same class as the dead Settings editor."""
    _wire(monkeypatch, MockLLMClient(extraction_responses=[_extraction()]))
    batch_id = _create_batch(client)

    _edit(client, batch_id, "vendor", "EDITED-BY-REVIEWER")
    _attach(client, batch_id)

    with _store(client) as store:
        store.set_expense_field_override(
            batch_id, DOC_ID, "vendor", None, "2026-08-25T00:00:00Z"
        )

    vendor = _row(client, batch_id)["vendor"]
    assert vendor["display"] == "OriginalVendor", (
        "clearing the edit did not restore the extracted vendor"
    )
    assert vendor["source"] == "extraction"


def test_a_corrected_total_can_still_be_reverted_after_the_bake(
    client, monkeypatch
):
    """The money case, which the backlog's ranking rule puts first. A
    reviewer who corrects a total and then wants the OCR figure back must
    be able to get it; post-bake the original was unrecoverable."""
    _wire(monkeypatch, MockLLMClient(extraction_responses=[_extraction()]))
    batch_id = _create_batch(client)

    _edit(client, batch_id, "total", "99.99")
    _attach(client, batch_id)
    assert _row(client, batch_id)["total"] == "99.99"

    with _store(client) as store:
        store.set_expense_field_override(
            batch_id, DOC_ID, "total", None, "2026-08-25T00:00:00Z"
        )

    assert _row(client, batch_id)["total"] == "42.50", (
        "the extracted total was destroyed by the bake"
    )


def test_the_baseline_is_written_once_and_never_re_baked(client, monkeypatch):
    """First write wins per document. A second re-match reads an ALREADY
    baked snapshot, so if the baseline were refreshed each time it would
    capture the baked values and lose the truth it exists to hold."""
    _wire(monkeypatch, MockLLMClient(extraction_responses=[_extraction()]))
    batch_id = _create_batch(client)

    _edit(client, batch_id, "vendor", "FIRST-EDIT")
    _attach(client, batch_id)

    with _store(client) as store:
        run = store.get_run(batch_id)
        baseline = (run.snapshot or {}).get("extracted_receipts") or []
        assert baseline, "no extraction baseline was persisted by the bake"
        first = {r["document_id"]: r.get("detected_vendor") for r in baseline}
        assert first[DOC_ID] == "OriginalVendor"

        # Simulate a later re-match committing over the baked snapshot.
        from expense_recon.web.service import rematch_month
        from expense_recon.web.serialize import snapshot_from_dict

        txs, _, _, _ = snapshot_from_dict(run.snapshot)
        rematch_month(
            store, run, transactions=txs, cfg=run.config or {},
            entity="Corporate Services",
        )
        run2 = store.get_run(batch_id)
        again = {
            r["document_id"]: r.get("detected_vendor")
            for r in (run2.snapshot or {}).get("extracted_receipts") or []
        }

    assert again[DOC_ID] == "OriginalVendor", (
        "the second re-match re-captured the baseline from the baked pool"
    )


# NOT tested here, deliberately: that a receipt arriving AFTER a bake joins
# the baseline. `_extended_baseline` grows per document to make that work, but
# no caller can reach the state today -- `add_receipts_to_expense_batch` and
# `POST .../receipts` both still refuse a statement-bearing month. The test
# belongs with the guard lift that makes it drivable end to end, rather than
# being faked here by injecting a receipt the app could not have added.
