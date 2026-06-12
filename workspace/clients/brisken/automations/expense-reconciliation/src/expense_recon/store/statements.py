"""Bank-statement table + dedup (BLUEPRINT 8.2, Path A).

One persistent SQLite table of bank-statement transactions across all
banks/cards. Two jobs:

1. **Dedup on re-ingest.** A transaction is identified by a content
   fingerprint (account + dates + amount + currency + vendor), not by
   the parser's row-index id (which is unstable across re-exports). So
   re-downloading an overlapping period counts each transaction once.
   This is a real Brisken case: the Chase historic-activity export
   spans 2023-11 -> 2026-06 and overlaps every monthly statement
   download. ``INSERT OR IGNORE`` on the fingerprint primary key does
   the dedup at the storage layer.

2. **Statement-number validation.** Each ingest batch is recorded under
   a caller-supplied ``statement_id`` with a content hash. Re-ingesting
   the same ``statement_id`` with identical content is an idempotent
   no-op; re-ingesting it with *different* content raises
   ``StatementConflictError`` unless ``replace=True`` is passed. This
   catches "Chris re-downloaded and the bank revised a charge" instead
   of silently double-storing it.

Follows the ``runlog.py`` pattern: thin wrapper, schema-on-open,
opt-in (no table exists until a caller opens a store), caller-provided
timestamp for deterministic tests. The table stores real transaction
fields (amount, vendor) and so IS client financial data, unlike the
run-log; it lives wherever the deployment keeps Brisken's data, not
alongside the tool.

The reconciliation guarantee (v2 spec 25.5) is preserved at this layer
too: a bank revision under ``replace=True`` inserts the new version and
does NOT retract the superseded transaction (both survive, flagged at
match time), so nothing the tool ever saw is silently dropped. Net-new
retraction of stale revisions waits for a real revised statement to
land (BLUEPRINT "do not over-anneal before data lands").
"""
from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from ..matching.types import Transaction

_SCHEMA = """
CREATE TABLE IF NOT EXISTS statements (
    statement_id     TEXT PRIMARY KEY,
    account_id       TEXT,
    source_path      TEXT,
    ingested_at      TEXT NOT NULL,
    period_start     TEXT,
    period_end       TEXT,
    content_hash     TEXT NOT NULL,
    n_transactions   INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS statement_transactions (
    fingerprint           TEXT PRIMARY KEY,
    statement_id          TEXT NOT NULL,
    source_transaction_id TEXT,
    account_id            TEXT NOT NULL,
    legal_entity_id       TEXT,
    transaction_date      TEXT NOT NULL,
    posting_date          TEXT,
    amount                TEXT NOT NULL,
    transaction_currency  TEXT NOT NULL,
    account_card_currency TEXT NOT NULL,
    vendor_from_statement TEXT,
    raw_text              TEXT,
    FOREIGN KEY (statement_id) REFERENCES statements(statement_id)
);
CREATE INDEX IF NOT EXISTS ix_stmt_tx_account ON statement_transactions(account_id);
CREATE INDEX IF NOT EXISTS ix_stmt_tx_statement ON statement_transactions(statement_id);
"""


class StatementConflictError(ValueError):
    """A ``statement_id`` was re-ingested with different content and the
    caller did not pass ``replace=True``."""


def fingerprint(tx: Transaction) -> str:
    """Stable content fingerprint for one statement transaction.

    The parser's ``transaction_id`` (``{account_id}:{row_index}``) is
    NOT used: row index shifts between exports, so the same charge would
    fingerprint differently across two downloads and defeat dedup.
    Instead we hash the fields that identify the charge itself. Amount
    is normalized through ``Decimal`` so ``50``, ``50.0`` and ``50.00``
    collapse to one fingerprint; dates are ISO; the vendor string is
    taken verbatim (banks print it consistently within one card).
    """
    parts = (
        (tx.account_id or "").strip().upper(),
        tx.transaction_date.isoformat() if tx.transaction_date else "",
        tx.posting_date.isoformat() if tx.posting_date else "",
        _norm_amount(tx.amount),
        (tx.transaction_currency or "").strip().upper(),
        (tx.vendor_from_statement or "").strip().upper(),
    )
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _norm_amount(amount: Decimal) -> str:
    # Normalize so 50 == 50.0 == 50.00 fingerprint identically, while
    # preserving sign (refunds are negative and must not collapse into
    # the matching positive charge).
    return format(Decimal(amount).normalize(), "f")


