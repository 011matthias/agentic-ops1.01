"""The "open" tile and the chase list agree in words (item 260, note #132).

2026-10-29, August: the "Charges without a receipt" tile read 43 open and the
chase list 42. The difference was ANNUAL MEMBERSHIP FEE (a fee line): open for
a person, not a purchase, so nobody chases a receipt for it. The tile and the
list were both right; nothing on screen said what separated them.
`n_charges_open_no_receipt_due` is that remainder, so open = chase + this.
"""
from __future__ import annotations

from expense_recon.web.month_readiness import completeness_counts


def _row(row_type: str, **extra) -> dict:
    return {"effective_bucket": "unmatched", "section": "noreceipt",
            "row_type": row_type, **extra}


def test_a_fee_line_is_open_but_not_chased():
    rows = [
        _row("purchase"),
        _row("purchase"),
        _row("fee"),
        _row("fee", no_receipt_expected="annual fee"),   # a person closed it
        _row("fee", section="posted"),                   # already booked
        {"effective_bucket": "reconciled", "row_type": "purchase"},
    ]
    counts = completeness_counts(rows, [])
    assert counts["n_charges_need_receipt"] == 2
    assert counts["n_charges_open_no_receipt_due"] == 1


def test_the_counter_rides_the_run_summary(tmp_path):
    from expense_recon.web.month_readiness import READINESS_KEYS

    assert "n_charges_open_no_receipt_due" in READINESS_KEYS
