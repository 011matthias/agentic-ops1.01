"""Item 115: corrections are stored AND recalled.

Three holes, each driven through the caller that actually runs in a live
month, never through the helper alone:

* a receipt with readable line items used to take the model's line read and
  never consult memory, so a merchant Criss had corrected came back as the
  model's guess every month (`POST /api/expense-batches/{id}/receipts`);
* the lookup needed the receipt's company and a month's corrections are
  saved under the company each expense carried, which for most live rows is
  none, so the rules reached no row at all;
* only the statement-mode sign-off taught vendor spellings and exchange
  rates, and every live month is receipt-first WITH a statement, so
  publishing taught the matcher nothing (`POST /api/runs/{id}/publish`).

Plus the invariant none of it may break: a category the reviewer chose is
never overwritten by a remembered one.
"""
from __future__ import annotations

import io
from datetime import datetime

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedLineItem,
    ExtractedReceipt,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _chair_receipt(vendor="Contoso Hardware", date="2026-07-02", total="120.00"):
    """A receipt whose ONE line reads as Equipment & Hardware to the model."""
    return ExtractedReceipt(
        date=date, total=total, currency="USD", vendor=vendor, reference="",
        line_items=(ExtractedLineItem(description="Office chair", line_total=total),),
        confidence=0.9, notes="",
    )


def _wire(monkeypatch, *extractions):
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    return mock


def _month(client, monkeypatch, *extractions, entity="Corporate Services",
           label="July 2026", name="a.jpg", data=JPG):
    _wire(monkeypatch, *extractions)
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": entity, "label": label}
    )
    _done(client, resp)
    batch = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch}/receipts",
        files=[("files", (name, data, "application/octet-stream"))],
    ))
    return batch


def _add(client, monkeypatch, batch, *extractions, name="b.jpg", data=JPG + b"x"):
    _wire(monkeypatch, *extractions)
    _done(client, client.post(
        f"/api/expense-batches/{batch}/receipts",
        files=[("files", (name, data, "application/octet-stream"))],
    ))


def _rows(client, batch):
    return client.get(f"/api/expense-batches/{batch}").json()["expenses"]


def _row(client, batch, vendor):
    return next(r for r in _rows(client, batch) if vendor in r["vendor"]["display"])


def _row_by_doc(client, batch, doc):
    return next(r for r in _rows(client, batch) if r["document_id"] == doc)


def _set_category(client, batch, doc, category):
    resp = client.put(
        f"/api/runs/{batch}/expenses/{doc}",
        json={"field": "category", "value": category},
    )
    assert resp.status_code == 200, resp.text


def _publish(client, batch) -> dict:
    resp = client.post(f"/api/runs/{batch}/publish", json={"override": True})
    assert resp.status_code == 200, resp.text
    return resp.json()["memory"]


def _memory(client) -> dict:
    return client.get("/api/memory").json()


# ── hole 1: a receipt with line items now consults memory ───────────────


def test_a_corrected_category_arrives_on_next_months_receipt(client, monkeypatch):
    july = _month(client, monkeypatch, _chair_receipt())
    row = _row(client, july, "Contoso")
    assert row["posting_category"]["category"] == "Equipment & Hardware"
    assert row["posting_category"]["source"] == "llm"
    _set_category(client, july, row["document_id"], "Office Supplies & Consumables")
    assert _publish(client, july)["saved"] is True

    august = _month(
        client, monkeypatch, _chair_receipt(date="2026-08-02"),
        label="August 2026", name="aug.jpg", data=JPG + b"aug",
    )
    row = _row(client, august, "Contoso")
    # The correction arrives pre-filled. Since note item M1 (2026-09-18) the
    # sign-off's registry upsert makes it the MERCHANT'S default, so the
    # row reads it from the registry with no glance: one merchant, one
    # category, is the rule the owner stated. The glance stays on a rule
    # that reaches a merchant with no default (next test).
    assert row["posting_category"]["category"] == "Office Supplies & Consumables"
    assert row["posting_category"]["source"] == "registry"
    assert row["review"]["reason_code"] != "vendor_guess"