@dataclass(frozen=True)
class IngestResult:
    """Outcome of one ``ingest_transactions`` batch.

    ``inserted`` are transactions new to the table; ``duplicates`` were
    already present (same fingerprint) and ignored. ``inserted +
    duplicates == total`` always.
    """

    statement_id: str
    inserted: int
    duplicates: int

    @property
    def total(self) -> int:
        return self.inserted + self.duplicates


@dataclass(frozen=True)
class StatementBatch:
    statement_id: str
    account_id: str | None
    source_path: str | None
    ingested_at: str
    period_start: str | None
    period_end: str | None
    content_hash: str
    n_transactions: int


class StatementStore:
    """Thin wrapper over the persistent bank-statement table. Open it,
    ``ingest_transactions`` / ``transactions`` / ``count`` / ``batches``,
    close it (or use as a context manager)."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        with closing(self._conn.cursor()) as cur:
            cur.executescript(_SCHEMA)
        self._conn.commit()

    def __enter__(self) -> "StatementStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        self._conn.close()

    def ingest_transactions(
        self,
        transactions: list[Transaction],
        *,
        statement_id: str,
        source_path: str | None = None,
        ingested_at: str | None = None,
        replace: bool = False,
    ) -> IngestResult:
        """Ingest one statement's transactions under ``statement_id``.

        Dedup is global by content fingerprint across the whole table,
        so transactions shared with an earlier batch (overlapping
        period) are reported as ``duplicates`` and stored once. The
        batch is recorded in ``statements`` with a content hash for
        statement-number validation.

        Raises ``StatementConflictError`` if ``statement_id`` already
        exists with different content and ``replace`` is False.
        """
        if ingested_at is None:
            ingested_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

        content_hash = self._batch_hash(transactions)
        existing = self.get_batch(statement_id)
        if existing is not None and existing.content_hash != content_hash and not replace:
            raise StatementConflictError(
                f"statement_id {statement_id!r} already ingested with different "
                f"content (was {existing.n_transactions} tx, now "
                f"{len(transactions)}). Pass replace=True to update, or use a "
                f"distinct statement_id for a separate download."
            )

        account_ids = {(t.account_id or "").strip().upper() for t in transactions}
        batch_account = next(iter(account_ids)) if len(account_ids) == 1 else None
        period_start, period_end = _period(transactions)

        inserted = 0
        with self._conn:  # one transaction for the whole batch
            self._conn.execute(
                """INSERT INTO statements (
                        statement_id, account_id, source_path, ingested_at,
                        period_start, period_end, content_hash, n_transactions
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(statement_id) DO UPDATE SET
                        account_id=excluded.account_id,
                        source_path=excluded.source_path,
                        ingested_at=excluded.ingested_at,
                        period_start=excluded.period_start,
                        period_end=excluded.period_end,
                        content_hash=excluded.content_hash,
                        n_transactions=excluded.n_transactions""",
                (
                    statement_id, batch_account, source_path, ingested_at,
                    period_start, period_end, content_hash, len(transactions),
                ),
            )
            for tx in transactions:
                cur = self._conn.execute(
                    """INSERT OR IGNORE INTO statement_transactions (
                            fingerprint, statement_id, source_transaction_id,
                            account_id, legal_entity_id, transaction_date,
                            posting_date, amount, transaction_currency,
                            account_card_currency, vendor_from_statement, raw_text
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        fingerprint(tx), statement_id, tx.transaction_id,
                        tx.account_id, tx.legal_entity_id,
                        tx.transaction_date.isoformat() if tx.transaction_date else None,
                        tx.posting_date.isoformat() if tx.posting_date else None,
                        format(Decimal(tx.amount), "f"),
                        tx.transaction_currency, tx.account_card_currency,
                        tx.vendor_from_statement, tx.raw_text,
                    ),
                )
                inserted += cur.rowcount  # 1 when inserted, 0 when ignored

        return IngestResult(
            statement_id=statement_id,
            inserted=inserted,
            duplicates=len(transactions) - inserted,
        )

    def count(self, account_id: str | None = None) -> int:
        """Distinct transactions held (optionally for one account)."""
        if account_id is None:
            cur = self._conn.execute("SELECT COUNT(*) FROM statement_transactions")
        else:
            cur = self._conn.execute(
                "SELECT COUNT(*) FROM statement_transactions WHERE account_id = ?",
                (account_id,),
            )
        return int(cur.fetchone()[0])

    def transactions(self, account_id: str | None = None) -> list[Transaction]:
        """Reconstruct ``Transaction`` objects from the table, ready to
        feed the matcher again without re-parsing files (the
        survives-the-Zoho-exit property).

        The reconstructed ``transaction_id`` is derived from the
        fingerprint (``{account_id}:{fingerprint[:12]}``) so it is both
        stable across reconstructions and unique (fingerprint is the
        primary key), unlike the row-index id the parser assigns.
        """
        sql = "SELECT * FROM statement_transactions"
        params: tuple = ()
        if account_id is not None:
            sql += " WHERE account_id = ?"
            params = (account_id,)
        sql += " ORDER BY transaction_date, fingerprint"
        cur = self._conn.execute(sql, params)
        return [_row_to_tx(r) for r in cur.fetchall()]

    def batches(self) -> list[StatementBatch]:
        cur = self._conn.execute(
            "SELECT * FROM statements ORDER BY ingested_at DESC, statement_id DESC"
        )
        return [_row_to_batch(r) for r in cur.fetchall()]

    def get_batch(self, statement_id: str) -> StatementBatch | None:
        cur = self._conn.execute(
            "SELECT * FROM statements WHERE statement_id = ?", (statement_id,)
        )
        row = cur.fetchone()
        return _row_to_batch(row) if row is not None else None

    @staticmethod
    def _batch_hash(transactions: list[Transaction]) -> str:
        """Order-independent hash of a batch's transaction fingerprints,
        so a re-download whose rows come back in a different order still
        hashes identically (only genuine content changes flip it)."""
        fps = sorted(fingerprint(t) for t in transactions)
        return hashlib.sha256("|".join(fps).encode("utf-8")).hexdigest()


