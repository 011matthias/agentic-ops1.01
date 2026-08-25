"""Cards R4: a batch whose receipts belong to different legal entities.

Owner ruling 2026-08-22, answering the R4 question directly: **one file with
the entity as a column**, not one file per entity. A month of receipts is one
month of receipts; who paid is a property of the row.

The second half is the chart gate. `CoaGate` was built when "a run targets ONE
legal entity" was true; after Cards R3 a batch legitimately mixes them, so a
single gate would validate every row against ONE entity's chart and divert
rows that are perfectly valid under their own. Each row is gated against the
chart of the entity that actually pays it.

Harness mirrors test_cards_r3_entity_flow.
"""
from __future__ import annotations

import csv
import io

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.coa_gate import CoaGate  # noqa: E402
from expense_recon.ingest.chart_of_accounts import (  # noqa: E402
    Account,
    ChartOfAccounts,
)
from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.output.zoho_expense_export import EXPENSE_COLUMNS  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
JPG2 = b"\xff\xd8\xff\xe0other-jpeg-bytes"
COL_ENTITY = EXPENSE_COLUMNS.index("Legal Entity")
COL_ACCOUNT = EXPENSE_COLUMNS.index("Expense Account")
COL_VENDOR = EXPENSE_COLUMNS.index("Vendor")

# One card per entity: the two-entity month in miniature.
TWO_ENTITY_CARDS = {
    "corp-2838": {
        "label": "Corporate card",
        "digits": ["2838"],
        "entity": "Corporate Services",
    },
    "cloud-9693": {
        "label": "Cloud card",
        "digits": ["9693"],
        "entity": "Cloud Services",
    },
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_COA_PROVISION", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(date="2026-08-01", total="42.50", currency="USD", vendor="Staples",
                reference="", line_items=(), confidence=0.9, notes="")
    base.update(overrides)
    return ExtractedReceipt(**base)


def _patch_ocr(monkeypatch, *extractions: ExtractedReceipt) -> None:
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))


