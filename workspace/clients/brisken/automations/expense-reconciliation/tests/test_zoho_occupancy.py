"""The month-occupancy guard refuses a month someone else already entered.

The 4.8 ledger stops THIS tool re-posting. It cannot see Criss, who enters
these charges by hand weeks late, and a 2026-09-22 probe found no bank
feed anywhere (0 of 39 sampled rows carried imported_transactions). So the
realistic double is a first post into a month a human already did, which
the ledger cannot detect and this guard must.
"""
from __future__ import annotations

import pytest

from expense_recon.zoho.occupancy import (
    VERDICT_ALREADY_OCCUPIED,
    VERDICT_CLEAR,
    VERDICT_LOCKED_PERIOD,
    VERDICT_UNVERIFIABLE,
    check_month_occupancy,
    month_bounds,
)

_CARD = "CHASE VISA - 2838 - TRAVEL"
_PROD = "822741658"   # Corporate Services, real books
_SANDBOX = "822116290"  # TEST-BTS, a clone


class FakeClient:
    """Records whether it was called, so a locked period can be proven to
    refuse WITHOUT a network round trip."""

    def __init__(self, rows=None, raises=None):
        self._rows = rows or []
        self._raises = raises
        self.calls: list[tuple[str, str]] = []

    def list_expenses(self, *, date_start=None, date_end=None):
        self.calls.append((date_start, date_end))
        if self._raises is not None:
            raise self._raises
        return list(self._rows)


# ── month_bounds ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "period,expected",
    [
        ("2026-09", ("2026-09-01", "2026-09-30")),
        ("2026-07", ("2026-07-01", "2026-07-31")),
        # December must roll the YEAR, not the month.
        ("2026-12", ("2026-12-01", "2026-12-31")),
        # 2028 is a leap year; February is arithmetic, not a table.
        ("2028-02", ("2028-02-01", "2028-02-29")),
        ("2026-02", ("2026-02-01", "2026-02-28")),
    ],
)
def test_month_bounds(period, expected):
    assert month_bounds(period) == expected


@pytest.mark.parametrize("bad", ["2026-13", "2026", "26-09", "", "2026-1", None])
def test_month_bounds_rejects_malformed_period(bad):
    """A malformed period must raise, never silently produce a window that
    matches nothing, which would read as "the month is empty"."""
    with pytest.raises(ValueError):
        month_bounds(bad)


# ── the guard ───────────────────────────────────────────────────────


def test_july_is_locked_and_refuses_without_asking_zoho():
    client = FakeClient(rows=[])
    out = check_month_occupancy(client, org_id=_PROD, period="2026-07")
    assert out.verdict == VERDICT_LOCKED_PERIOD
    assert not out.ok
    # The standing rule needs no evidence, so it must not spend a call.
    assert client.calls == []


def test_an_occupied_month_refuses_and_reports_what_is_there():
    client = FakeClient(
        rows=[
            {
                "date": "2026-09-05",
                "total": 80.04,
                "reference_number": "AI Subsc",
                "paid_through_account_name": _CARD,
            },
            {
                "date": "2026-09-10",
                "total": 12.5,
                "description": "SUPERMEC",
                "paid_through_account_name": _CARD,
            },
        ]
    )
    out = check_month_occupancy(
        client, org_id=_PROD, period="2026-09", paid_through=_CARD
    )
    assert out.verdict == VERDICT_ALREADY_OCCUPIED
    assert not out.ok
    assert out.existing_count == 2
    assert len(out.sample) == 2
    assert "2026-09-05" in out.sample[0]
    # The query must be the month's real bounds.
    assert client.calls == [("2026-09-01", "2026-09-30")]


def test_rows_on_another_card_do_not_block_this_card():
    client = FakeClient(
        rows=[
            {
                "date": "2026-09-05",
                "total": 80.04,
                "paid_through_account_name": "Chase Visa | 9693 | Cloud Expenses",
            }
        ]
    )
    out = check_month_occupancy(
        client, org_id=_PROD, period="2026-09", paid_through=_CARD
    )
    assert out.verdict == VERDICT_CLEAR
    assert out.ok


def test_without_a_card_every_row_in_the_month_blocks():
    """A month-wide post has a month-wide blast radius, so with no card
    named, any row in the month is an occupancy hit."""
    client = FakeClient(
        rows=[
            {
                "date": "2026-09-05",
                "total": 80.04,
                "paid_through_account_name": "some other card",
            }
        ]
    )
    out = check_month_occupancy(client, org_id=_PROD, period="2026-09")
    assert out.verdict == VERDICT_ALREADY_OCCUPIED


