# Checkpoint: WW W2-14 Duplicate Test Run

**Date:** 2026-10-12
**Status:** Internal rehearsal of the Monday walkthrough done on the duplicate; duplicate rebuilt for today's session with Tobias and Sabine (release-6 code, company recipients); cleanup after that session pending.

---

## Summary
Owner rehearsed the full W2-14 sales flow by hand on an internal copy of the workflow ("W2-14 - duplicate", n8n `tB5anuCbpmYsrA7K`) against test project HUK-106489, mirroring runbook §7-9. The rehearsal found two production bugs in the original (Hero appointment times read as UTC; R20 task title rejected by Hero for `;`), which a separate fix session addressed; the duplicate now carries both fixes for today's session.

---

## What Was Done This Session

### Read-only explanation work (start)
1. Extracted the 9 sticky notes of W2-14 (release 4, `7ec5e029`) verbatim from the tracked export, confirmed live = export (GET), wrote a German flow description for Tobias/Sabine, then explained run types, rule checks, step entry, Altbestand, skip-protocol location, and the action table per rule in plain words.

### Duplicate made internal + manual rehearsal
1. Duplicate: test-only recipients/users, own data table (seeded with the original ledger's 13 rows because `LEDGER_MINDEST_ZEILEN = 13`), schedule node disabled, `errorWorkflow` set to `""` (PUT without the key does NOT clear it), activated; zero-action acceptance run green.
2. Starter `.scratch/ww-sales-72627/tools/testlauf-duplikat.mjs` (gitignored, WW clone): reuses `testlauf()`/`mitSperre()` from `tools/ww-vertrieb-release-72627.mjs` (same safe windows, same lock, same flags) against the duplicate's webhook; refuses unless the published duplicate matches the intended config; `--abnahme`, `--stopp`.
3. Owner ran the flow step by step (PowerShell `function T`), agent verified each step via n8n API, Hero GraphQL (owner's key, read guard) and iCloud IMAP. 21 of 23 rules behaved as specified (R1-R13, R15-R19, R22, R23, R3, send guard, Testuhr, rule filter); R20 failed (Hero 422), so R21 was not reachable; R14 offline only.
4. Cleanup: 13 TEST tasks soft-deleted (`update_task {id, is_deleted:true}`, probed on one first, 13/13 read back), HUK-106489 back to Neue Projekte, duplicate deactivated, test table deleted.

### Bugs found, handed to a separate fix session (prompts delivered in chat)
1. Hero `calendar_events.start/end` are Berlin wall-clock labelled `+00:00`; W2-14 rendered a 10:00 appointment as 12:00. Fixed in original **Release 5** (`0f6e58df`, live 2026-10-11 22:28 UTC, acceptance 52237).
2. Hero rejects the R20 task title (`_noSpecialChars`, 422) because of `;` (only `;` and `ü` were unique to that title; ä/ö/`:`/`,`/`()`/`.`/`-` pass). Fix committed (`8b49e5e`, candidate-r6) but **Release 6 not published** (window closed 06:00).

### Duplicate rebuilt for today's session (owner decision)
1. Kandidaten/Faellige Aktionen/Aufgabenversuch nodes taken from `candidate-r6.json` (both fixes), recipients = company test list (Sabine, Tobias, iCloud), Vertrieb tasks → Tobias 255830, rest → Sabine 255797, new test table `nnnYVH7709ySG347` (13 seed rows, hash-equal), schedule off, no error alert, active (`b7d94a8c`); acceptance run 52412 green. Starter asserts updated to this state.

### System
1. Pattern rule `block-grep-no-ignore` (see friction).

---

## Key Decisions Made

### Rehearse on a duplicate, not the original
- **Choice:** Owner-made copy, internal-only first, then company recipients for the real session.
- **Rationale:** Original is under release discipline (windows, pins, acceptance); the duplicate can be changed today without touching it.

### Use the duplicate for today's session with release-6 code
- **Choice:** Run today's walkthrough on the duplicate, not the original.
- **Rationale:** Original still has the R20 bug until Release 6 (earliest 20:00); runbook 8.12/8.13 would go red and alert Nicolas.

### Tasks go to Sabine/Tobias today
- **Choice:** Montag recipients and role mapping.
- **Rationale:** Ticking a task is the trigger for R8/R11/R16/R19-R21/R23; they should tick in their own lists while Matthias starts the runs.

---

## What Did NOT Work (and why)
- **PUT /workflows with `errorWorkflow` omitted:** n8n kept the old value (settings are merged); had to send `errorWorkflow: ""`.
- **Empty test data table:** W2-14 throws "vertrieb_log liefert 0 Zeilen, mindestens 13 erwartet" (read-failure guard); seeded with the original's 13 rows.
- **Hero `project_matches(ids:[…])` on an archived project:** returns nothing; use `project_match(project_match_id:)`.
- **Introspecting `ProjectStatusStep` via `__type`:** returned no fields; query `type { project_status_steps { id name } }` directly.
- **`grep -r --no-ignore … 2>/dev/null`:** ripgrep-only flag, GNU grep exits 2, silent empty result (now blocked by pattern rule).
- **Setting a Hero status by clicking the status field twice:** the UI jumps one entry further (Neue Projekte → Planung 23 s later).
- **Appointment created with category Umsetzung, changed afterwards:** W2-06 had already fired and set a Wiedervorlage on the then-current status.
- **Bash call with heredoc + `cd`:** cd-guard rewrote it, auto-mode classifier gave no verdict; ran the script from a file without `cd` instead.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `agentic-ops/.scratch/ww-sales-72627/tools/testlauf-duplikat.mjs` (WW clone, gitignored) | Created/edited | Test-run starter for the duplicate |
| `.claude/patterns/block-grep-no-ignore.md` | Created | Block grep with ripgrep-only `--no-ignore` |
| n8n `tB5anuCbpmYsrA7K` + data tables | Edited (live) | Duplicate config; tables `D1LdrenDW56hL7Xx` (deleted), `nnnYVH7709ySG347` (current) |
| Hero HUK-106489 (12189161) | Edited (live) | Status moves, ~20 `[TEST]` logbook lines (not deletable), tasks soft-deleted |
| memory: `reference_ww_hero_api_quirks.md`, `feedback_manual_walkthrough_one_step.md` | Created | Hero API facts; walkthrough guidance |

---

## Current Status
- Original W2-14: active, Release 5 `0f6e58df`, test mode, ledger 13 rows. Release 6 (R20 `;`) prepared in the fix session, needs a new owner yes, window from 20:00 Berlin.
- Duplicate: active `b7d94a8c`, release-6 code, company test recipients, table `nnnYVH7709ySG347`, schedule off, no error alert. Ready for today's walkthrough (runbook §8 run sheet in chat).
- HUK-106489: Neue Projekte (entry 2026-10-12 07:04 UTC), no open TEST task, no appointment.
- warme-wimmer has no `infrastructure.yaml`/comms-log in this repo (lives in the agentic-ops clone).

---

## Next Steps
1. After today's session ("fertig"): soft-delete all TEST tasks on HUK-106489, move it back to a rule step (Neue Projekte), deactivate the duplicate, delete table `nnnYVH7709ySG347`.
2. Release 6 on the original from 20:00 Berlin with owner yes (fix session runbook §5e); preconditions: lock free, HUK-106489 in a rule step, session finished.
3. Decide whether the duplicate stays (inactive) or is deleted.
4. Fix note "3 Entscheiden" (still references the removed header note) in the next release.

---

## Context for Next Session
### Files to Read First
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops\.scratch\ww-sales-72627\release-runbook.md` (§7-9 walkthrough, §5d/5e releases)
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops\.scratch\ww-sales-72627\tools\testlauf-duplikat.mjs`

### Open Questions
- Is `ü` allowed in Hero task titles? (`;` is the likely culprit; not proven by a controlled test.)
- What held `w214-testlauf.lock` between 01:23 and 05:30 Berlin? The last duplicate run ended 01:22; the fix session reported the lock never free for 5 min until 03:30 UTC (machine sleep suspected).

### Working Notes
- Hero status names: sidebar groups are global status codes ("Neu - Erstkontakt" = 201); inside the project the type's steps show (🆕 Neue Projekte, ✒️ Planung, …). Test project type is "Wärmepumpen 2.0 Test" (72627); HUK-106508/103831 are the real type 13293.
- `--bis-ruhe` sequences: logbook first, status move next run ("Wechsel wartet"), then the new step's actions, then 0.

### Reference Materials
- n8n duplicate `tB5anuCbpmYsrA7K`, original `NPHbbRF2NVAbUyzF`; WW fix PR #305 (agentic-ops).

---

## How to Continue
Wait for the owner's "fertig" after the session, then run the cleanup (step 1) with readback, and leave Release 6 to the fix session.

---

## Strategic Feedback

### What Worked Well This Session
- Verify-after-every-step (n8n execution, test ledger, Hero, IMAP) caught the status-field jump, the unticked task, a stale lock and both production bugs before Monday.

### Suggestions
- For any W2-14 test, start from runbook §7-9 and build the duplicate/starter around it instead of drafting a new plan.

### System Health
- Autonomy score: 5 human interventions (redirect to the Monday flow, two requests for clearer steps, two Hero navigation screenshots).
