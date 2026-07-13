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
                      poller, kill switch, worker heartbeat).

Campaign-engine tables (iteration 3):

* ``campaigns``       one row per campaign; approval freezes copy + list.
* ``templates``       versioned message copy; editing INSERTs a new version.
* ``sequences``       one cadence per (campaign, warmness degree).
* ``sequence_steps``  ordered steps: channel, template, day offset from the
                      PREVIOUS step's actual completion.
* ``degree_rules``    data-driven warmness classification (first match wins).
* ``enrollments``     contact x campaign membership + degree; inert until
                      approved.
* ``send_attempts``   the outbox lock table (leases). NEVER pipeline truth:
                      a send is real only when its 'sent' event lands.
* ``campaign_template_pins``  which template version an approval froze.

RESERVED ext_key NAMESPACE: cadence events carry
``ext_key = 'cadence:{enrollment_id}:{step_no}'``. The event-hash basis
(contact, type, ext_key) then admits at most ONE 'sent' event per
enrollment-step, ever - the structural double-send backstop. External
ingest (POST /events) must reject payloads claiming this prefix.

Two SQL VIEWS derive from the log: ``contact_stage`` (sourced..accepted) and
``contact_activity`` (last inbound/outbound timestamp);
``enrollment_progress`` derives cadence progress per enrollment.

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
SOURCES = ("graph-auto", "manual", "import", "worker-auto")

# Warmness degrees (cold -> warm). Each degree maps to one sequence per
# campaign; 'warm' steps default to draft-dirk mode (he clicks send).
DEGREES = ("cold", "cold_touched", "warm")

# How an email step executes: auto-send from matthias.silva@ (CC Dirk) vs a
# ready draft loaded into Dirk's mailbox (his click is the gate on his name).
SEND_MODES = ("auto-matthias", "draft-dirk")

# draft: editable, nothing sends. approved: copy+list FROZEN but still NOT
# sending (the second gate). sending: a human pressed "Start sending" - the
# worker claims only from here. paused: sending halted. done: finished.
CAMPAIGN_STATUSES = ("draft", "approved", "sending", "paused", "done")

# Reserved ext_key prefix for cadence-emitted events (see module docstring).
CADENCE_PREFIX = "cadence:"


def attempt_key_for(enrollment_id: int, step_no: int) -> str:
    return f"{CADENCE_PREFIX}{enrollment_id}:{step_no}"

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

CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id   TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'draft',
    from_address  TEXT NOT NULL DEFAULT 'matthias.silva@brisken.com',
    cc_address    TEXT NOT NULL DEFAULT 'dirk.neumann@brisken.com',
    bcc_address   TEXT NOT NULL DEFAULT 's9hitl_pv69mu@mails4.zohocrm.com',
    send_window   TEXT NOT NULL DEFAULT '{"days":[0,1,2,3,4],"start":"08:30","end":"17:30","tz":"Europe/Berlin"}',
    daily_cap     INTEGER NOT NULL DEFAULT 40,
    throttle_seconds INTEGER NOT NULL DEFAULT 12,
    jitter_seconds   INTEGER NOT NULL DEFAULT 4,
    approved_at   TEXT,
    approved_by   TEXT,
    approved_contacts_hash TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS templates (
    template_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    template_key  TEXT NOT NULL,
    version       INTEGER NOT NULL,
    channel       TEXT NOT NULL CHECK (channel IN ('email', 'linkedin')),
    subject       TEXT,
    body          TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    created_by    TEXT,
    UNIQUE(template_key, version)
);

CREATE TABLE IF NOT EXISTS sequences (
    sequence_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id   TEXT NOT NULL REFERENCES campaigns(campaign_id),
    degree        TEXT NOT NULL,
    name          TEXT NOT NULL,
    send_mode     TEXT NOT NULL DEFAULT 'auto-matthias',
    UNIQUE(campaign_id, degree)
);

CREATE TABLE IF NOT EXISTS sequence_steps (
    step_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    sequence_id   INTEGER NOT NULL REFERENCES sequences(sequence_id),
    step_no       INTEGER NOT NULL,
    channel       TEXT NOT NULL CHECK (channel IN ('email', 'linkedin')),
    template_key  TEXT NOT NULL,
    day_offset    INTEGER NOT NULL,
    UNIQUE(sequence_id, step_no)
);

CREATE TABLE IF NOT EXISTS degree_rules (
    rule_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id TEXT NOT NULL REFERENCES campaigns(campaign_id),
    priority    INTEGER NOT NULL,
    degree      TEXT NOT NULL,
    predicate   TEXT NOT NULL,
    label       TEXT NOT NULL,
    UNIQUE(campaign_id, priority)
);