def test_an_empty_month_is_clear():
    client = FakeClient(rows=[])
    out = check_month_occupancy(
        client, org_id=_SANDBOX, period="2026-10", paid_through=_CARD
    )
    assert out.verdict == VERDICT_CLEAR
    assert out.ok


def test_an_unreadable_month_refuses_rather_than_reading_as_empty():
    """The dangerous direction. A failed query and an empty month must
    never take the same branch, or an outage becomes permission to post."""
    client = FakeClient(raises=RuntimeError("502 upstream"))
    out = check_month_occupancy(
        client, org_id=_PROD, period="2026-09", paid_through=_CARD
    )
    assert out.verdict == VERDICT_UNVERIFIABLE
    assert not out.ok
    assert "502 upstream" in out.detail


def test_ok_is_true_only_for_clear():
    """`ok` is the property callers branch on, so every non-CLEAR verdict
    must report False even as new verdicts get added."""
    client = FakeClient(rows=[])
    clear = check_month_occupancy(client, org_id=_PROD, period="2026-10")
    locked = check_month_occupancy(client, org_id=_PROD, period="2026-07")
    occupied = check_month_occupancy(
        FakeClient(rows=[{"date": "2026-09-01", "total": 1}]),
        org_id=_PROD,
        period="2026-09",
    )
    unverifiable = check_month_occupancy(
        FakeClient(raises=RuntimeError("x")), org_id=_PROD, period="2026-09"
    )
    assert clear.ok
    assert not locked.ok
    assert not occupied.ok
    assert not unverifiable.ok


# ── the standing lock is production-only ────────────────────────────
# What makes July dangerous is 118 rows a human typed, and those exist
# only in the production orgs. In a clone July is empty and is the month
# most worth rehearsing, because a full month is the shape the tool has
# to survive. A global lock would forbid exactly the rehearsal that
# de-risks the real run.


def test_july_is_rehearsable_in_the_sandbox():
    client = FakeClient(rows=[])
    out = check_month_occupancy(
        client, org_id=_SANDBOX, period="2026-07", paid_through=_CARD
    )
    assert out.verdict == VERDICT_CLEAR
    assert out.ok
    # Waiving a safety rule silently is how it gets forgotten; the
    # verdict has to say the lock was waived and why.
    assert "waived" in out.detail
    # And it must have actually asked Zoho, unlike the locked path.
    assert client.calls == [("2026-07-01", "2026-07-31")]


def test_july_is_still_locked_in_both_production_orgs():
    for org in ("822741658", "697686691"):
        out = check_month_occupancy(FakeClient(rows=[]), org_id=org, period="2026-07")
        assert out.verdict == VERDICT_LOCKED_PERIOD, org


def test_the_sandbox_waiver_does_not_waive_occupancy():
    """Only the standing lock is production-scoped. A rehearsal that
    double-posts is still a bug, and catching it in the sandbox is the
    entire reason to rehearse there."""
    client = FakeClient(
        rows=[
            {
                "date": "2026-07-15",
                "total": 42.0,
                "paid_through_account_name": _CARD,
            }
        ]
    )
    out = check_month_occupancy(
        client, org_id=_SANDBOX, period="2026-07", paid_through=_CARD
    )
    assert out.verdict == VERDICT_ALREADY_OCCUPIED
    assert not out.ok


def test_an_unknown_org_is_not_treated_as_production():
    """`is_production_org` is a positive list, not "anything that is not
    the sandbox". A typo'd or newly-cloned org must not inherit
    production's protections by accident; the allowlist is what refuses
    it, and that refusal lives in the posting CLI."""
    out = check_month_occupancy(
        FakeClient(rows=[]), org_id="999999999", period="2026-07"
    )
    assert out.verdict == VERDICT_CLEAR


def test_locked_periods_are_configurable_but_not_empty_by_default():
    client = FakeClient(rows=[])
    # An explicitly widened lock set.
    out = check_month_occupancy(
        client, org_id=_PROD, period="2026-08", locked_periods={"2026-07", "2026-08"}
    )
    assert out.verdict == VERDICT_LOCKED_PERIOD
    # And the default still carries July rather than trusting a caller.
    assert check_month_occupancy(client, org_id=_PROD, period="2026-07").verdict == (
        VERDICT_LOCKED_PERIOD
    )
