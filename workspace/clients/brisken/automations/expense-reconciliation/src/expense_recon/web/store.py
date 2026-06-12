"""SQLite persistence for web runs and the reviewer's decisions.

One small database (default `recon-web.sqlite` under the app data dir)
holds three tables:

* `runs`      one row per reconciliation the browser kicked off, with the
              full snapshot blob (see `serialize.py`) so the workbench
              re-renders without re-running the pipeline.
* `decisions` the reviewer's per-transaction verdict (pending / confirmed
              / rejected) and, for a needs-review row, which candidate
              receipt she picked. Applied when the exports regenerate.
* `category_overrides`  a reclassified category for one receipt line,
              keyed by (run, document, line index). Also applied on export.

The store is opened per operation as a context manager, mirroring the
`runlog.RunLog` precedent; for a single-user local tool SQLite's default
locking is sufficient.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

# Reviewer verdicts. `pending` is the default for every transaction until
# Chris acts; `confirmed` locks the (possibly picked) match as reconciled;
# `rejected` drops the match and sends the transaction to unmatched.
STATUS_PENDING = "pending"
STATUS_CONFIRMED = "confirmed"
STATUS_REJECTED = "rejected"
VALID_STATUSES = (STATUS_PENDING, STATUS_CONFIRMED, STATUS_REJECTED)


@dataclass
class RunRow:
    run_id: str
    created_at: str
    label: str
    operator: str | None
    summary: dict
    snapshot: dict
    config: dict
    work_dir: str
    llm_enabled: bool
    has_coa: bool


@dataclass
class Decision:
    status: str
    chosen_document_id: str | None


class RunStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def __enter__(self) -> "RunStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        self.conn.close()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id      TEXT PRIMARY KEY,
                created_at  TEXT NOT NULL,
                label       TEXT NOT NULL,
                operator    TEXT,
                summary     TEXT NOT NULL,
                snapshot    TEXT NOT NULL,
                config      TEXT NOT NULL,
                work_dir    TEXT NOT NULL,
                llm_enabled INTEGER NOT NULL DEFAULT 0,
                has_coa     INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS decisions (
                run_id             TEXT NOT NULL,
                transaction_id     TEXT NOT NULL,
                status             TEXT NOT NULL,
                chosen_document_id TEXT,
                updated_at         TEXT,
                PRIMARY KEY (run_id, transaction_id)
            );
            CREATE TABLE IF NOT EXISTS category_overrides (
                run_id       TEXT NOT NULL,
                document_id  TEXT NOT NULL,
                line_index   INTEGER NOT NULL,
                category     TEXT,
                zoho_account TEXT,
                updated_at   TEXT,
                PRIMARY KEY (run_id, document_id, line_index)
            );
            """
        )
        self.conn.commit()

    # -- runs -------------------------------------------------------------

    def create_run(
        self,
        *,
        run_id: str,
        created_at: str,
        label: str,
        operator: str | None,
        summary: dict,
        snapshot: dict,
        config: dict,
        work_dir: str,
        llm_enabled: bool,
        has_coa: bool,
    ) -> None:
        self.conn.execute(
            "INSERT INTO runs (run_id, created_at, label, operator, summary, "
            "snapshot, config, work_dir, llm_enabled, has_coa) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                created_at,
                label,
                operator,
                json.dumps(summary),
                json.dumps(snapshot),
                json.dumps(config),
                work_dir,
                int(llm_enabled),
                int(has_coa),
            ),
        )
        self.conn.commit()

    def list_runs(self) -> list[RunRow]:
        rows = self.conn.execute(
            "SELECT * FROM runs ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_run(r) for r in rows]

    def get_run(self, run_id: str) -> RunRow | None:
        row = self.conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        return self._row_to_run(row) if row else None

    @staticmethod
    def _row_to_run(row: sqlite3.Row) -> RunRow:
        return RunRow(
            run_id=row["run_id"],
            created_at=row["created_at"],
            label=row["label"],
            operator=row["operator"],
            summary=json.loads(row["summary"]),
            snapshot=json.loads(row["snapshot"]),
            config=json.loads(row["config"]),
            work_dir=row["work_dir"],
            llm_enabled=bool(row["llm_enabled"]),
            has_coa=bool(row["has_coa"]),
        )

    # -- decisions --------------------------------------------------------

    def get_decisions(self, run_id: str) -> dict[str, Decision]:
        rows = self.conn.execute(
            "SELECT transaction_id, status, chosen_document_id "
            "FROM decisions WHERE run_id = ?",
            (run_id,),
        ).fetchall()
        return {
            r["transaction_id"]: Decision(r["status"], r["chosen_document_id"])
            for r in rows
        }

    def set_decision(
        self,
        run_id: str,
        transaction_id: str,
        status: str,
        chosen_document_id: str | None,
        updated_at: str,
    ) -> None:
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid status {status!r}; expected {VALID_STATUSES}")
        self.conn.execute(
            "INSERT INTO decisions (run_id, transaction_id, status, "
            "chosen_document_id, updated_at) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(run_id, transaction_id) DO UPDATE SET "
            "status = excluded.status, "
            "chosen_document_id = excluded.chosen_document_id, "
            "updated_at = excluded.updated_at",
            (run_id, transaction_id, status, chosen_document_id, updated_at),
        )
        self.conn.commit()

    # -- category overrides ----------------------------------------------

    def get_category_overrides(self, run_id: str) -> dict[tuple[str, int], dict]:
        rows = self.conn.execute(
            "SELECT document_id, line_index, category, zoho_account "
            "FROM category_overrides WHERE run_id = ?",
            (run_id,),
        ).fetchall()
        return {
            (r["document_id"], r["line_index"]): {
                "category": r["category"],
                "zoho_account": r["zoho_account"],
            }
            for r in rows
        }

    def set_category_override(
        self,
        run_id: str,
        document_id: str,
        line_index: int,
        category: str | None,
        zoho_account: str | None,
        updated_at: str,
    ) -> None:
        self.conn.execute(
            "INSERT INTO category_overrides (run_id, document_id, line_index, "
            "category, zoho_account, updated_at) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(run_id, document_id, line_index) DO UPDATE SET "
            "category = excluded.category, "
            "zoho_account = excluded.zoho_account, "
            "updated_at = excluded.updated_at",
            (run_id, document_id, line_index, category, zoho_account, updated_at),
        )
        self.conn.commit()
