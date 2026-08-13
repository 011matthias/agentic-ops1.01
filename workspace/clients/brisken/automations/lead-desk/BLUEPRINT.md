# Lead Desk, Blueprint

Status: Phase 1 LIVE (brisken-lead-desk.fly.dev). Iteration 2 shipped
2026-07-12 (stage reflects real status). Iteration 3 built 2026-07-13
(campaign engine: upload -> warmness -> approved cadences -> auto-send).
Owner decisions 2026-07-12: bespoke app, Rome-first, gated for
Matthias/Dirk/Chris, cloud-only auto-capture. This file is the record of
state for the automation (in place of a separate spec, per the expense-recon
convention).

## Iteration 4, Dirk's self-serve cockpit (scope, 2026-07-14)

Owner goal: Dirk runs the **entire** Rome email pipeline from the Lead
Desk alone, without Matthias and without touching the SharePoint sheet,
Outlook, Planner, or Sales Nav. He must be able to view/edit every field
and classification on a contact, see the full context on each person,
generate sequences, and get a bullet brief when he wants to hand-write a
copy. Two dependencies that blocked earlier work are now cleared: the
Graph app `BRISKEN MARKETING OPS INTEGRATION` exists (unblocks Phase 2
auto-capture), and [[rule_brisken_graph_first]] retires the desktop
Outlook-COM send worker in favor of Graph.

### A. View + edit ALL contact data and classifications
Today the contact page edits only BANT/verdict/next-step/persona/signal/
notes. Extend to **every** field, grouped into editable sections:
- **Identity**: first/last, company, job_title, email, alt_email, phone,
  country, linkedin_url.
- **Classification**: tier (H5/T1/T2/T3/GA/STOP/ANON/… dropdown),
  tier_reason, lead_type, persona, signal, crm_owner, brisken_customer.
- **Provenance** (read-mostly): source, in_our_booth, scanned_at_booth,
  fob_encoded, booth_registered_at, attendee_type, no_show, sponsor_opt_in.
- **Qualification + next step**: BANT, demo_date, dirk_verdict, demo_owner,
  next_step, next_step_due, notes, dirk_notes.
Board gets inline quick-edit (tier, next_step, suppress) without opening a
contact, plus **add-contact** and **merge-duplicate** flows (the
dmorrison5 cross-contamination class of bug). Every edit stays audited: a
field change writes a `note` event, preserving the append-only invariant
(stage still derived, never hand-stamped).

### B. Context surface + draft-brief generator
Per-contact **Context** panel aggregating everything needed to write:
role, company, tier + reason, signal, booth provenance, the touch
timeline, the last inbound reply snippet, BANT, CRM owner/last activity,
customer flag, notes, LinkedIn. On top of it a **"Brief for a draft"**
button that emits bullet points (who / angle / the ask / do's + don'ts /
load-bearing facts) for Dirk to write from. This is a BRIEF, not a
finished email ([[feedback_dirk_draftbox_notes_not_drafts]]); grounded in
queried data only, no fabrication (B4). LLM synthesis (Claude) optional
and grounded; the structured fallback is a template over the fields.

### C. Sequence generation
- **Define** named cadences: ordered steps (delay, channel, subject,
  body/merge-template), with per-tier defaults. Delay sits on the earlier
  step ([[reference_instantly_sequence_delay_semantics]]).
- **Assign** a cadence to a contact or a segment (tier/filter); preview
  rendered steps with merge fields resolved from the contact.
