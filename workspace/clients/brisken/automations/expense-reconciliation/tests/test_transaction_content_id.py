"""Content-derived transaction identity (PR 2a of the living month).

Transaction ids used to be positional (`f"{account_id}:{row_index}"`).
Operator decisions key on the id, so a partial or appended statement
upload renumbered every row and silently re-pointed every confirm /
reject / manual-match onto a different charge. PR 2b makes appends
routine, so the identity has to stop depending on where in the file a
row happened to sit.

The tests that actually bite are the reorder / insert ones: those are
the two shapes a positional id cannot survive, and they fail against
the old source.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from expense_recon.ingest._common import (
    assign_content_ids,
    canonical_amount,
    transaction_content_id,
)
from expense_recon.ingest.statement_csv import parse_statement_csv
from expense_recon.ingest.statement_pdf import parse_statement_text
from expense_recon.ingest.statement_xlsx import parse_statement_xlsx
from expense_recon.matching.types import Transaction
from expense_recon.web.serialize import (
    transaction_from_dict,
    transaction_to_dict,
)


MAP = {"transaction_date": "Date", "vendor": "Description", "amount": "Amount"}

HEADER = "Date,Description,Amount\n"
ROW_COFFEE = "04/01/2026,COFFEE SHOP,5.75\n"
ROW_STAPLES = "04/15/2026,STAPLES,42.50\n"
ROW_HOTEL = "04/20/2026,HOTEL BERLIN,310.00\n"


def _csv(tmp_path: Path, name: str, body: str) -> list[Transaction]:
    src = tmp_path / name
    src.write_text(HEADER + body, encoding="utf-8")
    return parse_statement_csv(
        src,
        column_map=MAP,
        account_id="brisken-amex-usd",
        legal_entity_id="brisken-us",
        account_card_currency="USD",
    )


def _ids(txs: list[Transaction]) -> list[str]:
    return [t.transaction_id for t in txs]


def _tx(**kw) -> Transaction:
    base = dict(
        transaction_id="",
        legal_entity_id="brisken-us",
        account_id="brisken-amex-usd",
        transaction_date=date(2026, 4, 1),
        posting_date=None,
        amount=Decimal("5.75"),
        transaction_currency="USD",
        account_card_currency="USD",
        vendor_from_statement="COFFEE SHOP",
    )
    base.update(kw)
    return Transaction(**base)


# ── the identity contract ──────────────────────────────────────────


def test_same_row_same_id_across_separate_uploads(tmp_path):
    """The same charge uploaded twice is the same charge. This is what
    lets PR 2b dedupe an append against what the month already holds."""
    first = _csv(tmp_path, "a.csv", ROW_COFFEE + ROW_STAPLES)
    second = _csv(tmp_path, "b.csv", ROW_COFFEE + ROW_STAPLES)
    assert _ids(first) == _ids(second)


def test_reordering_rows_does_not_change_any_id(tmp_path):
    """The bite. A positional id is a row number, so swapping two rows
    swaps their ids and every decision keyed on them follows the wrong
    charge. A content id does not move."""
    forward = _csv(tmp_path, "fwd.csv", ROW_COFFEE + ROW_STAPLES + ROW_HOTEL)
    reverse = _csv(tmp_path, "rev.csv", ROW_HOTEL + ROW_STAPLES + ROW_COFFEE)
    assert set(_ids(forward)) == set(_ids(reverse))


def test_inserting_a_row_does_not_renumber_the_rows_below(tmp_path):
    """The other bite, and the shape PR 2b actually creates: a later
    statement upload carries earlier charges plus new ones."""
    partial = _csv(tmp_path, "partial.csv", ROW_STAPLES + ROW_HOTEL)
    full = _csv(tmp_path, "full.csv", ROW_COFFEE + ROW_STAPLES + ROW_HOTEL)
    assert set(_ids(partial)).issubset(set(_ids(full)))
    assert len(set(_ids(full))) == 3


def test_identical_rows_stay_distinct_charges(tmp_path):
    """Two identical coffees on one day are two real charges, not one
    charge seen twice. The second occurrence takes a `-1` suffix."""
    txs = _csv(tmp_path, "dupes.csv", ROW_COFFEE + ROW_COFFEE + ROW_COFFEE)
    ids = _ids(txs)
    assert len(set(ids)) == 3
    assert ids[1] == f"{ids[0]}-1"
    assert ids[2] == f"{ids[0]}-2"


def test_repeat_upload_reproduces_the_same_occurrence_suffixes(tmp_path):
    """The occurrence counter must be reproducible, or a re-upload of a
    file containing duplicate rows would look like new charges."""
    first = _csv(tmp_path, "d1.csv", ROW_COFFEE + ROW_COFFEE)
    second = _csv(tmp_path, "d2.csv", ROW_COFFEE + ROW_COFFEE)
    assert _ids(first) == _ids(second)


def test_a_different_charge_gets_a_different_id(tmp_path):
    """Sanity in the other direction: identity must actually discriminate."""
    txs = _csv(tmp_path, "mixed.csv", ROW_COFFEE + ROW_STAPLES + ROW_HOTEL)
    assert len(set(_ids(txs))) == 3


@pytest.mark.parametrize(
    "field,value",
    [
        ("account_id", "other-account"),
        ("card_last4", "9999"),
        ("transaction_date", date(2026, 4, 2)),
        ("amount", Decimal("5.76")),
        ("transaction_currency", "EUR"),
        ("vendor_from_statement", "TEA SHOP"),
    ],
)
def test_every_identity_field_changes_the_id(field, value):
    """Each field named in the identity must be load-bearing; a field
    that never changes the digest is a field silently not in the hash."""
    baseline = assign_content_ids([_tx()])[0].transaction_id
    changed = assign_content_ids([_tx(**{field: value})])[0].transaction_id
    assert changed != baseline


def test_a_field_outside_the_identity_does_not_change_the_id():
    """Posting date is bank-side metadata that can be restated on a later
    export; it must not fork the identity of the same charge."""
    baseline = assign_content_ids([_tx()])[0].transaction_id
    same = assign_content_ids([_tx(posting_date=date(2026, 4, 3))])[0]
    assert same.transaction_id == baseline


# ── amount canonicalization ────────────────────────────────────────


@pytest.mark.parametrize(
    "a,b",
    [
        ("10.30", "10.3"),
        ("100.00", "100"),
        ("0.00", "-0.00"),
        ("5.750", "5.75"),
    ],
)
def test_trailing_zeros_are_the_same_money(a, b):
    assert canonical_amount(Decimal(a)) == canonical_amount(Decimal(b))


def test_large_round_amounts_do_not_go_exponential():
    """`Decimal.normalize()` alone spells 100.00 as 1E+2, which would put
    exponent notation inside the hashed payload."""
    assert canonical_amount(Decimal("100.00")) == "100"
    assert canonical_amount(Decimal("1000000.00")) == "1000000"


def test_amounts_that_differ_are_not_collapsed():
    assert canonical_amount(Decimal("10.30")) != canonical_amount(Decimal("10.31"))


# ── the join cannot be forged ──────────────────────────────────────


def test_a_vendor_containing_the_separator_cannot_forge_a_collision():
    """Fields are joined through json.dumps precisely so a vendor name
    carrying the separator cannot impersonate a different field split."""
    left = transaction_content_id(
        account_id="acct",
        card_last4=None,
        transaction_date=date(2026, 4, 1),
        amount=Decimal("1.00"),
        transaction_currency="USD",
        vendor_from_statement='A","B',
    )
    right = transaction_content_id(
        account_id="acct",
        card_last4=None,
        transaction_date=date(2026, 4, 1),
        amount=Decimal("1.00"),
        transaction_currency="USD",
        vendor_from_statement='A"',
        reference='B',
    )
    assert left != right


def test_absent_card_and_empty_card_are_the_same_charge():
    """`""` and None both mean "the source printed no card"; they must
    not fork one charge into two."""
    kw = dict(
        account_id="acct",
        transaction_date=date(2026, 4, 1),
        amount=Decimal("1.00"),
        transaction_currency="USD",
        vendor_from_statement="X",
    )
    assert (
        transaction_content_id(card_last4=None, **kw)
        == transaction_content_id(card_last4="  ", **kw)
    )


def test_vendor_whitespace_and_case_do_not_fork_a_charge():
    kw = dict(
        account_id="acct",
        card_last4=None,
        transaction_date=date(2026, 4, 1),
        amount=Decimal("1.00"),
        transaction_currency="USD",
    )
    assert (
        transaction_content_id(vendor_from_statement="COFFEE  SHOP", **kw)
        == transaction_content_id(vendor_from_statement=" coffee shop ", **kw)
    )


# ── every parser agrees ────────────────────────────────────────────


def test_xlsx_ids_are_content_derived(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    src = tmp_path / "sheet.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Date", "Description", "Amount"])
    ws.append([date(2026, 4, 1), "COFFEE SHOP", 5.75])
    ws.append([date(2026, 4, 15), "STAPLES", 42.50])
    wb.save(src)

    txs = parse_statement_xlsx(
        src,
        column_map=MAP,
        account_id="brisken-amex-usd",
        legal_entity_id="brisken-us",
        account_card_currency="USD",
    )
    assert [t.source_row for t in txs] == [2, 3]
    assert all(":" not in t.transaction_id for t in txs)
    # The same two charges read off a CSV carry the SAME ids: identity is
    # the charge, not the file format it arrived in.
    assert _ids(txs) == _ids(_csv(tmp_path, "same.csv", ROW_COFFEE + ROW_STAPLES))


def test_pdf_ids_are_content_derived_and_carry_no_source_row():
    text = (
        "Opening/Closing Date 04/01/26 - 04/30/26\n"
        "04/01 COFFEE SHOP 5.75\n"
        "04/15 STAPLES 42.50\n"
        "CARD 2838\n"
    )
    txs, _issues = parse_statement_text(
        text,
        file_name="stmt.pdf",
        legal_entity_id="brisken-us",
        account_card_currency="USD",
    )
    assert txs, "fixture should yield charges"
    assert all(t.source_row is None for t in txs)
    assert all(len(t.transaction_id.split("-")[0]) == 16 for t in txs)
    # No `:` anywhere: the writeback's legacy row-parsing fallback must
    # never mistake an occurrence suffix for a spreadsheet row.
    assert all(":" not in t.transaction_id for t in txs)


# ── nothing at rest moves ──────────────────────────────────────────


def test_existing_positional_ids_survive_the_snapshot_round_trip():
    """No migration: a run stored before PR 2a keeps its positional ids,
    so the decisions keyed on them still resolve."""
    stored = {
        "transaction_id": "brisken-amex-usd:6",
        "legal_entity_id": "brisken-us",
        "account_id": "brisken-amex-usd",
        "transaction_date": "2026-04-01",
        "posting_date": None,
        "amount": "5.75",
        "transaction_currency": "USD",
        "account_card_currency": "USD",
        "vendor_from_statement": "COFFEE SHOP",
    }
    tx = transaction_from_dict(stored)
    assert tx.transaction_id == "brisken-amex-usd:6"
    assert tx.source_row is None


def test_source_row_survives_the_snapshot_round_trip():
    """The sheet writeback reads `source_row` off a re-loaded snapshot,
    so it has to be persisted, not just present at parse time."""
    tx = _tx(transaction_id="abc123", source_row=7)
    assert transaction_from_dict(transaction_to_dict(tx)).source_row == 7
