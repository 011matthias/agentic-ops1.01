# Lead Desk, Blueprint

Status: Phase 1 LIVE (brisken-lead-desk.fly.dev). Iteration 2 shipped
2026-07-12 (stage reflects real status). Iteration 3 built 2026-07-13
(campaign engine: upload -> warmness -> approved cadences -> auto-send).
Owner decisions 2026-07-12: bespoke app, Rome-first, gated for
Matthias/Dirk/Chris, cloud-only auto-capture. This file is the record of
state for the automation (in place of a separate spec, per the expense-recon
convention).

## Iteration 3, campaign engine (built 2026-07-13)

Owner decisions 2026-07-13: CRM target = Zoho CRM (BCC dropbox now, API
write later); warmness = deterministic rules + manual override; front end =
extend the board; sender = HYBRID (cold degrees auto-send from
matthias.silva@ CC Dirk, warm degree staged as drafts in Dirk's mailbox -
his click is the gate on his own name).

**Sending is a TWO-gate confirm (owner add 2026-07-13, "gate the sending
with at least a confirm button").** Status flow `draft -> approved ->
sending -> (paused) -> done`. Gate 1 = **Approve** (type the id): freezes the
copy (template version pins) + enrolled-list hash; the campaign is now
`approved` but sends NOTHING. Gate 2 = **Start sending** (type the id again):
`approved -> sending`. The worker claims ONLY from a `sending` campaign, so
no email leaves until a human passes BOTH gates in the app. Pause halts
(`sending -> paused`); resume goes back to `sending`. Any copy/sequence edit
supersedes both and drops to `draft`. This is on top of the three kill
switches (app flag, KILL file, schtasks disable).

Brain / hands split:

- **Fly app (brain):** campaigns, versioned templates, sequences per
  warmness degree (`cold`/`cold_touched`/`warm`), data-driven degree rules,
  enrollments (`UNIQUE(contact_id, campaign_id)` over GLOBAL contacts - one
  person, one timeline, consent everywhere), the approval object (pins
  template versions + list hash + schedule), the outbox lock table
  (`send_attempts`, at-most-once leases, no auto-re-lease), kill switch,
  worker heartbeat. Never sends.
- **Local Windows worker (hands, `lead-desk-worker`):** scheduled task every
  15 min in the interactive session. Tick order IS the halt guarantee:
  replay journal -> capture replies/bounces from matthias+dirk inboxes via
  Outlook COM -> claim due sends -> execute (COM send / Dirk-draft load)
  -> heartbeat. Machine off = sends queue server-side, drain at throttle
  pace, never burst. Glue + runbook in `worker/` (dockerignored).

Invariant extended: **cadence state is a pure function of the log.** Cadence
events carry the reserved `ext_key='cadence:{enrollment_id}:{step_no}'`, so
the event hash admits at most ONE sent event per step ever; the
`enrollment_progress` view derives the step pointer; `send_attempts` is a
lock table, never truth (`lead-desk-reconcile` repairs drift). Stops
(re-checked at claim time): reply since enrollment, bounce (auto-suppresses
`bounced`), suppression, pause, superseded approval. LinkedIn steps never
auto-execute - they surface as "Manual touches" board tasks. Draft-dirk
steps complete only when his ACTUAL send is observed in Sent Items (no
follow-up fires while he sits on a draft).

Zoho CRM injection: every auto-send BCCs the CRM dropbox
(s9hitl_pv69mu@mails4.zohocrm.com) - verify once live that a Matthias-sent
BCC files correctly. CRM API write module (contact upsert + inbound notes,
scope minting on the existing self-client) is a later, separable phase.

New secrets: `LEAD_DESK_WORKER_SECRET` (outbox API bearer, separate from
ingest). New scripts: `lead-desk-adopt` (Rome 290 -> enrollments under a
`status='done'` campaign that can never auto-send), `lead-desk-reconcile`,
`lead-desk-worker` (`worker` extra: httpx + pywin32, Windows-only).

Before the first real campaign: run the TEST-campaign gate (enroll
ourselves + one external address, cap 10; verify reply-halt, NDR ->
bounce -> suppress, Zoho dropbox filing, crash drill, kill switches,
catch-up) per `worker/README.md`.

## Iteration 2, stage reflects real status (shipped 2026-07-12)

The raw log missed two real-status signals the master sheet already carried,
so the board mis-showed two groups as active "sourced" to-dos. Fixed:

- **Dirk personal touch -> "Reached (Dirk)".** A `dirk_notes` personal-outreach
  marker, or an `if_we_know_them` note naming Dirk with an engagement verb,
  emits one outbound `touch` event (new event type; channel inferred from the
  note). The `contact_stage` view now treats an outbound `touch` as `sent`, and
  `status_label` shows "Reached (Dirk)" when a touch (and no campaign send) put
  the contact at `sent`, so a relationship touch reads distinctly from a
  campaign send. 8 contacts move sourced -> reached.
- **GA + deliberate holds -> "Held".** A new `suppress_reason='held'`
  (revisitable, ranked below the consent reasons + exclusion tiers) covers the
  GA general-awareness cohort (`tier='GA'` / `dirk_notes='GA'`) and explicit
  `next_step` holds (`on hold|do not send|excluded|covered by`). Transient holds
  (OOO, awaiting-decision, scheduling) stay active. 44 contacts move off the
  active board (active 124 -> 80), filterable via the "Held" chip and shown as
  "Held", visibly distinct from consent-suppressed ("Do not contact") and
  excluded tiers ("Excluded").
- Board gains "Reached (Dirk)" and "Held" filter chips + buckets. Migration
  stays idempotent (touch keyed by a stable `dirk-touch-{cid}` ext_key).

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

## Phase 2, cloud auto-capture (worker built; gated on Brisken IT creds)

A Fly scheduled Machine reads Dirk's mailbox app-only via Microsoft Graph
(`Mail.Read` + `Calendars.Read`, scoped to his mailbox only via Exchange RBAC
for Applications), polls SentItems/Inbox/Calendar, matches recipients to
contacts, and posts `sent`/`reply`/`booked` events to `POST /events` keyed by
`internetMessageId` (calendar: `iCalUId`) so re-polling is a no-op. Planner
app-only writes are tenant-wide, so the Lead Desk is the board of record and
Planner writes are dropped.

**Built (2026-07-12):** `src/lead_desk/capture.py` + console script
`lead-desk-capture` (`capture` extra: httpx). Pure Graph->sink mapping is
unit-tested (`tests/test_capture.py`); idempotency comes from the sink, so a
fixed lookback window each run is safe (no durable delta cursor needed). Runs
with `--dry-run` to inspect before posting.

**Deploy (once creds land)** as a scheduled Machine on the same image:

```bash
# secrets: LEAD_DESK_TENANT_ID, LEAD_DESK_CLIENT_ID, LEAD_DESK_CLIENT_SECRET,
#          LEAD_DESK_MAILBOX (=dirk.neumann@brisken.com); LEAD_DESK_URL + INGEST_SECRET already set
flyctl machine run . -a brisken-lead-desk --schedule hourly \
  --entrypoint "lead-desk-capture" --region fra
```

**Hard client dependency** (nothing in Phase 2 runs until done): Brisken IT
creates the Entra app registration in tenant `aa3bd2bf-...`, grants admin
consent for the two read scopes, applies the mailbox-scoped Application Access
Policy, and issues the credential (stored as Fly secrets). The forwardable
request is `PHASE2-IT-REQUEST.md`.

## Open items (recommended defaults applied)

- Planner lead-gen bucket: retire in favor of the Lead Desk (recommended).
- ANON tier (89 booth scans, no identity): imported as `suppressed=anon`.
- Milestone event types (booked/held/accepted) keep those stages log-derived.
- Gate: standalone Fly HMAC (not the Vercel proxy).
