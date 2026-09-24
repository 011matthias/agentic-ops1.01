"""The unified month-end runner, driven THROUGH `run_month` and `main`.

Every assertion here goes through the runner, not the pieces it composes,
so unthreading a flag from the runner's plan call (`period=`,
`convert_foreign_to_base=`) turns a test red rather than leaving a green
suite that proves only the helpers. The fake client is the whole network:
no test reaches Zoho.
"""
from __future__ import annotations

import csv
import sqlite3
from decimal import Decimal

import pytest

from expense_recon.output.zoho_expense_export import (
    ENTITY_PLACEHOLDER,
    EXPENSE_COLUMNS,
    PAID_THROUGH_PLACEHOLDER,
)
from expense_recon.zoho import reconcile_month as rm
from expense_recon.zoho.client import ZohoAPIError
from expense_recon.zoho.expense_post import (
    REFUSAL_ACCOUNT,
    REFUSAL_CONFLICTING_DATES,
    REFUSAL_LEDGER,
    REFUSAL_STALE_DATE,
    REFUSAL_UNASSIGNED,
)
from expense_recon.zoho.idempotent import PostLedger
from expense_recon.zoho.occupancy import (
    VERDICT_ALREADY_OCCUPIED,
    VERDICT_CLEAR,
    VERDICT_UNVERIFIABLE,
)
from expense_recon.zoho.orgs import PRODUCTION_ORG_IDS, SANDBOX_ORG_ID
from expense_recon.zoho.reconcile_month import (
    POST_ENV,
    REFUSAL_BLANK_REFERENCE,
    OrgRefused,
    RunRefused,
    compare_expense,
    main,
    run_month,
)

ORG = SANDBOX_ORG_ID
CARD = "4369050000000320002"
CARD_NAME = "Visa dummy card Matthias"
SOFTWARE = "4369050000000078239"  # E500010-30, IT: Cloud Subscriptions-Others
OFFICE = "4369050000000078300"  # E500030-20, Office Supplies

CHART = [
    {
        "account_id": SOFTWARE,
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
        "account_id": OFFICE,
        "account_name": "Office Supplies",
        "account_code": "E500030-20",
        "account_type": "expense",
        "is_active": True,
    },
]


# ── fixtures ────────────────────────────────────────────────────────


def _row(**over):
    row = dict.fromkeys(EXPENSE_COLUMNS, "")
    row.update(
        {
            "Expense Date": "2026-07-14",
            "Expense Account": "IT: Cloud Subscriptions-Others",
            "Expense Amount": "100.00",
            "Currency Code": "USD",
            "Exchange Rate": "",
            "Reference#": "R1",
            "Vendor": "Anthropic, PBC",
            "Expense Description": "Claude Max",
            "Legal Entity": "Corporate Services",
        }
    )
    row.update(over)
    return row


def _csv(tmp_path, rows, name="july.csv"):
    """A reviewed export, footer and all, so the reader's blank-row stop is
    exercised through the runner rather than assumed."""
    path = tmp_path / name
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(EXPENSE_COLUMNS)
        for row in rows:
            writer.writerow([row[c] for c in EXPENSE_COLUMNS])
        writer.writerow([""] * len(EXPENSE_COLUMNS))
        writer.writerow(["Prose footer that must not parse as a row."] + [""] * (len(EXPENSE_COLUMNS) - 1))
    return path


def _stored(payload, expense_id):
    """What Zoho hands back for a posted payload."""
    if payload.get("line_items"):
        lines = [dict(li) for li in payload["line_items"]]
        total = sum(Decimal(str(li["amount"])) for li in lines)
        account_id = ""
    else:
        lines = [{"account_id": payload["account_id"], "amount": payload["amount"]}]
        total = Decimal(str(payload["amount"]))
        account_id = payload["account_id"]
    return {
        "expense_id": expense_id,
        "date": payload["date"],
        "reference_number": payload["reference_number"],
        "total": float(total),
        "amount": float(total),
        "currency_code": payload["currency_code"],
        "paid_through_account_id": payload["paid_through_account_id"],
        "paid_through_account_name": CARD_NAME,
        "account_id": account_id,
        "line_items": lines,
        "description": payload["description"],
        "vendor_name": "",
    }


def _existing(date="2026-07-05", ref="HAND-1", card=CARD_NAME, expense_id="OLD1"):
    return {
        "expense_id": expense_id,
        "date": date,
        "total": 12.5,
        "reference_number": ref,
        "paid_through_account_name": card,
        "description": "hand-entered",
    }


