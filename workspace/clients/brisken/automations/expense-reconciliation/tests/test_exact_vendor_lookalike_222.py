"""Item 222 step 6 (item 133 rules 1 and 3): an exact pair whose merchant
disagrees is held for review when a same-amount receipt is left over.

`MatchingConfig.exact_vendor_lookalike_guard`, the card-named sibling of the
D5 no-card guard: when the matcher's CHOSEN pair is a same-currency EXACT,
its receipt names a card, the merchant words disagree (`_vendor_score` below
0.5) and ANOTHER receipt of the same total and currency ends up unmatched,
the pair keeps its assignment but lands in `judgment_required` with
`review_code` `exact_vendor_disagrees`. Otherwise nothing changes.

A floor alone cannot be drawn: July's Network Solutions 7.98 (0.46) and the
Google twins (0.42) are labelled right, August `0025` (0.40) wrong. Measured
2026-09-27 on live July, August, September and the six bundles: two chosen
pairs qualify on merchant and card (Network Solutions, September SendGrid
89.95 at 0.32), neither has a same-amount receipt left over, so 0 move.

Route-level tests read `GET /api/runs/{id}` after the real upload and
statement attach, through `rematch_month`.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import json
from pathlib import Path

import pytest

from expense_recon.matching.deterministic import (
    EXACT_VENDOR_LOOKALIKE_REVIEW,
    NO_CARD_VENDOR_REVIEW,
    MatchingConfig,
    match_month,
)
from expense_recon.matching.types import Receipt, Transaction


def _tx(tx_id, amount, day, vendor, card="3645"):
    return Transaction(
        transaction_id=tx_id,
        legal_entity_id="",
        account_id=f"card-{card}",
        transaction_date=date(2026, 8, day),
        posting_date=None,
        amount=Decimal(amount),
        transaction_currency="USD",
        account_card_currency="USD",
        vendor_from_statement=vendor,
        card_last4=card,
    )


def _receipt(doc, amount, day, vendor, payment_mode="Visa ...3645", currency="USD"):
    return Receipt(
        document_id=doc,
        legal_entity_id="",
        detected_date=date(2026, 8, day),
        detected_total=Decimal(amount),
        detected_currency=currency,
        detected_vendor=vendor,
        payment_mode=payment_mode,
    )


def _pairs(ms):
    return [(m.transaction_id, m.document_id) for m in ms]


# ── the matcher ──────────────────────────────────────────────────────────


def test_a_waiting_same_amount_receipt_sends_the_disagreeing_pair_to_review():
    # BASE44 50.00 holds a card-named Lovable invoice; a Base44 receipt of the
    # same 50.00 sits 20 days away with no charge of its own.
    tx = _tx("t1", "50.00", 22, "BASE44")
    chosen = _receipt("r1", "50.00", 22, "Lovable Labs Incorporated")
    waiting = _receipt("r2", "50.00", 2, "Base44 Inc")
    out = match_month([tx], [chosen, waiting], MatchingConfig())
    assert out.matches == []
    assert _pairs(out.judgment_required) == [("t1", "r1")]
    m = out.judgment_required[0]
    assert m.requires_review is True
    assert m.review_code == EXACT_VENDOR_LOOKALIKE_REVIEW == "exact_vendor_disagrees"
    assert "merchants differ" in m.reason, m.reason
    assert "same amount is still unmatched (Base44 Inc 50.00 USD on 2026-08-02)" in m.reason
    # the pair keeps its evidence and its assignment; the waiting receipt
    # stays unmatched, the charge is not
    assert m.amount_score == 1.0 and m.vendor_score < 0.5
    assert out.unmatched_receipts == ["r2"]
    assert out.unmatched_transactions == []


def test_without_a_waiting_receipt_the_pair_books_as_before():
    # live July: WEB*NETWORKSOLUTIONS 7.98 at vendor 0.46, labelled right
    tx = _tx("t1", "7.98", 5, "WEB*NETWORKSOLUTIONS")
    rec = _receipt("r1", "7.98", 5, "Network Solutions, LLC")
    out = match_month([tx], [rec], MatchingConfig())
    assert _pairs(out.matches) == [("t1", "r1")]
    assert out.matches[0].vendor_score < 0.5
    assert out.matches[0].review_code == ""
    assert out.judgment_required == []


def test_a_same_amount_receipt_that_found_its_own_charge_does_not_count():
    t1 = _tx("t1", "50.00", 22, "BASE44")
    t2 = _tx("t2", "50.00", 10, "ANTHROPIC")
    r1 = _receipt("r1", "50.00", 22, "Lovable Labs Incorporated")
    r2 = _receipt("r2", "50.00", 10, "Anthropic, PBC")
    out = match_month([t1, t2], [r1, r2], MatchingConfig())
    assert sorted(_pairs(out.matches)) == [("t1", "r1"), ("t2", "r2")]
    assert out.judgment_required == []


@pytest.mark.parametrize("waiting", [
    _receipt("r2", "50.00", 2, "Base44 Inc", currency="EUR"),  # other currency
    _receipt("r2", "51.00", 2, "Base44 Inc"),  # other amount
])
def test_only_the_same_total_in_the_same_currency_counts(waiting):
    tx = _tx("t1", "50.00", 22, "BASE44")
    rec = _receipt("r1", "50.00", 22, "Lovable Labs Incorporated")
    out = match_month([tx], [rec, waiting], MatchingConfig())
    assert _pairs(out.matches) == [("t1", "r1")]


def test_an_agreeing_merchant_books_even_with_a_waiting_receipt():
    tx = _tx("t1", "50.00", 22, "LOVABLE")
    rec = _receipt("r1", "50.00", 22, "Lovable Labs Incorporated")
    waiting = _receipt("r2", "50.00", 2, "Base44 Inc")
    out = match_month([tx], [rec, waiting], MatchingConfig())
    assert _pairs(out.matches) == [("t1", "r1")]
    assert out.matches[0].vendor_score >= 0.5


def test_a_no_card_receipt_stays_with_the_d5_guard():
    tx = _tx("t1", "50.00", 22, "BASE44")
    rec = _receipt("r1", "50.00", 22, "Lovable Labs Incorporated", payment_mode=None)
    waiting = _receipt("r2", "50.00", 2, "Base44 Inc", payment_mode=None)
    out = match_month([tx], [rec, waiting], MatchingConfig())
    assert [m.review_code for m in out.judgment_required] == [NO_CARD_VENDOR_REVIEW]


def test_the_knob_turns_it_off_and_the_asset_carries_it_on():
    tx = _tx("t1", "50.00", 22, "BASE44")
    rec = _receipt("r1", "50.00", 22, "Lovable Labs Incorporated")
    waiting = _receipt("r2", "50.00", 2, "Base44 Inc")
    out = match_month([tx], [rec, waiting], MatchingConfig(exact_vendor_lookalike_guard=False))
    assert _pairs(out.matches) == [("t1", "r1")]
    assert out.judgment_required == []
    assert MatchingConfig().exact_vendor_lookalike_guard is True
    assert MatchingConfig.from_dict(
        {"exact_vendor_lookalike_guard": False}
    ).exact_vendor_lookalike_guard is False
    asset = Path(__file__).resolve().parents[1] / "config" / "match-tuning.json"
    assert json.loads(asset.read_text(encoding="utf-8"))["exact_vendor_lookalike_guard"] is True


# ── route-level, through rematch_month ───────────────────────────────────

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web.app import create_app  # noqa: E402
from tests.test_feedback_notes_52_53_62_63 import (  # noqa: E402
    CARDS,
    _attach,
    _expense,
    _extraction,
    _month,
    _wire,
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    with TestClient(create_app(tmp_path)) as c:
        yield c


def _row(client, batch, card: str) -> dict:
    view = client.get(f"/api/runs/{batch}").json()
    rows = [r for r in view["rows"] if card in r["coverage_key"]]
    assert len(rows) == 1, [(r["vendor"], r["coverage_key"]) for r in view["rows"]]
    return rows[0]


def test_route_the_pair_sits_in_review_and_names_the_waiting_receipt(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARDS})
    _wire(
        monkeypatch,
        _extraction("Lovable Labs Incorporated", "50.00", "2026-08-22", "Visa ...3645"),
        _extraction("Base44 Inc", "50.00", "2026-08-02", "Visa ...3645"),
    )
    batch = _month(client, 2)
    _attach(client, batch, [("3645", datetime(2026, 8, 22), "BASE44", "Sale", -50.00)])
    doc = _expense(client, batch, "Lovable Labs Incorporated")["document_id"]

    row = _row(client, batch, "3645")
    assert row["effective_bucket"] == "review", row["effective_bucket"]
    assert row["status"] == "pending"
    cand = row["candidates"][0]
    assert cand["document_id"] == doc
    assert cand["review_code"] == "exact_vendor_disagrees", cand
    assert cand["match_type"] == "exact"
    assert cand["requires_review"] is True
    assert cand["vendor_pct"] < 50
    assert cand["card_evidence"]["receipt"] != "none", cand["card_evidence"]
    review = row["review"]
    assert review["cause"] == "merchant_disagrees", review
    assert review["cause_detail"]["document_id"] == doc
    assert review["cause_detail"]["same_amount_receipt"] == "Base44 Inc 50.00 USD on 2026-08-02"


def test_route_without_the_waiting_receipt_the_pair_stays_reconciled(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARDS})
    _wire(
        monkeypatch,
        _extraction("Lovable Labs Incorporated", "50.00", "2026-08-22", "Visa ...3645"),
    )
    batch = _month(client, 1)
    _attach(client, batch, [("3645", datetime(2026, 8, 22), "BASE44", "Sale", -50.00)])
    doc = _expense(client, batch, "Lovable Labs Incorporated")["document_id"]

    row = _row(client, batch, "3645")
    assert row["effective_bucket"] == "reconciled", row["effective_bucket"]
    assert row["chosen_document_id"] == doc
    cand = next(c for c in row["candidates"] if c["document_id"] == doc)
    assert "review_code" not in cand
