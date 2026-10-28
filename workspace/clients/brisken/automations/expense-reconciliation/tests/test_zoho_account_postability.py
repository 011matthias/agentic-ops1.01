"""Which accounts may take a posting, and who decides.

Replaces the tests of the retired category-to-account table. What that
table's hand audit held (never post to a roll-up) now lives in
`resolve_account_id`, with one correction the audit could not see: in an
org Dirk curated, the curated marking decides, and it approves 35 chart
parents that Zoho does accept postings on. Everything here runs through
`plan_expense_post`, the caller, because a suite that exercised the
resolver alone would stay green if the planner stopped passing `org_id`.
"""
from __future__ import annotations

from decimal import Decimal

from expense_recon.ingest.chart_of_accounts import ChartOfAccounts
from expense_recon.output.zoho_expense_export import EXPENSE_COLUMNS
from expense_recon.zoho import curated_leaves
from expense_recon.zoho.accounts import (
    REASON_CHART_ORG_MISMATCH,
    REASON_NON_LEAF,
    REASON_NOT_EXPENSE_RELEVANT,
    REASON_OUT_OF_SCOPE,
    REASON_UNKNOWN,
    AccountRefusal,
    ResolvedAccount,
    resolve_account_id,
)
from expense_recon.zoho.expense_post import (
    REFUSAL_ACCOUNT,
    ExpenseGroup,
    plan_expense_post,
)
from expense_recon.zoho.idempotent import PostLedger
from expense_recon.zoho.orgs import SANDBOX_ORG_ID

CLOUD = "697686691"  # Cloud Services, curated (BCS tab)
CORP = "822741658"  # Corporate Services, curated (CorpServ tab)
CARD_ID = "4369050000000320002"
# Cloud Services' own card: a chart only carries its own org's cards, and
# since item 184 the paid-through id must be in the chart posted against.
CLOUD_CARD_ID = "2031056000017742154"

IT_PARENT = "IT: Computer and Internet Expenses"


def _acct(account_id, name, code, parent=None, account_type="expense"):
    return {
        "account_id": account_id,
        "account_name": name,
        "account_code": code,
        "account_type": account_type,
        "is_active": True,
        "parent_account_name": parent,
    }


# Cloud Services, with the ids and names its live chart carries. The child
# row is load-bearing: it is what makes `IT: Computer and Internet
# Expenses` a parent in this chart.
CLOUD_CHART = ChartOfAccounts.from_api(
    [
        _acct("2031056000000104391", IT_PARENT, "E500010"),
        _acct("2031056000000106807", "IT: Cloud Subscriptions-Others",
              "E500010-30", IT_PARENT),
        _acct("2031056000014161139",
              "COGS - DEV Infrastructure (SAP Apps & others)", "E700030-19"),
        _acct("2031056000000104265", "Travel Expense | Food", "E100010-31"),
        _acct("2031056000000403080", "Payroll Taxes: Medicare", "E300000-10"),
        _acct("2031056000099999999", "Unlisted Expense", "E999990"),
        _acct(CLOUD_CARD_ID, "Chase Visa | 9693 | Cloud Expenses", "9693",
              account_type="credit_card"),
    ]
)

# TEST-BTS, which nobody curated: same parent, the sandbox's own ids.
SANDBOX_CHART = ChartOfAccounts.from_api(
    [
        _acct("4369050000000078183", IT_PARENT, "E500010"),
        _acct("4369050000000078239", "IT: Cloud Subscriptions-Others",
              "E500010-30", IT_PARENT),
        _acct(CARD_ID, "Visa dummy card Matthias", "",
              account_type="credit_card"),
    ]
)


def _row(account, ref="R1", amount="240.00"):
    row = dict.fromkeys(EXPENSE_COLUMNS, "")
    row.update(
        {
            "Expense Date": "2026-07-09",
            "Expense Account": account,
            "Expense Amount": amount,
            "Currency Code": "USD",
            "Reference#": ref,
            "Expense Description": "test purchase",
        }
    )
    return row


def _plan(groups, coa, *, org_id, tmp_path):
    ledger = PostLedger(tmp_path / f"plan-{org_id}.db")
    try:
        return plan_expense_post(
            groups,
            coa,
            ledger,
            org_id=org_id,
            paid_through_account_id=(
                CLOUD_CARD_ID if coa is CLOUD_CHART else CARD_ID
            ),
            base_currency="USD",
        )
    finally:
        ledger.close()


def _plan_one(account, coa, *, org_id, tmp_path):
    group = ExpenseGroup(reference="R1", rows=(_row(account),))
    return _plan([group], coa, org_id=org_id, tmp_path=tmp_path)


def test_the_pinned_marking_still_says_what_these_tests_assume():
    """The cases below lean on Dirk's sheet. If it is re-marked, this
    fails first and names the row, instead of a refusal test passing for
    the wrong reason."""
    assert curated_leaves.is_postable(CLOUD, "E500010")
    assert curated_leaves.is_postable(CLOUD, "E700030-19")
    assert not curated_leaves.is_postable(CLOUD, "E300000-10")
    assert curated_leaves.binding("E999990", CLOUD) is None
    assert curated_leaves.is_postable(CORP, "E100010-31")
    assert not curated_leaves.covers_org(SANDBOX_ORG_ID)
    assert IT_PARENT in CLOUD_CHART._parent_names()  # noqa: SLF001


