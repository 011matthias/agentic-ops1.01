# Checkpoint: Expense-Recon Front 4 Copies Part 2

**Date:** 2026-09-27
**Status:** item 223 steps 4, 5 and 7 live (PR #1480, `382b2a35`). Step 6 and feedback note #97 open. Three Lovable prompts wait for the owner's paste.

---

## Summary
Front 4's last buildable steps shipped as one PR, built by this session plus two builder subagents, with an owner-approved A/B gating the extraction change. After the mini-checkpoint the session audited every Lovable prompt against the published bundle and cleared one of the two new feedback notes with an owner-approved settings write.

---

## What Was Done This Session

### Item 223 (PR #1480, Fly `382b2a35`)
1. **Step 4:** `document_kind` added to the extraction schema only. The kept copy reads it first. A reminder is never kept, and on its own it asks for review (`reads_as_reminder`). The extraction fingerprint was re-pinned.
2. **Step 5:** billing-account keys across months, stored at re-match and at a no-statement receipt add, plus the `cross_month_copies[]` advisory. Built by a subagent.
3. **Step 7:** `POST /api/runs/{id}/duplicates/reapply`, with a dry run that writes nothing. Built by a subagent.
4. **Verification:**
   - Merged suite: 4015 passed.
   - Bite proofs: 5, 27 and 15, one per wiring point.
   - Live: route probe, dry runs on September and July, and a cold CDP drive.

### After the mini-checkpoint
1. **Prompt audit:** 13 prompts that `PROMPT-STATUS.md` called "not pasted" are live, and their rows were corrected (PR #1494). Still to paste:
   - `lovable-attach-month-filter-prompt.md`
   - `lovable-statement-colour-prompt.md`
   - the `duplicates_reapply` line of `lovable-copies-kind-prompt.md`

   All three were handed to the owner in chat.
2. **Feedback store** (98 notes): #98 was written on the owner's yes. #97 is open. Every other note is already cited in the backlog. The addendum landed in PR #1498.
3. **New pattern rule** `warn-git-write-after-script-semicolon` (see Friction).

---

## Key Decisions Made

### Extraction A/B budget
- **Choice:** the full four passes on the 09-25 backup, hard stop at $4; the owner chose it. The actual cost was $2.32.
- **Rationale:** gpt-5-mini reads the photos and mail bodies, which is where readings drift. A text-only run would not have answered the question.

### Ship step 4 despite one currency move
- **Choice:** ship. The owner chose it after seeing the slip.
- **Rationale:** the slip prints no currency. The new reading is null, which asks a person; it never produces a wrong value.

### Document kind before the printed numbers
- **Choice:** `payment_document_kind` asks `document_kind` first.
- **Rationale (A/B):** the kind was right on 57 of 57 Stripe files. The numbers call 33 real receipts invoices.

### One PR for three steps
- **Choice:** the step 5 and step 7 branches were merged into the step 4 branch, with one suite run and one deploy.
- **Rationale:** one CI run and one deploy instead of three. The cost was three rounds of conflicts with siblings.

### July reapply
- **Choice:** leave July (owner). No write.
- **Rationale:** a real reapply is a full re-match of Criss's month. The dry run cannot preview matcher changes.

### Note #98
- **Choice:** alias `nicolas` → "Nicolas Neumann" (owner yes). Readiness check first, then a whole-settings diff after.

---

## What Did NOT Work (and why)
- **Sizing the A/B from the app's cost tracker:** gpt-5-mini is priced at $0 in `llm/cost.py`. The real cost was about $0.58 per pass against the brief's $0.02 (item 227).
- **Asking the printed numbers first:** see Key Decisions (33 receipts misread as invoices).
- **`gh pr merge` chained after a CI wait:** the gate reads CI before the command runs and refused the merge (a repeat of 2026-09-25).
- **A resolver script followed by `;`:** the failed assertion still let `git add`, `commit` and `push` run. Conflict markers were pushed in `f2c56eb4` and fixed in `139c82ff`.
- **Expecting September's 12 swaps:** a natural re-match at 2026-09-26 21:06 had already applied them.
- **Parsing the vault output as JSON:** it is labelled lines, and the `notes` line matched "code". Read the `operator_code:` line only.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `…/src/expense_recon/llm/client.py` | edit | `document_kind` in the schema, parser |
| `…/src/expense_recon/duplicates.py` | edit | kind-first reading, reminder never kept (step 5 `account_keys` threading) |
| `…/src/expense_recon/web/service.py` | edit | `reads_as_reminder` review (step 5 stored keys) |
| `…/src/expense_recon/web/duplicate_reapply.py`, `web/app.py` | new/edit | step 7 route |
| `…/src/expense_recon/matching/types.py`, `web/serialize.py`, `ingest/receipts_folder.py` | edit | carry `document_kind` |
| `…/tests/test_document_kind_front4_step4.py`, `test_cross_month_account_keys_step5.py`, `test_duplicates_reapply_step7.py` | new | route-level tests |
| `…/tests/test_extraction_prompt_pin.py`, `test_view_contract.py` | edit | re-pin; review code, advisory field, trigger |
| `…/docs/api-contract.md`, `PROMPT-STATUS.md`, `lovable-copies-kind-prompt.md` | edit | contract sections, ledger, trigger label |
| `workspace/clients/brisken/status/p1-improvement-backlog.md`, `p1-expense-reconciliation.md` | edit | item 223, item 227, Shipped rows 148-150, status |
| `.claude/patterns/warn-git-write-after-script-semicolon.md` | new | pattern rule |
| Live settings `intake.aliases` | write | note #98 (owner yes) |

---

## Current Status
- **Live:** Fly at `382b2a35`. No live row moved at deploy.
- **July:** 0054 (BRL 340.00) leaves the count at July's next natural re-match.
- **Nicolas:** receipts mailed to nicolas@expenses.brisken.com are now attributed to Nicolas Neumann.
- **Ops status:** platform unknown (`infrastructure.yaml` has no assessed platform plan).
- **Comms:** last contact 2026-09-24, not stale.

---

## Next Steps
1. **Note #97:** read the published month filter / summary component and the payload counts. Itemize the note, write the Lovable prompt and its PROMPT-STATUS row, and hand it over in a four-backtick fence.
2. **Item 223 step 6:** record `intake_provenance.twin_of` at arrival (`web/intake_mail.py` part filter ~560-600), and have the ladder start from it.
3. **Optional, item 227:** add the gpt-5-mini price and a test that every configurable model has one.
4. **After the owner publishes:** re-run the bundle key check for the three pending prompts.

---

## Context for Next Session

### Files to Read First
- `docs/2026-09-27 - Expense-Recon Front 4 Copies Part 2/Mini-Checkpoint-1.md` (continuation prompt plus addendum)
- `workspace/clients/brisken/status/p1-improvement-backlog.md`: item 223, item 227
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`: the last three sections

### Open Questions
- None for the owner. The three prompts are simply waiting to be pasted.

### Working Notes
- **Feedback store:** the note text is the `comment` field of `/feedback.jsonl`. The latest cited note is #98.
- **Live-check scripts** in the main clone's `.scratch`:
  - `recon-reapply-dryrun.py`
  - `recon-cold-drive-months.py` (month route `/expenses/{run_id}`; the only non-GET calls are Lovable analytics beacons)
- **Settings writes:** `PUT /api/settings` takes one group per request, and a whole-group round-trip is safe.

### Reference Materials
- PRs #1480, #1490, #1494, #1498. Fly `brisken-expense-recon` at `382b2a35`.

---

## How to Continue
Paste the continuation prompt from `Mini-Checkpoint-1.md` (the version in the chat's last reply, whose queue starts with note #97) and start `/comd_resume brisken`.

---

## Strategic Feedback

### What Worked Well This Session
- **Parallel subagents:** two builder subagents ran in their own worktrees while an A/B subagent measured the extraction change. My context stayed within budget, and every builder report came with named tests and bite proofs I could merge directly.
- **Budget gate:** the A/B subagent's estimate step ($1 cap) caught a ten-times cost error before any money was spent.

### Suggestions
- Upgrade `warn-merge-chained-after-any-command` from warn to block. It has now repeated on 2026-09-25 and 2026-09-27; a warn on the same call does not stop the merge being chained.

### System Health
- Siblings merge into main every few minutes. PR #1480 needed three rounds of merging main before it went in, and each re-run of the module suite (about 10 minutes) left a fresh window for the next conflict. A merge queue, or relying on CI for suite re-runs after conflicts that touch only docs, would shorten this.
- **Autonomy:** 4 human interventions, all owner decisions on spend and live writes (A/B budget, ship with the currency move, July reapply, the #98 write). Elevated by count, but no unblocking was needed.
