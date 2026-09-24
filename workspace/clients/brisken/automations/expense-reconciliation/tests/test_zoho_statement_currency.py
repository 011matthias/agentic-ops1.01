"""Statement-currency posting, and the stale-date guard.

Two owner calls from 2026-09-23. The first adopts the house rule
`posting_common` already states for the journal: the bank statement is
what the company actually paid, so a EUR receipt on a USD card posts as
`amount x rate` USD. That also walks around TEST-BTS being on the FREE
Zoho plan, which rejects any expense in a non-base currency.

The second answers a real outlier: July's batch held a 2026-03-30 invoice
(ref 360172592, 360Crossmedia EUR 900). Four months out is not a
statement-date nuance, so rows that far back refuse and wait for a human.

Assertions run through `plan_expense_post` wherever they can, so removing
the wiring from the planner turns tests red rather than leaving them green.
"""
from __future__ import annotations

from decimal import Decimal

from expense_recon.ingest.chart_of_accounts import ChartOfAccounts
from expense_recon.output.zoho_expense_export import EXPENSE_COLUMNS
from expense_recon.zoho.expense_post import (
    AUDIT_PREFIX,
    MAX_DESCRIPTION_CHARS,
    REFUSAL_EXCHANGE_RATE,
    REFUSAL_STALE_DATE,
    ExpenseGroup,
    build_expense_payload,
    plan_expense_post,
)
from expense_recon.zoho.idempotent import PostLedger
from expense_recon.zoho.orgs import SANDBOX_ORG_ID

CARD = "4369050000000320002"
ACCT = "4369050000000078239"

