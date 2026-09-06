"""Backlog item 41 (owner directive 2026-09-06): unknown payment methods
suggest a private expense.

Owner: "When payment methods arise that have not been defined in the
system they must be suggested to the user as private expenses that will
require reimbursement to the person who expensed."

Pinned here:
* SUGGESTED, never stamped: a non-empty hint the chain resolves to no
  registered card reads check/`suggested_private` (rule-5 prose beside
  the code). Ambiguity does not suggest (a known-card contest), an
  explicit entity override does not (an operator decision), and nothing
  auto-books.
* Confirming private (POST .../expenses/{doc}/private, reimburse_to
  required) turns the row into a reimbursement row: person =
  reimburse_to, source "private", no entity required, paid-through
  "Private ({person})" on grid and CSV alike. Clearing it brings the
  suggestion back; assigning the real card clears it through the
  existing flow.
* `reimburse_to_prefill` is the ONE sanctioned use of the sender claim:
  offered only on the private flow, from `submitted_by`, never resolved
  into `person` without the operator's confirm — it must never
  generalize into sender-based attribution.
* The month report partitions confirmed private rows out of the company
  listing into a reimbursements-owed section, grouped per person with
  sums; the CSV keeps them as rows whose two columns say private.
"""
from __future__ import annotations

import csv
import io

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.output.zoho_expense_export import EXPENSE_COLUMNS  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
COL_PAID_THROUGH = EXPENSE_COLUMNS.index("Paid Through")
COL_ENTITY = EXPENSE_COLUMNS.index("Legal Entity")
COL_VENDOR = EXPENSE_COLUMNS.index("Vendor")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _patch_ocr(monkeypatch, *extractions):
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(date="2026-08-01", total="42.50", currency="USD",
                vendor="Staples", reference="", line_items=(),
                confidence=0.9, notes="")
    base.update(overrides)
    return ExtractedReceipt(**base)


def _create_batch(client, n_files=1, label="August 2026"):
    files = [
        ("files", (f"r{i}.jpg", JPG + bytes([i]), "application/octet-stream"))
        for i in range(n_files)
    ]
    resp = client.post("/api/expense-batches", files=files,
                       data={"legal_entity": "", "label": label})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert client.get(f"/jobs/{body['job_id']}").json()["status"] == "done"
    return body["batch_id"]


