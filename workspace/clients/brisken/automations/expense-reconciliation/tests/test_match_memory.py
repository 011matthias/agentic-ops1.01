"""Match-pass memory consult (PR 2c): a confirmed vendor alias pins the
tie-break to the right (truncated-name) receipt, and a per-merchant FX mean
re-centers the FX triage score WITHIN the band. Neither changes which bucket
a pair lands in — the reconciliation guarantee is untouched."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from expense_recon.learning import LearningStore, MatchMemory, normalize_vendor
from expense_recon.matching.deterministic import MatchingConfig, match_month
from expense_recon.matching.types import MatchType, Receipt, Transaction

LE = "brisken-llc"
D = date(2026, 4, 1)


def _tx(tx_id, vendor, amount, ccy="USD"):
    return Transaction(
        transaction_id=tx_id, legal_entity_id=LE, account_id="card",
        transaction_date=D, posting_date=None, amount=Decimal(amount),
        transaction_currency=ccy, account_card_currency="USD",
        vendor_from_statement=vendor,
    )


def _rcpt(doc, vendor, amount, ccy="USD"):
    return Receipt(
        document_id=doc, legal_entity_id=LE, detected_date=D,
        detected_total=Decimal(amount), detected_currency=ccy,
        detected_vendor=vendor,
    )


def _matched_doc(outcome, tx_id):
    return next((m.document_id for m in outcome.matches if m.transaction_id == tx_id), None)


def test_alias_breaks_tie_to_the_correct_receipt():
    # Same amount + date: both receipts are EXACT candidates for the charge,
    # so the vendor signal decides. The decoy "Mega Center" scores higher on
    # fuzzy text than the truly-correct but heavily abbreviated "MCC Ltda".
    tx = _tx("t1", "MEGA CENTE CONSTR", "100.00")
    correct = _rcpt("A", "MCC Ltda", "100.00")
    decoy = _rcpt("B", "Mega Center", "100.00")

    # Without memory, fuzzy text picks the decoy.
    assert _matched_doc(match_month([tx], [correct, decoy]), "t1") == "B"

    # The confirmed alias pins the real receipt's vendor score to 1.0.
    cfg = MatchingConfig(vendor_aliases=frozenset({
        (LE, normalize_vendor("MEGA CENTE CONSTR"), normalize_vendor("MCC Ltda"))
    }))
    assert _matched_doc(match_month([tx], [correct, decoy], cfg), "t1") == "A"


def test_merchant_fx_mean_recenters_score_not_bucket():
    # USD 110 charge vs EUR 100 receipt -> implied 1.10, inside the EUR band
    # but below its midpoint (1.225). A learned mean of 1.10 re-centers the
    # score upward; the bucket stays FX_JUDGMENT either way.
    tx = _tx("t1", "Hostaria", "110.00", ccy="USD")
    r = _rcpt("d1", "Hostaria", "100.00", ccy="EUR")

    base = match_month([tx], [r]).judgment_required[0]
    cfg = MatchingConfig(merchant_fx={
        (LE, normalize_vendor("Hostaria"), "EUR", "USD"): Decimal("1.10")
    })
    learned = match_month([tx], [r], cfg).judgment_required[0]

    assert learned.score > base.score
    assert base.match_type is MatchType.FX_JUDGMENT
    assert learned.match_type is MatchType.FX_JUDGMENT


def test_default_config_has_empty_memory():
    cfg = MatchingConfig()
    assert cfg.vendor_aliases == frozenset()
    assert dict(cfg.merchant_fx) == {}


def test_guarantee_holds_with_memory():
    txs = [_tx("t1", "Acme", "50.00"), _tx("t2", "Beta", "75.00")]
    rs = [_rcpt("d1", "Acme", "50.00")]  # only t1 has a receipt
    cfg = MatchingConfig(vendor_aliases=frozenset({
        (LE, normalize_vendor("Acme"), normalize_vendor("Acme"))
    }))
    out = match_month(txs, rs, cfg)
    bucketed = (
        {m.transaction_id for m in out.matches}
        | set(out.unmatched_transactions)
        | {m.transaction_id for m in out.judgment_required}
        | {m.transaction_id for m in out.ambiguous}
    )
    assert bucketed == {"t1", "t2"}


def test_match_memory_from_store(tmp_path):
    db = tmp_path / "learning.sqlite"
    with LearningStore(db) as s:
        s.record_vendor_alias(LE, "mega cente constr", "mcc ltda", "t", "r")
        s.record_merchant_fx(LE, "hostaria", "EUR", "USD", Decimal("1.10"), "t", "r")
        s.record_merchant_fx(LE, "hostaria", "EUR", "USD", Decimal("1.20"), "t", "r")
    mm = MatchMemory.from_db_path(db)
    assert (LE, "mega cente constr", "mcc ltda") in mm.vendor_aliases
    assert mm.merchant_fx[(LE, "hostaria", "EUR", "USD")] == Decimal("1.15")  # mean
