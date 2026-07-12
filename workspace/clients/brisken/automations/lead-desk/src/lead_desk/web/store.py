"""SQLite persistence for the Lead Desk.

One database (default ``lead-desk.sqlite`` under the data dir) holds:

* ``contacts``        one row per person: identity, tier, the UNIFIED
                      consent/suppression flag, owner, booth/source
                      provenance, and the human judgment fields (BANT, demo
                      date, Dirk verdict). Status is NOT stored here; it is
                      derived from the event log.
* ``outreach_events`` append-only, one immutable row per touch (auto-captured
                      or hand-logged). The pipeline stage is a pure function of
                      these rows. A correction is a new ``note`` event, never
                      an edit.
* ``state``           small key/value store (delta tokens for the cloud
                      poller, misc runtime state).

Two SQL VIEWS derive from the log: ``contact_stage`` (sourced..accepted) and
``contact_activity`` (last inbound/outbound timestamp).

Opened per operation as a context manager, mirroring the expense-recon
``RunStore`` precedent.
"""
from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

CHANNELS = ("email", "linkedin", "meeting", "call")
DIRECTIONS = ("outbound", "inbound")
EVENT_TYPES = (
    "sent", "touch", "reply", "invite", "bounce", "note", "booked", "held", "accepted"
)
SOURCES = ("graph-auto", "manual", "import")

# Pipeline stages, lowest to highest. Derived from the event log + judgment.
STAGES = ("sourced", "sent", "replied", "qualifying", "booked", "held", "accepted")

