"""Zoho Expense report table + per-expense cross-reference (BLUEPRINT 8.3, Path A).

One persistent SQLite table of Zoho Expense REPORT metadata (ER-NNNNN),
plus a cross-reference linking each ingested expense to the report it
belongs to. Two jobs, paralleling the statement table (8.2):

1. **Report metadata + report-number validation.** Each report is
   recorded under its ``report_number`` with a content hash over its
   header fields and its expense set. Re-ingesting the same
   ``report_number`` with identical content is an idempotent no-op;
   re-ingesting it with *different* content raises ``ReportConflictError``
   unless ``replace=True``. This catches "Dirk revised ER-00215 and
   re-exported it" instead of silently keeping the stale header.

2. **Per-expense cross-reference.** Every expense (a ``Receipt`` keyed by
   ``document_id``) is linked to exactly one report, so the Books journal
   export (8.5) can carry the report reference next to each line, and so
   the report grouping that Zoho currently owns survives the Zoho
   switch-off. ``report_for(document_id)`` is the lookup 8.5 uses;
   ``expenses_for(report_number)`` is the reverse. ``document_id`` is the
   primary key of the cross-reference, so the database itself enforces
   "one expense, one report"; claiming an expense already linked to a
   different report raises unless ``replace=True``.

The report header fields are the ones the ER-00214/215/216 samples fix
(``context/expense-reports/2026-06-11-expense-report-samples.md``):
``report_name`` (the trip name), ``description``, ``submitter``,
``period_start``/``period_end`` (the report's month boundaries),
``status`` (Draft), ``ic_allocation`` ("All CorpServ"), and the
per-currency totals. Only ``report_number`` is required; the rest are
optional because the only live expense source is the Zoho Expense CSV
(8.1), whose rows carry the report number but not the report header, so
header fields the caller does not have stay None rather than fabricated
(B4 — never invent a plausible value).

Derived from the expense set, not the caller: ``period_start``/``end``
(min/max expense date), ``currency_totals`` (sum of expense totals by
native currency, the "BRL 10,943.33 + USD 128.36" shape on the report
header), and ``n_expenses``. ``base_total``/``base_currency`` (Zoho's
converted whole-report total, e.g. USD $2,203.05) are header-stated and
optional, because converting native subtotals to one base currency is an
FX step this layer does not perform.

Follows the ``statements.py`` / ``runlog.py`` pattern: thin wrapper,
schema-on-open, opt-in (no table exists until a caller opens a store),
caller-provided timestamp for deterministic tests. The table stores real
report metadata and so IS client financial data; it lives wherever the
deployment keeps Brisken's data, not alongside the tool.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from ..matching.types import Receipt

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    report_number    TEXT PRIMARY KEY,
    report_name      TEXT,
    description      TEXT,
    submitter        TEXT,
    period_start     TEXT,
    period_end       TEXT,
    status           TEXT,
    ic_allocation    TEXT,
    currency_totals  TEXT,
    base_total       TEXT,
    base_currency    TEXT,
    source_path      TEXT,
    ingested_at      TEXT NOT NULL,
    content_hash     TEXT NOT NULL,
    n_expenses       INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS report_expenses (
    document_id      TEXT PRIMARY KEY,
    report_number    TEXT NOT NULL,
    FOREIGN KEY (report_number) REFERENCES reports(report_number)
);
CREATE INDEX IF NOT EXISTS ix_report_exp_report ON report_expenses(report_number);
"""


class ReportConflictError(ValueError):
    """A ``report_number`` was re-ingested with different content, or an
    expense already linked to a different report was claimed, and the
    caller did not pass ``replace=True``."""


@dataclass(frozen=True)
class ReportIngestResult:
    """Outcome of one ``ingest_report`` call.

    ``linked`` are expenses newly attached to this report (new rows in the
    cross-reference); ``already_linked`` were already attached to it (an
    idempotent re-ingest). ``linked + already_linked == n_expenses`` for
    the non-replace path. Under ``replace=True`` the membership is rewritten
    wholesale and every expense reads as ``linked``.
    """

    report_number: str
    linked: int
    already_linked: int

    @property
    def total(self) -> int:
        return self.linked + self.already_linked


