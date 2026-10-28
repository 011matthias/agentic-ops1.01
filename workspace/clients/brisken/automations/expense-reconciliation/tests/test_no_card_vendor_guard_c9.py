"""Item 204 step 6 (case 9, build 2; owner D5, 2026-09-25): a receipt with no
card evidence is not booked to a charge that does not carry its vendor.

`MatchingConfig.no_card_vendor_guard`: when the matcher's CHOSEN pair has
`card_evidence` receipt "none" and the merchant words disagree
(`_vendor_score` below 0.5, the API's `vendor_pct` 50), the pair keeps its
assignment but lands in `judgment_required` with `review_code`
`no_card_vendor_disagrees`, so it sits in review, never in reconciled, and
lends no card. Live August 2026: BASE44 50.00 on 3645 held a Lovable invoice
(40%) and gave that row the wrong card and company.

"A blank prompts Criss to look; a wrong card silently books the receipt to
the wrong entity and the wrong person" (item 173). The cost the owner
accepted: right pairs whose charge prints a CNPJ descriptor also take a click.

Route-level tests read `GET /api/runs/{id}` and `GET /api/expense-batches/{id}`
after the real upload and statement attach, through `rematch_month`.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from expense_recon.matching.deterministic import (
    NO_CARD_RIVAL_REVIEW,
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


def _receipt(doc, amount, day, vendor, payment_mode=None, **kw):
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


# ── the matcher ──────────────────────────────────────────────────────────


def test_a_no_card_pair_whose_vendor_disagrees_goes_to_review_not_matches():
    # live August 2026: BASE44 50.00 on 3645 holding the Lovable invoice
    tx = _tx("t1", "50.00", 22, "BASE44")
    rec = _receipt("r1", "50.00", 22, "Lovable Labs Incorporated")
    out = match_month([tx], [rec], MatchingConfig())
    assert out.matches == []
    assert [(m.transaction_id, m.document_id) for m in out.judgment_required] == [("t1", "r1")]
    m = out.judgment_required[0]
    assert m.requires_review is True
    assert m.review_code == NO_CARD_VENDOR_REVIEW == "no_card_vendor_disagrees"
    assert "names no card" in m.reason and "(40%)" in m.reason, m.reason
    # the pair keeps its evidence: still the exact amount, still the top
    # candidate, so a person confirms it in one click
    assert m.amount_score == 1.0 and m.vendor_score < 0.5
    # consumed on both sides exactly as before: nothing falls to unmatched
    assert out.unmatched_transactions == [] and out.unmatched_receipts == []


def test_a_no_card_pair_whose_vendor_agrees_stays_booked():
    tx = _tx("t1", "50.00", 22, "LOVABLE")
    rec = _receipt("r1", "50.00", 22, "Lovable Labs Incorporated")
    out = match_month([tx], [rec], MatchingConfig())
    assert [m.document_id for m in out.matches] == ["r1"]
    assert out.judgment_required == []
    assert out.matches[0].review_code == ""


def test_a_receipt_printing_its_card_is_untouched_whatever_the_vendor():
    tx = _tx("t1", "50.00", 22, "BASE44")
    printed = _receipt("r1", "50.00", 22, "Lovable Labs Incorporated",
                       payment_mode="Visa ending in 3645")
    out = match_month([tx], [printed], MatchingConfig())
    assert [m.document_id for m in out.matches] == ["r1"]
    assert out.judgment_required == []
    # a printed number no card on the statement carries is card evidence too
    other = _receipt("r2", "50.00", 22, "Lovable Labs Incorporated",
                     payment_mode="Visa ending in 9999")
    out = match_month([tx], [other], MatchingConfig())
    assert out.judgment_required == [] and len(out.matches) == 1


def test_a_card_resolved_for_the_receipt_is_card_evidence():
    tx = _tx("t1", "50.00", 22, "BASE44")
    learned = _receipt("r1", "50.00", 22, "Lovable Labs Incorporated",
                       card_scope_keys=("3645",), card_scope_source="learned")
    out = match_month([tx], [learned], MatchingConfig())
    assert [m.document_id for m in out.matches] == ["r1"]
    assert out.judgment_required == []


def test_the_guard_reads_only_the_chosen_pair():
    # the receipt's own merchant wins its charge; the stranger charge on the
    # same amount is left with nothing, as before, and nothing is reviewed
    own = _tx("t1", "50.00", 22, "LOVABLE", card="2838")
    stranger = _tx("t2", "50.00", 22, "BASE44", card="3645")
    rec = _receipt("r1", "50.00", 22, "Lovable Labs Incorporated")
    out = match_month([own, stranger], [rec], MatchingConfig())
    assert [(m.transaction_id, m.document_id) for m in out.matches] == [("t1", "r1")]
    assert out.judgment_required == []
    assert out.unmatched_transactions == ["t2"]


def test_an_existing_rival_code_is_kept_and_the_pair_still_goes_to_review():
    tx = _tx("t1", "25.00", 5, "BASE44", card="2838")
    rival = _tx("t2", "25.00", 6, "BASE44", card="3645")
    rec = _receipt("r1", "25.00", 5, "Lovable")
    out = match_month([tx, rival], [rec], MatchingConfig())
    assert out.matches == []
    assert len(out.judgment_required) == 1
    m = out.judgment_required[0]
    assert m.review_code == NO_CARD_RIVAL_REVIEW
    assert "merchant words do not match" in m.reason, m.reason


def test_the_knob_off_restores_booking():
    tx = _tx("t1", "50.00", 22, "BASE44")
    rec = _receipt("r1", "50.00", 22, "Lovable Labs Incorporated")
    out = match_month([tx], [rec], MatchingConfig(no_card_vendor_guard=False))
    assert [m.document_id for m in out.matches] == ["r1"]
    assert out.judgment_required == []
    assert out.matches[0].review_code == ""


def test_the_judgment_layer_leaves_the_guarded_pair_as_built():
    # every re-match runs the FX judge over `judgment_required`; the guarded
    # pair is not an FX pair and must not be re-judged, re-worded or unbound
    from expense_recon.cli import _apply_judgment
    from expense_recon.llm.client import MockLLMClient

    tx = _tx("t1", "50.00", 22, "BASE44")
    rec = _receipt("r1", "50.00", 22, "Lovable Labs Incorporated")
    out = match_month([tx], [rec], MatchingConfig())
    before = list(out.judgment_required)
    mock = MockLLMClient()
    _apply_judgment(out, {"t1": tx}, {"r1": rec}, mock,
                    suggest_floor=0.2, cfg=MatchingConfig())
    assert out.judgment_required == before
    assert out.judgment_required[0].review_code == NO_CARD_VENDOR_REVIEW
    assert [c for c in mock.calls if c[0] == "judge_fx_match"] == []


def test_the_knob_is_file_loadable_and_on_in_the_shipped_asset():
    import json
    from pathlib import Path

    assert MatchingConfig().no_card_vendor_guard is True
    assert MatchingConfig.from_dict({"no_card_vendor_guard": False}).no_card_vendor_guard is False
    asset = Path(__file__).resolve().parents[1] / "config" / "match-tuning.json"
    assert json.loads(asset.read_text(encoding="utf-8"))["no_card_vendor_guard"] is True


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


def test_route_the_disagreeing_pair_sits_in_review_and_lends_no_card(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARDS})
    _wire(monkeypatch, _extraction("Lovable Labs Incorporated", "50.00", "2026-08-22"))
    batch = _month(client, 1)
    _attach(client, batch, [("3645", datetime(2026, 8, 22), "BASE44", "Sale", -50.00)])
    doc = _expense(client, batch, "Lovable Labs Incorporated")["document_id"]

    row = _row(client, batch, "3645")
    assert row["effective_bucket"] == "review", row["effective_bucket"]
    assert row["status"] == "pending"
    # the pair is the charge's top candidate, so one click confirms it
    cand = row["candidates"][0]
    assert cand["document_id"] == doc
    assert cand["review_code"] == "no_card_vendor_disagrees", cand
    assert cand["requires_review"] is True
    # the matcher's pair as built, not an FX verdict from the judgment layer
    # (the wired mock would answer p=0.90 "same purchase" for any FX pair)
    assert cand["match_type"] == "exact", cand["match_type"]
    assert "names no card" in cand["reason"], cand["reason"]
    assert "FX judgment" not in cand["reason"]
    assert cand["vendor_pct"] < 50
    assert cand["card_evidence"] == {"receipt": "none", "charge": "row"}

    exp = _expense(client, batch, "Lovable Labs Incorporated")
    assert exp["card"] is None, exp["card"]
    assert exp.get("card_source") != "settled_charge", exp.get("card_source")


def test_route_an_agreeing_pair_stays_reconciled_and_lends_its_card(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARDS})
    _wire(monkeypatch, _extraction("Lovable Labs Incorporated", "50.00", "2026-08-22"))
    batch = _month(client, 1)
    _attach(client, batch, [("3645", datetime(2026, 8, 22), "LOVABLE", "Sale", -50.00)])
    doc = _expense(client, batch, "Lovable Labs Incorporated")["document_id"]

    row = _row(client, batch, "3645")
    assert row["effective_bucket"] == "reconciled"
    assert row["chosen_document_id"] == doc
    cand = next(c for c in row["candidates"] if c["document_id"] == doc)
    assert "review_code" not in cand
    exp = _expense(client, batch, "Lovable Labs Incorporated")
    assert exp["card"]["key"] == "corp-3645"