def _period(transactions: list[Transaction]) -> tuple[str | None, str | None]:
    dates: list[date] = [t.transaction_date for t in transactions if t.transaction_date]
    if not dates:
        return None, None
    return min(dates).isoformat(), max(dates).isoformat()


def _row_to_tx(r: sqlite3.Row) -> Transaction:
    fp = r["fingerprint"]
    account_id = r["account_id"]
    return Transaction(
        transaction_id=f"{account_id}:{fp[:12]}",
        legal_entity_id=r["legal_entity_id"] or "",
        account_id=account_id,
        transaction_date=date.fromisoformat(r["transaction_date"]),
        posting_date=date.fromisoformat(r["posting_date"]) if r["posting_date"] else None,
        amount=Decimal(r["amount"]),
        transaction_currency=r["transaction_currency"],
        account_card_currency=r["account_card_currency"],
        vendor_from_statement=r["vendor_from_statement"] or "",
        raw_text=r["raw_text"] or "",
    )


def _row_to_batch(r: sqlite3.Row) -> StatementBatch:
    return StatementBatch(
        statement_id=r["statement_id"],
        account_id=r["account_id"],
        source_path=r["source_path"],
        ingested_at=r["ingested_at"],
        period_start=r["period_start"],
        period_end=r["period_end"],
        content_hash=r["content_hash"],
        n_transactions=r["n_transactions"],
    )
