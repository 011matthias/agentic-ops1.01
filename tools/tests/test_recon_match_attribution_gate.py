"""The attribution tool reads the matcher's uniqueness gate, it does not
mirror it (backlog item 69, round B, 2026-09-15).

`recon-match-attribution.py` is the judge of what the matcher does on the
labelled months. Until round B it carried its own copy of the
bilateral-uniqueness rules, so the two could drift apart silently and the
measurement would go on reporting the OLD gate's classes while the matcher
ran new ones. `trace_candidates` now calls
`expense_recon.matching.deterministic.uniqueness_verdicts`, the same
function `match_month` applies.

These tests bite if that import is replaced by a local re-implementation:
they assert the tool reports the round-B classes on shapes the pre-round-B
rules classified differently.
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "recon-match-attribution.py"
MODULE_SRC = (
    REPO
    / "workspace/clients/brisken/automations/expense-reconciliation/src"
)


@pytest.fixture(scope="module")
def attribution():
    """Import the hyphenated tool by path, with the module tree in front."""
    if not MODULE_SRC.is_dir():
        pytest.skip(f"expense-recon module not present at {MODULE_SRC}")
    if str(MODULE_SRC) not in sys.path:
        sys.path.insert(0, str(MODULE_SRC))
    pytest.importorskip("expense_recon.matching.deterministic")
    spec = importlib.util.spec_from_file_location("recon_attribution", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tx(tx_id, amount, vendor="ERICK SPORTS"):
    from expense_recon.matching.types import Transaction

    return Transaction(
        transaction_id=tx_id,
        legal_entity_id="corpserv",
        account_id="2838",
        transaction_date=date(2026, 4, 1),
        posting_date=None,
        amount=Decimal(amount),
        transaction_currency="USD",
        account_card_currency="USD",
        vendor_from_statement=vendor,
    )


def _receipt(doc, total, base=None, currency="BRL", vendor="Erick Sports"):
    from expense_recon.matching.types import Receipt

    return Receipt(
        document_id=doc,
        legal_entity_id="corpserv",
        detected_vendor=vendor,
        detected_date=date(2026, 4, 1),
        detected_total=Decimal(total),
        detected_currency=currency,
        base_amount=Decimal(base) if base else None,
        exchange_rate=Decimal("0.193945") if base else None,
    )


def _trace(attribution, transactions, receipts):
    from expense_recon.matching.deterministic import MatchingConfig

    return attribution.trace_candidates(transactions, receipts, MatchingConfig())


def test_the_tool_reports_a_spoken_for_rival_as_kept(attribution):
    """Two charges claim one BRL receipt; the second holds a bank-printed
    exact match of its own. The pre-round-B rules called the true pair
    `demoted_uniqueness`; the shared gate keeps it and says which clause
    did."""
    trace = _trace(
        attribution,
        [_tx("2838:1", "9.69"), _tx("2838:2", "9.75")],
        [
            _receipt("ER#BRL", "49.98", base="9.69"),
            _receipt("ER#USD", "9.75", currency="USD"),
        ],
    )
    cand = trace["cands"][("2838:1", "ER#BRL")]
    assert cand["status"] == "clean"
    assert cand["kept_by"] == "spoken_for"


def test_the_tool_reports_vendor_dominance_as_kept(attribution):
    """One charge, two receipts, only one naming the merchant."""
    trace = _trace(
        attribution,
        [_tx("2838:1", "9.69")],
        [
            _receipt("ER#SAME", "49.98", base="9.69"),
            _receipt("ER#OTHER", "49.98", base="9.69",
                     vendor="Quinta Wu Zabriskie"),
        ],
    )
    assert trace["cands"][("2838:1", "ER#SAME")]["kept_by"] == "vendor_dominance"
    assert (
        trace["cands"][("2838:1", "ER#OTHER")]["status"] == "demoted_uniqueness"
    )


def test_the_tool_still_reports_a_genuine_contest_as_demoted(attribution):
    """Equal evidence on both sides: the gate holds, and so does the tool's
    class, rivals named."""
    trace = _trace(
        attribution,
        [_tx("2838:1", "9.69"), _tx("2838:2", "9.75")],
        [_receipt("ER#BRL", "49.98", base="9.69")],
    )
    cand = trace["cands"][("2838:1", "ER#BRL")]
    assert cand["status"] == "demoted_uniqueness"
    assert cand["rivals"] == (["2838:2"], [])


def test_the_tool_reports_a_contradicted_card_as_demoted_card(attribution):
    from expense_recon.matching.types import Receipt

    receipt = Receipt(
        document_id="ER#BRL",
        legal_entity_id="corpserv",
        detected_vendor="Erick Sports",
        detected_date=date(2026, 4, 1),
        detected_total=Decimal("49.98"),
        detected_currency="BRL",
        base_amount=Decimal("9.69"),
        exchange_rate=Decimal("0.193945"),
        payment_mode="Visa ...9999",
    )
    trace = _trace(attribution, [_tx("2838:1", "9.69")], [receipt])
    assert trace["cands"][("2838:1", "ER#BRL")]["status"] == "demoted_card"