- **Two modes**: draft-only (create drafts in Dirk's mailbox for review)
  and auto-send. Sequence progress and stop-on-reply/bounce are derived
  from the event log, not stamped.

### D. Cloud auto-capture + Graph send (Phase 2, now unblocked)
Replace the local `LeadDeskWorker` Outlook-COM task with a Fly scheduled
Machine using the Graph app, **hard-allowlisted to dirk.neumann@ and
matthias.silva@** ([[reference_brisken_graph_app_creds]]): delta-poll
SentItems/Inbox/Calendar (`Mail.Read`+`Calendars.Read`), match recipients
to contacts, POST `sent`/`reply`/`bounce`/`meeting` to `/events` keyed by
`internetMessageId` (idempotent). Sequence sends go via Graph `Mail.Send`
as Dirk. Every live send is invasive: draft-first, explicit per-batch
owner yes, readiness check ([[rule_instantly_invasive]]). (As built
2026-07-16 the worker runs as an in-app loop on the same Fly machine, not
a separate scheduled Machine; see the Iteration 3 brain/hands split below.)

### E. Master sheet relationship
Lead Desk is the single source of truth; the SharePoint master becomes a
**scheduled derived push** from the db (Graph workbook write, the pattern
proven 2026-07-14) so Dirk's existing sheet view stays fresh while the db
is canonical. `/export.{csv,xlsx}` already exist as the pull form.

### F. Navigation / UX (the "easier to navigate" ask)
Home dashboard (funnel + today's actions: awaiting / follow-up due /
aging hot / sends queued); board with saved views, per-tier swimlanes,
sort, and bulk actions (assign sequence, set tier, suppress); a 3-pane
contact cockpit (identity+classification left, context+brief+timeline
center, actions right); global Ctrl-K search across all fields; dark/light
+ keyboard nav per [[rule_deliverables]].

### G. Non-negotiables (carried over)
Server-side gate ([[rule_gated_access]]); PII on the Fly volume, never
committed; Graph-first ([[rule_brisken_graph_first]]); invasive-send gate;
append-only log + derived stage; briefs/context grounded in queried data
(B4).

### Phased build order (recommended)
1. **4a, Edit-all + navigation** (no external deps): all-field grouped
   contact editor, board inline quick-actions, add/merge-contact, saved
   views. Direct "view/manage all data" + "easier to navigate" win.
2. **4b, Context + draft-brief**: context panel + bullet-brief generator.
3. **4c, Sequences**: cadence definitions, assign/preview, draft-only first.
4. **4d, Cloud auto-capture + Graph send**: Fly poller (mail→events),
   retire the COM worker, then Graph `Mail.Send` for auto-send.
5. **4e, Sheet sync**: scheduled Graph push db→SharePoint master.

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
- **Cloud worker (hands, in-app since 4d, 2026-07-16):** an in-app loop on
  the same Fly machine (`cloud_worker.run_tick`, opt-in via
  `LEAD_DESK_CLOUD_WORKER=1` in fly.toml). Tick order IS the halt
  guarantee: replay journal -> capture sent/replies/bounces/meetings from
  the matthias+dirk mailboxes app-only via Microsoft Graph -> claim due
  sends -> execute (Graph sendMail as matthias / draft staged in Dirk's
  mailbox) -> heartbeat. HARD dirk+matthias mailbox allowlist before every
  Graph call; auto mode refuses any other from-address. The predecessor
  local Windows Outlook-COM worker (`worker/`, dockerignored) is retired:
  its scheduled task is disabled and the code stays only as a validated
  fallback until the Graph send path passes the watched send-gate drill.

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

Before the first real campaign: run the arming drill in `ARMING-DRILL.md`
(runbook + `lead-desk-drill` CLI; the COM worker passed the equivalent
gate 2026-07-13, and the Graph cloud sender must pass its own watched
drill before it is ever armed).

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
- **Deliberate holds -> "Held".** A new `suppress_reason='held'`
  (revisitable, ranked below the consent reasons + exclusion tiers) covers
  explicit `next_step` holds (`on hold|do not send|excluded|covered by`).
  Transient holds (OOO, awaiting-decision, scheduling) stay active. Filterable
  via the "Held" chip and shown as "Held", visibly distinct from
  consent-suppressed ("Do not contact") and excluded tiers ("Excluded").
  Iteration 2 originally held the GA cohort too; reversed 2026-07-17 (owner
  directive): GA is an active outreach tier that receives its own GA wave, and
  once T3 + GA sends are out, per-tier follow-up starts on non-responders.
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
