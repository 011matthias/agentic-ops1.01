# Checkpoint: Brisken Lead Desk Iteration 2 + Phase 2 Worker

**Date:** 2026-07-12
**Status:** Iteration 2 LIVE + verified; PR #213 merged; Phase 2 worker built (gated on Brisken IT creds)

---

## Summary
Shipped Iteration 2 of the Brisken Lead Desk (pipeline stage now reflects real
status: Dirk personal touches read as "Reached (Dirk)", the GA cohort and
deliberate holds read as "Held" instead of active "sourced" to-dos), reloaded
the live volume DB, verified live, and merged PR #213. Also built the Phase 2
cloud-capture worker and drafted the forwardable Brisken-IT request that gates
it. Most of the session's wall-clock was a hard outbound-network flap (GitHub,
depot.dev, pypi, and api.fly.io all intermittently unreachable) worked around
with retry loops and a Fly-native builder.

**Why this project exists (owner intent):** this is lead-generation work Dirk
specifically asked for so he can run the lead engine himself, WITHOUT Matthias,
someday. That is the load-bearing design goal behind every choice here: the tool
is the single source of truth (no tribal knowledge in Matthias's head), gated
per-user (Dirk logs in as himself), and moving toward cloud auto-capture (Phase
2) so the board keeps itself current without an operator. Iteration 2 pushes in
the same direction: the board should read the true state on its own, not require
Matthias to interpret a messy sheet.

---

## What Was Done This Session

### Iteration 2 — stage reflects real status
1. **Dirk personal touch → "Reached (Dirk)".** New outbound `touch` event type;
   a `dirk_notes` personal-outreach marker or an `if_we_know_them` "Dirk …
   engaged" note emits one `touch` (channel inferred). The `contact_stage` view
   treats an outbound touch as `sent`; `status_label` shows "Reached (Dirk)"
   only when a touch and no campaign send put the contact at sent (so a
   relationship touch reads distinctly from a campaign send). **8 contacts.**
2. **GA + deliberate holds → "Held".** New `suppress_reason='held'` (revisitable,
   ranked below the consent reasons + exclusion tiers). Held signal:
   `tier='GA'` / `dirk_notes='GA'` / `next_step` matches
   `on hold|do not send|excluded|covered by`. Transient holds (OOO,
   awaiting-decision, scheduling) stay active. **44 contacts; active board
   124 → 80.**
3. Off-board contacts now read WHY (Held / Do not contact / Excluded); board
   gains "Reached (Dirk)" + "Held" filter chips and buckets.
4. **Verified:** 37 tests (was 18, +14 iteration-2, +5 capture). Re-migration
   against the live master sheet moved counts exactly as predicted; TestClient
   rendered the board + a reached page + a held page.

### Live reload + verification
5. Overwrote the volume DB with the fresh iteration-2 migration (290 contacts /
   193 events / 44 held / 38 touch). First inspected the live DB and confirmed
   the only non-import events were 4 smoke-test artifacts on one contact
   (verification residue), safe to wipe.
6. Live-verified: board "80 active, 210 suppressed", Reached(Dirk) chip 8, Held
   chip 44, both bucket pages return matching link counts, Rohit Bali contact
   page reads "Reached (Dirk)" with a touch event in the timeline.

### Ship
7. Three commits on `client/brisken/lead-desk` (iteration 2, Phase 2 worker,
   uv.lock regen); PR #213 **merged** (squash `b75d7dc`) on green CI (hooks,
   spell, type/lint/build, Playwright).
8. Iteration-2 code deployed to Fly via `flyctl deploy --depot=false` (depot.dev
   was down); the deployed image equals the merged code.

### Phase 2 (built; gated on Brisken IT)
9. `src/lead_desk/capture.py` + `lead-desk-capture` console script (`capture`
   extra: httpx): app-only Graph reader polls SentItems/Inbox/Calendar → POSTs
   sent/reply/booked to `/events`, idempotent by `internetMessageId`/`iCalUId`
   (fixed lookback, no delta cursor needed). Pure mapping unit-tested (5 tests).
10. `PHASE2-IT-REQUEST.md`: forwardable Brisken-IT request for the Entra app
    registration (read-only Mail.Read + Calendars.Read, mailbox-scoped
    Application Access Policy, tenant aa3bd2bf-…, EU-hosted).

