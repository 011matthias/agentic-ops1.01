"""Note item M1 (owner directive 2026-09-18): merchant-to-category is the
default; the exceptions vary by company, on the account.

Dirk's rule: binding a merchant to ONE category is right about 90% of the
time; the exceptions (OpenAI, Anthropic, Lovable) book to several places,
and what varies by company is the ACCOUNT. So a merchant with a registry
default reads that category on every receipt, itemized or not, and the
(company, vendor) rule memory holds for the receipt's company decides the
account. Every test runs through the caller a live month takes: the receipt
add route, the statement attach route, and `GET /api/memory`.
"""
from __future__ import annotations

import io
import sqlite3
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

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes-m1"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SOFTWARE = "Software & Subscriptions"
CLOUD = "Cloud Services"
CORP = "Corporate Services"
COGS = "COGS - DEV Infrastructure (SAP Apps & others)"
OTHER = "Other Infra and IT Costs for Cloud Business"
REGISTRY = {
    "Anthropic": {
        "aliases": ["Anthropic, PBC", "ANTHROPIC"],
        "category": SOFTWARE, "zoho_account": None,
    },
    "Lovable": {
        "aliases": ["Lovable Labs Incorporated"],
        "category": SOFTWARE, "zoho_account": None,
    },
}


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


def _itemized(vendor, date="2026-07-02", total="120.00"):
    """A receipt whose ONE line reads as Equipment & Hardware to the model,
    so a registry category on it can only have come from the registry."""
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


def _month(client, monkeypatch, *extractions, entity=CLOUD, label="July 2026",
           name="a.jpg", data=JPG):
    mock = _wire(monkeypatch, *extractions)
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": entity, "label": label}
    )
    _done(client, resp)
    batch = resp.json()["batch_id"]
    if extractions:
        _done(client, client.post(
            f"/api/expense-batches/{batch}/receipts",
            files=[("files", (name, data, "application/octet-stream"))],
        ))
    return batch, mock


def _add(client, monkeypatch, batch, *extractions, name="b.jpg", data=JPG + b"x"):
    mock = _wire(monkeypatch, *extractions)
    _done(client, client.post(
        f"/api/expense-batches/{batch}/receipts",
        files=[("files", (name, data, "application/octet-stream"))],
    ))
    return mock


def _rows(client, batch):
    return client.get(f"/api/expense-batches/{batch}").json()["expenses"]


def _row(client, batch, vendor):
    return next(r for r in _rows(client, batch) if vendor in r["vendor"]["display"])


def _seed_registry(client, merchants=REGISTRY):
    resp = client.put("/api/settings", json={"merchants": merchants})
    assert resp.status_code == 200, resp.text


def _rule(client, entity, vendor, category, account):
    resp = client.put("/api/memory/categories", json={
        "legal_entity_id": entity, "vendor": vendor,
        "category": category, "zoho_account": account,
    })
    assert resp.status_code == 200, resp.text


