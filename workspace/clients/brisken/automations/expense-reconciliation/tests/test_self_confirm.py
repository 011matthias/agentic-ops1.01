"""Whose turn a row is, and clean exact pairs confirm themselves (item 76).

Owner notes #38 / #39 (July): "why do you need manual confirming on a date,
vendor and amount match?" and "things that are reconciled and there are no
mismatches should not need confirmation". Note #49: a yellow row already
booked in the workbook was offered Reject / Confirm. `rows[].status` read
`pending` on all 223 live rows, so the page asked about finished work as
loudly as about the 13 rows that were really the reviewer's to decide.

Owner rulings 2026-09-16: exact pairs only, vendor agreement at 75 or better.

Route-level. The self-confirmation is pinned through the caller that runs it
(`rematch_month`, reached by attaching a statement and by adding a receipt),
and the reversal through the decisions route a reviewer uses.
"""
from __future__ import annotations

import copy
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.matching.types import (  # noqa: E402
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)
from expense_recon.web import service  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.serialize import snapshot_to_dict  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
DOC_ID = "0000__a.jpg"
OFFICE = "Office Supplies & Consumables"
OFFICE_ACCOUNT = "6100 Office Supplies"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(vendor="STAPLES NYC", total="42.50", day="2026-04-15"):
    return ExtractedReceipt(
        date=day, total=total, currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
    )


def _job_done(client, resp):
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"


def _add_receipt(client, batch_id, name="a.jpg"):
    # distinct bytes per file: identical content is refused as a re-upload
    body = JPG + name.encode()
    _job_done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (name, body, "application/octet-stream"))],
    ))


def _month(client, monkeypatch, *extractions, registry=True):
    """One receipt (42.50, 04-15) that pairs exactly with the example
    statement's STAPLES NYC 42.50 charge, statement attached. With `registry`
    the merchant book categorizes it, a trusted tier, so the row's review
    state is `ready`. Extra extractions are consumed by later adds."""
    if registry:
        assert client.put("/api/settings", json={"merchants": {
            "Staples": {"aliases": ["STAPLES NYC"], "category": OFFICE,
                        "zoho_account": OFFICE_ACCOUNT},
        }}).status_code == 200
    mock = MockLLMClient(
        extraction_responses=list(extractions or (_extraction(),))
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": "April 2026"},
    )
    _job_done(client, resp)
    batch_id = resp.json()["batch_id"]
    _add_receipt(client, batch_id)
    _job_done(client, client.post(
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
    ))
    return batch_id


def _view(client, batch_id):
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _row(view, vendor="STAPLES"):
    return next(r for r in view["rows"] if vendor in r["vendor"])


def _decide(client, batch_id, tx_id, status, doc=None):
    resp = client.post(f"/api/runs/{batch_id}/decisions", json={
        "transaction_id": tx_id, "status": status, "chosen_document_id": doc,
    })
    assert resp.status_code == 200, resp.text


# ── the rule, through the re-match that runs it ─────────────────────


def test_a_clean_exact_pair_confirms_itself_when_the_statement_is_matched(
    client, monkeypatch
):
    """Same amount, same day, one candidate, category ready, vendor 100: the
    tool confirms it and says so, and the month has nothing left to decide."""
    batch_id = _month(client, monkeypatch)
    view = _view(client, batch_id)
    row = _row(view)
    (cand,) = row["candidates"]
    assert (cand["match_type"], cand["vendor_pct"]) == ("exact", 100)

    assert row["status"] == "confirmed"
    assert row["chosen_document_id"] == DOC_ID
    assert row["turn"] == "confirmed"
    assert row["decided_by"] == "tool"
    assert row["decided_rule"] == "exact_vendor_75"
    assert view["summary"]["n_self_confirmed"] == 1
    assert view["summary"]["n_undecided"] == 0


def test_a_vendor_that_does_not_agree_keeps_asking(client, monkeypatch):
    """"Staples" against "STAPLES NYC" scores 50: amount and date agree, the
    vendor does not reach 75, so it stays the reviewer's call (the
    WEB*NETWORKSOLUTIONS shape on July)."""
    batch_id = _month(client, monkeypatch, _extraction(vendor="STAPLES"))
    view = _view(client, batch_id)
    row = _row(view)
    assert row["candidates"][0]["vendor_pct"] < service.SELF_CONFIRM_VENDOR_FLOOR
    assert row["status"] == "pending"
    assert row["turn"] == "decide"
    assert "decided_by" not in row and "decided_rule" not in row
    assert view["summary"]["n_self_confirmed"] == 0
    assert view["summary"]["n_undecided"] == 1


def test_an_exact_pair_with_no_category_keeps_asking(client, monkeypatch):
    """The ruling is about the MATCH; a receipt with no category is not
    ready to post, so the tool does not confirm it for the reviewer."""
    batch_id = _month(client, monkeypatch, registry=False)
    row = _row(_view(client, batch_id))
    assert row["review"]["state"] == "pick"
    assert (row["status"], row["turn"]) == ("pending", "decide")


