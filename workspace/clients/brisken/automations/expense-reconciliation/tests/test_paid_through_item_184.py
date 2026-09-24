"""Item 184: the card an expense is paid FROM is checked like the account it
is paid TO.

Before this, `paid_through_account_id` reached the payload as a raw id that
nothing resolved: not against the org's chart, not for being active, not for
being a card at all. Every assertion runs through a caller, `run_month` or
`plan_expense_post`, so unwiring the check from `build_expense_payload`, or
the runner's card name from its plan kwargs, turns a test red.
"""
from __future__ import annotations

import pytest

from expense_recon.ingest.chart_of_accounts import ChartOfAccounts
from expense_recon.zoho.accounts import (
    REASON_DO_NOT_USE,
    REASON_EMPTY,
    REASON_INACTIVE,
    REASON_PAID_THROUGH_NAME_MISMATCH,
    REASON_PAID_THROUGH_NOT_A_CARD,
    REASON_PAID_THROUGH_NOT_NUMERIC,
    REASON_UNKNOWN,
)
from expense_recon.zoho.expense_post import (
    REFUSAL_PAID_THROUGH,
    ExpenseGroup,
    plan_expense_post,
)
from expense_recon.zoho.idempotent import PostLedger
from expense_recon.zoho.orgs import SANDBOX_ORG_ID

from tests.test_zoho_reconcile_month import (
    CARD,
    CARD_NAME,
    CHART,
    FakeClient,
    _row,
    _run,
)

# Cloud Services' Chase Visa 9693: a real card, in another org's chart.
CLOUD_CARD = "2031056000017742154"


class ChartClient(FakeClient):
    """The runner's fake network, serving a chart the test chooses."""

    def __init__(self, chart, **kw):
        super().__init__(**kw)
        self.chart = chart

    def list_chart_of_accounts(self):
        self.calls.append("coa")
        return [dict(a) for a in self.chart]


def _chart(**card_over):
    """The runner's chart with the card record changed (or dropped when
    `card_over` is None-valued for account_id)."""
    out = []
    for a in CHART:
        if a["account_id"] == CARD:
            a = {**a, **card_over}
            if a["account_id"] is None:
                continue
        out.append(dict(a))
    return out


def _paid_through_refusals(plan):
    return [r for r in plan.refusals if r.reason == REFUSAL_PAID_THROUGH]


# ── through the month runner ────────────────────────────────────────


def test_the_card_check_moves_with_the_chart_through_the_runner(tmp_path):
    """Differential: one batch, one live run each. With the card in the
    org's chart the purchase posts and carries the chart's id; with the card
    gone from the chart every purchase refuses and nothing is created."""
    rows = [_row(), _row(**{"Reference#": "R2"})]
    with_card, without_card = tmp_path / "with", tmp_path / "without"
    with_card.mkdir()
    without_card.mkdir()

    present = ChartClient(_chart())
    run, _ = _run(with_card, rows, client=present, dry_run=False)
    assert [p.reference for p in run.send_plan.postable] == ["R1", "R2"]
    assert {p.payload["paid_through_account_id"] for p in run.send_plan.postable} == {CARD}
    assert present.calls.count("create") == 2

    absent = ChartClient(_chart(account_id=None))
    run, out = _run(without_card, rows, client=absent, dry_run=False)
    assert run.send_plan.postable == ()
    refused = _paid_through_refusals(run.plan)
    assert [r.reference for r in refused] == ["R1", "R2"]
    assert all(r.detail.startswith(REASON_UNKNOWN) for r in refused)
    assert "create" not in absent.calls
    assert REFUSAL_PAID_THROUGH in out


def test_a_card_override_naming_another_card_refuses_through_the_runner(tmp_path):
    """Occupancy reads the card NAME, the post uses the ID. An override
    pairing this id with another card's name would check one card's month
    and post onto the other; the runner's plan kwargs carry the name so the
    builder can refuse it."""
    client = ChartClient(_chart())
    run, _ = _run(
        tmp_path, [_row()], client=client, dry_run=False,
        card_account_id=CARD, card_name="CHASE VISA - 2838 - TRAVEL",
    )
    assert run.send_plan.postable == ()
    (refused,) = _paid_through_refusals(run.plan)
    assert refused.detail.startswith(REASON_PAID_THROUGH_NAME_MISMATCH)
    assert CARD_NAME in refused.detail
    assert "create" not in client.calls


def test_the_profile_card_name_matches_regardless_of_case(tmp_path):
    client = ChartClient(_chart(account_name=CARD_NAME.upper()))
    run, _ = _run(tmp_path, [_row()], client=client)
    assert [p.reference for p in run.send_plan.postable] == ["R1"]


# ── through the planner ─────────────────────────────────────────────


def _plan(tmp_path, chart, paid_through):
    group = ExpenseGroup(reference="R1", rows=(_row(),))
    ledger = PostLedger(tmp_path / "p.db")
    try:
        return plan_expense_post(
            [group], ChartOfAccounts.from_api(chart), ledger,
            org_id=SANDBOX_ORG_ID, paid_through_account_id=paid_through,
            base_currency="USD",
        )
    finally:
        ledger.close()


@pytest.mark.parametrize(
    ("chart", "paid_through", "reason"),
    [
        # A name where an id belongs: the 2026-09-22 class, card side.
        (_chart(), CARD_NAME, REASON_PAID_THROUGH_NOT_NUMERIC),
        (_chart(), "", REASON_EMPTY),
        # Another org's real card: absent from this org's chart.
        (_chart(), CLOUD_CARD, REASON_UNKNOWN),
        (_chart(is_active=False), CARD, REASON_INACTIVE),
        (_chart(account_name="ZZZ | Old Visa | DO NOT USE"), CARD, REASON_DO_NOT_USE),
        # Undeposited Funds is `cash` in the sandbox and would be accepted
        # by Zoho as a paid-through: a card charge booked from the wrong
        # place entirely.
        (_chart(account_type="cash"), CARD, REASON_PAID_THROUGH_NOT_A_CARD),
        (_chart(account_type="bank"), CARD, REASON_PAID_THROUGH_NOT_A_CARD),
    ],
    ids=["name-not-id", "blank", "other-org", "inactive", "do-not-use", "cash", "bank"],
)
def test_the_planner_refuses_a_card_that_does_not_check_out(
    tmp_path, chart, paid_through, reason
):
    plan = _plan(tmp_path, chart, paid_through)
    assert plan.postable == ()
    (refused,) = plan.refusals
    assert refused.reason == REFUSAL_PAID_THROUGH
    assert refused.detail.startswith(reason)


def test_the_planner_posts_the_charts_id_for_a_card_that_does(tmp_path):
    plan = _plan(tmp_path, _chart(), f"  {CARD} ")
    (planned,) = plan.postable
    assert planned.payload["paid_through_account_id"] == CARD