_COA = ChartOfAccounts.from_api(
    [
        {
            "account_id": ACCT,
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
    ]
)


def _row(**over):
    row = dict.fromkeys(EXPENSE_COLUMNS, "")
    row.update(
        {
            "Expense Date": "2026-07-14",
            "Expense Account": "Software & Subscriptions",
            "Expense Amount": "100.00",
            "Currency Code": "EUR",
            "Exchange Rate": "1.162275",
            "Reference#": "EUR-1",
            "Vendor": "Anthropic, PBC",
        }
    )
    row.update(over)
    return row


def _group(*rows):
    return ExpenseGroup(reference=rows[0]["Reference#"], rows=tuple(rows))


def _build(group, **kw):
    kw.setdefault("convert_foreign_to_base", True)
    kw.setdefault("org_id", SANDBOX_ORG_ID)
    return build_expense_payload(
        group, _COA, paid_through_account_id=CARD, base_currency="USD", **kw
    )


def _plan(groups, tmp_path, **kw):
    kw.setdefault("convert_foreign_to_base", True)
    ledger = PostLedger(tmp_path / "s.db")
    try:
        return plan_expense_post(
            groups, _COA, ledger, org_id=SANDBOX_ORG_ID,
            paid_through_account_id=CARD, base_currency="USD", **kw,
        )
    finally:
        ledger.close()


# ── conversion ──────────────────────────────────────────────────────


def test_a_eur_purchase_posts_as_usd_through_the_planner(tmp_path):
    """100.00 EUR at 1.162275 is what the card was charged: 116.23 USD."""
    plan = _plan([_group(_row())], tmp_path)
    assert plan.refusals == ()
    p = plan.postable[0].payload
    assert p["currency_code"] == "USD"
    assert p["amount"] == 116.23
    assert "currency_id" not in p
    assert "exchange_rate" not in p


def test_the_note_carries_the_original_amount_and_rate():
    """Without it the books show a USD figure with no trace of the EUR
    receipt, and the conversion is unauditable from the record."""
    out = _build(_group(_row()))
    assert "Original: EUR 100.00 @ 1.162275" in out["description"]


def test_a_brl_purchase_converts_too():
    """BRL is not defined in TEST-BTS at all, so conversion is the ONLY
    route for 20 of July's purchases."""
    out = _build(
        _group(_row(**{"Currency Code": "BRL", "Exchange Rate": "0.197000",
                       "Expense Amount": "340.00"}))
    )
    assert out["currency_code"] == "USD"
    assert out["amount"] == 66.98  # 340.00 * 0.197
    assert "Original: BRL 340.00 @ 0.197000" in out["description"]


def test_split_lines_sum_to_the_converted_total_exactly():
    """Rounding each line alone does not give the rounded total: two
    lines of 10.005 round to 10.01 each (20.02) while the total rounds
    to 20.01. A one-cent disagreement between an expense and its own
    lines is exactly the quiet wrong that survives review."""
    ref = "SPLIT-1"
    out = _build(
        _group(
            _row(**{"Reference#": ref, "Expense Amount": "10.00",
                    "Exchange Rate": "1.0005"}),
            _row(**{"Reference#": ref, "Expense Amount": "10.00",
                    "Exchange Rate": "1.0005"}),
        )
    )
    lines = out["line_items"]
    assert len(lines) == 2
    total = sum(Decimal(str(li["amount"])) for li in lines)
    assert total == Decimal("20.01")
    assert Decimal(str(lines[0]["amount"])) != Decimal(str(lines[1]["amount"]))


def test_a_usd_row_is_untouched_by_conversion():
    """The 13 already-posted USD rows must build byte-identically."""
    out = _build(_group(_row(**{"Currency Code": "USD", "Exchange Rate": ""})))
    assert out["currency_code"] == "USD"
    assert out["amount"] == 100.0
    assert "Original:" not in out["description"]


def test_conversion_without_a_rate_refuses(tmp_path):
    """Inventing a rate would misstate what the card was charged."""
    for bad in ("", "0", "-1", "abc"):
        plan = _plan([_group(_row(**{"Exchange Rate": bad}))], tmp_path)
        assert plan.postable == (), bad
        assert plan.refusals[0].reason == REFUSAL_EXCHANGE_RATE, bad


def test_conversion_is_off_by_default(tmp_path):
    """Deny-by-default: a caller that does not opt in cannot silently
    start rewriting foreign amounts."""
    plan = _plan([_group(_row())], tmp_path, convert_foreign_to_base=False)
    assert plan.postable == ()


def test_the_conversion_flag_discriminates(tmp_path):
    """Same row, flag on and off, must differ. A flag that changes
    nothing would make every assertion above meaningless."""
    on = _plan([_group(_row())], tmp_path, convert_foreign_to_base=True)
    off = _plan([_group(_row())], tmp_path, convert_foreign_to_base=False)
    assert len(on.postable) == 1 and off.postable == ()


# ── stale-date guard ────────────────────────────────────────────────


def test_the_march_invoice_refuses(tmp_path):
    """The real outlier: 2026-03-30 inside a 2026-07 batch."""
    plan = _plan(
        [_group(_row(**{"Expense Date": "2026-03-30", "Reference#": "360172592"}))],
        tmp_path,
        period="2026-07",
    )
    assert plan.postable == ()
    assert plan.refusals[0].reason == REFUSAL_STALE_DATE
    assert "2026-03-30" in plan.refusals[0].detail
    assert "2026-05-17" in plan.refusals[0].detail  # the cutoff, named


def test_the_june_rows_still_post(tmp_path):
    """45 days must clear the ordinary case: a charge landing in the next
    statement cycle. July's three June-dated rows are legitimate."""
    for d in ("2026-06-30", "2026-06-21", "2026-05-17"):
        plan = _plan([_group(_row(**{"Expense Date": d}))], tmp_path,
                     period="2026-07")
        assert len(plan.postable) == 1, d


def test_the_cutoff_is_exact(tmp_path):
    """One day either side of 2026-05-17, so the boundary is pinned and
    an off-by-one cannot hide."""
    ok = _plan([_group(_row(**{"Expense Date": "2026-05-17"}))], tmp_path,
               period="2026-07")
    bad = _plan([_group(_row(**{"Expense Date": "2026-05-16"}))], tmp_path,
                period="2026-07")
    assert len(ok.postable) == 1
    assert bad.postable == ()
    assert bad.refusals[0].reason == REFUSAL_STALE_DATE


def test_an_unreadable_date_refuses_when_the_guard_is_on(tmp_path):
    """A row whose date cannot be verified is not posted. One July EUR
    row has no Expense Date at all."""
    for bad in ("", "not-a-date", "2026-13-01"):
        plan = _plan([_group(_row(**{"Expense Date": bad}))], tmp_path,
                     period="2026-07")
        assert plan.postable == (), bad
        assert plan.refusals[0].reason == REFUSAL_STALE_DATE, bad


def test_without_a_period_the_guard_is_off(tmp_path):
    """Opt-in, so existing callers keep their behaviour."""
    plan = _plan([_group(_row(**{"Expense Date": "2020-01-01"}))], tmp_path)
    assert len(plan.postable) == 1


def test_the_window_is_configurable(tmp_path):
    """A wider window must actually admit the March row, or `stale_days`
    is decoration rather than a control."""
    row = _row(**{"Expense Date": "2026-03-30"})
    tight = _plan([_group(row)], tmp_path, period="2026-07")
    wide = _plan([_group(row)], tmp_path, period="2026-07", stale_days=200)
    assert tight.postable == ()
    assert len(wide.postable) == 1


# ── Zoho's 500-character description cap ────────────────────────────


def test_a_long_receipt_is_trimmed_to_fit_zohos_cap():
    """Two July grocery receipts were rejected 400 for descriptions of
    523 and 630 characters. The cap is real and it bites."""
    out = _build(_group(_row(**{"Expense Description": "ITEM; " * 120})))
    assert len(out["description"]) <= MAX_DESCRIPTION_CHARS


def test_trimming_takes_the_prose_and_keeps_the_whole_envelope():
    """The envelope is the audit trail; the prose is a line-item list.
    Cutting the envelope to fit would trade traceability for text."""
    desc = _build(_group(_row(**{"Expense Description": "ITEM; " * 120})))[
        "description"
    ]
    for required in (
        AUDIT_PREFIX,
        "Ref: EUR-1",
        "Source: expense-recon",
        "Vendor: Anthropic, PBC",
        "Original: EUR 100.00 @ 1.162275",
    ):
        assert required in desc, required


def test_the_trim_says_how_much_it_dropped():
    """A silent truncation reads as a short receipt."""
    # Stripped, because `ExpenseGroup.cell` strips: comparing against the
    # unstripped literal is off by the trailing space.
    own = ("ITEM; " * 120).strip()
    desc = _build(_group(_row(**{"Expense Description": own})))["description"]
    assert "... (+" in desc and " chars)" in desc
    dropped = int(desc.split("... (+")[1].split(" chars)")[0])
    kept = len(own) - dropped
    assert 0 < kept < len(own)
    assert own[:kept] in desc


def test_a_short_description_is_untouched():
    """The rows already posted must not drift: only 2 of 46 July
    purchases were ever over the cap."""
    desc = _build(_group(_row(**{"Expense Description": "one line"})))[
        "description"
    ]
    assert desc.endswith("| one line")
    assert "... (+" not in desc
