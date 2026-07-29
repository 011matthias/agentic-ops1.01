"""SQLite persistence for web runs and the reviewer's decisions.

One small database (default `recon-web.sqlite` under the app data dir)
holds three tables:

* `runs`      one row per reconciliation the browser kicked off, with the
              full snapshot blob (see `serialize.py`) so the workbench
              re-renders without re-running the pipeline.
* `decisions` the reviewer's per-transaction verdict (pending / confirmed
              / rejected), for a needs-review row which candidate receipt
              she picked, and the §17 disposition (business / personal /
              reimbursable / do-not-export). Applied when the exports
              regenerate.
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
# L1/PR-E: "this charge is already entered in Zoho" (her yellow). Terminal
# like confirmed (counts as decided, claims its receipt) but the Zoho
# journal export EXCLUDES it -- never double-post.
STATUS_ALREADY_POSTED = "already_posted"
VALID_STATUSES = (
    STATUS_PENDING,
    STATUS_CONFIRMED,
    STATUS_REJECTED,
    STATUS_ALREADY_POSTED,
)

# §17 dispositions: whose spend a charge is and how it exports. Stored on
# the same (run_id, transaction_id) grain as the status verdict, but the
# two layers are orthogonal: `set_disposition` and `set_decision` each
# upsert ONLY their own columns, so triaging a row never clears its
# disposition and vice versa. `business` (the default when no row / NULL)
# posts normally; `personal_on_business_card` and `do_not_export` are
# withheld from the Zoho journal; `reimbursable_personal` posts with the
# credit redirected to the reimbursement clearing account.
DISPOSITION_BUSINESS = "business"
DISPOSITION_PERSONAL = "personal_on_business_card"
DISPOSITION_REIMBURSABLE = "reimbursable_personal"
DISPOSITION_DO_NOT_EXPORT = "do_not_export"
VALID_DISPOSITIONS = (
    DISPOSITION_BUSINESS,
    DISPOSITION_PERSONAL,
    DISPOSITION_REIMBURSABLE,
    DISPOSITION_DO_NOT_EXPORT,
)

# Receipt-first expense edits (Phase 4). `expense_field_overrides` holds
# the reviewer's per-expense HEADER edits (vendor / date / total / currency /
# tax / paid-through / legal entity), one row per (run, document, field);
# line-level category reclassification stays in `category_overrides`.
# `expense_edits` records whole-expense add / delete: one row per document,
# `op` add carries the manual expense's payload JSON, `op` delete soft-hides
# the document from the view + export. Both are applied at render/export
# time (`apply_expense_edits`), never written into the snapshot, mirroring
# how decisions overlay the statement-mode outcome.
EXPENSE_EDIT_ADD = "add"
EXPENSE_EDIT_DELETE = "delete"
VALID_EXPENSE_EDIT_OPS = (EXPENSE_EDIT_ADD, EXPENSE_EDIT_DELETE)

# Intake lifecycle (testing mode): the user's uploaded document set, waiting
# for an operator. `received` on upload; `processing` once an operator runs
# the pipeline on it; `ready` when the resulting run is published back.
INTAKE_RECEIVED = "received"
INTAKE_PROCESSING = "processing"
INTAKE_READY = "ready"
VALID_INTAKE_STATUSES = (INTAKE_RECEIVED, INTAKE_PROCESSING, INTAKE_READY)

# §18 duplicate-group resolutions. A reviewer's advisory verdict on a
# flagged duplicate group: `ignore` (dismiss the flag; not really a
# duplicate) or `confirmed` (yes, acknowledged). Advisory only — it never
# touches buckets, never auto-deletes. Absent => still flagged / unresolved.
DUP_IGNORE = "ignore"
DUP_CONFIRMED = "confirmed"
VALID_DUP_RESOLUTIONS = (DUP_IGNORE, DUP_CONFIRMED)

# §16 export policy (the single-row `settings` table). The gate ships
# advisory/OFF: `export_approved_only=False` keeps the current
# review-everything behaviour (only the writer's own posting policy
# applies). Snapshotted into each run's `config["policy"]` at creation so a
# run reproduces under the policy that was live when it ran, not whatever
# the setting later becomes.
#
# Master data (2026-07-22). The hosted surface had no home for the
# operator input the pipeline needs, so three capabilities were dead on
# every hosted run while working locally from a config file:
#
#   fx_reference_rates  {"BRL:USD": "0.192448"} — the month's reference
#     rate per currency pair. Without one, a cross-currency receipt can
#     only reach the implied-rate band / LLM judgment: the real April run
#     matched 0 of 94 while the same two files matched 29/36 locally with
#     a rate file. Month-scoped operator input, never derived from Zoho's
#     per-line rate (wrong by up to 12.8%, LD-5).
#   card_entities  {"2838": "Corporate Services"} — maps a card to the
#     legal entity whose chart of accounts guards the export. Without it
#     `resolve_legal_entity` falls back to the raw card id, matching no
#     COA entity, so the gate silently never fires (`has_coa: false`).
#   card_accounts  {"2838": "1010 Chase Corporate"} — the Zoho bank/card
#     account each card's balancing credit posts to. Without it every
#     journal entry credits the visible `Card: 2838` placeholder.
#
# All three are read at run creation and snapshotted into the run's own
# config, so an existing run keeps the master data it ran under.
#   entities  (Phase 5, receipt-first) — the legal-entity REGISTRY:
#     {"Corporate Services": {org_id, chart_path?, scope_groups?,
#     default_paid_through?, account_picks?}}. Definable in the UI; wins
#     over the /data provisioning file's entity mapping when present
#     (coa_provision.coa_validation_from_settings). Distinct from
#     `card_entities`, which stays the card -> entity MAP.
#   merchants (2026-07-29, receipt-first) — the canonical MERCHANT REGISTRY:
#     {"Uber": {aliases: [...], category?, zoho_account?}}. Definable in the
#     UI (like `entities`); the highest-priority deterministic source for a
#     receipt's canonical vendor + default category in generate_expenses
#     (expense_recon.merchant_registry). Empty => no canonicalization.
SETTINGS_DEFAULTS: dict = {
    "export_approved_only": False,
    "fx_reference_rates": {},
    "card_entities": {},
    "card_accounts": {},
    "entities": {},
    "merchants": {},
}

# Settings keys holding a {str: str} map. Values are kept as STRINGS: a
# Decimal FX rate keeps full precision as text, a json float does not.
SETTINGS_MAP_KEYS = ("fx_reference_rates", "card_entities", "card_accounts")

# Background-job states (durable: a Fly machine can scale to zero mid-run;
# a job row that is still `running` at boot was interrupted).
JOB_RUNNING = "running"
JOB_DONE = "done"
JOB_ERROR = "error"


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
    published: bool = False
    published_at: str | None = None
    intake_id: str | None = None


@dataclass
class IntakeRow:
    intake_id: str
    created_at: str
    label: str
    uploaded_by: str | None
    statement_name: str
    receipts_name: str | None
    card_key: str | None
    work_dir: str
    status: str
    run_id: str | None
    detect_note: str | None
    updated_at: str | None


@dataclass
class Decision:
    status: str
    chosen_document_id: str | None
    updated_at: str | None = None
    # §17: None means "no explicit verdict" — the effective disposition is
    # then seeded by the service layer (Receipt.reimbursable, else business).
    disposition: str | None = None


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
                disposition        TEXT,
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
            CREATE TABLE IF NOT EXISTS intakes (
                intake_id      TEXT PRIMARY KEY,
                created_at     TEXT NOT NULL,
                label          TEXT NOT NULL,
                uploaded_by    TEXT,
                statement_name TEXT NOT NULL,
                receipts_name  TEXT,
                card_key       TEXT,
                work_dir       TEXT NOT NULL,
                status         TEXT NOT NULL DEFAULT 'received',
                run_id         TEXT,
                detect_note    TEXT,
                updated_at     TEXT
            );
            CREATE TABLE IF NOT EXISTS jobs (
                job_id     TEXT PRIMARY KEY,
                intake_id  TEXT,
                status     TEXT NOT NULL,
                run_id     TEXT,
                error      TEXT,
                stage      TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS settings (
                id         INTEGER PRIMARY KEY CHECK (id = 1),
                data       TEXT NOT NULL,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS duplicate_resolutions (
                run_id     TEXT NOT NULL,
                group_id   TEXT NOT NULL,
                resolution TEXT NOT NULL,
                updated_at TEXT,
                PRIMARY KEY (run_id, group_id)
            );
            CREATE TABLE IF NOT EXISTS expense_field_overrides (
                run_id      TEXT NOT NULL,
                document_id TEXT NOT NULL,
                field       TEXT NOT NULL,
                value       TEXT,
                updated_at  TEXT,
                PRIMARY KEY (run_id, document_id, field)
            );
            CREATE TABLE IF NOT EXISTS expense_edits (
                run_id      TEXT NOT NULL,
                document_id TEXT NOT NULL,
                op          TEXT NOT NULL,
                payload     TEXT,
                updated_at  TEXT,
                PRIMARY KEY (run_id, document_id)
            );
            CREATE TABLE IF NOT EXISTS login_failures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL,
                ts REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_login_failures_ts
                ON login_failures (ts);
            CREATE INDEX IF NOT EXISTS idx_login_failures_ip_ts
                ON login_failures (ip, ts);
            """
        )
        self._migrate()
        self.conn.commit()

    def _migrate(self) -> None:
        """Idempotent column adds for databases created before testing mode.
        Existing runs stay published=0 (operator-visible only) until an
        operator publishes them explicitly."""
        existing = {
            row["name"]
            for row in self.conn.execute("PRAGMA table_info(runs)").fetchall()
        }
        adds = (
            ("published", "INTEGER NOT NULL DEFAULT 0"),
            ("published_at", "TEXT"),
            ("intake_id", "TEXT"),
        )
        for column, ddl in adds:
            if column not in existing:
                self.conn.execute(f"ALTER TABLE runs ADD COLUMN {column} {ddl}")
        # decisions.disposition (§17, 2026-07-20): the live /data volume on
        # Fly predates the column; NULL on old rows reads as "no explicit
        # verdict", which the service seeds to business.
        decision_cols = {
            row["name"]
            for row in self.conn.execute("PRAGMA table_info(decisions)").fetchall()
        }
        if "disposition" not in decision_cols:
            self.conn.execute("ALTER TABLE decisions ADD COLUMN disposition TEXT")

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
        intake_id: str | None = None,
    ) -> None:
        self.conn.execute(
            "INSERT INTO runs (run_id, created_at, label, operator, summary, "
            "snapshot, config, work_dir, llm_enabled, has_coa, intake_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                intake_id,
            ),
        )
        self.conn.commit()

    def list_runs(self, published_only: bool = False) -> list[RunRow]:
        query = "SELECT * FROM runs"
        if published_only:
            query += " WHERE published = 1"
        query += " ORDER BY created_at DESC"
        rows = self.conn.execute(query).fetchall()
        return [self._row_to_run(r) for r in rows]

    def set_run_published(
        self, run_id: str, published: bool, published_at: str | None
    ) -> None:
        self.conn.execute(
            "UPDATE runs SET published = ?, published_at = ? WHERE run_id = ?",
            (int(published), published_at, run_id),
        )
        self.conn.commit()

    def get_run(self, run_id: str) -> RunRow | None:
        row = self.conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        return self._row_to_run(row) if row else None

    def set_run_label(self, run_id: str, label: str) -> bool:
        """Rename a run. Returns True when a row was updated (F9)."""
        cur = self.conn.execute(
            "UPDATE runs SET label = ? WHERE run_id = ?", (label, run_id)
        )
        self.conn.commit()
        return cur.rowcount > 0

    def update_run_snapshot(self, run_id: str, snapshot: dict) -> bool:
        """Persist a revised snapshot (manual receipt attach, 2026-07-24).
        Returns True when a row was updated."""
        cur = self.conn.execute(
            "UPDATE runs SET snapshot = ? WHERE run_id = ?",
            (json.dumps(snapshot), run_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def update_run_summary(self, run_id: str, summary: dict) -> bool:
        """Persist a revised run summary (batch lifecycle: incremental
        receipt adds and statement attach change the headline counts the
        list screens read). Returns True when a row was updated."""
        cur = self.conn.execute(
            "UPDATE runs SET summary = ? WHERE run_id = ?",
            (json.dumps(summary), run_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def update_run_config(self, run_id: str, config: dict) -> bool:
        """Persist a revised run config (statement attach adds the
        statement block + master data to an expense batch's config).
        Returns True when a row was updated."""
        cur = self.conn.execute(
            "UPDATE runs SET config = ? WHERE run_id = ?",
            (json.dumps(config), run_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def delete_run(self, run_id: str) -> bool:
        """Drop a run and its per-run edit rows. Returns True when the run
        existed. The on-disk work_dir is removed by the caller (the store
        owns the db, not the volume); dropping the edit rows here keeps the
        db from carrying orphaned decisions/overrides for a gone run (F9)."""
        cur = self.conn.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
        self.conn.execute("DELETE FROM decisions WHERE run_id = ?", (run_id,))
        self.conn.execute(
            "DELETE FROM category_overrides WHERE run_id = ?", (run_id,)
        )
        self.conn.execute(
            "DELETE FROM duplicate_resolutions WHERE run_id = ?", (run_id,)
        )
        self.conn.execute(
            "DELETE FROM expense_field_overrides WHERE run_id = ?", (run_id,)
        )
        self.conn.execute(
            "DELETE FROM expense_edits WHERE run_id = ?", (run_id,)
        )
        self.conn.commit()
        return cur.rowcount > 0

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
            published=bool(row["published"]),
            published_at=row["published_at"],
            intake_id=row["intake_id"],
        )

    # -- intakes (testing mode) --------------------------------------------

    def create_intake(
        self,
        *,
        intake_id: str,
        created_at: str,
        label: str,
        uploaded_by: str | None,
        statement_name: str,
        receipts_name: str | None,
        card_key: str | None,
        work_dir: str,
        detect_note: str | None,
    ) -> None:
        self.conn.execute(
            "INSERT INTO intakes (intake_id, created_at, label, uploaded_by, "
            "statement_name, receipts_name, card_key, work_dir, status, "
            "detect_note, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                intake_id,
                created_at,
                label,
                uploaded_by,
                statement_name,
                receipts_name,
                card_key,
                work_dir,
                INTAKE_RECEIVED,
                detect_note,
                created_at,
            ),
        )
        self.conn.commit()

    def list_intakes(self) -> list[IntakeRow]:
        rows = self.conn.execute(
            "SELECT * FROM intakes ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_intake(r) for r in rows]

    def get_intake(self, intake_id: str) -> IntakeRow | None:
        row = self.conn.execute(
            "SELECT * FROM intakes WHERE intake_id = ?", (intake_id,)
        ).fetchone()
        return self._row_to_intake(row) if row else None

    def update_intake_files(
        self,
        intake_id: str,
        *,
        statement_name: str | None = None,
        receipts_name: str | None = None,
        detect_note: str | None = None,
        updated_at: str,
    ) -> None:
        """Partial update after a file replace (2026-07-16 user feedback:
        "tem que ter opcao para tirar o arquivo que foi colocado errado").
        Only the columns passed as non-None change; the status is
        untouched (the endpoint restricts replaces to `received`)."""
        sets, params = ["updated_at = ?"], [updated_at]
        if statement_name is not None:
            sets.append("statement_name = ?")
            params.append(statement_name)
        if receipts_name is not None:
            sets.append("receipts_name = ?")
            params.append(receipts_name)
        if detect_note is not None:
            sets.append("detect_note = ?")
            params.append(detect_note)
        params.append(intake_id)
        self.conn.execute(
            f"UPDATE intakes SET {', '.join(sets)} WHERE intake_id = ?", params
        )
        self.conn.commit()

    def set_intake_status(
        self,
        intake_id: str,
        status: str,
        *,
        run_id: str | None = None,
        updated_at: str,
    ) -> None:
        if status not in VALID_INTAKE_STATUSES:
            raise ValueError(
                f"invalid intake status {status!r}; expected {VALID_INTAKE_STATUSES}"
            )
        self.conn.execute(
            "UPDATE intakes SET status = ?, run_id = ?, updated_at = ? "
            "WHERE intake_id = ?",
            (status, run_id, updated_at, intake_id),
        )
        self.conn.commit()

    @staticmethod
    def _row_to_intake(row: sqlite3.Row) -> IntakeRow:
        return IntakeRow(
            intake_id=row["intake_id"],
            created_at=row["created_at"],
            label=row["label"],
            uploaded_by=row["uploaded_by"],
            statement_name=row["statement_name"],
            receipts_name=row["receipts_name"],
            card_key=row["card_key"],
            work_dir=row["work_dir"],
            status=row["status"],
            run_id=row["run_id"],
            detect_note=row["detect_note"],
            updated_at=row["updated_at"],
        )

    # -- jobs (durable background-run state) --------------------------------

    def create_job(
        self, job_id: str, intake_id: str | None, created_at: str
    ) -> None:
        self.conn.execute(
            "INSERT INTO jobs (job_id, intake_id, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (job_id, intake_id, JOB_RUNNING, created_at, created_at),
        )
        self.conn.commit()

    def set_job_status(
        self,
        job_id: str,
        status: str,
        *,
        run_id: str | None = None,
        error: str | None = None,
        stage: str | None = None,
        updated_at: str,
    ) -> None:
        self.conn.execute(
            # COALESCE keeps the last recorded pipeline stage when the final
            # status write passes no stage (done/error must not blank it).
            "UPDATE jobs SET status = ?, run_id = ?, error = ?, "
            "stage = COALESCE(?, stage), updated_at = ? WHERE job_id = ?",
            (status, run_id, error, stage, updated_at, job_id),
        )
        self.conn.commit()

    def list_active_jobs(self) -> list[dict]:
        """Jobs still `running`: the in-flight pipeline work the dashboard
        should show as processing (F3). A run row only exists once its
        pipeline finished, so without this a mid-flight upload is invisible
        between kickoff and completion."""
        rows = self.conn.execute(
            "SELECT job_id, intake_id, stage, created_at FROM jobs "
            "WHERE status = ? ORDER BY created_at",
            (JOB_RUNNING,),
        ).fetchall()
        return [
            {
                "job_id": r["job_id"],
                "intake_id": r["intake_id"],
                "stage": r["stage"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def set_job_stage(self, job_id: str, stage: str, updated_at: str) -> None:
        self.conn.execute(
            "UPDATE jobs SET stage = ?, updated_at = ? WHERE job_id = ?",
            (stage, updated_at, job_id),
        )
        self.conn.commit()

    def get_job(self, job_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT status, run_id, error, stage FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "status": row["status"],
            "run_id": row["run_id"],
            "error": row["error"],
            "stage": row["stage"],
        }

    def sweep_stale_jobs(self, now_iso: str) -> list[str | None]:
        """Mark every still-`running` job as interrupted (a server restart
        killed its thread) and return the affected intake ids so the caller
        can reset them to `received`. Keeps the queue honest after a Fly
        scale-to-zero stop."""
        rows = self.conn.execute(
            "SELECT job_id, intake_id FROM jobs WHERE status = ?", (JOB_RUNNING,)
        ).fetchall()
        for row in rows:
            self.conn.execute(
                "UPDATE jobs SET status = ?, error = ?, updated_at = ? "
                "WHERE job_id = ?",
                (
                    JOB_ERROR,
                    "interrupted by a server restart; run it again",
                    now_iso,
                    row["job_id"],
                ),
            )
        self.conn.commit()
        return [row["intake_id"] for row in rows]

    # -- decisions --------------------------------------------------------

    def get_decisions(self, run_id: str) -> dict[str, Decision]:
        rows = self.conn.execute(
            "SELECT transaction_id, status, chosen_document_id, updated_at, "
            "disposition FROM decisions WHERE run_id = ?",
            (run_id,),
        ).fetchall()
        return {
            r["transaction_id"]: Decision(
                status=r["status"],
                chosen_document_id=r["chosen_document_id"],
                updated_at=r["updated_at"],
                disposition=r["disposition"],
            )
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
        # The ON CONFLICT SET deliberately excludes `disposition` (§17):
        # re-triaging a row never clears its disposition verdict.
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

    def set_disposition(
        self,
        run_id: str,
        transaction_id: str,
        disposition: str,
        updated_at: str,
    ) -> None:
        """Upsert ONLY the §17 disposition for one transaction.

        Status-preserving: a fresh row seeds `status=pending`; an existing
        row keeps its `status` and `chosen_document_id` untouched (the
        ON CONFLICT SET lists only `disposition` + `updated_at`). The
        mirror-image guarantee lives in `set_decision`, whose upsert never
        lists `disposition` — the two verdict layers stay orthogonal.
        """
        if disposition not in VALID_DISPOSITIONS:
            raise ValueError(
                f"invalid disposition {disposition!r}; expected {VALID_DISPOSITIONS}"
            )
        self.conn.execute(
            "INSERT INTO decisions (run_id, transaction_id, status, "
            "chosen_document_id, updated_at, disposition) "
            "VALUES (?, ?, ?, NULL, ?, ?) "
            "ON CONFLICT(run_id, transaction_id) DO UPDATE SET "
            "disposition = excluded.disposition, "
            "updated_at = excluded.updated_at",
            (run_id, transaction_id, STATUS_PENDING, updated_at, disposition),
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

    # -- expense field overrides + edits (receipt-first, Phase 4) ----------

    def get_expense_field_overrides(self, run_id: str) -> dict[str, dict[str, str]]:
        """document_id -> {field: value} for a run's header-level expense
        edits. Absent documents / fields keep their extracted values."""
        rows = self.conn.execute(
            "SELECT document_id, field, value FROM expense_field_overrides "
            "WHERE run_id = ?",
            (run_id,),
        ).fetchall()
        out: dict[str, dict[str, str]] = {}
        for r in rows:
            if r["value"] is None:
                continue
            out.setdefault(r["document_id"], {})[r["field"]] = r["value"]
        return out

    def set_expense_field_override(
        self,
        run_id: str,
        document_id: str,
        field: str,
        value: str | None,
        updated_at: str,
    ) -> None:
        """Upsert one header-field edit. `value=None` clears the override
        (the expense reverts to its extracted value)."""
        if value is None:
            self.conn.execute(
                "DELETE FROM expense_field_overrides "
                "WHERE run_id = ? AND document_id = ? AND field = ?",
                (run_id, document_id, field),
            )
        else:
            self.conn.execute(
                "INSERT INTO expense_field_overrides (run_id, document_id, "
                "field, value, updated_at) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(run_id, document_id, field) DO UPDATE SET "
                "value = excluded.value, updated_at = excluded.updated_at",
                (run_id, document_id, field, value, updated_at),
            )
        self.conn.commit()

    def get_expense_edits(self, run_id: str) -> list[dict]:
        """The run's whole-expense add/delete edits, oldest first (stable
        manual-expense ordering in the grid)."""
        rows = self.conn.execute(
            "SELECT document_id, op, payload, updated_at FROM expense_edits "
            "WHERE run_id = ? ORDER BY updated_at, document_id",
            (run_id,),
        ).fetchall()
        return [
            {
                "document_id": r["document_id"],
                "op": r["op"],
                "payload": json.loads(r["payload"]) if r["payload"] else {},
            }
            for r in rows
        ]

    def set_expense_edit(
        self,
        run_id: str,
        document_id: str,
        op: str,
        payload: dict | None,
        updated_at: str,
    ) -> None:
        """Upsert one whole-expense edit. One row per document: a delete on
        a manually-added document overwrites its add row, so the manual
        expense simply disappears."""
        if op not in VALID_EXPENSE_EDIT_OPS:
            raise ValueError(
                f"invalid expense edit op {op!r}; expected {VALID_EXPENSE_EDIT_OPS}"
            )
        self.conn.execute(
            "INSERT INTO expense_edits (run_id, document_id, op, payload, "
            "updated_at) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(run_id, document_id) DO UPDATE SET "
            "op = excluded.op, payload = excluded.payload, "
            "updated_at = excluded.updated_at",
            (run_id, document_id, op, json.dumps(payload or {}), updated_at),
        )
        self.conn.commit()

    # -- settings (§16 export policy; one row, id=1) -----------------------

    def get_settings(self) -> dict:
        """The current settings, with defaults applied. No row yet => the
        defaults (`export_approved_only=False`), so a fresh install behaves
        exactly as before the policy existed."""
        row = self.conn.execute(
            "SELECT data FROM settings WHERE id = 1"
        ).fetchone()
        data = json.loads(row["data"]) if row else {}
        return {**SETTINGS_DEFAULTS, **data}

    # -- duplicate resolutions (§18; advisory, per run + group) -----------

    def get_duplicate_resolutions(self, run_id: str) -> dict[str, str]:
        """group_id -> resolution for a run. Absent groups are unresolved."""
        rows = self.conn.execute(
            "SELECT group_id, resolution FROM duplicate_resolutions "
            "WHERE run_id = ?",
            (run_id,),
        ).fetchall()
        return {r["group_id"]: r["resolution"] for r in rows}

    def set_duplicate_resolution(
        self, run_id: str, group_id: str, resolution: str, updated_at: str
    ) -> None:
        if resolution not in VALID_DUP_RESOLUTIONS:
            raise ValueError(
                f"invalid resolution {resolution!r}; expected {VALID_DUP_RESOLUTIONS}"
            )
        self.conn.execute(
            "INSERT INTO duplicate_resolutions (run_id, group_id, resolution, "
            "updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(run_id, group_id) DO UPDATE SET "
            "resolution = excluded.resolution, updated_at = excluded.updated_at",
            (run_id, group_id, resolution, updated_at),
        )
        self.conn.commit()

    def set_settings(self, patch: dict, updated_at: str) -> dict:
        """Merge `patch` into the stored settings (shallow) and return the
        effective settings. Only the keys in `patch` change; unknown keys
        are persisted as-is so a later phase can extend the policy without a
        migration."""
        current = {}
        row = self.conn.execute(
            "SELECT data FROM settings WHERE id = 1"
        ).fetchone()
        if row:
            current = json.loads(row["data"])
        merged = {**current, **patch}
        self.conn.execute(
            "INSERT INTO settings (id, data, updated_at) VALUES (1, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET "
            "data = excluded.data, updated_at = excluded.updated_at",
            (json.dumps(merged), updated_at),
        )
        self.conn.commit()
        return {**SETTINGS_DEFAULTS, **merged}

    # -- login throttle (see web/ratelimit.py for the policy) --------------
    # Failed /api/login attempts only. Timestamps are epoch seconds, so the
    # policy never has to parse a date. Successful logins clear the caller's
    # rows; `prune_login_failures` keeps the table bounded to one window.

    def record_login_failure(self, ip: str, ts: float) -> None:
        self.conn.execute(
            "INSERT INTO login_failures (ip, ts) VALUES (?, ?)", (ip, float(ts))
        )
        self.conn.commit()

    def login_failure_stats(
        self, since: float, ip: str | None = None
    ) -> tuple[int, float]:
        """`(count, latest_ts)` for failures at or after `since` — for one
        caller when `ip` is given, else across every caller. `latest_ts` is
        0.0 when there are none."""
        if ip is None:
            row = self.conn.execute(
                "SELECT COUNT(*) AS n, COALESCE(MAX(ts), 0.0) AS last "
                "FROM login_failures WHERE ts >= ?",
                (float(since),),
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT COUNT(*) AS n, COALESCE(MAX(ts), 0.0) AS last "
                "FROM login_failures WHERE ip = ? AND ts >= ?",
                (ip, float(since)),
            ).fetchone()
        return int(row["n"]), float(row["last"])

    def clear_login_failures(self, ip: str) -> None:
        self.conn.execute("DELETE FROM login_failures WHERE ip = ?", (ip,))
        self.conn.commit()

    def prune_login_failures(self, before: float) -> None:
        self.conn.execute("DELETE FROM login_failures WHERE ts < ?", (float(before),))
        self.conn.commit()