def test_a_memory_page_rule_on_a_merchant_with_no_default_asks_for_a_glance(
    client, monkeypatch
):
    # A rule a person taught on the Memory page, for a merchant the registry
    # has no default for: item 115's behaviour, unchanged by M1. The rule
    # fills the row, and because the receipt's own items read something
    # else the row asks for one glance rather than claiming certainty. Same
    # reason code (and so the same sentence and the same Keep button) as a
    # vendor-name guess.
    resp = client.put("/api/memory/categories", json={
        "legal_entity_id": "Corporate Services", "vendor": "Contoso Hardware",
        "category": "Office Supplies & Consumables",
    })
    assert resp.status_code == 200, resp.text
    assert client.get("/api/settings").json()["merchants"] == {}

    august = _month(
        client, monkeypatch, _chair_receipt(date="2026-08-02"),
        label="August 2026", name="aug.jpg", data=JPG + b"aug",
    )
    row = _row(client, august, "Contoso")
    assert row["posting_category"]["category"] == "Office Supplies & Consumables"
    assert row["posting_category"]["source"] == "learned"
    assert row["review"]["state"] == "check"
    assert row["review"]["reason_code"] == "vendor_guess"


def test_a_seeded_rule_does_not_displace_the_line_read(client, monkeypatch):
    # The Zoho seed is how the books posted, not a decision about this
    # merchant, and no live row is validated: it still fills a receipt with
    # no readable items and stays below one that has them (item 115, left
    # for the owner's ruling).
    july = _month(client, monkeypatch, _chair_receipt())
    doc = _row(client, july, "Contoso")["document_id"]
    resp = client.put("/api/memory/categories", json={
        "legal_entity_id": "Corporate Services", "vendor": "Contoso Hardware",
        "category": "Marketing & Advertising",
    })
    assert resp.status_code == 200, resp.text
    _seed_source(client, "Corporate Services", "contoso hardware")

    _add(client, monkeypatch, july, _chair_receipt(date="2026-07-09"))
    fresh = [r for r in _rows(client, july) if r["document_id"] != doc]
    assert fresh[0]["posting_category"]["category"] == "Equipment & Hardware"
    assert fresh[0]["posting_category"]["source"] == "llm"


def _seed_source(client, entity, vendor_norm):
    """Restamp a learned row as Zoho-seeded, the way `memory seed-zoho` does."""
    import sqlite3

    db = client._data_root / "learning.sqlite"
    conn = sqlite3.connect(str(db))
    with conn:
        conn.execute(
            "UPDATE merchant_category SET source_run = 'zoho-seed:822741658' "
            "WHERE legal_entity_id = ? AND vendor_norm = ?",
            (entity, vendor_norm),
        )
    conn.close()


# ── hole 2: a rule saved with no company still reaches a row ────────────


def test_a_rule_saved_with_no_company_reaches_a_row_that_has_one(client, monkeypatch):
    # A live month saves its corrections under the company each expense
    # carried, and most carry none (33 of 52 July receipts, 13 of 31 in
    # August). Keyed on company + vendor alone, those rules reached nothing.
    july = _month(client, monkeypatch, _chair_receipt(), entity="")
    row = _row(client, july, "Contoso")
    assert row["legal_entity_id"] == ""
    _set_category(client, july, row["document_id"], "Office Supplies & Consumables")
    assert _publish(client, july)["saved"] is True
    assert [c["entity"] for c in _memory(client)["categories"]] == [""]

    august = _month(
        client, monkeypatch, _chair_receipt(date="2026-08-02"),
        entity="Corporate Services", label="August 2026",
        name="aug.jpg", data=JPG + b"aug",
    )
    row = _row(client, august, "Contoso")
    assert row["legal_entity_id"] == "Corporate Services"
    assert row["posting_category"]["category"] == "Office Supplies & Consumables"
    # The sign-off also grew the registry, so M1 reads the category from
    # there ("registry"). Take the registry away and the company-less RULE
    # alone still reaches the row that has a company: hole 2, as built.
    assert row["posting_category"]["source"] == "registry"
    resp = client.put("/api/settings", json={"merchants": {}})
    assert resp.status_code == 200, resp.text
    _add(client, monkeypatch, august, _chair_receipt(date="2026-08-09"),
         name="aug2.jpg", data=JPG + b"aug2")
    later = [r for r in _rows(client, august) if r["document_id"] != row["document_id"]]
    assert later[0]["legal_entity_id"] == "Corporate Services"
    assert later[0]["posting_category"]["category"] == "Office Supplies & Consumables"
    assert later[0]["posting_category"]["source"] == "learned"


# ── hole 3: sign-off on a month with a statement teaches the pairs ──────