CREATE TABLE IF NOT EXISTS enrollments (
    enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id    TEXT NOT NULL REFERENCES contacts(contact_id),
    campaign_id   TEXT NOT NULL REFERENCES campaigns(campaign_id),
    degree        TEXT,
    degree_source TEXT NOT NULL DEFAULT 'rules',
    degree_rule   TEXT,
    approved_at   TEXT,
    approved_by   TEXT,
    enrolled_at   TEXT NOT NULL,
    enrolled_by   TEXT,
    UNIQUE(contact_id, campaign_id)
);

-- Operational lock/queue state ONLY, never pipeline truth. attempt_key is
-- PRIMARY KEY, so exactly one row per enrollment-step can ever exist.
CREATE TABLE IF NOT EXISTS send_attempts (
    attempt_key   TEXT PRIMARY KEY,
    enrollment_id INTEGER NOT NULL REFERENCES enrollments(enrollment_id),
    step_no       INTEGER NOT NULL,
    status        TEXT NOT NULL,
    send_mode     TEXT,
    lease_id      TEXT,
    lease_expires TEXT,
    worker_id     TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    to_addr       TEXT,
    rendered_subject TEXT,
    rendered_body TEXT,
    template_key  TEXT,
    template_version INTEGER,
    internet_message_id TEXT,
    entry_id      TEXT,
    claimed_at    TEXT,
    resolved_at   TEXT,
    failure_reason TEXT
);

CREATE TABLE IF NOT EXISTS campaign_template_pins (
    campaign_id  TEXT NOT NULL REFERENCES campaigns(campaign_id),
    template_key TEXT NOT NULL,
    version      INTEGER NOT NULL,
    PRIMARY KEY (campaign_id, template_key)
);

CREATE INDEX IF NOT EXISTS ix_events_extkey  ON outreach_events(ext_key);
CREATE INDEX IF NOT EXISTS ix_enroll_camp    ON enrollments(campaign_id);
CREATE INDEX IF NOT EXISTS ix_attempts_enrl  ON send_attempts(enrollment_id, step_no);

CREATE VIEW IF NOT EXISTS enrollment_progress AS
SELECT en.enrollment_id, en.contact_id, en.campaign_id,
  (SELECT COUNT(*) FROM outreach_events e
     WHERE e.contact_id = en.contact_id
       AND e.ext_key LIKE 'cadence:' || en.enrollment_id || ':%') AS steps_done,
  (SELECT MAX(e.ts) FROM outreach_events e
     WHERE e.contact_id = en.contact_id
       AND e.ext_key LIKE 'cadence:' || en.enrollment_id || ':%') AS last_step_ts,
  EXISTS (SELECT 1 FROM outreach_events e
     WHERE e.contact_id = en.contact_id AND e.direction = 'inbound'
       AND e.type = 'reply' AND e.ts >= en.enrolled_at)           AS replied,
  EXISTS (SELECT 1 FROM outreach_events e
     WHERE e.contact_id = en.contact_id AND e.type = 'bounce')    AS bounced
