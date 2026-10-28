"""Item X1 (owner, 2026-09-18): the statement description counts, and a
receipt whose card cannot be identified is still matched on the other
criteria, with the tool saying so.

Two rules, both in `matching/deterministic.py`:

* `strip_reference_tokens` / `MatchingConfig.vendor_ignore_reference_tokens`:
  an order or invoice number Chase prints inside the description
  ("Microsoft-G173514057") is a reference, not a merchant word, so it no
  longer halves the merchant score of a pair whose words agree. Live July
  2026: the Microsoft invoice printing G173514057 scored 0.50 and sat below
  the self-confirm floor (75) for a click it did not need.
* `card_evidence` + `no_card_rival_review`: the no-card fallback, defined in
  one place. A receipt naming no card (nothing printed, picked, assigned or
  remembered) is matched across every card's charges; when another
  deterministic candidate for the same receipt sits on a DIFFERENT card and
  is not spoken for elsewhere, the pair keeps its match but asks for review
  and carries `review_code` `no_card_rival_on_other_card`. A receipt that
  names its card is never reviewed for that reason.

Route-level tests read `GET /api/runs/{id}` after the real upload and
statement attach, through `rematch_month`.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

import pytest

from expense_recon.matching.deterministic import (
    CHARGE_CARD_EVIDENCE,
    NO_CARD_RIVAL_REVIEW,
    RECEIPT_CARD_EVIDENCE,
    MatchingConfig,
    _vendor_score,
    card_evidence,
    match_month,
    strip_reference_tokens,
)
from expense_recon.matching.types import Match, MatchType, Receipt, Transaction
from expense_recon.web.serialize import match_from_dict, match_to_dict


def _tx(tx_id, amount, day, vendor="LOVABLE", card="2838", account_id="card-2838"):
    return Transaction(
        transaction_id=tx_id,
        legal_entity_id="",
        account_id=account_id,
        transaction_date=date(2026, 8, day),
        posting_date=None,
        amount=Decimal(amount),
        transaction_currency="USD",
        account_card_currency="USD",
        vendor_from_statement=vendor,
        card_last4=card,
    )


def _receipt(doc, amount, day, vendor="Lovable", payment_mode=None, **kw):
    return Receipt(
        document_id=doc,
        legal_entity_id="",
        detected_date=date(2026, 8, day),
        detected_total=Decimal(amount),
        detected_currency="USD",
        detected_vendor=vendor,
        payment_mode=payment_mode,
        **kw,
    )


# ── the description's reference tokens are not merchant words ────────────


def test_strip_reference_tokens_keeps_the_merchant_words():
    assert strip_reference_tokens("Microsoft-G173514057") == "microsoft"
    assert strip_reference_tokens("LinkedIn SN P3078900231") == "linkedin sn"
    assert strip_reference_tokens("CASUALFOOD  2640 8") == "casualfood 8"
    assert strip_reference_tokens("7-ELEVEN B013") == "7 eleven"
    # two digits are a word ("BASE44" is the brand), and a description that
    # is only a number still compares as itself
    assert strip_reference_tokens("BASE44") == "base44"
    assert strip_reference_tokens("1251593381") == "1251593381"
    assert strip_reference_tokens(None) == ""


@pytest.mark.parametrize(
    ("statement", "receipt", "floor"),
    [
        ("Microsoft-G173514057", "Microsoft Corporation", 0.99),
        ("CASUALFOOD  2640 8", "casualfood gmbh", 0.99),
        ("7-ELEVEN B013", "7-ELEVEN", 0.99),
    ],
)
def test_a_reference_inside_the_description_does_not_dilute_the_merchant_score(
    statement, receipt, floor
):
    tx = _tx("t1", "718.20", 26, vendor=statement)
    rec = _receipt("r1", "718.20", 26, vendor=receipt)
    assert _vendor_score(tx, rec, MatchingConfig()) >= floor
    raw = _vendor_score(tx, rec, MatchingConfig(vendor_ignore_reference_tokens=False))
    assert raw < 0.75, raw  # the pre-X1 score, below the self-confirm floor


def test_a_brand_with_two_digits_is_still_a_word():
    tx = _tx("t1", "50.00", 22, vendor="BASE44")
    rec = _receipt("r1", "50.00", 22, vendor="Lovable Labs Incorporated")
    assert _vendor_score(tx, rec, MatchingConfig()) < 0.5


# ── card evidence, defined once ──────────────────────────────────────────


def test_card_evidence_names_where_each_side_got_its_card():
    row = _tx("t1", "25.00", 5)
    account_default = _tx("t2", "25.00", 5, card=None, account_id="1176")
    no_card = _tx("t3", "25.00", 5, card=None, account_id="card")
    none = _receipt("r0", "25.00", 5)
    printed = _receipt("r1", "25.00", 5, payment_mode="Visa ...9693")
    picked = replace(none, card_scope_keys=("2838",), card_scope_source="override")
    remembered = replace(none, card_scope_keys=("2838",), card_scope_source="learned")
    assert card_evidence(row, none) == ("none", "row")
    assert card_evidence(account_default, none) == ("none", "account")
    assert card_evidence(no_card, none) == ("none", "none")
    assert card_evidence(row, printed) == ("printed", "row")
    assert card_evidence(row, picked) == ("override", "row")
    assert card_evidence(row, remembered) == ("learned", "row")
    for src in ("override", "hint", "learned", "printed", "none"):
        assert src in RECEIPT_CARD_EVIDENCE
    assert CHARGE_CARD_EVIDENCE == ("row", "account", "none")


def _two_cards(receipt_kw=None, second_card="3645"):
    txs = [
        _tx("on-2838", "25.00", 5, card="2838"),
        _tx("on-other", "25.00", 6, card=second_card),
    ]
    rec = _receipt("doc", "25.00", 5, **(receipt_kw or {}))
    return txs, rec


def test_a_no_card_receipt_with_a_rival_on_another_card_asks_for_review():
    txs, rec = _two_cards()
    out = match_month(txs, [rec], MatchingConfig())
    held = next(m for m in out.matches if m.document_id == "doc")
    assert held.transaction_id == "on-2838"
    assert held.match_type is MatchType.EXACT
    assert held.requires_review is True
    assert held.review_code == NO_CARD_RIVAL_REVIEW
    assert "names no card" in held.reason and "3645" in held.reason, held.reason
    assert held.confidence == MatchingConfig().high_confidence  # rank untouched


def test_a_receipt_that_names_its_card_is_not_reviewed_for_that_reason():
    txs, rec = _two_cards({"payment_mode": "Visa ...2838"})
    out = match_month(txs, [rec], MatchingConfig())
    held = next(m for m in out.matches if m.document_id == "doc")
    assert held.transaction_id == "on-2838"
    assert held.requires_review is False and held.review_code == ""


def test_a_rival_on_the_same_card_does_not_flag():
    txs, rec = _two_cards(second_card="2838")
    out = match_month(txs, [rec], MatchingConfig())
    held = next(m for m in out.matches if m.document_id == "doc")
    assert held.requires_review is False and held.review_code == ""


def test_a_rival_spoken_for_by_exact_evidence_elsewhere_does_not_flag():
    txs, rec = _two_cards()
    theirs = _receipt("theirs", "25.00", 6, payment_mode="Visa ...3645")
    out = match_month(txs, [rec, theirs], MatchingConfig())
    held = next(m for m in out.matches if m.document_id == "doc")
    assert held.transaction_id == "on-2838"
    assert held.requires_review is False and held.review_code == ""
    assert next(m for m in out.matches if m.document_id == "theirs").transaction_id == "on-other"


def test_the_clause_has_a_knob_and_the_fallback_does_not():
    txs, rec = _two_cards()
    out = match_month(txs, [rec], MatchingConfig(no_card_rival_review=False))
    held = next(m for m in out.matches if m.document_id == "doc")
    assert held.transaction_id == "on-2838"  # still matched across the cards
    assert held.requires_review is False and held.review_code == ""


def test_the_tuning_file_knows_both_knobs():
    cfg = MatchingConfig.from_dict(
        {"vendor_ignore_reference_tokens": False, "no_card_rival_review": False}
    )
    assert cfg.vendor_ignore_reference_tokens is False
    assert cfg.no_card_rival_review is False


def test_review_code_survives_the_snapshot_and_old_snapshots_read_empty():
    m = Match(
        transaction_id="t", document_id="d", match_type=MatchType.EXACT,
        confidence=0.99, reason="x", requires_review=True,
        review_code=NO_CARD_RIVAL_REVIEW,
    )
    assert match_from_dict(match_to_dict(m)).review_code == NO_CARD_RIVAL_REVIEW
    old = match_to_dict(m)
    del old["review_code"]
    assert match_from_dict(old).review_code == ""


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


def test_route_a_no_card_receipt_between_two_cards_is_matched_and_asks_for_review(
    client, monkeypatch
):
    client.put("/api/settings", json={"cards": CARDS})
    _wire(monkeypatch, _extraction("Lovable", "25.00", "2026-08-05"))
    batch = _month(client, 1)
    _attach(client, batch, [
        ("2838", datetime(2026, 8, 5), "LOVABLE", "Sale", -25.00),
        ("3645", datetime(2026, 8, 6), "LOVABLE", "Sale", -25.00),
    ])
    doc = _expense(client, batch, "Lovable")["document_id"]
    on_2838 = _row(client, batch, "2838")
    assert on_2838["chosen_document_id"] == doc
    assert on_2838["effective_bucket"] == "reconciled"
    cand = next(c for c in on_2838["candidates"] if c["document_id"] == doc)
    assert cand["requires_review"] is True
    assert cand["review_code"] == "no_card_rival_on_other_card"
    assert cand["card_evidence"] == {"receipt": "none", "charge": "row"}
    assert "names no card" in cand["reason"], cand["reason"]
    assert _row(client, batch, "3645")["chosen_document_id"] is None
    # the pair never confirms itself (item 76)
    assert on_2838["review"]["state"] != "ready" or on_2838["status"] == "pending"


def test_route_a_receipt_naming_its_card_carries_the_evidence_and_no_code(
    client, monkeypatch
):
    client.put("/api/settings", json={"cards": CARDS})
    _wire(monkeypatch, _extraction("Lovable", "25.00", "2026-08-05", payment_hint="Visa ...2838"))
    batch = _month(client, 1)
    _attach(client, batch, [
        ("2838", datetime(2026, 8, 5), "LOVABLE", "Sale", -25.00),
        ("3645", datetime(2026, 8, 6), "LOVABLE", "Sale", -25.00),
    ])
    doc = _expense(client, batch, "Lovable")["document_id"]
    on_2838 = _row(client, batch, "2838")
    assert on_2838["chosen_document_id"] == doc
    cand = next(c for c in on_2838["candidates"] if c["document_id"] == doc)
    assert cand["requires_review"] is False
    assert "review_code" not in cand
    assert cand["card_evidence"] == {"receipt": "hint", "charge": "row"}


def test_route_the_description_reference_no_longer_dilutes_the_merchant(
    client, monkeypatch
):
    client.put("/api/settings", json={"cards": CARDS})
    _wire(monkeypatch, _extraction("Microsoft Corporation", "718.20", "2026-08-26"))
    batch = _month(client, 1)
    _attach(client, batch, [
        ("2838", datetime(2026, 8, 26), "Microsoft-G173514057", "Sale", -718.20),
    ])
    doc = _expense(client, batch, "Microsoft Corporation")["document_id"]
    row = _row(client, batch, "2838")
    cand = next(c for c in row["candidates"] if c["document_id"] == doc)
    assert cand["vendor_pct"] == 100, cand
    assert cand["card_evidence"] == {"receipt": "none", "charge": "row"}
