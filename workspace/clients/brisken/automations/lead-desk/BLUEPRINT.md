# Lead Desk, Blueprint

Status: Phase 1 built (app + migration), local verification in progress.
Owner decisions 2026-07-12: bespoke app, Rome-first, gated for Matthias/Dirk/
Chris, cloud-only auto-capture. This file is the record of state for the
automation (in place of a separate spec, per the expense-recon convention).

## Problem

Lead-gen status was smeared across ~9 stores (three master-sheet copies, E1/E2/
E3 send logs, booth notes, the Planner board, Sales Nav, Outlook drafts, Zoho)
with 5+ status vocabularies. "Do not contact" was encoded three ways in one
sheet. Every surface was hand-stamped, so they drifted and needed constant
manual reconciliation.

## Design

One SQLite database, two tables:

- `contacts`: identity, tier, a single `suppressed`/`suppress_reason` (the
  three legacy do-not-contact encodings collapsed into one), owner, booth/
  source provenance, and the human judgment fields (BANT, `demo_date`,
  `dirk_verdict`, `next_step`/`next_step_due`).
- `outreach_events`: append-only, one immutable row per touch. `channel`
  (email/linkedin/meeting/call), `direction` (outbound/inbound), `type`
  (sent/reply/invite/bounce/note/booked/held/accepted), `source`
  (graph-auto/manual/import), `event_hash` UNIQUE for idempotency.

The invariant: **stage is a pure function of the log.** Two SQL views derive it:
`contact_stage` (sourced -> sent -> replied -> qualifying -> booked -> held ->
accepted) and `contact_activity` (last inbound/outbound). The service layer adds
status buckets on top: awaiting reply, follow-up due (`next_step_due` past),
aging hot reply (unanswered inbound > 3 days). Nothing is hand-stamped; a
correction is a new `note` event, not an edit.

## App

FastAPI + Jinja + SQLite, cloned module-for-module from the expense-recon web
app. Routes: `/` board (filter by tier/stage/owner/bucket/search, localStorage
filter persistence, Ctrl/Cmd+K search), `/contacts/{id}` timeline + log-a-touch
+ suppress toggle + BANT/verdict/next-step, `/export.{csv,xlsx}` (the master
sheet becomes a derived download), and `POST /events` (the cloud-capture sink,
guarded by `LEAD_DESK_INGEST_SECRET`). Setting `demo_date` or an `accepted`
verdict emits the matching milestone event so the field and the derived stage
cannot disagree.

Gate: server-side HMAC cookie, per-user codes (`LEAD_DESK_ACCESS_CODES`) so
every event is attributed. Satisfies `rule_gated_access.md`'s hard constraints
for a standalone Fly app (no code in page source, codes in Fly secrets).

Deploy: Fly `brisken-lead-desk`, Frankfurt (EU, PII), scale-to-zero, SQLite on
the `lead_desk_data` volume at `/data`. Never committed.

## Migration

`lead-desk-migrate` reads the live `rome2026-post-event-master-contacts.xlsx`
(290 rows), UPSERTs contacts by natural key (email, else name+company hash),
unifies suppression, parses `outreach_log` into events, fills stage-critical
gaps from `last_outreach`/`last_reply`, and folds the E1/E2/E3 send logs when
present. Idempotent (re-run inserts nothing). Emits a same-name-different-key
duplicate review list. Once verified and adopted, the duplicate spreadsheet
copies are deleted (supersession discipline); the master xlsx becomes a
generated `/export.xlsx`.

## Phase 2, cloud auto-capture (built next, gated on Brisken IT)

A Fly scheduled Machine reads Dirk's mailbox app-only via Microsoft Graph
(`Mail.Read` + `Calendars.Read`, scoped to his mailbox only via Exchange RBAC
for Applications), delta-polls SentItems/Inbox/Calendar, matches recipients to
contacts, and posts `sent`/`reply`/`meeting` events to `POST /events` keyed by
`internetMessageId` (idempotent). Planner app-only writes are tenant-wide, so
the Lead Desk is the board of record and Planner writes are dropped.

Hard client dependency (nothing in Phase 2 runs until done): Brisken IT creates
the Entra app registration in tenant `aa3bd2bf-...`, grants admin consent for
the two read scopes, applies the RBAC scope to Dirk's mailbox, and issues the
credential (stored as Fly secrets).

## Open items (recommended defaults applied)

- Planner lead-gen bucket: retire in favor of the Lead Desk (recommended).
- ANON tier (89 booth scans, no identity): imported as `suppressed=anon`.
- Milestone event types (booked/held/accepted) keep those stages log-derived.
- Gate: standalone Fly HMAC (not the Vercel proxy).
