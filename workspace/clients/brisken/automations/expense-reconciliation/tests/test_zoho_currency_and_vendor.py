"""Foreign-currency posting, and the vendor that only survives in the note.

Two fixes from the 2026-09-23 rehearsal, both measured rather than
assumed:

* `vendor_name` is discarded by Zoho. All 13 posted expenses read back
  `vendor_name=""` and `vendor_id=""`, so the vendor now rides in the
  audit envelope, which does survive.
* Foreign rows refused for want of a `currency_id`. The org's currency
  map supplies it, and the RATE comes from the reviewed CSV rather than
  from a lookup at post time, so what posts is what a human approved.

As in the category-map suite, the assertions run through
`plan_expense_post` wherever they can: a suite that only exercised
`build_expense_payload` would stay green if the planner stopped passing
`currencies` down.
"""
from __future__ import annotations

from expense_recon.ingest.chart_of_accounts import ChartOfAccounts
from expense_recon.output.zoho_expense_export import EXPENSE_COLUMNS
from expense_recon.zoho.expense_post import (
    AUDIT_PREFIX,
    REFUSAL_CURRENCY,
    REFUSAL_CURRENCY_UNDEFINED,
    REFUSAL_EXCHANGE_RATE,
    ExpenseGroup,
    audit_note,
    build_expense_payload,
    plan_expense_post,
)
from expense_recon.zoho.idempotent import PostLedger
from expense_recon.zoho.orgs import SANDBOX_ORG_ID

CARD = "4369050000000320002"

# The real TEST-BTS ids, so a wrong constant fails here not in Zoho.
CURRENCIES = {
    "USD": "4369050000000000097",
    "EUR": "4369050000000000109",
}
EUR_ID = CURRENCIES["EUR"]

_COA = ChartOfAccounts.from_api(
    [
        {
            "account_id": "4369050000000078239",
            "account_name": "IT: Cloud Subscriptions-Others",
            "account_code": "E500010-30",
            "account_type": "expense",
            "is_active": True,
            "parent_account_name": "IT: Computer and Internet Expenses",
        },
        {
            "account_id": "4369050000000078183",
            "account_name": "IT: Computer and Internet Expenses",
            "account_code": "E500010",
            "account_type": "expense",
            "is_active": True,
        },
        {
            "account_id": CARD,
            "account_name": "Visa dummy card Matthias",
            "account_code": "",
            "account_type": "credit_card",
            "is_active": True,
        },
    ]
)


def _row(**over):
    row = dict.fromkeys(EXPENSE_COLUMNS, "")
    row.update(
        {
            "Expense Date": "2026-07-30",
            "Expense Account": "IT: Cloud Subscriptions-Others",
            "Expense Amount": "100.00",
            "Currency Code": "EUR",
            "Exchange Rate": "1.162275",
            "Reference#": "EUR-1",
            "Vendor": "Konsultancy Finance",
            "Expense Description": "(receipt total, no itemization)",
        }
    )
    row.update(over)
    return row


def _group(*rows):
    return ExpenseGroup(reference=rows[0]["Reference#"], rows=tuple(rows))


def _build(group, **kw):
    kw.setdefault("currencies", CURRENCIES)
    kw.setdefault("org_id", SANDBOX_ORG_ID)
    return build_expense_payload(
        group, _COA, paid_through_account_id=CARD, base_currency="USD", **kw
    )


def _plan(groups, tmp_path, **kw):
    kw.setdefault("currencies", CURRENCIES)
    ledger = PostLedger(tmp_path / "fx.db")
    try:
        return plan_expense_post(
            groups, _COA, ledger, org_id=SANDBOX_ORG_ID,
            paid_through_account_id=CARD, base_currency="USD", **kw,
        )
    finally:
        ledger.close()


# ── currency ────────────────────────────────────────────────────────


def test_a_eur_purchase_plans_with_the_orgs_currency_id(tmp_path):
    """The headline, through the planner: what refused yesterday now
    carries the org's numeric currency_id and the reviewed rate."""
    plan = _plan([_group(_row())], tmp_path)
    assert plan.refusals == ()
    payload = plan.postable[0].payload
    assert payload["currency_id"] == EUR_ID
    assert payload["currency_code"] == "EUR"
    assert payload["exchange_rate"] == 1.162275