def _mixed_batch(client, monkeypatch) -> str:
    resp = client.put("/api/settings", json={"cards": TWO_ENTITY_CARDS})
    assert resp.status_code == 200, resp.text
    _patch_ocr(
        monkeypatch,
        _extraction(vendor="Staples", payment_hint="Visa ...2838"),
        _extraction(vendor="Cafe Lisboa", total="18.00", payment_hint="Visa ...9693"),
    )
    resp = client.post(
        "/api/expense-batches",
        files=[("files", ("a.jpg", JPG, "application/octet-stream")),
               ("files", ("b.jpg", JPG2, "application/octet-stream"))],
        data={"legal_entity": "", "label": "Mixed month"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert client.get(f"/jobs/{body['job_id']}").json()["status"] == "done"
    return body["batch_id"]


def _chart(account_name: str, code: str) -> ChartOfAccounts:
    """A one-account chart: enough to say "this account exists here"."""
    return ChartOfAccounts([
        Account(name=account_name, code=code, account_type="expense",
                parent_name=None, is_active=True)
    ])


def _export_rows(client, batch_id) -> list[list[str]]:
    resp = client.get(f"/runs/{batch_id}/expenses.csv")
    assert resp.status_code == 200, resp.text
    rows = list(csv.reader(io.StringIO(resp.text)))
    assert rows[0] == list(EXPENSE_COLUMNS)
    return rows[1:]


def test_a_mixed_entity_month_exports_as_one_file(client, monkeypatch):
    """The ruling: ONE file, entity as a column. Not one file per entity, and
    never a refusal to export because the rows disagree about who paid."""
    batch_id = _mixed_batch(client, monkeypatch)

    rows = _export_rows(client, batch_id)
    assert len(rows) == 2
    by_vendor = {r[COL_VENDOR]: r for r in rows}
    assert by_vendor["Staples"][COL_ENTITY] == "Corporate Services"
    assert by_vendor["Cafe Lisboa"][COL_ENTITY] == "Cloud Services"


def test_the_grid_shows_both_entities_with_their_provenance(client, monkeypatch):
    batch_id = _mixed_batch(client, monkeypatch)

    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    by_vendor = {e["vendor"]["display"]: e for e in grid["expenses"]}
    assert by_vendor["Staples"]["legal_entity_id"] == "Corporate Services"
    assert by_vendor["Cafe Lisboa"]["legal_entity_id"] == "Cloud Services"
    assert {e["entity_source"] for e in grid["expenses"]} == {"card"}
    assert grid["summary"]["n_needs_entity"] == 0


def test_each_row_is_gated_against_its_own_entitys_chart():
    """A single gate would judge every row against ONE chart: a Cloud Services
    row whose account exists only in the Cloud chart would be diverted to
    review as non-postable, and a Corporate row would sail through on the
    strength of the wrong chart. Both rows are gated against their own."""
    from expense_recon.coa_gate import gate_for_entities
    from expense_recon.matching.types import Categorization, LineItem, Receipt

    corp_chart = _chart("Office Supplies", "E500")
    cloud_chart = _chart("Cloud Hosting", "C100")

    def _receipt(doc: str, entity: str, account: str) -> Receipt:
        item = LineItem(
            description="x", line_total=None, quantity=None, unit_price=None,
            categorization=Categorization(
                category="Software & Subscriptions", zoho_account=account,
                confidence=1.0, source=None, reasoning=""),
        )
        return Receipt(
            document_id=doc, legal_entity_id=entity, detected_date=None,
            detected_total=None, detected_currency="USD", detected_vendor="V",
            line_items=(item,),
        )

    receipts = [
        _receipt("corp.jpg", "Corporate Services", "Office Supplies"),
        _receipt("cloud.jpg", "Cloud Services", "Cloud Hosting"),
    ]
    gate = gate_for_entities({
        "Corporate Services": CoaGate(chart=corp_chart, entity="Corporate Services"),
        "Cloud Services": CoaGate(chart=cloud_chart, entity="Cloud Services"),
    })
    gated, report = gate.run(receipts)

    # Every row postable under its OWN chart: nothing diverted.
    assert report.n_diverted == 0, report
    assert [r.line_items[0].categorization.zoho_account for r in gated] == [
        "Office Supplies", "Cloud Hosting",
    ]


def test_a_row_whose_account_is_foreign_to_its_entity_is_still_caught():
    """Per-entity gating must not become no gating: an account that exists in
    the OTHER entity's chart is still not postable under this row's."""
    from expense_recon.coa_gate import gate_for_entities
    from expense_recon.matching.types import Categorization, LineItem, Receipt

    corp_chart = _chart("Office Supplies", "E500")
    cloud_chart = _chart("Cloud Hosting", "C100")
    item = LineItem(
        description="x", line_total=None, quantity=None, unit_price=None,
        categorization=Categorization(
            category="Software & Subscriptions", zoho_account="Cloud Hosting",
            confidence=1.0, source=None, reasoning=""),
    )
    receipt = Receipt(
        document_id="corp.jpg", legal_entity_id="Corporate Services",
        detected_date=None, detected_total=None, detected_currency="USD",
        detected_vendor="V", line_items=(item,),
    )
    gate = gate_for_entities({
        "Corporate Services": CoaGate(chart=corp_chart, entity="Corporate Services"),
        "Cloud Services": CoaGate(chart=cloud_chart, entity="Cloud Services"),
    })
    _gated, report = gate.run([receipt])
    assert report.n_diverted == 1, report


def test_an_entityless_batch_is_provisioned_against_every_entity_chart(tmp_path):
    """The live gap this closes: `apply_to_config` looked up ONE entity, so a
    batch with no single entity (every Cards R3 batch) got no `coa_validation`
    block at all and exported completely un-gated — precisely the batches most
    able to post an account to the wrong company."""
    import json

    from expense_recon.cli import _build_coa_gate
    from expense_recon.coa_gate import MultiEntityCoaGate
    from expense_recon.coa_provision import apply_to_config

    chart = tmp_path / "coa.json"
    chart.write_text(json.dumps({
        "822741658": {"org": {"name": "Corporate Services"}, "accounts": [
            {"account_id": "1", "account_name": "Office Supplies",
             "account_code": "E500", "account_type": "expense",
             "parent_account_name": None, "is_active": True}]},
        "697686691": {"org": {"name": "Cloud Services"}, "accounts": [
            {"account_id": "9", "account_name": "Cloud Hosting",
             "account_code": "C100", "account_type": "expense",
             "parent_account_name": None, "is_active": True}]},
    }), encoding="utf-8")
    prov = tmp_path / "coa-provision.json"
    prov.write_text(json.dumps({
        "chart_path": str(chart),
        "entities": {
            "Corporate Services": {"org_id": "822741658"},
            "Cloud Services": {"org_id": "697686691"},
        },
    }), encoding="utf-8")

    cfg = apply_to_config({"receipts": {}}, "", path=str(prov))
    entries = cfg["coa_validation"]["entities"]
    assert [e["entity_label"] for e in entries] == [
        "Cloud Services", "Corporate Services",
    ]

    gate = _build_coa_gate(cfg, tmp_path)
    assert isinstance(gate, MultiEntityCoaGate)
    assert set(gate.gates) == {"Cloud Services", "Corporate Services"}

    # And it judges each row against its own chart, end to end.
    receipts = [
        _receipt_for("corp.jpg", "Corporate Services", "E500 Office Supplies"),
        _receipt_for("cloud.jpg", "Cloud Services", "C100 Cloud Hosting"),
        # Corporate row reaching for the Cloud-only account: still caught.
        _receipt_for("wrong.jpg", "Corporate Services", "C100 Cloud Hosting"),
    ]
    _gated, report = gate.run(receipts)
    assert report.n_diverted == 1
    (failed,) = report.failing()
    assert failed.document_id == "wrong.jpg"


def _receipt_for(doc: str, entity: str, account: str):
    from expense_recon.matching.types import Categorization, LineItem, Receipt

    item = LineItem(
        description="x", line_total=None, quantity=None, unit_price=None,
        categorization=Categorization(
            category="Software & Subscriptions", zoho_account=account,
            confidence=1.0, source=None, reasoning=""),
    )
    return Receipt(
        document_id=doc, legal_entity_id=entity, detected_date=None,
        detected_total=None, detected_currency="USD", detected_vendor="V",
        line_items=(item,),
    )