### Housekeeping
11. `infrastructure.yaml` `instances: []` → records the live lead-desk Fly app
    (app/url/region/machine/volume/gate/secrets/Phase-2 dependency).
12. Prepared the vault command + handed the three access codes to the user for
    distribution.

---

## Key Decisions Made

### Iteration-2 classifiers keep stage DERIVED
- **Choice:** `touch` is a new event type the view reads (not a stamped stage);
  `held` is a `suppress_reason` (not a stamped stage). The board columns
  `has_touch` / `has_campaign_send` distinguish a relationship touch from a
  campaign send at query time.
- **Rationale:** preserves the core invariant (stage = f(event log)); a
  correction stays a new event, never an edit.

### Held ranks below consent + exclusion tiers
- **Choice:** in `suppression()`, held is checked last, so a GA contact who is
  also `stop=X` keeps the stronger, permanent `stop` reason.
- **Rationale:** held is revisitable; consent/exclusion is not. The board must
  not soften a permanent do-not-contact into a revisitable hold.

### Overwrite the live DB wholesale
- **Choice:** replace the volume DB with the fresh migration rather than
  in-place migrate.
- **Rationale:** the migration is the authoritative rebuild from the master
  sheet; the only live-only data was 4 smoke-test events (verified, discardable).
  The new SQL views travel inside the DB file, so no in-place view migration.