def test_the_rate_is_the_csvs_own_not_a_lookup():
    """Post the reviewed artifact: an odd rate in the CSV must reach the
    payload verbatim, never be replaced by a 'correct' one."""
    out = _build(_group(_row(**{"Exchange Rate": "1.000001"})))
    assert out["exchange_rate"] == 1.000001


def test_a_base_currency_row_carries_no_fx_fields():
    """USD rows must be untouched by this change: no currency_id, no
    exchange_rate, exactly the payload that posted 13/13 yesterday."""
    out = _build(_group(_row(**{"Currency Code": "USD", "Exchange Rate": ""})))
    assert "currency_id" not in out
    assert "exchange_rate" not in out
    assert out["currency_code"] == "USD"


def test_a_currency_the_org_does_not_define_refuses(tmp_path):
    """BRL is 20 of July's purchases and TEST-BTS defines no BRL. That is
    a config gap in the target org, and it gets its own reason code so it
    is not confused with missing data."""
    plan = _plan([_group(_row(**{"Currency Code": "BRL", "Reference#": "BRL-1"}))],
                 tmp_path)
    assert plan.postable == ()
    assert plan.refusals[0].reason == REFUSAL_CURRENCY_UNDEFINED
    assert "BRL" in plan.refusals[0].detail


def test_a_foreign_row_without_a_rate_refuses(tmp_path):
    """Zoho would apply a rate nobody chose, misstating the amount in
    exactly the silent way this path exists to refuse."""
    for bad in ("", "   ", "0", "-1.5", "not-a-number"):
        plan = _plan([_group(_row(**{"Exchange Rate": bad}))], tmp_path)
        assert plan.postable == (), bad
        assert plan.refusals[0].reason == REFUSAL_EXCHANGE_RATE, bad


def test_without_a_currency_map_a_foreign_row_refuses_as_before(tmp_path):
    """Deny-by-default survives: the map is opt-in, so a caller that does
    not supply one cannot acquire foreign posting by accident."""
    plan = _plan([_group(_row())], tmp_path, currencies=None)
    assert plan.postable == ()
    assert plan.refusals[0].reason == REFUSAL_CURRENCY


def test_the_currency_map_discriminates(tmp_path):
    """The map must be the thing that decides. Same row, two maps: one
    that knows EUR and one that does not."""
    known = _plan([_group(_row())], tmp_path, currencies=CURRENCIES)
    unknown = _plan([_group(_row())], tmp_path, currencies={"USD": "1"})
    assert len(known.postable) == 1
    assert unknown.postable == ()
    assert unknown.refusals[0].reason == REFUSAL_CURRENCY_UNDEFINED


# ── vendor ──────────────────────────────────────────────────────────


def test_the_vendor_rides_in_the_audit_envelope():
    """`vendor_name` does not survive the POST, so the note carries it."""
    note = audit_note(_group(_row()), source="expense-recon")
    assert note.startswith(AUDIT_PREFIX)
    assert "Vendor: Konsultancy Finance" in note


def test_the_vendor_reaches_the_posted_description(tmp_path):
    """Through the planner, because the description is what a reviewer
    actually reads in the Zoho UI."""
    plan = _plan([_group(_row())], tmp_path)
    assert "Vendor: Konsultancy Finance" in plan.postable[0].payload["description"]


def test_a_split_carries_the_vendor_too():
    """The 2026-09-22 trial lost the envelope on exactly the split; the
    vendor must not repeat that."""
    ref = "EUR-SPLIT"
    note = audit_note(
        _group(_row(**{"Reference#": ref}), _row(**{"Reference#": ref})),
        source="expense-recon",
    )
    assert "Vendor: Konsultancy Finance" in note
    assert "Split: 2 accounts" in note


def test_a_blank_vendor_adds_no_empty_field():
    """No `Vendor: ` with nothing after it, which would read as data."""
    note = audit_note(_group(_row(**{"Vendor": ""})), source="expense-recon")
    assert "Vendor:" not in note


def test_vendor_name_is_still_sent_for_the_day_contacts_exist():
    """Inert today (Zoho drops it without a contact), kept so the field
    starts working the moment vendor contacts are resolved."""
    out = _build(_group(_row()))
    assert out["vendor_name"] == "Konsultancy Finance"
