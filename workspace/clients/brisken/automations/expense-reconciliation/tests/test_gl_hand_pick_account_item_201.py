"""Item 201: on a GL month, an account picked by hand exports under its name.

The GL picker sends only the leaf code. The account rule written for the eight
buckets (item 70: a changed category keeps no account) dropped the line's
account and stored none, so a hand pick printed "(account unmapped - assign)"
in the export while the engine's own pick printed the account's name. On a GL
month the code IS the account: its name is read from the row's company chart,
at read time, so a later company change reads the new company's wording.

Every assertion runs through a route: the category edit, the expense grid, the
CSV the reviewer downloads, the company change, and a receiptless charge.
"""
from __future__ import annotations

import csv
import io
import json
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ClassificationResult,
    ExtractedReceipt,
    MockLLMClient,
)
from expense_recon.output.zoho_expense_export import EXPENSE_COLUMNS  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.zoho import curated_leaves  # noqa: E402

CORP, CLOUD = "Corporate Services", "Cloud Services"
CORP_ORG, CLOUD_ORG = "822741658", "697686691"
UNMAPPED = "(account unmapped - assign)"
COL_ACCOUNT = EXPENSE_COLUMNS.index("Expense Account")
JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


def _label(org: str, code: str) -> str:
    return next(lbl for lbl in curated_leaves.llm_leaf_labels(org)
                if lbl.startswith(code + " "))


def _name(org: str, code: str) -> str:
    return curated_leaves.binding(code, org).name


def _shared_code_named_differently() -> str:
    """A code both companies post to under different names (Corporate
    Services prefixes its own: `CorpServ | Travel Expense | Food`)."""
    for code in sorted(curated_leaves.postable_codes(CORP_ORG)):
        if (curated_leaves.is_postable(CLOUD_ORG, code)
                and _name(CORP_ORG, code) != _name(CLOUD_ORG, code)
                and not curated_leaves.has_postable_children(CORP_ORG, code)
                and not curated_leaves.has_postable_children(CLOUD_ORG, code)):
            return code
    raise AssertionError("fixture: no shared code with two names")


def _two_codes(org: str) -> tuple[str, str]:
    """Two leaves the model is offered (never a parent, item 216 Build 2)."""
    a, b = [c for c in sorted(curated_leaves.postable_codes(org))
            if not curated_leaves.has_postable_children(org, c)][:2]
    return a, b


def _chart_accounts(org: str) -> list[dict]:
    """The org's real curated accounts, the chart shape the export gate reads
    (the live chart holds them; an empty chart would divert every line)."""
    from expense_recon.zoho._curated_leaves_data import LEAVES

    return [
        {"account_id": b[org][0], "account_name": b[org][1], "account_code": code,
         "account_type": "expense", "is_active": True, "parent_account_name": None}
        for code, (_branch, b) in LEAVES.items() if org in b
    ]


@pytest.fixture
def web(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    chart = tmp_path / "coa.json"
    chart.write_text(json.dumps({
        CORP_ORG: {"org": {"name": CORP}, "accounts": _chart_accounts(CORP_ORG)},
        CLOUD_ORG: {"org": {"name": CLOUD}, "accounts": _chart_accounts(CLOUD_ORG)},
    }), encoding="utf-8")
    prov = tmp_path / "coa-provision.json"
    prov.write_text(json.dumps({
        "chart_path": str(chart),
        "entities": {CORP: {"org_id": CORP_ORG}, CLOUD: {"org_id": CLOUD_ORG}},
    }), encoding="utf-8")
    monkeypatch.setenv("EXPENSE_RECON_COA_PROVISION", str(prov))
    with TestClient(create_app(tmp_path)) as c:
        yield c


def _mock(monkeypatch, reply: str, *, extract: bool = True) -> None:
    kwargs = {"responses": [ClassificationResult(reply, None, 0.9, "mock")] * 4}
    if extract:
        kwargs["extraction_responses"] = [ExtractedReceipt(
            date="2026-08-01", total="40.00", currency="USD", vendor="Acme",
            reference="", line_items=(), confidence=0.9, notes="")]
    mock = MockLLMClient(**kwargs)
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))


