"""Numeric account_id resolution refuses rather than defaulting.

The case that produced this module: in the 2026-09-22 TEST-BTS trial the
account was passed as a NAME, Zoho accepted every row with a 201 and
silently assigned its own default, and 6 of 9 expenses landed in
`Office Infra and Admin`. Nothing errored. So the contract under test is
not "resolution works" but "resolution REFUSES", and the negative cases
below are the point of the file.
"""
from __future__ import annotations

import pytest

from expense_recon.ingest.chart_of_accounts import ChartOfAccounts
from expense_recon.zoho.accounts import (
    REASON_DO_NOT_USE,
    REASON_EMPTY,
    REASON_INACTIVE,
    REASON_NO_ACCOUNT_ID,
    REASON_PLACEHOLDER,
    REASON_UNKNOWN,
    AccountRefusal,
    ResolvedAccount,
    resolve_account_id,
    resolve_all,
)

_API_ROWS = [
    {
        "account_id": "4369050000000078289",
        "account_name": "COGS - Other Infra and IT Costs for Cloud Business",
        "account_code": "E500010-20",
        "account_type": "cost_of_goods_sold",
        "is_active": True,
    },
    {
        "account_id": "4369050000000078353",
        "account_name": "Office Infra and Admin",
        "account_code": "E600010-10",
        "account_type": "expense",
        "is_active": True,
    },
    {
        "account_id": "4369050000000078999",
        "account_name": "Legacy Travel (DO NOT USE)",
        "account_code": "E100010-99",
        "account_type": "expense",
        "is_active": True,
    },
    {
        "account_id": "4369050000000078777",
        "account_name": "Closed Marketing Account",
        "account_code": "E200010-50",
        "account_type": "expense",
        "is_active": False,
    },
]


def _coa() -> ChartOfAccounts:
    return ChartOfAccounts.from_api(_API_ROWS)


def test_resolves_by_name_to_the_numeric_id():
    out = resolve_account_id(
        "COGS - Other Infra and IT Costs for Cloud Business", _coa()
    )
    assert isinstance(out, ResolvedAccount)
    assert out.account_id == "4369050000000078289"
    assert out.code == "E500010-20"


def test_resolves_by_code_and_by_code_plus_name_label():
    coa = _coa()
    by_code = resolve_account_id("E500010-20", coa)
    by_label = resolve_account_id(
        "E500010-20 COGS - Other Infra and IT Costs for Cloud Business", coa
    )
    assert isinstance(by_code, ResolvedAccount)
    assert isinstance(by_label, ResolvedAccount)
    # Both spellings must mean the same account, or the CSV a human
    # reviews and the payload the API gets could disagree.
    assert by_code.account_id == by_label.account_id == "4369050000000078289"


@pytest.mark.parametrize("ref", [None, "", "   "])
def test_empty_reference_refuses(ref):
    out = resolve_account_id(ref, _coa())
    assert isinstance(out, AccountRefusal)
    assert out.reason == REASON_EMPTY


@pytest.mark.parametrize(
    "placeholder",
    [
        "(uncategorized - assign)",
        "(account unmapped - assign)",
        "(reimbursable clearing - assign)",
        "(paid-through - assign)",
        "(entity - assign)",
        "Card: 4369050000000320002",
    ],
)
def test_export_placeholders_refuse(placeholder):
    """Each placeholder means a human still has to decide. Posting one
    would turn 'someone must assign this' into a number in the books."""
    out = resolve_account_id(placeholder, _coa())
    assert isinstance(out, AccountRefusal)
    assert out.reason == REASON_PLACEHOLDER


def test_unknown_account_refuses_instead_of_defaulting():
    """The 6-of-9 regression in one assertion: a category this org's
    chart does not carry must NOT come back as some other account."""
    out = resolve_account_id("Meals & Entertainment", _coa())
    assert isinstance(out, AccountRefusal)
    assert out.reason == REASON_UNKNOWN
    assert "Office Infra and Admin" not in out.detail


def test_a_csv_sourced_chart_cannot_post():
    """`ChartOfAccounts.from_csv` leaves account_id None on every row, so
    a chart a human exported from the Zoho UI resolves names perfectly and
    still cannot post. That has to say so, not post a None id."""
    coa = ChartOfAccounts.from_api(
        [{**_API_ROWS[0], "account_id": None}]
    )
    out = resolve_account_id(
        "COGS - Other Infra and IT Costs for Cloud Business", coa
    )
    assert isinstance(out, AccountRefusal)
    assert out.reason == REASON_NO_ACCOUNT_ID


def test_inactive_account_refuses():
    out = resolve_account_id("Closed Marketing Account", _coa())
    assert isinstance(out, AccountRefusal)
    assert out.reason == REASON_INACTIVE


def test_do_not_use_account_refuses():
    out = resolve_account_id("Legacy Travel (DO NOT USE)", _coa())
    assert isinstance(out, AccountRefusal)
    assert out.reason == REASON_DO_NOT_USE


def test_resolve_all_partitions_and_preserves_order():
    resolved, refusals = resolve_all(
        [
            "E500010-20",
            "Meals & Entertainment",
            "Office Infra and Admin",
            "(uncategorized - assign)",
        ],
        _coa(),
    )
    assert [r.code for r in resolved] == ["E500010-20", "E600010-10"]
    assert [r.reason for r in refusals] == [REASON_UNKNOWN, REASON_PLACEHOLDER]


def test_every_refusal_names_the_reference_and_a_remedy():
    """A refusal is read by whoever has to fix it, so it has to say which
    reference failed. A bare reason code sends them hunting."""
    for ref in ("Meals & Entertainment", "(uncategorized - assign)"):
        out = resolve_account_id(ref, _coa())
        assert isinstance(out, AccountRefusal)
        assert out.ref == ref
        assert len(out.detail) > 20
