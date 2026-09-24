"""The sandbox reset is the only destructive path, so its guards are the
thing under test.

TEST-BTS is a CLONE of a production org: same chart, same account names,
same id shape. Nothing about a row says "this is only a test", so a reset
pointed one digit wrong is an irreversible delete of a client's books.
Every test below is about refusing, except the two that prove it can
still do its job.
"""
from __future__ import annotations

import pytest

from expense_recon.zoho.orgs import PRODUCTION_ORG_IDS, SANDBOX_ORG_ID
from expense_recon.zoho.sandbox_reset import (
    SandboxGuardError,
    execute_reset,
    plan_reset,
)

_ROWS = [
    {
        "expense_id": "4369050000000277033",
        "date": "2026-09-21",
        "total": 100.0,
        "paid_through_account_name": "Petty Cash",
        "reference_number": "TEST-EXP-001",
    },
    {
        "expense_id": "4369050000000321001",
        "date": "2026-09-21",
        "total": 125.0,
        "paid_through_account_name": "Visa dummy card Matthias",
        "reference_number": "Sep 2026 - Sub ID 88392",
    },
]


class FakeClient:
    def __init__(self, rows=None, fail_on=(), list_after=None):
        self._rows = list(rows if rows is not None else _ROWS)
        self._fail_on = set(fail_on)
        self._list_after = list_after
        self.deleted: list[str] = []
        self.list_calls = 0

    def list_expenses(self, **_):
        self.list_calls += 1
        if self.list_calls > 1 and self._list_after is not None:
            return list(self._list_after)
        return list(self._rows)

    def delete_expense(self, expense_id):
        if expense_id in self._fail_on:
            raise RuntimeError("403 not permitted")
        self.deleted.append(expense_id)
        self._rows = [r for r in self._rows if r["expense_id"] != expense_id]
        return {"code": 0}


# ── the guards ──────────────────────────────────────────────────────


@pytest.mark.parametrize("org", sorted(PRODUCTION_ORG_IDS))
def test_planning_a_reset_of_real_books_refuses(org):
    client = FakeClient()
    with pytest.raises(SandboxGuardError) as exc:
        plan_reset(client, org_id=org)
    assert "real books" in str(exc.value)
    # It must refuse BEFORE reading, so a wrong org never even enumerates.
    assert client.list_calls == 0


@pytest.mark.parametrize("org", ["", None, "999999999", "82211629", "822116290 "])
def test_an_unrecognised_org_refuses(org):
    """Not-production is not the same as safe. A truncated or typo'd id
    must refuse rather than fall through to 'well, it isn't production'.
    The trailing-space case matters because ids arrive from config."""
    if org == "822116290 ":
        # ...but a stray space around the RIGHT id is tolerated, since
        # refusing that would only invite someone to disable the guard.
        plan_reset(FakeClient(), org_id=org)
        return
    with pytest.raises(SandboxGuardError):
        plan_reset(FakeClient(), org_id=org)


def test_execute_refuses_without_go():
    client = FakeClient()
    plan = plan_reset(client, org_id=SANDBOX_ORG_ID)
    with pytest.raises(SandboxGuardError) as exc:
        execute_reset(client, plan, go=False)
    assert "go=True" in str(exc.value)
    assert client.deleted == []


def test_execute_rechecks_the_org_rather_than_trusting_the_plan():
    """The plan is a value object and could be built or edited anywhere,
    so execute asserts the org again instead of trusting it."""
    client = FakeClient()
    plan = plan_reset(client, org_id=SANDBOX_ORG_ID)
    tampered = type(plan)(
        org_id=sorted(PRODUCTION_ORG_IDS)[0],
        expense_ids=plan.expense_ids,
        lines=plan.lines,
    )
    with pytest.raises(SandboxGuardError):
        execute_reset(client, tampered, go=True)
    assert client.deleted == []


# ── doing the job ───────────────────────────────────────────────────


def test_plan_enumerates_every_expense_by_id():
    plan = plan_reset(FakeClient(), org_id=SANDBOX_ORG_ID)
    assert len(plan) == 2
    assert plan.expense_ids == (
        "4369050000000277033",
        "4369050000000321001",
    )
    # The lines are what a human reads before saying go.
    assert "TEST-EXP-001" in plan.lines[0]


def test_reset_deletes_by_id_and_verifies_the_org_is_empty():
    client = FakeClient()
    plan = plan_reset(client, org_id=SANDBOX_ORG_ID)
    report = execute_reset(client, plan, go=True)
    assert client.deleted == list(plan.expense_ids)
    assert report.remaining == 0
    assert report.ok