def _grid(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _confirm_private(client, batch_id, doc, person="Dirk"):
    resp = client.post(
        f"/api/runs/{batch_id}/expenses/{doc}/private",
        json={"private": True, "reimburse_to": person},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _set_category(client, batch_id, doc):
    r = client.post(f"/api/runs/{batch_id}/categories", json={
        "document_id": doc, "line_index": 0,
        "category": "Travel & Transport",
    })
    assert r.status_code == 200, r.text


# ── the suggestion ───────────────────────────────────────────────────


def test_unknown_payment_methods_are_suggested_private(client, monkeypatch):
    _patch_ocr(
        monkeypatch,
        _extraction(payment_hint="****0340"),
        _extraction(vendor="Padaria", total="8.00",
                    payment_hint="Cartao de Credito"),
        _extraction(vendor="No Hint Co", total="5.00"),
    )
    batch = _create_batch(client, n_files=3)
    grid = _grid(client, batch)
    by_vendor = {e["vendor"]["display"]: e for e in grid["expenses"]}

    for vendor in ("Staples", "Padaria"):  # unlisted digits AND tender word
        row = by_vendor[vendor]
        assert row["suggested_private"] is True
        assert row["review"]["state"] == "check"
        assert row["review"]["reason_code"] == "suggested_private"
        assert row["review"]["reason"]  # rule 5: prose label beside the code
        assert row["private"] is False

    # no payment method arose on this one: plain needs_entity, no guess
    no_hint = by_vendor["No Hint Co"]
    assert no_hint["suggested_private"] is False
    assert no_hint["review"]["reason_code"] == "needs_entity"

    assert grid["summary"]["n_suggested_private"] == 2
    assert grid["summary"]["n_private"] == 0
    assert grid["card_review"]["n_suggested_private"] == 2
    for entry in grid["card_review"]["unresolved_hints"]:
        assert entry["suggested_private"] is True


def test_ambiguity_never_suggests_private(client, monkeypatch):
    # two cards both claim 1672: a known-card contest, not private money
    client.put("/api/settings", json={"cards": {
        "a-1672": {"digits": ["1672"], "entity": "Corporate Services"},
        "b-1672": {"digits": ["1672"], "entity": "Cloud Services"},
    }})
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa ...1672"))
    batch = _create_batch(client)
    row = _grid(client, batch)["expenses"][0]
    assert row["suggested_private"] is False
    assert row["review"]["reason_code"] == "needs_entity"
    (entry,) = _grid(client, batch)["card_review"]["unresolved_hints"]
    assert entry["ambiguous"] is True
    assert entry["suggested_private"] is False


def test_entity_override_is_a_decision_and_clears_the_suggestion(
    client, monkeypatch
):
    _patch_ocr(monkeypatch, _extraction(payment_hint="****0340"))
    batch = _create_batch(client)
    doc = _grid(client, batch)["expenses"][0]["document_id"]
    r = client.put(f"/api/runs/{batch}/expenses/{doc}/entity",
                   json={"legal_entity": "Corporate Services"})
    assert r.status_code == 200, r.text
    row = _grid(client, batch)["expenses"][0]
    assert row["suggested_private"] is False
    assert row["review"]["reason_code"] != "suggested_private"


def test_assigning_the_card_clears_the_suggestion(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction(payment_hint="****0340"))
    batch = _create_batch(client)
    resp = client.post(f"/api/expense-batches/{batch}/cards", json={
        "assignments": [{"hint": "****0340", "card": "card-0340"}],
        "new_cards": {"card-0340": {
            "label": "Visa 0340", "entity": "Cloud Services",
            "person": "Criss",
        }},
    })
    assert resp.status_code == 200, resp.text
    row = _grid(client, batch)["expenses"][0]
    assert row["suggested_private"] is False
    assert row["legal_entity_id"] == "Cloud Services"
    assert row["person"] == "Criss"
    assert _grid(client, batch)["summary"]["n_suggested_private"] == 0


# ── the confirmation ─────────────────────────────────────────────────


def test_confirm_private_makes_a_reimbursement_row(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction(payment_hint="Cartao de Credito"))
    batch = _create_batch(client)
    doc = _grid(client, batch)["expenses"][0]["document_id"]

    # a reimbursement owed to nobody is not a decision
    r = client.post(f"/api/runs/{batch}/expenses/{doc}/private",
                    json={"private": True})
    assert r.status_code == 400
    assert "reimburse_to" in r.json()["error"]

    body = _confirm_private(client, batch, doc, person="Dirk")
    assert body["summary"]["n_private"] == 1
    assert body["summary"]["n_suggested_private"] == 0
    # a private row needs no entity: it leaves MISSING ENTITY too
    assert body["summary"]["n_needs_entity"] == 0

    row = _grid(client, batch)["expenses"][0]
    assert row["private"] is True
    assert row["reimburse_to"] == "Dirk"
    assert row["person"] == "Dirk"
    assert row["person_source"] == "private"
    assert row["review"]["reason_code"] != "suggested_private"
    assert row["posting_paid_through"] == {
        "account": "Private (Dirk)", "source": "private",
    }

    # nothing auto-books: the category judgment still applies, and once
    # categorized the decided row is ready
    _set_category(client, batch, doc)
    row = _grid(client, batch)["expenses"][0]
    assert row["review"]["state"] == "ready"

    # clearing the confirmation brings the suggestion back
    r = client.post(f"/api/runs/{batch}/expenses/{doc}/private",
                    json={"private": False})
    assert r.status_code == 200, r.text
    row = _grid(client, batch)["expenses"][0]
    assert row["private"] is False
    assert row["reimburse_to"] == ""
    assert row["person"] == ""
    assert row["review"]["reason_code"] == "suggested_private"


def test_prefill_rides_only_the_private_flow(client, monkeypatch):
    """The sender claim is offered ONLY where the owner sanctioned it:
    pre-filling reimburse_to on the private flow, for mailed receipts.
    It never attributes a card-resolved row and never fills person."""
    client.put("/api/settings", json={"cards": {
        "corp-1672": {"digits": ["1672"], "entity": "Corporate Services",
                      "person": "Nicolas"},
    }})
    _patch_ocr(
        monkeypatch,
        _extraction(payment_hint="Visa ...1672"),
        _extraction(vendor="Padaria", total="8.00",
                    payment_hint="Cartao de Credito"),
    )
    batch = _create_batch(client, n_files=2)
    grid = _grid(client, batch)
    by_vendor = {e["vendor"]["display"]: e for e in grid["expenses"]}

    # manual uploads: no submitted_by claim, so the prefill is blank
    assert by_vendor["Padaria"]["reimburse_to_prefill"] == ""

    store = RunStore(client._data_root / "recon-web.sqlite")
    try:
        run = store.get_run(batch)
        snapshot = dict(run.snapshot or {})
        snapshot["intake_provenance"] = {
            e["document_id"]: {"person": "Dirk", "source": "alias",
                               "address": "dirk.neumann@brisken.com",
                               "received_at": "2026-08-02T09:00:00"}
            for e in grid["expenses"]
        }
        store.update_run_snapshot(batch, snapshot)
    finally:
        store.close()

    grid = _grid(client, batch)
    by_vendor = {e["vendor"]["display"]: e for e in grid["expenses"]}
    # mailed + suggested: the claim is offered, shown as a claim
    assert by_vendor["Padaria"]["reimburse_to_prefill"] == "Dirk"
    assert by_vendor["Padaria"]["person"] == ""  # offered, never resolved
    # card-resolved row: NO prefill, and the card still owns the person
    assert by_vendor["Staples"]["reimburse_to_prefill"] == ""
    assert by_vendor["Staples"]["person"] == "Nicolas"


# ── the report and the export ────────────────────────────────────────


def test_private_rows_partition_into_reimbursements(client, monkeypatch):
    client.put("/api/settings", json={"cards": {
        "corp-1672": {"digits": ["1672"], "entity": "Corporate Services",
                      "person": "Nicolas"},
    }})
    _patch_ocr(
        monkeypatch,
        _extraction(payment_hint="Visa ...1672"),
        _extraction(vendor="Taxi Roma", total="18.00",
                    payment_hint="Cartao de Credito"),
    )
    batch = _create_batch(client, n_files=2)
    grid = _grid(client, batch)
    by_vendor = {e["vendor"]["display"]: e["document_id"]
                 for e in grid["expenses"]}
    for doc in by_vendor.values():
        _set_category(client, batch, doc)
    _confirm_private(client, batch, by_vendor["Taxi Roma"], person="Dirk")

    # CSV: one file, both rows, the private one saying so in both columns
    resp = client.get(f"/runs/{batch}/expenses.csv")
    assert resp.status_code == 200, resp.text
    rows = list(csv.reader(io.StringIO(resp.text)))[1:]
    by_csv_vendor = {r[COL_VENDOR]: r for r in rows}
    assert by_csv_vendor["Taxi Roma"][COL_ENTITY] == "(private expense)"
    assert by_csv_vendor["Taxi Roma"][COL_PAID_THROUGH] == "Private (Dirk)"
    assert by_csv_vendor["Staples"][COL_ENTITY] == "Corporate Services"

    # PDF: the company listing loses the private row; the section gains it
    pypdf = pytest.importorskip("pypdf")
    resp = client.get(f"/runs/{batch}/expense-report.pdf")
    assert resp.status_code == 200
    reader = pypdf.PdfReader(io.BytesIO(resp.content))
    first_page = reader.pages[0].extract_text() or ""
    assert "Reimbursements owed" in first_page
    assert "Reimburse Dirk" in first_page
    assert "Owed to Dirk: USD 18.00" in first_page
    # the listing head counts only company expenses now
    assert "1 expenses" in first_page