### Deploy the code now (before merge), from the branch
- **Choice:** deploy iteration-2 code to Fly from the branch so live could be
  verified as step 1, then merge as step 2 (the user's ordering). Fly deploys
  are manual (`flyctl`), not auto-on-merge, so this does not conflict with the
  later merge.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| automations/lead-desk/src/lead_desk/migrate.py | Modified | `is_held` + `dirk_touch` classifiers; wire held into `suppression`; emit `touch` events; report reached/held |
| automations/lead-desk/src/lead_desk/web/store.py | Modified | `touch` event type; `touch`→sent in `contact_stage`; `has_touch`/`has_campaign_send` on board rows |
| automations/lead-desk/src/lead_desk/web/service.py | Modified | Reached(Dirk)/Held/Do-not-contact/Excluded labels; reached+held buckets + filters |
| automations/lead-desk/src/lead_desk/web/templates/{board,base}.html | Modified | Reached(Dirk) + Held chips; chip color variants |
| automations/lead-desk/tests/{test_derivation,test_suppression}.py | Modified | +14 tests (touch→sent, reached label, held classification, transient exclusion) |
| automations/lead-desk/src/lead_desk/capture.py | Created | Phase 2 Graph capture worker |
| automations/lead-desk/tests/test_capture.py | Created | +5 mapping tests |
| automations/lead-desk/PHASE2-IT-REQUEST.md | Created | Forwardable Brisken-IT Entra request |
| automations/lead-desk/{BLUEPRINT.md,pyproject.toml,uv.lock} | Modified | Iteration-2 + Phase-2 record; capture extra + script; lock regen |
| workspace/clients/brisken/infrastructure.yaml | Modified | `instances:` records the live lead-desk app |

---

## Current Status
- **LIVE + verified:** https://brisken-lead-desk.fly.dev — iteration-2 code + DB.
  Board: 80 active / 210 suppressed; Reached(Dirk) 8; Held 44. Machine
  `2869e67c347558` (fra, scale-to-zero), image `deployment-01KXB3…`.
- **PR #213 MERGED** (squash `b75d7dc`); all commits on main.
- **Phase 2 worker built**, does not run until Brisken IT issues the Entra
  credential.
- Platform (expense-recon p1): no `platform`-section ops tier to report; the
  lead-desk is a standalone Fly app, not a metered orchestrator instance.

---

## Next Steps
1. **Send `PHASE2-IT-REQUEST.md` to Brisken IT** (via Dirk). Nothing in Phase 2
   runs until the Entra app registration + mailbox-scoped credential land.
2. **Deploy the capture worker** once creds arrive: scheduled Fly Machine on the
   same image (`flyctl machine run . --schedule hourly --entrypoint
   lead-desk-capture`), secrets = tenant/client-id/secret/mailbox. Verify with
   `--dry-run` first.
3. **Distribute + vault the access codes** (user action): the three codes are in
   the working notes; vault line is prepared.
4. **Iteration-2 backlog (owner picks first):** ITERATION-2-PROMPT.md §2 —
   scheduled value-radar digest (highest ROI/low effort), Zoho read-sync,
   send-from-the-desk, reply triage.
5. **Retire the Planner lead-gen bucket** now that the Lead Desk is the board of
   record (recommended in BLUEPRINT open items).

---

## Context for Next Session

### Files to Read First
- workspace/clients/brisken/automations/lead-desk/BLUEPRINT.md (architecture + iteration-2 + Phase-2 state)
- workspace/clients/brisken/automations/lead-desk/PHASE2-IT-REQUEST.md (the IT ask)
- workspace/clients/brisken/automations/lead-desk/ITERATION-2-PROMPT.md (§2 integration backlog)
- ~/.claude/.../memory/project_brisken_lead_desk.md (deploy topology, reload gotcha, secrets)

### Open Questions
- Which §2 integration to build first (scheduled digest recommended)?
- Retire the Planner lead-gen bucket outright, or keep a hand-run coarse mirror?

### Working Notes
- **Reload gotcha (cost ~30 min this session):** the Fly machine scale-to-zeros,
  and `flyctl ssh console` to a STOPPED machine fails outright ("no started
  VMs"). A blind retry loop just races the shutdown. Correct sequence:
  `flyctl machine start <id>` FIRST, then `base64 -w0 <db> | flyctl ssh console
  -C "sh -c 'base64 -d > /data/lead-desk.sqlite'"`, then verify the in-container
  event count, then `flyctl machine restart`. All in one connected run.
- **Network flap:** GitHub, depot.dev, pypi, api.fly.io all intermittently timed
  out for ~40 min mid-session; they recover independently. `flyctl deploy
  --depot=false` uses Fly's native builder when depot.dev is down. Push/lock
  retries landed on their own.
- **Pre-existing data note (NOT iteration-2 scope):** the 89 ANON booth-scans
  migrate as `suppress_reason='no_consent'` (their status text says "no
  consent"), not `anon`. Confirmed identical in the baseline — a pre-existing
  migration behavior, left as-is. Flag if the "Excluded (anon)" vs "Do not
  contact" distinction matters to Dirk.
- **Access codes** (login https://brisken-lead-desk.fly.dev): matthias
  `mts-bcf42010`, dirk `dnk-11fcf435`, chris `chr-36b0019f` (also in
  `.scratch/ld_secrets.env`).
- Local iteration-2 DB kept at `.scratch/ld-iter2/lead-desk.sqlite` for re-upload.

### Reference Materials
- Live: https://brisken-lead-desk.fly.dev
- PR (merged): https://github.com/011matthias/agentic-ops1.01/pull/213
- Phase-1 checkpoint: docs/2026-07-12 - Brisken Lead Desk Build/Checkpoint.md

---

## How to Continue
The board is live and correct. To advance toward "Dirk runs it without Matthias":
(1) get the IT request sent and the capture worker deployed (removes the manual
logging burden), then (2) build the scheduled value-radar digest so the board
pushes to Dirk instead of waiting to be opened. Reload the DB (if re-migrated)
via machine-start-first + base64|ssh + restart.

---

## Strategic Feedback

### What Worked Well This Session
- Calibrating the classifiers against the real sheet BEFORE writing regexes (the
  `.scratch/inspect_master.py` distribution pass) meant the counts moved exactly
  as predicted and the "8 reached / 44 held" targets were hit first try.
- Working the network flap in the background (retry loops for push + reload)
  while doing unblocked local work (Phase-2 worker, IT request, infra.yaml) kept
  the session productive instead of stalled on the outage.

### Suggestions
- The DB reload is now a recurring manual operation (Phase 1 + this session).
  Worth a `tools/lead-desk-reload.sh` that does machine-start → base64 upload →
  verify count → restart, so the scale-to-zero footgun can't recur.

### System Health
- **Recurring B1 closing-offer reflex** fired again on the final response
  ("say the word if you want me to draft…"); stop-b1-gate caught it. This is the
  most-logged friction class in the register (structural backstop holds; the
  generation-time reflex persists). No new fix — the hook is the working control.
- **Reload footgun (B3 attribution):** ~30 min lost to blaming the network flap
  when the compounding cause (machine scale-to-zero) was agent-controllable and
  had already surfaced ("no started VMs") earlier in the session. The
  machine-start-first fix is now in memory; a reload helper would make it
  structural.
- Autonomy score: 2 self/hook-detected friction events, 0 user corrections
  (the user's one mid-turn message added the "why", it did not correct an error).
