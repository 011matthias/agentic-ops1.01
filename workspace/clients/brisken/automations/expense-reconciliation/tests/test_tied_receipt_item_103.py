"""Item 103 (item 72's matcher-level cause): one receipt on two charges.

Pass 1 sets a charge aside for a human pick when its top deterministic
candidates tie, and until now it left the tied RECEIPTS free, so pass 2 could
hand one of them to another charge as well. The stored numbers (the months
list, the re-match event, the claims table) counted that second pairing; the
page dropped it, and which charge kept the receipt depended on statement row
order rather than on score. Live August 2026 at round B: `0023` (Anthropic
52.59) stored as matched to ANTHROPIC 52.46 while the workbench showed it
held by the undecided ANTHROPIC 50.52 pick.

Two rules, and the counts:

* spoken for: a tied receipt holding a clean EXACT candidate on another
  charge does not sustain the tie (the charge goes to the assignment);
* held: a receipt a surviving tie lists is skipped by the assignment;
* the months list counts the reviewer's effective verdict, the page's own
  derivation, so the two screens report one number.

Route-level: every count assertion reads `GET /api/expense-batches` against
`GET /api/runs/{id}` after the real upload, statement attach and decision
routes.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt  # noqa: E402
from expense_recon.matching.deterministic import (  # noqa: E402
    MatchingConfig,
    match_month,
)
from expense_recon.matching.types import Receipt, Transaction  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from tests.test_feedback_notes_52_53_62_63 import (  # noqa: E402
    CARDS,
    _attach,
    _month,
    _wire,
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Copied rather than imported: a fixture imported across test modules is
    # an F811 redefinition in the CI lint.
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    with TestClient(create_app(tmp_path)) as c:
        yield c


def _receipt(vendor: str, total: str, day: str, reference: str = "") -> ExtractedReceipt:
    return ExtractedReceipt(
        date=day, total=total, currency="USD", vendor=vendor, reference=reference,
        line_items=(), confidence=0.9, notes="",
    )


def _view(client, batch) -> dict:
    resp = client.get(f"/api/runs/{batch}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _list_summary(client, batch) -> dict:
    resp = client.get("/api/expense-batches")
    assert resp.status_code == 200, resp.text
    row = next(b for b in resp.json()["batches"] if b["batch_id"] == batch)
    return row["summary"]


def _counts_agree(client, batch) -> dict:
    """The four charge counters, asserted equal on the list and the page."""
    page = _view(client, batch)["summary"]
    listed = _list_summary(client, batch)
    assert (
        listed["n_matched"],
        listed["n_review"],
        listed["n_unmatched_tx"],
        listed["n_refunds"],
    ) == (
        page["n_reconciled"],
        page["n_review"],
        page["n_unmatched_tx"],
        page["n_refunds"]
    ), (listed, page)
    return page


def _row(client, batch, amount: str) -> dict:
    rows = [r for r in _view(client, batch)["rows"] if r["amount"] == amount]
    assert len(rows) == 1, [r["amount"] for r in _view(client, batch)["rows"]]
    return rows[0]


def _held(view: dict) -> dict[str, list[str]]:
    """document_id -> the charges holding it, off the page's own rows."""
    out: dict[str, list[str]] = {}
    for row in view["rows"]:
        doc = row["chosen_document_id"]
        if doc:
            out.setdefault(doc, []).append(row["transaction_id"])
    return out


def _docs(client, batch) -> dict[str, str]:
    """vendor+total -> document_id, off the expense grid."""
    grid = client.get(f"/api/expense-batches/{batch}").json()
    return {
        f"{e['vendor']['display']} {e['amount']['total']}": e["document_id"]
        for e in grid["expenses"]
    }


# ── the matcher's two rules, on the shape the live month had ──────────────


def _tx(tx_id: str, amount: str, day: int) -> Transaction:
    return Transaction(
        transaction_id=tx_id,
        legal_entity_id="brisken-us",
        account_id="card-3645",
        transaction_date=date(2026, 8, day),
        posting_date=None,
        amount=Decimal(amount),
        transaction_currency="USD",
        account_card_currency="USD",
        vendor_from_statement="ANTHROPIC",
    )


def _rec(doc: str, total: str, day: int) -> Receipt:
    return Receipt(
        document_id=doc,
        legal_entity_id="brisken-us",
        detected_date=date(2026, 8, day),
        detected_total=Decimal(total),
        detected_currency="USD",
        detected_vendor="Anthropic",
    )


def test_a_tied_receipt_with_an_exact_charge_elsewhere_dissolves_the_tie():
    """The live shape: two receipts tie over one charge, and one of them holds
    the statement's own exact line somewhere else. It is spoken for, so it no
    longer sustains the tie; the charge goes to the assignment and takes the
    receipt that is actually free."""
    charges = [_tx("t_tie", "100.00", 10), _tx("t_exact", "99.00", 9)]
    receipts = [_rec("r_exact", "99.00", 9), _rec("r_free", "101.00", 11)]

    outcome = match_month(charges, receipts, MatchingConfig())

    assert not outcome.ambiguous, [
        (m.transaction_id, m.document_id) for m in outcome.ambiguous
    ]
    assert {(m.transaction_id, m.document_id) for m in outcome.matches} == {
        ("t_exact", "r_exact"),
        ("t_tie", "r_free"),
    }