class FakeClient:
    """The whole network. Records every call so a test can prove what the
    runner did NOT do (no chart pull after an abort, no POST on a dry run)."""

    def __init__(self, *, existing=(), fail=None, corrupt=None,
                 occupancy_raises=None):
        self.existing = list(existing)
        self.created: list[dict] = []
        self.fail = fail or {}
        self.corrupt = corrupt or (lambda rec: rec)
        self.occupancy_raises = occupancy_raises
        self.calls: list[str] = []
        self._n = 0

    def list_chart_of_accounts(self):
        self.calls.append("coa")
        return [dict(a) for a in CHART]

    def list_expenses(self, *, date_start=None, date_end=None):
        self.calls.append("list")
        if self.occupancy_raises is not None:
            raise self.occupancy_raises
        out = []
        for rec in self.existing + self.created:
            d = rec.get("date") or ""
            if date_start is not None and d < date_start:
                continue
            if date_end is not None and d > date_end:
                continue
            out.append(dict(rec))
        return out

    def create_expense(self, payload):
        self.calls.append("create")
        ref = payload.get("reference_number")
        if ref in self.fail:
            raise self.fail[ref]
        self._n += 1
        rec = _stored(payload, f"NEW{self._n}")
        self.created.append(rec)
        return {"expense_id": rec["expense_id"]}

    def _get(self, path, params=None):
        self.calls.append("get")
        eid = path.rsplit("/", 1)[1]
        for rec in self.existing + self.created:
            if rec["expense_id"] == eid:
                return {"code": 0, "expense": self.corrupt(dict(rec))}
        raise ZohoAPIError(f"no expense {eid}", status=404)


class NeverPosts(FakeClient):
    def create_expense(self, payload):
        raise AssertionError("create_expense must not be reached on this path")


def _boom(org_id):
    raise AssertionError("no client may be constructed on this path")


def _run(tmp_path, rows, *, client, dry_run=True, env=None, **kw):
    lines: list[str] = []
    ledger = tmp_path / "ledger.sqlite"
    run = run_month(
        period=kw.pop("period", "2026-07"),
        csv_path=_csv(tmp_path, rows),
        ledger_path=ledger,
        org_id=kw.pop("org_id", ORG),
        dry_run=dry_run,
        client_factory=lambda org: client,
        environ=env if env is not None else {POST_ENV: "1"},
        emit=lines.append,
        **kw,
    )
    return run, "\n".join(lines)


def _ledger_states(tmp_path):
    con = sqlite3.connect(tmp_path / "ledger.sqlite")
    try:
        return dict(
            con.execute(
                "SELECT state, COUNT(*) FROM posted_journals GROUP BY state"
            ).fetchall()
        )
    finally:
        con.close()


THE_BATCH = [
    _row(),
    _row(**{"Reference#": "R2", "Expense Amount": "40.00",
            "Currency Code": "EUR", "Exchange Rate": "1.162275"}),
    _row(**{"Reference#": "SPLIT", "Expense Amount": "10.00"}),
    _row(**{"Reference#": "SPLIT", "Expense Amount": "5.50",
            "Expense Account": "Office Supplies"}),
    _row(**{"Reference#": "OLD", "Expense Date": "2026-03-30"}),
    _row(**{"Reference#": "UNMAPPED", "Expense Account": "Travel & Transport"}),
]


# ── dry run ─────────────────────────────────────────────────────────


def test_dry_run_plans_the_fixture_and_posts_nothing(tmp_path, monkeypatch):
    """Stages 1-4 through the runner: the footer is skipped, splits regroup,
    the EUR row converts, the stale row and the unmapped category refuse,
    and nothing reaches the poster."""
    monkeypatch.setattr(
        rm, "execute_expense_post",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("poster reached on a dry run")),
    )
    client = NeverPosts()
    run, out = _run(tmp_path, THE_BATCH, client=client, dry_run=True)

    assert run.exit_code == 0
    assert run.rows == 6 and run.purchases == 5
    assert run.occupancy.verdict == VERDICT_CLEAR
    assert [p.reference for p in run.send_plan.postable] == ["R1", "R2", "SPLIT"]
    assert {r.reason for r in run.plan.refusals} == {REFUSAL_STALE_DATE, REFUSAL_ACCOUNT}
    assert run.planned_total == Decimal("100.00") + Decimal("46.49") + Decimal("15.50")
    assert "readback: SKIPPED (dry run)" in out
    assert "PLAN ASSERT: 3 expense(s), zero refusals, tie-out 161.99 USD" in out
    assert "create" not in client.calls
    assert _ledger_states(tmp_path) == {}


def test_the_period_is_threaded_into_the_plan(tmp_path):
    """The March row must refuse with the stale-date reason. Unthread
    `period=` from the runner's plan call and this goes red."""
    run, _ = _run(tmp_path, [_row(**{"Expense Date": "2026-03-30"})], client=FakeClient())
    assert run.send_plan.postable == ()
    assert [r.reason for r in run.plan.refusals] == [REFUSAL_STALE_DATE]


def test_conversion_is_threaded_into_the_plan(tmp_path):
    """A EUR row posts as USD at the CSV's own rate with the Original tag.
    Unthread `convert_foreign_to_base=` and this goes red."""
    run, _ = _run(
        tmp_path,
        [_row(**{"Currency Code": "EUR", "Exchange Rate": "1.162275"})],
        client=FakeClient(),
    )
    (p,) = run.send_plan.postable
    assert p.payload["currency_code"] == "USD"
    assert p.payload["amount"] == 116.23
    assert "Original: EUR 100.00 @ 1.162275" in p.payload["description"]


