# Checkpoint: Expense-Recon Month Views Live

**Date:** 2026-09-16
**Status:** Item 79 live and verified; item 23 round 4 backend deletion unblocked

---

## Summary

Backlog item 79 (owner direction: a month's page structured as a receipts overview plus a separate matching overview) went from plan to live in one session. It shipped as a planned walkthrough, two Lovable prompts, two parallel backend fields (Fly v133), and the owner's publish. A bundle audit and a cold browser drive then confirmed the new pages at the expected counts.

---

## What Was Done This Session

### Plan (approved)
1. Drove the published SPA and read the three live months before designing. Found: the two month pages link one way only; `/runs/{id}` crashes on the four statementless months; July's 85 workbook-posted charges look like open work; the 13-tile bar pins 301 of 900 px.
2. Wrote a plain-language walkthrough (September receipt-only, July and August with a statement), 15 owner decisions with recommendations, and a technical appendix. Saved as `~/.claude/plans/plan-the-restructure-of-crispy-wozniak.md`.

### Prompts (PR #899)
1. `docs/lovable-month-views-prompt.md`: a shared month strip with Expenses / Matching tabs. It also adds the statementless redirect (fresh-read guard), five cards in place of the bucket toggles and tile bar, decided rows folded into a record with the existing undo (note #46), the Expenses reconciliation line, and ride-along fixes (SourceBadge "; " split, singulars, em-dashes).
2. `docs/lovable-journal-callers-prompt.md`: the consumer half of item 23 round 4 (three journal callers).
3. An adversarial review confirmed 46 defects in the first drafts, all folded in before merge. Notable ones: a hook below an early return, a stale-cache redirect, the ExpenseRow vendor object, a live Settings Save in the drive.

### Backend (PR #900, Fly v133)
1. Top-level `updated_at` on both review payloads (`service.month_updated_at`, `RunStore.latest_edit_at`).
2. `candidates[].held_by` names receipts held by a pending review row. August `n_charges_receipt_taken` went 0 -> 1.
3. Suite 1832 -> 1844, with every wiring point regress-checked red first. Consumer driven before any paste.

### Records (PR #901, PR #907)
1. #901: backlog item 79 plan + shipped blocks, status element row, PROMPT-STATUS Not-applied rows.
2. #907 (this turn): after the owner published, both prompts moved to Applied with evidence, round 4 marked unblocked, element row LIVE.

### Verification after publish
1. Bundle, 48 chunks / 1,022 KB, controls hitting. Every item-79 key is present (`month.tab.*` in the shared `chunk-ReceiptViewer`, as predicted). Every retired key is absent per chunk. `zoho.csv` and `export_approved_only` read 0 everywhere.
2. Cold browser drive, payloads re-read first:
   - September `/runs` lands on `/expenses` with "Expenses 36 · Add a statement".
   - July cards 14/9, 73/24, 7/0, 1/0, 31/3, with folds 5 copies / 49 / 7 / 1 / 28 posted and view-2 chips 31/18/24/0.
   - July Expenses line "31 matched · 7 need review · 73 charges without a receipt · 14 receipts without a charge · 1 credit".
   - August cards 21/10, 100, 2, 1/0, 8, and "11 decided".

---

## Key Decisions Made

### Restructure before the 73-77 wave, not gated on item 76
- **Choice:** The prompt reads only fields live today and leaves `RowView`, `RowStatusBadge` and the Status cell untouched.
- **Rationale:** Each wave item's SPA half is a caption, cell or grouping inside a card this defines; pasted against the old sections it would move twice.

### Posted rows stay in their card, folded
- **Choice:** Whole counts stay on the cards, with an "{open} open" subline and a "Show decided rows" switch.
- **Rationale:** Counts must agree with the screen. A posted charge with no receipt may still need its receipt.

### Card 4 is "Credits on the statement"
- **Choice:** Never "Refund" until item 73 types the rows.
- **Rationale:** Both live rows are the card payment, and Criss objected to the word (note #42).

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-month-views-prompt.md` | created (#899) | item 79 SPA prompt |
| `.../docs/lovable-journal-callers-prompt.md` | created (#899) | item 23 round 4 consumer half |
| `.../src/expense_recon/web/service.py`, `store.py`, `app.py` | modified (#900) | `updated_at`, widened `held_by` |
| `.../tests/test_receipt_held_by_review.py`, `test_month_updated_at.py`, `test_view_contract.py` | created/modified (#900) | caller-level proofs |
| `.../docs/api-contract.md` | modified (#900) | two parallel fields |
| `.../docs/PROMPT-STATUS.md` | modified (#901, #907) | Not applied -> Applied with evidence |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | modified (#901, #907) | item 79 blocks, round 4 row |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | modified (#901, #907) | element row LIVE |

---

## Current Status

- Item 79 is live on `expenses.brisken.com` and verified by bundle audit and browser drive. The PT pass was not driven.
- Item 23 round 4: the consumer half is live, and the backend route deletion is unblocked and not started.
- Fly `brisken-expense-recon` is on v133 or later (siblings deploy on top).
- PR #907 (records) is open, awaiting CI.
- Pending Lovable prompts from sibling sessions: date-gap (item 80), fx-reference (item 81), row-type (item 73). None of the three is in the bundle (`date_gap_zone`, `reference_gap_band`, `row_type` 0 hits).
- Ops status for brisken: unknown plan, no `platform` section assessed (FastAPI on Fly; not a Make/n8n client).

---

## Next Steps

1. Merge PR #907 on CI green.
2. Item 23 round 4 backend PR: delete `@app.get("/runs/{run_id}/zoho.csv")`, the journal module, and `export_approved_only` with its store default. Regress-check, deploy, then drive July's Downloads row.
3. Re-check two drive residues by hand before writing any fix. First, August view 2's caption "1 waits on a receipt another charge holds". Second, whether `?view=unmatched` seeds the view on load: in a fresh session the query was stripped and view 1 opened.
4. PT pass on July (strip, card labels, folds, "Mostrar linhas decididas"), and ask Criss to read the new PT keys.
5. Before the owner pastes `lovable-date-gap-prompt.md`: its preamble still names `brisken-expense-recon.fly.dev` as the backend, so strip that phrase or it may repoint the API base.
6. Remove merged worktrees (the classifier blocked removal this session): `agentic-ops1-deploy-0916`, `agentic-ops1-heldby`, `agentic-ops1-monthviews`, and after #907 merges `agentic-ops1-p79-applied` and `agentic-ops1-cp-monthviews`.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 79, item 23 round table)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` (Applied rows for items 79 / 23, Not applied rows for 80 / 81 / 73)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-month-views-prompt.md` (what every later SPA prompt now writes against)

### Open Questions
- PT wording of the new keys (Criss's read).
- Did "ordered in their respective overview pages" mean the listed card sequence or only "organised into"?
- Is the `?view=` deep-link behaviour a defect or a drive artefact?

### Working Notes
- **Vault login without printing:** the entry `Brisken recon operator code matthias` is a dict `{code, notes}`. Fill `['code']` via a shell variable. Filling the whole entry cost two 401s earlier, and the throttle is 5 failures per 15 minutes.
- **Bearer for API re-reads:** the token is in the SPA's `localStorage['erc-token']` after login. Read it into a variable, never echo it.
- **agent-browser click misses:** the first card click after a navigation did not switch the view on July, and three attempts on August never did, while later July clicks worked. `find role button click --name "..."` also did nothing. Next attempt: `eval` a DOM `.click()` on the button whose text starts with the card label, then read `location.search`.
- **Consumer gate:** `deploy-consumer-gate.py` does not see `agent-browser` behind a shell variable (`$AB ...`). Use the literal command for page-state reads.
- **Bundle audit:** `tools/lovable-bundle-audit.py` has no args; a round is audited by editing `NEW`. This session imported its `fetch_corpus` from a scratch script instead, which avoids a tracked edit per round.
- **Duplicate count in the panel:** July reads "6 decided" (receipt groups count as decided) and August "11 decided".

### Reference Materials
- Plan: `C:\Users\neuma_p1qrsic\.claude\plans\plan-the-restructure-of-crispy-wozniak.md`
- PRs: #899 (prompts), #900 (backend), #901 (records), #907 (verified records)
- Live months: July `50622baec444`, August `074a7b8905d7`, September `51a22ad72864`; legacy run `f639bef7813a`

---

## How to Continue

`/comd_resume brisken`, confirm #907 merged, then take next step 2 (round 4 backend deletion) in a fresh worktree off origin/main. The SPA consumer half is proven gone, so the deletion needs no further gate.

---

## Strategic Feedback

### What Worked Well This Session
- Driving the live pages before designing. The four structural findings (one-way links, the statementless crash, posted rows as open work, the pinned tile bar) came from the drive, not from the code, and each became a section of the prompt.
- An adversarial review of the prompts before merge caught a hook-order bug that would have crashed every workbench load. The alternative was discovering it after the owner's publish.
- Predicting where the build would put the shared component (`chunk-ReceiptViewer`) meant the bundle audit's absence from the route chunks read as expected rather than as a failure.

### Suggestions
- `regress_check.py` fails on CRLF sources with an IndentationError from the mutation, and a subagent had to convert and restore by hand. Make the tool read and write bytes with the file's own newline so mutation checks work on this module's CRLF files.

### System Health
- The consumer gate cannot see a browser drive issued through a shell variable, which cost one redone turn. Resolving simple variable indirection in the hook would close it.
- Autonomy: 3 human interventions (plan approval, the prompt hand-off request, the publish report). All were owner-held steps (approval, Lovable paste and publish); none was a correction.
