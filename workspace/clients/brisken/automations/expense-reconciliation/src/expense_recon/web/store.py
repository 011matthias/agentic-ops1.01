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

# Note item T3: which statement upload printed a charge. Its own module,
# not `service.py`, because the service imports this file.
from ..learning.store import (
    CATEGORY_SOURCE_HUMAN,
    CATEGORY_SOURCES,
)
from .decision_history import ROW_CHARGE, ROW_RECEIPT
from .statement_origin import origins_from_snapshot

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
#   fx_reference_rates  RETIRED 2026-09-23 (rates come from the daily
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
#     default_paid_through?}}. Definable in the UI; wins
#     over the /data provisioning file's entity mapping when present
#     (coa_provision.coa_validation_from_settings). Distinct from
#     `card_entities`, which stays the card -> entity MAP.
#   entity_order (item 92, owner ask 2026-09-17) — the operator's own ORDER
#     for the entity list: ["Corporate Services", "Cloud Services"]. A list,
#     not a field on each registry entry, because most entities never reach
#     that registry: they arrive from /data provisioning and the card map,
#     which the operator cannot edit. Names it does not know are appended
#     alphabetically, names it knows that no longer exist are ignored, so
#     the picker can neither hide an entity nor break on a stale name.
#     Read through `service.available_entities`.
#   merchants (2026-07-29, receipt-first) — the canonical MERCHANT REGISTRY:
#     {"Uber": {aliases: [...], category?, zoho_account?}}. Definable in the
#     UI (like `entities`); the highest-priority deterministic source for a
#     receipt's canonical vendor + default category in generate_expenses
#     (expense_recon.merchant_registry). Empty => no canonicalization.
#   cards (2026-08-21, owner directive: Zoho independence) — the CARD
#     REGISTRY: {"corp-2838": {label, digits: ["2838","1672"], aliases,
#     entity, zoho_account?, currency, active}}. The tool's own card
#     identity; `zoho_account` is optional (export-only attribute). Read
#     through `cards.effective_cards`, which folds the legacy
#     `card_entities`/`card_accounts` maps + the /data presets file in at
#     read time — the legacy keys stay authoritative until an explicit
#     card entry exists (no write migration).
SETTINGS_DEFAULTS: dict = {
    "export_approved_only": False,
    "card_entities": {},
    "card_accounts": {},
    "entities": {},
    "entity_order": [],
    "merchants": {},
    "cards": {},
    # Cost centers (item 47): owner-authored only. The empty default is
    # load-bearing, not incidental — an empty registry resolves nothing AND
    # flags nothing, so a tenant that has never defined one sees no
    # cost-center review state at all. See cost_centers.py.
    "cost_centers": {},
    # Receipt chasing (item 107): {"enabled": false, "holders": {person:
    # address}}. OFF by default and off on the live volume until the owner
    # approves the chase mail; with it off the month still builds the
    # missing-receipts list and still composes the mail for preview, and
    # nothing sends either way (receipt_chase.py sends nothing at all).
    "receipt_requests": {"enabled": False, "holders": {}},
}

# Settings keys holding a {str: str} map. Values are kept as STRINGS: a
# Decimal FX rate keeps full precision as text, a json float does not.
SETTINGS_MAP_KEYS = ("card_entities", "card_accounts")

# Every top-level key `PUT /api/settings` actually writes. The settings
# screen saves ONE group per request (the tabbed page sends {"cards": ...}
# and nothing else), so a key the handler does not recognise used to be
# dropped in silence and answered 200: the tab said "saved" and nothing had
# changed. The PUT refuses an unknown key instead, and names it.
SETTINGS_WRITABLE_KEYS = (
    "export_approved_only",
    *SETTINGS_MAP_KEYS,
    "entities",
    "entity_order",
    "merchants",
    "cards",
    "cost_centers",
    "intake",
    "receipt_requests",
)

# Keys `GET /api/settings` DERIVES and the PUT never stores. A client that
# reads the settings payload, edits one group and sends the whole object
# back carries these along; they are accepted and ignored rather than
# refused, which is what keeps that round-trip legal. `applied` / `ignored`
# are the PUT response's own fields, listed here for the same reason.
SETTINGS_DERIVED_KEYS = (
    "categories",
    # The curated GL leaves, per entity, and the taxonomy revision they came
    # from. Derived beside `categories` rather than replacing it, so a
    # client that reads the payload and sends the whole object back does not
    # trip `unknown_settings_keys` on them (2026-09-23).
    "gl_accounts",
    "gl_revision",
    "entity_options",
    "cards_effective",
    "merchants_inert",
    "cost_center_options",
    "fx_daily_rates",
    "applied",
    "ignored",
)

# Fields an `entities` entry no longer carries. `account_picks` was a
# per-company shortlist of the accounts an expense row offered; the owner
# removed it on 2026-09-17 (note #61), so every row offers the company's
# full chart. The PUT drops it silently (the published SPA sends it until
# its prompt lands) and the settings payload never serves a value stored
# before the removal.
RETIRED_ENTITY_KEYS = frozenset({"account_picks"})

# Whole settings keys the app no longer stores. `GET` never serves them,
# `PUT` drops them silently (a 400 would break the published SPA, which
# keeps sending the key until its removal prompt is applied), and
# `_migrate` deletes them from the stored row once.
#
# `fx_reference_rates` retired 2026-09-23, owner directive: "no more typing
# them in settings you can remove that function entirely, we will only rely
# on these daily rates API stuff". The live row held EUR:USD 1.162275 and
# BRL:USD 0.192448, which outranked every fetched rate for every month.
RETIRED_SETTINGS_KEYS = frozenset({"fx_reference_rates"})


def without_retired_settings_keys(settings: dict) -> dict:
    """`settings` with every retired top-level key removed. A shallow copy:
    the stored row is never touched (the migration does that once)."""
    if not any(k in settings for k in RETIRED_SETTINGS_KEYS):
        return settings
    return {k: v for k, v in settings.items() if k not in RETIRED_SETTINGS_KEYS}


def without_retired_entity_keys(settings: dict) -> dict:
    """`settings` with every `RETIRED_ENTITY_KEYS` field taken off each
    `entities` entry. A shallow copy: the stored row is never touched."""
    entities = settings.get("entities")
    if not isinstance(entities, dict):
        return settings
    return {
        **settings,
        "entities": {
            label: (
                {k: v for k, v in ent.items() if k not in RETIRED_ENTITY_KEYS}
                if isinstance(ent, dict)
                else ent
            )
            for label, ent in entities.items()
        },
    }


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
    # Item 100: the operator label of the session that published, and whether
    # it published a month the completeness gate refused. Cleared on unpublish.
    published_by: str | None = None
    published_override: bool = False