def test_a_blank_reference_is_not_selected_for_the_send_set(tmp_path):
    run, out = _run(tmp_path, [_row(), _row(**{"Reference#": ""})], client=FakeClient())
    assert [p.reference for p in run.send_plan.postable] == ["R1"]
    assert [r.reason for r in run.runner_refusals] == [REFUSAL_BLANK_REFERENCE]
    assert REFUSAL_BLANK_REFERENCE in out


# ── the occupancy resume rule, both directions ──────────────────────


def test_an_occupied_month_that_is_partly_ours_resumes(tmp_path):
    """The ledger holds R1 as posted and Zoho holds a July row on the card:
    report the occupancy, do not abort, and let already_in_ledger skip R1."""
    with PostLedger(tmp_path / "ledger.sqlite") as ledger:
        ledger.mark_posted(ORG, "R1", zoho_journal_id="NEW-EARLIER", entry_number=None,
                           now_iso="2026-09-23T10:00:00+00:00", content_hash="h")
    client = FakeClient(existing=[_existing(ref="R1", expense_id="NEW-EARLIER")])
    rows = [_row(), _row(**{"Reference#": "R2"})]
    run, out = _run(tmp_path, rows, client=client)

    assert run.abort_reason is None
    assert run.occupancy.verdict == VERDICT_ALREADY_OCCUPIED
    assert run.ours_in_ledger == ("R1",)
    assert "resume" in out
    assert [p.reference for p in run.send_plan.postable] == ["R2"]
    assert [(r.reference, r.reason) for r in run.plan.refusals] == [("R1", REFUSAL_LEDGER)]
    assert run.exit_code == 0


def test_an_occupied_month_that_is_not_ours_aborts_before_planning(tmp_path):
    """Zoho holds a July row on the card and the ledger holds none of the
    batch: that is someone else's hand-entered month. Abort, pull no
    chart, post nothing."""
    client = NeverPosts(existing=[_existing()])
    run, out = _run(tmp_path, [_row(), _row(**{"Reference#": "R2"})], client=client, dry_run=False)

    assert run.abort_reason is not None
    assert "someone else's hand-entered month" in run.abort_reason
    assert run.exit_code == 2
    assert run.plan is None and run.send_plan is None
    assert "coa" not in client.calls
    assert "create" not in client.calls
    assert "ABORT" in out


def test_the_resume_rule_only_counts_posted_rows(tmp_path):
    """An inflight or ambiguous row is not evidence the month is ours."""
    with PostLedger(tmp_path / "ledger.sqlite") as ledger:
        ledger.mark_inflight(ORG, "R1", "h", now_iso="2026-09-23T10:00:00+00:00")
    client = FakeClient(existing=[_existing()])
    run, _ = _run(tmp_path, [_row()], client=client)
    assert run.ours_in_ledger == ()
    assert run.abort_reason is not None


def test_an_unverifiable_month_aborts(tmp_path):
    client = NeverPosts(occupancy_raises=ZohoAPIError("boom", status=500))
    run, _ = _run(tmp_path, [_row()], client=client, dry_run=False)
    assert run.occupancy.verdict == VERDICT_UNVERIFIABLE
    assert run.exit_code == 2
    assert "coa" not in client.calls


def test_a_clear_month_with_a_fresh_ledger_continues(tmp_path):
    run, _ = _run(tmp_path, [_row()], client=FakeClient())
    assert run.abort_reason is None
    assert run.occupancy.verdict == VERDICT_CLEAR


# ── synthetic references, scoped by the runner ──────────────────────


def test_the_runner_scopes_a_synthetic_reference(tmp_path):
    """The export falls back to the archive filename when it reads no
    invoice number, and those filenames restart every batch. Unthread
    `period=` from the runner's group_by_reference call and this goes
    red: the bare filename would reach both Zoho and the ledger."""
    run, out = _run(
        tmp_path, [_row(**{"Reference#": "0003__rendered-body.pdf"})],
        client=FakeClient(),
    )
    (p,) = run.send_plan.postable
    assert p.reference == "2026-07_0003__rendered-body.pdf"
    assert p.payload["reference_number"] == "2026-07_0003__rendered-body.pdf"
    assert "1 synthetic reference(s) scoped to 2026-07" in out


