# Lead Desk, Iteration 2 build prompt

Run in a fresh session (`/resume brisken`), or paste the body below as the task.
Read `BLUEPRINT.md` and `../../../../../.claude/.../memory/project_brisken_lead_desk.md` first.

---

## Context

The Lead Desk is LIVE (brisken-lead-desk.fly.dev; code in
`workspace/clients/brisken/automations/lead-desk/`; DB on the Fly volume; 290
contacts). Pipeline stage is derived only from the parsed `outreach_log` +
`last_outreach`/`last_reply`. That misses real-status signals the master sheet
already carries, so the board misclassifies two groups (counts measured against
the live migration):

1. **Dirk personally reached out, but shown "sourced".** ~13-24 contacts carry
   a personal-touch note (`dirk_notes` = "personal outreach DN" (18),
   "Individual outreach DN", "DN personal", "Personal DN"; or `if_we_know_them`
   mentions Dirk, 24 rows) yet have no send line in `outreach_log`, so they read
   as "not contacted". At least 8 are currently active "sourced" to-dos when
   Dirk already engaged them.
2. **Purposefully held, but shown as active "sourced" to-dos.** The GA group
   (`tier='GA'` / `dirk_notes`='GA', 40 contacts, **33 currently active +
   sourced**) is a deliberate hold. Plus `next_step` holds like "On hold:
   excluded_no_verified_email", "Covered by the LSEG note", "DO NOT SEND yet".
   These should be off the active board, distinct from consent-suppressed.

## Task 1 - make stage reflect real status

Update `src/lead_desk/migrate.py`; the derivation lives in `store.py`
(`contact_stage` view) + `service.py` (`status_label`). Keep stage DERIVED,
never a stamped column.

**1a. Dirk personal touch -> "reached", not "sourced".**
- Signal: `dirk_notes` matches `/personal.*(outreach|DN)|individual outreach|DN[\s:]*personal|personally engaged/i`, OR `if_we_know_them` matches `/dirk/i` with an engagement verb.
- Action: emit an outbound event `type='touch'` (add this event type), channel per the note (`email`|`linkedin`|`meeting`), dated `last_outreach` or the note's date, `detail` = the note. Extend `contact_stage` so an outbound `touch` reaches at least `sent`; add a `status_label` "Reached (Dirk)" so the board shows a relationship touch, not a campaign send.

**1b. GA + deliberate holds -> "held", not active.**
- Add a new `suppress_reason='held'` (revisitable), distinct from the consent reasons (`do_not_contact`/`no_consent`) and the exclusion tiers.
- Held signal: `tier='GA'` OR `dirk_notes`=='GA' OR `next_step` matches `/on hold|do not send|excluded|covered by/i`.
- Action: `suppressed=1, suppress_reason='held'`. Keep them OFF the active board but filterable as a "Held" bucket, visibly different from consent-suppressed.
- Do NOT suppress transient holds (`OOO until`, "awaiting Dirk's decision", "scheduling in progress"): leave active, surface via the `next_step`/dangling bucket.

**1c. Surface the reason.** Make `status_label` / the board show WHY a contact is off-board (consent vs held vs excluded-tier); add board filter chips for "Held" and "Reached (Dirk)".

**1d. Re-migrate + reload.** The importer UPSERTs, so re-running applies the new rules idempotently. Re-run `lead-desk-migrate` against a fresh scratch DB, verify counts move as expected (GA active-sourced 33 -> 0 held; Dirk-touch sourced 8+ -> reached), then reload the volume DB via `base64 -w0 | flyctl ssh console -C "sh -c 'base64 -d > /data/lead-desk.sqlite'"` + `flyctl machine restart`, and verify live (login, board counts).

## Task 2 - integrations to fold in (pick + scope; recommended order)

1. **Scheduled value-radar digest** (highest ROI, low effort): a Fly scheduled Machine (or the `morning-briefing.yml` GH-Actions pattern) emails a weekly per-owner digest of the three buckets already computed (awaiting reply, follow-up due, aging hot replies) via Resend. Turns the board into a push.
2. **Zoho CRM read-sync:** pull live `Account_Status`/owner/`last_activity` from Zoho (`.scratch/zoho.py`, read token exists) into `contacts`; flag stage-vs-CRM drift. Later push booked/accepted back (needs a write scope).
3. **Send-from-the-desk:** compose + send an outreach email from a contact page via Graph (Dirk's mailbox, Phase-2 creds), auto-emitting the `sent` event. Makes our own sends self-logging even before inbound capture.
4. **Reply triage:** when Phase-2 capture lands an inbound reply, run a small LLM classification (interested / not / OOO / referral) -> suggested `next_step`, surfaced on the board.
5. **Sales Nav membership reconcile:** import "TA Cook Rome 26" list membership (`reconcile_salesnav.py`) so the board shows LinkedIn-list status alongside email.
6. **Dedup/merge UI:** surface the migration's same-name-different-key list in the app for one-click merge.
7. **Bulk board actions:** multi-select to set owner / next_step / tier / suppress.
8. **Multi-campaign import route:** a CSV/xlsx upload to onboard the MDH cohort, Wix-form leads, future campaigns (schema already keyed on `campaign`).
9. **Funnel metrics page:** counts + conversion by tier/stage/wave, response rates, time-in-stage.
10. **Retire the Planner lead-gen bucket** (or a read-only mirror) now that the Lead Desk is the board of record.

## Constraints

- Idempotent (re-run inserts nothing new); stage DERIVED (events + suppressed/reason, then extend the views), never a hand-stamped stage column.
- PII stays on the Fly volume; never commit the DB. Reload via base64|ssh (sftp put does not work).
- Verify LIVE after any change (curl login + board counts + a contact). The 18 tests must still pass; add tests for the new `touch`/`held` rules.
