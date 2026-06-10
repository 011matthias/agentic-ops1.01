"""Run history — SQLite run-log (BLUEPRINT 5.7-5.10, ANNEALING C1).

Persists one row per reconciliation run plus one row per transaction
decision, so Chris can answer "what did we do for Amex in April" and
compare two runs of the same month after fixing a receipt.

Opt-in: the CLI only writes to the run-log when the config carries a
`run_log:` block (`{"run_log": {"path": "history.sqlite"}}`). With no
block the tool behaves exactly as before — no file is created, no
behaviour changes. This keeps the run-log off by default (and out of
every existing test) until a deployment turns it on.

Audit columns (C1): when, who (operator), source files, output path,
counts, and LLM cost — enough to reconstruct a run without re-reading
the report.

The run-log is operational metadata, NOT client financial data: it
stores transaction IDs, match types, and counts, never account names,
amounts, vendor names, or receipt contents. Safe to keep alongside the
tool; it is not the chart of accounts.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id           TEXT PRIMARY KEY,
    created_at       TEXT NOT NULL,
    operator         TEXT,
    config_path      TEXT,
    statement_path   TEXT,
    account_id       TEXT,
    legal_entity_id  TEXT,
    report_path      TEXT,
    n_transactions   INTEGER NOT NULL,
    n_receipts       INTEGER NOT NULL,
    n_matched        INTEGER NOT NULL,
    n_review         INTEGER NOT NULL,
    n_unmatched      INTEGER NOT NULL,
    n_parse_errors   INTEGER NOT NULL,
    llm_calls        INTEGER NOT NULL,
    llm_cost_usd     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tx_decisions (
    run_id          TEXT NOT NULL,
    transaction_id  TEXT NOT NULL,
    document_id     TEXT,
    match_type      TEXT NOT NULL,
    confidence      REAL,
    requires_review INTEGER NOT NULL,
    reason          TEXT,
    PRIMARY KEY (run_id, transaction_id),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);
CREATE INDEX IF NOT EXISTS ix_tx_decisions_run ON tx_decisions(run_id);
"""


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    created_at: str
    operator: str | None
    account_id: str | None
    legal_entity_id: str | None
    statement_path: str | None
    report_path: str | None
    n_transactions: int
    n_receipts: int
    n_matched: int
    n_review: int
    n_unmatched: int
    n_parse_errors: int
    llm_calls: int
    llm_cost_usd: Decimal


@dataclass(frozen=True)
class TxDecision:
    transaction_id: str
    document_id: str | None
    match_type: str
    confidence: float | None
    requires_review: bool
    reason: str | None