def test_the_runner_reads_the_ledger_on_the_scoped_key(tmp_path):
    """Once migrated, the ledger holds the scoped key and the runner must
    match it there. A fallback to the bare key is deliberately absent:
    from another month it would find the wrong month's row, which is the
    collision the scoping removes."""
    with PostLedger(tmp_path / "ledger.sqlite") as ledger:
        ledger.mark_posted(
            ORG, "2026-07_0003__rendered-body.pdf", zoho_journal_id="OLD",
            entry_number=None, now_iso="2026-09-23T09:39:55+00:00",
            content_hash="h",
        )
    client = FakeClient(
        existing=[_existing(ref="0003__rendered-body.pdf", expense_id="OLD")]
    )
    run, _ = _run(
        tmp_path, [_row(**{"Reference#": "0003__rendered-body.pdf"})],
        client=client,
    )
    assert run.ours_in_ledger == ("2026-07_0003__rendered-body.pdf",)
    assert run.abort_reason is None
    assert run.send_plan.postable == ()


# ── unassigned card / entity ────────────────────────────────────────
#
# Both columns are COSMETIC in the payload today: the card comes from the
# org profile and the entity only rides inside the audit note. So these
# tests do not protect a mis-post that exists now; they hold the columns
# load-bearing for the moment per-org routing starts reading them. That
# is also why every one of them drives `run_month`: the guard lives in
# `build_expense_payload`, and a test that called it directly would stay
# green if the runner ever stopped planning through it.


def _unassigned(ref, **over):
    row = {"Reference#": ref, "Paid Through": PAID_THROUGH_PLACEHOLDER}
    row.update(over)
    return _row(**row)


def test_an_unassigned_card_refuses_through_the_runner(tmp_path):
    run, out = _run(tmp_path, [_row(), _unassigned("R2")], client=FakeClient())

    assert [p.reference for p in run.send_plan.postable] == ["R1"]
    assert [(r.reference, r.reason) for r in run.plan.refusals] == [
        ("R2", REFUSAL_UNASSIGNED)
    ]
    (refusal,) = run.plan.refusals
    assert "Paid Through" in refusal.detail
    assert "Legal Entity" not in refusal.detail
    assert REFUSAL_UNASSIGNED in out


def test_an_unassigned_entity_refuses_through_the_runner(tmp_path):
    rows = [_row(), _row(**{"Reference#": "R2", "Legal Entity": ENTITY_PLACEHOLDER})]
    run, _ = _run(tmp_path, rows, client=FakeClient())

    (refusal,) = run.plan.refusals
    assert (refusal.reference, refusal.reason) == ("R2", REFUSAL_UNASSIGNED)
    assert "Legal Entity" in refusal.detail
    assert "Paid Through" not in refusal.detail


def test_one_refusal_names_both_unassigned_columns(tmp_path):
    """A reviewer who fixes the card and re-runs, only to be told about
    the entity, has paid for two round trips on one row."""
    run, _ = _run(
        tmp_path,
        [_unassigned("R2", **{"Legal Entity": ENTITY_PLACEHOLDER})],
        client=FakeClient(),
    )
    (refusal,) = run.plan.refusals
    assert refusal.reason == REFUSAL_UNASSIGNED
    assert "Paid Through and Legal Entity" in refusal.detail


def test_the_refusal_is_not_the_account_one(tmp_path):
    """`account_unresolved` means nobody said which GL account; this means
    nobody said which card or company. The summary must tell them apart,
    or the operator reads one number and fixes the wrong thing."""
    rows = [
        _unassigned("CARD"),
        _row(**{"Reference#": "ACCT", "Expense Account": "(uncategorized - assign)"}),
    ]
    run, out = _run(tmp_path, rows, client=FakeClient())

    assert {(r.reference, r.reason) for r in run.plan.refusals} == {
        ("CARD", REFUSAL_UNASSIGNED),
        ("ACCT", REFUSAL_ACCOUNT),
    }
    assert f"1  {REFUSAL_UNASSIGNED}" in out and f"1  {REFUSAL_ACCOUNT}" in out


def test_a_split_refuses_when_only_its_second_line_is_unassigned(tmp_path):
    """Both columns are per-expense, so a split cannot legitimately
    disagree with itself. If one ever does, the disagreement is the thing
    to stop on: the header row alone would have posted this."""
    rows = [
        _row(**{"Reference#": "SPLIT", "Expense Amount": "10.00"}),
        _unassigned(
            "SPLIT",
            **{"Expense Amount": "5.50", "Expense Account": "Office Supplies"},
        ),
    ]
    run, _ = _run(tmp_path, rows, client=FakeClient())

    assert run.send_plan.postable == ()
    assert [r.reason for r in run.plan.refusals] == [REFUSAL_UNASSIGNED]


# ── a reference whose rows disagree on the date ──────────────────────


HOSTINGER = "H_46243348"


def _hostinger():
    """The real July case: one invoice number reused across two documents
    dated 25 days apart, 172.61 each, which `group_by_reference` merged
    into a single USD 345.22 expense stamped 2026-07-03. The statement
    carries exactly ONE Hostinger charge."""
    return [
        _row(**{"Reference#": HOSTINGER, "Expense Date": "2026-07-03",
                "Expense Amount": "172.61"}),
        _row(**{"Reference#": HOSTINGER, "Expense Date": "2026-07-28",
                "Expense Amount": "172.61"}),
    ]


