"""The per-org category fallback: what it unblocks and what it must not.

The July dry run refused 36 of 46 purchases because the export leaks a
CATEGORY into the account column when a receipt's vendor has no account
rule. Mapping those categories is only safe if the refusals that matter
survive it, so most of this file is about what still refuses: an org
nobody mapped, a placeholder a human still owes, a near-miss name.

The assertions run through `plan_expense_post` wherever they can, not
only through the resolver. A suite that exercised `resolve_account_id`
alone would stay green if the caller stopped passing `org_id`, which is
exactly the wiring this change adds.
"""
from __future__ import annotations

from decimal import Decimal

from expense_recon.ingest.chart_of_accounts import ChartOfAccounts
from expense_recon.output.zoho_expense_export import EXPENSE_COLUMNS
from expense_recon.zoho.accounts import (
    REASON_CATEGORY_CODE_MISSING,
    REASON_PLACEHOLDER,
    REASON_UNKNOWN,
    AccountRefusal,
    ResolvedAccount,
    resolve_account_id,
)
from expense_recon.output.zoho_expense_export import (
    ENTITY_PLACEHOLDER,
    PAID_THROUGH_PLACEHOLDER,
)
from expense_recon.zoho.category_accounts import (
    CATEGORY_ACCOUNT_CODES,
    NEVER_MAPPED,
    category_account_code,
)
from expense_recon.zoho.expense_post import (
    REFUSAL_ACCOUNT,
    ExpenseGroup,
    PostRefusal,
    plan_expense_post,
)
from expense_recon.zoho.idempotent import PostLedger
from expense_recon.zoho.orgs import PRODUCTION_ORG_IDS, SANDBOX_ORG_ID

CARD_ID = "4369050000000320002"
A_PRODUCTION_ORG = sorted(PRODUCTION_ORG_IDS)[0]

def _acct(account_id, name, code, parent=None):
    return {
        "account_id": account_id,
        "account_name": name,
        "account_code": code,
        "account_type": "expense",
        "is_active": True,
        "parent_account_name": parent,
    }


# Real TEST-BTS accounts (ids, names and codes as the live chart carries
# them), so a typo in the shipped map fails here rather than in Zoho.
# The parent rows are carried too, and they are load-bearing: a parent is
# only detectable because some child names it, and the leaf assertion
# below is what stops a roll-up account being mapped again.
_COA = ChartOfAccounts.from_api(
    [
        # IT: Computer and Internet Expenses (parent) and its leaves
        _acct("4369050000000078183", "IT: Computer and Internet Expenses", "E500010"),
        _acct("4369050000000078239", "IT: Cloud Subscriptions-Others", "E500010-30",
              "IT: Computer and Internet Expenses"),
        _acct("4369050000000078295", "IT: Cloud Subscriptions-Microsoft office",
              "E500010-20", "IT: Computer and Internet Expenses"),
        _acct("4369050000000078383", "IT: equipment, peripherals, phones, devices",
              "E500010-40", "IT: Computer and Internet Expenses"),
        # Travel Expense (parent) and the leaves in play
        _acct("4369050000000000418", "Travel Expense", "E100010"),
        _acct("4369050000000078157", "Travel Expense:Meals", "E100010-31",
              "Travel Expense"),
        _acct("4369050000000078127", "Travel Expense: Automobile Expense",
              "E100010-01", "Travel Expense"),
        _acct("4369050000000078159", "Travel Expense:Rental Cars", "E100010-36",
              "Travel Expense"),
        # Professional Fees (parent) and its catch-all leaf
        _acct("4369050000000078201", "Professional Fees", "E600060"),
        _acct("4369050000000000460", "Other Expenses", "E600060-70",
              "Professional Fees"),
        _acct("4369050000000078197", "Legal Fees", "E600060-20", "Professional Fees"),
        # Marketing (parent) > Advertising and Promotion (parent) > leaves
        _acct("4369050000000078285", "Marketing & Selling Expenses", "E600010"),
        _acct("4369050000000078191", "Advertising and Promotion", "E600010-05",
              "Marketing & Selling Expenses"),
        _acct("4369050000000078341", "Other Promotions and Advertising Channels",
              "E600010-05-09", "Advertising and Promotion"),
        _acct("4369050000000078335", "LinkedIn Advertising", "E600010-05-02",
              "Advertising and Promotion"),
        # Office Infra and Admin (parent) and its leaves
        _acct("4369050000000078353", "Office Infra and Admin", "E500030"),
        _acct("4369050000000000400", "Office Supplies", "E500030-20",
              "Office Infra and Admin"),
        _acct("4369050000000078189", "Utilities", "E500030-60",
              "Office Infra and Admin"),
    ]
)