FROM enrollments en;
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

    # -- campaigns ---------------------------------------------------------

    def create_campaign(self, campaign_id: str, name: str, now: str, **opts) -> None:
        cols = ["campaign_id", "name", "created_at", "updated_at"]
        vals = [campaign_id, name, now, now]
        for k in ("status", "from_address", "cc_address", "bcc_address",
                  "send_window", "daily_cap", "throttle_seconds", "jitter_seconds"):
            if k in opts and opts[k] not in (None, ""):
                cols.append(k)
                vals.append(opts[k])
        self.conn.execute(
            f"INSERT OR IGNORE INTO campaigns ({', '.join(cols)}) "
            f"VALUES ({', '.join('?' for _ in cols)})",
            vals,
        )
        self.conn.commit()

    def get_campaign(self, campaign_id: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)
        ).fetchone()

    def list_campaigns(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM campaigns ORDER BY created_at DESC"
        ).fetchall()

    def update_campaign(self, campaign_id: str, fields: dict, now: str) -> None:
        cols = [c for c in fields if c in (
            "name", "status", "from_address", "cc_address", "bcc_address",
            "send_window", "daily_cap", "throttle_seconds", "jitter_seconds",
            "approved_at", "approved_by", "approved_contacts_hash",
        )]
        if not cols:
            return
        set_clause = ", ".join(f"{c} = ?" for c in cols) + ", updated_at = ?"
        self.conn.execute(
            f"UPDATE campaigns SET {set_clause} WHERE campaign_id = ?",
            [fields[c] for c in cols] + [now, campaign_id],
        )
        self.conn.commit()

    # -- templates (versioned; editing inserts a new version) --------------

    def save_template(self, template_key: str, channel: str, subject: str | None,
                      body: str, by: str | None, now: str) -> int:
        """Insert the next version for the key and return the version number."""
        row = self.conn.execute(
            "SELECT COALESCE(MAX(version), 0) AS v FROM templates WHERE template_key = ?",
            (template_key,),
        ).fetchone()
        version = int(row["v"]) + 1
        self.conn.execute(
            "INSERT INTO templates (template_key, version, channel, subject, body, created_at, created_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (template_key, version, channel, subject, body, now, by),
        )
        self.conn.commit()
        return version

    def get_template(self, template_key: str, version: int | None = None) -> sqlite3.Row | None:
        if version is None:
            return self.conn.execute(
                "SELECT * FROM templates WHERE template_key = ? ORDER BY version DESC LIMIT 1",
                (template_key,),
            ).fetchone()
        return self.conn.execute(
            "SELECT * FROM templates WHERE template_key = ? AND version = ?",
            (template_key, version),
        ).fetchone()

    def list_templates(self) -> list[sqlite3.Row]:
        """Latest version per template_key."""
        return self.conn.execute(
            "SELECT t.* FROM templates t JOIN (SELECT template_key, MAX(version) AS v "
            "FROM templates GROUP BY template_key) m "
            "ON m.template_key = t.template_key AND m.v = t.version "
            "ORDER BY t.template_key"
        ).fetchall()

    # -- sequences + steps --------------------------------------------------

    def upsert_sequence(self, campaign_id: str, degree: str, name: str,
                        send_mode: str, steps: list[dict]) -> int:
        """Replace the sequence definition for (campaign, degree) atomically.
        ``steps``: [{step_no, channel, template_key, day_offset}]. Allowed only
        pre-approval (service enforces)."""
        cur = self.conn.execute(
            "INSERT INTO sequences (campaign_id, degree, name, send_mode) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(campaign_id, degree) DO UPDATE SET name = excluded.name, "
            "send_mode = excluded.send_mode",
            (campaign_id, degree, name, send_mode),
        )
        row = self.conn.execute(
            "SELECT sequence_id FROM sequences WHERE campaign_id = ? AND degree = ?",
            (campaign_id, degree),
        ).fetchone()
        seq_id = int(row["sequence_id"])
        self.conn.execute("DELETE FROM sequence_steps WHERE sequence_id = ?", (seq_id,))
        for s in steps:
            self.conn.execute(
                "INSERT INTO sequence_steps (sequence_id, step_no, channel, template_key, day_offset) "
                "VALUES (?, ?, ?, ?, ?)",
                (seq_id, s["step_no"], s["channel"], s["template_key"], s["day_offset"]),
            )
        self.conn.commit()
        return seq_id

    def delete_sequence(self, campaign_id: str, degree: str) -> None:
        row = self.conn.execute(
            "SELECT sequence_id FROM sequences WHERE campaign_id = ? AND degree = ?",
            (campaign_id, degree),
        ).fetchone()
        if row is None:
            return
        self.conn.execute("DELETE FROM sequence_steps WHERE sequence_id = ?", (row["sequence_id"],))
        self.conn.execute("DELETE FROM sequences WHERE sequence_id = ?", (row["sequence_id"],))
        self.conn.commit()

    def get_sequence(self, campaign_id: str, degree: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM sequences WHERE campaign_id = ? AND degree = ?",
            (campaign_id, degree),
        ).fetchone()
        if row is None:
            return None
        steps = self.conn.execute(
            "SELECT * FROM sequence_steps WHERE sequence_id = ? ORDER BY step_no",
            (row["sequence_id"],),
        ).fetchall()
        return {**dict(row), "steps": [dict(s) for s in steps]}

    def sequences_for_campaign(self, campaign_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM sequences WHERE campaign_id = ? ORDER BY degree", (campaign_id,)
        ).fetchall()
        out = []
        for row in rows:
            steps = self.conn.execute(
                "SELECT * FROM sequence_steps WHERE sequence_id = ? ORDER BY step_no",
                (row["sequence_id"],),
            ).fetchall()
            out.append({**dict(row), "steps": [dict(s) for s in steps]})
        return out

    # -- degree rules --------------------------------------------------------

    def replace_rules(self, campaign_id: str, rules: list[dict]) -> None:
        """``rules``: [{priority, degree, predicate(json str), label}]."""
        self.conn.execute("DELETE FROM degree_rules WHERE campaign_id = ?", (campaign_id,))
        for r in rules:
            self.conn.execute(
                "INSERT INTO degree_rules (campaign_id, priority, degree, predicate, label) "
                "VALUES (?, ?, ?, ?, ?)",
                (campaign_id, r["priority"], r["degree"], r["predicate"], r["label"]),
            )
        self.conn.commit()

    def get_rules(self, campaign_id: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM degree_rules WHERE campaign_id = ? ORDER BY priority",
            (campaign_id,),
        ).fetchall()

    # -- enrollments ---------------------------------------------------------

    def enroll(self, contact_id: str, campaign_id: str, by: str | None, now: str) -> bool:
        """Idempotent membership insert. Returns True when newly enrolled."""
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO enrollments (contact_id, campaign_id, enrolled_at, enrolled_by) "
            "VALUES (?, ?, ?, ?)",
            (contact_id, campaign_id, now, by),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def get_enrollment(self, enrollment_id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM enrollments WHERE enrollment_id = ?", (enrollment_id,)
        ).fetchone()

    def find_enrollment(self, contact_id: str, campaign_id: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM enrollments WHERE contact_id = ? AND campaign_id = ?",
            (contact_id, campaign_id),
        ).fetchone()

    def enrollments_for_campaign(self, campaign_id: str) -> list[sqlite3.Row]:
        """Enrollment x contact x derived progress, one row per enrolled contact."""
        return self.conn.execute(
            """
            SELECT en.enrollment_id, en.degree, en.degree_source, en.degree_rule,
                   en.approved_at AS enrollment_approved_at, en.enrolled_at,
                   c.*, s.stage AS stage, a.last_out, a.last_in,
                   ep.steps_done, ep.last_step_ts,
                   ep.replied AS cadence_replied, ep.bounced AS cadence_bounced
            FROM enrollments en
            JOIN contacts c        ON c.contact_id = en.contact_id
            JOIN contact_stage s   ON s.contact_id = c.contact_id
            LEFT JOIN contact_activity a     ON a.contact_id = c.contact_id
            LEFT JOIN enrollment_progress ep ON ep.enrollment_id = en.enrollment_id
            WHERE en.campaign_id = ?
            ORDER BY c.company, c.last_name
            """,
            (campaign_id,),
        ).fetchall()

    def set_degree(self, enrollment_id: int, degree: str | None, source: str,
                   rule_label: str | None) -> None:
        self.conn.execute(
            "UPDATE enrollments SET degree = ?, degree_source = ?, degree_rule = ? "
            "WHERE enrollment_id = ?",
            (degree, source, rule_label, enrollment_id),
        )
        self.conn.commit()

    def approve_pending_enrollments(self, campaign_id: str, by: str, now: str) -> int:
        cur = self.conn.execute(
            "UPDATE enrollments SET approved_at = ?, approved_by = ? "
            "WHERE campaign_id = ? AND approved_at IS NULL",
            (now, by, campaign_id),
        )
        self.conn.commit()
        return cur.rowcount

    def remove_enrollment(self, enrollment_id: int) -> None:
        self.conn.execute("DELETE FROM enrollments WHERE enrollment_id = ?", (enrollment_id,))
        self.conn.commit()

    # -- template pins ---------------------------------------------------------

    def pin_templates(self, campaign_id: str, pins: dict[str, int]) -> None:
        self.conn.execute(
            "DELETE FROM campaign_template_pins WHERE campaign_id = ?", (campaign_id,)
        )
        for key, version in pins.items():
            self.conn.execute(
                "INSERT INTO campaign_template_pins (campaign_id, template_key, version) "
                "VALUES (?, ?, ?)",
                (campaign_id, key, version),
            )
        self.conn.commit()

    def get_pins(self, campaign_id: str) -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT template_key, version FROM campaign_template_pins WHERE campaign_id = ?",
            (campaign_id,),
        ).fetchall()
        return {r["template_key"]: int(r["version"]) for r in rows}

    # -- send attempts (outbox lock table) --------------------------------------

    def get_attempt(self, attempt_key: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM send_attempts WHERE attempt_key = ?", (attempt_key,)
        ).fetchone()

    def attempts_for_campaign(self, campaign_id: str, statuses: tuple[str, ...] | None = None) -> list[sqlite3.Row]:
        q = (
            "SELECT sa.*, en.campaign_id, en.contact_id FROM send_attempts sa "
            "JOIN enrollments en ON en.enrollment_id = sa.enrollment_id "
            "WHERE en.campaign_id = ?"
        )
        args: list = [campaign_id]
        if statuses:
            q += f" AND sa.status IN ({', '.join('?' for _ in statuses)})"
            args.extend(statuses)
        return self.conn.execute(q + " ORDER BY sa.claimed_at", args).fetchall()

    def try_lease(self, *, attempt_key: str, enrollment_id: int, step_no: int,
                  send_mode: str, lease_id: str, lease_expires: str, worker_id: str,
                  to_addr: str | None, rendered_subject: str | None, rendered_body: str,
                  template_key: str, template_version: int, now: str,
                  max_attempts: int = 3) -> bool:
        """Take the per-step lock (committed immediately - the attempt_key
        PRIMARY KEY is the atomicity guarantee across connections).

        Insert when no row exists; re-lease only a 'queued' row (transient
        retry) under the attempt cap. Every other status (leased, sent,
        drafted, parked, stalled, failed) is not claimable here."""
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO send_attempts "
            "(attempt_key, enrollment_id, step_no, status, send_mode, lease_id, lease_expires, "
            " worker_id, attempt_count, to_addr, rendered_subject, rendered_body, "
            " template_key, template_version, claimed_at) "
            "VALUES (?, ?, ?, 'leased', ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)",
            (attempt_key, enrollment_id, step_no, send_mode, lease_id, lease_expires,
             worker_id, to_addr, rendered_subject, rendered_body,
             template_key, template_version, now),
        )
        if cur.rowcount > 0:
            self.conn.commit()
            return True
        cur = self.conn.execute(
            "UPDATE send_attempts SET status = 'leased', send_mode = ?, lease_id = ?, "
            "lease_expires = ?, worker_id = ?, attempt_count = attempt_count + 1, "
            "to_addr = ?, rendered_subject = ?, rendered_body = ?, "
            "template_key = ?, template_version = ?, claimed_at = ?, failure_reason = NULL "
            "WHERE attempt_key = ? AND status = 'queued' AND attempt_count < ?",
            (send_mode, lease_id, lease_expires, worker_id, to_addr, rendered_subject,
             rendered_body, template_key, template_version, now, attempt_key, max_attempts),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def update_attempt(self, attempt_key: str, fields: dict) -> None:
        cols = [c for c in fields if c in (
            "status", "lease_id", "lease_expires", "worker_id", "attempt_count",
            "internet_message_id", "entry_id", "resolved_at", "failure_reason",
        )]
        if not cols:
            return
        set_clause = ", ".join(f"{c} = ?" for c in cols)
        self.conn.execute(
            f"UPDATE send_attempts SET {set_clause} WHERE attempt_key = ?",
            [fields[c] for c in cols] + [attempt_key],
        )
        self.conn.commit()

    def find_attempt_by_imid(self, internet_message_id: str) -> sqlite3.Row | None:
        if not internet_message_id:
            return None
        return self.conn.execute(
            "SELECT * FROM send_attempts WHERE internet_message_id = ? LIMIT 1",
            (internet_message_id,),
        ).fetchone()

    def expire_leases(self, now: str) -> int:
        """Flip expired leases to 'stalled' (surfaced for a human; never auto
        re-leased: at-most-once beats at-least-once for real email)."""
        cur = self.conn.execute(
            "UPDATE send_attempts SET status = 'stalled' "
            "WHERE status = 'leased' AND lease_expires < ?",
            (now,),
        )
        self.conn.commit()
        return cur.rowcount

    def cadence_sends_today(self, campaign_id: str, day_prefix: str) -> int:
        """Cap accounting: today's landed cadence sends + outstanding leases."""
        landed = self.conn.execute(
            "SELECT COUNT(*) FROM outreach_events e "
            "JOIN enrollments en ON e.ext_key LIKE 'cadence:' || en.enrollment_id || ':%' "
            "WHERE en.campaign_id = ? AND e.type = 'sent' AND e.ts LIKE ?",
            (campaign_id, day_prefix + "%"),
        ).fetchone()[0]
        outstanding = self.conn.execute(
            "SELECT COUNT(*) FROM send_attempts sa "
            "JOIN enrollments en ON en.enrollment_id = sa.enrollment_id "
            "WHERE en.campaign_id = ? AND sa.status = 'leased'",
            (campaign_id,),
        ).fetchone()[0]
        return int(landed) + int(outstanding)
