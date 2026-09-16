"""Changes in a month that did not stick (backlog item 70).

Criss, 2026-09-14, July: "Qdo entro na categoria e eu coloco a categoria
certa, nao acontece nada... permanece sem categoria mesmo dando refresh."
Three causes, each pinned here through the HTTP routes:

A. A category set on a needs-review row's candidate saved and never showed:
   the row's `posting_category` resolved from the HELD receipt, and a review
   row holds none until it is confirmed.
B. On a month with a statement the five expense-edit routes answered 400 ("a
   statement is attached"), so company, category, paid-through and cost
   center could be set nowhere on July or August. They reopen here, each
   followed by the re-match its edit needs, and every edit stays reversible.
C. Reclassify changed line 0 only (the SPA sent `line_index: 0`) and kept the
   account chosen for the old category.
"""
from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.matching.types import (  # noqa: E402
    Categorization,
    ClassificationSource,
    LineItem,
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.serialize import snapshot_to_dict  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
DOC_ID = "0000__a.jpg"
OFFICE = "Office Supplies & Consumables"
SOFTWARE = "Software & Subscriptions"
OFFICE_ACCOUNT = "6100 Office Supplies"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(vendor="Staples", total="42.50", day="2026-04-15"):
    return ExtractedReceipt(
        date=day, total=total, currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
    )


def _wire(monkeypatch, *extractions):
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    return mock


def _create_batch(client, label="April 2026"):
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": label},
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    batch_id = resp.json()["batch_id"]
    resp = client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("a.jpg", JPG, "application/octet-stream"))],
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return batch_id


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
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"