def _gl_batch(web, monkeypatch, entity: str, engine_code: str):
    """The live shape: a month created with no company (so its export gate
    covers every company), a receipt that arrives without one, and the
    company set on the row, which runs the engine for it."""
    _mock(monkeypatch, _label(CORP_ORG, engine_code))
    resp = web.post("/api/expense-batches", data={"legal_entity": ""})
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["batch_id"]
    resp = web.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("acme.jpg", JPG, "application/octet-stream"))])
    assert web.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    body = web.get(f"/api/expense-batches/{batch_id}").json()
    assert body["category_vocabulary"] == "gl", "precondition: a GL month"
    (expense,) = body["expenses"]
    doc = expense["document_id"]
    r = web.put(f"/api/runs/{batch_id}/expenses/{doc}/entity",
                json={"legal_entity": entity})
    assert r.status_code == 200, r.text
    return batch_id, doc


def _pick(web, batch_id, doc, code):
    r = web.post(f"/api/runs/{batch_id}/categories",
                 json={"document_id": doc, "line_index": 0, "category": code})
    assert r.status_code == 200, r.text


def _row(web, batch_id):
    (row,) = web.get(f"/api/expense-batches/{batch_id}").json()["expenses"]
    return row


def _csv_accounts(web, batch_id) -> list[str]:
    resp = web.get(f"/runs/{batch_id}/expenses.csv")
    assert resp.status_code == 200, resp.text
    rows = list(csv.reader(io.StringIO(resp.text)))
    return [r[COL_ACCOUNT] for r in rows[1:]]


def test_a_hand_picked_code_books_and_exports_under_its_account_name(web, monkeypatch):
    engine_code, picked = _two_codes(CORP_ORG)
    batch_id, doc = _gl_batch(web, monkeypatch, CORP, engine_code)
    # Control: the engine's own pick passes the export gate under its name.
    assert _row(web, batch_id)["posting_category"]["zoho_account"] == _name(CORP_ORG, engine_code)
    assert _csv_accounts(web, batch_id) == [_name(CORP_ORG, engine_code)]

    _pick(web, batch_id, doc, picked)

    row = _row(web, batch_id)
    want = _name(CORP_ORG, picked)
    assert row["posting_category"]["category"] == picked
    assert row["posting_category"]["zoho_account"] == want
    assert [b["account"] for b in row["books_as"]] == [want]
    assert _csv_accounts(web, batch_id) == [want]
    assert UNMAPPED not in _csv_accounts(web, batch_id)


def test_the_name_follows_the_rows_company_when_it_changes(web, monkeypatch):
    code = _shared_code_named_differently()
    engine_code = next(c for c in _two_codes(CORP_ORG) if c != code)
    batch_id, doc = _gl_batch(web, monkeypatch, CORP, engine_code)
    _pick(web, batch_id, doc, code)
    assert _csv_accounts(web, batch_id) == [_name(CORP_ORG, code)]

    # The company change re-runs the engine for the TOOL's answer only; her
    # pick stays, and now reads the new company's wording for the same code.
    _mock(monkeypatch, _label(CLOUD_ORG, code), extract=False)
    r = web.put(f"/api/runs/{batch_id}/expenses/{doc}/entity",
                json={"legal_entity": CLOUD})
    assert r.status_code == 200, r.text
    row = _row(web, batch_id)
    assert row["posting_category"]["zoho_account"] == _name(CLOUD_ORG, code)
    assert _csv_accounts(web, batch_id) == [_name(CLOUD_ORG, code)]


def test_a_row_whose_company_comes_from_its_card_reads_that_companys_name(
    web, monkeypatch,
):
    """The live shape of most rows: the receipt's own stamp is blank and the
    company the grid shows, and the export writes, comes from the card chain.
    The name has to resolve in THAT company, on screen and in the file."""
    web.put("/api/settings", json={"cards": {"corp-1672": {
        "label": "Corporate card", "digits": ["1672"], "entity": CORP,
        "person": "Nicolas", "zoho_account": "Chase 1672"}}})
    engine_code, picked = _two_codes(CORP_ORG)
    _mock(monkeypatch, _label(CORP_ORG, engine_code))
    batch_id = web.post("/api/expense-batches", data={"legal_entity": ""}).json()["batch_id"]
    resp = web.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("acme.jpg", JPG, "application/octet-stream"))])
    assert web.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    doc = _row(web, batch_id)["document_id"]
    r = web.put(f"/api/runs/{batch_id}/expenses/{doc}",
                json={"field": "card_key", "value": "corp-1672"})
    assert r.status_code == 200, r.text
    row = _row(web, batch_id)
    assert row["legal_entity_id"] == CORP and row["entity_source"] != "override"

    _pick(web, batch_id, doc, picked)

    want = _name(CORP_ORG, picked)
    row = _row(web, batch_id)
    assert row["posting_category"]["zoho_account"] == want
    assert [b["account"] for b in row["books_as"]] == [want]
    assert _csv_accounts(web, batch_id) == [want]