def test_a_reviewer_takes_it_back_and_the_next_rematch_leaves_it(
    client, monkeypatch
):
    """Reversible: a reviewer resets the self-confirmed row to pending, and
    a later re-match (a receipt arriving) does not confirm it again."""
    batch_id = _month(
        client, monkeypatch, _extraction(),
        _extraction(vendor="Unrelated GmbH", total="9.99", day="2026-04-02"),
    )
    tx_id = _row(_view(client, batch_id))["transaction_id"]
    _decide(client, batch_id, tx_id, "pending")
    row = _row(_view(client, batch_id))
    assert (row["status"], row["turn"]) == ("pending", "decide")
    assert "decided_by" not in row

    _add_receipt(client, batch_id, name="b.jpg")
    view = _view(client, batch_id)
    assert any(r["vendor"] == "Unrelated GmbH" for r in view["unmatched_receipts"]), (
        "the add must have re-matched the month"
    )
    row = _row(view)
    assert (row["status"], row["turn"]) == ("pending", "decide")
    assert view["summary"]["n_self_confirmed"] == 0


def _correct_vendor(client, batch_id, value="Office Depot"):
    """A reviewer corrects the receipt's vendor; a match field, so the
    edit route re-matches the month (item 70)."""
    resp = client.put(
        f"/api/runs/{batch_id}/expenses/{DOC_ID}",
        json={"field": "vendor", "value": value},
    )
    assert resp.status_code == 200, resp.text


def test_a_pair_that_stops_agreeing_loses_the_tools_confirmation(
    client, monkeypatch
):
    """The tool's verdict is re-judged on every re-match: once the receipt's
    vendor no longer agrees, the confirmation goes back to pending and the
    row is the reviewer's again."""
    batch_id = _month(client, monkeypatch)
    assert _row(_view(client, batch_id))["decided_by"] == "tool"

    _correct_vendor(client, batch_id)
    view = _view(client, batch_id)
    row = _row(view)
    (cand,) = row["candidates"]
    assert cand["match_type"] == "exact"
    assert cand["vendor_pct"] < service.SELF_CONFIRM_VENDOR_FLOOR
    assert (row["status"], row["turn"]) == ("pending", "decide")
    assert "decided_by" not in row
    assert view["summary"]["n_self_confirmed"] == 0


def test_a_reviewers_confirmation_survives_the_same_change(client, monkeypatch):
    """The tool only ever withdraws its own verdicts."""
    batch_id = _month(client, monkeypatch)
    tx_id = _row(_view(client, batch_id))["transaction_id"]
    _decide(client, batch_id, tx_id, "confirmed", DOC_ID)
    assert _row(_view(client, batch_id))["decided_by"] == "reviewer"

    _correct_vendor(client, batch_id)
    row = _row(_view(client, batch_id))
    assert (row["status"], row["decided_by"]) == ("confirmed", "reviewer")


# ── whose turn every row is ─────────────────────────────────────────


def _tx(tx_id, day, vendor, amount="10.00", entry_status=None):
    return Transaction(
        transaction_id=tx_id, legal_entity_id="le1", account_id="card-2838",
        transaction_date=date(2026, 7, day), posting_date=None,
        amount=Decimal(amount), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement=vendor,
        entry_status=entry_status,
    )


def _rec(doc_id, day, vendor, amount="10.00"):
    return Receipt(
        document_id=doc_id, legal_entity_id="le1",
        detected_date=date(2026, 7, day), detected_total=Decimal(amount),
        detected_currency="USD", detected_vendor=vendor,
        detected_reference="R" + doc_id,
    )


def _pair(tx_id, doc_id, match_type=MatchType.EXACT):
    review = match_type is not MatchType.EXACT
    return Match(
        transaction_id=tx_id, document_id=doc_id, match_type=match_type,
        confidence=0.6 if review else 0.99, reason="seeded",
        requires_review=review, score=60 if review else 95,
        amount_score=1.0, date_score=1.0, vendor_score=1.0,
    )


