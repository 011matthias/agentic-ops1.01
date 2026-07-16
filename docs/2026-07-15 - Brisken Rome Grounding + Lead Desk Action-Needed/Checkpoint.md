# Checkpoint: Brisken Rome Grounding + Lead Desk Action-Needed

**Date:** 2026-07-15
**Status:** Complete + verified live

---

## Summary
Ground the TAC Rome 2026 master contact sheet against every source (mailboxes, calendar, Zoho, Lead Desk, Sales Nav) — 51 non-destructive cell writes across both tabs, backed up and diff-verified — then re-synced the Lead Desk off the grounded sheet and shipped a board UX feature: a clickable "Action needed" badge with a recommended-action detail modal, plus clarified bucket labels. Merged (PR #227), deployed to Fly, live-verified.

---

## What Was Done This Session
### 1. Master-sheet grounding (read-many, write-blanks-only)
1. Built `.scratch/rome_ground.py`, one re-runnable pipeline joining the sheet (both tabs, app-only Graph) by email against: both mailboxes (Sent/Inbox/Drafts app-only), calendar, Zoho CRM, Lead Desk mirror.
2. Wrote **24 blank-fills** (20 `crm_last_activity` from Zoho, 1 `last_outreach` + 2 `last_reply` from mailbox, 1 `E3_response` = Askew's unrecorded reply) + **7 `last_outreach` corrections** (sheet showed the E1 date; mailbox proved later E2/E3/post-event sends) + **20 consistency writes** (cleared a stray `(`, fixed 2 statuses to "Replied - action needed", propagated 10 booked calendar meetings into `next_step` + `email outreach_status`="In conversation").
3. **51 cells total**, delegated Files.ReadWrite token, `PRE-GROUND-BACKUP-2026-07-15-...xlsx` + whole-sheet diff-verify (0 collateral each pass).
4. Re-synced the Lead Desk (`POST /sync`): contacts 338, events 182→197, app-owned `next_step` preserved, no sends.
5. Scanned both inboxes for recent replies: 4 Rome replies (Szczecina, Asako, Uffe, Thomas) all captured; Dominic Oberlander (JTI) + kazuya.tazoe (NYK) surfaced and left as thread participants only (owner: "no need, keep them in the thread record").

### 2. Lead Desk board feature (PR #227)
1. `service.recommended_action(row, today)` → concrete next action for contacts owing one (Replied-needs-reply / past-due follow-up / aging reply); attached to `board_rows` + `build_contact_view`.
2. Board Status cell → clickable "Action needed" badge opening a self-contained detail modal (no deps); contact page → "Action needed" callout.
3. Clarified all bucket chips with plain-language `title=` tooltips; renamed "Awaiting reply" → "Awaiting their reply" (chip + `status_label`); "Held" tooltip = deliberately-parked revisitable outreach.
4. Fixed a pre-existing repo-wide time-bomb in `test_outbox` (real-clock `enrolled_at` vs fixed 2026-07-15 reply timestamps).
5. 145 tests; CI green on both commits; merged (squash `3077b10`); `flyctl deploy` to `brisken-lead-desk`; live-verified 8 action buttons render with real actions (Christos Georgiou "Reply to their latest message.", etc.), modal + contact callout + labels all live.

---

## Key Decisions Made
### crm_owner NOT grounded from Zoho
- **Choice:** Dropped `crm_owner` grounding entirely (would have written "Dirk Neumann" to 233 cells + 17 false conflicts).
- **Rationale:** The Zoho Self-Client connection returns "Dirk Neumann" as Owner for ALL 1443 contacts + 465 accounts (uniform, the connection user). The sheet's existing `crm_owner` (real reps) is the better source. Caught by verify-before-write.

### Calendar meetings → "In conversation" status
- **Choice:** Bumped 10 contacts with a booked Brisken meeting to `email outreach_status`="In conversation" (from blank/"Not contacted"/"awaiting reply").
- **Rationale:** A booked meeting is the strongest signal a lead is engaged; "Not contacted" beside a confirmed meeting is exactly the inconsistency the owner asked to fix. All logged + reversible.

### Fixed the test_outbox time-bomb rather than merge-anyway
- **Choice:** Root-fixed the pre-existing time-dependent test failure (not mine) instead of shipping past a red CI.
- **Rationale:** It blocks CI repo-wide as of today; the fix is small, correct, and intent-preserving.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| SharePoint `TAC Rome2026-...DN-Edits.xlsx` | Modified (Graph) | 51 non-destructive cell writes (both tabs), backed up + diff-verified |
| `.scratch/rome_ground.py` | Created | Re-runnable all-source grounding + consistency + replies pipeline (gitignored scratch) |
| `lead-desk/.../web/service.py` | Modified | `recommended_action()`; `status_label` rename; attach to board/contact |
| `lead-desk/.../web/templates/board.html` | Modified | Action-needed button + detail modal + chip tooltips |
| `lead-desk/.../web/templates/contact.html` | Modified | Action-needed callout |
| `lead-desk/.../tests/{test_derivation,test_webflow,test_outbox}.py` | Modified | 7 new tests + time-bomb fix |
| Prod Fly `brisken-lead-desk` | Deployed | Image `01KXK68V`; feature live |

---

## Current Status
- **Master sheet:** fully reconciled + grounded; single source of truth; rollback = `PRE-GROUND-BACKUP-2026-07-15` + version history.
- **Lead Desk:** live at `brisken-lead-desk.fly.dev`; board reflects the grounded truth (events 197); action-needed feature + clarified labels deployed + verified. No-send kill switch untouched.
- Platform: n/a for this work (Lead Desk = FastAPI on Fly, not Make/n8n).

---

## Next Steps
1. Owner-requested: run an **overall functionality + usability audit on the Lead Desk** (audit prompt authored this session — paste it into a fresh session).
2. Decide whether to automate mailbox→sheet gap-fill as a periodic tool or keep it manual.
3. Ian Haegemans has a stale `next_step` ("No reply yet") beside an accepted 07-17 meeting — one-line owner edit.
4. LinkedIn URL gap (234 blank on the sheet) needs a live Sales-Nav CDP read if wanted (not driven autonomously against the live LinkedIn seat).

---

## Context for Next Session
### Files to Read First
- `~/.claude/.../memory/project_brisken_lead_desk.md` (2026-07-15 entries: sync gotcha + action-needed feature)
- `~/.claude/.../memory/project_brisken_rome_master_contact_sheet.md` (2026-07-15 grounding pass + gotchas)
- `.scratch/rome_ground.py` (the grounding pipeline, re-runnable)
- Lead Desk: `workspace/clients/brisken/automations/lead-desk/src/lead_desk/web/{service.py,templates/board.html}`

### Open Questions
- Automate mailbox→sheet gap-fill periodically, or keep manual?
- Should the calendar→board link (meeting → "In conversation") eventually flow through the gated Phase-2 capture worker rather than the sheet?

### Working Notes
- **Graph workbook readback LAGS** ~1s after a PATCH (shows old/empty value); trust the whole-sheet diff, not the immediate readback.
- **`@microsoft.graph.downloadUrl`** reflects live workbook writes immediately even though the driveItem `lastModifiedDateTime` (sync report's `source_modified`) lags hours.
- **`POST /sync` needs a logged-in cookie** (login with an access code), NOT the ingest secret — the `require_login` middleware only exempts `/events`.
- **`email outreach_status` uses `-` as a valid dropdown value** (No channel/NA); a hold-detector doing `"-" in status` wrongly flags every hyphenated status — match `-` as the exact whole value. (Caught pre-apply via B3.)
- **`gh pr merge` on a self-authored PR** is blocked by the auto-mode classifier even under a "deploy" order — needs an explicit "merge".
- Worktree `agentic-ops1-lead-desk` is on the merged `client/brisken/lead-desk-action-detail` branch (was on the closed-#226 branch); harmless, can be cleaned.

### Reference Materials
- PR: https://github.com/011matthias/agentic-ops1.01/pull/227
- Live app: https://brisken-lead-desk.fly.dev/

---

## How to Continue
Master-sheet grounding is closed out (owner confirmed). For the Lead Desk, the next owner-requested step is the functionality + usability audit — the runnable prompt is in the checkpoint's companion (this conversation's final message). To re-ground the sheet later, `uv run .scratch/rome_ground.py {sheet|mail|calendar|reconcile|consistency|replies}` then the write/verify steps.

---

## Strategic Feedback

### What Worked Well This Session
- Verify-before-write caught two would-be data-corruption bugs (the uniform-Zoho-owner trap; the `"-"`-substring hold bug) before either touched the live sheet — the diff-verify-every-write discipline paid off directly.
- Auditing (read-only) before applying the consistency writes surfaced that 42 "garbage" cells were actually valid `-` statuses — one audit pass avoided wrongly clearing them.

### Suggestions
- The calendar→board signal (a booked meeting) is high-value but currently only reaches the sheet, not the Lead Desk board (status isn't a board column; `next_step` is app-owned). Getting the gated Phase-2 capture worker its IT creds would close this permanently.

### System Health
- The `.scratch/rome_ground.py` pipeline is genuinely re-runnable and would make a good `tools/` promotion if mailbox→sheet grounding becomes periodic (currently gitignored scratch).
- Autonomy score: 2 human interventions this session (both B1 closing-offer deferrals, hook-caught + corrected). The recurrent closing-offer generation reflex persists; the stop-b1-gate hook holds every time.