# Insertable contact columns (created_at / updated_at are managed by the store).
CONTACT_COLUMNS = (
    "contact_id", "natural_key", "campaign",
    "first_name", "last_name", "company", "job_title",
    "email", "alt_email", "phone", "country", "linkedin_url",
    "tier", "tier_reason", "lead_type", "persona", "signal",
    "suppressed", "suppress_reason", "suppressed_at", "suppressed_by",
    "crm_owner", "demo_owner", "next_step", "next_step_due",
    "source", "in_our_booth", "scanned_at_booth", "if_we_know_them",
    "brisken_customer", "attendee_type", "sponsor_opt_in", "no_show",
    "fob_encoded", "booth_registered_at", "crm_last_activity",
    "bant_need", "bant_authority", "bant_timeline", "bant_budget",
    "demo_date", "dirk_verdict", "dirk_notes", "notes",
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    contact_id        TEXT PRIMARY KEY,
    natural_key       TEXT NOT NULL UNIQUE,
    campaign          TEXT NOT NULL DEFAULT 'rome-2026',

    first_name        TEXT,
    last_name         TEXT,
    company           TEXT,
    job_title         TEXT,
    email             TEXT,
    alt_email         TEXT,
    phone             TEXT,
    country           TEXT,
    linkedin_url      TEXT,

    tier              TEXT,
    tier_reason       TEXT,
    lead_type         TEXT,
    persona           TEXT,
    signal            TEXT,

    suppressed        INTEGER NOT NULL DEFAULT 0,
    suppress_reason   TEXT,
    suppressed_at     TEXT,
    suppressed_by     TEXT,

    crm_owner         TEXT,
    demo_owner        TEXT,
    next_step         TEXT,
    next_step_due     TEXT,

    source            TEXT,
    in_our_booth      INTEGER DEFAULT 0,
    scanned_at_booth  INTEGER DEFAULT 0,
    if_we_know_them   TEXT,
    brisken_customer  TEXT,
    attendee_type     TEXT,
    sponsor_opt_in    INTEGER DEFAULT 0,
    no_show           INTEGER DEFAULT 0,
    fob_encoded       INTEGER DEFAULT 0,
    booth_registered_at TEXT,
    crm_last_activity TEXT,

    bant_need         INTEGER DEFAULT 0,
    bant_authority    INTEGER DEFAULT 0,
    bant_timeline     INTEGER DEFAULT 0,
    bant_budget       INTEGER DEFAULT 0,
    demo_date         TEXT,
    dirk_verdict      TEXT,
    dirk_notes        TEXT,
    notes             TEXT,

    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach_events (
    event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id  TEXT NOT NULL REFERENCES contacts(contact_id),
    campaign    TEXT NOT NULL DEFAULT 'rome-2026',
    ts          TEXT NOT NULL,
    channel     TEXT NOT NULL,
    direction   TEXT NOT NULL,
    type        TEXT NOT NULL,
    subject     TEXT,
    detail      TEXT,
    source      TEXT NOT NULL,
    created_by  TEXT,
    ext_key     TEXT,
    created_at  TEXT NOT NULL,
    event_hash  TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS state (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TEXT
);

CREATE INDEX IF NOT EXISTS ix_events_contact ON outreach_events(contact_id, ts);
CREATE INDEX IF NOT EXISTS ix_events_type    ON outreach_events(campaign, type, direction);
CREATE INDEX IF NOT EXISTS ix_contacts_camp  ON contacts(campaign, suppressed, tier);

CREATE VIEW IF NOT EXISTS contact_activity AS
SELECT c.contact_id,
  (SELECT MAX(e.ts) FROM outreach_events e
     WHERE e.contact_id = c.contact_id AND e.direction = 'outbound') AS last_out,
  (SELECT MAX(e.ts) FROM outreach_events e
     WHERE e.contact_id = c.contact_id AND e.direction = 'inbound')  AS last_in
FROM contacts c;

CREATE VIEW IF NOT EXISTS contact_stage AS
SELECT c.contact_id,
  CASE
    WHEN c.dirk_verdict = 'accepted'
      OR EXISTS (SELECT 1 FROM outreach_events e WHERE e.contact_id = c.contact_id AND e.type = 'accepted')
      THEN 'accepted'
    WHEN EXISTS (SELECT 1 FROM outreach_events e WHERE e.contact_id = c.contact_id AND e.type = 'held')
      THEN 'held'
    WHEN c.demo_date IS NOT NULL AND c.demo_date != ''
      OR EXISTS (SELECT 1 FROM outreach_events e WHERE e.contact_id = c.contact_id AND e.type = 'booked')
      THEN 'booked'
    WHEN (c.bant_need + c.bant_authority + c.bant_timeline) > 0
      AND EXISTS (SELECT 1 FROM outreach_events e
                  WHERE e.contact_id = c.contact_id AND e.direction = 'inbound' AND e.type = 'reply')
      THEN 'qualifying'
    WHEN EXISTS (SELECT 1 FROM outreach_events e
                 WHERE e.contact_id = c.contact_id AND e.direction = 'inbound' AND e.type = 'reply')
      THEN 'replied'
    WHEN EXISTS (SELECT 1 FROM outreach_events e
                 WHERE e.contact_id = c.contact_id AND e.direction = 'outbound' AND e.type IN ('sent', 'invite', 'touch'))
      THEN 'sent'
    ELSE 'sourced'
  END AS stage
FROM contacts c;
"""


def event_hash(contact_id, ts, channel, type_, detail, ext_key=None) -> str:
    """Idempotency key. When an external id (e.g. internetMessageId) is known,
    key on (contact, type, ext_key) so re-polling the same message is a no-op;
    otherwise key on content so a re-import does not double-insert."""
    if ext_key:
        basis = f"{contact_id}|{type_}|{ext_key}"
    else:
        basis = f"{contact_id}|{ts}|{channel}|{type_}|{detail or ''}"
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()


class ContactStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    def __enter__(self) -> "ContactStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        self.conn.close()

    def _init_schema(self) -> None:
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    # -- contacts ---------------------------------------------------------

    def upsert_contact(self, data: dict, now: str) -> None:
        """Insert or refresh a contact keyed by natural_key (idempotent)."""
        cols = [c for c in CONTACT_COLUMNS if c in data]
        if "natural_key" not in cols or "contact_id" not in cols:
            raise ValueError("upsert_contact needs contact_id and natural_key")
        insert_cols = cols + ["created_at", "updated_at"]
        placeholders = ", ".join("?" for _ in insert_cols)
        values = [data[c] for c in cols] + [now, now]
        # On conflict, refresh the provided columns + updated_at; keep created_at.
        updatable = [c for c in cols if c not in ("contact_id", "natural_key")]
        set_clause = ", ".join(f"{c} = excluded.{c}" for c in updatable + ["updated_at"])
        self.conn.execute(
            f"INSERT INTO contacts ({', '.join(insert_cols)}) VALUES ({placeholders}) "
            f"ON CONFLICT(natural_key) DO UPDATE SET {set_clause}",
            values,
        )
        self.conn.commit()

    def get_contact(self, contact_id: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM contacts WHERE contact_id = ?", (contact_id,)
        ).fetchone()

    def get_contact_by_key(self, natural_key: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM contacts WHERE natural_key = ?", (natural_key,)
        ).fetchone()

    def find_by_email(self, addr: str) -> sqlite3.Row | None:
        addr = (addr or "").strip().lower()
        if not addr:
            return None
        return self.conn.execute(
            "SELECT * FROM contacts WHERE lower(email) = ? OR lower(alt_email) = ? LIMIT 1",
            (addr, addr),
        ).fetchone()

    def update_fields(self, contact_id: str, fields: dict, now: str) -> None:
        cols = [c for c in fields if c in CONTACT_COLUMNS
                and c not in ("contact_id", "natural_key")]
        if not cols:
            return
        set_clause = ", ".join(f"{c} = ?" for c in cols) + ", updated_at = ?"
        values = [fields[c] for c in cols] + [now, contact_id]
        self.conn.execute(
            f"UPDATE contacts SET {set_clause} WHERE contact_id = ?", values
        )
        self.conn.commit()

    def set_suppressed(
        self, contact_id: str, suppressed: bool, reason: str | None,
        by: str | None, now: str,
    ) -> None:
        self.conn.execute(
            "UPDATE contacts SET suppressed = ?, suppress_reason = ?, "
            "suppressed_at = ?, suppressed_by = ?, updated_at = ? WHERE contact_id = ?",
            (1 if suppressed else 0, reason, now if suppressed else None,
             by if suppressed else None, now, contact_id),
        )
        self.conn.commit()

    def board_rows(self, campaign: str = "rome-2026") -> list[sqlite3.Row]:
        """Every contact joined with its derived stage + last activity."""
        return self.conn.execute(
            """
            SELECT c.*, s.stage AS stage, a.last_out AS last_out, a.last_in AS last_in,
                   (SELECT COUNT(*) FROM outreach_events e WHERE e.contact_id = c.contact_id) AS event_count,
                   EXISTS (SELECT 1 FROM outreach_events e WHERE e.contact_id = c.contact_id
                           AND e.direction = 'outbound' AND e.type = 'touch') AS has_touch,
                   EXISTS (SELECT 1 FROM outreach_events e WHERE e.contact_id = c.contact_id
                           AND e.direction = 'outbound' AND e.type IN ('sent', 'invite')) AS has_campaign_send
            FROM contacts c
            JOIN contact_stage s ON s.contact_id = c.contact_id
            LEFT JOIN contact_activity a ON a.contact_id = c.contact_id
            WHERE c.campaign = ?
            ORDER BY c.company, c.last_name
            """,
            (campaign,),
        ).fetchall()

    def all_contacts(self, campaign: str = "rome-2026") -> list[sqlite3.Row]:
        return self.board_rows(campaign)

    def count_contacts(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]

    # -- events -----------------------------------------------------------

    def add_event(
        self, *, contact_id: str, ts: str, channel: str, direction: str,
        type: str, subject: str | None = None, detail: str | None = None,
        source: str = "manual", created_by: str | None = None,
        ext_key: str | None = None, campaign: str = "rome-2026", now: str,
    ) -> bool:
        """Append one event (idempotent). Returns True if a new row was inserted."""
        h = event_hash(contact_id, ts, channel, type, detail, ext_key)
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO outreach_events "
            "(contact_id, campaign, ts, channel, direction, type, subject, detail, "
            " source, created_by, ext_key, created_at, event_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (contact_id, campaign, ts, channel, direction, type, subject, detail,
             source, created_by, ext_key, now, h),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def get_events(self, contact_id: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM outreach_events WHERE contact_id = ? ORDER BY ts, event_id",
            (contact_id,),
        ).fetchall()

    def count_events(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM outreach_events").fetchone()[0]

    # -- state (delta tokens etc.) ---------------------------------------

    def get_state(self, key: str) -> str | None:
        row = self.conn.execute("SELECT value FROM state WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def set_state(self, key: str, value: str, now: str) -> None:
        self.conn.execute(
            "INSERT INTO state (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, value, now),
        )
        self.conn.commit()