def test_turn_names_whose_move_every_row_is(client):
    """`decide` on exactly the rows `n_undecided` counts; a booked row never
    asks; a verdict names who gave it; no pairing is nothing to do."""
    txs = [
        _tx("t-match", 1, "ALPHA"),
        _tx("t-review", 2, "BRAVO"),
        _tx("t-posted", 3, "CHARLIE", entry_status="posted"),
        _tx("t-none", 4, "DELTA"),
        _tx("t-credit", 5, "PAYMENT THANK YOU", amount="-500.00"),
        _tx("t-confirmed", 6, "ECHO"),
        _tx("t-rejected", 7, "FOXTROT"),
    ]
    recs = [
        _rec("r-match", 1, "Alpha"), _rec("r-review", 2, "Bravo"),
        _rec("r-posted", 3, "Charlie"), _rec("r-confirmed", 6, "Echo"),
        _rec("r-rejected", 7, "Foxtrot"),
    ]
    outcome = MatchOutcome(
        matches=[
            _pair("t-match", "r-match"), _pair("t-posted", "r-posted"),
            _pair("t-confirmed", "r-confirmed"), _pair("t-rejected", "r-rejected"),
        ],
        judgment_required=[_pair("t-review", "r-review", MatchType.FX_JUDGMENT)],
        refunds=["t-credit"],
        unmatched_transactions=["t-none"], unmatched_receipts=[],
    )
    store = RunStore(client._data_root / "recon-web.sqlite")
    try:
        store.create_run(
            run_id="turns", created_at="2026-08-01T00:00:00+00:00",
            label="July 2026", operator=None, summary={},
            snapshot=snapshot_to_dict(txs, recs, outcome, []), config={},
            work_dir=str(client._data_root), llm_enabled=False, has_coa=False,
        )
    finally:
        store.close()
    _decide(client, "turns", "t-confirmed", "confirmed", "r-confirmed")
    _decide(client, "turns", "t-rejected", "rejected")

    view = _view(client, "turns")
    by_id = {r["transaction_id"]: r for r in view["rows"]}
    assert {tx: r["turn"] for tx, r in by_id.items()} == {
        "t-match": "decide",
        "t-review": "decide",
        "t-posted": "posted",
        "t-none": "none",
        "t-credit": "none",
        "t-confirmed": "confirmed",
        "t-rejected": "rejected",
    }
    assert sum(r["turn"] == "decide" for r in view["rows"]) == (
        view["summary"]["n_undecided"]
    )
    assert by_id["t-confirmed"]["decided_by"] == "reviewer"
    assert by_id["t-rejected"]["decided_by"] == "reviewer"
    for tx in ("t-match", "t-review", "t-posted", "t-none", "t-credit"):
        assert "decided_by" not in by_id[tx], by_id[tx]
        assert "decided_rule" not in by_id[tx], by_id[tx]
    for tx in ("t-confirmed", "t-rejected"):
        assert "decided_rule" not in by_id[tx], by_id[tx]


# ── the store never lets the tool overwrite a person ────────────────


def test_the_tool_never_overwrites_a_persons_verdict(tmp_path):
    store = RunStore(tmp_path / "s.sqlite")
    try:
        now = "2026-09-16T20:00:00+00:00"
        store.set_decision("r", "reviewed", "pending", None, now)
        store.set_decision("r", "confirmed-by-person", "confirmed", "d1", now)
        store.set_disposition("r", "seeded", "business", now)
        store.set_tool_decision("r", "by-tool", "confirmed", "d3", now, "rule")

        assert not store.set_tool_decision("r", "reviewed", "confirmed", "d", now, "rule")
        assert not store.set_tool_decision("r", "confirmed-by-person", "pending", None, now, None)
        assert store.set_tool_decision("r", "seeded", "confirmed", "d2", now, "rule")
        assert store.set_tool_decision("r", "fresh", "confirmed", "d4", now, "rule")
        assert store.set_tool_decision("r", "by-tool", "pending", None, now, None)

        got = store.get_decisions("r")
        assert (got["reviewed"].status, got["reviewed"].decided_by) == ("pending", "reviewer")
        assert (got["confirmed-by-person"].status, got["confirmed-by-person"].chosen_document_id) == ("confirmed", "d1")
        assert (got["seeded"].status, got["seeded"].decided_by, got["seeded"].rule) == ("confirmed", "tool", "rule")
        assert got["seeded"].disposition == "business", "a tool write keeps the disposition"
        assert (got["by-tool"].status, got["by-tool"].decided_by, got["by-tool"].rule) == ("pending", "tool", None)
    finally:
        store.close()


# ── the rule's edges, on a row the view would build ─────────────────


def _qualifying_row():
    return {
        "transaction_id": "t1", "status": "pending", "turn": "decide",
        "effective_bucket": "reconciled", "review": {"state": "ready"},
        "candidates": [{
            "document_id": "d1", "is_chosen": True, "match_type": "exact",
            "requires_review": False, "vendor_pct": 75,
        }],
    }


@pytest.mark.parametrize("change", [
    ("vendor_pct", 74),
    ("match_type", "probable"),
    ("match_type", "fx_reference"),
    ("requires_review", True),
    ("is_chosen", False),
    ("from_batch", {"kind": "adjacent"}),
    ("held_by", {"transaction_id": "t2"}),
    ("rejected", True),
    ("row:turn", "posted"),
    ("row:review", {"state": "check"}),
    ("row:status", "confirmed"),
    ("row:effective_bucket", "review"),
    ("two_candidates", None),
])
def test_each_condition_of_the_rule_is_required(change):
    assert service.self_confirm_pairs({"rows": [_qualifying_row()]}) == {"t1": "d1"}
    row = _qualifying_row()
    key, value = change
    if key == "two_candidates":
        row["candidates"].append(dict(row["candidates"][0], document_id="d2", is_chosen=False))
    elif key.startswith("row:"):
        row[key[4:]] = value
    else:
        row["candidates"][0][key] = value
    assert service.self_confirm_pairs({"rows": [copy.deepcopy(row)]}) == {}, change