def test_a_failed_delete_is_reported_and_the_report_is_not_ok():
    client = FakeClient(fail_on={"4369050000000321001"})
    plan = plan_reset(client, org_id=SANDBOX_ORG_ID)
    report = execute_reset(client, plan, go=True)
    assert report.deleted == ("4369050000000277033",)
    assert len(report.failed) == 1
    assert "403" in report.failed[0][1]
    assert not report.ok
    # It keeps going rather than stopping at the first failure, so one
    # run names every problem.
    assert client.deleted == ["4369050000000277033"]


def test_rows_left_behind_make_the_report_not_ok_even_with_no_failures():
    """Every delete returning 200 proves each call was accepted, not that
    the org is empty. Only the re-list proves that."""
    client = FakeClient(list_after=[{"expense_id": "leftover"}])
    plan = plan_reset(client, org_id=SANDBOX_ORG_ID)
    report = execute_reset(client, plan, go=True)
    assert not report.failed
    assert report.remaining == 1
    assert not report.ok


def test_an_unverifiable_re_list_is_not_ok():
    class Blind(FakeClient):
        def list_expenses(self, **kw):
            self.list_calls += 1
            if self.list_calls > 1:
                raise RuntimeError("502")
            return list(self._rows)

    client = Blind()
    plan = plan_reset(client, org_id=SANDBOX_ORG_ID)
    report = execute_reset(client, plan, go=True)
    assert report.remaining is None
    assert not report.ok


# ── targeted reset: pull one stray row, keep the rehearsal ──────────
#
# The sandbox now holds months the durable ledger records as `posted`, so
# a full reset would silently desynchronise the ledger from Zoho. Pulling
# ONE row is the operation actually wanted, and the rows left standing
# are the point rather than collateral.


def test_a_targeted_reset_deletes_only_the_named_row():
    client = FakeClient()
    plan = plan_reset(
        client, org_id=SANDBOX_ORG_ID, only_ids=["4369050000000321001"]
    )
    assert plan.expense_ids == ("4369050000000321001",)
    assert plan.total_in_org == 2 and plan.expected_remaining == 1

    report = execute_reset(client, plan, go=True)
    assert client.deleted == ["4369050000000321001"]
    assert report.ok and report.remaining == 1


def test_ok_means_the_plan_happened_not_that_the_org_is_empty():
    """A targeted delete legitimately leaves rows standing. If that read
    as failure, `ok` would always be False here and stop being read."""
    client = FakeClient()
    plan = plan_reset(
        client, org_id=SANDBOX_ORG_ID, only_ids=["4369050000000277033"]
    )
    report = execute_reset(client, plan, go=True)
    assert report.ok and report.remaining == 1 and report.expected_remaining == 1


def test_a_full_reset_still_demands_an_empty_org():
    """The stricter original contract must survive the addition."""
    client = FakeClient()
    plan = plan_reset(client, org_id=SANDBOX_ORG_ID)
    assert plan.expected_remaining == 0
    report = execute_reset(client, plan, go=True)
    assert report.ok and report.remaining == 0


def test_an_id_the_org_does_not_hold_aborts():
    """A delete-by-id that skips a miss reports success for a row that is
    still standing. Refuse the whole plan instead."""
    client = FakeClient()
    with pytest.raises(SandboxGuardError, match="not in it"):
        plan_reset(
            client,
            org_id=SANDBOX_ORG_ID,
            only_ids=["4369050000000321001", "9999999999999999999"],
        )
    assert client.deleted == []


def test_an_empty_only_ids_never_widens_into_a_full_reset():
    """The dangerous default: an empty selection must not fall through to
    deleting everything in a cloned production org."""
    client = FakeClient()
    for empty in ([], ["", "  "]):
        with pytest.raises(SandboxGuardError, match="refusing to fall back"):
            plan_reset(client, org_id=SANDBOX_ORG_ID, only_ids=empty)
    assert client.deleted == []


@pytest.mark.parametrize("org", sorted(PRODUCTION_ORG_IDS))
def test_a_targeted_reset_still_refuses_production(org):
    client = FakeClient()
    with pytest.raises(SandboxGuardError):
        plan_reset(client, org_id=org, only_ids=["4369050000000321001"])
    assert client.deleted == []


def test_a_targeted_plan_still_needs_go():
    client = FakeClient()
    plan = plan_reset(
        client, org_id=SANDBOX_ORG_ID, only_ids=["4369050000000321001"]
    )
    with pytest.raises(SandboxGuardError):
        execute_reset(client, plan)
    assert client.deleted == []
