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
    "sent", "touch", "reply", "invite", "bounce", "note", "booked", "held", "accepted",
    # compensating events (reverse a milestone; the stage view reads the latest)
    "unbooked", "unaccepted",
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
    "outreach_status",
    "suppressed", "suppress_reason", "suppressed_at", "suppressed_by",
    "crm_owner", "demo_owner", "next_step", "next_step_due", "next_step_at",
    "source", "in_our_booth", "scanned_at_booth", "if_we_know_them",
    "brisken_customer", "attendee_type", "sponsor_opt_in", "no_show",
    "fob_encoded", "booth_registered_at", "crm_last_activity",
    "bant_need", "bant_authority", "bant_timeline", "bant_budget",
    "demo_date", "dirk_verdict", "dirk_notes", "notes",
    "merged_into",
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
    start_not_before TEXT,
    ramp_per_day  INTEGER,
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
    reply_to_prior INTEGER NOT NULL DEFAULT 0,
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
    failure_reason TEXT,
    force_fresh   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS campaign_template_pins (
    campaign_id  TEXT NOT NULL REFERENCES campaigns(campaign_id),
    template_key TEXT NOT NULL,
    version      INTEGER NOT NULL,
    PRIMARY KEY (campaign_id, template_key)
);

-- Each approved contact's EXACT recipient address, frozen at approval. The
-- claim path refuses to send to an address that has drifted from this value
-- (the daily sheet-sync can overwrite a contact's email after approval), so a
-- send only ever goes to an address a human reviewed at approval time.
CREATE TABLE IF NOT EXISTS campaign_recipient_pins (
    campaign_id  TEXT NOT NULL REFERENCES campaigns(campaign_id),
    contact_id   TEXT NOT NULL REFERENCES contacts(contact_id),
    email        TEXT NOT NULL,
    PRIMARY KEY (campaign_id, contact_id)
);

CREATE INDEX IF NOT EXISTS ix_events_extkey  ON outreach_events(ext_key);
CREATE INDEX IF NOT EXISTS ix_enroll_camp    ON enrollments(campaign_id);
CREATE INDEX IF NOT EXISTS ix_attempts_enrl  ON send_attempts(enrollment_id, step_no);

-- Captured events that matched no contact, parked for operator review (link
-- to an existing contact or dismiss). Never auto-creates a contact - that is
-- an owner decision (2026-07-14). event_hash dedupes a re-poll of the same
-- message into one row (seen_count bumps instead).
CREATE TABLE IF NOT EXISTS unmatched_events (
    id                  INTEGER PRIMARY KEY,
    email               TEXT NOT NULL,
    payload             TEXT NOT NULL,
    first_seen          TEXT NOT NULL,
    last_seen           TEXT NOT NULL,
    seen_count          INTEGER NOT NULL DEFAULT 1,
    status              TEXT NOT NULL DEFAULT 'open',
    resolved_contact_id TEXT,
    resolved_at         TEXT,
    resolved_by         TEXT,
    event_hash          TEXT NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS ix_unmatched_status ON unmatched_events(status, email);

-- Mailbox-truth scaffolding (v11): suppression ledger, truth-scan run log,
-- and the per-mailbox folder cache the scanner walks. Written by the truth
-- pipeline; no store methods yet.
CREATE TABLE IF NOT EXISTS suppression_entries (
    entry    TEXT PRIMARY KEY,
    kind     TEXT NOT NULL,
    source   TEXT NOT NULL,
    added_at TEXT NOT NULL,
    note     TEXT
);

CREATE TABLE IF NOT EXISTS truth_runs (
    run_id          TEXT PRIMARY KEY,
    kind            TEXT NOT NULL,
    started_at      TEXT,
    finished_at     TEXT,
    window_since    TEXT,
    corpus_messages INTEGER,
    folders_scanned INTEGER,
    folders_failed  TEXT,
    events_added    INTEGER,
    anomalies       TEXT,
    report          TEXT
);

CREATE TABLE IF NOT EXISTS folder_cache (
    mailbox          TEXT NOT NULL,
    folder_id        TEXT NOT NULL,
    path             TEXT,
    total_item_count INTEGER,
    last_scanned     TEXT,
    last_hit         TEXT,
    skip             INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (mailbox, folder_id)
);
"""

# ---------------------------------------------------------------------------
# Derived VIEWS live here, NOT in _SCHEMA, and are (re)created by the
# migration runner below rather than by ``CREATE VIEW IF NOT EXISTS``. The
# old bootstrap used IF NOT EXISTS, which froze a view's definition on the
# already-deployed prod DB: editing the SQL never reached production because
# the view already existed. The runner drops + recreates them from these
# definitions whenever SCHEMA_VERSION advances, so a definition change here
# actually lands on the prod volume. Keep each as the single source of truth.
_VIEWS = {
    "contact_activity": """
CREATE VIEW contact_activity AS
SELECT c.contact_id,
  (SELECT MAX(e.ts) FROM outreach_events e
     WHERE e.contact_id = c.contact_id AND e.direction = 'outbound') AS last_out,
  (SELECT MAX(e.ts) FROM outreach_events e
     WHERE e.contact_id = c.contact_id AND e.direction = 'inbound')  AS last_in
FROM contacts c
""",
    "contact_stage": """
CREATE VIEW contact_stage AS
SELECT c.contact_id,
  CASE
    WHEN c.dirk_verdict = 'accepted'
      OR (SELECT e.type FROM outreach_events e
          WHERE e.contact_id = c.contact_id AND e.type IN ('accepted', 'unaccepted')
          ORDER BY e.ts DESC, e.event_id DESC LIMIT 1) = 'accepted'
      THEN 'accepted'
    WHEN EXISTS (SELECT 1 FROM outreach_events e WHERE e.contact_id = c.contact_id AND e.type = 'held')
      THEN 'held'
    WHEN (c.demo_date IS NOT NULL AND c.demo_date != '')
      OR (SELECT e.type FROM outreach_events e
          WHERE e.contact_id = c.contact_id AND e.type IN ('booked', 'unbooked')
          ORDER BY e.ts DESC, e.event_id DESC LIMIT 1) = 'booked'
      THEN 'booked'
    WHEN (c.bant_need + c.bant_authority + c.bant_timeline + c.bant_budget) > 0
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
FROM contacts c
""",
    "enrollment_progress": """
CREATE VIEW enrollment_progress AS
SELECT en.enrollment_id, en.contact_id, en.campaign_id,
  (SELECT COUNT(*) FROM outreach_events e
     WHERE e.contact_id = en.contact_id
       AND e.ext_key LIKE 'cadence:' || en.enrollment_id || ':%') AS steps_done,
  -- The SET of step_nos already sent, parsed from the reserved ext_key
  -- 'cadence:{eid}:{step_no}' (comma-joined, unordered). step_no is the stable
  -- send-identity, so keying cadence progress on this set (not the bare count
  -- above) keeps the pointer correct across a mid-sequence INSERT/REORDER: an
  -- unsent step is never skipped and a sent step is never re-sent. Same WHERE as
  -- steps_done, so len(sent_steps) == steps_done always.
  (SELECT group_concat(
       CAST(substr(e.ext_key,
                   length('cadence:' || en.enrollment_id || ':') + 1) AS INTEGER))
     FROM outreach_events e
     WHERE e.contact_id = en.contact_id
       AND e.ext_key LIKE 'cadence:' || en.enrollment_id || ':%') AS sent_steps,
  (SELECT MAX(e.ts) FROM outreach_events e
     WHERE e.contact_id = en.contact_id
       AND e.ext_key LIKE 'cadence:' || en.enrollment_id || ':%') AS last_step_ts,
  EXISTS (SELECT 1 FROM outreach_events e
     WHERE e.contact_id = en.contact_id AND e.direction = 'inbound'
       AND e.type = 'reply' AND e.ts >= en.enrolled_at)           AS replied,
  EXISTS (SELECT 1 FROM outreach_events e
     WHERE e.contact_id = en.contact_id AND e.type = 'bounce')    AS bounced
FROM enrollments en
""",
}


def _refresh_views_sql(*names: str) -> list[str]:
    """DROP + CREATE statements that make the named views match ``_VIEWS``.
    A migration uses this so an existing prod DB picks up a view-definition
    change (``CREATE VIEW IF NOT EXISTS`` never refreshes an existing view)."""
    out: list[str] = []
    for n in names:
        out.append(f"DROP VIEW IF EXISTS {n}")
        out.append(_VIEWS[n].strip())
    return out


def _add_column(table: str, col: str, decl: str):
    """A replay-safe ADD COLUMN migration step: SQLite has no
    ``ADD COLUMN IF NOT EXISTS``, so guard on table_info. Idempotent even if a
    DB's user_version is ever rolled back and the migration replays."""
    def _step(conn) -> None:
        existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if col not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
    return _step


# v6 (passwordless auth) DDL. Kept out of _SCHEMA so a fresh DB gets these via
# the migration and an existing prod DB via the same migration - one code path,
# so the runner's user_version guard covers both.
_USERS_DDL = """
CREATE TABLE IF NOT EXISTS users (
    email         TEXT PRIMARY KEY,
    name          TEXT,
    role          TEXT NOT NULL DEFAULT 'member',
    status        TEXT NOT NULL DEFAULT 'pending',
    created_at    TEXT NOT NULL,
    approved_at   TEXT,
    approved_by   TEXT,
    last_login_at TEXT
)
"""
# Single-use magic-link tokens. Only the sha256 of the raw token is stored, so
# a DB leak never yields a live link; the raw token lives only in the email.
_LOGIN_TOKENS_DDL = """
CREATE TABLE IF NOT EXISTS login_tokens (
    token_hash  TEXT PRIMARY KEY,
    email       TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    used_at     TEXT,
    request_ip  TEXT
)
"""

USER_ROLES = ("admin", "member")
USER_STATUSES = ("pending", "approved", "disabled")


def _seed_admin_users(conn) -> None:
    """Seed the two known operators as approved admins so the gate is never
    left with zero approvers after cut-over. Idempotent: INSERT OR IGNORE
    keyed on the email PK, and it never demotes an existing row."""
    from datetime import datetime, timezone

    from .auth import SEED_ADMIN_EMAILS
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for email in SEED_ADMIN_EMAILS:
        conn.execute(
            "INSERT OR IGNORE INTO users "
            "(email, name, role, status, created_at, approved_at, approved_by) "
            "VALUES (?, '', 'admin', 'approved', ?, ?, 'seed')",
            (email, now, now),
        )


# Ordered schema migrations. Each key N holds the steps that move a DB from
# user_version N-1 to N; a step is either a raw SQL string or a callable(conn).
# All steps are replay-safe (DROP...IF EXISTS / guarded ADD COLUMN). BUMP
# SCHEMA_VERSION and append a new entry whenever a _VIEWS definition changes or
# a column is added, so the change reaches the deployed prod DB.
_MIGRATIONS: dict[int, list] = {
    # v1: establish the runner and refresh all three derived views so future
    # definition edits reach the prod volume (whose views were frozen by the
    # old CREATE VIEW IF NOT EXISTS bootstrap).
    1: _refresh_views_sql("contact_activity", "contact_stage", "enrollment_progress"),
    # v2: the sheet's human status column, stored for display only (owner 2026
    # -07-15: display-only, no stage mapping). Sheet-authoritative on re-sync;
    # NOT in migrate.APP_OWNED_ON_RESYNC. Lives only here (not in _SCHEMA) so a
    # fresh DB gets it via this migration and an existing DB via the ALTER.
    2: [_add_column("contacts", "outreach_status", "TEXT")],
    # v3: refresh contact_stage - qualifying now counts bant_budget in the BANT
    # sum, and booked/accepted read the LATEST booked/unbooked (accepted/
    # unaccepted) event so clearing a demo_date / verdict actually reverses.
    3: _refresh_views_sql("contact_stage"),
    # v4: merge-duplicate tombstone pointer. A merged loser stays as a
    # suppressed 'duplicate' row pointing at its survivor, so the next sheet
    # sync cannot resurrect it as a fresh active contact.
    4: [_add_column("contacts", "merged_into", "TEXT")],
    # v5: next_step authored-time. Without it the board cannot tell a stale
    # pre-reply plan (a "No reply yet / nudge on <date>" next_step written
    # before the contact replied) from a genuine post-reply plan, so it kept
    # surfacing "No reply yet" as the action next to a captured reply
    # (Asako Teruki / NYK, 2026-07-21). Going forward every next_step write is
    # stamped accurately (update_fields / upsert_contact). The one-time backfill
    # can only DATE legacy rows, so it stamps created_at (a safe lower bound;
    # updated_at is UNSAFE - a sheet sync bumps it past the reply) ONLY for
    # plans that literally assert "No reply yet", which a captured reply
    # contradicts. Everything else stays NULL = honored verbatim, so a genuine
    # post-reply note (e.g. "HOT: he asked for a call") is never suppressed.
    5: [
        _add_column("contacts", "next_step_at", "TEXT"),
        "UPDATE contacts SET next_step_at = created_at "
        "WHERE next_step LIKE 'No reply yet%' AND next_step_at IS NULL",
    ],
    # v6: passwordless auth. A per-account registry (`users`) plus single-use
    # magic-link tokens (`login_tokens`), and the two known operators seeded as
    # approved admins. Access-code login stays as an admin break-glass; this
    # only ADDS the email path and the admin-approval registry.
    6: [
        _USERS_DDL.strip(),
        _LOGIN_TOKENS_DDL.strip(),
        "CREATE INDEX IF NOT EXISTS ix_login_tokens_email ON login_tokens(email)",
        _seed_admin_users,
    ],
    # v7: recipient pins. approve_campaign now snapshots each approved contact's
    # exact email; the claim path refuses to send to an address that drifted
    # from the approved value (the daily sheet-sync can overwrite a contact's
    # email after approval). Table is in _SCHEMA for a fresh DB and here for the
    # existing prod volume - one code path, both covered by the user_version
    # guard.
    7: [
        "CREATE TABLE IF NOT EXISTS campaign_recipient_pins ("
        "campaign_id TEXT NOT NULL REFERENCES campaigns(campaign_id), "
        "contact_id TEXT NOT NULL REFERENCES contacts(contact_id), "
        "email TEXT NOT NULL, "
        "PRIMARY KEY (campaign_id, contact_id))",
    ],
    # v8: vacation-aware scheduling. A nullable 'no earlier than' date per
    # campaign: the claim path sends nothing before it, and step 1 anchors on
    # max(approved_at, start_not_before) so day-offset math counts from the
    # real start. Lets a wave be approved now but held until people are back.
    8: [_add_column("campaigns", "start_not_before", "TEXT")],
    # v9: spaced sending. A nullable per-day NEW-contact ramp: at most
    # ramp_per_day first-step (step 1) sends per day, so a large wave spreads
    # over days instead of firing every step-1 at once (daily_cap alone only
    # bounds the total, not the fresh-contact burst). Follow-up steps are not
    # ramp-limited.
    9: [_add_column("campaigns", "ramp_per_day", "INTEGER")],
    # v10: step_no-keyed cadence progress. enrollment_progress now also exposes
    # sent_steps (the SET of sent step_nos), so enrollment_state picks the first
    # UNSENT step by identity instead of a positional count. This makes live
    # mid-sequence INSERT/REORDER safe (no re-send of old copy, no skipped new
    # step). A pure view-definition change; refresh so the prod volume picks it up.
    10: _refresh_views_sql("enrollment_progress"),
    # v11: truth ingest. unmatched_events parks captured events that matched no
    # contact for operator link/dismiss (no auto-created contacts - owner
    # 2026-07-14); suppression_entries / truth_runs / folder_cache back the
    # mailbox-truth pipeline. Tables are in _SCHEMA for a fresh DB and here for
    # the existing prod volume - one user_version guard covers both (v7 pattern).
    11: [
        "CREATE TABLE IF NOT EXISTS unmatched_events ("
        "id INTEGER PRIMARY KEY, "
        "email TEXT NOT NULL, "
        "payload TEXT NOT NULL, "
        "first_seen TEXT NOT NULL, "
        "last_seen TEXT NOT NULL, "
        "seen_count INTEGER NOT NULL DEFAULT 1, "
        "status TEXT NOT NULL DEFAULT 'open', "
        "resolved_contact_id TEXT, "
        "resolved_at TEXT, "
        "resolved_by TEXT, "
        "event_hash TEXT NOT NULL UNIQUE)",
        "CREATE INDEX IF NOT EXISTS ix_unmatched_status "
        "ON unmatched_events(status, email)",
        "CREATE TABLE IF NOT EXISTS suppression_entries ("
        "entry TEXT PRIMARY KEY, "
        "kind TEXT NOT NULL, "
        "source TEXT NOT NULL, "
        "added_at TEXT NOT NULL, "
        "note TEXT)",
        "CREATE TABLE IF NOT EXISTS truth_runs ("
        "run_id TEXT PRIMARY KEY, "
        "kind TEXT NOT NULL, "
        "started_at TEXT, "
        "finished_at TEXT, "
        "window_since TEXT, "
        "corpus_messages INTEGER, "
        "folders_scanned INTEGER, "
        "folders_failed TEXT, "
        "events_added INTEGER, "
        "anomalies TEXT, "
        "report TEXT)",
        "CREATE TABLE IF NOT EXISTS folder_cache ("
        "mailbox TEXT NOT NULL, "
        "folder_id TEXT NOT NULL, "
        "path TEXT, "
        "total_item_count INTEGER, "
        "last_scanned TEXT, "
        "last_hit TEXT, "
        "skip INTEGER NOT NULL DEFAULT 0, "
        "PRIMARY KEY (mailbox, folder_id))",
    ],
    # v12: in-thread reply steps. A sequence step flagged reply_to_prior sends
    # as a Graph reply threaded onto the PRIOR step's sent mail (wire subject
    # 'RE: <prior subject>'). force_fresh is the operator escape hatch on a
    # parked reply attempt: re-queue it as a plain fresh send when the anchor
    # is unrecoverable. Columns are in _SCHEMA for a fresh DB and here for the
    # existing prod volume - one user_version guard covers both (v2 pattern).
    12: [
        _add_column("sequence_steps", "reply_to_prior", "INTEGER NOT NULL DEFAULT 0"),
        _add_column("send_attempts", "force_fresh", "INTEGER NOT NULL DEFAULT 0"),
    ],
}

# Highest applied migration. On a fresh DB the runner applies 1..N in order;
# on the prod DB it applies only the entries above its current user_version.
SCHEMA_VERSION = max(_MIGRATIONS)


# Suppression reasons, most-restrictive first (permanent consent blocks, then
# exclusion tiers, then the revisitable hold). Used when a merge unions two
# contacts' suppression onto the survivor.
_SUPPRESS_PRIORITY = (
    "no_consent", "stop", "do_not_contact", "bounced",
    "duplicate", "test", "organiser", "own_team", "unreachable", "anon", "held",
)


def _stronger_suppress_reason(a: str | None, b: str | None) -> str | None:
    for r in _SUPPRESS_PRIORITY:
        if a == r or b == r:
            return r
    return a or b


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
        # Wait up to 5s for a competing write instead of erroring immediately;
        # matters at cold boot when several threadpool connections open at once
        # and the migration runner briefly holds the write lock.
        self.conn.execute("PRAGMA busy_timeout = 5000")
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
        self._run_migrations()

    def _run_migrations(self) -> None:
        """Apply pending schema migrations exactly once, gated on
        ``PRAGMA user_version``.

        Views and future column adds live in ``_MIGRATIONS`` (NOT in
        per-connect DDL): running DROP VIEW / ALTER TABLE on every connect
        would race the concurrent threadpool connections a scale-to-zero
        machine opens at cold boot. The version guard means the DDL runs
        only until one connection advances user_version to SCHEMA_VERSION;
        every later connect is a single PRAGMA read and returns. BEGIN
        IMMEDIATE serialises the first-boot race: a loser blocks, then
        re-reads the (now current) version inside the lock and skips."""
        if self.conn.execute("PRAGMA user_version").fetchone()[0] >= SCHEMA_VERSION:
            return
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            version = self.conn.execute("PRAGMA user_version").fetchone()[0]
            for target in range(version + 1, SCHEMA_VERSION + 1):
                for stmt in _MIGRATIONS[target]:
                    if callable(stmt):
                        stmt(self.conn)
                    else:
                        self.conn.execute(stmt)
                # user_version takes no bind parameter; target is a trusted int.
                self.conn.execute(f"PRAGMA user_version = {target}")
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    # -- contacts ---------------------------------------------------------

    def upsert_contact(self, data: dict, now: str) -> None:
        """Insert or refresh a contact keyed by natural_key (idempotent)."""
        # A first-adopt next_step (sheet column) is authored now; stamp its
        # time so a later reply can supersede it. Re-sync drops next_step from
        # the payload (APP_OWNED_ON_RESYNC), so this never re-stamps a hold.
        if data.get("next_step") and "next_step_at" not in data:
            data = {**data, "next_step_at": now}
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
        row = self.conn.execute(
            "SELECT * FROM contacts WHERE lower(email) = ? OR lower(alt_email) = ? LIMIT 1",
            (addr, addr),
        ).fetchone()
        # Follow a merge tombstone to the survivor, so an event captured for a
        # merged loser's address lands on the surviving contact's timeline.
        if row is not None and row["merged_into"]:
            survivor = self.get_contact(row["merged_into"])
            if survivor is not None:
                return survivor
        return row

    def merge_contacts(self, survivor_id: str, loser_id: str, now: str) -> dict:
        """Fold ``loser`` into ``survivor``: repoint the loser's events +
        enrollments, union suppression most-restrictively, and leave the loser
        as a suppressed 'duplicate' tombstone pointing at the survivor (so the
        next sheet sync cannot resurrect it). Returns a small result dict."""
        survivor = self.get_contact(survivor_id)
        loser = self.get_contact(loser_id)
        if survivor is None or loser is None or survivor_id == loser_id:
            return {"ok": False, "error": "bad survivor/loser"}
        moved = self.conn.execute(
            "UPDATE outreach_events SET contact_id = ? WHERE contact_id = ?",
            (survivor_id, loser_id)).rowcount
        self.conn.execute(
            "UPDATE OR IGNORE enrollments SET contact_id = ? WHERE contact_id = ?",
            (survivor_id, loser_id))
        self.conn.execute("DELETE FROM enrollments WHERE contact_id = ?", (loser_id,))
        # most-restrictive suppression wins on the survivor
        reason = _stronger_suppress_reason(
            survivor["suppress_reason"] if survivor["suppressed"] else None,
            loser["suppress_reason"] if loser["suppressed"] else None)
        if reason and not survivor["suppressed"]:
            self.conn.execute(
                "UPDATE contacts SET suppressed = 1, suppress_reason = ?, "
                "suppressed_at = ?, suppressed_by = 'merge', updated_at = ? WHERE contact_id = ?",
                (reason, now, now, survivor_id))
        self.conn.execute(
            "UPDATE contacts SET suppressed = 1, suppress_reason = 'duplicate', "
            "merged_into = ?, updated_at = ? WHERE contact_id = ?",
            (survivor_id, now, loser_id))
        self.conn.commit()
        return {"ok": True, "events_moved": moved,
                "survivor": survivor_id, "loser": loser_id}

    def update_fields(self, contact_id: str, fields: dict, now: str) -> None:
        # Stamp when next_step was (re)authored so the board can tell a fresh
        # plan from one overtaken by a later reply (see the v5 migration).
        if "next_step" in fields and "next_step_at" not in fields:
            fields = {**fields, "next_step_at": now}
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

    # -- unmatched capture events -----------------------------------------

    def record_unmatched(self, email: str, payload_json: str,
                         event_hash: str, now: str) -> None:
        """Park a captured event that matched no contact. Idempotent per
        event_hash: a re-poll of the same message bumps last_seen/seen_count
        on the existing row instead of inserting a duplicate."""
        self.conn.execute(
            "INSERT INTO unmatched_events "
            "(email, payload, first_seen, last_seen, event_hash) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(event_hash) DO UPDATE SET "
            "last_seen = excluded.last_seen, seen_count = seen_count + 1",
            (email, payload_json, now, now, event_hash),
        )
        self.conn.commit()

    def get_unmatched(self, unmatched_id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM unmatched_events WHERE id = ?", (unmatched_id,)
        ).fetchone()

    def list_unmatched(self, status: str = "open") -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM unmatched_events WHERE status = ? "
            "ORDER BY last_seen DESC, id",
            (status,),
        ).fetchall()

    def resolve_unmatched(self, unmatched_id: int, contact_id: str | None,
                          by: str | None, now: str,
                          dismiss_reason: str | None = None) -> None:
        """Close an unmatched row: linked (contact_id given) or dismissed.
        ``dismiss_reason``, when given, is kept in resolved_by alongside who
        dismissed it, so the queue shows WHY without another column."""
        status = "linked" if contact_id else "dismissed"
        resolved_by = by
        if status == "dismissed" and dismiss_reason:
            resolved_by = f"{by or 'unknown'}: {dismiss_reason}"
        self.conn.execute(
            "UPDATE unmatched_events SET status = ?, resolved_contact_id = ?, "
            "resolved_at = ?, resolved_by = ? WHERE id = ?",
            (status, contact_id, now, resolved_by, unmatched_id),
        )
        self.conn.commit()

    # -- truth scan (folder cache + run log) ------------------------------

    def get_folder_cache(self, mailbox: str) -> dict[str, sqlite3.Row]:
        """The mailbox's cached folder rows, keyed by folder_id."""
        rows = self.conn.execute(
            "SELECT * FROM folder_cache WHERE mailbox = ?", (mailbox,)
        ).fetchall()
        return {r["folder_id"]: r for r in rows}

    def upsert_folder_cache(self, mailbox: str, folder_id: str,
                            path: str | None, total_item_count: int,
                            now: str, *, hit: bool = False) -> None:
        """Record a scanned folder's count. ``hit`` stamps last_hit (the
        folder yielded an event the DB did not know). The operator-set
        ``skip`` flag is never touched here."""
        self.conn.execute(
            "INSERT INTO folder_cache "
            "(mailbox, folder_id, path, total_item_count, last_scanned, last_hit) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(mailbox, folder_id) DO UPDATE SET "
            "path = excluded.path, "
            "total_item_count = excluded.total_item_count, "
            "last_scanned = excluded.last_scanned, "
            "last_hit = COALESCE(excluded.last_hit, last_hit)",
            (mailbox, folder_id, path, total_item_count, now,
             now if hit else None),
        )
        self.conn.commit()

    def insert_truth_run(self, *, run_id: str, kind: str, started_at: str,
                         finished_at: str, window_since: str,
                         corpus_messages: int, folders_scanned: int,
                         folders_failed: str, events_added: int,
                         report: str, anomalies: str | None = None) -> None:
        self.conn.execute(
            "INSERT INTO truth_runs (run_id, kind, started_at, finished_at, "
            "window_since, corpus_messages, folders_scanned, folders_failed, "
            "events_added, anomalies, report) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, kind, started_at, finished_at, window_since,
             corpus_messages, folders_scanned, folders_failed, events_added,
             anomalies, report),
        )
        self.conn.commit()

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

    def state_keys_with_prefix(self, prefix: str) -> list[str]:
        """State keys starting with ``prefix`` ('%'/'_' in prefix are escaped)."""
        esc = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        rows = self.conn.execute(
            "SELECT key FROM state WHERE key LIKE ? ESCAPE '\\' ORDER BY key",
            (esc + "%",),
        ).fetchall()
        return [r["key"] for r in rows]

    def delete_state(self, key: str) -> bool:
        """Remove one state row. Returns True if a row was deleted."""
        cur = self.conn.execute("DELETE FROM state WHERE key = ?", (key,))
        self.conn.commit()
        return cur.rowcount > 0

    def campaign_ids(self) -> set[str]:
        rows = self.conn.execute("SELECT campaign_id FROM campaigns").fetchall()
        return {r["campaign_id"] for r in rows}

    # -- users + magic-link tokens (passwordless auth) ----------------------

    def get_user(self, email: str) -> sqlite3.Row | None:
        email = (email or "").strip().lower()
        if not email:
            return None
        return self.conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()

    def list_users(self) -> list[sqlite3.Row]:
        """Pending first (they need action), then by email."""
        return self.conn.execute(
            "SELECT * FROM users ORDER BY "
            "CASE status WHEN 'pending' THEN 0 WHEN 'approved' THEN 1 ELSE 2 END, "
            "email"
        ).fetchall()

    def create_pending_user(self, email: str, name: str, now: str) -> bool:
        """Record a new access request. Idempotent (no-op if the email already
        exists in any state). Returns True when a new pending row was created."""
        email = (email or "").strip().lower()
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO users (email, name, role, status, created_at) "
            "VALUES (?, ?, 'member', 'pending', ?)",
            (email, name.strip(), now),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def upsert_user(self, email: str, name: str, role: str, status: str,
                    by: str | None, now: str) -> None:
        """Admin proactively adds/updates a user (the 'invite' path). Sets
        approved_at/by when the status is 'approved'."""
        email = (email or "").strip().lower()
        role = role if role in USER_ROLES else "member"
        status = status if status in USER_STATUSES else "pending"
        approved_at = now if status == "approved" else None
        approved_by = by if status == "approved" else None
        self.conn.execute(
            "INSERT INTO users (email, name, role, status, created_at, approved_at, approved_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(email) DO UPDATE SET name = excluded.name, role = excluded.role, "
            "status = excluded.status, "
            "approved_at = COALESCE(approved_at, excluded.approved_at), "
            "approved_by = COALESCE(approved_by, excluded.approved_by)",
            (email, name.strip(), role, status, now, approved_at, approved_by),
        )
        self.conn.commit()

    def set_user_status(self, email: str, status: str, by: str | None, now: str) -> None:
        email = (email or "").strip().lower()
        if status not in USER_STATUSES:
            raise ValueError(f"bad status {status!r}")
        if status == "approved":
            self.conn.execute(
                "UPDATE users SET status = 'approved', approved_at = ?, approved_by = ? "
                "WHERE email = ?",
                (now, by, email),
            )
        else:
            self.conn.execute(
                "UPDATE users SET status = ? WHERE email = ?", (status, email))
        self.conn.commit()

    def set_user_role(self, email: str, role: str) -> None:
        email = (email or "").strip().lower()
        if role not in USER_ROLES:
            raise ValueError(f"bad role {role!r}")
        self.conn.execute("UPDATE users SET role = ? WHERE email = ?", (role, email))
        self.conn.commit()

    def touch_user_login(self, email: str, now: str) -> None:
        self.conn.execute(
            "UPDATE users SET last_login_at = ? WHERE email = ?",
            (now, (email or "").strip().lower()),
        )
        self.conn.commit()

    def count_admins(self) -> int:
        """Approved admins - the guard that stops the last admin disabling
        themselves and locking everyone out."""
        return self.conn.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'admin' AND status = 'approved'"
        ).fetchone()[0]

    def create_login_token(self, token_hash: str, email: str, now: str,
                           expires_at: str, request_ip: str | None) -> None:
        self.conn.execute(
            "INSERT INTO login_tokens (token_hash, email, created_at, expires_at, request_ip) "
            "VALUES (?, ?, ?, ?, ?)",
            (token_hash, (email or "").strip().lower(), now, expires_at, request_ip),
        )
        self.conn.commit()

    def consume_login_token(self, token_hash: str, now: str) -> str | None:
        """Single-use redemption: return the token's email iff it exists, is
        unused, and is unexpired - and atomically mark it used so a replay (or
        a concurrent click) cannot redeem it twice. Fail-closed on any miss."""
        row = self.conn.execute(
            "SELECT email, expires_at, used_at FROM login_tokens WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()
        if row is None or row["used_at"] is not None or row["expires_at"] < now:
            return None
        cur = self.conn.execute(
            "UPDATE login_tokens SET used_at = ? WHERE token_hash = ? AND used_at IS NULL",
            (now, token_hash),
        )
        self.conn.commit()
        return row["email"] if cur.rowcount == 1 else None

    def purge_expired_tokens(self, now: str) -> int:
        """Drop spent/expired tokens so the table cannot grow unbounded."""
        cur = self.conn.execute(
            "DELETE FROM login_tokens WHERE expires_at < ? OR used_at IS NOT NULL",
            (now,),
        )
        self.conn.commit()
        return cur.rowcount

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
            "start_not_before", "ramp_per_day",
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
        ``steps``: [{step_no, channel, template_key, day_offset,
        reply_to_prior?}]. Allowed only pre-approval (service enforces).
        Validation runs BEFORE any write so a raise leaves the stored
        sequence untouched."""
        for s in steps:
            if int(s["step_no"]) == 1 and int(s.get("reply_to_prior") or 0):
                raise ValueError(
                    "step 1 cannot be a reply: no prior step to reply to")
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
                "INSERT INTO sequence_steps "
                "(sequence_id, step_no, channel, template_key, day_offset, reply_to_prior) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (seq_id, s["step_no"], s["channel"], s["template_key"],
                 s["day_offset"], int(s.get("reply_to_prior") or 0)),
            )
        self.conn.commit()
        return seq_id

    def frozen_step_nos(self, campaign_id: str, degree: str | None) -> set[int]:
        """step_nos that are immutable send history for this (campaign, degree):
        any step with a send_attempt (any status: sent / drafted / leased /
        stalled / parked / queued) OR a landed cadence 'sent' event, for an
        enrollment of that degree. A live sequence delta must preserve these
        unchanged - their send ext_key ``cadence:{eid}:{step_no}`` is spoken for,
        so reusing or renumbering the step_no would corrupt an enrollment's
        pointer. Everything past them is the free-to-edit future region."""
        attempts = self.conn.execute(
            "SELECT DISTINCT sa.step_no FROM send_attempts sa "
            "JOIN enrollments en ON en.enrollment_id = sa.enrollment_id "
            "WHERE en.campaign_id = ? AND en.degree IS ?",
            (campaign_id, degree),
        ).fetchall()
        frozen = {int(r["step_no"]) for r in attempts}
        # Belt-and-suspenders: a landed cadence 'sent' event whose attempt row is
        # somehow absent still freezes its step_no.
        events = self.conn.execute(
            "SELECT DISTINCT CAST(substr(e.ext_key, "
            "  length('cadence:' || en.enrollment_id || ':') + 1) AS INTEGER) AS step_no "
            "FROM outreach_events e "
            "JOIN enrollments en ON e.ext_key LIKE 'cadence:' || en.enrollment_id || ':%' "
            "WHERE en.campaign_id = ? AND en.degree IS ? AND e.type = 'sent'",
            (campaign_id, degree),
        ).fetchall()
        frozen |= {int(r["step_no"]) for r in events if r["step_no"] is not None}
        return frozen

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

    def enroll_campaign_contacts(self, campaign_id: str, by: str | None, now: str) -> int:
        """Enroll every contact tagged with this campaign that is not yet
        enrolled (idempotent). Mirrors the per-row enroll in uploads.py so a
        sheet sync makes synced leads visible on the board. Returns the number
        newly enrolled. No-op when the campaign row does not exist (FK)."""
        if self.get_campaign(campaign_id) is None:
            return 0
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO enrollments (contact_id, campaign_id, enrolled_at, enrolled_by) "
            "SELECT c.contact_id, ?, ?, ? FROM contacts c "
            "WHERE c.campaign = ? "
            "AND NOT EXISTS (SELECT 1 FROM enrollments en "
            "                WHERE en.contact_id = c.contact_id AND en.campaign_id = ?)",
            (campaign_id, now, by, campaign_id, campaign_id),
        )
        self.conn.commit()
        return cur.rowcount

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
                   ep.steps_done, ep.sent_steps, ep.last_step_ts,
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

    def pin_recipients(self, campaign_id: str, pins: dict[str, str]) -> None:
        """Freeze each approved contact's exact recipient address at approval.
        Replace-all per approval (mirrors ``pin_templates``), so an incremental
        re-approval re-snapshots the current, human-reviewed addresses."""
        self.conn.execute(
            "DELETE FROM campaign_recipient_pins WHERE campaign_id = ?", (campaign_id,)
        )
        for contact_id, email in pins.items():
            self.conn.execute(
                "INSERT INTO campaign_recipient_pins (campaign_id, contact_id, email) "
                "VALUES (?, ?, ?)",
                (campaign_id, contact_id, email),
            )
        self.conn.commit()

    def get_recipient_pins(self, campaign_id: str) -> dict[str, str]:
        rows = self.conn.execute(
            "SELECT contact_id, email FROM campaign_recipient_pins WHERE campaign_id = ?",
            (campaign_id,),
        ).fetchall()
        return {r["contact_id"]: r["email"] for r in rows}

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
            "force_fresh",
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

    def first_step_sends_today(self, campaign_id: str, day_prefix: str) -> int:
        """Ramp accounting: today's landed FIRST-step (step 1) cadence sends +
        outstanding step-1 leases. 'New contacts started today' - what the
        per-day ramp bounds (follow-up steps are not ramp-limited)."""
        landed = self.conn.execute(
            "SELECT COUNT(*) FROM outreach_events e "
            "JOIN enrollments en ON e.ext_key = 'cadence:' || en.enrollment_id || ':1' "
            "WHERE en.campaign_id = ? AND e.type = 'sent' AND e.ts LIKE ?",
            (campaign_id, day_prefix + "%"),
        ).fetchone()[0]
        outstanding = self.conn.execute(
            "SELECT COUNT(*) FROM send_attempts sa "
            "JOIN enrollments en ON en.enrollment_id = sa.enrollment_id "
            "WHERE en.campaign_id = ? AND sa.status = 'leased' AND sa.step_no = 1",
            (campaign_id,),
        ).fetchone()[0]
        return int(landed) + int(outstanding)

    def mailbox_sends_today(self, from_address: str, day_prefix: str) -> int:
        """Per-mailbox cap accounting across ALL campaigns that send from this
        address: today's landed cadence sends + outstanding leases. The
        per-campaign daily_cap does not bound the mailbox's total when several
        campaigns send from the same warm mailbox concurrently; this does."""
        landed = self.conn.execute(
            "SELECT COUNT(*) FROM outreach_events e "
            "JOIN enrollments en ON e.ext_key LIKE 'cadence:' || en.enrollment_id || ':%' "
            "JOIN campaigns c ON c.campaign_id = en.campaign_id "
            "WHERE c.from_address = ? AND e.type = 'sent' AND e.ts LIKE ?",
            (from_address, day_prefix + "%"),
        ).fetchone()[0]
        outstanding = self.conn.execute(
            "SELECT COUNT(*) FROM send_attempts sa "
            "JOIN enrollments en ON en.enrollment_id = sa.enrollment_id "
            "JOIN campaigns c ON c.campaign_id = en.campaign_id "
            "WHERE c.from_address = ? AND sa.status = 'leased'",
            (from_address,),
        ).fetchone()[0]
        return int(landed) + int(outstanding)