class RunLog:
    """Thin wrapper over a SQLite run-log. Open it, call record_run /
    list_runs / get_run / get_decisions, close it (or use as a context
    manager)."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        with closing(self._conn.cursor()) as cur:
            cur.executescript(_SCHEMA)
        self._conn.commit()

    def __enter__(self) -> "RunLog":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        self._conn.close()

    def record_run(
        self,
        *,
        run_id: str,
        created_at: str,
        summary: dict,
        decisions: list[TxDecision],
        operator: str | None = None,
    ) -> None:
        """Insert one run + its transaction decisions atomically."""
        with self._conn:  # transaction
            self._conn.execute(
                """INSERT INTO runs (
                    run_id, created_at, operator, config_path, statement_path,
                    account_id, legal_entity_id, report_path, n_transactions,
                    n_receipts, n_matched, n_review, n_unmatched, n_parse_errors,
                    llm_calls, llm_cost_usd
                ) VALUES (
                    :run_id, :created_at, :operator, :config_path, :statement_path,
                    :account_id, :legal_entity_id, :report_path, :n_transactions,
                    :n_receipts, :n_matched, :n_review, :n_unmatched, :n_parse_errors,
                    :llm_calls, :llm_cost_usd
                )""",
                {
                    "run_id": run_id,
                    "created_at": created_at,
                    "operator": operator,
                    "config_path": summary.get("config_path"),
                    "statement_path": summary.get("statement_path"),
                    "account_id": summary.get("account_id"),
                    "legal_entity_id": summary.get("legal_entity_id"),
                    "report_path": summary.get("report_path"),
                    "n_transactions": summary["n_transactions"],
                    "n_receipts": summary["n_receipts"],
                    "n_matched": summary["n_matched"],
                    "n_review": summary["n_review"],
                    "n_unmatched": summary["n_unmatched"],
                    "n_parse_errors": summary.get("n_parse_errors", 0),
                    "llm_calls": summary.get("llm_calls", 0),
                    "llm_cost_usd": str(summary.get("llm_cost_usd", "0")),
                },
            )
            self._conn.executemany(
                """INSERT INTO tx_decisions (
                    run_id, transaction_id, document_id, match_type,
                    confidence, requires_review, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        run_id, d.transaction_id, d.document_id, d.match_type,
                        d.confidence, int(d.requires_review), d.reason,
                    )
                    for d in decisions
                ],
            )

    def list_runs(self, limit: int = 20) -> list[RunSummary]:
        cur = self._conn.execute(
            "SELECT * FROM runs ORDER BY created_at DESC, run_id DESC LIMIT ?",
            (limit,),
        )
        return [_row_to_summary(r) for r in cur.fetchall()]

    def get_run(self, run_id: str) -> RunSummary | None:
        """Exact match, or unique prefix match (run IDs are long; Chris
        types the first few characters)."""
        cur = self._conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
        row = cur.fetchone()
        if row is not None:
            return _row_to_summary(row)
        cur = self._conn.execute(
            "SELECT * FROM runs WHERE run_id LIKE ? || '%'", (run_id,)
        )
        rows = cur.fetchall()
        if len(rows) == 1:
            return _row_to_summary(rows[0])
        return None  # 0 or ambiguous

    def get_decisions(self, run_id: str) -> list[TxDecision]:
        cur = self._conn.execute(
            "SELECT * FROM tx_decisions WHERE run_id = ? ORDER BY transaction_id",
            (run_id,),
        )
        return [_row_to_decision(r) for r in cur.fetchall()]


def _row_to_summary(r: sqlite3.Row) -> RunSummary:
    return RunSummary(
        run_id=r["run_id"],
        created_at=r["created_at"],
        operator=r["operator"],
        account_id=r["account_id"],
        legal_entity_id=r["legal_entity_id"],
        statement_path=r["statement_path"],
        report_path=r["report_path"],
        n_transactions=r["n_transactions"],
        n_receipts=r["n_receipts"],
        n_matched=r["n_matched"],
        n_review=r["n_review"],
        n_unmatched=r["n_unmatched"],
        n_parse_errors=r["n_parse_errors"],
        llm_calls=r["llm_calls"],
        llm_cost_usd=Decimal(r["llm_cost_usd"]),
    )


def _row_to_decision(r: sqlite3.Row) -> TxDecision:
    return TxDecision(
        transaction_id=r["transaction_id"],
        document_id=r["document_id"],
        match_type=r["match_type"],
        confidence=r["confidence"],
        requires_review=bool(r["requires_review"]),
        reason=r["reason"],
    )


def decisions_from_outcome(outcome) -> list[TxDecision]:
    """Flatten a MatchOutcome into one TxDecision per transaction.

    Matched + judgment + ambiguous transactions each contribute their
    Match; unmatched transactions contribute a synthetic "unmatched"
    decision so every transaction the run saw is recorded (the
    reconciliation guarantee carried into the log)."""
    decisions: list[TxDecision] = []
    seen: set[str] = set()

    for bucket in (outcome.matches, outcome.judgment_required, outcome.ambiguous):
        for m in bucket:
            if m.transaction_id in seen:
                continue
            seen.add(m.transaction_id)
            decisions.append(
                TxDecision(
                    transaction_id=m.transaction_id,
                    document_id=m.document_id,
                    match_type=m.match_type.value if hasattr(m.match_type, "value") else str(m.match_type),
                    confidence=m.confidence,
                    requires_review=m.requires_review,
                    reason=m.reason,
                )
            )

    for tx_id in outcome.unmatched_transactions:
        if tx_id in seen:
            continue
        seen.add(tx_id)
        decisions.append(
            TxDecision(
                transaction_id=tx_id,
                document_id=None,
                match_type="unmatched",
                confidence=None,
                requires_review=True,
                reason="no receipt matched",
            )
        )
    return decisions
