"""4.8 idempotency ledger + guarded poster tests — all offline (BLUEPRINT 4.8/4b).

The contract under test: the same journal entry can never reach Zoho
twice, across re-runs, crashes mid-batch, network ambiguity, and
content drift. Synthetic chart only (the real Brisken chart never
lands in the repo)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from expense_recon.ingest.chart_of_accounts import ChartOfAccounts
from expense_recon.zoho.client import ZohoAPIError
from expense_recon.zoho.idempotent import (
    PostLedger,
    PostedConflictError,
    build_journal_payload,
    entries_from_rows,
    entry_content_hash,
    execute_post,
    plan_post,
    verify_ambiguous,
)

ORG = "822741658"

_COA_RECORDS = [
    {"account_id": "111", "account_name": "Travel: Flights", "account_code": "6000",
     "account_type": "expense", "parent_account_name": None, "is_active": True},
    {"account_id": "222", "account_name": "Amex Card", "account_code": "A200",
     "account_type": "credit_card", "parent_account_name": None, "is_active": True},
    {"account_id": None, "account_name": "Idless Acct", "account_code": "9999",
     "account_type": "expense", "parent_account_name": None, "is_active": True},
]


def _chart() -> ChartOfAccounts:
    return ChartOfAccounts.from_api(_COA_RECORDS)


def _row(date="2026-04-03", account="Travel: Flights", desc="flight", ref="t1",
         notes="llm conf=0.91", debit="", credit="", url="", report=""):
    return [date, account, desc, ref, notes, debit, credit, url, report]


def _entry_rows(ref="t1", amount="180.00", debit_acct="Travel: Flights",
                credit_acct="Amex Card", date="2026-04-03"):
    return [
        _row(date=date, account=debit_acct, ref=ref, debit=amount),
        _row(date=date, account=credit_acct, desc="Payment to X", ref=ref,
             credit=amount),
    ]


class FakeClient:
    """Scripted stand-in for ZohoClient: each posts entry pops the next
    scripted result (a dict = created journal, an Exception = raised)."""

    def __init__(self, results=(), journals=()):
        self._results = list(results)
        self._journals = list(journals)
        self.posted_payloads: list[dict] = []

    def create_journal(self, payload):
        self.posted_payloads.append(payload)
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def list_journals(self, **kwargs):
        return list(self._journals)


# ── entry construction ───────────────────────────────────────────────

def test_entries_group_by_reference_and_resolve_ids():
    rows = _entry_rows("t1") + _entry_rows("t2", amount="45.10")
    entries = entries_from_rows(rows, _chart())
    assert [e.reference for e in entries] == ["t1", "t2"]
    e = entries[0]
    assert e.postable and e.journal_date == "2026-04-03"
    debit = next(ln for ln in e.lines if ln.debit_or_credit == "debit")
    credit = next(ln for ln in e.lines if ln.debit_or_credit == "credit")
    assert debit.account_id == "111" and credit.account_id == "222"
    assert debit.amount == Decimal("180.00")


def test_placeholder_account_blocks_entry():
    rows = _entry_rows("t1", debit_acct="(uncategorized - assign)")
    (entry,) = entries_from_rows(rows, _chart())
    assert not entry.postable
    assert any("placeholder" in b for b in entry.blockers)


def test_card_placeholder_blocks_entry():
    rows = _entry_rows("t1", credit_acct="Card: amex-usd")
    (entry,) = entries_from_rows(rows, _chart())
    assert any("placeholder" in b for b in entry.blockers)


def test_unknown_account_blocks_entry():
    rows = _entry_rows("t1", debit_acct="No Such Account")
    (entry,) = entries_from_rows(rows, _chart())
    assert any("not found in the entity chart" in b for b in entry.blockers)


def test_idless_account_blocks_entry():
    rows = _entry_rows("t1", debit_acct="Idless Acct")
    (entry,) = entries_from_rows(rows, _chart())
    assert any("no Zoho account_id" in b for b in entry.blockers)


def test_unbalanced_entry_blocks():
    rows = [
        _row(debit="180.00"),
        _row(account="Amex Card", credit="90.00"),
    ]
    (entry,) = entries_from_rows(rows, _chart())
    assert any("unbalanced" in b for b in entry.blockers)


def test_two_credit_rows_block():
    rows = _entry_rows("t1") + [
        _row(account="Amex Card", ref="t1", credit="180.00"),
        _row(ref="t1", debit="180.00"),
    ]
    (entry,) = entries_from_rows(rows, _chart())
    assert any("credit rows" in b for b in entry.blockers)


def test_date_drift_within_entry_blocks():
    rows = _entry_rows("t1")
    rows[1][0] = "2026-04-04"
    (entry,) = entries_from_rows(rows, _chart())
    assert any("disagree on Date" in b for b in entry.blockers)


def test_blank_reference_blocks():
    # Blank refs cannot be grouped (nothing says the rows belong
    # together), so each row becomes its own unpostable entry.
    rows = _entry_rows("")
    entries = entries_from_rows(rows, _chart())
    assert len(entries) == 2
    for entry in entries:
        assert not entry.postable
        assert any("blank Reference#" in b for b in entry.blockers)


def test_hash_ignores_notes_and_provenance_but_not_amounts():
    base = entries_from_rows(_entry_rows("t1"), _chart())[0]
    noisy_rows = _entry_rows("t1")
    noisy_rows[0][4] = "llm conf=0.12"  # Notes changed
    noisy_rows[0][7] = "https://elsewhere/r1.pdf"  # Receipt URL changed
    noisy = entries_from_rows(noisy_rows, _chart())[0]
    assert entry_content_hash(base) == entry_content_hash(noisy)

    edited = entries_from_rows(_entry_rows("t1", amount="181.00"), _chart())[0]
    assert entry_content_hash(base) != entry_content_hash(edited)


def test_payload_shape_and_draft_default():
    (entry,) = entries_from_rows(_entry_rows("t1"), _chart())
    payload = build_journal_payload(entry)
    assert payload["status"] == "draft"
    assert payload["reference_number"] == "t1"
    assert payload["journal_date"] == "2026-04-03"
    assert payload["line_items"] == [
        {"account_id": "111", "amount": 180.0, "debit_or_credit": "debit",
         "description": "flight"},
        {"account_id": "222", "amount": 180.0, "debit_or_credit": "credit",
         "description": "Payment to X"},
    ]


# ── ledger ───────────────────────────────────────────────────────────

def test_ledger_roundtrip_and_persistence(tmp_path):
    db = tmp_path / "ledger.sqlite"
    with PostLedger(db) as ledger:
        ledger.mark_inflight(ORG, "t1", "hash1", now_iso="2026-07-28T10:00:00+00:00")
        ledger.mark_posted(ORG, "t1", zoho_journal_id="J1", entry_number="JE-1",
                           now_iso="2026-07-28T10:00:01+00:00", content_hash="hash1")
    with PostLedger(db) as ledger:  # reopen proves persistence
        row = ledger.status_for(ORG, "t1")
        assert row.state == "posted" and row.zoho_journal_id == "J1"
        assert row.content_hash == "hash1"


def test_mark_posted_restores_concurrently_deleted_row(tmp_path):
    # The invariant "no journal in Zoho without a ledger record" must
    # survive a concurrent --forget/--verify clear between the intent
    # and the confirmation: mark_posted is an UPSERT, never a silent
    # 0-row UPDATE.
    with PostLedger(tmp_path / "l.sqlite") as ledger:
        ledger.mark_inflight(ORG, "t1", "h1", now_iso="2026-07-28T10:00:00+00:00")
        ledger.remove(ORG, "t1")  # the concurrent delete
        ledger.mark_posted(ORG, "t1", zoho_journal_id="J1", entry_number=None,
                           now_iso="2026-07-28T10:00:30+00:00", content_hash="h1")
        row = ledger.status_for(ORG, "t1")
        assert row is not None and row.state == "posted"
        assert row.zoho_journal_id == "J1"


def test_mark_ambiguous_restores_concurrently_deleted_row(tmp_path):
    with PostLedger(tmp_path / "l.sqlite") as ledger:
        ledger.mark_inflight(ORG, "t1", "h1", now_iso="2026-07-28T10:00:00+00:00")
        ledger.remove(ORG, "t1")
        ledger.mark_ambiguous(ORG, "t1", now_iso="2026-07-28T10:00:30+00:00",
                              content_hash="h1", note="timeout")
        row = ledger.status_for(ORG, "t1")
        assert row is not None and row.state == "ambiguous"


def test_ledger_rows_are_org_scoped(tmp_path):
    other_org = "697686691"
    with PostLedger(tmp_path / "l.sqlite") as ledger:
        ledger.mark_inflight(ORG, "t1", "hA", now_iso="2026-07-28T10:00:00+00:00")
        ledger.mark_posted(ORG, "t1", zoho_journal_id="J1", entry_number=None,
                           now_iso="2026-07-28T10:00:01+00:00", content_hash="hA")
        ledger.mark_inflight(other_org, "t1", "hB",
                             now_iso="2026-07-28T10:00:02+00:00")
        # Same reference, two orgs: independent rows...
        assert ledger.status_for(ORG, "t1").state == "posted"
        assert ledger.status_for(other_org, "t1").state == "inflight"
        # ...remove is org-scoped...
        ledger.remove(other_org, "t1")
        assert ledger.status_for(ORG, "t1") is not None
        assert ledger.status_for(other_org, "t1") is None
        # ...and the cross-org lookup sees the sibling.
        assert [r.org_id for r in ledger.other_org_rows("t1", exclude_org=other_org)] \
            == [ORG]


def test_mark_inflight_conflicts_on_existing_row(tmp_path):
    with PostLedger(tmp_path / "l.sqlite") as ledger:
        ledger.mark_inflight(ORG, "t1", "h", now_iso="2026-07-28T10:00:00+00:00")
        with pytest.raises(PostedConflictError):
            ledger.mark_inflight(ORG, "t1", "h", now_iso="2026-07-28T10:00:05+00:00")


# ── plan ─────────────────────────────────────────────────────────────

def test_plan_partitions_all_states(tmp_path):
    chart = _chart()
    entries = entries_from_rows(
        _entry_rows("new1") + _entry_rows("same1") + _entry_rows("changed1")
        + _entry_rows("stuck1")
        + _entry_rows("flagged1", debit_acct="(uncategorized - assign)"),
        chart,
    )
    by_ref = {e.reference: e for e in entries}
    with PostLedger(tmp_path / "l.sqlite") as ledger:
        now = "2026-07-28T10:00:00+00:00"
        same_hash = entry_content_hash(by_ref["same1"])
        ledger.mark_inflight(ORG, "same1", same_hash, now_iso=now)
        ledger.mark_posted(ORG, "same1", zoho_journal_id="J1", entry_number=None,
                           now_iso=now, content_hash=same_hash)
        ledger.mark_inflight(ORG, "changed1", "different-hash", now_iso=now)
        ledger.mark_posted(ORG, "changed1", zoho_journal_id="J2", entry_number=None,
                           now_iso=now, content_hash="different-hash")
        ledger.mark_inflight(ORG, "stuck1", "h", now_iso=now)  # stays inflight

        plan = plan_post(entries, ledger, ORG)
    assert [e.reference for e in plan.to_post] == ["new1"]
    assert [e.reference for e in plan.skip_posted] == ["same1"]
    assert [e.reference for e, _ in plan.conflicts] == ["changed1"]
    assert [e.reference for e, _ in plan.blocked] == ["stuck1"]
    assert [e.reference for e in plan.unpostable] == ["flagged1"]
    kinds = [kind for kind, _ in plan.batch_refusals]
    assert kinds == ["conflict", "unresolved", "unpostable"]


def test_plan_flags_cross_org_duplicate(tmp_path):
    other_org = "697686691"
    entries = entries_from_rows(_entry_rows("t1"), _chart())
    with PostLedger(tmp_path / "l.sqlite") as ledger:
        ledger.mark_inflight(other_org, "t1", "h",
                             now_iso="2026-07-28T10:00:00+00:00")
        ledger.mark_posted(other_org, "t1", zoho_journal_id="J1", entry_number=None,
                           now_iso="2026-07-28T10:00:01+00:00", content_hash="h")

        plan = plan_post(entries, ledger, ORG)
        assert not plan.to_post
        assert [e.reference for e, _ in plan.cross_org] == ["t1"]
        assert [kind for kind, _ in plan.batch_refusals] == ["cross-org"]

        # The explicit waiver (operator confirmed distinct transactions).
        waived = plan_post(entries, ledger, ORG, allow_cross_org=True)
        assert [e.reference for e in waived.to_post] == ["t1"]
        assert not waived.batch_refusals


def test_plan_without_ledger_file_treats_all_as_new():
    entries = entries_from_rows(_entry_rows("t1"), _chart())
    plan = plan_post(entries, None, ORG)
    assert [e.reference for e in plan.to_post] == ["t1"]
    assert not plan.batch_refusals


# ── execute ──────────────────────────────────────────────────────────

def _now() -> str:
    return "2026-07-28T12:00:00+00:00"


def test_execute_posts_records_and_second_run_skips(tmp_path):
    entries = entries_from_rows(_entry_rows("t1") + _entry_rows("t2", amount="9.99"),
                                _chart())
    client = FakeClient(results=[
        {"journal_id": "J1", "entry_number": "JE-1"},
        {"journal_id": "J2", "entry_number": "JE-2"},
    ])
    with PostLedger(tmp_path / "l.sqlite") as ledger:
        plan = plan_post(entries, ledger, ORG)
        report = execute_post(client, plan.to_post, ledger, ORG, now_iso=_now())
        assert report.posted == (("t1", "J1"), ("t2", "J2"))
        assert client.posted_payloads[0]["status"] == "draft"

        # The core idempotency property: an identical re-run posts NOTHING.
        rerun = plan_post(entries, ledger, ORG)
    assert not rerun.to_post
    assert [e.reference for e in rerun.skip_posted] == ["t1", "t2"]


def test_execute_clean_4xx_rolls_back_and_continues(tmp_path):
    entries = entries_from_rows(_entry_rows("bad") + _entry_rows("good"), _chart())
    client = FakeClient(results=[
        ZohoAPIError("invalid account", status=400, code=15),
        {"journal_id": "J1", "entry_number": None},
    ])
    with PostLedger(tmp_path / "l.sqlite") as ledger:
        report = execute_post(client, tuple(entries), ledger, ORG, now_iso=_now())
        assert report.rejected[0][0] == "bad"
        assert report.posted == (("good", "J1"),)
        assert ledger.status_for(ORG, "bad") is None  # intent rolled back
        assert ledger.status_for(ORG, "good").state == "posted"


@pytest.mark.parametrize("failure", [
    ZohoAPIError("gateway timeout", status=502),
    ZohoAPIError("network error calling https://x", status=None),
    ConnectionResetError("peer reset"),
])
def test_execute_ambiguous_failure_aborts_batch(tmp_path, failure):
    entries = entries_from_rows(
        _entry_rows("ok1") + _entry_rows("boom") + _entry_rows("later"), _chart()
    )
    client = FakeClient(results=[{"journal_id": "J1", "entry_number": None}, failure])
    with PostLedger(tmp_path / "l.sqlite") as ledger:
        report = execute_post(client, tuple(entries), ledger, ORG, now_iso=_now())
        assert report.posted == (("ok1", "J1"),)
        assert report.ambiguous[0][0] == "boom"
        assert report.not_attempted == ("later",)
        assert ledger.status_for(ORG, "boom").state == "ambiguous"
        assert ledger.status_for(ORG, "later") is None
        # And the ambiguous row now blocks any re-plan until verified.
        replan = plan_post(entries, ledger, ORG)
        assert [e.reference for e, _ in replan.blocked] == ["boom"]
        assert replan.batch_refusals


def test_execute_row_appearing_mid_batch_denies_rest(tmp_path):
    entries = entries_from_rows(_entry_rows("t1") + _entry_rows("t2"), _chart())
    client = FakeClient(results=[{"journal_id": "J1", "entry_number": None}])
    with PostLedger(tmp_path / "l.sqlite") as ledger:
        # Simulate a concurrent poster: t2 gains a row after the plan.
        ledger.mark_inflight(ORG, "t2", "h", now_iso=_now())
        report = execute_post(client, tuple(entries), ledger, ORG, now_iso=_now())
        assert report.posted == (("t1", "J1"),)
        assert report.ambiguous[0][0] == "t2"  # filed as unresolved, batch aborted


# ── verify ───────────────────────────────────────────────────────────

def test_verify_confirms_found_but_keeps_absent_by_default(tmp_path):
    # Absence from one point-in-time listing is NOT proof of
    # non-commit (a timed-out POST can land after the listing; drafts
    # may not even appear in it). Default = confirm-only.
    with PostLedger(tmp_path / "l.sqlite") as ledger:
        ledger.mark_inflight(ORG, "was-posted", "h1", now_iso=_now())
        ledger.mark_ambiguous(ORG, "was-posted", now_iso=_now(),
                              content_hash="h1", note="timeout")
        ledger.mark_inflight(ORG, "never-landed", "h2", now_iso=_now())

        client = FakeClient(journals=[
            {"reference_number": "was-posted", "journal_id": "J77",
             "entry_number": "JE-77", "journal_date": "2026-04-03"},
        ])
        report = verify_ambiguous(client, ledger, ORG, now_iso=_now())
        assert report.confirmed == (("was-posted", "J77"),)
        assert report.cleared == ()
        assert report.kept and report.kept[0][0] == "never-landed"
        assert ledger.status_for(ORG, "was-posted").state == "posted"
        assert ledger.status_for(ORG, "was-posted").content_hash == "h1"
        assert ledger.status_for(ORG, "never-landed").state == "inflight"


def test_verify_clears_absent_only_past_the_grace_cutoff(tmp_path):
    with PostLedger(tmp_path / "l.sqlite") as ledger:
        ledger.mark_inflight(ORG, "old-row", "h1",
                             now_iso="2026-07-27T09:00:00+00:00")
        ledger.mark_inflight(ORG, "young-row", "h2",
                             now_iso="2026-07-28T11:59:00+00:00")
        client = FakeClient(journals=[])
        report = verify_ambiguous(
            client, ledger, ORG, now_iso=_now(),
            clear_absent_before="2026-07-28T11:00:00+00:00",
        )
        assert report.cleared == ("old-row",)
        assert [ref for ref, _ in report.kept] == ["young-row"]
        assert ledger.status_for(ORG, "old-row") is None
        assert ledger.status_for(ORG, "young-row").state == "inflight"


def test_auth_failure_is_a_known_non_commit_not_ambiguous(tmp_path):
    # ZohoAuthError comes from the token refresh, which strictly
    # precedes the POST: nothing reached Zoho, so the intent rolls
    # back (no quarantine) and the batch stops with a credential error.
    from expense_recon.zoho.client import ZohoAuthError

    entries = entries_from_rows(_entry_rows("t1") + _entry_rows("t2"), _chart())
    client = FakeClient(results=[ZohoAuthError("token refresh failed (status 400)")])
    with PostLedger(tmp_path / "l.sqlite") as ledger:
        report = execute_post(client, tuple(entries), ledger, ORG, now_iso=_now())
        assert report.posted == () and report.ambiguous == ()
        assert report.rejected[0][0] == "t1"
        assert "auth failed before POST" in report.rejected[0][1]
        assert report.not_attempted == ("t2",)
        assert ledger.status_for(ORG, "t1") is None  # rolled back, re-postable
        assert ledger.status_for(ORG, "t2") is None


# ── writer -> reader -> entries round-trip (column-contract pin) ─────

def test_writer_reader_entries_round_trip(tmp_path):
    """The poster consumes REAL write_zoho_export output, not
    hand-built rows: pins the column contract end to end so a
    ZOHO_COLUMNS change cannot desynchronize the reader silently."""
    from datetime import date

    from expense_recon.matching.types import (
        Categorization,
        ClassificationSource,
        LineItem,
        Match,
        MatchOutcome,
        MatchType,
        Receipt,
        Transaction,
    )
    from expense_recon.output.zoho_export import read_journal_csv, write_zoho_export

    tx = Transaction(
        transaction_id="t1", legal_entity_id="le1", account_id="amex-usd",
        transaction_date=date(2026, 4, 7), posting_date=None,
        amount=Decimal("180"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement="AMAZON",
    )
    rec = Receipt(
        document_id="r1", legal_entity_id="le1",
        detected_date=date(2026, 4, 7), detected_total=Decimal("180"),
        detected_currency="USD", detected_vendor="Amazon",
        line_items=(
            LineItem(
                description="flight", line_total=Decimal("180"),
                categorization=Categorization(
                    category="Travel", zoho_account="6000 Travel: Flights",
                    confidence=0.9, source=ClassificationSource.LINE,
                    reasoning="t",
                ),
            ),
        ),
    )
    outcome = MatchOutcome(matches=[Match("t1", "r1", MatchType.EXACT, 0.99, "x", False)])
    chart = _chart()
    out = write_zoho_export(
        outcome, [tx], [rec], tmp_path / "zoho.csv",
        chart_of_accounts=chart,
        card_accounts={"amex-usd": "A200 Amex Card"},
    )

    entries = entries_from_rows(read_journal_csv(out), chart)
    (entry,) = entries
    assert entry.postable, entry.blockers
    assert entry.reference == "t1" and entry.journal_date == "2026-04-07"
    debit = next(ln for ln in entry.lines if ln.debit_or_credit == "debit")
    credit = next(ln for ln in entry.lines if ln.debit_or_credit == "credit")
    assert debit.account_id == "111" and debit.amount == Decimal("180.00")
    assert credit.account_id == "222" and credit.amount == Decimal("180.00")
