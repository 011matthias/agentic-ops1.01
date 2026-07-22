"""The journal posts in the statement currency (2026-07-22).

Found in the hands-on test of the real April month: a 9.18 USD charge
matched to a 47.50 BRL receipt exported the receipt's BRL line totals into
the USD journal (debits 46.00, credit 46.00). Imported as-is that posts
roughly 5x the true amount, and the entry disagrees with the bank statement
that Chris treats as the source of truth.

The fix allocates the CHARGED amount across the receipt's lines, so the
debits always sum to what the bank actually took.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

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
from expense_recon.output.zoho_export import _posting_amounts, build_journal_rows

DEBIT, CREDIT = 5, 6
ACCOUNT, NOTES = 1, 4


def _cat(category: str = "Meals & Entertainment") -> Categorization:
    return Categorization(
        category=category,
        confidence=0.7,
        source=ClassificationSource.LINE,
        zoho_account=category,
    )


def _tx(amount: str, currency: str = "USD") -> Transaction:
    return Transaction(
        transaction_id="2838:91",
        legal_entity_id="Corporate Services",
        account_id="2838",
        transaction_date=date(2026, 4, 1),
        posting_date=date(2026, 4, 2),
        amount=Decimal(amount),
        transaction_currency=currency,
        account_card_currency="USD",
        vendor_from_statement="KI-MASSA",
    )


def _receipt(line_totals: list[str], currency: str = "BRL") -> Receipt:
    return Receipt(
        document_id="ER-00215#009",
        legal_entity_id="Corporate Services",
        detected_vendor="Padrao e Pastelaria Ki-Massa",
        detected_date=date(2026, 4, 1),
        detected_total=sum((Decimal(t) for t in line_totals), Decimal("0")),
        detected_currency=currency,
        line_items=tuple(
            LineItem(
                description=f"item {i}",
                line_total=Decimal(t),
                categorization=_cat(),
            )
            for i, t in enumerate(line_totals)
        ),
    )


def _rows(tx: Transaction, rec: Receipt) -> list[list[str]]:
    outcome = MatchOutcome(
        matches=[
            Match(
                transaction_id=tx.transaction_id,
                document_id=rec.document_id,
                match_type=MatchType.EXACT,
                confidence=0.99,
                score=0.99,
                reason="test fixture",
            )
        ],
    )
    return build_journal_rows(
        outcome,
        {tx.transaction_id: tx},
        {rec.document_id: rec},
    )


# ── the April regression ───────────────────────────────────────────────


def test_foreign_receipt_posts_the_charged_amount():
    """The real April pair: 9.18 USD charged, 47.50 BRL of receipt lines."""
    tx = _tx("9.18")
    rec = _receipt(["36.00", "11.50"])  # 47.50 BRL
    rows = _rows(tx, rec)

    debits = [Decimal(r[DEBIT]) for r in rows if r[DEBIT]]
    credits = [Decimal(r[CREDIT]) for r in rows if r[CREDIT]]
    assert sum(debits) == Decimal("9.18"), "debits must equal the bank charge"
    assert credits == [Decimal("9.18")], "one balancing credit, same amount"
    # No BRL figure may reach an amount column.
    assert Decimal("36.00") not in debits
    assert Decimal("47.50") not in debits


def test_receipt_amount_is_kept_in_notes_for_audit():
    rows = _rows(_tx("9.18"), _receipt(["36.00", "11.50"]))
    notes = " ".join(r[NOTES] for r in rows)
    assert "36.00 BRL" in notes and "11.50 BRL" in notes


def test_lines_that_undershoot_the_printed_total_still_balance():
    """April's parse produced lines summing 46.00 against a printed 47.50.
    The bank's number wins; the journal never disagrees with the statement."""
    rows = _rows(_tx("9.18"), _receipt(["36.00", "10.00"]))
    debits = [Decimal(r[DEBIT]) for r in rows if r[DEBIT]]
    assert sum(debits) == Decimal("9.18")


def test_zero_value_lines_are_dropped():
    """April's export carried 0.00-debit rows; they are noise in an import."""
    rows = _rows(_tx("9.18"), _receipt(["0.00", "46.00", "0.00"]))
    debit_rows = [r for r in rows if r[DEBIT]]
    assert len(debit_rows) == 1
    assert Decimal(debit_rows[0][DEBIT]) == Decimal("9.18")


# ── same-currency runs are untouched ───────────────────────────────────


def test_same_currency_receipt_is_unchanged():
    """A USD receipt whose lines already sum to the charge posts exactly as
    before: the allocation is the identity."""
    rows = _rows(_tx("50.00"), _receipt(["30.00", "20.00"], currency="USD"))
    debits = [Decimal(r[DEBIT]) for r in rows if r[DEBIT]]
    assert debits == [Decimal("30.00"), Decimal("20.00")]
    assert all("receipt" not in r[NOTES] for r in rows if r[DEBIT])


# ── allocation arithmetic ──────────────────────────────────────────────


def test_allocation_is_exact_despite_rounding():
    """Thirds of a cent-odd charge still sum to the charge exactly."""
    out = _posting_amounts([Decimal("1"), Decimal("1"), Decimal("1")], Decimal("10.00"))
    assert sum(out) == Decimal("10.00")
    assert all(a.as_tuple().exponent >= -2 for a in out), "cent-quantized"


def test_allocation_survives_all_zero_lines():
    out = _posting_amounts([Decimal("0"), Decimal("0")], Decimal("7.50"))
    assert sum(out) == Decimal("7.50")
