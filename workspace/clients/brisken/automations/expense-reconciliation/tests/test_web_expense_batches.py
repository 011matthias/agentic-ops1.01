"""Receipt-first expense batches on the web layer (Phase 4).

Dirk's note #1 ("the flow is backwards"): upload receipts, get Zoho-quality
expenses with NO bank statement. The upload is its own top-level object
(POST /api/expense-batches — the decoupling from the results page), the
review surface is a receipt-spine grid (`build_expense_view`), edits overlay
at render/export time (field overrides + add/delete + the existing
line-level category overrides), and the export is the Zoho Books Expenses
import CSV. Everything sits behind EXPENSE_RECON_RECEIPT_FIRST, so a deploy
with the flag unset serves 404s and statement-mode behaviour is untouched.

OCR is injected via MockLLMClient by monkeypatching cli._build_llm_client
(generate_expenses resolves it at call time), so the tests are CI-safe with
no API key. The TestClient runs background jobs in-process, so a POST then
an immediate /jobs poll sees the batch done.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.output.zoho_expense_export import EXPENSE_COLUMNS  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"

# EXPENSE_COLUMNS indices the assertions read.
COL_DATE = EXPENSE_COLUMNS.index("Expense Date")
COL_ACCOUNT = EXPENSE_COLUMNS.index("Expense Account")
COL_AMOUNT = EXPENSE_COLUMNS.index("Expense Amount")
COL_CCY = EXPENSE_COLUMNS.index("Currency Code")
COL_VENDOR = EXPENSE_COLUMNS.index("Vendor")
COL_TAX_AMT = EXPENSE_COLUMNS.index("Tax Amount")
COL_ENTITY = EXPENSE_COLUMNS.index("Legal Entity")


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
        date="2026-07-01",
        total="42.50",
        currency="USD",
        vendor="Staples",
        reference="",
        line_items=(),
        confidence=0.9,
        notes="",
    )
    base.update(overrides)
    return ExtractedReceipt(**base)


def _patch_ocr(monkeypatch, *extractions: ExtractedReceipt) -> None:
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _create_batch(client, files=None, legal_entity="Corporate Services", **data):
    payload = [
        ("files", (n, d, "application/octet-stream"))
        for n, d in (files or [("a.jpg", JPG)])
    ]
    resp = client.post(
        "/api/expense-batches",
        files=payload,
        data={"legal_entity": legal_entity, **data},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    job = client.get(f"/jobs/{body['job_id']}").json()
    assert job["status"] == "done", job
    return body["batch_id"]


def _grid(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _export_rows(client, batch_id) -> list[list[str]]:
    resp = client.get(f"/runs/{batch_id}/expenses.csv")
    assert resp.status_code == 200, resp.text
    rows = list(csv.reader(io.StringIO(resp.text)))
    assert rows[0] == list(EXPENSE_COLUMNS)
    return rows[1:]


# ── flag off: the whole surface is invisible ────────────────────────


def test_flag_off_serves_404(tmp_path, monkeypatch):
    monkeypatch.delenv("EXPENSE_RECON_RECEIPT_FIRST", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        assert c.post("/api/expense-batches").status_code == 404
        assert c.get("/api/expense-batches").status_code == 404
        assert c.get("/api/expense-batches/x").status_code == 404
        assert c.get("/runs/x/expenses.csv").status_code == 404
        assert (
            c.put("/api/runs/x/expenses/y", json={"field": "vendor", "value": "a"})
            .status_code == 404
        )


# ── create -> OCR -> grid ───────────────────────────────────────────


def test_batch_create_ocr_and_grid(client, monkeypatch):
    _patch_ocr(
        monkeypatch,
        _extraction(vendor="Staples", total="42.50", tax="5.00", tax_label="VAT"),
        _extraction(vendor="Cafe Lisboa", total="18.00", currency="EUR",
                    date="2026-07-02"),
    )
    batch_id = _create_batch(
        client, files=[("a.jpg", JPG), ("b.jpg", JPG + b"2")]
    )

    grid = _grid(client, batch_id)
    assert grid["mode"] == "expense_generation"
    assert grid["summary"]["n_expenses"] == 2
    assert len(grid["category_options"]) == 8
    vendors = {e["vendor"]["display"] for e in grid["expenses"]}
    assert vendors == {"Staples", "Cafe Lisboa"}
    staples = next(e for e in grid["expenses"] if e["vendor"]["display"] == "Staples")
    assert staples["total"] == "42.50"
    assert staples["tax"] == "5.00"
    assert staples["tax_label"] == "VAT"
    assert staples["legal_entity_id"] == "Corporate Services"
    assert staples["review"]["state"] in ("ready", "check", "pick")
    # The batch appears in the list endpoint.
    batches = client.get("/api/expense-batches").json()["batches"]
    assert [b["batch_id"] for b in batches] == [batch_id]


def test_runs_endpoint_dispatches_by_mode(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    view = client.get(f"/api/runs/{batch_id}").json()
    assert "expenses" in view and "rows" not in view
    assert view["mode"] == "expense_generation"


def test_no_llm_and_no_key_fails_the_job_honestly(client):
    resp = client.post(
        "/api/expense-batches",
        files=[("files", ("a.jpg", JPG, "application/octet-stream"))],
        data={"legal_entity": "Corporate Services"},
    )
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "error"
    assert "llm" in (job["error"] or "").lower()


def test_batch_create_validation(client):
    # No files at all -> 400.
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "Corporate Services"}
    )
    assert resp.status_code == 400
    # Only unreadable files -> 400. (No legal entity is VALID since Cards
    # R3 — entity resolves per receipt; see test_cards_r3_entity_flow.)
    resp = client.post(
        "/api/expense-batches",
        files=[("files", ("a.txt", b"nope", "text/plain"))],
        data={"legal_entity": "Corporate Services"},
    )
    assert resp.status_code == 400


# ── field edits ─────────────────────────────────────────────────────


def test_field_edit_updates_grid_and_export(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    doc = _grid(client, batch_id)["expenses"][0]["document_id"]

    for field, value in (
        ("vendor", "Staples Inc"),
        ("total", "99.99"),
        ("currency", "eur"),
        ("date", "2026-07-15"),
        ("tax", "7.77"),
    ):
        resp = client.put(
            f"/api/runs/{batch_id}/expenses/{doc}",
            json={"field": field, "value": value},
        )
        assert resp.status_code == 200, resp.text

    row = _grid(client, batch_id)["expenses"][0]
    assert row["vendor"]["display"] == "Staples Inc"
    assert row["total"] == "99.99"
    assert row["currency"] == "EUR"
    assert row["date"] == "2026-07-15"
    assert row["tax"] == "7.77"
    assert set(row["edited_fields"]) == {"vendor", "total", "currency", "date", "tax"}

    (export_row,) = _export_rows(client, batch_id)
    assert export_row[COL_VENDOR] == "Staples Inc"
    assert export_row[COL_AMOUNT] == "99.99"
    assert export_row[COL_CCY] == "EUR"
    assert export_row[COL_DATE] == "2026-07-15"
    assert export_row[COL_TAX_AMT] == "7.77"

    # Clearing an edit reverts to the extracted value.
    resp = client.put(
        f"/api/runs/{batch_id}/expenses/{doc}",
        json={"field": "vendor", "value": None},
    )
    assert resp.status_code == 200
    assert _grid(client, batch_id)["expenses"][0]["vendor"]["display"] == "Staples"


def test_field_edit_validation(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    doc = _grid(client, batch_id)["expenses"][0]["document_id"]
    put = lambda body: client.put(  # noqa: E731
        f"/api/runs/{batch_id}/expenses/{doc}", json=body
    )
    assert put({"field": "date", "value": "07/15/2026"}).status_code == 400
    assert put({"field": "total", "value": "abc"}).status_code == 400
    assert put({"field": "currency", "value": "EURO"}).status_code == 400
    assert put({"field": "nonsense", "value": "x"}).status_code == 400
    assert put({"field": "category", "value": "Not A Category"}).status_code == 400


def test_category_edit_folds_into_overrides(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    doc = _grid(client, batch_id)["expenses"][0]["document_id"]

    resp = client.put(
        f"/api/runs/{batch_id}/expenses/{doc}",
        json={"field": "category", "value": "Office Supplies & Consumables"},
    )
    assert resp.status_code == 200, resp.text
    resp = client.put(
        f"/api/runs/{batch_id}/expenses/{doc}",
        json={"field": "zoho_account", "value": "E200010 - Office Supplies"},
    )
    assert resp.status_code == 200, resp.text

    row = _grid(client, batch_id)["expenses"][0]
    assert row["posting_category"]["category"] == "Office Supplies & Consumables"
    assert row["posting_category"]["zoho_account"] == "E200010 - Office Supplies"
    assert row["posting_category"]["source"] == "override"
    # Setting the account did NOT clear the category (merge, not clobber).
    (export_row,) = _export_rows(client, batch_id)
    assert export_row[COL_ACCOUNT] == "E200010 - Office Supplies"


# ── manual add + delete ─────────────────────────────────────────────


def test_manual_add_and_delete(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction())
    batch_id = _create_batch(client)

    resp = client.post(
        f"/api/runs/{batch_id}/expenses",
        json={
            "vendor": "Taxi Roma",
            "total": "30.00",
            "currency": "EUR",
            "date": "2026-07-03",
            "category": "Travel & Transport",
        },
    )
    assert resp.status_code == 200, resp.text
    manual_doc = resp.json()["document_id"]
    assert manual_doc.startswith("manual:")

    grid = _grid(client, batch_id)
    assert grid["summary"]["n_expenses"] == 2
    manual = next(e for e in grid["expenses"] if e["document_id"] == manual_doc)
    assert manual["is_manual"] is True
    assert manual["vendor"]["display"] == "Taxi Roma"
    assert manual["legal_entity_id"] == "Corporate Services"  # batch default
    assert manual["posting_category"]["category"] == "Travel & Transport"

    rows = _export_rows(client, batch_id)
    assert any(r[COL_VENDOR] == "Taxi Roma" and r[COL_AMOUNT] == "30.00" for r in rows)

    # Deleting the manual add removes it entirely.
    resp = client.request("DELETE", f"/api/runs/{batch_id}/expenses/{manual_doc}")
    assert resp.status_code == 200, resp.text
    grid = _grid(client, batch_id)
    assert grid["summary"]["n_expenses"] == 1
    assert all(not e["document_id"].startswith("manual:") for e in grid["expenses"])


def test_manual_add_validation(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    post = lambda body: client.post(  # noqa: E731
        f"/api/runs/{batch_id}/expenses", json=body
    )
    assert post({"vendor": "X"}).status_code == 400  # no total
    assert post({"total": "5.00"}).status_code == 400  # no vendor
    assert post({"vendor": "X", "total": "abc"}).status_code == 400
    assert post(
        {"vendor": "X", "total": "5.00", "category": "Nope"}
    ).status_code == 400


def test_delete_ocr_expense_soft_hides_it(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction(), _extraction(vendor="Cafe", total="9.00"))
    batch_id = _create_batch(client, files=[("a.jpg", JPG), ("b.jpg", JPG + b"2")])
    grid = _grid(client, batch_id)
    doc = next(e["document_id"] for e in grid["expenses"] if e["vendor"]["display"] == "Cafe")

    resp = client.request("DELETE", f"/api/runs/{batch_id}/expenses/{doc}")
    assert resp.status_code == 200, resp.text
    grid = _grid(client, batch_id)
    assert grid["summary"]["n_expenses"] == 1
    assert all(e["document_id"] != doc for e in grid["expenses"])
    assert all(r[COL_VENDOR] != "Cafe" for r in _export_rows(client, batch_id))
    # The snapshot itself is untouched (soft delete, never a rewrite).
    with RunStore(client._data_root / "recon-web.sqlite") as db:
        run = db.get_run(batch_id)
    assert len(run.snapshot["receipts"]) == 2
    # Unknown expense -> 404.
    resp = client.request("DELETE", f"/api/runs/{batch_id}/expenses/nope")
    assert resp.status_code == 404


# ── per-expense entity override ─────────────────────────────────────


def test_entity_override(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    doc = _grid(client, batch_id)["expenses"][0]["document_id"]

    resp = client.put(
        f"/api/runs/{batch_id}/expenses/{doc}/entity",
        json={"legal_entity": "Cloud Services"},
    )
    assert resp.status_code == 200, resp.text
    row = _grid(client, batch_id)["expenses"][0]
    assert row["legal_entity_id"] == "Cloud Services"
    (export_row,) = _export_rows(client, batch_id)
    assert export_row[COL_ENTITY] == "Cloud Services"
    # Blank entity -> 400.
    resp = client.put(
        f"/api/runs/{batch_id}/expenses/{doc}/entity", json={"legal_entity": ""}
    )
    assert resp.status_code == 400


# ── review-by-exception ─────────────────────────────────────────────


def test_missing_fields_flag_review_check(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction(date=None, total=None, currency=None))
    batch_id = _create_batch(client)
    row = _grid(client, batch_id)["expenses"][0]
    assert row["review"]["state"] == "check"
    assert row["review"]["reason_code"] == "missing_fields"


# ── receipt image serving ───────────────────────────────────────────


def test_expense_receipt_image_serves(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    row = _grid(client, batch_id)["expenses"][0]
    assert row["receipt_image_available"] is True
    img = client.get(f"/api/runs/{batch_id}/receipts/{row['document_id']}/image")
    assert img.status_code == 200, img.text
    assert img.content == JPG
    # A crafted id cannot escape the receipts dir.
    esc = client.get(f"/api/runs/{batch_id}/receipts/../recon-web.sqlite/image")
    assert esc.status_code in (404, 400)


# ── statement-mode isolation ────────────────────────────────────────


def _create_statement_run(client) -> str:
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
        data={
            "account_id": "amex-9001",
            "account_card_currency": "USD",
            "receipts_source": "csv",
        },
    )
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job["run_id"]


def test_statement_runs_stay_untouched(client):
    run_id = _create_statement_run(client)
    view = client.get(f"/api/runs/{run_id}").json()
    assert "rows" in view and "expenses" not in view
    # Expense endpoints refuse a statement run.
    resp = client.put(
        f"/api/runs/{run_id}/expenses/rcpt-001",
        json={"field": "vendor", "value": "x"},
    )
    assert resp.status_code == 400
    assert client.get(f"/runs/{run_id}/expenses.csv").status_code == 400
    assert client.get(f"/api/expense-batches/{run_id}").status_code == 400
    # And a statement run never shows in the batch list.
    assert client.get("/api/expense-batches").json()["batches"] == []


# ── store: delete_run purges the new tables ─────────────────────────


def test_delete_run_purges_expense_tables(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    doc = _grid(client, batch_id)["expenses"][0]["document_id"]
    client.put(
        f"/api/runs/{batch_id}/expenses/{doc}",
        json={"field": "vendor", "value": "Edited"},
    )
    client.post(
        f"/api/runs/{batch_id}/expenses",
        json={"vendor": "Manual", "total": "1.00"},
    )
    db_path = client._data_root / "recon-web.sqlite"
    with RunStore(db_path) as db:
        assert db.get_expense_field_overrides(batch_id)
        assert db.get_expense_edits(batch_id)
    assert client.post(
        f"/api/runs/{batch_id}/delete", json={"confirm": batch_id}
    ).status_code == 200
    with RunStore(db_path) as db:
        assert db.get_expense_field_overrides(batch_id) == {}
        assert db.get_expense_edits(batch_id) == []


# ---------------- language + receipt visibility round (notes 4/8) --------

def test_manual_add_has_honest_receipt_state(client, monkeypatch):
    """Note 8: a manual expense with no file must not render a View
    button that 404s. File-backed rows keep availability and gain their
    source_file identity."""
    _patch_ocr(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    resp = client.post(
        f"/api/runs/{batch_id}/expenses",
        json={"vendor": "Cash Kiosk", "total": "5.00", "currency": "EUR",
              "date": "2026-07-04", "category": "Travel & Transport"},
    )
    assert resp.status_code == 200, resp.text
    manual_doc = resp.json()["document_id"]

    rows = {e["document_id"]: e for e in _grid(client, batch_id)["expenses"]}
    manual = rows[manual_doc]
    assert manual["receipt_image_available"] is False  # pre-fix: True
    assert manual["source_file"] == ""
    uploaded = next(e for e in rows.values() if e["document_id"] != manual_doc)
    assert uploaded["receipt_image_available"] is True
    assert uploaded["source_file"]  # which upload the row came from


def test_missing_fields_review_is_structured(client, monkeypatch):
    """Note 4: the missing-field LIST rides as data so the SPA composes
    the sentence from its own localized field names."""
    _patch_ocr(monkeypatch, _extraction(date=None, total=None))
    batch_id = _create_batch(client)
    row = _grid(client, batch_id)["expenses"][0]
    assert row["review"]["reason_code"] == "missing_fields"
    assert row["review"]["missing"] == ["date", "amount"]


def test_books_as_uncategorized_is_a_sentinel(client, monkeypatch):
    """Note 4: the grid never shows the export's English placeholder;
    the SPA maps {account: null, unassigned: true} to its own wording."""
    _patch_ocr(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    resp = client.post(
        f"/api/runs/{batch_id}/expenses",
        json={"vendor": "Mystery Vendor", "total": "9.99",
              "currency": "EUR", "date": "2026-07-05"},
    )
    assert resp.status_code == 200, resp.text
    doc = resp.json()["document_id"]
    row = {e["document_id"]: e for e in
           _grid(client, batch_id)["expenses"]}[doc]
    assert row["books_as"] == [
        {"account": None, "unassigned": True, "amount": "9.99"}
    ]
    assert "(uncategorized" not in str(row["books_as"])


def test_attached_manual_receipt_keeps_view_button(client, monkeypatch):
    """Review carry: a workbench-attached manual receipt (file under
    manual-receipts/, id manual:{tx}) keeps availability — the honest
    rule must not wrongly hide real documents on a graduated batch."""
    from pathlib import Path

    from expense_recon.web.store import RunStore

    _patch_ocr(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    resp = client.post(
        f"/api/runs/{batch_id}/expenses",
        json={"vendor": "Attached Later", "total": "7.00",
              "currency": "EUR", "date": "2026-07-06",
              "category": "Travel & Transport"},
    )
    manual_doc = resp.json()["document_id"]
    tx_key = manual_doc[len("manual:"):]

    with RunStore(client._data_root / "recon-web.sqlite") as store:
        work_dir = Path(store.get_run(batch_id).work_dir)
    folder = work_dir / "manual-receipts"
    folder.mkdir(exist_ok=True)
    (folder / f"{tx_key}__hotel-bill.jpg").write_bytes(JPG)

    row = {e["document_id"]: e for e in
           _grid(client, batch_id)["expenses"]}[manual_doc]
    assert row["receipt_image_available"] is True
    assert row["source_file"] == "hotel-bill.jpg"