def _row(**over):
    row = dict.fromkeys(EXPENSE_COLUMNS, "")
    row.update(
        {
            "Expense Date": "2026-07-09",
            "Expense Account": "Software & Subscriptions",
            "Expense Amount": "240.00",
            "Currency Code": "USD",
            "Reference#": "1200-2026-JUL",
            "Expense Description": "Vercel July usage",
        }
    )
    row.update(over)
    return row


def _plan(rows, *, org_id, tmp_path):
    """Plan one purchase per row, through the real caller."""
    groups = [ExpenseGroup(reference=r["Reference#"], rows=(r,)) for r in rows]
    ledger = PostLedger(tmp_path / f"plan-{org_id}.db")
    try:
        return plan_expense_post(
            groups,
            _COA,
            ledger,
            org_id=org_id,
            paid_through_account_id=CARD_ID,
            base_currency="USD",
        )
    finally:
        ledger.close()


# ── what it unblocks ────────────────────────────────────────────────


def test_a_mapped_category_posts_through_the_planner(tmp_path):
    """The headline: a category that matched nothing in the chart now
    plans to a real account id, end to end through `plan_expense_post`."""
    plan = _plan([_row()], org_id=SANDBOX_ORG_ID, tmp_path=tmp_path)
    assert plan.refusals == ()
    assert len(plan.postable) == 1
    payload = plan.postable[0].payload
    # IT: Cloud Subscriptions-Others, the unbranded subscriptions leaf.
    assert payload["account_id"] == "4369050000000078239"
    assert payload["amount"] == 240.0


def test_every_shipped_mapping_resolves_to_a_postable_account():
    """A typo in the map is a silent refusal in production and a wrong
    account nowhere; pin every entry against the real chart."""
    for category, code in CATEGORY_ACCOUNT_CODES[SANDBOX_ORG_ID].items():
        out = resolve_account_id(category, _COA, org_id=SANDBOX_ORG_ID)
        assert isinstance(out, ResolvedAccount), f"{category!r} -> {code!r}"
        assert out.code == code
        assert out.account_id


def test_every_shipped_mapping_targets_a_leaf_account():
    """Zoho posts only to leaves; a parent is a roll-up. The first draft
    of the map pointed three categories at parents (Professional Fees,
    Travel Expense, Marketing & Selling Expenses), so this assertion is
    the guard that mistake earned."""
    leaf_codes = {a.code for a in _COA.leaf_accounts()}
    for category, code in CATEGORY_ACCOUNT_CODES[SANDBOX_ORG_ID].items():
        assert code in leaf_codes, (
            f"{category!r} maps to {code!r}, which is a PARENT account in "
            "this chart; Zoho cannot post to it"
        )


def test_the_leaf_assertion_discriminates():
    """The guard above is only worth having if it can fail. A parent code
    must be visible as a non-leaf, or the test would pass on anything."""
    leaf_codes = {a.code for a in _COA.leaf_accounts()}
    for parent in ("E600060", "E100010", "E600010", "E500010", "E500030"):
        assert parent not in leaf_codes
    assert "E600060-70" in leaf_codes  # and a real leaf still registers


def test_resolution_records_which_category_supplied_the_account():
    """Provenance, so a reviewer can tell a category default from a rule
    somebody actually chose for that vendor."""
    out = resolve_account_id(
        "Meals & Entertainment", _COA, org_id=SANDBOX_ORG_ID
    )
    assert isinstance(out, ResolvedAccount)
    assert out.via_category == "Meals & Entertainment"
    assert out.name == "Travel Expense:Meals"


def test_case_and_spacing_fold():
    out = resolve_account_id(
        "  software   &   SUBSCRIPTIONS ", _COA, org_id=SANDBOX_ORG_ID
    )
    assert isinstance(out, ResolvedAccount)
    assert out.account_id == "4369050000000078239"


# ── what must still refuse (the half that makes it safe) ────────────


def test_an_unmapped_org_refuses_the_very_category_the_sandbox_posts(tmp_path):
    """The discrimination test, and the one that matters most. The same
    row that plans cleanly for the sandbox must refuse for a production
    org, or a sandbox guess has become an entry in Brisken's real books."""
    sandbox = _plan([_row()], org_id=SANDBOX_ORG_ID, tmp_path=tmp_path)
    production = _plan([_row()], org_id=A_PRODUCTION_ORG, tmp_path=tmp_path)

    assert len(sandbox.postable) == 1
    assert production.postable == ()
    assert len(production.refusals) == 1
    assert production.refusals[0].reason == REFUSAL_ACCOUNT
    assert REASON_UNKNOWN in production.refusals[0].detail


def test_omitting_the_org_refuses_exactly_as_before():
    """Back-compat, and the deny-by-default posture: the fallback is opt
    in per org, so an unthreaded caller cannot acquire it by accident."""
    out = resolve_account_id("Software & Subscriptions", _COA)
    assert isinstance(out, AccountRefusal)
    assert out.reason == REASON_UNKNOWN