def _reconciling_month(client, monkeypatch):
    """One Staples receipt (42.50, 04-15) that pairs exactly with the
    statement's STAPLES NYC 42.50 charge, with the statement attached."""
    _wire(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    _attach(client, batch_id)
    assert _row(client, batch_id, "STAPLES")["chosen_document_id"] == DOC_ID
    return batch_id


def _row(client, batch_id, vendor):
    view = client.get(f"/api/runs/{batch_id}").json()
    return next(r for r in view["rows"] if vendor in r["vendor"])


def _expense(client, batch_id, doc_id=DOC_ID):
    rows = client.get(f"/api/expense-batches/{batch_id}").json()["expenses"]
    return next((r for r in rows if r["document_id"] == doc_id), None)


def _put(client, batch_id, field, value, doc_id=DOC_ID):
    return client.put(
        f"/api/runs/{batch_id}/expenses/{doc_id}",
        json={"field": field, "value": value},
    )


def _store(client):
    return RunStore(Path(client._data_root) / "recon-web.sqlite")


# ── B: the five routes are open on a statement month ─────────────────


def test_a_total_edit_moves_the_charge_and_clearing_it_brings_it_back(
    client, monkeypatch
):
    """The reversibility proof the reopening rests on. A corrected total that
    no longer fits the charge releases it; clearing the correction restores
    the EXTRACTED total -- in the grid, in the audit baseline, and in the pool
    the matcher sees -- and the charge pairs again."""
    batch_id = _reconciling_month(client, monkeypatch)

    resp = _put(client, batch_id, "total", "99.99")
    assert resp.status_code == 200, resp.text
    assert "error" not in resp.json()["rematch"], resp.json()
    staples = _row(client, batch_id, "STAPLES")
    assert staples["effective_bucket"] != "reconciled"
    assert staples["chosen_document_id"] != DOC_ID
    assert _expense(client, batch_id)["total"] == "99.99"

    resp = _put(client, batch_id, "total", "")
    assert resp.status_code == 200, resp.text
    assert "rematch" in resp.json()

    assert _expense(client, batch_id)["total"] == "42.50"
    with _store(client) as store:
        snapshot = store.get_run(batch_id).snapshot or {}
    baseline = {
        r["document_id"]: r for r in snapshot.get("extracted_receipts") or []
    }
    assert baseline[DOC_ID]["detected_total"] == "42.50"
    pool = {r["document_id"]: r for r in snapshot.get("receipts") or []}
    assert pool[DOC_ID]["detected_total"] == "42.50", (
        "the matcher's pool kept the cleared 99.99: the re-match baked from "
        "the already-baked snapshot instead of the extraction baseline"
    )
    staples = _row(client, batch_id, "STAPLES")
    assert staples["effective_bucket"] == "reconciled"
    assert staples["chosen_document_id"] == DOC_ID


def test_a_vendor_edit_keeps_the_extracted_vendor_as_the_audit_value(
    client, monkeypatch
):
    batch_id = _reconciling_month(client, monkeypatch)

    assert _put(client, batch_id, "vendor", "Staples Inc").status_code == 200
    vendor = _expense(client, batch_id)["vendor"]
    assert vendor["display"] == "Staples Inc"
    assert vendor["raw"] == "Staples"

    assert _put(client, batch_id, "vendor", "").status_code == 200
    vendor = _expense(client, batch_id)["vendor"]
    assert vendor["display"] == "Staples"
    assert vendor["source"] == "extraction"


def test_the_learning_harvest_keys_on_the_extracted_vendor_after_a_re_match(
    client, monkeypatch
):
    """Item 29's note: the harvest teaches corrections against the ORIGINAL
    extracted vendor. The edit route now re-matches, which bakes the edit
    into the pool; the harvest must still read the baseline."""
    batch_id = _reconciling_month(client, monkeypatch)

    resp = _put(client, batch_id, "vendor", "Staples Inc")
    assert resp.status_code == 200 and "rematch" in resp.json(), resp.text
    with _store(client) as store:
        pool = {
            r["document_id"]: r
            for r in (store.get_run(batch_id).snapshot or {})["receipts"]
        }
    assert pool[DOC_ID]["detected_vendor"] == "Staples Inc"  # baked

    resp = client.post(f"/api/runs/{batch_id}/commit-memory")
    assert resp.status_code == 200, resp.text
    memory = client.get("/api/memory").json()
    vendor_rows = [
        c for c in memory["field_corrections"] if c["field"] == "vendor"
    ]
    assert [c["vendor"] for c in vendor_rows] == ["staples"], vendor_rows
    assert vendor_rows[0]["value"] == "Staples Inc"


def test_an_entity_change_re_matches_and_can_release_the_charge(
    client, monkeypatch
):
    """Matching is entity-scoped: a receipt moved to another company no
    longer pairs with a Corporate Services charge, and moving it back
    pairs it again. The entity route reports its re-match."""
    batch_id = _reconciling_month(client, monkeypatch)

    resp = client.put(
        f"/api/runs/{batch_id}/expenses/{DOC_ID}/entity",
        json={"legal_entity": "Cloud Services"},
    )
    assert resp.status_code == 200, resp.text
    assert "rematch" in resp.json()
    assert _row(client, batch_id, "STAPLES")["chosen_document_id"] != DOC_ID

    resp = client.put(
        f"/api/runs/{batch_id}/expenses/{DOC_ID}/entity",
        json={"legal_entity": "Corporate Services"},
    )
    assert resp.status_code == 200, resp.text
    assert _row(client, batch_id, "STAPLES")["chosen_document_id"] == DOC_ID


def test_delete_on_a_statement_month_releases_the_charge(client, monkeypatch):
    batch_id = _reconciling_month(client, monkeypatch)

    resp = client.request("DELETE", f"/api/runs/{batch_id}/expenses/{DOC_ID}")
    assert resp.status_code == 200, resp.text
    assert "rematch" in resp.json()
    staples = _row(client, batch_id, "STAPLES")
    assert staples["effective_bucket"] == "unmatched"
    assert staples["chosen_document_id"] is None


def test_a_manual_add_joins_the_pool_and_pairs_with_its_exact_charge(
    client, monkeypatch
):
    batch_id = _reconciling_month(client, monkeypatch)

    resp = client.post(f"/api/runs/{batch_id}/expenses", json={
        "vendor": "Uber", "total": "22.30", "currency": "USD",
        "date": "2026-04-05",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    manual_id = body["document_id"]
    assert "rematch" in body and "error" not in body["rematch"], body
    uber = _row(client, batch_id, "UBER")
    assert uber["effective_bucket"] == "reconciled"
    assert uber["chosen_document_id"] == manual_id

    # And the add stays editable and reversible after it was baked: the
    # payload is its extraction.
    assert _put(client, batch_id, "total", "5.00", manual_id).status_code == 200
    assert _row(client, batch_id, "UBER")["chosen_document_id"] != manual_id
    assert _put(client, batch_id, "total", "", manual_id).status_code == 200
    assert _expense(client, batch_id, manual_id)["total"] == "22.30"
    assert _row(client, batch_id, "UBER")["chosen_document_id"] == manual_id


def test_a_manual_add_edited_before_the_statement_can_still_be_reverted(
    client, monkeypatch
):
    """A manual add is not in the extraction baseline when its first bake
    happens, so the baked copy (with the edit in it) is all the snapshot
    holds. Its payload is its extraction: clearing the edit has to rebuild
    from the payload, or the edited total sticks in the grid and the pool."""
    _wire(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    manual_id = client.post(f"/api/runs/{batch_id}/expenses", json={
        "vendor": "Uber", "total": "22.30", "currency": "USD",
        "date": "2026-04-05",
    }).json()["document_id"]
    assert _put(client, batch_id, "total", "5.00", manual_id).status_code == 200
    _attach(client, batch_id)
    assert _row(client, batch_id, "UBER")["chosen_document_id"] != manual_id

    resp = _put(client, batch_id, "total", "", manual_id)
    assert resp.status_code == 200 and "rematch" in resp.json(), resp.text
    assert _expense(client, batch_id, manual_id)["total"] == "22.30"
    assert _row(client, batch_id, "UBER")["chosen_document_id"] == manual_id


def test_only_fields_the_matcher_reads_pay_for_a_re_match(client, monkeypatch):
    """Booking fields (category, tax, private, ...) change what a row books
    to, never what it pairs with; a re-match for them costs time and model
    calls for nothing. An unchanged match field does not re-match either."""
    batch_id = _reconciling_month(client, monkeypatch)

    for field, value in (("category", OFFICE), ("tax", "3.00"),
                         ("tax_label", "VAT"), ("paid_through", "1010 Chase")):
        resp = _put(client, batch_id, field, value)
        assert resp.status_code == 200, (field, resp.text)
        assert "rematch" not in resp.json(), field
    resp = client.post(
        f"/api/runs/{batch_id}/expenses/{DOC_ID}/private",
        json={"private": True, "reimburse_to": "Dirk"},
    )
    assert resp.status_code == 200, resp.text
    assert "rematch" not in resp.json()

    assert "rematch" in _put(client, batch_id, "reference", "INV-1").json()
    assert "rematch" not in _put(client, batch_id, "reference", "INV-1").json()


def test_a_statement_less_month_is_unchanged(client, monkeypatch):
    """No statement, nothing to re-match: the reply has no `rematch` key."""
    _wire(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    resp = _put(client, batch_id, "total", "10.00")
    assert resp.status_code == 200, resp.text
    assert set(resp.json()) == {"ok", "summary"}


def test_every_other_validation_still_refuses(client, monkeypatch):
    batch_id = _reconciling_month(client, monkeypatch)

    assert _put(client, batch_id, "nope", "x").status_code == 400
    assert _put(client, batch_id, "category", "Not A Category").status_code == 400
    assert _put(client, batch_id, "cost_center", "Undefined").status_code == 400
    assert _put(client, batch_id, "private", "1").status_code == 400
    assert client.post(
        f"/api/runs/{batch_id}/expenses/{DOC_ID}/private",
        json={"private": True},
    ).status_code == 400
    assert client.request(
        "DELETE", f"/api/runs/{batch_id}/expenses/unknown.jpg"
    ).status_code == 404
    assert _put(client, batch_id, "category", OFFICE, "unknown.jpg").status_code == 404


def test_a_failed_re_match_rides_back_and_the_edit_stays(client, monkeypatch):
    batch_id = _reconciling_month(client, monkeypatch)
    import expense_recon.web.service as service

    def _boom(*a, **k):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(service, "rematch_month", _boom)
    resp = _put(client, batch_id, "total", "99.99")
    assert resp.status_code == 200, resp.text
    assert resp.json()["rematch"] == {"error": "RuntimeError: model unavailable"}
    assert _expense(client, batch_id)["total"] == "99.99"


# ── C: reclassify applies to the whole receipt and moves the account ──


def _registry_month(client, monkeypatch, *, attach: bool):
    """A Staples receipt the merchant registry categorizes with an account,
    so there is an account for a reclassification to leave behind."""
    assert client.put("/api/settings", json={"merchants": {
        "Staples": {"aliases": [], "category": OFFICE,
                    "zoho_account": OFFICE_ACCOUNT},
    }}).status_code == 200
    _wire(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    if attach:
        _attach(client, batch_id)
    posting = _expense(client, batch_id)["posting_category"]
    assert posting["category"] == OFFICE, posting
    return batch_id


def _csv_accounts(client, batch_id):
    resp = client.get(f"/runs/{batch_id}/expenses.csv")
    assert resp.status_code == 200, resp.text
    return [r["Expense Account"] for r in csv.DictReader(io.StringIO(resp.text))]


def test_reclassify_without_an_account_drops_the_old_categorys_account(
    client, monkeypatch
):
    """The iCloud row: category changed, account stayed. No deterministic
    category -> account map exists, so the export books the row to what it
    derives for a category with no account (the category label when no chart
    is wired; the unmapped placeholder with one), never the stale account."""
    batch_id = _registry_month(client, monkeypatch, attach=True)
    assert _csv_accounts(client, batch_id) == [OFFICE_ACCOUNT]

    resp = client.post(f"/api/runs/{batch_id}/categories", json={
        "document_id": DOC_ID, "category": SOFTWARE,
    })
    assert resp.status_code == 200, resp.text

    assert _csv_accounts(client, batch_id) == [SOFTWARE]
    posting = _row(client, batch_id, "STAPLES")["posting_category"]
    assert posting["category"] == SOFTWARE
    assert posting["zoho_account"] == ""


def test_re_sending_the_same_category_keeps_the_account(client, monkeypatch):
    batch_id = _registry_month(client, monkeypatch, attach=True)
    resp = client.post(f"/api/runs/{batch_id}/categories", json={
        "document_id": DOC_ID, "category": OFFICE,
    })
    assert resp.status_code == 200, resp.text
    assert _csv_accounts(client, batch_id) == [OFFICE_ACCOUNT]


def test_an_explicit_account_is_stored_with_the_category(client, monkeypatch):
    batch_id = _registry_month(client, monkeypatch, attach=True)
    resp = client.post(f"/api/runs/{batch_id}/categories", json={
        "document_id": DOC_ID, "category": SOFTWARE,
        "zoho_account": "6200 Software",
    })
    assert resp.status_code == 200, resp.text
    assert _csv_accounts(client, batch_id) == ["6200 Software"]


def test_the_grid_category_edit_follows_the_same_account_rule(
    client, monkeypatch
):
    batch_id = _registry_month(client, monkeypatch, attach=False)
    assert _put(client, batch_id, "category", SOFTWARE).status_code == 200
    assert _csv_accounts(client, batch_id) == [SOFTWARE]


def test_a_picked_account_does_not_survive_a_category_change_in_the_grid(
    client, monkeypatch
):
    """The PUT path used to carry the stored override's account onto the new
    category. An account picked for Office supplies is just as stale once the
    row is Software as the categorizer's own was."""
    batch_id = _registry_month(client, monkeypatch, attach=False)
    assert _put(client, batch_id, "zoho_account", "6150 Stationery").status_code == 200
    assert _csv_accounts(client, batch_id) == ["6150 Stationery"]

    assert _put(client, batch_id, "category", SOFTWARE).status_code == 200
    assert _csv_accounts(client, batch_id) == [SOFTWARE]


def _multi_line_month(client):
    """A seeded statement run whose one receipt has three categorized lines
    and pairs with its charge, the 33-line Lidl receipt in miniature."""
    lines = tuple(
        LineItem(
            description=f"item {i}", line_total=Decimal("10"),
            categorization=Categorization(
                category=OFFICE, zoho_account=OFFICE_ACCOUNT, confidence=0.9,
                source=ClassificationSource.LINE,
            ),
        )
        for i in range(3)
    )
    tx = Transaction(
        transaction_id="t1", legal_entity_id="le1", account_id="amex-usd",
        transaction_date=date(2026, 4, 7), posting_date=None,
        amount=Decimal("30"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement="LIDL",
    )
    rec = Receipt(
        document_id="lidl", legal_entity_id="le1",
        detected_date=date(2026, 4, 7), detected_total=Decimal("30"),
        detected_currency="USD", detected_vendor="Lidl", line_items=lines,
    )
    outcome = MatchOutcome(matches=[Match(
        transaction_id="t1", document_id="lidl", match_type=MatchType.EXACT,
        confidence=0.99, reason="exact", score=95,
    )])
    snapshot = snapshot_to_dict([tx], [rec], outcome, [])
    with _store(client) as store:
        store.create_run(
            run_id="lidl-run", created_at="2026-09-15T00:00:00", label="lidl",
            operator=None, summary={}, snapshot=snapshot, config={},
            work_dir=str(client._data_root), llm_enabled=False, has_coa=False,
        )
    return "lidl-run"


def test_reclassify_with_no_line_index_changes_every_line(client):
    run_id = _multi_line_month(client)
    resp = client.post(f"/api/runs/{run_id}/categories", json={
        "document_id": "lidl", "category": SOFTWARE,
    })
    assert resp.status_code == 200, resp.text
    row = client.get(f"/api/runs/{run_id}").json()["rows"][0]
    assert row["posting_category"]["category"] == SOFTWARE, row["posting_category"]
    (chosen,) = [c for c in row["candidates"] if c["is_chosen"]]
    assert {li["category"] for li in chosen["receipt"]["line_items"]} == {SOFTWARE}


def test_an_explicit_line_index_still_edits_one_line(client):
    run_id = _multi_line_month(client)
    resp = client.post(f"/api/runs/{run_id}/categories", json={
        "document_id": "lidl", "line_index": 0, "category": SOFTWARE,
    })
    assert resp.status_code == 200, resp.text
    row = client.get(f"/api/runs/{run_id}").json()["rows"][0]
    assert row["posting_category"]["category"] == f"{SOFTWARE}; {OFFICE}"


def test_reclassify_of_an_unknown_receipt_is_a_404_without_a_line_index(client):
    run_id = _multi_line_month(client)
    assert client.post(f"/api/runs/{run_id}/categories", json={
        "document_id": "nope", "category": SOFTWARE,
    }).status_code == 404
    assert client.post(f"/api/runs/{run_id}/categories", json={
        "document_id": "lidl", "line_index": "0", "category": SOFTWARE,
    }).status_code == 400


# ── A: a needs-review row shows the category the reviewer set ─────────


def _review_month(client):
    """A charge with two review candidates and no verdict, so the row holds
    no receipt: the July / August "needs review" shape."""
    tx = Transaction(
        transaction_id="t3", legal_entity_id="le1", account_id="amex-usd",
        transaction_date=date(2026, 4, 9), posting_date=None,
        amount=Decimal("20"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement="ICLOUD",
    )

    def _rec(doc_id):
        return Receipt(
            document_id=doc_id, legal_entity_id="le1",
            detected_date=date(2026, 4, 9), detected_total=Decimal("20"),
            detected_currency="USD", detected_vendor="iCloud",
            line_items=(LineItem(description="storage",
                                 line_total=Decimal("20")),),
        )

    outcome = MatchOutcome(ambiguous=[
        Match(transaction_id="t3", document_id="first",
              match_type=MatchType.AMBIGUOUS, confidence=0.6,
              reason="two candidates", requires_review=True, score=61),
        Match(transaction_id="t3", document_id="second",
              match_type=MatchType.AMBIGUOUS, confidence=0.55,
              reason="two candidates", requires_review=True, score=55),
    ])
    snapshot = snapshot_to_dict([tx], [_rec("first"), _rec("second")], outcome, [])
    with _store(client) as store:
        store.create_run(
            run_id="review-run", created_at="2026-09-15T00:00:00",
            label="review", operator=None, summary={}, snapshot=snapshot,
            config={}, work_dir=str(client._data_root), llm_enabled=False,
            has_coa=False,
        )
    return "review-run"


def test_a_category_set_on_a_review_candidate_shows_on_the_row(client):
    run_id = _review_month(client)
    before = client.get(f"/api/runs/{run_id}").json()
    (row,) = before["rows"]
    assert row["effective_bucket"] == "review"
    assert row["posting_category"] is None
    assert "posting_category_proposed" not in row

    resp = client.post(f"/api/runs/{run_id}/categories", json={
        "document_id": "second", "category": SOFTWARE,
    })
    assert resp.status_code == 200, resp.text

    after = client.get(f"/api/runs/{run_id}").json()
    (row,) = after["rows"]
    assert row["posting_category"]["category"] == SOFTWARE, (
        "the reviewer's category saved and never showed on the review row"
    )
    assert row["posting_category_proposed"] is True
    # Display only: the row still holds nothing and nothing counted moved.
    assert row["chosen_document_id"] is None
    assert row["review"] == before["rows"][0]["review"]
    for key in ("n_undecided", "n_unmapped", "n_review", "ready_to_post"):
        if key in before["summary"]:
            assert after["summary"][key] == before["summary"][key], key


def test_a_confirmed_row_never_carries_the_proposed_flag(client):
    run_id = _multi_line_month(client)
    client.post(f"/api/runs/{run_id}/categories", json={
        "document_id": "lidl", "category": SOFTWARE,
    })
    row = client.get(f"/api/runs/{run_id}").json()["rows"][0]
    assert "posting_category_proposed" not in row