def test_a_reference_whose_rows_are_25_days_apart_refuses(tmp_path):
    run, out = _run(tmp_path, [_row(), *_hostinger()], client=FakeClient())

    assert [(r.reference, r.reason) for r in run.plan.refusals] == [
        (HOSTINGER, REFUSAL_CONFLICTING_DATES)
    ]
    assert [p.reference for p in run.send_plan.postable] == ["R1"]
    assert REFUSAL_CONFLICTING_DATES in out


def test_the_refusal_names_both_dates(tmp_path):
    """Named in the detail so the reviewer sees the spread without
    opening the CSV to find out what disagreed."""
    run, _ = _run(tmp_path, _hostinger(), client=FakeClient())

    (refusal,) = run.plan.refusals
    assert "2026-07-03" in refusal.detail
    assert "2026-07-28" in refusal.detail
    assert "25 days apart" in refusal.detail


def test_a_genuine_split_on_one_date_still_posts_as_one_expense(tmp_path):
    """THE REGRESSION THIS GUARD MUST NOT CAUSE. A real split is one
    receipt across several accounts, so its rows share a date exactly and
    must still group into a single itemized expense."""
    rows = [
        _row(**{"Reference#": "SPLIT", "Expense Amount": "10.00"}),
        _row(**{"Reference#": "SPLIT", "Expense Amount": "5.50",
                "Expense Account": "Office Supplies"}),
    ]
    run, _ = _run(tmp_path, rows, client=FakeClient())

    assert run.plan.refusals == ()
    (planned,) = run.send_plan.postable
    assert planned.reference == "SPLIT"
    assert [li["account_id"] for li in planned.payload["line_items"]] == [
        SOFTWARE, OFFICE
    ]
    assert planned.total == Decimal("15.50")


@pytest.mark.parametrize(
    ("second_date", "posts"), [("2026-07-16", True), ("2026-07-17", False)]
)
def test_the_boundary_is_two_days(tmp_path, second_date, posts):
    """Base row is 2026-07-14, so these are a 2-day and a 3-day spread."""
    rows = [
        _row(**{"Reference#": "SPLIT", "Expense Amount": "10.00"}),
        _row(**{"Reference#": "SPLIT", "Expense Date": second_date,
                "Expense Amount": "5.50",
                "Expense Account": "Office Supplies"}),
    ]
    run, _ = _run(tmp_path, rows, client=FakeClient())

    if posts:
        assert run.plan.refusals == ()
        assert [p.reference for p in run.send_plan.postable] == ["SPLIT"]
    else:
        assert run.send_plan.postable == ()
        assert [r.reason for r in run.plan.refusals] == [REFUSAL_CONFLICTING_DATES]


def test_a_group_with_one_unreadable_date_keeps_the_stale_date_reason(tmp_path):
    """July's `00000031010` has an empty date cell. A spread computed over
    one readable date is no spread, so this falls through to the branch
    that already names the problem exactly."""
    rows = [
        _row(**{"Reference#": "00000031010", "Expense Date": ""}),
        _row(**{"Reference#": "00000031010", "Expense Date": "2026-07-28",
                "Expense Account": "Office Supplies"}),
    ]
    run, _ = _run(tmp_path, rows, client=FakeClient())

    (refusal,) = run.plan.refusals
    assert refusal.reason == REFUSAL_STALE_DATE
    assert "not a readable ISO date" in refusal.detail


# ── refusal precedence, both halves decided deliberately ────────────


def test_conflicting_dates_outrank_a_stale_date(tmp_path):
    """INTRA-BUILD ORDER. The stale check reads row[0]'s date only, so
    which date it judges is an accident of CSV order while the rows
    disagree. Move the spread guard below it and this goes red."""
    rows = [
        _row(**{"Reference#": "OLD", "Expense Date": "2026-03-30"}),
        _row(**{"Reference#": "OLD", "Expense Date": "2026-03-05",
                "Expense Account": "Office Supplies"}),
    ]
    run, _ = _run(tmp_path, rows, client=FakeClient())

    assert [r.reason for r in run.plan.refusals] == [REFUSAL_CONFLICTING_DATES]


def test_an_already_posted_conflicting_group_refuses_as_ledger(tmp_path):
    """LEDGER-FIRST ORDER SURVIVES. What the cells say now cannot change
    what went to Zoho, so a recorded purchase answers `already_in_ledger`
    even when its rows disagree. This is what keeps both rehearsed
    months' refusal mix byte-identical."""
    with PostLedger(tmp_path / "ledger.sqlite") as ledger:
        ledger.mark_posted(ORG, HOSTINGER, zoho_journal_id="OLD", entry_number=None,
                           now_iso="2026-09-23T10:00:00+00:00", content_hash="h")
    run, _ = _run(tmp_path, [_row(), *_hostinger()], client=FakeClient())

    assert [(r.reference, r.reason) for r in run.plan.refusals] == [
        (HOSTINGER, REFUSAL_LEDGER)
    ]
    assert [p.reference for p in run.send_plan.postable] == ["R1"]