def test_a_code_the_company_cannot_post_to_stays_visibly_unmapped(web, monkeypatch):
    foreign = next(
        c for c in sorted(curated_leaves.postable_codes(CLOUD_ORG))
        if not curated_leaves.is_postable(CORP_ORG, c))
    engine_code, _ = _two_codes(CORP_ORG)
    batch_id, doc = _gl_batch(web, monkeypatch, CORP, engine_code)
    _pick(web, batch_id, doc, foreign)
    assert _row(web, batch_id)["posting_category"]["zoho_account"] in ("", None)
    assert _csv_accounts(web, batch_id) == [UNMAPPED]


def test_a_picked_account_still_wins_over_the_codes_name(web, monkeypatch):
    engine_code, picked = _two_codes(CORP_ORG)
    batch_id, doc = _gl_batch(web, monkeypatch, CORP, engine_code)
    r = web.post(f"/api/runs/{batch_id}/categories",
                 json={"document_id": doc, "line_index": 0, "category": picked,
                       "zoho_account": _name(CORP_ORG, engine_code)})
    assert r.status_code == 200, r.text
    assert _row(web, batch_id)["posting_category"]["zoho_account"] == _name(CORP_ORG, engine_code)


def test_a_receiptless_charge_pick_reads_its_account_name(tmp_path):
    """The charge half: the pick sits on the charge's own pseudo-receipt id
    and resolves in the CHARGE's company (the card's, stamped at re-match)."""
    from datetime import date

    from expense_recon.matching.types import (
        Categorization,
        ClassificationSource,
        MatchOutcome,
        Transaction,
    )
    from expense_recon.web.serialize import categorization_to_dict, snapshot_to_dict
    from expense_recon.web.store import RunStore

    engine_code, picked = _two_codes(CLOUD_ORG)
    tx = Transaction(
        transaction_id="tx1", legal_entity_id=CLOUD, account_id="card-9693",
        transaction_date=date(2026, 8, 3), posting_date=None,
        amount=Decimal("-12.00"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement="SOME SAAS")
    snapshot = snapshot_to_dict([tx], [], MatchOutcome(
        matches=[], unmatched_transactions=["tx1"], unmatched_receipts=[],
        ambiguous=[]), [])
    snapshot["charge_categorizations"] = {"tx1": categorization_to_dict(Categorization(
        category=engine_code, zoho_account=_name(CLOUD_ORG, engine_code),
        confidence=0.9, source=ClassificationSource.VENDOR, reasoning="fake"))}
    store = RunStore(tmp_path / "recon-web.sqlite")
    for run_id, config in (("gl-month", {"gl_entity_orgs": {CLOUD: CLOUD_ORG}}),
                           ("bucket-month", {})):
        store.create_run(
            run_id=run_id, created_at="2026-09-25T00:00:00", label=run_id,
            operator=None, summary={}, snapshot=snapshot, config=config,
            work_dir=str(tmp_path), llm_enabled=False, has_coa=False)
    store.close()
    with TestClient(create_app(tmp_path)) as client:
        for run_id, want in (("gl-month", _name(CLOUD_ORG, picked)),
                             ("bucket-month", None)):
            r = client.put(f"/api/runs/{run_id}/charges/tx1/category",
                           json={"category": picked})
            assert r.status_code == 200, r.text
            (row,) = [x for x in client.get(f"/api/runs/{run_id}").json()["rows"]
                      if x["transaction_id"] == "tx1"]
            assert row["posting_category"]["category"] == picked, run_id
            # A bucket month keeps item 70's rule: a changed category, no account.
            assert (row["posting_category"]["zoho_account"] or None) == want, run_id