# ── the curated org: the marking decides ───────────────────────────


def test_a_parent_the_marking_approves_posts(tmp_path):
    """The correction. `IT: Computer and Internet Expenses` is a roll-up
    in the chart and marked Y; Zoho accepts postings on it (Corporate
    Services' books hold one). A chart-shape rule would refuse it."""
    plan = _plan_one(IT_PARENT, CLOUD_CHART, org_id=CLOUD, tmp_path=tmp_path)
    assert plan.refusals == ()
    assert plan.postable[0].payload["account_id"] == "2031056000000104391"


def test_the_account_anthropic_posts_to_resolves(tmp_path):
    """The design's own flagship: COGS - DEV Infrastructure under Cloud
    Services. It sits outside every scope group the old export gate was
    provisioned with, and it is marked Y."""
    plan = _plan_one(
        "E700030-19", CLOUD_CHART, org_id=CLOUD, tmp_path=tmp_path
    )
    assert plan.refusals == ()
    assert plan.postable[0].payload["account_id"] == "2031056000014161139"


def test_an_account_marked_n_refuses_though_the_chart_allows_it(tmp_path):
    """A payroll tax is an active leaf; nothing in the chart says a card
    cannot pay it. The marking does."""
    plan = _plan_one(
        "Payroll Taxes: Medicare", CLOUD_CHART, org_id=CLOUD, tmp_path=tmp_path
    )
    assert plan.postable == ()
    assert plan.refusals[0].reason == REFUSAL_ACCOUNT
    assert REASON_NOT_EXPENSE_RELEVANT in plan.refusals[0].detail


def test_an_account_off_the_list_refuses_as_out_of_scope(tmp_path):
    plan = _plan_one(
        "Unlisted Expense", CLOUD_CHART, org_id=CLOUD, tmp_path=tmp_path
    )
    assert plan.postable == ()
    assert REASON_OUT_OF_SCOPE in plan.refusals[0].detail


def test_a_chart_loaded_for_another_org_refuses(tmp_path):
    """E100010-31 is postable in both orgs under the same code and
    different ids. Posting Cloud Services' chart under Corporate Services
    would send Cloud's id into Corporate's books."""
    plan = _plan_one(
        "Travel Expense | Food", CLOUD_CHART, org_id=CORP, tmp_path=tmp_path
    )
    assert plan.postable == ()
    assert REASON_CHART_ORG_MISMATCH in plan.refusals[0].detail
    assert "2031056000000104265" in plan.refusals[0].detail


# ── an org nobody curated: the chart decides ───────────────────────


def test_the_same_parent_refuses_where_no_list_exists(tmp_path):
    """The discrimination: the row that posts for Cloud Services refuses
    for the sandbox, whose only rule is the chart's shape."""
    parent = _plan_one(
        IT_PARENT, SANDBOX_CHART, org_id=SANDBOX_ORG_ID, tmp_path=tmp_path
    )
    child = _plan_one(
        "IT: Cloud Subscriptions-Others", SANDBOX_CHART,
        org_id=SANDBOX_ORG_ID, tmp_path=tmp_path,
    )
    assert parent.postable == ()
    assert REASON_NON_LEAF in parent.refusals[0].detail
    assert child.refusals == ()
    assert child.postable[0].payload["account_id"] == "4369050000000078239"


def test_no_org_at_all_takes_the_chart_rule():
    out = resolve_account_id(IT_PARENT, SANDBOX_CHART)
    assert isinstance(out, AccountRefusal)
    assert out.reason == REASON_NON_LEAF
    assert isinstance(
        resolve_account_id("E500010-30", SANDBOX_CHART), ResolvedAccount
    )


def test_a_category_label_is_not_an_account_anywhere(tmp_path):
    """The translation table is gone. What it used to rescue for the
    sandbox now refuses there too, naming the label."""
    plan = _plan_one(
        "Software & Subscriptions", SANDBOX_CHART,
        org_id=SANDBOX_ORG_ID, tmp_path=tmp_path,
    )
    assert plan.postable == ()
    assert REASON_UNKNOWN in plan.refusals[0].detail
    assert "Software & Subscriptions" in plan.refusals[0].detail


def test_a_split_refuses_whole_when_one_line_is_not_postable(tmp_path):
    """Splits post as one expense, so one refused line takes the whole
    purchase with it rather than posting a partial amount."""
    group = ExpenseGroup(
        reference="SPLIT",
        rows=(
            _row(IT_PARENT, ref="SPLIT", amount="100.00"),
            _row("Payroll Taxes: Medicare", ref="SPLIT", amount="50.00"),
        ),
    )
    plan = _plan([group], CLOUD_CHART, org_id=CLOUD, tmp_path=tmp_path)
    assert plan.postable == ()
    assert plan.refusals[0].reason == REFUSAL_ACCOUNT
    assert plan.total == Decimal("0")