def _validate(client, entity, vendor):
    resp = client.post("/api/memory/categories/validate", json={
        "rows": [{"legal_entity_id": entity, "vendor": vendor}],
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["validated"] == 1, resp.text


def _seed_source(client, entity, vendor_norm):
    """Restamp a rule as Zoho-seeded, the shape the live 103 rows have."""
    conn = sqlite3.connect(str(client._data_root / "learning.sqlite"))
    with conn:
        conn.execute(
            "UPDATE merchant_category SET source_run = 'zoho-seed:822741658' "
            "WHERE legal_entity_id = ? AND vendor_norm = ?",
            (entity, vendor_norm),
        )
    conn.close()


def _statement(client, batch, rows):
    wb = Workbook()
    ws = wb.active
    ws.append(["Date", "Description", "Type", "Amount"])
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    _done(client, client.post(
        f"/api/expense-batches/{batch}/statement",
        files={"statement": ("July2026.xlsx", buf.getvalue(), XLSX)},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    ))


def _line_read_happened(mock) -> bool:
    return any(name == "classify_line_items" for name, _ in mock.calls)


# ── (a) + (b): the registry's category, the company's account ───────────


def test_a_merchant_keeps_its_category_and_takes_the_companys_account(
    client, monkeypatch
):
    _seed_registry(client)
    _rule(client, CLOUD, "Anthropic, PBC", SOFTWARE, COGS)

    cloud, mock = _month(client, monkeypatch, _itemized("Anthropic, PBC"))
    row = _row(client, cloud, "Anthropic")
    assert row["vendor"]["display"] == "Anthropic"
    # The items read Equipment & Hardware; the merchant's default wins and
    # the line read was never paid for.
    assert row["posting_category"]["category"] == SOFTWARE
    assert row["posting_category"]["source"] == "registry"
    assert row["posting_category"]["zoho_account"] == COGS
    assert row["line_items"][0]["provenance"] == (
        "merchant registry default; account from the rule saved for Cloud Services"
    )
    assert row["review"]["reason_code"] != "vendor_guess"
    assert not _line_read_happened(mock)

    # The other company has no rule: same category, the registry's own
    # account (none), and the line says nothing about a rule.
    corp, _ = _month(
        client, monkeypatch, _itemized("Anthropic, PBC", date="2026-07-03"),
        entity=CORP, label="July 2026 corp", name="c.jpg", data=JPG + b"c",
    )
    row = _row(client, corp, "Anthropic")
    assert row["posting_category"]["category"] == SOFTWARE
    assert row["posting_category"]["source"] == "registry"
    assert row["posting_category"]["zoho_account"] == ""
    assert row["line_items"][0]["provenance"] == ""


def test_a_seeded_rule_under_another_category_gives_no_account_until_validated(
    client, monkeypatch
):
    # The live seed files a few vendors under a category Criss would not
    # use. Such a row is how the books once posted, not an account for the
    # registry's category, so it contributes nothing until a person stands
    # behind it; validating it on the Memory page is that.
    _seed_registry(client)
    _rule(client, CORP, "Anthropic, PBC", "Marketing & Advertising", OTHER)
    _seed_source(client, CORP, "anthropic pbc")

    corp, _ = _month(client, monkeypatch, _itemized("Anthropic, PBC"), entity=CORP)
    row = _row(client, corp, "Anthropic")
    assert row["posting_category"]["category"] == SOFTWARE
    assert row["posting_category"]["zoho_account"] == ""
    assert row["line_items"][0]["provenance"] == ""

    _validate(client, CORP, "Anthropic, PBC")
    _add(client, monkeypatch, corp, _itemized("Anthropic, PBC", date="2026-07-09"))
    later = [r for r in _rows(client, corp) if r["document_id"] != row["document_id"]]
    assert later[0]["posting_category"]["category"] == SOFTWARE
    assert later[0]["posting_category"]["source"] == "registry"
    assert later[0]["posting_category"]["zoho_account"] == OTHER
    assert "the rule saved for Corporate Services" in later[0]["line_items"][0]["provenance"]


def test_a_company_less_receipt_takes_the_account_the_vendors_rules_agree_on(
    client, monkeypatch
):
    _seed_registry(client)
    _rule(client, CLOUD, "Anthropic, PBC", SOFTWARE, COGS)
    _rule(client, CORP, "Anthropic, PBC", SOFTWARE, COGS)

    month, _ = _month(client, monkeypatch, _itemized("Anthropic, PBC"), entity="")
    row = _row(client, month, "Anthropic")
    assert row["legal_entity_id"] == ""
    assert row["posting_category"]["category"] == SOFTWARE
    assert row["posting_category"]["zoho_account"] == COGS
    assert row["line_items"][0]["provenance"] == (
        "merchant registry default; account from the rules for "
        "Cloud Services, Corporate Services, which agree"
    )

    # Once the companies disagree on the account, a receipt with no
    # company gets the category and no account: an account belongs to one
    # company's chart.
    _rule(client, CORP, "Anthropic, PBC", SOFTWARE, OTHER)
    _add(client, monkeypatch, month, _itemized("Anthropic, PBC", date="2026-07-09"))
    later = [r for r in _rows(client, month) if r["document_id"] != row["document_id"]]
    assert later[0]["posting_category"]["category"] == SOFTWARE
    assert later[0]["posting_category"]["zoho_account"] == ""
    assert later[0]["line_items"][0]["provenance"] == ""


# ── (a) on a receiptless charge: the bank description names the merchant ─


def test_a_receiptless_charge_reads_its_merchants_default_not_a_guess(
    client, monkeypatch
):
    # Live July read the bank's "LOVABLE" as Meals & Entertainment four
    # times, a model guess. The charge's company (from its card) is
    # Corporate Services, whose rule names the account.
    _seed_registry(client)
    _rule(client, CORP, "LOVABLE", SOFTWARE, OTHER)
    month, _ = _month(client, monkeypatch, entity=CORP)
    _statement(client, month, [
        (datetime(2026, 7, 21), "LOVABLE", "Sale", -15.00),
        (datetime(2026, 7, 22), "PRESSMASTER FZCO", "Sale", -220.00),
    ])
    view = client.get(f"/api/runs/{month}").json()
    by_vendor = {r["vendor"]: r for r in view["rows"]}
    lovable = by_vendor["LOVABLE"]["charge_category"]
    assert lovable["category"] == SOFTWARE
    assert lovable["source"] == "REGISTRY"
    assert lovable["zoho_account"] == OTHER
    assert lovable["provenance"] == (
        "merchant registry default; account from the rule saved for Corporate Services"
    )
    # The bank's own description stays on the row; the registry names
    # nothing here.
    assert "LOVABLE" in by_vendor
    # A description no merchant matches is untouched by the registry.
    other = by_vendor["PRESSMASTER FZCO"]["charge_category"]
    assert other is None or other["source"] != "REGISTRY"


# ── (c): the Memory page shows the split per vendor, one line per company ─


def test_the_memory_page_groups_rules_per_vendor_one_line_per_company(client):
    _seed_registry(client)
    _rule(client, CORP, "Anthropic, PBC", SOFTWARE, OTHER)
    _rule(client, CLOUD, "Anthropic, PBC", SOFTWARE, COGS)
    _seed_source(client, CORP, "anthropic pbc")
    _rule(client, CORP, "Pressmaster FZCO", SOFTWARE, OTHER)

    view = client.get("/api/memory").json()
    assert [v["vendor"] for v in view["by_vendor"]] == ["anthropic pbc", "pressmaster fzco"]
    anthropic, pressmaster = view["by_vendor"]
    assert anthropic["merchant"] == "Anthropic"
    assert anthropic["category"] == SOFTWARE
    assert anthropic["multi_category"] is False
    companies = [
        {k: c[k] for k in ("entity", "category", "zoho_account", "count", "seeded", "validated")}
        for c in anthropic["companies"]
    ]
    assert companies == [
        {"entity": CLOUD, "category": SOFTWARE, "zoho_account": COGS,
         "count": 1, "seeded": False, "validated": ""},
        {"entity": CORP, "category": SOFTWARE, "zoho_account": OTHER,
         "count": 1, "seeded": True, "validated": ""},
    ]
    # No registry merchant: the vendor line says so, and the company line
    # alone carries the category its receipts will read.
    assert pressmaster["merchant"] == ""
    assert pressmaster["category"] == ""
    assert [c["entity"] for c in pressmaster["companies"]] == [CORP]
    # The flat table carries the same seed flag, and the two agree.
    flat = {(c["entity"], c["vendor"]): c["seeded"] for c in view["categories"]}
    assert flat[(CORP, "anthropic pbc")] is True
    assert flat[(CLOUD, "anthropic pbc")] is False

    # The "needs review" filter applies to the grouped view too.
    _validate(client, CLOUD, "Anthropic, PBC")
    view = client.get("/api/memory?unvalidated=1").json()
    anthropic = next(v for v in view["by_vendor"] if v["vendor"] == "anthropic pbc")
    assert [c["entity"] for c in anthropic["companies"]] == [CORP]


def test_the_memory_page_is_empty_shaped_with_no_store(client):
    view = client.get("/api/memory").json()
    assert view["by_vendor"] == []
    assert view["categories"] == []