def _xlsx(rows) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["Date", "Description", "Type", "Amount"])
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _statement(client, batch, rows):
    _done(client, client.post(
        f"/api/expense-batches/{batch}/statement",
        files={"statement": ("July2026.xlsx", _xlsx(rows), XLSX)},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    ))


def _bare_receipt(vendor, date, total, currency="USD"):
    return ExtractedReceipt(
        date=date, total=total, currency=currency, vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
    )


def test_publishing_a_month_with_a_statement_teaches_spelling_and_rate(
    client, monkeypatch
):
    july = _month(
        client, monkeypatch,
        _bare_receipt("Amazon.de", "2026-07-02", "276.08", currency="EUR"),
        label="July 2026",
    )
    _statement(client, july, [
        (datetime(2026, 7, 2), "AMAZON* Z11US7DF5", "Sale", -315.56),
    ])
    view = client.get(f"/api/runs/{july}").json()
    row = next(r for r in view["rows"] if "AMAZON" in (r["vendor"] or ""))
    doc = row["candidates"][0]["document_id"]
    resp = client.post(f"/api/runs/{july}/decisions", json={
        "transaction_id": row["transaction_id"], "status": "confirmed",
        "chosen_document_id": doc,
    })
    assert resp.status_code == 200, resp.text
    assert _memory(client)["counts"] == {
        "merchant_category": 0, "vendor_alias": 0, "merchant_fx": 0,
        "merchant_entity": 0, "field_correction": 0,
    }

    memory = _publish(client, july)
    assert memory["saved"] is True
    assert memory["learned"]["confirmed_pairs"] == 1
    assert memory["learned"]["vendor_aliases"] == 1
    assert memory["learned"]["merchant_fx"] == 1

    view = _memory(client)
    assert view["counts"]["vendor_alias"] == 1
    alias = view["aliases"][0]
    assert alias["stmt"] == "amazon z11us7df5"
    assert alias["receipt"] == "amazon de"
    assert view["counts"]["merchant_fx"] == 1


def test_a_generic_statement_description_teaches_no_alias(client, monkeypatch):
    # Item 117's guard, on this path too: "SUPERMERCADO" names a kind of
    # shop, not a merchant, so it must not become a remembered spelling.
    july = _month(
        client, monkeypatch,
        _bare_receipt("Supermercado", "2026-07-02", "41.85"),
        label="July 2026",
    )
    _statement(client, july, [
        (datetime(2026, 7, 2), "SUPERMERCADO", "Sale", -41.85),
    ])
    view = client.get(f"/api/runs/{july}").json()
    row = next(r for r in view["rows"] if "SUPERMERCADO" in (r["vendor"] or ""))
    assert client.post(f"/api/runs/{july}/decisions", json={
        "transaction_id": row["transaction_id"], "status": "confirmed",
        "chosen_document_id": row["candidates"][0]["document_id"],
    }).status_code == 200

    memory = _publish(client, july)
    assert memory["learned"]["confirmed_pairs"] == 1
    assert memory["learned"]["vendor_aliases"] == 0
    assert _memory(client)["counts"]["vendor_alias"] == 0


# ── the invariant: a reviewer's own category is never overwritten ───────


def test_a_reviewer_edit_survives_a_remembered_category(client, monkeypatch):
    july = _month(client, monkeypatch, _chair_receipt())
    doc = _row(client, july, "Contoso")["document_id"]
    _set_category(client, july, doc, "Office Supplies & Consumables")
    assert _publish(client, july)["saved"] is True

    august = _month(
        client, monkeypatch, _chair_receipt(date="2026-08-02"),
        label="August 2026", name="aug.jpg", data=JPG + b"aug",
    )
    row = _row(client, august, "Contoso")
    aug_doc = row["document_id"]
    # The remembered category filled the row (through the registry the
    # sign-off grew, since M1); the reviewer disagrees.
    assert row["posting_category"]["source"] == "registry"
    _set_category(client, august, aug_doc, "Travel & Transport")

    # A later arrival re-runs the whole pass over the month. Her category
    # stands, and it stands as HERS.
    _add(client, monkeypatch, august, _chair_receipt(date="2026-08-09"),
         name="aug2.jpg", data=JPG + b"aug2")
    row = _row_by_doc(client, august, aug_doc)
    assert row["posting_category"]["category"] == "Travel & Transport"
    assert row["posting_category"]["source"] == "override"
    assert row["line_items"][0]["source"] == "EDITED"