def test_a_surviving_tie_holds_its_receipts_against_the_greedy_pass():
    """Neither tied receipt is spoken for, so the pick stands; the charge that
    scored one of them lower does not get to take it away in the meantime."""
    charges = [_tx("t_tie", "100.00", 10), _tx("t_rival", "98.50", 9)]
    receipts = [_rec("r_a", "99.00", 9), _rec("r_b", "101.00", 11)]

    outcome = match_month(charges, receipts, MatchingConfig())

    assert {(m.transaction_id, m.document_id) for m in outcome.ambiguous} == {
        ("t_tie", "r_a"),
        ("t_tie", "r_b"),
    }
    # The rival charge scored r_a too; the tie holds it, so nothing is matched
    # and no receipt is named on two charges.
    assert not outcome.matches, [
        (m.transaction_id, m.document_id) for m in outcome.matches
    ]
    assert outcome.unmatched_transactions == ["t_rival"]
    bound: dict[str, set[str]] = {}
    for bucket in (outcome.matches, outcome.judgment_required, outcome.ambiguous):
        for m in bucket:
            bound.setdefault(m.document_id, set()).add(m.transaction_id)
    assert all(len(txs) == 1 for txs in bound.values()), bound


def test_two_exact_twins_over_two_identical_charges_stay_a_human_pick():
    """The other live shape (July 2026: two GOOGLE Workspace 71.64 charges on
    07-01, two invoices): each receipt holds an exact candidate elsewhere, but
    so does its rival, so neither is spoken for and both charges wait for a
    human rather than being paired by row order."""
    charges = [_tx("t_a", "71.64", 10), _tx("t_b", "71.64", 10)]
    receipts = [_rec("r_a", "71.64", 10), _rec("r_b", "71.64", 10)]

    outcome = match_month(charges, receipts, MatchingConfig())

    assert {m.transaction_id for m in outcome.ambiguous} == {"t_a", "t_b"}
    assert not outcome.matches


# ── the same shapes through the routes, with the two screens compared ─────


def test_the_tie_and_the_exact_charge_both_land_and_the_screens_agree(
    client, monkeypatch
):
    """The August shape end to end: the page holds each receipt on exactly one
    charge, and the months list reports the page's counts."""
    client.put("/api/settings", json={"cards": CARDS})
    _wire(
        monkeypatch,
        _receipt("Anthropic", "99.00", "2026-08-09"),
        _receipt("Anthropic", "101.00", "2026-08-11"),
    )
    batch = _month(client, 2)
    _attach(client, batch, [
        ("3645", datetime(2026, 8, 10), "ANTHROPIC", "Sale", -100.00),
        ("3645", datetime(2026, 8, 9), "ANTHROPIC", "Sale", -99.00),
    ])

    view = _view(client, batch)
    held = _held(view)
    assert all(len(txs) == 1 for txs in held.values()), held
    assert len(held) == 2, held
    assert _row(client, batch, "100.00")["effective_bucket"] == "reconciled"
    assert _row(client, batch, "99.00")["effective_bucket"] == "reconciled"
    page = _counts_agree(client, batch)
    assert (page["n_reconciled"], page["n_review"], page["n_unmatched_tx"]) == (2, 0, 0)


def test_the_months_list_counts_a_pending_pick_the_way_the_page_does(
    client, monkeypatch
):
    """Two identical charges, two receipts that fit both: one charge waits on
    the pick and holds both receipts, the other has none left. Before item 103
    the list served the raw outcome and reported two charges in review while
    the page showed one in review and one unmatched."""
    client.put("/api/settings", json={"cards": CARDS})
    _wire(
        monkeypatch,
        _receipt("Google", "71.64", "2026-08-10", reference="5608449734"),
        _receipt("Google", "71.64", "2026-08-10", reference="5614551183"),
    )
    batch = _month(client, 2)
    _attach(client, batch, [
        ("2838", datetime(2026, 8, 10), "GOOGLE *Workspace", "Sale", -71.64),
        ("2838", datetime(2026, 8, 10), "GOOGLE *Workspace", "Sale", -71.64),
    ])

    view = _view(client, batch)
    buckets = sorted(r["effective_bucket"] for r in view["rows"])
    assert buckets == ["review", "unmatched"], [
        (r["vendor"], r["effective_bucket"]) for r in view["rows"]
    ]
    taken = next(r for r in view["rows"] if r["effective_bucket"] == "unmatched")
    assert taken["candidates"] and all(c.get("held_by") for c in taken["candidates"])
    page = _counts_agree(client, batch)
    assert (page["n_reconciled"], page["n_review"], page["n_unmatched_tx"]) == (0, 1, 1)
    # The event the notifier mails counts what the month it just rebuilt
    # shows, not the raw pairing the page drops.
    events = [
        e for e in client.get("/api/operator/state").json()["rematches"]
        if e["run_id"] == batch
    ]
    assert events, "the attach appended no re-match event"
    assert (
        events[-1]["n_matched"],
        events[-1]["n_review"],
        events[-1]["n_unmatched_tx"],
    ) == (page["n_reconciled"], page["n_review"], page["n_unmatched_tx"])


def test_a_reject_moves_the_months_list_too(client, monkeypatch):
    """The list reads the same effective verdict the page does, so a decision
    taken after the re-match moves both screens."""
    client.put("/api/settings", json={"cards": CARDS})
    _wire(monkeypatch, _receipt("Anthropic", "99.00", "2026-08-09"))
    batch = _month(client, 1)
    _attach(client, batch, [
        ("3645", datetime(2026, 8, 9), "ANTHROPIC", "Sale", -99.00),
    ])
    assert _counts_agree(client, batch)["n_reconciled"] == 1

    row = _row(client, batch, "99.00")
    resp = client.post(
        f"/api/runs/{batch}/decisions",
        json={"transaction_id": row["transaction_id"], "status": "rejected"},
    )
    assert resp.status_code == 200, resp.text

    page = _counts_agree(client, batch)
    assert (page["n_reconciled"], page["n_unmatched_tx"]) == (0, 1)