def test_an_already_posted_row_refuses_as_ledger_not_unassigned(tmp_path):
    """THE ORDER DECISION. A purchase this tool already posted is history:
    what its cells say now cannot change what went to Zoho, so the ledger
    answers first. Move `ledger.status_for` back below the payload build
    in `plan_expense_post` and this goes red, taking both rehearsed
    months' known refusal mix with it."""
    with PostLedger(tmp_path / "ledger.sqlite") as ledger:
        ledger.mark_posted(ORG, "R2", zoho_journal_id="OLD", entry_number=None,
                           now_iso="2026-09-23T10:00:00+00:00", content_hash="h")
    run, _ = _run(tmp_path, [_row(), _unassigned("R2")], client=FakeClient())

    assert [(r.reference, r.reason) for r in run.plan.refusals] == [
        ("R2", REFUSAL_LEDGER)
    ]
    assert [p.reference for p in run.send_plan.postable] == ["R1"]


def test_a_stale_date_outranks_an_unassigned_card(tmp_path):
    """Within the build the date guard stays first. "Dated four months
    before the period" is the more alarming fact about a row carrying
    both; the unassigned card is the second defect, met once the first is
    settled."""
    run, _ = _run(
        tmp_path, [_unassigned("OLD", **{"Expense Date": "2026-03-30"})],
        client=FakeClient(),
    )
    assert [r.reason for r in run.plan.refusals] == [REFUSAL_STALE_DATE]


def test_a_live_run_posts_the_neighbours_and_leaves_the_unassigned_row(tmp_path):
    client = FakeClient()
    run, out = _run(
        tmp_path, [_row(), _unassigned("R2"), _row(**{"Reference#": "R3"})],
        client=client, dry_run=False,
    )

    assert run.exit_code == 0, out
    assert [ref for ref, _ in run.report.posted] == ["R1", "R3"]
    assert [r["reference_number"] for r in client.created] == ["R1", "R3"]
    assert all(r.clean for r in run.readback)
    assert _ledger_states(tmp_path) == {"posted": 2}


# ── org refusal ─────────────────────────────────────────────────────


@pytest.mark.parametrize("org", sorted(PRODUCTION_ORG_IDS))
def test_a_production_org_is_refused_by_name_before_any_client(tmp_path, org):
    with pytest.raises(OrgRefused, match="production"):
        run_month(period="2026-07", csv_path=_csv(tmp_path, [_row()]),
                  ledger_path=tmp_path / "l.sqlite", org_id=org,
                  client_factory=_boom, emit=lambda _: None)


@pytest.mark.parametrize("org", ["", None, "123", "8221162900", " 822116290x"])
def test_anything_but_the_sandbox_is_refused(tmp_path, org):
    with pytest.raises(OrgRefused):
        run_month(period="2026-07", csv_path=_csv(tmp_path, [_row()]),
                  ledger_path=tmp_path / "l.sqlite", org_id=org,
                  client_factory=_boom, emit=lambda _: None)


def test_a_card_override_needs_both_id_and_name(tmp_path):
    with pytest.raises(RunRefused, match="card-name"):
        run_month(period="2026-07", csv_path=_csv(tmp_path, [_row()]),
                  ledger_path=tmp_path / "l.sqlite", card_account_id="999",
                  client_factory=_boom, emit=lambda _: None)


def test_a_malformed_period_is_refused_before_any_client(tmp_path):
    with pytest.raises(ValueError):
        run_month(period="2026-7", csv_path=_csv(tmp_path, [_row()]),
                  ledger_path=tmp_path / "l.sqlite",
                  client_factory=_boom, emit=lambda _: None)


# ── dry-run cannot post, live path cannot skip the gate ─────────────


def test_a_dry_run_never_constructs_a_poster_path(tmp_path, monkeypatch):
    """Belt and braces with the first test: even with the env gate open,
    dry_run=True must not reach execute_expense_post."""
    monkeypatch.setattr(
        rm, "execute_expense_post",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("reached")),
    )
    run, _ = _run(tmp_path, [_row()], client=NeverPosts(), dry_run=True, env={POST_ENV: "1"})
    assert run.exit_code == 0 and run.report is None


def test_a_live_run_without_the_env_gate_is_refused_before_reading(tmp_path):
    with pytest.raises(RunRefused, match=POST_ENV):
        run_month(period="2026-07", csv_path=tmp_path / "missing.csv",
                  ledger_path=tmp_path / "l.sqlite", dry_run=False,
                  client_factory=_boom, environ={}, emit=lambda _: None)


# ── live path ───────────────────────────────────────────────────────


