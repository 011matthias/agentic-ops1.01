"""learn_from_run capture tests (PR 2a) — proves the explicit-only rule:
alias + FX come from confirmed matches, merchant category from explicit
reclassifications, and nothing is taught from an unconfirmed match or a
category the reviewer never touched."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from expense_recon.learning import LearningStore, learn_from_run, normalize_vendor
from expense_recon.matching.types import (
    Categorization,
    ClassificationSource,
    LineItem,
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)

LE = "brisken-llc"


def _tx(tx_id, vendor, amount="10.00", ccy="USD"):
    return Transaction(
        transaction_id=tx_id, legal_entity_id=LE, account_id="card",
        transaction_date=date(2026, 4, 1), posting_date=None,
        amount=Decimal(amount), transaction_currency=ccy,
        account_card_currency="USD", vendor_from_statement=vendor,
    )


def _rcpt(doc_id, vendor, total="10.00", ccy="USD", line_items=()):
    return Receipt(
        document_id=doc_id, legal_entity_id=LE, detected_date=date(2026, 4, 1),
        detected_total=Decimal(total), detected_currency=ccy,
        detected_vendor=vendor, line_items=line_items,
    )


def _line(desc, total, category, source=ClassificationSource.LINE):
    return LineItem(
        description=desc, line_total=Decimal(total),
        categorization=Categorization(
            category=category, zoho_account=None, confidence=0.9,
            source=source, reasoning="",
        ),
    )


def _match(tx_id, doc_id, mt=MatchType.EXACT):
    return Match(transaction_id=tx_id, document_id=doc_id, match_type=mt,
                 confidence=0.99, reason="x")


def _store(tmp_path):
    return LearningStore(tmp_path / "learning.sqlite")


def test_confirmed_match_writes_alias(tmp_path):
    tx = _tx("t1", "MEGA CENTE CONSTR")
    r = _rcpt("d1", "Mega Center Comercio Construcao")
    outcome = MatchOutcome(matches=[_match("t1", "d1")])
    with _store(tmp_path) as s:
        summ = learn_from_run(
            s, transactions=[tx], receipts=[r], outcome=outcome,
            confirmed_tx_ids={"t1"}, category_overrides={},
            source_run="run-1", now_iso="t",
        )
        aliases = s.get_vendor_aliases(LE)
    assert summ.vendor_aliases == 1
    assert aliases[0].stmt_vendor_norm == normalize_vendor("MEGA CENTE CONSTR")
    assert aliases[0].receipt_vendor_norm == normalize_vendor("Mega Center Comercio Construcao")


def test_unconfirmed_match_teaches_nothing(tmp_path):
    tx = _tx("t1", "MEGA CENTE CONSTR")
    r = _rcpt("d1", "Mega Center Comercio")
    outcome = MatchOutcome(matches=[_match("t1", "d1")])
    with _store(tmp_path) as s:
        summ = learn_from_run(
            s, transactions=[tx], receipts=[r], outcome=outcome,
            confirmed_tx_ids=set(), category_overrides={},  # NOT confirmed
            source_run="run-1", now_iso="t",
        )
        assert s.get_vendor_aliases(LE) == []
    assert summ.vendor_aliases == 0
    assert summ.confirmed_pairs == 0


def test_confirmed_fx_match_writes_fx_sample(tmp_path):
    tx = _tx("t1", "Hostaria Pantheon", amount="116.00", ccy="USD")
    r = _rcpt("d1", "Hostaria Pantheon", total="100.00", ccy="EUR")
    outcome = MatchOutcome(matches=[_match("t1", "d1", MatchType.FX_JUDGMENT)])
    with _store(tmp_path) as s:
        summ = learn_from_run(
            s, transactions=[tx], receipts=[r], outcome=outcome,
            confirmed_tx_ids={"t1"}, category_overrides={},
            source_run="run-1", now_iso="t",
        )
        fx = s.get_merchant_fx(LE, normalize_vendor("Hostaria Pantheon"))
    assert summ.merchant_fx == 1
    assert fx[0].samples == (Decimal("1.16"),)


def test_category_learned_from_explicit_override(tmp_path):
    r = _rcpt("d1", "Amazon", line_items=(_line("Chair", "150.00", "Equipment & Hardware"),))
    overrides = {("d1", 0): {"category": "Office Supplies & Consumables", "zoho_account": None}}
    with _store(tmp_path) as s:
        summ = learn_from_run(
            s, transactions=[], receipts=[r], outcome=MatchOutcome(),
            confirmed_tx_ids=set(), category_overrides=overrides,
            source_run="run-1", now_iso="t",
        )
        mc = s.get_merchant_category(LE, normalize_vendor("Amazon"))
    assert summ.merchant_categories == 1
    assert mc.category == "Office Supplies & Consumables"


def test_mixed_category_override_is_skipped(tmp_path):
    # Same vendor, two lines reclassified to different categories -> we must
    # not teach a wrong single mapping; skip and count it.
    r = _rcpt("d1", "Amazon", line_items=(
        _line("Chair", "150.00", None), _line("Beans", "30.00", None),
    ))
    overrides = {
        ("d1", 0): {"category": "Equipment & Hardware", "zoho_account": None},
        ("d1", 1): {"category": "Meals & Entertainment", "zoho_account": None},
    }
    with _store(tmp_path) as s:
        summ = learn_from_run(
            s, transactions=[], receipts=[r], outcome=MatchOutcome(),
            confirmed_tx_ids=set(), category_overrides=overrides,
            source_run="run-1", now_iso="t",
        )
        assert s.get_merchant_category(LE, normalize_vendor("Amazon")) is None
    assert summ.merchant_categories == 0
    assert summ.skipped_mixed_category == 1


def test_confirmed_match_does_not_learn_unreviewed_category(tmp_path):
    # A confirmed match teaches the alias, but NOT the LLM's category guess
    # on that receipt — only an explicit reclassification teaches a category.
    tx = _tx("t1", "Adobe")
    r = _rcpt("d1", "Adobe", line_items=(_line("Creative Cloud", "10.00", "Software & Subscriptions"),))
    outcome = MatchOutcome(matches=[_match("t1", "d1")])
    with _store(tmp_path) as s:
        summ = learn_from_run(
            s, transactions=[tx], receipts=[r], outcome=outcome,
            confirmed_tx_ids={"t1"}, category_overrides={},
            source_run="run-1", now_iso="t",
        )
        assert s.get_merchant_category(LE, normalize_vendor("Adobe")) is None
    assert summ.vendor_aliases == 1
    assert summ.merchant_categories == 0