@dataclass
class TripRow:
    """One trip (item 38, owner directive 2026-09-06): named, date-ranged,
    with a VARIABLE roster of travelers. The entity is deliberately not a
    run: a trip has a name and a roster only a human knows, so it is
    created empty and its expense BATCH materializes when the first
    receipt joins (create-with-receipt, the item-39 ordering). The batch
    references the trip via ``config["trip_id"]``; the trip stores no
    batch id, so there is exactly one source of truth for the link."""

    trip_id: str
    created_at: str
    name: str
    start_date: str   # YYYY-MM-DD, inclusive
    end_date: str     # YYYY-MM-DD, inclusive
    travelers: list[str]
    updated_at: str | None = None
    # Item 47: the project or purpose this trip's spend belongs to.
    # A trip is the strongest AUTOMATIC cost-center signal, because a
    # human DECLARED it at creation rather than anything inferring it.
    cost_center: str = ""


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
    # Item 76: who wrote the current `status`. "tool" only for a
    # self-confirmation (`service.apply_self_confirmations`), with the rule
    # that fired in `rule`; "reviewer" for every route a person drives. None
    # on rows written before the column existed, every one of them by a
    # person or by a disposition seed that left the status pending.
    decided_by: str | None = None
    rule: str | None = None
    # Item 107, both reviewer-set and both absent on every row nobody has
    # chased. `receipt_requested_at` (with `receipt_requested_to`) records
    # that the holder was ASKED, which closes nothing; `no_receipt_expected`
    # holds the REASON no receipt will ever exist, which closes the charge.
    receipt_requested_at: str | None = None
    receipt_requested_to: str | None = None
    no_receipt_expected: str | None = None


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
                receipt_requested_at TEXT,
                receipt_requested_to TEXT,
                no_receipt_expected  TEXT,
                PRIMARY KEY (run_id, transaction_id)
            );
            CREATE TABLE IF NOT EXISTS category_overrides (
                run_id       TEXT NOT NULL,
                document_id  TEXT NOT NULL,
                line_index   INTEGER NOT NULL,
                category     TEXT,
                zoho_account TEXT,
                updated_at   TEXT,
                category_source TEXT,
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
                result     TEXT,
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
            CREATE TABLE IF NOT EXISTS receipt_claims (
                receipt_run_id    TEXT NOT NULL,
                document_id       TEXT NOT NULL,
                claimed_by_run_id TEXT NOT NULL,
                transaction_id    TEXT NOT NULL,
                claimed_at        TEXT NOT NULL,
                PRIMARY KEY (receipt_run_id, document_id)
            );
            CREATE INDEX IF NOT EXISTS idx_receipt_claims_by_run
                ON receipt_claims (claimed_by_run_id);
            CREATE TABLE IF NOT EXISTS login_failures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL,
                ts REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS trips (
                trip_id    TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                name       TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date   TEXT NOT NULL,
                travelers  TEXT NOT NULL,
                updated_at TEXT,
                cost_center TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS client_errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                received_at TEXT NOT NULL,
                received_ts REAL NOT NULL,
                operator TEXT NOT NULL,
                caller TEXT NOT NULL,
                kind TEXT NOT NULL,
                url TEXT NOT NULL,
                method TEXT NOT NULL,
                message TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                seconds_ago REAL,
                duration_ms INTEGER,
                online INTEGER,
                detail TEXT NOT NULL,
                machine TEXT NOT NULL,
                region TEXT NOT NULL,
                server_commit TEXT NOT NULL DEFAULT '',
                server_image TEXT NOT NULL DEFAULT '',
                process_started_at TEXT NOT NULL,
                uptime_s REAL NOT NULL,
                process_predates_failure INTEGER
            );
            CREATE TABLE IF NOT EXISTS memory_commits (
                run_id       TEXT PRIMARY KEY,
                digest       TEXT NOT NULL,
                committed_at TEXT NOT NULL,
                trigger      TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS fx_daily_rates (
                day        TEXT NOT NULL,
                ccy        TEXT NOT NULL,
                per_eur    TEXT NOT NULL,
                source     TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                PRIMARY KEY (day, ccy)
            );
            CREATE TABLE IF NOT EXISTS fx_daily_rates_meta (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            -- Item 163: one row per memory SAVE, carrying the pre-image of
            -- every learning row it touched and of the merchant registry,
            -- so a save can be read back ("where did this go") and put back
            -- ("this should be reversible"). Its own table beside
            -- memory_commits, which holds only the last digest per run and
            -- is overwritten by the next save.
            CREATE TABLE IF NOT EXISTS memory_journal (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id           TEXT NOT NULL,
                label            TEXT NOT NULL DEFAULT '',
                committed_at     TEXT NOT NULL,
                trigger          TEXT NOT NULL,
                rows_json        TEXT NOT NULL,
                merchants_before TEXT NOT NULL,
                merchants_after  TEXT NOT NULL,
                learned_json     TEXT NOT NULL,
                reverted_at      TEXT
            );
            CREATE TABLE IF NOT EXISTS decision_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                row_key TEXT NOT NULL,
                row_kind TEXT NOT NULL,
                field TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                who TEXT NOT NULL,
                at TEXT NOT NULL,
                trigger TEXT NOT NULL,
                detail TEXT,
                undone_at TEXT,
                undone_by TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_decision_history_run
                ON decision_history (run_id, id);
            CREATE INDEX IF NOT EXISTS idx_client_errors_ts
                ON client_errors (received_ts);
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
        operator publishes them explicitly.

        Also drops any `RETIRED_SETTINGS_KEYS` still in the stored settings
        row, so retiring a settings function actually removes its data
        instead of merely hiding it behind the read path."""
        self._drop_retired_settings()
        existing = {
            row["name"]
            for row in self.conn.execute("PRAGMA table_info(runs)").fetchall()
        }
        adds = (
            ("published", "INTEGER NOT NULL DEFAULT 0"),
            ("published_at", "TEXT"),
            ("intake_id", "TEXT"),
            # Item 100 (2026-09-17): who published, and whether over the gate.
            ("published_by", "TEXT"),
            ("published_override", "INTEGER NOT NULL DEFAULT 0"),
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
        # decisions.decided_by + decided_rule (item 76, 2026-09-16): NULL on
        # the live volume's existing rows, read as "a person" for a verdict
        # and as "no verdict" for a pending row (see Decision.decided_by).
        if "decided_by" not in decision_cols:
            self.conn.execute("ALTER TABLE decisions ADD COLUMN decided_by TEXT")
        if "decided_rule" not in decision_cols:
            self.conn.execute("ALTER TABLE decisions ADD COLUMN decided_rule TEXT")
        # decisions.receipt_requested_* + no_receipt_expected (item 107,
        # 2026-09-17): the live volume predates all three. NULL everywhere
        # reads as "nobody has chased this charge", which is what every
        # charge on every existing month was.
        for column in (
            "receipt_requested_at", "receipt_requested_to", "no_receipt_expected",
        ):
            if column not in decision_cols:
                self.conn.execute(
                    f"ALTER TABLE decisions ADD COLUMN {column} TEXT"
                )
        # jobs.result (receipts drop, 2026-09-08): the live volume predates
        # the column; NULL on old rows reads as "this job kind carries no
        # payload", which is true of every job kind before the drop.
        job_cols = {
            row["name"]
            for row in self.conn.execute("PRAGMA table_info(jobs)").fetchall()
        }
        if "result" not in job_cols:
            self.conn.execute("ALTER TABLE jobs ADD COLUMN result TEXT")
        # trips.cost_center (item 47, 2026-09-10): the live volume
        # predates the column; "" on old rows reads as "unassigned",
        # which is what every trip created before cost centers was.
        trip_cols = {
            row["name"]
            for row in self.conn.execute("PRAGMA table_info(trips)").fetchall()
        }
        if "cost_center" not in trip_cols:
            self.conn.execute(
                "ALTER TABLE trips ADD COLUMN cost_center TEXT NOT NULL DEFAULT ''"
            )
        # decisions / decision_history / receipt_claims .statement_id (note
        # item T3, 2026-09-18): which statement upload printed the charge
        # this record is about. NULL on every row written before the column
        # and on every row whose charge the month cannot place (a month
        # whose uploads predate `statement_origins` and whose statement is
        # a PDF, a history line about a receipt that settles nothing, a
        # duplicate ruling), which reads as "not recorded" and never as
        # "no statement". `decision_history` is added here as well as in
        # the CREATE block: the live volume already holds the table from
        # item 104's deploy, so IF NOT EXISTS is a no-op there.
        for table, cols in (
            ("decisions", decision_cols),
            ("decision_history", None),
            ("receipt_claims", None),
        ):
            names = cols if cols is not None else {
                row["name"]
                for row in self.conn.execute(
                    f"PRAGMA table_info({table})"
                ).fetchall()
            }
            if "statement_id" not in names:
                self.conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN statement_id TEXT"
                )

        # client_errors.server_commit + server_image (item 120, 2026-09-21):
        # which BUILD served the failure, stamped at the moment the report
        # arrives. Rows written before the column read "" for the same
        # reason /healthz reports "" on an unstamped build: the build that
        # served them is not recoverable from the row, and a back-fill
        # could only write the build doing the back-filling. Absent
        # identity is honest; wrong identity sends the next investigation
        # to the wrong release. Named `server_*` because `commit` is a
        # SQLite keyword and cannot be a bare column name.
        error_cols = {
            row["name"]
            for row in self.conn.execute(
                "PRAGMA table_info(client_errors)"
            ).fetchall()
        }
        for column in ("server_commit", "server_image"):
            if column not in error_cols:
                self.conn.execute(
                    f"ALTER TABLE client_errors ADD COLUMN {column} "
                    "TEXT NOT NULL DEFAULT ''"
                )

        # category_overrides.category_source (the learning-leak marker,
        # 2026-09-24): whether a PERSON stated this line's category, or the
        # row merely carries the model's own guess because the edit was
        # about something else. Two edits store a category nobody stated -
        # the note-#62 Confirm (keep the guess as it is) and an
        # account-only PUT - and sign-off then taught both as corrections.
        # NULL reads as CATEGORY_SOURCE_HUMAN: every row written before this
        # column existed is overwhelmingly an explicit pick, and defaulting
        # the other way would stop every already-reviewed month teaching
        # anything. The account half needs no marker: `category_edit_account`
        # stores an explicit pick or an earlier override's account, never
        # the model's.
        override_cols = {
            row["name"]
            for row in self.conn.execute(
                "PRAGMA table_info(category_overrides)"
            ).fetchall()
        }
        if "category_source" not in override_cols:
            self.conn.execute(
                "ALTER TABLE category_overrides ADD COLUMN category_source TEXT"
            )

    # -- where a charge was printed (note item T3) --------------------------
    #
    # A stored verdict names a `transaction_id`, which is content-derived:
    # a re-read of a corrected file gives the same printed line a new id
    # and `rekey_decisions` moves the verdict onto it. The statement the
    # line was printed on is the fact that does NOT move, so stamping it
    # beside the id is what lets a decision, a history line or a claim say
    # which document it was about months later.
    #
    # Resolved here rather than passed in by each of the seventeen writers:
    # the value is a pure function of (run_id, transaction_id), so a
    # caller could only get it wrong. The snapshot is parsed once per run
    # per process and dropped whenever this store rewrites it, which is
    # the only way it changes.

    def _charge_origins(self, run_id: str) -> dict[str, dict]:
        cache = getattr(self, "_origin_cache", None)
        if cache is None:
            cache = self._origin_cache = {}
        if run_id not in cache:
            run = self.get_run(run_id)
            cache[run_id] = origins_from_snapshot(run.snapshot if run else None)
        return cache[run_id]

    def _forget_charge_origins(self, run_id: str) -> None:
        """Drop the memo for one run. Called wherever this store writes a
        snapshot, which is the only event that can change the answer (an
        attach, a re-read, a manual receipt attach)."""
        cache = getattr(self, "_origin_cache", None)
        if cache is not None:
            cache.pop(run_id, None)

    def statement_id_for_charge(
        self, run_id: str, transaction_id: str
    ) -> str | None:
        """The upload that printed this charge, or None when the month
        does not record one (see the column comment in `_migrate`)."""
        origin = self._charge_origins(run_id).get(str(transaction_id))
        return (origin or {}).get("statement_id") or None

    def _stamp_decision_statement(
        self, run_id: str, transaction_id: str
    ) -> None:
        """Write the charge's statement id onto its decision row, if the
        row does not already carry one. Runs inside the writer's own
        transaction, before its commit, so a verdict and the statement it
        was about land together or not at all. Cheap and idempotent: the
        id never changes for a given charge, so the guard makes a bulk
        confirm's second pass over the same row a no-op."""
        statement_id = self.statement_id_for_charge(run_id, transaction_id)
        if not statement_id:
            return
        self.conn.execute(
            "UPDATE decisions SET statement_id = ? WHERE run_id = ? "
            "AND transaction_id = ? AND (statement_id IS NULL "
            "OR statement_id = '')",
            (statement_id, run_id, transaction_id),
        )

    # -- decision history (item 104) ---------------------------------------
    #
    # Append-only. Nothing in this class updates a history row's values or
    # deletes one; the single UPDATE below stamps `undone_at` / `undone_by`
    # and touches no other column, so a line that has been put back still
    # says what it originally did. The table is created by the CREATE block
    # above rather than by `_migrate`, which is what every table added since
    # the live volume existed does: `IF NOT EXISTS` runs on every open, so
    # the running database grows the table on the first request after the
    # deploy and starts empty, which is the truth (nothing before the deploy
    # was recorded).

    def append_history(self, entries: list[dict]) -> list[int]:
        """Append history lines and return their ids, in order.

        Takes a list because the bulk routes write one line per row moved
        and a single commit for a hundred rows is the difference between a
        confirm-all that feels instant and one that does not.
        """
        ids: list[int] = []
        for entry in entries:
            cur = self.conn.execute(
                "INSERT INTO decision_history (run_id, row_key, row_kind, "
                "field, old_value, new_value, who, at, trigger, detail, "
                "statement_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    entry["run_id"], entry["row_key"], entry["row_kind"],
                    entry["field"], entry["old_value"], entry["new_value"],
                    entry["who"], entry["at"], entry["trigger"],
                    entry.get("detail"),
                    # Note item T3: stamped at INSERT because the table is
                    # append-only -- a line filled in afterwards would be a
                    # rewrite, which is the one thing this ledger forbids.
                    # A charge line resolves through its own row_key; a
                    # receipt line through the charge that currently holds
                    # it, which is what the line was about.
                    self._history_statement_id(entry),
                ),
            )
            ids.append(int(cur.lastrowid))
        if entries:
            self.conn.commit()
        return ids

    def _history_statement_id(self, entry: dict) -> str | None:
        """The statement one history line is about.

        `charge`: the line's own `row_key` IS a transaction id.
        `receipt`: the charge this run currently books the document
        against, which is the line the category change lands on; None
        when the receipt settles nothing here.
        `group` (a duplicate ruling): about no single charge, so None.
        """
        run_id = entry["run_id"]
        kind = entry.get("row_kind")
        if kind == ROW_CHARGE:
            return self.statement_id_for_charge(run_id, entry["row_key"])
        if kind == ROW_RECEIPT:
            row = self.conn.execute(
                "SELECT transaction_id FROM decisions WHERE run_id = ? "
                "AND chosen_document_id = ? LIMIT 1",
                (run_id, entry["row_key"]),
            ).fetchone()
            if row is None:
                return None
            return self.statement_id_for_charge(run_id, row["transaction_id"])
        return None

    def list_history(
        self,
        run_id: str,
        *,
        limit: int = 200,
        before_id: int | None = None,
        row_key: str | None = None,
    ) -> list[dict]:
        """Newest first, because the question is always "what changed since
        I last looked". `before_id` pages further back; `row_key` narrows to
        one row's own story."""
        sql = "SELECT * FROM decision_history WHERE run_id = ?"
        args: list = [run_id]
        if before_id is not None:
            sql += " AND id < ?"
            args.append(int(before_id))
        if row_key:
            sql += " AND row_key = ?"
            args.append(str(row_key))
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(int(limit))
        return [dict(r) for r in self.conn.execute(sql, args).fetchall()]

    def count_history(self, run_id: str, *, row_key: str | None = None) -> int:
        """The count the caller is looking at. `row_key` narrows it to one
        row, because the per-row fold shows this number and the month's
        total beside two of that row's lines is simply wrong."""
        sql = "SELECT COUNT(*) AS n FROM decision_history WHERE run_id = ?"
        args: list = [run_id]
        if row_key:
            sql += " AND row_key = ?"
            args.append(str(row_key))
        row = self.conn.execute(sql, args).fetchone()
        return int(row["n"]) if row else 0

    def get_history_entry(self, entry_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM decision_history WHERE id = ?", (int(entry_id),)
        ).fetchone()
        return dict(row) if row else None

    def mark_history_undone(
        self, entry_id: int, *, undone_at: str, undone_by: str
    ) -> bool:
        """Stamp one line as put back.

        The WHERE carries `undone_at IS NULL`, so the STAMP is written once
        however many clicks race: the first sets it, the rest return False
        and leave the name and time of the real undo alone. The caller
        discards that False on purpose, because it applies the old value
        before stamping and writing the same old value twice is the same
        state.
        """
        cur = self.conn.execute(
            "UPDATE decision_history SET undone_at = ?, undone_by = ? "
            "WHERE id = ? AND undone_at IS NULL",
            (undone_at, undone_by, int(entry_id)),
        )
        self.conn.commit()
        return cur.rowcount > 0

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
        self,
        run_id: str,
        published: bool,
        published_at: str | None,
        *,
        published_by: str | None = None,
        override: bool = False,
    ) -> None:
        """Publish or unpublish. Unpublishing clears who and whether it was
        an override along with the time, so the row describes the CURRENT
        sign-off only."""
        self.conn.execute(
            "UPDATE runs SET published = ?, published_at = ?, published_by = ?, "
            "published_override = ? WHERE run_id = ?",
            (
                int(published),
                published_at,
                published_by if published else None,
                int(bool(published and override)),
                run_id,
            ),
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
        # Note item T3: a new snapshot is the only event that changes which
        # upload printed which charge, so the memo goes with it.
        self._forget_charge_origins(run_id)
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
        db from carrying orphaned decisions/overrides for a gone run (F9).
        Jobs that finished into this run go too: a /jobs poll on a deleted
        month must answer 404, not hand the SPA a run_id that no longer
        resolves."""
        cur = self.conn.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
        self.conn.execute("DELETE FROM decisions WHERE run_id = ?", (run_id,))
        # The month's ledger goes with the month (item 104). Append-only is
        # a rule about editing a line, not about outliving the run it
        # describes: rows left behind are unreachable through the API, which
        # is the orphan state the rest of this method exists to prevent.
        self.conn.execute(
            "DELETE FROM decision_history WHERE run_id = ?", (run_id,)
        )
        # R4 (item 38): both claim directions go with the run. Claims BY it
        # release every receipt its matches settled (a trip's receipts become
        # matchable again when the month that consumed them is deleted);
        # claims ON its receipts point at documents that no longer exist.
        self.conn.execute(
            "DELETE FROM receipt_claims "
            "WHERE receipt_run_id = ? OR claimed_by_run_id = ?",
            (run_id, run_id),
        )
        self.conn.execute(
            "DELETE FROM category_overrides WHERE run_id = ?", (run_id,)
        )
        self.conn.execute(
            "DELETE FROM duplicate_resolutions WHERE run_id = ?", (run_id,)
        )
        # Item 88: what was saved to memory for the run. The learned rows
        # themselves stay (deleting a month never unlearns; the Memory page
        # is the undo), only the record of the save goes.
        self.conn.execute("DELETE FROM memory_commits WHERE run_id = ?", (run_id,))
        self.conn.execute(
            "DELETE FROM expense_field_overrides WHERE run_id = ?", (run_id,)
        )
        self.conn.execute(
            "DELETE FROM expense_edits WHERE run_id = ?", (run_id,)
        )
        self.conn.execute("DELETE FROM jobs WHERE run_id = ?", (run_id,))
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
            published_by=row["published_by"],
            published_override=bool(row["published_override"]),
        )

    # -- trips (item 38) ---------------------------------------------------

    def create_trip(
        self,
        *,
        trip_id: str,
        created_at: str,
        name: str,
        start_date: str,
        end_date: str,
        travelers: list[str],
        cost_center: str = "",
    ) -> None:
        self.conn.execute(
            "INSERT INTO trips (trip_id, created_at, name, start_date, "
            "end_date, travelers, updated_at, cost_center) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (trip_id, created_at, name, start_date, end_date,
             json.dumps(travelers), created_at, cost_center),
        )
        self.conn.commit()

    def list_trips(self) -> list[TripRow]:
        rows = self.conn.execute(
            "SELECT * FROM trips ORDER BY start_date DESC, created_at DESC"
        ).fetchall()
        return [self._row_to_trip(r) for r in rows]

    def get_trip(self, trip_id: str) -> TripRow | None:
        row = self.conn.execute(
            "SELECT * FROM trips WHERE trip_id = ?", (trip_id,)
        ).fetchone()
        return self._row_to_trip(row) if row else None

    def update_trip(
        self,
        trip_id: str,
        *,
        name: str,
        start_date: str,
        end_date: str,
        travelers: list[str],
        updated_at: str,
        cost_center: str = "",
    ) -> bool:
        cur = self.conn.execute(
            "UPDATE trips SET name = ?, start_date = ?, end_date = ?, "
            "travelers = ?, updated_at = ?, cost_center = ? WHERE trip_id = ?",
            (name, start_date, end_date, json.dumps(travelers),
             updated_at, cost_center, trip_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def delete_trip(self, trip_id: str) -> bool:
        """Drop a trip entity. The caller refuses the delete while a batch
        still references it (the batch holds real expenses; the entity is
        the lighter object and goes second)."""
        cur = self.conn.execute(
            "DELETE FROM trips WHERE trip_id = ?", (trip_id,)
        )
        self.conn.commit()
        return cur.rowcount > 0

    @staticmethod
    def _row_to_trip(row: sqlite3.Row) -> TripRow:
        try:
            travelers = json.loads(row["travelers"])
        except (TypeError, ValueError):
            travelers = []
        if not isinstance(travelers, list):
            travelers = []
        return TripRow(
            trip_id=row["trip_id"],
            created_at=row["created_at"],
            name=row["name"],
            start_date=row["start_date"],
            end_date=row["end_date"],
            travelers=[str(t) for t in travelers],
            updated_at=row["updated_at"],
            # Tolerant of a row read before the migration ran (a
            # stored config must never be able to break a view).
            cost_center=str(
                (row["cost_center"] if "cost_center" in row.keys() else "")
                or ""
            ),
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
        result: str | None = None,
        updated_at: str,
    ) -> None:
        self.conn.execute(
            # COALESCE keeps the last recorded pipeline stage when the final
            # status write passes no stage (done/error must not blank it).
            # Same rule for result: only a job kind that produces a payload
            # (the receipts drop) ever passes one, and a later status write
            # must not blank it.
            "UPDATE jobs SET status = ?, run_id = ?, error = ?, "
            "stage = COALESCE(?, stage), result = COALESCE(?, result), "
            "updated_at = ? WHERE job_id = ?",
            (status, run_id, error, stage, result, updated_at, job_id),
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
            "SELECT status, run_id, error, stage, result FROM jobs "
            "WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            return None
        job = {
            "status": row["status"],
            "run_id": row["run_id"],
            "error": row["error"],
            "stage": row["stage"],
        }
        if row["result"]:
            # Stored as JSON text; a corrupt payload degrades to absent
            # rather than 500ing the poll.
            try:
                job["result"] = json.loads(row["result"])
            except ValueError:
                pass
        return job

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
            "disposition, decided_by, decided_rule, receipt_requested_at, "
            "receipt_requested_to, no_receipt_expected FROM decisions "
            "WHERE run_id = ?",
            (run_id,),
        ).fetchall()
        return {
            r["transaction_id"]: Decision(
                status=r["status"],
                chosen_document_id=r["chosen_document_id"],
                updated_at=r["updated_at"],
                disposition=r["disposition"],
                decided_by=r["decided_by"],
                rule=r["decided_rule"],
                receipt_requested_at=r["receipt_requested_at"],
                receipt_requested_to=r["receipt_requested_to"],
                no_receipt_expected=r["no_receipt_expected"],
            )
            for r in rows
        }

    def rekey_decisions(self, run_id: str, mapping: dict[str, str]) -> int:
        """Move a run's decisions from old transaction ids to new ones.

        A statement re-read (2026-09-11) re-parses the stored files, and a
        content-derived id changes whenever the parse changes the canonical
        amount (the sign fix is exactly that). The reviewer's verdicts are
        keyed on the old ids; this carries each one over to the id the same
        sheet row now has, so a re-read never orphans a decision. OR REPLACE:
        if the target id already holds a row, the moved verdict wins, which
        cannot happen unless two old rows collapse onto one new one. Returns
        the number of rows moved.
        """
        if not mapping:
            return 0
        moved = 0
        for old_id, new_id in mapping.items():
            if old_id == new_id:
                continue
            cur = self.conn.execute(
                "UPDATE OR REPLACE decisions SET transaction_id = ? "
                "WHERE run_id = ? AND transaction_id = ?",
                (new_id, run_id, old_id),
            )
            moved += cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
        # Note item T3: the re-read rebuilt the month's uploads, so the
        # memo is stale and each moved verdict has to name the statement
        # its NEW id was printed on. The same bytes re-read give the same
        # `statement_id`, so on the ordinary re-read this rewrites the
        # same value; on a corrected file it follows the correction.
        self._forget_charge_origins(run_id)
        for new_id in mapping.values():
            statement_id = self.statement_id_for_charge(run_id, new_id)
            if statement_id:
                self.conn.execute(
                    "UPDATE decisions SET statement_id = ? WHERE run_id = ? "
                    "AND transaction_id = ?",
                    (statement_id, run_id, new_id),
                )
        self.conn.commit()
        return moved

    def set_decision(
        self,
        run_id: str,
        transaction_id: str,
        status: str,
        chosen_document_id: str | None,
        updated_at: str,
        decided_by: str = "reviewer",
        rule: str | None = None,
    ) -> None:
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid status {status!r}; expected {VALID_STATUSES}")
        # The ON CONFLICT SET deliberately excludes `disposition` (§17):
        # re-triaging a row never clears its disposition verdict.
        # `decided_by` defaults to "reviewer" because every caller but one is
        # a route a person drives; a reviewer's write, pending included, is
        # what stops the tool from confirming that charge again (item 76).
        self.conn.execute(
            "INSERT INTO decisions (run_id, transaction_id, status, "
            "chosen_document_id, updated_at, decided_by, decided_rule) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(run_id, transaction_id) DO UPDATE SET "
            "status = excluded.status, "
            "chosen_document_id = excluded.chosen_document_id, "
            "updated_at = excluded.updated_at, "
            "decided_by = excluded.decided_by, "
            "decided_rule = excluded.decided_rule",
            (run_id, transaction_id, status, chosen_document_id, updated_at,
             decided_by, rule),
        )
        self._stamp_decision_statement(run_id, transaction_id)
        self.conn.commit()

    def set_tool_decision(
        self,
        run_id: str,
        transaction_id: str,
        status: str,
        chosen_document_id: str | None,
        updated_at: str,
        rule: str | None,
    ) -> bool:
        """The tool's own verdict (item 76), written only where no person has
        spoken: no row yet, a row the tool wrote, or a legacy pending row
        (NULL `decided_by`, which is a disposition seed or an un-attributed
        reset). The condition sits in the UPDATE's WHERE, so a reviewer's
        click that lands between the tool's read and this write is kept, not
        overwritten. Returns whether the row now holds the tool's verdict."""
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid status {status!r}; expected {VALID_STATUSES}")
        cur = self.conn.execute(
            "INSERT INTO decisions (run_id, transaction_id, status, "
            "chosen_document_id, updated_at, decided_by, decided_rule) "
            "VALUES (?, ?, ?, ?, ?, 'tool', ?) "
            "ON CONFLICT(run_id, transaction_id) DO UPDATE SET "
            "status = excluded.status, "
            "chosen_document_id = excluded.chosen_document_id, "
            "updated_at = excluded.updated_at, "
            "decided_by = 'tool', "
            "decided_rule = excluded.decided_rule "
            "WHERE decisions.decided_by = 'tool' "
            "OR (decisions.decided_by IS NULL AND decisions.status = 'pending')",
            (run_id, transaction_id, status, chosen_document_id, updated_at, rule),
        )
        self._stamp_decision_statement(run_id, transaction_id)
        self.conn.commit()
        return cur.rowcount > 0

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
        self._stamp_decision_statement(run_id, transaction_id)
        self.conn.commit()

    def set_receipt_requested(
        self,
        run_id: str,
        transaction_id: str,
        requested_at: str | None,
        requested_to: str | None,
        updated_at: str,
    ) -> None:
        """Item 107: record that this charge's receipt was asked for, or
        clear the record (`requested_at=None`).

        Status-preserving in the same way `set_disposition` is: a fresh row
        seeds `status=pending`, an existing row keeps its status, its chosen
        document and its disposition untouched. Asking for a receipt is not
        a verdict on the charge, and it must never look like one."""
        self.conn.execute(
            "INSERT INTO decisions (run_id, transaction_id, status, "
            "chosen_document_id, updated_at, receipt_requested_at, "
            "receipt_requested_to) VALUES (?, ?, ?, NULL, ?, ?, ?) "
            "ON CONFLICT(run_id, transaction_id) DO UPDATE SET "
            "receipt_requested_at = excluded.receipt_requested_at, "
            "receipt_requested_to = excluded.receipt_requested_to, "
            "updated_at = excluded.updated_at",
            (run_id, transaction_id, STATUS_PENDING, updated_at,
             requested_at, requested_to),
        )
        self._stamp_decision_statement(run_id, transaction_id)
        self.conn.commit()

    def set_no_receipt_expected(
        self,
        run_id: str,
        transaction_id: str,
        reason: str | None,
        updated_at: str,
    ) -> None:
        """Item 107: record that no receipt will ever exist for this charge,
        and why (`reason=None` clears the mark).

        Status-preserving like the two upserts above. The reason is the whole
        content of the verdict: a mark with no reason closes a charge for a
        reason nobody can read next month, so the route refuses a blank one
        rather than storing an empty string."""
        self.conn.execute(
            "INSERT INTO decisions (run_id, transaction_id, status, "
            "chosen_document_id, updated_at, no_receipt_expected) "
            "VALUES (?, ?, ?, NULL, ?, ?) "
            "ON CONFLICT(run_id, transaction_id) DO UPDATE SET "
            "no_receipt_expected = excluded.no_receipt_expected, "
            "updated_at = excluded.updated_at",
            (run_id, transaction_id, STATUS_PENDING, updated_at, reason),
        )
        self._stamp_decision_statement(run_id, transaction_id)
        self.conn.commit()

    # -- category overrides ----------------------------------------------

    def get_category_overrides(self, run_id: str) -> dict[tuple[str, int], dict]:
        rows = self.conn.execute(
            "SELECT document_id, line_index, category, zoho_account, "
            "category_source FROM category_overrides WHERE run_id = ?",
            (run_id,),
        ).fetchall()
        return {
            (r["document_id"], r["line_index"]): {
                "category": r["category"],
                "zoho_account": r["zoho_account"],
                # A row written before the column existed reads as a
                # person's own pick; see the migration note above.
                "category_source": r["category_source"] or CATEGORY_SOURCE_HUMAN,
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
        *,
        category_source: str,
    ) -> None:
        """Upsert one line's category / account pick.

        `category_source` is REQUIRED and keyword-only on purpose: it is the
        one fact the learning path cannot recover afterwards, and every
        writer knows it at the moment it writes. A default here would let a
        new caller teach the model its own guess by omission, which is the
        leak this column closed."""
        if category_source not in CATEGORY_SOURCES:
            raise ValueError(
                f"invalid category_source {category_source!r}; "
                f"expected {CATEGORY_SOURCES}"
            )
        self.conn.execute(
            "INSERT INTO category_overrides (run_id, document_id, line_index, "
            "category, zoho_account, updated_at, category_source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(run_id, document_id, line_index) DO UPDATE SET "
            "category = excluded.category, "
            "zoho_account = excluded.zoho_account, "
            "updated_at = excluded.updated_at, "
            "category_source = excluded.category_source",
            (run_id, document_id, line_index, category, zoho_account, updated_at,
             category_source),
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

    # -- when a run was last edited (2026-09-16) ---------------------------

    # Every per-run edit table carrying `run_id` + `updated_at`. `receipt_claims`
    # is keyed on two run columns and stamps `claimed_at`; a claim always rides
    # a decision write, whose stamp is already in `decisions`.
    _EDIT_TABLES = (
        "decisions",
        "category_overrides",
        "expense_field_overrides",
        "expense_edits",
        "duplicate_resolutions",
    )

    def latest_edit_at(self, run_id: str) -> str | None:
        """The latest `updated_at` over this run's rows in every edit table,
        or None when it has none. Feeds the review payloads' `updated_at`: a
        field edit on a month without a statement changes no snapshot, so the
        edit tables are the only place it is recorded.

        MAX over the stored strings, which every writer produces with the one
        `_now_iso` format; the service parses and normalizes the result."""
        union = " UNION ALL ".join(
            f"SELECT MAX(updated_at) AS at FROM {table} WHERE run_id = ?"
            for table in self._EDIT_TABLES
        )
        row = self.conn.execute(
            f"SELECT MAX(at) AS at FROM ({union})",
            (run_id,) * len(self._EDIT_TABLES),
        ).fetchone()
        return row["at"] if row and row["at"] else None

    # -- memory_commits (item 88) -------------------------------------------

    def get_memory_commit(self, run_id: str) -> dict | None:
        """The last time this run's corrections were saved to memory:
        `{digest, committed_at, trigger}`, or None when they never were."""
        row = self.conn.execute(
            "SELECT digest, committed_at, trigger FROM memory_commits "
            "WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        return dict(row) if row else None

    def clear_memory_commit(self, run_id: str) -> None:
        """Forget that this run's corrections were saved (item 163's undo).
        The next publish then teaches them again instead of answering
        "unchanged" over a memory that no longer holds them."""
        self.conn.execute("DELETE FROM memory_commits WHERE run_id = ?", (run_id,))
        self.conn.commit()

    # -- memory_journal (item 163) ------------------------------------------

    def add_memory_journal(
        self,
        *,
        run_id: str,
        label: str,
        committed_at: str,
        trigger: str,
        rows: list[dict],
        merchants_before: dict,
        merchants_after: dict,
        learned: dict,
    ) -> int:
        """Record one memory save with everything an undo needs, and return
        its id."""
        cur = self.conn.execute(
            "INSERT INTO memory_journal (run_id, label, committed_at, trigger, "
            "rows_json, merchants_before, merchants_after, learned_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id, label or "", committed_at, trigger,
                json.dumps(rows, default=str),
                json.dumps(merchants_before or {}, default=str),
                json.dumps(merchants_after or {}, default=str),
                json.dumps(learned or {}, default=str),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    @staticmethod
    def _memory_journal_row(row) -> dict:
        return {
            "id": int(row["id"]),
            "run_id": row["run_id"],
            "label": row["label"] or "",
            "committed_at": row["committed_at"],
            "trigger": row["trigger"],
            "rows": json.loads(row["rows_json"]),
            "merchants_before": json.loads(row["merchants_before"]),
            "merchants_after": json.loads(row["merchants_after"]),
            "learned": json.loads(row["learned_json"]),
            "reverted_at": row["reverted_at"] or "",
        }

    def get_memory_journal(self, journal_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM memory_journal WHERE id = ?", (journal_id,)
        ).fetchone()
        return self._memory_journal_row(row) if row else None

    def list_memory_journal(self, limit: int = 50) -> list[dict]:
        """The saves, newest first."""
        rows = self.conn.execute(
            "SELECT * FROM memory_journal ORDER BY id DESC LIMIT ?", (int(limit),)
        ).fetchall()
        return [self._memory_journal_row(r) for r in rows]

    def latest_memory_journal(self) -> dict | None:
        """The newest save that has not been undone; None when every save
        has been. Saves stack on the same rows, so this is the only one an
        undo can put back without discarding a later one."""
        row = self.conn.execute(
            "SELECT * FROM memory_journal WHERE reverted_at IS NULL "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return self._memory_journal_row(row) if row else None

    def set_memory_journal_reverted(self, journal_id: int, at: str) -> None:
        self.conn.execute(
            "UPDATE memory_journal SET reverted_at = ? WHERE id = ?",
            (at, journal_id),
        )
        self.conn.commit()

    def set_memory_commit(
        self, run_id: str, digest: str, committed_at: str, trigger: str
    ) -> None:
        """Record what was saved to memory, and by which trigger (`button` /
        `publish`). Its own table because the run summary is rebuilt by
        every re-match, which would forget the record."""
        self.conn.execute(
            "INSERT INTO memory_commits (run_id, digest, committed_at, trigger) "
            "VALUES (?, ?, ?, ?) ON CONFLICT(run_id) DO UPDATE SET "
            "digest = excluded.digest, committed_at = excluded.committed_at, "
            "trigger = excluded.trigger",
            (run_id, digest, committed_at, trigger),
        )
        self.conn.commit()

    # -- daily FX rates (note #79; polled from OpenTickers) ------------------

    def upsert_fx_daily_rates(self, rows, fetched_at: str) -> int:
        """Store `(day, currency, units per EUR, source)` rows, replacing a
        (day, currency) already held: a provider revision for the same day
        wins. Values are kept as the text they arrived as (a Decimal rate
        keeps its digits, a float does not). Returns the row count."""
        rows = [
            (str(day), str(ccy).upper(), str(per_eur), str(source), fetched_at)
            for day, ccy, per_eur, source in rows
        ]
        self.conn.executemany(
            "INSERT INTO fx_daily_rates (day, ccy, per_eur, source, fetched_at) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT(day, ccy) DO UPDATE SET "
            "per_eur = excluded.per_eur, source = excluded.source, "
            "fetched_at = excluded.fetched_at",
            rows,
        )
        self.conn.commit()
        return len(rows)

    def fx_daily_rates(
        self, start: str | None = None, end: str | None = None
    ) -> dict[str, dict[str, str]]:
        """`{day: {currency: units per EUR}}` for start..end inclusive
        (ISO days; either bound optional), days ascending."""
        query = "SELECT day, ccy, per_eur FROM fx_daily_rates"
        clauses, params = [], []
        if start:
            clauses.append("day >= ?")
            params.append(str(start))
        if end:
            clauses.append("day <= ?")
            params.append(str(end))
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY day, ccy"
        out: dict[str, dict[str, str]] = {}
        for row in self.conn.execute(query, params).fetchall():
            out.setdefault(row["day"], {})[row["ccy"]] = row["per_eur"]
        return out

    def fx_daily_rates_status(self) -> dict:
        """How far the table reaches: `{n_days, first_day, last_day,
        currencies}`; zeros / None / [] when empty."""
        row = self.conn.execute(
            "SELECT COUNT(DISTINCT day) AS n, MIN(day) AS first, MAX(day) AS last "
            "FROM fx_daily_rates"
        ).fetchone()
        ccys = [
            r["ccy"] for r in self.conn.execute(
                "SELECT DISTINCT ccy FROM fx_daily_rates ORDER BY ccy"
            ).fetchall()
        ]
        return {
            "n_days": int(row["n"] or 0),
            "first_day": row["first"],
            "last_day": row["last"],
            "currencies": ccys,
        }

    def get_fx_meta(self, key: str) -> str | None:
        row = self.conn.execute(
            "SELECT value FROM fx_daily_rates_meta WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def set_fx_meta(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO fx_daily_rates_meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
        self.conn.commit()

    # -- settings (§16 export policy; one row, id=1) -----------------------

    def _drop_retired_settings(self) -> None:
        """Delete every retired key from the stored settings row, once.
        Runs on every open and is a no-op when none is present, so it needs
        no version stamp and a rollback simply stops dropping."""
        row = self.conn.execute(
            "SELECT data FROM settings WHERE id = 1"
        ).fetchone()
        if row is None:
            return
        try:
            data = json.loads(row["data"])
        except (TypeError, ValueError):
            return
        if not isinstance(data, dict):
            return
        keep = {k: v for k, v in data.items() if k not in RETIRED_SETTINGS_KEYS}
        if len(keep) != len(data):
            self.conn.execute(
                "UPDATE settings SET data = ? WHERE id = 1",
                (json.dumps(keep),),
            )
            self.conn.commit()

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

    # -- receipt claims (R4, backlog item 38) ------------------------------
    # The cross-run settlement registry: one row says "the receipt
    # (receipt_run_id, document_id) is settled against charge transaction_id
    # in run claimed_by_run_id". The PRIMARY KEY is the global invariant --
    # a receipt can never settle two charges across two batches, the
    # cross-run shape of `rematch_month`'s never-drop rule. Within one run
    # the matcher's own per-call assignment already guarantees it.
    # An empty table (every database before this round) makes the invariant
    # vacuously true for history.

    def get_claims_on_receipts(self, receipt_run_id: str) -> dict[str, dict]:
        """document_id -> claim for every claimed receipt LIVING in a run.
        The advisory read at match time and the commit-time re-check both
        filter this on `claimed_by_run_id != run_id`: a run's own claims
        never exclude its own receipts from its own re-match."""
        rows = self.conn.execute(
            "SELECT document_id, claimed_by_run_id, transaction_id, "
            "claimed_at FROM receipt_claims WHERE receipt_run_id = ?",
            (receipt_run_id,),
        ).fetchall()
        return {
            r["document_id"]: {
                "claimed_by_run_id": r["claimed_by_run_id"],
                "transaction_id": r["transaction_id"],
                "claimed_at": r["claimed_at"],
            }
            for r in rows
        }

    def get_claims_by_run(self, claimed_by_run_id: str) -> list[dict]:
        """Every claim a run's matches HOLD, oldest-insert order."""
        rows = self.conn.execute(
            "SELECT receipt_run_id, document_id, transaction_id, claimed_at "
            "FROM receipt_claims WHERE claimed_by_run_id = ? "
            "ORDER BY receipt_run_id, document_id",
            (claimed_by_run_id,),
        ).fetchall()
        return [
            {
                "receipt_run_id": r["receipt_run_id"],
                "document_id": r["document_id"],
                "transaction_id": r["transaction_id"],
                "claimed_at": r["claimed_at"],
            }
            for r in rows
        ]

    def upsert_receipt_claim(
        self,
        receipt_run_id: str,
        document_id: str,
        claimed_by_run_id: str,
        transaction_id: str,
        claimed_at: str,
    ) -> bool:
        """Claim one receipt for one charge. Returns False -- and writes
        nothing -- when another run already holds the receipt: a cross-run
        steal is never silent, the caller surfaces it. The same run
        re-claiming (a re-pick onto a different charge) updates in place."""
        cur = self.conn.execute(
            "UPDATE receipt_claims SET transaction_id = ?, claimed_at = ?, "
            "statement_id = ? "
            "WHERE receipt_run_id = ? AND document_id = ? "
            "AND claimed_by_run_id = ?",
            (transaction_id, claimed_at,
             self.statement_id_for_charge(claimed_by_run_id, transaction_id),
             receipt_run_id, document_id, claimed_by_run_id),
        )
        if cur.rowcount > 0:
            self.conn.commit()
            return True
        try:
            self.conn.execute(
                "INSERT INTO receipt_claims (receipt_run_id, document_id, "
                "claimed_by_run_id, transaction_id, claimed_at, "
                "statement_id) VALUES (?, ?, ?, ?, ?, ?)",
                (receipt_run_id, document_id, claimed_by_run_id,
                 transaction_id, claimed_at,
                 # Note item T3: the claim names a charge in the CLAIMING
                 # run, so the statement is that run's, not the receipt's.
                 self.statement_id_for_charge(
                     claimed_by_run_id, transaction_id)),
            )
        except sqlite3.IntegrityError:
            # Raced or standing claim by another run: the PRIMARY KEY held.
            self.conn.commit()
            return False
        self.conn.commit()
        return True

    def delete_claims_for_tx(
        self, claimed_by_run_id: str, transaction_id: str
    ) -> None:
        """Release whatever receipt a charge's settlement holds (the
        reviewer rejected the match, or re-picked another receipt)."""
        self.conn.execute(
            "DELETE FROM receipt_claims "
            "WHERE claimed_by_run_id = ? AND transaction_id = ?",
            (claimed_by_run_id, transaction_id),
        )
        self.conn.commit()

    def delete_claims_for_receipt(
        self, receipt_run_id: str, document_id: str
    ) -> None:
        """Drop any claim on one receipt (the receipt itself was deleted)."""
        self.conn.execute(
            "DELETE FROM receipt_claims "
            "WHERE receipt_run_id = ? AND document_id = ?",
            (receipt_run_id, document_id),
        )
        self.conn.commit()

    def replace_claims_by_run(
        self,
        claimed_by_run_id: str,
        claims: list[tuple[str, str, str]],
        claimed_at: str,
    ) -> list[tuple[str, str, str]]:
        """Set a run's held claims to exactly `claims`
        ((receipt_run_id, document_id, transaction_id) triples) and return
        the ones REFUSED because another run holds the receipt. Called at
        `rematch_month` commit under the batch writer lock; a non-empty
        return is the race the commit-time re-check downgrades on."""
        self.conn.execute(
            "DELETE FROM receipt_claims WHERE claimed_by_run_id = ?",
            (claimed_by_run_id,),
        )
        conflicts: list[tuple[str, str, str]] = []
        for receipt_run_id, document_id, transaction_id in claims:
            try:
                self.conn.execute(
                    "INSERT INTO receipt_claims (receipt_run_id, "
                    "document_id, claimed_by_run_id, transaction_id, "
                    "claimed_at, statement_id) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (receipt_run_id, document_id, claimed_by_run_id,
                     transaction_id, claimed_at,
                     self.statement_id_for_charge(
                         claimed_by_run_id, transaction_id)),
                )
            except sqlite3.IntegrityError:
                conflicts.append((receipt_run_id, document_id, transaction_id))
        self.conn.commit()
        return conflicts

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

    # -- client-side failure reports (backlog item 50) ---------------------
    # A fetch that rejects never reached this app, so nothing server-side
    # can contain it; these rows are the browser's own account, stamped
    # with what THIS process was at the moment the account arrived. The
    # table is deliberately bounded: it shares a 1GB volume with receipts,
    # and a diagnostic log that can grow without limit is a second fault.

    CLIENT_ERROR_KEEP = 500

    def record_client_error(self, row: dict) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO client_errors (
                received_at, received_ts, operator, caller, kind, url,
                method, message, occurred_at, seconds_ago, duration_ms,
                online, detail, machine, region, server_commit, server_image,
                process_started_at, uptime_s, process_predates_failure
            ) VALUES (
                :received_at, :received_ts, :operator, :caller, :kind, :url,
                :method, :message, :occurred_at, :seconds_ago, :duration_ms,
                :online, :detail, :machine, :region, :server_commit,
                :server_image, :process_started_at, :uptime_s,
                :process_predates_failure
            )
            """,
            row,
        )
        self.conn.execute(
            "DELETE FROM client_errors WHERE id NOT IN ("
            "  SELECT id FROM client_errors ORDER BY id DESC LIMIT ?"
            ")",
            (int(self.CLIENT_ERROR_KEEP),),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_client_errors(self, limit: int = 50) -> list[dict]:
        """Newest first, so the investigation opens on the last failure."""
        rows = self.conn.execute(
            "SELECT * FROM client_errors ORDER BY id DESC LIMIT ?",
            (max(1, int(limit)),),
        ).fetchall()
        return [dict(r) for r in rows]

    def count_client_errors_since(self, since: float, caller: str) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM client_errors "
            "WHERE caller = ? AND received_ts >= ?",
            (caller, float(since)),
        ).fetchone()
        return int(row["n"])