def test_placeholders_are_never_mapped(tmp_path):
    """`(uncategorized - assign)` means a human still owes a decision.
    Mapping it would turn that into a number in the books, which is the
    whole failure this path exists to prevent."""
    for marker in NEVER_MAPPED:
        assert category_account_code(SANDBOX_ORG_ID, marker) is None

    plan = _plan(
        [_row(**{"Expense Account": "(uncategorized - assign)"})],
        org_id=SANDBOX_ORG_ID,
        tmp_path=tmp_path,
    )
    assert plan.postable == ()
    assert isinstance(plan.refusals[0], PostRefusal)
    assert REASON_PLACEHOLDER in plan.refusals[0].detail


def test_never_mapped_holds_the_export_s_own_card_and_entity_strings():
    """`NEVER_MAPPED` restates its markers as literals, deliberately, to
    keep the guarantee local and testable. That restatement is also where
    a rename in the export would go unnoticed: change
    `PAID_THROUGH_PLACEHOLDER` there and this set would quietly stop
    matching the cell it is meant to refuse."""
    assert {PAID_THROUGH_PLACEHOLDER, ENTITY_PLACEHOLDER} <= NEVER_MAPPED


def test_a_direct_reference_outranks_its_categorys_default():
    """Precedence from the M1 registry design: a vendor rule that already
    picked an account wins. A Microsoft subscription must land on the
    Microsoft leaf, not on the Software & Subscriptions default."""
    out = resolve_account_id("E500010-20", _COA, org_id=SANDBOX_ORG_ID)
    assert isinstance(out, ResolvedAccount)
    assert out.name == "IT: Cloud Subscriptions-Microsoft office"
    assert out.via_category == ""  # a direct match, not the fallback


def test_a_near_miss_category_refuses_rather_than_guessing():
    """Lookup is exact after folding, never fuzzy. A near-miss is fixed
    at the source; matching it here would post money on a guess."""
    for near in ("Software and Subscriptions", "Subscriptions", "Software"):
        out = resolve_account_id(near, _COA, org_id=SANDBOX_ORG_ID)
        assert isinstance(out, AccountRefusal), near
        assert out.reason == REASON_UNKNOWN


def test_a_mapping_to_a_code_no_chart_carries_is_its_own_refusal(monkeypatch):
    """A broken map and absent data want different fixes, so they get
    different reason codes."""
    import expense_recon.zoho.category_accounts as ca

    monkeypatch.setitem(
        ca._BY_ORG_NORMALIZED, SANDBOX_ORG_ID, {"software & subscriptions": "E999999"}
    )
    out = resolve_account_id(
        "Software & Subscriptions", _COA, org_id=SANDBOX_ORG_ID
    )
    assert isinstance(out, AccountRefusal)
    assert out.reason == REASON_CATEGORY_CODE_MISSING
    assert "E999999" in out.detail


def test_travel_and_transport_stays_unmapped_on_purpose():
    """Its July rows are gasoline and a vehicle rental, which belong to
    different leaves, and Travel Expense has no generic leaf. A default
    wrong half the time is worse than a refusal that names the row."""
    assert category_account_code(SANDBOX_ORG_ID, "Travel & Transport") is None
    out = resolve_account_id("Travel & Transport", _COA, org_id=SANDBOX_ORG_ID)
    assert isinstance(out, AccountRefusal)
    assert out.reason == REASON_UNKNOWN


def test_no_production_org_is_mapped():
    """Adding one is an owner decision. This test is the tripwire."""
    for org in PRODUCTION_ORG_IDS:
        assert org not in CATEGORY_ACCOUNT_CODES
        assert category_account_code(org, "Software & Subscriptions") is None


def test_a_split_refuses_whole_when_one_line_is_unmapped(tmp_path):
    """Splits post as one expense, so a single unmapped line must take
    the whole purchase with it rather than posting a partial amount."""
    ref = "1201-2026-JUL"
    group = ExpenseGroup(
        reference=ref,
        rows=(
            _row(**{"Reference#": ref, "Expense Amount": "100.00"}),
            _row(
                **{
                    "Reference#": ref,
                    "Expense Amount": "50.00",
                    "Expense Account": "Nothing In Any Chart",
                }
            ),
        ),
    )
    ledger = PostLedger(tmp_path / "split.db")
    try:
        plan = plan_expense_post(
            [group],
            _COA,
            ledger,
            org_id=SANDBOX_ORG_ID,
            paid_through_account_id=CARD_ID,
            base_currency="USD",
        )
    finally:
        ledger.close()
    assert plan.postable == ()
    assert plan.refusals[0].reason == REFUSAL_ACCOUNT
    assert plan.total == Decimal("0")
