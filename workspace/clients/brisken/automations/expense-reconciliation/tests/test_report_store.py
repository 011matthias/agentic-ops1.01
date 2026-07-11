"""BLUEPRINT 8.3 — Zoho Expense report table + per-expense cross-reference.

All offline. Shapes mirror the ER-00214/215/216 samples (a monthly admin
report carrying a few BRL/USD/EUR expense lines)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from expense_recon.matching.types import Receipt
from expense_recon.store import (
    Report,
    ReportConflictError,
    ReportIngestResult,
    ReportStore,
    group_by_report,
)


def _rcpt(
    doc: str,
    *,
    report: str | None = "ER-00214",
    total: str | None = "50.00",
    currency: str | None = "USD",
    when: str | None = "2026-03-05",
    vendor: str = "STARBUCKS",
) -> Receipt:
    return Receipt(
        document_id=doc,
        legal_entity_id="brisken-us",
        detected_date=date.fromisoformat(when) if when else None,
        detected_total=Decimal(total) if total is not None else None,
        detected_currency=currency,
        detected_vendor=vendor,
        report_number=report,
    )


# ── ingest + metadata ───────────────────────────────────────────────


def test_fresh_ingest_links_all_and_records_report(tmp_path):
    db = tmp_path / "reports.sqlite"
    with ReportStore(db) as store:
        res = store.ingest_report(
            [_rcpt("EXP-1"), _rcpt("EXP-2", total="12.00"), _rcpt("EXP-3", total="9.50")],
            report_number="ER-00214",
            submitter="Dirk Neumann",
            status="Draft",
            ingested_at="2026-06-12T00:00:00+00:00",
        )
        assert res == ReportIngestResult("ER-00214", linked=3, already_linked=0)
        assert res.total == 3
        assert store.count() == 1
        assert store.expense_count() == 3
        rep = store.get_report("ER-00214")
        assert rep.submitter == "Dirk Neumann"
        assert rep.status == "Draft"
        assert rep.n_expenses == 3


def test_derives_period_and_multicurrency_totals(tmp_path):
    # The ER-00214 shape: one report mixing BRL and USD lines. Totals are
    # summed per native currency; period is the min/max expense date.
    db = tmp_path / "reports.sqlite"
    with ReportStore(db) as store:
        store.ingest_report(
            [
                _rcpt("EXP-1", total="10000.00", currency="BRL", when="2026-03-02"),
                _rcpt("EXP-2", total="943.33", currency="BRL", when="2026-03-28"),
                _rcpt("EXP-3", total="128.36", currency="USD", when="2026-03-15"),
            ],
            report_number="ER-00214",
            ingested_at="2026-06-12T00:00:00+00:00",
        )
        rep = store.get_report("ER-00214")
        assert rep.currency_totals == {"BRL": Decimal("10943.33"), "USD": Decimal("128.36")}
        assert rep.period_start == "2026-03-02"
        assert rep.period_end == "2026-03-28"


def test_header_fields_and_base_total_roundtrip(tmp_path):
    db = tmp_path / "reports.sqlite"
    with ReportStore(db) as store:
        store.ingest_report(
            [_rcpt("EXP-1", total="128.36", currency="USD")],
            report_number="ER-00214",
            report_name="CorpServ ADMIN DN 2838 - Dirk Neumann - 2026-03-01 to 2026-03-31",
            description="DN expenses Admin 2026-03",
            submitter="Dirk Neumann",
            status="Draft",
            ic_allocation="All CorpServ",
            base_total=Decimal("2203.05"),
            base_currency="USD",
            source_path="ER-00214.csv",
            ingested_at="2026-06-12T00:00:00+00:00",
        )
        rep = store.get_report("ER-00214")
        assert rep.report_name.startswith("CorpServ ADMIN DN 2838")
        assert rep.description == "DN expenses Admin 2026-03"
        assert rep.ic_allocation == "All CorpServ"
        assert rep.base_total == Decimal("2203.05")
        assert rep.base_currency == "USD"
        assert rep.source_path == "ER-00214.csv"


def test_missing_total_skipped_and_missing_currency_bucketed(tmp_path):
    # A line with no parsed total adds nothing; a line with no currency
    # must not silently drop its amount — it buckets under UNKNOWN.
    db = tmp_path / "reports.sqlite"
    with ReportStore(db) as store:
        store.ingest_report(
            [
                _rcpt("EXP-1", report="ER-00216", total=None, currency="USD"),
                _rcpt("EXP-2", report="ER-00216", total="40.00", currency=None),
            ],
            report_number="ER-00216",
            ingested_at="2026-06-12T00:00:00+00:00",
        )
        rep = store.get_report("ER-00216")
        assert rep.currency_totals == {"UNKNOWN": Decimal("40.00")}
        assert rep.n_expenses == 2  # both still linked, even the no-total one
        assert store.expense_count("ER-00216") == 2


# ── idempotency + report-number validation ──────────────────────────


def test_reingest_identical_is_idempotent(tmp_path):
    db = tmp_path / "reports.sqlite"
    rcpts = [_rcpt("EXP-1"), _rcpt("EXP-2", total="12.00")]
    with ReportStore(db) as store:
        store.ingest_report(rcpts, report_number="ER-00214", ingested_at="2026-06-12T00:00:00+00:00")
        # Same id, same content (rows reordered) -> no new links, no error.
        res = store.ingest_report(
            list(reversed(rcpts)), report_number="ER-00214",
            ingested_at="2026-06-12T01:00:00+00:00",
        )
        assert res.linked == 0
        assert res.already_linked == 2
        assert store.expense_count("ER-00214") == 2
        assert store.count() == 1


def test_same_report_changed_content_conflicts(tmp_path):
    db = tmp_path / "reports.sqlite"
    with ReportStore(db) as store:
        store.ingest_report([_rcpt("EXP-1")], report_number="ER-00214", ingested_at="2026-06-12T00:00:00+00:00")
        with pytest.raises(ReportConflictError):
            store.ingest_report(
                [_rcpt("EXP-1"), _rcpt("EXP-2", total="99.00")],
                report_number="ER-00214",
                ingested_at="2026-06-12T01:00:00+00:00",
            )
        # The rejected ingest left no partial state.
        assert store.expense_count("ER-00214") == 1
        assert store.get_report("ER-00214").n_expenses == 1


def test_replace_true_updates_header_and_membership(tmp_path):
    db = tmp_path / "reports.sqlite"
    with ReportStore(db) as store:
        store.ingest_report(
            [_rcpt("EXP-1")], report_number="ER-00214", status="Draft",
            ingested_at="2026-06-12T00:00:00+00:00",
        )
        res = store.ingest_report(
            [_rcpt("EXP-1"), _rcpt("EXP-2", total="99.00")],
            report_number="ER-00214", status="Submitted",
            ingested_at="2026-06-12T03:00:00+00:00",
            replace=True,
        )
        assert res.total == 2
        assert store.expense_count("ER-00214") == 2
        rep = store.get_report("ER-00214")
        assert rep.status == "Submitted"
        assert rep.ingested_at == "2026-06-12T03:00:00+00:00"


def test_replace_shrinks_membership_removes_orphans(tmp_path):
    # A re-export that dropped a line must not leave the orphan linked.
    db = tmp_path / "reports.sqlite"
    with ReportStore(db) as store:
        store.ingest_report(
            [_rcpt("EXP-1"), _rcpt("EXP-2", total="12.00")],
            report_number="ER-00214", ingested_at="2026-06-12T00:00:00+00:00",
        )
        store.ingest_report(
            [_rcpt("EXP-1")], report_number="ER-00214",
            ingested_at="2026-06-12T02:00:00+00:00", replace=True,
        )
        assert store.expenses_for("ER-00214") == ["EXP-1"]
        assert store.report_for("EXP-2") is None


# ── cross-reference ─────────────────────────────────────────────────


def test_report_for_and_expenses_for(tmp_path):
    db = tmp_path / "reports.sqlite"
    with ReportStore(db) as store:
        store.ingest_report(
            [_rcpt("EXP-1"), _rcpt("EXP-2", total="12.00")],
            report_number="ER-00214", ingested_at="2026-06-12T00:00:00+00:00",
        )
        store.ingest_report(
            [_rcpt("EXP-9", report="ER-00216", total="155.61", currency="USD")],
            report_number="ER-00216", ingested_at="2026-06-12T00:00:00+00:00",
        )
        assert store.report_for("EXP-1") == "ER-00214"
        assert store.report_for("EXP-9") == "ER-00216"
        assert store.report_for("EXP-404") is None
        assert store.expenses_for("ER-00214") == ["EXP-1", "EXP-2"]
        assert store.expenses_for("ER-00216") == ["EXP-9"]


def test_mislink_expense_names_other_report_raises(tmp_path):
    # An expense whose own report_number disagrees with the target report
    # is a grouping bug; always rejected, even with replace.
    db = tmp_path / "reports.sqlite"
    with ReportStore(db) as store:
        with pytest.raises(ReportConflictError, match="ER-00999"):
            store.ingest_report(
                [_rcpt("EXP-1", report="ER-00999")],
                report_number="ER-00214",
                ingested_at="2026-06-12T00:00:00+00:00",
            )


def test_cross_report_expense_conflicts_without_replace(tmp_path):
    # document_id is globally unique: one expense, one report. Claiming an
    # expense already linked elsewhere raises unless replace is passed.
    db = tmp_path / "reports.sqlite"
    with ReportStore(db) as store:
        store.ingest_report(
            [_rcpt("EXP-1", report=None)], report_number="ER-00214",
            ingested_at="2026-06-12T00:00:00+00:00",
        )
        with pytest.raises(ReportConflictError, match="already linked"):
            store.ingest_report(
                [_rcpt("EXP-1", report=None)], report_number="ER-00216",
                ingested_at="2026-06-12T01:00:00+00:00",
            )
        # EXP-1 stayed on its original report.
        assert store.report_for("EXP-1") == "ER-00214"


def test_replace_moves_expense_between_reports(tmp_path):
    db = tmp_path / "reports.sqlite"
    with ReportStore(db) as store:
        store.ingest_report(
            [_rcpt("EXP-1", report=None)], report_number="ER-00214",
            ingested_at="2026-06-12T00:00:00+00:00",
        )
        store.ingest_report(
            [_rcpt("EXP-1", report=None)], report_number="ER-00216",
            ingested_at="2026-06-12T01:00:00+00:00", replace=True,
        )
        assert store.report_for("EXP-1") == "ER-00216"
        assert store.expenses_for("ER-00214") == []
        assert store.expense_count() == 1  # not double-counted


# ── grouping + persistence ──────────────────────────────────────────


def test_group_by_report_splits_including_none_bucket():
    grouped = group_by_report(
        [
            _rcpt("EXP-1", report="ER-00214"),
            _rcpt("EXP-2", report="ER-00216"),
            _rcpt("EXP-3", report="ER-00214"),
            _rcpt("EXP-4", report=None),
        ]
    )
    assert set(grouped) == {"ER-00214", "ER-00216", None}
    assert [r.document_id for r in grouped["ER-00214"]] == ["EXP-1", "EXP-3"]
    assert [r.document_id for r in grouped[None]] == ["EXP-4"]


def test_persists_across_reopen(tmp_path):
    db = tmp_path / "reports.sqlite"
    with ReportStore(db) as store:
        store.ingest_report(
            [_rcpt("EXP-1"), _rcpt("EXP-2", total="12.00")],
            report_number="ER-00214", ingested_at="2026-06-12T00:00:00+00:00",
        )
    # Reopen: the report + its links survive (the outlives-Zoho property).
    with ReportStore(db) as store:
        assert store.count() == 1
        assert store.expense_count() == 2
        assert store.report_for("EXP-1") == "ER-00214"
        assert isinstance(store.reports()[0], Report)


def test_count_and_expense_count(tmp_path):
    db = tmp_path / "reports.sqlite"
    with ReportStore(db) as store:
        store.ingest_report(
            [_rcpt("EXP-1"), _rcpt("EXP-2", total="12.00")],
            report_number="ER-00214", ingested_at="2026-06-12T00:00:00+00:00",
        )
        store.ingest_report(
            [_rcpt("EXP-9", report="ER-00216", total="155.61")],
            report_number="ER-00216", ingested_at="2026-06-12T00:00:00+00:00",
        )
        assert store.count() == 2
        assert store.expense_count() == 3
        assert store.expense_count("ER-00214") == 2
        assert store.expense_count("ER-00216") == 1