@dataclass(frozen=True)
class Report:
    report_number: str
    report_name: str | None
    description: str | None
    submitter: str | None
    period_start: str | None
    period_end: str | None
    status: str | None
    ic_allocation: str | None
    currency_totals: dict[str, Decimal]
    base_total: Decimal | None
    base_currency: str | None
    source_path: str | None
    ingested_at: str
    content_hash: str
    n_expenses: int


class ReportStore:
    """Thin wrapper over the persistent report table + cross-reference.
    Open it, ``ingest_report`` one report's metadata + its expenses,
    read back with ``reports`` / ``get_report`` / ``expenses_for`` /
    ``report_for``, close it (or use as a context manager)."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        with closing(self._conn.cursor()) as cur:
            cur.executescript(_SCHEMA)
        self._conn.commit()

    def __enter__(self) -> "ReportStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        self._conn.close()

    def ingest_report(
        self,
        expenses: list[Receipt],
        *,
        report_number: str,
        report_name: str | None = None,
        description: str | None = None,
        submitter: str | None = None,
        status: str | None = None,
        ic_allocation: str | None = None,
        base_total: Decimal | None = None,
        base_currency: str | None = None,
        source_path: str | None = None,
        ingested_at: str | None = None,
        replace: bool = False,
    ) -> ReportIngestResult:
        """Record one report's header + link its expenses.

        ``expenses`` are the receipts belonging to this report (group a
        flat receipt list with :func:`group_by_report` first). Period,
        per-currency totals, and the count are derived from them; the
        header fields not carried on the expense lines are passed in.

        Raises ``ReportConflictError`` when (a) an expense names a
        *different* ``report_number`` (a mis-link — always rejected), or
        (b) ``report_number`` already exists with different content, or
        (c) an expense is already linked to another report — for (b)/(c)
        pass ``replace=True`` to overwrite.
        """
        if ingested_at is None:
            ingested_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

        # (a) Mis-link guard. An expense that names its own report must
        # name THIS one; otherwise the caller grouped wrong. This is a
        # programming error, never a replace-able state.
        mismatched = sorted(
            {
                r.report_number
                for r in expenses
                if r.report_number and r.report_number != report_number
            }
        )
        if mismatched:
            raise ReportConflictError(
                f"ingest_report({report_number!r}) was given expense(s) whose own "
                f"report_number is {mismatched}. Group expenses by report_number "
                f"(see group_by_report) before ingesting."
            )

        currency_totals = _currency_totals(expenses)
        period_start, period_end = _period(expenses)
        n_expenses = len(expenses)
        content_hash = self._report_hash(
            report_number, report_name, description, submitter, status,
            ic_allocation, base_total, base_currency, expenses,
        )

        # (b) Report-number validation.
        existing = self.get_report(report_number)
        if existing is not None and existing.content_hash != content_hash and not replace:
            raise ReportConflictError(
                f"report_number {report_number!r} already ingested with different "
                f"content (was {existing.n_expenses} expense(s), now {n_expenses}). "
                f"Pass replace=True to update it."
            )

        # (c) Cross-report expense guard. document_id is globally unique;
        # an expense already linked to another report would be silently
        # kept there by INSERT OR IGNORE, so check explicitly.
        doc_ids = [r.document_id for r in expenses]
        elsewhere = self._linked_to_other_report(doc_ids, report_number)
        if elsewhere and not replace:
            raise ReportConflictError(
                f"expense(s) {elsewhere} are already linked to a different report. "
                f"Pass replace=True to move them to {report_number!r}."
            )

        inserted = 0
        with self._conn:  # one transaction for the whole report
            self._conn.execute(
                """INSERT INTO reports (
                        report_number, report_name, description, submitter,
                        period_start, period_end, status, ic_allocation,
                        currency_totals, base_total, base_currency, source_path,
                        ingested_at, content_hash, n_expenses
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(report_number) DO UPDATE SET
                        report_name=excluded.report_name,
                        description=excluded.description,
                        submitter=excluded.submitter,
                        period_start=excluded.period_start,
                        period_end=excluded.period_end,
                        status=excluded.status,
                        ic_allocation=excluded.ic_allocation,
                        currency_totals=excluded.currency_totals,
                        base_total=excluded.base_total,
                        base_currency=excluded.base_currency,
                        source_path=excluded.source_path,
                        ingested_at=excluded.ingested_at,
                        content_hash=excluded.content_hash,
                        n_expenses=excluded.n_expenses""",
                (
                    report_number, report_name, description, submitter,
                    period_start, period_end, status, ic_allocation,
                    _totals_to_json(currency_totals),
                    _opt_amount(base_total), base_currency, source_path,
                    ingested_at, content_hash, n_expenses,
                ),
            )
            if replace:
                # Rewrite membership: drop this report's prior links (so a
                # shrunk expense set leaves no orphans) and detach any
                # expense being moved in from another report.
                self._conn.execute(
                    "DELETE FROM report_expenses WHERE report_number = ?",
                    (report_number,),
                )
                for doc in elsewhere:
                    self._conn.execute(
                        "DELETE FROM report_expenses WHERE document_id = ?", (doc,)
                    )
            for doc in doc_ids:
                cur = self._conn.execute(
                    "INSERT OR IGNORE INTO report_expenses (document_id, report_number) "
                    "VALUES (?, ?)",
                    (doc, report_number),
                )
                inserted += cur.rowcount  # 1 when newly linked, 0 when already there

        return ReportIngestResult(
            report_number=report_number,
            linked=inserted,
            already_linked=n_expenses - inserted,
        )

    def count(self) -> int:
        """Number of reports held."""
        return int(self._conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0])

    def expense_count(self, report_number: str | None = None) -> int:
        """Number of expenses linked (optionally for one report)."""
        if report_number is None:
            cur = self._conn.execute("SELECT COUNT(*) FROM report_expenses")
        else:
            cur = self._conn.execute(
                "SELECT COUNT(*) FROM report_expenses WHERE report_number = ?",
                (report_number,),
            )
        return int(cur.fetchone()[0])

    def reports(self) -> list[Report]:
        cur = self._conn.execute(
            "SELECT * FROM reports ORDER BY ingested_at DESC, report_number DESC"
        )
        return [_row_to_report(r) for r in cur.fetchall()]

    def get_report(self, report_number: str) -> Report | None:
        cur = self._conn.execute(
            "SELECT * FROM reports WHERE report_number = ?", (report_number,)
        )
        row = cur.fetchone()
        return _row_to_report(row) if row is not None else None

    def expenses_for(self, report_number: str) -> list[str]:
        """The document_ids linked to ``report_number`` (the reverse of
        ``report_for``)."""
        cur = self._conn.execute(
            "SELECT document_id FROM report_expenses WHERE report_number = ? "
            "ORDER BY document_id",
            (report_number,),
        )
        return [r["document_id"] for r in cur.fetchall()]

    def report_for(self, document_id: str) -> str | None:
        """The report a given expense belongs to, or None if unlinked.
        This is the lookup the Books export (8.5) uses to carry the report
        reference next to each journal line."""
        cur = self._conn.execute(
            "SELECT report_number FROM report_expenses WHERE document_id = ?",
            (document_id,),
        )
        row = cur.fetchone()
        return row["report_number"] if row is not None else None

    def _linked_to_other_report(
        self, doc_ids: list[str], report_number: str
    ) -> list[str]:
        """document_ids in ``doc_ids`` already linked to a report other
        than ``report_number`` (sorted)."""
        if not doc_ids:
            return []
        placeholders = ",".join("?" * len(doc_ids))
        rows = self._conn.execute(
            f"SELECT document_id FROM report_expenses "
            f"WHERE document_id IN ({placeholders}) AND report_number <> ?",
            (*doc_ids, report_number),
        ).fetchall()
        return sorted(r["document_id"] for r in rows)

    @staticmethod
    def _report_hash(
        report_number: str,
        report_name: str | None,
        description: str | None,
        submitter: str | None,
        status: str | None,
        ic_allocation: str | None,
        base_total: Decimal | None,
        base_currency: str | None,
        expenses: list[Receipt],
    ) -> str:
        """Content hash over the header fields plus the expense set
        (each as document_id + normalized amount + currency), so a
        re-export whose expense rows come back in a different order still
        hashes identically; only a genuine header or membership change
        flips it."""
        header = "|".join(
            "" if v is None else str(v)
            for v in (
                report_number, report_name, description, submitter, status,
                ic_allocation, _opt_amount(base_total), base_currency,
            )
        )
        exp = sorted(
            f"{r.document_id}={_norm_amount(r.detected_total)}="
            f"{(r.detected_currency or '').strip().upper()}"
            for r in expenses
        )
        payload = "R:" + header + "||E:" + "|".join(exp)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def group_by_report(expenses: list[Receipt]) -> dict[str | None, list[Receipt]]:
    """Group receipts by ``report_number`` (the None bucket holds expenses
    with no report number). Order-preserving within each group. The caller
    feeds one group per ``ingest_report`` call; the None bucket is expenses
    that carry no report reference and so are not ingested as a report."""
    groups: dict[str | None, list[Receipt]] = {}
    for r in expenses:
        groups.setdefault(r.report_number, []).append(r)
    return groups


def _period(expenses: list[Receipt]) -> tuple[str | None, str | None]:
    dates: list[date] = [r.detected_date for r in expenses if r.detected_date]
    if not dates:
        return None, None
    return min(dates).isoformat(), max(dates).isoformat()


def _currency_totals(expenses: list[Receipt]) -> dict[str, Decimal]:
    """Sum expense totals by native currency. Expenses with no total are
    skipped (nothing to add); an expense with no currency buckets under
    ``"UNKNOWN"`` so its amount is never silently dropped."""
    totals: dict[str, Decimal] = {}
    for r in expenses:
        if r.detected_total is None:
            continue
        cur = (r.detected_currency or "").strip().upper() or "UNKNOWN"
        totals[cur] = totals.get(cur, Decimal("0")) + r.detected_total
    return totals


def _norm_amount(amount: Decimal | None) -> str:
    # Normalize so 50 == 50.0 == 50.00 hash identically; None (a receipt
    # with no parsed total) hashes as the empty string.
    if amount is None:
        return ""
    return format(Decimal(amount).normalize(), "f")


def _opt_amount(amount: Decimal | None) -> str | None:
    return None if amount is None else format(Decimal(amount), "f")


def _totals_to_json(totals: dict[str, Decimal]) -> str:
    return json.dumps({k: format(v, "f") for k, v in sorted(totals.items())})


def _totals_from_json(raw: str | None) -> dict[str, Decimal]:
    if not raw:
        return {}
    return {k: Decimal(v) for k, v in json.loads(raw).items()}


def _row_to_report(r: sqlite3.Row) -> Report:
    return Report(
        report_number=r["report_number"],
        report_name=r["report_name"],
        description=r["description"],
        submitter=r["submitter"],
        period_start=r["period_start"],
        period_end=r["period_end"],
        status=r["status"],
        ic_allocation=r["ic_allocation"],
        currency_totals=_totals_from_json(r["currency_totals"]),
        base_total=Decimal(r["base_total"]) if r["base_total"] else None,
        base_currency=r["base_currency"],
        source_path=r["source_path"],
        ingested_at=r["ingested_at"],
        content_hash=r["content_hash"],
        n_expenses=r["n_expenses"],
    )