def test_a_live_run_posts_reads_back_and_ties_out(tmp_path):
    client = FakeClient()
    run, out = _run(tmp_path, THE_BATCH, client=client, dry_run=False)

    assert run.exit_code == 0, out
    assert [ref for ref, _ in run.report.posted] == ["R1", "R2", "SPLIT"]
    assert run.report.rejected == () and run.report.ambiguous == ()
    assert all(r.clean for r in run.readback), [r.problems for r in run.readback]
    assert run.stored_total == run.planned_total == Decimal("161.99")
    assert "MATCH" in out and "MISMATCH" not in out
    assert _ledger_states(tmp_path) == {"posted": 3}
    # Every posted id was read back individually, none existed before.
    assert client.calls.count("get") == 3
    # The split reached Zoho itemized and came back with both lines.
    split = next(r for r in client.created if r["reference_number"] == "SPLIT")
    assert {li["account_id"] for li in split["line_items"]} == {SOFTWARE, OFFICE}


def test_a_second_live_run_posts_nothing_and_exits_clean(tmp_path):
    """The ledger plus occupancy make a re-run a no-op: every reference
    refuses as already_in_ledger and the poster is never reached."""
    client = FakeClient()
    _run(tmp_path, THE_BATCH, client=client, dry_run=False)
    again = NeverPosts(existing=client.created)
    run, out = _run(tmp_path, THE_BATCH, client=again, dry_run=False)
    assert run.exit_code == 0
    assert run.occupancy.verdict == VERDICT_ALREADY_OCCUPIED
    assert run.ours_in_ledger == ("R1", "R2", "SPLIT")
    assert run.send_plan.postable == ()
    assert "nothing to post" in out


@pytest.mark.parametrize(
    "field,value,expect",
    [
        ("line_items", [{"account_id": OFFICE, "amount": 100.0}], "lines"),
        ("total", 99.99, "total"),
        ("date", "2026-07-15", "date"),
        ("reference_number", "R9", "reference"),
        ("paid_through_account_id", "1", "paid_through"),
        ("currency_code", "EUR", "currency"),
        ("description", "no envelope here", "audit envelope"),
    ],
)
def test_the_readback_catches_a_corrupted_record(tmp_path, field, value, expect):
    """A readback that cannot fail is not evidence. Each checked field is
    corrupted on the stored record in turn; the run must exit 1 and name it."""

    def corrupt(rec):
        if rec["reference_number"] == "R1":
            rec[field] = value
        return rec

    client = FakeClient(corrupt=corrupt)
    run, out = _run(tmp_path, [_row()], client=client, dry_run=False)
    assert run.exit_code == 1
    (result,) = run.readback
    assert not result.clean
    assert any(expect in p for p in result.problems), result.problems
    assert "MISMATCH" in out


def test_the_readback_wants_the_original_tag_on_a_converted_row(tmp_path):
    def corrupt(rec):
        rec["description"] = rec["description"].replace("Original: ", "Orig ")
        return rec

    client = FakeClient(corrupt=corrupt)
    run, _ = _run(
        tmp_path,
        [_row(**{"Currency Code": "EUR", "Exchange Rate": "1.162275"})],
        client=client, dry_run=False,
    )
    assert run.exit_code == 1
    assert any("Original:" in p for p in run.readback[0].problems)


def test_a_pre_existing_id_is_not_a_new_record(tmp_path):
    """If Zoho answered with an id that was already there, nothing was
    created, whatever the accept code said."""
    client = FakeClient(existing=[_existing(date="2026-01-05", expense_id="NEW1")])

    run, _ = _run(tmp_path, [_row()], client=client, dry_run=False)
    assert run.exit_code == 1
    assert any("BEFORE this run" in p for p in run.readback[0].problems)


def test_a_clean_rejection_is_released_and_exits_nonzero(tmp_path):
    client = FakeClient(fail={"R2": ZohoAPIError("plan says no", status=400)})
    run, out = _run(tmp_path, [_row(), _row(**{"Reference#": "R2"})], client=client, dry_run=False)
    assert run.exit_code == 1
    assert [ref for ref, _ in run.report.posted] == ["R1"]
    assert [ref for ref, _ in run.report.rejected] == ["R2"]
    assert _ledger_states(tmp_path) == {"posted": 1}  # R2's intent released
    assert "REJECTED" in out and "MISMATCH" in out


def test_an_ambiguous_result_aborts_the_batch_and_exits_nonzero(tmp_path):
    client = FakeClient(fail={"R1": ZohoAPIError("timeout", status=None)})
    run, _ = _run(tmp_path, [_row(), _row(**{"Reference#": "R2"})], client=client, dry_run=False)
    assert run.exit_code == 1
    assert run.report.aborted
    assert [ref for ref, _ in run.report.ambiguous] == ["R1"]
    assert _ledger_states(tmp_path) == {"ambiguous": 1}
    assert client.calls.count("create") == 1  # R2 never attempted


# ── compare_expense on its own, for the flat-vs-itemized shapes ─────


