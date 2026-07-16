# Checkpoint: Brisken Lead Desk Campaign Engine

**Date:** 2026-07-14
**Status:** SHIPPED + LIVE. Iteration 3 (campaign engine) + two-gate sending confirm deployed to prod; TEST-campaign gate passed live end-to-end. Production standby: outbox armed, worker on schedule, nothing armed to send.

---

## Summary
Turned the Brisken Lead Desk from a passive tracker into a full campaign engine (upload leads → warmness degrees → predetermined cadences → local Windows worker auto-sends via Outlook COM, stops on reply/bounce, BCCs the Zoho dropbox), then ran the whole send gate LIVE (real self-only sends, kill switch, NDR→suppress, reply-halt), and finally split sending behind an explicit in-app confirm (approve freezes; "Start sending" arms). Two PRs merged + deployed; a live board bug (dead Active/Clear buttons) fixed along the way.

---

## What Was Done This Session

### 1. Access code
- Set Matthias's Lead Desk access code to `mn040307` (Fly secret `LEAD_DESK_ACCESS_CODES`, preserving Dirk/Chris); verified new code logs in (303 + cookie), old code 401s.

### 2. Iteration 3 — campaign engine (PR #217, merged + deployed)
- **Brain (Fly app):** new tables — campaigns, versioned+pinned templates, sequences per degree (`cold`/`cold_touched`/`warm`), data-driven `degree_rules`, `enrollments` (UNIQUE(contact_id,campaign_id) over GLOBAL contacts), `send_attempts` (at-most-once lease lock table). Cadence state = pure function of the log via reserved `ext_key='cadence:{enrollment_id}:{step_no}'`. Upload+classify+approve flow, outbox API (`/api/outbox/claim|result|draft-sent`, `/api/worker/*`) behind a new `LEAD_DESK_WORKER_SECRET` bearer. Board extended (campaign selector, Degree/Step/Next-touch columns, Due/Manual/Stalled chips); campaign admin + contact cadence card. `lead-desk-adopt` (Rome 290 → enrollments under a `done` campaign that can never auto-send).
- **Hands (local Windows worker):** `lead-desk-worker` package (config, journal WAL, api, com_mail, sender, capture_local, cli) + Windows glue (`worker/install-task.ps1`, `run-worker.cmd`, README). Ports the proven Outlook-COM patterns (Recipients.ResolveAll, Dirk-draft loader, Sent-Items readback, inbox Restrict polling).
- **122 tests** (Phase-A suites written via a fan-out workflow; worker unit tests hand-written). HTTP-lifecycle test caught a real bug (leases weren't committed across per-request SQLite connections).
- Deployed to Fly, ran `lead-desk-adopt` on the volume (events + stage distribution byte-unchanged), fixed the live **Active/Clear button bug** (they linked to bare `/` and the filter-persistence script bounced them back to the last filter; new links carry `?campaign=`).

### 3. TEST-campaign gate — passed LIVE (watched session)
- Set `LEAD_DESK_WORKER_SECRET` (Fly + `context/lead-desk-worker/worker.env`); verified auth (200/401).
- Drills, all green on the real system: draft-to-self (COM proof, no send) → real self-only send (2 emails matthias.silva@ → gmail+icloud, Exchange msg-IDs read back, cap accounted) → kill switch (preflight abort) → NDR→bounce→auto-suppress (real Exchange "Unzustellbar") → reply-halt (icloud reply halted its step 2; gmail got step 2).
- Installed `LeadDeskWorker` scheduled task (every 15 min, interactive session, from pinned worktree `agentic-ops1-leaddesk-runner`). Deleted test campaigns + fake contacts (board back to clean 290 Rome / only `rome-2026`).

### 4. Two-gate sending confirm (PR #219, merged + deployed + verified live)
- Split approval from sending: `draft → [Approve: freeze copy+list] → approved → [Start sending: confirm] → sending`. Worker claims ONLY from `sending`. New `cadence.start_sending()`, `enrollment_state` `ready` state, `/campaigns/{id}/start-sending` route, "Sending gate" UI card, board/list banners.
- Fixed two bugs found while wiring it: reply-capture watchlist now includes `sending` (else replies wouldn't halt a live cadence); incremental approval preserves pins for a `sending` campaign.
- **124 tests**; verified live on prod (approve → 0 claims / gate closed; Start sending → status `sending`), then deleted the throwaway campaign.

---

## Key Decisions Made

### Enrollments over composite keys
- **Choice:** Contacts stay global (one person = one row); campaign membership + cadence state live on `enrollments`.
- **Rationale:** Suppression is per-person consent; one timeline; zero rekeying of Rome history.

### At-most-once sends (no auto-retry)
- **Choice:** Expired leases → `stalled` (human Retry/Mark-sent), never auto-resent. Crash reconcile resolves ambiguity toward "assume sent + alert."
- **Rationale:** A duplicate cold email is an unrecoverable reputation cost.

### Hybrid sender (owner decision)
- **Choice:** Cold degrees auto-send from matthias.silva@ (CC Dirk); warm degree staged as drafts in Dirk's mailbox (his click is the gate on his name).

### Two-gate sending confirm (owner: "gate sending with at least a confirm button")
- **Choice:** Approval only freezes copy+list; a separate typed "Start sending" confirm arms the worker.
- **Rationale:** Approval alone should never auto-send; sending needs a deliberate second human action (on top of the three kill switches).

---

## Files Modified
All under `workspace/clients/brisken/automations/lead-desk/` — merged to main via PR #217 then PR #219.

| File | Action | Purpose |
|------|--------|---------|
| src/lead_desk/identity.py | Created | Shared natural_key/contact_id (out of migrate.py) |
| src/lead_desk/web/cadence.py | Created | Rules, render, enrollment_state, claim/result, approve, start_sending, reconcile |
| src/lead_desk/web/uploads.py | Created | CSV/xlsx upload → upsert + enroll + classify |
| src/lead_desk/adopt.py, reconcile_cli.py | Created | Rome adoption + drift reconcile CLIs |
| src/lead_desk/worker/*.py | Created | Local Windows send/capture worker package |
| src/lead_desk/worker (glue: run-worker.cmd, install-task.ps1, README.md) | Created | Scheduled-task glue (dockerignored) |
| src/lead_desk/web/store.py | Modified | Campaign-engine DDL + CRUD + transactional lease |
| src/lead_desk/web/service.py, app.py, auth.py | Modified | Board enrollment join, routes, worker bearer |
| src/lead_desk/web/templates/{board,campaign,campaigns,contact,base}.html | Created/Modified | Campaign UI + sending-gate card + button-bug fix |
| tests/test_*.py (10 files) | Created/Modified | 124 tests |
| BLUEPRINT.md, README.md, pyproject.toml, .dockerignore, uv.lock | Modified | Docs, scripts, worker extra |
| memory: project_brisken_lead_desk.md, MEMORY.md | Modified | Deployed state + gotchas |

**Live infra (not in git):** Fly `brisken-lead-desk` redeployed twice; secrets `LEAD_DESK_ACCESS_CODES` (new Matthias code) + `LEAD_DESK_WORKER_SECRET` set; volume DB adopted; `LeadDeskWorker` Windows task installed; pinned worktree `agentic-ops1-leaddesk-runner`; `context/lead-desk-worker/worker.env`.

---

## Current Status
- Live at brisken-lead-desk.fly.dev. Board clean: 290 Rome contacts, only `rome-2026` (status `done` — can never auto-send).
- Outbox armed (`LEAD_DESK_WORKER_SECRET` set) but **nothing armed to send**: a final claim returns 0. Scheduled worker ticks every 15 min, self-guards when Outlook closed / kill on, idles until a real campaign is approved AND started.
- Sending requires TWO in-app confirms (approve, then Start sending) on top of three kill switches (app flag, `context/lead-desk-worker/KILL` file, `schtasks /Change /TN LeadDeskWorker /DISABLE`).

---

## Next Steps
1. **First real campaign** (when ready): upload a real list → approve (freeze) → Start sending (confirm). Each is a deliberate typed confirm. Watch the first live window.
2. **Verify Zoho dropbox FILING** on the first real send — test recipients weren't CRM contacts, so filing was never actually confirmed (only the BCC wiring).
3. **Phase 2 Graph capture** still gated on Brisken IT creds (Entra app + Mail.Read + Calendars.Read + mailbox RBAC); forwardable ask at `PHASE2-IT-REQUEST.md`.
4. Optional: teach `migrate.py` to read Dirk's `emails_sent`/`post_event_outreach` sheet columns, OR rely on the capture worker, so Lead Desk mirrors the SharePoint sheet's outreach state (see parallel-session note in memory).

---

## Context for Next Session

### Files to Read First
- `~/.claude/.../memory/project_brisken_lead_desk.md` (full deployed state + gotchas)
- `workspace/clients/brisken/automations/lead-desk/BLUEPRINT.md` (architecture + two-gate model)
- `workspace/clients/brisken/automations/lead-desk/worker/README.md` (worker runbook + kill switches)
- `.scratch/ld_secrets.env` (access codes + worker/ingest secrets, gitignored)

### Open Questions
- Does a Matthias-sent BCC actually FILE in Zoho against a real CRM contact? (Unverified — needs a real lead recipient.)
- Should the recurring worker task run 24/7 in standby, or be enabled only when a campaign is live? (Currently installed + enabled; idles safely.)

### Working Notes
- **Send window gotcha:** claim_sends enforces the campaign's send_window (default weekdays 08:30–17:30 Europe/Berlin). For off-hours testing I widened test campaigns' windows via transparent `flyctl ssh -C "python3 -c \"...update_campaign...\""` (base64-exec is classifier-blocked).
- **curl multipart:** `-F file=@<path>` needs a **Windows** path (`C:/...`); an MSYS `/tmp` path gives curl error 26.
- **Default campaign CC = dirk.neumann@**, BCC = Zoho dropbox. Clear the CC for any TEST campaign so the client isn't emailed.
- **Prod DB edits** (widen window, delete test campaigns, reset leases): transparent `python3 -c` over `flyctl ssh`, single-quoted python strings + parameterized SQL to avoid quoting hell.
- **Two-gate status flow:** draft → approved (frozen, `ready` per-enrollment, 0 claims) → sending (claims) → paused/done. Any copy/sequence edit supersedes back to draft.

### Reference Materials
- PRs: https://github.com/011matthias/agentic-ops1.01/pull/217 , /219
- App: https://brisken-lead-desk.fly.dev
- Runner worktree: `C:/Users/neuma_p1qrsic/Repo/agentic-ops1-leaddesk-runner` (detached at origin/main)

---

## How to Continue
The engine is done, deployed, and safe. To run a campaign: create it in the app (Campaigns page), upload a CSV, confirm degrees, approve (freeze), then Start sending. Nothing sends without both confirms + the worker running (needs classic Outlook open, both mailboxes signed in). To stop everything instantly: the Campaigns-page kill switch, the KILL file, or disable the scheduled task.

---

## Strategic Feedback

### What Worked Well This Session
- Tight directive loop ("go", "go ahead on all", "make sure sending is gated") let the build move fast; each drill was verified live rather than assumed.
- Using a fan-out workflow to write/adapt the test suites in parallel (both the initial 122 and the gate-change fixes) was efficient and kept the source honest.

### Suggestions
- The send-window default (business hours) makes off-hours testing awkward — a per-campaign "test mode / ignore window" toggle in the UI would remove the need to hand-edit the volume DB for a drill.

### System Health
- Autonomy score: 2 human interventions this session (one B1 closing-deferral caught by the stop-b1-gate hook; one curl-multipart slow-path). Both self/hook-detected, not user corrections — the session was otherwise directive-driven and autonomous.
- The permission classifier correctly gated every high-blast-radius action (flyctl secrets, PR merge, prod-DB base64-exec) and cleared on explicit user go-ahead — guardrails working as designed, not friction.
- `agent-deferred` (B1 closing-offer) remains the most-logged friction class across sessions; the stop-b1-gate hook holds each time but the generation-time reflex persists. Structural fix already in place; no new action.
