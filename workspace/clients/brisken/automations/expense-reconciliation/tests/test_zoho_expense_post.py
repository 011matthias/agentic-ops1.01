"""Payload builder and guarded post loop for the month-end injection.

The contract is mostly about refusing. A wrong expense that posts cleanly
is the failure mode this whole path exists to prevent: in the 2026-09-22
trial Zoho returned 201 with a valid expense_id on rows that had landed in
the wrong account and on a split that had lost its audit trail.
"""
from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal

import pytest

from expense_recon.ingest.chart_of_accounts import ChartOfAccounts
from expense_recon.output.zoho_expense_export import EXPENSE_COLUMNS
from expense_recon.zoho.expense_post import (
    AUDIT_PREFIX,
    REFUSAL_ACCOUNT,
    REFUSAL_AMOUNT,
    REFUSAL_CURRENCY,
    REFUSAL_LEDGER,
    ExpenseGroup,
    PostRefusal,
    audit_note,
    build_expense_payload,
    execute_expense_post,
    group_by_reference,
    plan_expense_post,
    read_expense_csv,
    reference_date_spread,
)
from expense_recon.zoho.idempotent import PostLedger

CARD_ID = "4369050000000320002"
BASE = "USD"

_COA = ChartOfAccounts.from_api(
    [
        {
            "account_id": "4369050000000078277",
            "account_name": "COGS - CLOUD Infrastructure (ePaaS)",
            "account_code": "E700030-20",
            "account_type": "cost_of_goods_sold",
            "is_active": True,
        },
        {
            "account_id": "4369050000000078287",
            "account_name": "COGS - Other Infra and IT Costs for Cloud Business",
            "account_code": "E700030-30",
            "account_type": "cost_of_goods_sold",
            "is_active": True,
        },
        # The card the payloads are paid from (item 184 checks it here).
        {
            "account_id": CARD_ID,
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
            "Expense Date": "2026-07-09",
            "Expense Account": "COGS - CLOUD Infrastructure (ePaaS)",
            "Expense Amount": "2400.00",
            "Currency Code": "USD",
            "Reference#": "1188-2026-JUL",
            "Expense Description": "AWS July usage",
        }
    )
    row.update(over)
    return row


def _group(*rows):
    return ExpenseGroup(reference=rows[0]["Reference#"], rows=tuple(rows))


def _build(group, **kw):
    return build_expense_payload(
        group,
        _COA,
        paid_through_account_id=CARD_ID,
        base_currency=BASE,
        **kw,
    )


# ── reading the reviewed artifact ───────────────────────────────────


def test_read_stops_at_the_footer_rather_than_parsing_prose(tmp_path):
    """`write_zoho_expense_export` appends a prose footer under a blank
    row. A reader that merely skipped blanks would parse an English
    sentence as an expense."""
    path = tmp_path / "expenses.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(EXPENSE_COLUMNS)
        w.writerow([_row()[c] for c in EXPENSE_COLUMNS])
        w.writerow([])
        w.writerow(["Amounts are as printed on each receipt."])
    rows = read_expense_csv(path)
    assert len(rows) == 1
    assert rows[0]["Reference#"] == "1188-2026-JUL"


def test_read_rejects_a_foreign_header(tmp_path):
    path = tmp_path / "wrong.csv"
    path.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    with pytest.raises(ValueError, match="header mismatch"):
        read_expense_csv(path)


# ── grouping ────────────────────────────────────────────────────────


def test_split_rows_sharing_a_reference_become_one_purchase():
    rows = [
        _row(),
        _row(
            **{
                "Expense Account": "COGS - Other Infra and IT Costs for Cloud Business",
                "Expense Amount": "447.31",
            }
        ),
    ]
    groups = group_by_reference(rows)
    assert len(groups) == 1
    assert groups[0].is_split
    assert len(groups[0].rows) == 2


def test_blank_references_never_merge_into_one_expense():
    """Merging on a shared ABSENCE would fuse unrelated purchases into a
    single record that still ties out to the cent."""
    groups = group_by_reference([_row(**{"Reference#": ""}) for _ in range(3)])
    assert len(groups) == 3


def test_grouping_preserves_first_appearance_order():
    rows = [_row(**{"Reference#": "B"}), _row(**{"Reference#": "A"}), _row(**{"Reference#": "B"})]
    assert [g.reference for g in group_by_reference(rows)] == ["B", "A"]


# ── payload ─────────────────────────────────────────────────────────


def test_a_single_account_expense_posts_flat_with_a_resolved_id():
    payload = _build(_group(_row()))
    assert payload["account_id"] == "4369050000000078277"
    assert payload["amount"] == 2400.0
    assert payload["paid_through_account_id"] == CARD_ID
    assert payload["reference_number"] == "1188-2026-JUL"
    assert "line_items" not in payload


def test_a_split_posts_itemized_and_the_lines_tie_out():
    group = _group(
        _row(),
        _row(
            **{
                "Expense Account": "COGS - Other Infra and IT Costs for Cloud Business",
                "Expense Amount": "447.31",
            }
        ),
    )
    payload = _build(group)
    assert "account_id" not in payload
    ids = [li["account_id"] for li in payload["line_items"]]
    assert ids == ["4369050000000078277", "4369050000000078287"]
    assert sum(Decimal(str(li["amount"])) for li in payload["line_items"]) == Decimal(
        "2847.31"
    )


@pytest.mark.parametrize("split", [False, True])
def test_the_audit_envelope_is_on_both_shapes(split):
    """The trial put it on 7 of 9 and lost it on exactly the split,
    because the itemized path wrote a different description. One builder,
    both shapes, asserted here so that cannot recur."""
    rows = [_row()]
    if split:
        rows.append(
            _row(
                **{
                    "Expense Account": "COGS - Other Infra and IT Costs for Cloud Business",
                    "Expense Amount": "447.31",
                }
            )
        )
    payload = _build(_group(*rows))
    assert payload["description"].startswith(AUDIT_PREFIX)
    assert "1188-2026-JUL" in payload["description"]


def test_the_audit_envelope_keeps_the_rows_own_description():
    note = audit_note(_group(_row()), source="expense-recon")
    assert note.startswith(AUDIT_PREFIX)
    assert "AWS July usage" in note


def test_an_unresolved_account_refuses_instead_of_defaulting():
    payload = _build(_group(_row(**{"Expense Account": "Meals & Entertainment"})))
    assert isinstance(payload, PostRefusal)
    assert payload.reason == REFUSAL_ACCOUNT


def test_a_blank_amount_refuses_because_blank_is_not_zero():
    """The export writes a blank amount when a receipt's total was never
    read. Coercing that to 0 would post a real expense worth nothing."""
    payload = _build(_group(_row(**{"Expense Amount": ""})))
    assert isinstance(payload, PostRefusal)
    assert payload.reason == REFUSAL_AMOUNT


def test_a_foreign_currency_refuses_while_settings_read_is_missing():
    """Zoho wants a currency_id, not a code, and the re-consented grant
    dropped settings.READ so /settings/currencies 401s. Assuming base
    currency for a BRL charge would misstate the amount."""
    payload = _build(_group(_row(**{"Currency Code": "BRL"})))
    assert isinstance(payload, PostRefusal)
    assert payload.reason == REFUSAL_CURRENCY


# ── plan + post ─────────────────────────────────────────────────────


class FakeClient:
    def __init__(self, fail=None):
        self.fail = fail or {}
        self.posted: list[dict] = []
        self._n = 0

    def create_expense(self, payload):
        ref = payload.get("reference_number")
        if ref in self.fail:
            raise self.fail[ref]
        self._n += 1
        self.posted.append(payload)
        return {"expense_id": f"E{self._n}"}


def _ledger(tmp_path):
    return PostLedger(tmp_path / "ledger.db")


def test_plan_partitions_and_post_writes_each_once(tmp_path):
    groups = group_by_reference([_row(), _row(**{"Reference#": "R2"})])
    with _ledger(tmp_path) as ledger:
        plan = plan_expense_post(
            groups,
            _COA,
            ledger,
            org_id="822116290",
            paid_through_account_id=CARD_ID,
            base_currency=BASE,
        )
        assert len(plan.postable) == 2
        assert not plan.refusals
        client = FakeClient()
        report = execute_expense_post(client, plan, ledger, go=True)
        assert report.ok
        assert len(report.posted) == 2
        assert len(client.posted) == 2


def test_a_second_run_of_the_same_month_posts_nothing(tmp_path):
    """The ledger's whole job. A re-run must plan zero postable, not
    re-post what already landed."""
    groups = group_by_reference([_row()])
    with _ledger(tmp_path) as ledger:
        first = plan_expense_post(
            groups, _COA, ledger, org_id="822116290",
            paid_through_account_id=CARD_ID, base_currency=BASE,
        )
        client = FakeClient()
        execute_expense_post(client, first, ledger, go=True)

        second = plan_expense_post(
            groups, _COA, ledger, org_id="822116290",
            paid_through_account_id=CARD_ID, base_currency=BASE,
        )
        assert not second.postable
        assert [r.reason for r in second.refusals] == [REFUSAL_LEDGER]
        assert len(client.posted) == 1


def test_posting_refuses_without_go(tmp_path):
    groups = group_by_reference([_row()])
    with _ledger(tmp_path) as ledger:
        plan = plan_expense_post(
            groups, _COA, ledger, org_id="822116290",
            paid_through_account_id=CARD_ID, base_currency=BASE,
        )
        with pytest.raises(ValueError, match="go=True"):
            execute_expense_post(FakeClient(), plan, ledger, go=False)


def test_posting_refuses_a_plan_that_carries_refusals(tmp_path):
    """A partial post leaves a month half-entered, which is harder to
    reason about than one that never started."""
    groups = group_by_reference(
        [_row(), _row(**{"Reference#": "R2", "Expense Account": "Nope"})]
    )
    with _ledger(tmp_path) as ledger:
        plan = plan_expense_post(
            groups, _COA, ledger, org_id="822116290",
            paid_through_account_id=CARD_ID, base_currency=BASE,
        )
        assert plan.refusals
        with pytest.raises(ValueError, match="refusal"):
            execute_expense_post(FakeClient(), plan, ledger, go=True)


def test_the_expect_count_aborts_the_whole_batch(tmp_path):
    groups = group_by_reference([_row(), _row(**{"Reference#": "R2"})])
    with _ledger(tmp_path) as ledger:
        plan = plan_expense_post(
            groups, _COA, ledger, org_id="822116290",
            paid_through_account_id=CARD_ID, base_currency=BASE,
        )
        client = FakeClient()
        with pytest.raises(ValueError, match="expected exactly 5"):
            execute_expense_post(client, plan, ledger, go=True, expect=5)
        assert client.posted == []


def test_a_4xx_rejection_releases_the_intent_and_the_batch_continues(tmp_path):
    """Zoho answered and wrote nothing, so the reference must be postable
    again after a fix rather than wedged in the ledger."""
    err = RuntimeError("invalid account")
    err.status = 400
    groups = group_by_reference([_row(), _row(**{"Reference#": "R2"})])
    with _ledger(tmp_path) as ledger:
        plan = plan_expense_post(
            groups, _COA, ledger, org_id="822116290",
            paid_through_account_id=CARD_ID, base_currency=BASE,
        )
        report = execute_expense_post(
            FakeClient(fail={"1188-2026-JUL": err}), plan, ledger, go=True
        )
        assert not report.ok
        assert len(report.rejected) == 1
        assert len(report.posted) == 1  # the batch continued
        assert ledger.status_for("822116290", "1188-2026-JUL") is None


def test_an_unknown_outcome_marks_ambiguous_and_aborts_the_rest(tmp_path):
    """A timeout leaves the commit state unknown. Continuing past that is
    how one uncertainty becomes several."""
    groups = group_by_reference([_row(), _row(**{"Reference#": "R2"})])
    with _ledger(tmp_path) as ledger:
        plan = plan_expense_post(
            groups, _COA, ledger, org_id="822116290",
            paid_through_account_id=CARD_ID, base_currency=BASE,
        )
        client = FakeClient(fail={"1188-2026-JUL": TimeoutError("no answer")})
        report = execute_expense_post(client, plan, ledger, go=True)
        assert report.aborted
        assert not report.ok
        assert len(report.ambiguous) == 1
        assert client.posted == []  # nothing after the unknown
        row = ledger.status_for("822116290", "1188-2026-JUL")
        assert row is not None and row.state == "ambiguous"


# ── the date-spread helper ──────────────────────────────────────────


@pytest.mark.parametrize(
    ("dates", "expect"),
    [
        # Hostinger: two documents on one invoice number.
        (("2026-07-03", "2026-07-28"), (date(2026, 7, 3), date(2026, 7, 28))),
        # A genuine split: one receipt, one date, zero spread.
        (("2026-07-14", "2026-07-14"), (date(2026, 7, 14), date(2026, 7, 14))),
        # Fewer than two readable dates is no spread. The unreadable
        # cases belong to `date_precedes_period_window`, which names them
        # better than a spread could.
        (("2026-07-14",), None),
        (("2026-07-14", ""), None),
        (("2026-07-14", "not-a-date"), None),
        (("", ""), None),
        # Min and max, not first and last: CSV order is not date order.
        (("2026-07-28", "2026-07-03", "2026-07-10"),
         (date(2026, 7, 3), date(2026, 7, 28))),
    ],
)
def test_the_spread_reads_min_and_max_of_the_readable_dates(dates, expect):
    group = ExpenseGroup(
        reference="R", rows=tuple({"Expense Date": d} for d in dates)
    )
    assert reference_date_spread(group) == expect