def test_compare_accepts_zohos_flat_shape_without_line_items():
    payload = {
        "date": "2026-07-14", "reference_number": "R1", "currency_code": "USD",
        "paid_through_account_id": CARD, "account_id": SOFTWARE, "amount": 100.0,
        "description": "[External Match Audit] Ref: R1 | Source: x",
    }
    stored = {
        "date": "2026-07-14", "reference_number": "R1", "currency_code": "USD",
        "paid_through_account_id": CARD, "account_id": SOFTWARE, "amount": 100.0,
        "total": 100.0, "line_items": [],
        "description": "[External Match Audit] Ref: R1 | Source: x",
    }
    assert compare_expense(stored, payload, card_account_id=CARD,
                           base_currency="USD", converted=False) == []


def test_compare_catches_a_dropped_split_line():
    payload = {
        "date": "2026-07-14", "reference_number": "S", "currency_code": "USD",
        "paid_through_account_id": CARD,
        "line_items": [{"account_id": SOFTWARE, "amount": 10.0},
                       {"account_id": OFFICE, "amount": 5.5}],
        "description": "[External Match Audit] Ref: S | Source: x | Split: 2 accounts",
    }
    stored = {
        "date": "2026-07-14", "reference_number": "S", "currency_code": "USD",
        "paid_through_account_id": CARD, "total": 15.5,
        "line_items": [{"account_id": SOFTWARE, "amount": 15.5}],
        "description": payload["description"],
    }
    problems = compare_expense(stored, payload, card_account_id=CARD,
                               base_currency="USD", converted=False)
    assert len(problems) == 1 and problems[0].startswith("lines")


# ── the CLI ─────────────────────────────────────────────────────────


def test_cli_dry_run_exits_zero_and_prints_the_summary(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(rm, "_make_client", lambda org: NeverPosts())
    monkeypatch.delenv(POST_ENV, raising=False)
    code = main([
        "--month", "2026-07", "--csv", str(_csv(tmp_path, THE_BATCH)),
        "--ledger", str(tmp_path / "ledger.sqlite"), "--dry-run",
    ])
    out = capsys.readouterr().out
    assert code == 0
    assert "readback: SKIPPED (dry run)" in out
    assert "postable               3" in out
    assert "date_precedes_period_window" in out


def test_cli_refuses_a_production_org_without_a_client(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(rm, "_make_client", _boom)
    code = main([
        "--month", "2026-07", "--csv", str(_csv(tmp_path, [_row()])),
        "--ledger", str(tmp_path / "ledger.sqlite"), "--org", "822741658", "--dry-run",
    ])
    assert code == 2
    assert "production" in capsys.readouterr().err


def test_cli_live_run_refuses_without_the_env_gate(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(rm, "_make_client", _boom)
    monkeypatch.delenv(POST_ENV, raising=False)
    code = main([
        "--month", "2026-07", "--csv", str(_csv(tmp_path, [_row()])),
        "--ledger", str(tmp_path / "ledger.sqlite"),
    ])
    assert code == 2
    assert POST_ENV in capsys.readouterr().err


def test_cli_live_run_posts_when_every_gate_is_open(tmp_path, monkeypatch, capsys):
    client = FakeClient()
    monkeypatch.setattr(rm, "_make_client", lambda org: client)
    monkeypatch.setenv(POST_ENV, "1")
    code = main([
        "--month", "2026-07", "--csv", str(_csv(tmp_path, [_row()])),
        "--ledger", str(tmp_path / "ledger.sqlite"),
    ])
    out = capsys.readouterr().out
    assert code == 0, out
    assert client.calls.count("create") == 1
    assert "verified clean         1 / 1" in out
    assert "MATCH" in out


def test_cli_env_file_loads_credentials_without_overriding(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text('ZOHO_CLIENT_ID="from-file"\nALREADY=file\n# comment\n', encoding="utf-8")
    monkeypatch.delenv("ZOHO_CLIENT_ID", raising=False)
    monkeypatch.setenv("ALREADY", "process")
    rm._load_env_file(env)
    import os
    assert os.environ["ZOHO_CLIENT_ID"] == "from-file"
    assert os.environ["ALREADY"] == "process"
    monkeypatch.delenv("ZOHO_CLIENT_ID", raising=False)


def test_cli_missing_env_file_is_an_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(rm, "_make_client", _boom)
    code = main([
        "--month", "2026-07", "--csv", str(_csv(tmp_path, [_row()])),
        "--ledger", str(tmp_path / "ledger.sqlite"), "--dry-run",
        "--env-file", str(tmp_path / "nope.env"),
    ])
    assert code == 2
    assert "env file not found" in capsys.readouterr().err


def test_the_web_layer_guard_would_catch_an_import_of_the_runner():
    """The runner lives under `zoho/`, so the standing import guard in
    test_zoho_posting_is_gated.py covers it. Pinned so a move out of the
    package cannot silently leave the hosted layer able to import it."""
    from tests.test_zoho_posting_is_gated import _ZOHO_IMPORT

    assert _ZOHO_IMPORT.search("from ..zoho.reconcile_month import run_month")
    assert _ZOHO_IMPORT.search("import expense_recon.zoho.reconcile_month")
